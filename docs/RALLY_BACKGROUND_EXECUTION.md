# Rally background execution

> Run lifetime is a function of the run directory, not the shell that launched it.

## 1. North star

Rally is filesystem-first: every piece of runtime state that matters is a
file under `runs/active/<RUN_ID>/`. Background execution preserves that
contract end-to-end. There is no daemon, no socket, no database, and no
queue. A run's liveness is computed on every read from four sources:

1. `state.yaml` — the durable, stored status.
2. `heartbeat.json` — a 15-second wall clock that a live loop updates.
3. `done.json` — a sentinel written on any clean exit.
4. `control/stop.requested` — presence means "stop at the next turn
   boundary."

The reference implementation we draw from is `runc`: terminal states are
stored, transient states are computed, and `CRASHED` / `ORPHANED` / `STALE`
fall out of a lazy reconciler rather than an event loop.

## 2. Model

### 2.1 Run directory layout

```
runs/active/<RUN_ID>/
├── run.yaml                     Atomic-written
├── state.yaml                   Atomic-written; schema_version=2
├── heartbeat.json               Background thread, every 15s
├── done.json                    Written on any clean loop exit
├── control/
│   └── stop.requested           rally stop writes; loop observes
├── logs/
│   ├── events.jsonl             Authoritative event stream
│   ├── stdout.log               Detached child stdout
│   ├── stderr.log               Detached child stderr
│   └── agents/<slug>.jsonl      Per-agent event fans-out
└── home/
    ├── issue.md                 Current-view ledger
    └── ...
runs/locks/<FLOW_CODE>.lock      Held via fcntl.flock for the run's lifetime
```

### 2.2 Process identity

A bare PID is not a durable identity because PIDs are reused. Rally
records `(pid, create_time)` — the process's kernel-reported start time,
which is immutable across the process's lifetime. The reconciler compares
the live process's `create_time` against the recorded one; a mismatch is
how `ORPHANED` gets detected.

`psutil` is the single source of this information. It is isolated to
`rally.services.process_identity`; no other module imports psutil, which
keeps the dependency swappable.

### 2.3 Lock discipline

The per-flow lock migrated from O_EXCL + PID file to `fcntl.flock`. Two
properties matter:

1. The lock is on the open file description, not the process, so closing
   one fd does not release it while another open fd points to the same
   OFD. This lets the flow lock survive a `fork` — the grandchild
   inherits a copy of the fd and the lock stays held.
2. The kernel releases the lock on process death, so a crashed run can't
   leave a stuck `.lock` file behind.

### 2.4 Status matrix

**Stored in `state.yaml`** (unchanged plus STOPPED):
`PENDING`, `RUNNING`, `PAUSED`, `SLEEPING`, `BLOCKED`, `DONE`, `STOPPED`.

**Computed by `reconcile`** (never written back):

| Stored | PID probe | heartbeat | done.json | → Reconciled |
|---|---|---|---|---|
| DONE / BLOCKED / STOPPED | any | any | any | pass-through |
| RUNNING / PAUSED / SLEEPING | no pid recorded (v1 / foreground) | — | — | pass-through |
| RUNNING / PAUSED | DEAD | — | present | pass-through (race at shutdown) |
| RUNNING / PAUSED | DEAD | — | absent | **CRASHED** |
| RUNNING / PAUSED | REUSED | — | — | **ORPHANED** |
| RUNNING | ALIVE | stale (> 3× interval) | — | **STALE** |
| else | ALIVE | fresh | — | pass-through |

A live stop request is a diagnostic, not a state — `rally status` shows
`Stop requested: yes` while the loop is still mid-turn, then the loop
transitions to `STOPPED` the moment it observes the file.

### 2.5 Heartbeat

A `HeartbeatThread` writes `heartbeat.json` every 15 seconds with
`{pid, create_time, turn_index, ts, schema_version}`. It runs inside the
main loop's lock / recorder scope and stops cleanly in the `finally`
block. Adapter turns often take many minutes, so the heartbeat is what
distinguishes "long turn in progress" from "loop is wedged."

## 3. CLI surface

```
rally run <flow> [--detach] [--step] [--new] [--from-file <path>] \
                 [--model <name>] [--thinking <effort>]
rally resume <run-id> [--detach] [--step] [--edit|--restart] \
                      [--model <name>] [--thinking <effort>]
rally stop <run-id> [--now] [--grace <secs>]
rally watch <run-id> [--since <n>] [--follow]
rally status [<run-id>]
```

`--detach` is opt-in for this release; flipping it to the default waits
on a follow-up verification pass across Linux and macOS.

`rally stop` is cooperative by default. `--now` escalates directly to
SIGTERM → (grace) → SIGKILL, targeting the run's recorded pgid when the
run was detached (pgid == pid for a double-fork leader), and otherwise
the recorded pid.

## 4. Lifecycle

```
                    ┌────────────┐
                    │  PENDING   │
                    └─────┬──────┘
                          ▼
                    ┌────────────┐
               ┌────│  RUNNING   │────┐
               │    └─────┬──────┘    │
               │          │           │
           handoff     sleep /      stop.requested
               │      step / eof       │
               │          │            ▼
               ▼          ▼     ┌────────────┐
         ┌─────────┐ ┌─────────┐│  STOPPED   │
         │ SLEEPING│ │ PAUSED  │└────────────┘
         └────┬────┘ └────┬────┘
              ▼           ▼
         ┌────────────────────┐
         │  DONE  /  BLOCKED  │
         └────────────────────┘

Computed overlay (never persisted):
  RUNNING|PAUSED + pid dead + no done.json  → CRASHED
  RUNNING|PAUSED + pid reused               → ORPHANED
  RUNNING        + heartbeat stale          → STALE
```

## 5. Failure matrix

| Failure | Observed behavior | Recovery |
|---|---|---|
| `kill -9 <pid>` | `rally status` reports CRASHED (dead pid + no done.json). | `rally resume <id> --restart` |
| Process forks off, parent dies mid-turn | Reconciler flags CRASHED; lock released by kernel. | `rally resume <id> --restart` |
| PID reused by an unrelated process | Reconciler reports ORPHANED via create_time mismatch. | `rally resume <id> --restart` |
| Loop alive but wedged (SIGSTOP, deadlocked adapter) | Heartbeat goes stale; status shows STALE. | `rally stop <id> --now` |
| Two concurrent `rally run <flow>` | Second exits cleanly with "flow is locked by another Rally command." | Wait or stop the current run. |
| `stop.requested` dropped mid-turn | Loop picks it up at the next turn boundary; transitions to STOPPED. | `rally resume <id>` |
| Cooperative stop ignored (adapter hung) | Follow up with `rally stop <id> --now`; SIGTERM, then SIGKILL after grace. | — |
| `heartbeat.json` deleted from a live run | Reconciler reports STALE at next threshold. | No action needed; thread recreates on next beat. |

## 6. Verification runbook

Run the following end-to-end before merging:

1. **Detach happy path** — `rally run <flow> --detach --from-file ./issue.md` returns immediately with the grandchild pid; `rally status <id>` is RUNNING; `rally watch <id> --follow` streams events; the run reaches DONE; `done.json` is present.
2. **Cooperative stop** — start a long detached run, `rally stop <id>`, watch the loop transition to STOPPED at the next turn boundary; `home/issue.md` gains a "Rally Stopped" entry.
3. **Hard stop** — start a detached run, `rally stop <id> --now`, confirm the run's process group terminates and reconciler reports CRASHED (no `done.json`).
4. **Crash recovery** — `kill -9 <pid>` on a live detached run, confirm `rally status` reports CRASHED and that `rally run <flow>` refuses with clear guidance pointing at `rally resume <id> --restart`.
5. **PID reuse** — hand-edit `state.yaml` to a known-unrelated pid with a recent `create_time`, confirm reconciler reports ORPHANED.
6. **Heartbeat stale** — start a detached run, `kill -STOP <pid>`, wait the stale threshold, confirm `rally status` reports STALE, then `kill -CONT <pid>` to restore RUNNING.
7. **Concurrent lock** — two simultaneous `rally run <same-flow>`; the second exits cleanly without trampling state.

## 7. Rationale

**Why no daemon.** A daemon would solve exactly one problem (liveness
detection) and introduce several: process supervision, state
synchronization, install footprint, failure modes that extend beyond the
run directory. The filesystem primitives here solve the same problem with
no additional surface area.

**Why `fcntl.flock` over O_EXCL+PID.** O_EXCL requires writing a PID to
the lock file and reading it back later; that implies reconciling the PID
against a live probe. `fcntl.flock` makes the kernel do exactly that. It
also survives `fork` cleanly, which matters for the double-fork detach
path.

**Why `(pid, create_time)` over bare PID.** Pure-PID probes lie when
something else reuses the pid. ORPHANED detection is not a nice-to-have;
it is the only way to keep from mis-signaling an unrelated process during
`rally stop --now`.

**Why computed status over stored status.** Storing CRASHED means
whichever process notices the crash has to successfully write state.yaml
to record it — that's exactly the class of process that just failed.
Computing status on every read puts correctness where the knowledge is.

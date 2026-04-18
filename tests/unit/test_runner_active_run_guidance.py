"""Tests for tailored active-run refusal messages and terminal-run prompt skipping.

Covers two recovery-path UX fixes:

* ``_render_active_run_refusal_message`` emits status-specific next-action
  guidance (run / stop / resume / restart) — ``rally run <flow>`` now points
  the operator at the right recovery command instead of the bare "already
  has an active run" wording.

* ``_confirm_replace_active_run`` auto-accepts when the active run's
  reconciled status is terminal (DONE/BLOCKED/STOPPED/CRASHED/ORPHANED).
  That lets ``rally run --new --detach`` and ``rally resume --restart
  --detach`` hand back control without needing a TTY on the
  crash-recovery path.
"""

from __future__ import annotations

import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from rally.domain.run import (
    RECONCILED_STATUS_TERMINAL,
    ReconciledStatus,
    RunRecord,
    RunState,
    RunStatus,
)
from rally.errors import RallyUsageError
from rally.services.runner import (
    _confirm_replace_active_run,
    _refuse_if_active_run_exists,
    _render_active_run_guidance,
    _render_active_run_refusal_message,
)


def _record(run_id: str = "DMO-1", flow_code: str = "DMO") -> RunRecord:
    return RunRecord(
        id=run_id,
        flow_name="demo",
        flow_code=flow_code,
        adapter_name="codex",
        start_agent_key="scope_lead",
        created_at="2026-04-17T12:00:00Z",
    )


def _state(status: RunStatus = RunStatus.RUNNING) -> RunState:
    return RunState(
        status=status,
        current_agent_key="scope_lead",
        current_agent_slug="scope_lead",
        turn_index=0,
        updated_at="2026-04-17T12:00:00Z",
    )


class RenderActiveRunRefusalMessageTests(unittest.TestCase):
    def test_message_includes_run_id_and_reconciled_status(self) -> None:
        msg = _render_active_run_refusal_message(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.RUNNING,
        )
        self.assertIn("`DMO-1`", msg)
        self.assertIn("status: running", msg)
        self.assertIn("demo", msg)

    def test_crashed_points_at_restart_or_new(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.CRASHED,
        )
        self.assertIn("rally resume DMO-1 --restart", guidance)
        self.assertIn("rally run demo --new", guidance)
        self.assertIn("no longer alive", guidance)

    def test_orphaned_matches_crashed_guidance(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.ORPHANED,
        )
        self.assertIn("rally resume DMO-1 --restart", guidance)
        self.assertIn("rally run demo --new", guidance)

    def test_running_points_at_watch_stop_or_new(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.RUNNING,
        )
        self.assertIn("rally watch DMO-1", guidance)
        self.assertIn("rally stop DMO-1", guidance)
        self.assertIn("rally run demo --new", guidance)

    def test_stale_points_at_status_and_stop_or_restart(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.STALE,
        )
        self.assertIn("rally status DMO-1", guidance)
        self.assertIn("rally stop DMO-1", guidance)
        self.assertIn("rally resume DMO-1 --restart", guidance)

    def test_paused_points_at_resume(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.PAUSED,
        )
        self.assertIn("rally resume DMO-1", guidance)
        self.assertNotIn("--restart", guidance)

    def test_sleeping_points_at_resume(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.SLEEPING,
        )
        self.assertIn("rally resume DMO-1", guidance)

    def test_terminal_stored_points_at_new(self) -> None:
        for status in (
            ReconciledStatus.DONE,
            ReconciledStatus.BLOCKED,
            ReconciledStatus.STOPPED,
        ):
            with self.subTest(status=status):
                guidance = _render_active_run_guidance(
                    flow_name="demo",
                    active_run_id="DMO-1",
                    reconciled_status=status,
                )
                self.assertIn("rally run demo --new", guidance)
                self.assertIn("finished", guidance)

    def test_pending_falls_back_to_generic_menu(self) -> None:
        guidance = _render_active_run_guidance(
            flow_name="demo",
            active_run_id="DMO-1",
            reconciled_status=ReconciledStatus.PENDING,
        )
        self.assertIn("rally resume DMO-1", guidance)
        self.assertIn("rally stop DMO-1", guidance)
        self.assertIn("rally run demo --new", guidance)


class ConfirmReplaceActiveRunTests(unittest.TestCase):
    def test_terminal_reconciled_status_skips_prompt(self) -> None:
        for status in RECONCILED_STATUS_TERMINAL:
            with self.subTest(status=status):
                # No TTY patching — prompt-skip must trigger before the TTY
                # check, otherwise ``rally resume --restart --detach`` would
                # still fail in non-interactive environments.
                result = _confirm_replace_active_run(
                    active_run=_record(),
                    active_state=_state(RunStatus.RUNNING),
                    reconciled_status=status,
                    command_text="rally run demo --new",
                    prompt="should not display",
                )
                self.assertTrue(result)

    def test_non_terminal_status_without_tty_raises(self) -> None:
        with self.assertRaisesRegex(RallyUsageError, "needs an interactive TTY"):
            _confirm_replace_active_run(
                active_run=_record(),
                active_state=_state(RunStatus.RUNNING),
                reconciled_status=ReconciledStatus.RUNNING,
                command_text="rally run demo --new",
                prompt="Archive run `DMO-1`? [y/N]: ",
            )

    def test_non_terminal_status_with_tty_prompts(self) -> None:
        class _FakeTTY:
            def __init__(self, text: str = "") -> None:
                self._text = text
                self.written = ""

            def isatty(self) -> bool:
                return True

            def write(self, value: str) -> None:
                self.written += value

            def flush(self) -> None:
                return None

            def readline(self) -> str:
                return self._text

        fake_stdin = _FakeTTY("yes\n")
        fake_stdout = _FakeTTY()
        with patch("rally.services.runner.sys.stdin", fake_stdin), patch(
            "rally.services.runner.sys.stdout", fake_stdout
        ):
            accepted = _confirm_replace_active_run(
                active_run=_record(),
                active_state=_state(RunStatus.RUNNING),
                reconciled_status=ReconciledStatus.RUNNING,
                command_text="rally run demo --new",
                prompt="Archive run `DMO-1`? [y/N]: ",
            )
        self.assertTrue(accepted)
        self.assertIn("Archive run `DMO-1`?", fake_stdout.written)


class RefuseIfActiveRunExistsTests(unittest.TestCase):
    """Direct tests for the helper that ``run_flow`` uses to fail fast.

    We avoid the full ``run_flow`` entry point (which loads flow YAML,
    compiled agents, and a real adapter) by calling the helper directly
    with a lightweight flow stub that exposes only the two attributes
    the helper reads (``name`` and ``code``).
    """

    def _flow_stub(self) -> object:
        return types.SimpleNamespace(name="demo", code="DMO")

    def test_returns_quietly_when_no_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            _refuse_if_active_run_exists(
                repo_root=repo_root, flow=self._flow_stub()
            )

    def test_raises_tailored_crashed_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_dir = _seed_active_run(
                repo_root=repo_root, status=RunStatus.RUNNING
            )
            with patch(
                "rally.services.runner.reconcile_from_state",
                return_value=_fake_reconciled(
                    ReconciledStatus.CRASHED, run_dir=run_dir
                ),
            ):
                with self.assertRaises(RallyUsageError) as ctx:
                    _refuse_if_active_run_exists(
                        repo_root=repo_root, flow=self._flow_stub()
                    )
            message = str(ctx.exception)
            self.assertIn("`DMO-1`", message)
            self.assertIn("status: crashed", message)
            self.assertIn("rally resume DMO-1 --restart", message)
            self.assertIn("rally run demo --new", message)

    def test_raises_tailored_running_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_dir = _seed_active_run(
                repo_root=repo_root, status=RunStatus.RUNNING
            )
            with patch(
                "rally.services.runner.reconcile_from_state",
                return_value=_fake_reconciled(
                    ReconciledStatus.RUNNING, run_dir=run_dir
                ),
            ):
                with self.assertRaises(RallyUsageError) as ctx:
                    _refuse_if_active_run_exists(
                        repo_root=repo_root, flow=self._flow_stub()
                    )
            message = str(ctx.exception)
            self.assertIn("rally watch DMO-1", message)
            self.assertIn("rally stop DMO-1", message)
            self.assertIn("status: running", message)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _fake_reconciled(status: ReconciledStatus, *, run_dir: Path):
    from rally.services.reconcile import ReconciledRun
    from rally.services.run_store import load_run_state

    return ReconciledRun(
        status=status,
        state=load_run_state(run_dir=run_dir),
        identity=None,
        liveness=None,
        heartbeat=None,
        heartbeat_stale=False,
        done_marker_present=False,
        stop_requested=False,
    )


def _seed_active_run(*, repo_root: Path, status: RunStatus) -> Path:
    from rally.services.run_store import active_runs_dir, write_run_record, write_run_state

    run_dir = active_runs_dir(repo_root) / "DMO-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    write_run_record(run_dir=run_dir, record=_record())
    write_run_state(run_dir=run_dir, state=_state(status=status))
    return run_dir


if __name__ == "__main__":
    unittest.main()

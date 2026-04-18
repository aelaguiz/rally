from __future__ import annotations

import multiprocessing as mp
import os
import time
import unittest
from dataclasses import replace

from rally.services.process_identity import (
    LivenessStatus,
    ProcessIdentity,
    capture_self,
    probe,
)


def _sleep_forever() -> None:
    # Child that blocks until killed; used to exercise ALIVE and REUSED paths.
    time.sleep(60)


class ProcessIdentityTests(unittest.TestCase):
    def test_capture_self_returns_current_pid(self) -> None:
        identity = capture_self()
        self.assertEqual(identity.pid, os.getpid())
        self.assertGreater(identity.create_time, 0.0)

    def test_probe_self_is_alive(self) -> None:
        identity = capture_self()
        self.assertEqual(probe(identity), LivenessStatus.ALIVE)

    def test_probe_dead_pid_is_dead(self) -> None:
        ctx = mp.get_context("fork")
        proc = ctx.Process(target=_sleep_forever)
        proc.start()
        try:
            self.assertIsNotNone(proc.pid)
            identity = ProcessIdentity(pid=proc.pid or 0, create_time=time.time())
            # Capture real create_time while the process is running.
            from rally.services.process_identity import psutil  # internal handle
            identity = ProcessIdentity.from_psutil(psutil.Process(proc.pid))
            self.assertEqual(probe(identity), LivenessStatus.ALIVE)
        finally:
            proc.kill()
            proc.join(timeout=5.0)

        # Give the kernel a moment to reap.
        time.sleep(0.05)
        self.assertEqual(probe(identity), LivenessStatus.DEAD)

    def test_probe_reused_pid_is_reused(self) -> None:
        # Forge an identity with the current pid but a wildly wrong
        # create_time. The process itself is alive, but the identity's
        # create_time does not match, so we classify as REUSED.
        identity = capture_self()
        stale = replace(identity, create_time=identity.create_time - 3600.0)
        self.assertEqual(probe(stale), LivenessStatus.REUSED)

    def test_probe_tolerates_subsecond_jitter(self) -> None:
        identity = capture_self()
        jittered = replace(identity, create_time=identity.create_time + 0.1)
        self.assertEqual(probe(jittered), LivenessStatus.ALIVE)

    def test_probe_nonexistent_pid_is_dead(self) -> None:
        # PID 2^31-1 is reserved / unused on every mainstream kernel.
        forged = ProcessIdentity(pid=(1 << 31) - 1, create_time=time.time())
        self.assertEqual(probe(forged), LivenessStatus.DEAD)


if __name__ == "__main__":
    unittest.main()

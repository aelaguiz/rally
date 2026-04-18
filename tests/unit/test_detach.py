from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


# Best-effort smoke tests for the double-fork detach machinery. Fork
# semantics are awkward to exercise in-process under unittest, so we
# run each scenario in its own subprocess with a small Python script.

_DETACH_SCRIPT = """
import os
import sys
import time
from pathlib import Path

from rally.services.detach import spawn_detached

run_dir = Path(sys.argv[1])
run_dir.mkdir(parents=True, exist_ok=True)
handoff = spawn_detached(run_dir)
if handoff is not None:
    print(f"PARENT pid={handoff.child_pid}")
    sys.exit(0)
# Grandchild: write a marker file proving detach worked, then exit.
marker = run_dir / "grandchild.done"
marker.write_text(f"pid={os.getpid()} pgid={os.getpgid(0)} sid={os.getsid(0)}\\n")
sys.stdout.write("GRANDCHILD wrote marker\\n")
sys.stdout.flush()
"""


@unittest.skipIf(os.name != "posix", "double-fork is POSIX-only")
class SpawnDetachedTests(unittest.TestCase):
    def test_parent_returns_handoff_and_grandchild_writes_marker(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run"
            script_path = Path(temp_dir) / "detach_script.py"
            script_path.write_text(_DETACH_SCRIPT)

            completed = subprocess.run(
                [sys.executable, str(script_path), str(run_dir)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PARENT pid=", completed.stdout)

            marker = run_dir / "grandchild.done"
            deadline = time.monotonic() + 5.0
            while not marker.is_file() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(
                marker.is_file(),
                msg=f"Grandchild never wrote marker. Parent stdout: {completed.stdout!r}",
            )
            body = marker.read_text()
            self.assertIn("pid=", body)
            self.assertIn("pgid=", body)
            self.assertIn("sid=", body)

    def test_grandchild_stdout_redirects_into_logs(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run"
            script_path = Path(temp_dir) / "detach_script.py"
            script_path.write_text(_DETACH_SCRIPT)

            subprocess.run(
                [sys.executable, str(script_path), str(run_dir)],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            marker = run_dir / "grandchild.done"
            deadline = time.monotonic() + 5.0
            while not marker.is_file() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(marker.is_file())
            stdout_log = run_dir / "logs" / "stdout.log"
            self.assertTrue(stdout_log.is_file())
            self.assertIn("GRANDCHILD wrote marker", stdout_log.read_text())


if __name__ == "__main__":
    unittest.main()

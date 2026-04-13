from __future__ import annotations

import unittest

from rally.domain.run import RunStatus


class RunContractsTests(unittest.TestCase):
    def test_run_status_values_stay_stable(self) -> None:
        self.assertEqual(RunStatus.PENDING.value, "pending")
        self.assertEqual(RunStatus.RUNNING.value, "running")
        self.assertEqual(RunStatus.SLEEPING.value, "sleeping")
        self.assertEqual(RunStatus.BLOCKED.value, "blocked")
        self.assertEqual(RunStatus.DONE.value, "done")


if __name__ == "__main__":
    unittest.main()

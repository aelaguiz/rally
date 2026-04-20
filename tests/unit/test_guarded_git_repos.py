from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from rally.services.guarded_git_repos import (
    GuardedGitRepoViolation,
    check_guarded_git_repos,
    render_guarded_git_repo_blocker,
)


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr=stderr)


class CheckGuardedGitReposTests(unittest.TestCase):
    # Protects the guard that refuses to launch a flow whose bundled repos are
    # missing or dirty. A regression here would allow real product runs to
    # start against half-prepared repos, corrupting fixture state silently.

    def test_missing_repo_yields_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: self.fail("git should not run when repo is missing"),
            )
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].relative_path, Path("repos/demo"))
            self.assertIn("missing", violations[0].reason)

    def test_non_directory_yields_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos").mkdir()
            (run_home / "repos" / "demo").write_text("not a dir", encoding="utf-8")

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: self.fail("git should not run on non-dir"),
            )
            self.assertEqual(len(violations), 1)
            self.assertIn("not a directory", violations[0].reason)

    def test_clean_repo_yields_no_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos" / "demo").mkdir(parents=True)

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: _completed(returncode=0, stdout=""),
            )
            self.assertEqual(violations, ())

    def test_dirty_repo_preview_includes_up_to_five_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos" / "demo").mkdir(parents=True)
            status = "\n".join([
                " M a.py",
                " M b.py",
                "?? c.py",
            ])

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: _completed(returncode=0, stdout=status + "\n"),
            )

            self.assertEqual(len(violations), 1)
            reason = violations[0].reason
            self.assertTrue(reason.startswith("repo is dirty:"))
            self.assertIn("M a.py", reason)
            self.assertIn("M b.py", reason)
            self.assertIn("?? c.py", reason)
            self.assertNotIn("...", reason)

    def test_dirty_repo_preview_truncates_beyond_five_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos" / "demo").mkdir(parents=True)
            status_lines = [f" M file_{i}.py" for i in range(7)]
            status = "\n".join(status_lines)

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: _completed(returncode=0, stdout=status + "\n"),
            )

            self.assertEqual(len(violations), 1)
            reason = violations[0].reason
            self.assertIn("M file_0.py", reason)
            self.assertIn("M file_4.py", reason)
            self.assertNotIn("M file_5.py", reason)
            self.assertTrue(reason.endswith("; ..."))

    def test_git_status_nonzero_exit_uses_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos" / "demo").mkdir(parents=True)

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: _completed(
                    returncode=128,
                    stdout="",
                    stderr="fatal: not a git repository\n",
                ),
            )

            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].reason, "fatal: not a git repository")

    def test_git_status_nonzero_exit_falls_back_to_generic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos" / "demo").mkdir(parents=True)

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=lambda *a, **kw: _completed(returncode=1, stdout="", stderr=""),
            )

            self.assertEqual(violations[0].reason, "git status failed")

    def test_os_error_from_subprocess_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir)
            (run_home / "repos" / "demo").mkdir(parents=True)

            def raise_os_error(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                raise OSError("git binary missing")

            violations = check_guarded_git_repos(
                run_home=run_home,
                guarded_git_repos=[Path("repos/demo")],
                subprocess_run=raise_os_error,
            )

            self.assertEqual(len(violations), 1)
            self.assertIn("git binary missing", violations[0].reason)
            self.assertTrue(violations[0].reason.startswith("git status failed to start"))


class RenderGuardedGitRepoBlockerTests(unittest.TestCase):
    # Protects the operator-facing blocker message. The single vs. multiple
    # branch is the path operators see in Rally's stop-ledger; wording drift
    # would break grep-based diagnosis.

    def test_empty_violations_raises(self) -> None:
        with self.assertRaises(ValueError):
            render_guarded_git_repo_blocker(violations=())

    def test_single_violation_renders_singular_phrase(self) -> None:
        violation = GuardedGitRepoViolation(
            relative_path=Path("repos/demo"),
            reason="repo is dirty: M a.py",
        )
        message = render_guarded_git_repo_blocker(violations=[violation])
        self.assertEqual(
            message,
            "Guarded repo `repos/demo` is not ready: repo is dirty: M a.py.",
        )

    def test_multiple_violations_render_plural_phrase(self) -> None:
        violations = [
            GuardedGitRepoViolation(
                relative_path=Path("repos/demo"),
                reason="repo is missing from the run home",
            ),
            GuardedGitRepoViolation(
                relative_path=Path("repos/other"),
                reason="repo is dirty: ?? new.py",
            ),
        ]
        message = render_guarded_git_repo_blocker(violations=violations)
        self.assertEqual(
            message,
            (
                "Guarded repos are not ready: "
                "`repos/demo`: repo is missing from the run home; "
                "`repos/other`: repo is dirty: ?? new.py."
            ),
        )


if __name__ == "__main__":
    unittest.main()

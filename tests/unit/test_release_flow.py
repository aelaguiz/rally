from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from rally._release_flow.parsing import (
    load_compiled_contract_version,
    load_doctrine_floor,
    load_doctrine_package_line,
    load_package_metadata_version,
    load_workspace_version,
)
from rally.release_flow import (
    draft_release,
    prepare_release,
    publish_release,
    render_release_worksheet,
    tag_release,
)


class ReleaseFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.docs_dir = self.root / "docs"
        self.docs_dir.mkdir(parents=True)
        (self.root / "src" / "rally" / "services").mkdir(parents=True)

        self._git("init", "-b", "main")
        self._git("config", "user.name", "Rally Test")
        self._git("config", "user.email", "rally@example.com")

        (self.root / "README.md").write_text("# Rally test repo\n", encoding="utf-8")
        self._write_pyproject(package_version="0.1.0")
        self._write_versioning(public_release="none yet", package_version="0.1.0")
        self._write_flow_loader(contract_version=1)
        self._write_changelog(unreleased="- No public release yet.\n")
        self._commit("initial state")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_prepare_release_renders_ready_minor_release_worksheet(self) -> None:
        self._tag("v0.1.0")
        self._write_pyproject(package_version="0.2.0")
        self._write_versioning(public_release="v0.1.0", package_version="0.2.0")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v0.2.0",
                    release_kind="Non-breaking",
                    channel="stable",
                ),
            ),
        )

        with patch("rally._release_flow.tags.require_public_release_tag"):
            plan = prepare_release(
                repo_root=self.root,
                release="v0.2.0",
                release_class="additive",
                channel="stable",
            )
        worksheet = render_release_worksheet(plan)

        self.assertEqual(plan.release_kind, "Non-breaking")
        self.assertEqual(plan.previous_stable_tag.raw, "v0.1.0")
        self.assertIn("Current public release version: v0.1.0", worksheet)
        self.assertIn("Requested release version: v0.2.0", worksheet)
        self.assertIn("Package metadata status: ready (`0.2.0`)", worksheet)
        self.assertIn("Current workspace manifest version: 1", worksheet)
        self.assertIn("Current compiled contract version: 1", worksheet)
        self.assertIn("Current minimum Doctrine release: v1.0.2", worksheet)
        self.assertIn("Current supported Doctrine package line: doctrine-agents>=1.0.2,<2", worksheet)
        self.assertIn("Changelog entry status: ready (`v0.2.0 - 2026-04-14`)", worksheet)
        self.assertIn("make build-dist", worksheet)
        self.assertIn("make verify-package", worksheet)
        self.assertIn("tests/unit/test_package_release.py -q", worksheet)
        self.assertIn(
            "Before the first real TestPyPI or PyPI publish for `rally-agents`",
            worksheet,
        )
        self.assertIn(
            "make release-draft RELEASE=v0.2.0 CHANNEL=stable PREVIOUS_TAG=auto",
            worksheet,
        )

    def test_load_support_surface_versions_from_repo_truth(self) -> None:
        self.assertEqual(load_package_metadata_version(self.root), "0.1.0")
        self.assertEqual(load_workspace_version(self.root), 1)
        self.assertEqual(load_compiled_contract_version(self.root), 1)
        self.assertEqual(load_doctrine_floor(self.root), "v1.0.2")
        self.assertEqual(load_doctrine_package_line(self.root), "doctrine-agents>=1.0.2,<2")

    def test_prepare_release_reports_package_metadata_status(self) -> None:
        self._tag("v0.1.0")
        self._write_versioning(public_release="v0.1.0", package_version="0.1.0")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v0.1.1",
                    release_kind="Non-breaking",
                    channel="stable",
                ),
            ),
        )

        with patch("rally._release_flow.tags.require_public_release_tag"):
            plan = prepare_release(
                repo_root=self.root,
                release="v0.1.1",
                release_class="internal",
                channel="stable",
            )
        worksheet = render_release_worksheet(plan)

        self.assertIn("Current package metadata version: 0.1.0", worksheet)
        self.assertIn("Requested package metadata version: 0.1.1", worksheet)
        self.assertIn(
            'Package metadata status: needs `[project].version = "0.1.1"` in `pyproject.toml`',
            worksheet,
        )

    def test_prepare_release_rejects_internal_minor_bump(self) -> None:
        self._tag("v0.1.0")

        with (
            patch("rally._release_flow.tags.require_public_release_tag"),
            self.assertRaisesRegex(RuntimeError, "E525 release error: Invalid release version move"),
        ):
            prepare_release(
                repo_root=self.root,
                release="v0.2.0",
                release_class="internal",
                channel="stable",
            )

    def test_prepare_release_rejects_lightweight_previous_tag(self) -> None:
        self._tag("v0.1.0")

        with self.assertRaisesRegex(RuntimeError, "must be an annotated tag, not a lightweight tag"):
            prepare_release(
                repo_root=self.root,
                release="v0.2.0",
                release_class="additive",
                channel="stable",
            )

    def test_prepare_release_rejects_unsigned_annotated_previous_tag(self) -> None:
        self._annotated_tag("v0.1.0")

        with self.assertRaisesRegex(RuntimeError, "must pass `git verify-tag`"):
            prepare_release(
                repo_root=self.root,
                release="v0.2.0",
                release_class="additive",
                channel="stable",
            )

    def test_tag_release_requires_signing_key(self) -> None:
        self._tag("v0.1.0")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v0.1.1",
                    release_kind="Non-breaking",
                    channel="stable",
                ),
            ),
        )
        self._commit("prepare release entry")

        with self.assertRaisesRegex(
            RuntimeError,
            "E528 release error: Release tag signing is not configured",
        ):
            tag_release(repo_root=self.root, release="v0.1.1", channel="stable")

    def test_tag_release_rejects_mismatched_package_version(self) -> None:
        self._tag("v0.1.0")
        self._git("config", "user.signingkey", "fake-key")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v0.1.1",
                    release_kind="Non-breaking",
                    channel="stable",
                ),
            ),
        )
        self._commit("prepare patch release entry with stale package version")

        with (
            patch("rally._release_flow.tags.require_public_release_tag"),
            self.assertRaisesRegex(
                RuntimeError,
                r'E530 release error: Release package metadata version is missing or does not match',
            ),
        ):
            tag_release(repo_root=self.root, release="v0.1.1", channel="stable")

    def test_draft_release_builds_prerelease_github_command_and_notes(self) -> None:
        self._tag("v0.1.0")
        self._tag("v1.0.0-beta.1")
        self._write_pyproject(package_version="1.0.0b2")
        self._write_versioning(public_release="v0.1.0", package_version="1.0.0b2")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v1.0.0-beta.2",
                    release_kind="Breaking",
                    channel="beta.2",
                    upgrade_steps="Replace the old tag-push release flow with the new draft-and-publish flow.",
                ),
            ),
        )
        self._commit("prepare prerelease entry")

        real_run = subprocess.run
        gh_calls: list[list[str]] = []

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            command = args[0]
            if command[0] == "gh":
                gh_calls.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")
            return real_run(*args, **kwargs)

        with (
            patch("rally._release_flow.ops.require_pushed_public_release_tag"),
            patch("rally._release_flow.tags.require_public_release_tag"),
            patch("rally._release_flow.common.subprocess.run", side_effect=fake_run),
        ):
            draft_release(
                repo_root=self.root,
                release="v1.0.0-beta.2",
                channel="beta",
                previous_tag="auto",
            )

        self.assertEqual(len(gh_calls), 1)
        command = gh_calls[0]
        self.assertIn("--draft", command)
        self.assertIn("--verify-tag", command)
        self.assertIn("--generate-notes", command)
        self.assertIn("--prerelease", command)
        self.assertIn("--latest=false", command)
        self.assertIn("--notes-start-tag", command)
        self.assertIn("v1.0.0-beta.1", command)
        notes_path = Path(command[command.index("--notes-file") + 1])
        notes_text = notes_path.read_text(encoding="utf-8")
        self.assertIn("Release kind: Breaking", notes_text)
        self.assertIn("Release channel: beta.2", notes_text)
        self.assertIn("Release version: v1.0.0-beta.2", notes_text)
        self.assertIn("### Changed", notes_text)

    def test_draft_release_builds_stable_github_command_and_notes(self) -> None:
        self._tag("v0.1.0")
        self._write_pyproject(package_version="0.2.0")
        self._write_versioning(public_release="v0.1.0", package_version="0.2.0")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v0.2.0",
                    release_kind="Non-breaking",
                    channel="stable",
                ),
            ),
        )
        self._commit("prepare stable release entry")

        real_run = subprocess.run
        gh_calls: list[list[str]] = []

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            command = args[0]
            if command[0] == "gh":
                gh_calls.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")
            return real_run(*args, **kwargs)

        with (
            patch("rally._release_flow.ops.require_pushed_public_release_tag"),
            patch("rally._release_flow.tags.require_public_release_tag"),
            patch("rally._release_flow.common.subprocess.run", side_effect=fake_run),
        ):
            draft_release(
                repo_root=self.root,
                release="v0.2.0",
                channel="stable",
                previous_tag="auto",
            )

        self.assertEqual(len(gh_calls), 1)
        command = gh_calls[0]
        self.assertIn("--draft", command)
        self.assertIn("--verify-tag", command)
        self.assertIn("--generate-notes", command)
        self.assertNotIn("--prerelease", command)
        self.assertNotIn("--latest=false", command)
        self.assertIn("--notes-start-tag", command)
        self.assertIn("v0.1.0", command)
        notes_path = Path(command[command.index("--notes-file") + 1])
        notes_text = notes_path.read_text(encoding="utf-8")
        self.assertIn("Release kind: Non-breaking", notes_text)
        self.assertIn("Release channel: stable", notes_text)
        self.assertIn("Release version: v0.2.0", notes_text)

    def test_draft_release_rejects_placeholder_release_header(self) -> None:
        self._tag("v0.1.0")
        self._write_pyproject(package_version="0.2.0")
        self._write_versioning(public_release="v0.1.0", package_version="0.2.0")
        self._write_changelog(
            unreleased="- Next release planning starts after this cut.\n",
            released_sections=(
                self._release_section(
                    tag="v0.2.0",
                    release_kind="Non-breaking",
                    channel="stable",
                    affected_surfaces="...",
                ),
            ),
        )
        self._commit("prepare placeholder release entry")

        with (
            patch("rally._release_flow.ops.require_pushed_public_release_tag"),
            patch("rally._release_flow.tags.require_public_release_tag"),
            self.assertRaisesRegex(RuntimeError, "placeholder text in `Affected surfaces`"),
        ):
            draft_release(
                repo_root=self.root,
                release="v0.2.0",
                channel="stable",
                previous_tag="auto",
            )

    def test_publish_release_publishes_and_watches_publish_workflow(self) -> None:
        self._tag("v0.2.0")
        real_run = subprocess.run
        gh_calls: list[list[str]] = []

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            command = args[0]
            if command[:3] == ["gh", "release", "edit"]:
                gh_calls.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")
            if command[:3] == ["gh", "run", "list"]:
                gh_calls.append(command)
                return subprocess.CompletedProcess(
                    command,
                    0,
                    '[{"databaseId": 42, "event": "release", "headSha": "abc", "status": "completed"}]',
                    "",
                )
            if command[:3] == ["gh", "run", "watch"]:
                gh_calls.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")
            return real_run(*args, **kwargs)

        with (
            patch("rally._release_flow.ops.require_pushed_public_release_tag"),
            patch("rally._release_flow.common.subprocess.run", side_effect=fake_run),
        ):
            publish_release(repo_root=self.root, release="v0.2.0")

        self.assertEqual(
            gh_calls,
            [
                ["gh", "release", "edit", "v0.2.0", "--draft=false"],
                [
                    "gh",
                    "run",
                    "list",
                    "--workflow",
                    "publish.yml",
                    "--event",
                    "release",
                    "--commit",
                    self._git_output("rev-list", "-n", "1", "v0.2.0"),
                    "--json",
                    "databaseId,event,headSha,status",
                    "-L",
                    "20",
                ],
                ["gh", "run", "watch", "42", "--exit-status"],
            ],
        )

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )

    def _git_output(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    def _commit(self, message: str) -> None:
        self._git("add", ".")
        self._git("commit", "-m", message)

    def _tag(self, tag: str) -> None:
        self._git("tag", tag)

    def _annotated_tag(self, tag: str) -> None:
        self._git("tag", "-a", tag, "-m", tag)

    def _write_pyproject(self, *, package_version: str, workspace_version: int = 1) -> None:
        (self.root / "pyproject.toml").write_text(
            textwrap.dedent(
                f"""\
                [build-system]
                requires = ["setuptools>=69"]
                build-backend = "setuptools.build_meta"

                [project]
                name = "rally-agents"
                version = "{package_version}"
                requires-python = ">=3.14"
                dependencies = [
                    "doctrine-agents>=1.0.2,<2",
                ]

                [tool.rally.workspace]
                version = {workspace_version}

                [tool.rally.package]
                import_name = "rally"
                pypi_environment = "pypi"
                testpypi_environment = "testpypi"
                """
            ),
            encoding="utf-8",
        )

    def _write_versioning(
        self,
        *,
        public_release: str,
        package_version: str,
        doctrine_floor: str = "v1.0.2",
        doctrine_package_line: str = "doctrine-agents>=1.0.2,<2",
    ) -> None:
        (self.root / "docs" / "VERSIONING.md").write_text(
            textwrap.dedent(
                f"""\
                # Versioning

                Current public Rally release version: {public_release}
                Current Rally package version: {package_version}
                Current workspace manifest version: 1
                Current compiled agent contract version: 1
                Current minimum Doctrine release: {doctrine_floor}
                Current supported Doctrine package line: {doctrine_package_line}
                """
            ),
            encoding="utf-8",
        )

    def _write_flow_loader(self, *, contract_version: int) -> None:
        (self.root / "src" / "rally" / "services" / "flow_loader.py").write_text(
            textwrap.dedent(
                f"""\
                SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS = frozenset({{{contract_version}}})
                """
            ),
            encoding="utf-8",
        )

    def _write_changelog(
        self,
        *,
        unreleased: str,
        released_sections: tuple[str, ...] = (),
    ) -> None:
        released = "\n\n".join(released_sections)
        if released:
            released = f"\n\n{released}"
        (self.root / "CHANGELOG.md").write_text(
            textwrap.dedent(
                f"""\
                # Changelog

                ## Unreleased

                {unreleased.strip()}{released}
                """
            ),
            encoding="utf-8",
        )

    def _release_section(
        self,
        *,
        tag: str,
        release_kind: str,
        channel: str,
        affected_surfaces: str = "CLI release flow, package metadata, and public docs.",
        who_must_act: str = "Maintainers cutting Rally releases.",
        who_does_not_need_to_act: str = "Users who are not cutting a Rally release today.",
        upgrade_steps: str = "No upgrade needed.",
        verification: str = "uv run pytest tests/unit/test_release_flow.py -q",
        support_surface_changes: str = "none",
    ) -> str:
        return textwrap.dedent(
            f"""\
            ## {tag} - 2026-04-14

            Release kind: {release_kind}
            Release channel: {channel}
            Release version: {tag}
            Affected surfaces: {affected_surfaces}
            Who must act: {who_must_act}
            Who does not need to act: {who_does_not_need_to_act}
            Upgrade steps: {upgrade_steps}
            Verification: {verification}
            Support-surface version changes: {support_surface_changes}

            ### Changed
            - Release flow and package metadata were updated for this release.
            """
        ).strip()


if __name__ == "__main__":
    unittest.main()

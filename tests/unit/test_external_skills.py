from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.skill_bundles import (
    resolve_external_skill_bundle_source,
    split_external_skill_name,
)
from rally.services.workspace import (
    ExternalSkillRoot,
    load_external_skill_roots_for_repo_root,
    workspace_context_from_root,
)


_PYPROJECT_HEADER = textwrap.dedent(
    """\
    [project]
    name = "host"

    [tool.rally.workspace]
    version = 1
    """
)


def _write_markdown_skill(root: Path, skill_name: str) -> Path:
    skill_dir = root / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {skill_name}
            description: "An external markdown skill."
            ---

            # {skill_name}
            """
        ),
        encoding="utf-8",
    )
    return skill_dir


def _write_doctrine_skill(root: Path, skill_name: str, *, with_build: bool) -> Path:
    skill_dir = root / skill_name
    (skill_dir / "prompts").mkdir(parents=True)
    (skill_dir / "prompts" / "SKILL.prompt").write_text(
        f'skill package X: "X"\n    metadata:\n        name: "{skill_name}"\n',
        encoding="utf-8",
    )
    if with_build:
        build_dir = skill_dir / "build"
        build_dir.mkdir()
        (build_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: \"Pre-built.\"\n---\n",
            encoding="utf-8",
        )
    return skill_dir


class SplitExternalSkillNameTests(unittest.TestCase):
    def test_splits_qualified_name(self) -> None:
        self.assertEqual(
            split_external_skill_name("psmobile:device-farm"),
            ("psmobile", "device-farm"),
        )

    def test_rejects_missing_alias(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "of the form `<alias>:<skill-name>`"):
            split_external_skill_name("device-farm")

    def test_rejects_empty_skill(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "of the form `<alias>:<skill-name>`"):
            split_external_skill_name("psmobile:")

    def test_rejects_uppercase_alias(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "of the form `<alias>:<skill-name>`"):
            split_external_skill_name("PsMobile:x")


class ResolveExternalSkillBundleSourceTests(unittest.TestCase):
    def test_resolves_markdown_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            root.mkdir()
            _write_markdown_skill(root, "device-farm")

            bundle = resolve_external_skill_bundle_source(
                root=root,
                alias="psmobile",
                skill_name="device-farm",
            )

            self.assertEqual(bundle.kind, "markdown")
            self.assertEqual(bundle.origin_alias, "psmobile")
            self.assertEqual(bundle.runtime_source_dir(), root / "device-farm")

    def test_resolves_doctrine_skill_with_prebuilt_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            root.mkdir()
            skill_dir = _write_doctrine_skill(root, "device-farm", with_build=True)

            bundle = resolve_external_skill_bundle_source(
                root=root,
                alias="psmobile",
                skill_name="device-farm",
            )

            self.assertEqual(bundle.kind, "doctrine")
            self.assertEqual(bundle.runtime_source_dir(), skill_dir / "build")

    def test_doctrine_skill_without_build_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            root.mkdir()
            _write_doctrine_skill(root, "device-farm", with_build=False)

            bundle = resolve_external_skill_bundle_source(
                root=root,
                alias="psmobile",
                skill_name="device-farm",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"External Doctrine skill `psmobile:device-farm` is missing `build/SKILL.md`",
            ):
                bundle.runtime_source_dir()

    def test_missing_skill_directory_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            root.mkdir()

            with self.assertRaisesRegex(
                RallyConfigError,
                r"External skill `psmobile:device-farm` does not exist",
            ):
                resolve_external_skill_bundle_source(
                    root=root,
                    alias="psmobile",
                    skill_name="device-farm",
                )

    def test_rejects_both_markdown_and_doctrine(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            root.mkdir()
            skill_dir = _write_markdown_skill(root, "device-farm")
            (skill_dir / "prompts").mkdir()
            (skill_dir / "prompts" / "SKILL.prompt").write_text("x\n", encoding="utf-8")

            with self.assertRaisesRegex(
                RallyConfigError,
                r"External skill `psmobile:device-farm` must define exactly one source kind",
            ):
                resolve_external_skill_bundle_source(
                    root=root,
                    alias="psmobile",
                    skill_name="device-farm",
                )


class WorkspaceExternalSkillRootsTests(unittest.TestCase):
    def test_loads_external_skill_roots_from_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()
            external_root = Path(temp_dir).resolve() / "external_skills"
            external_root.mkdir()
            (workspace_root / "pyproject.toml").write_text(
                _PYPROJECT_HEADER
                + textwrap.dedent(
                    f"""\
                    [tool.rally.workspace.external_skill_roots]
                    psmobile = "{external_root}"
                    """
                ),
                encoding="utf-8",
            )

            workspace = workspace_context_from_root(
                workspace_root,
                cli_bin=workspace_root / "bin" / "rally",
            )

            self.assertEqual(
                workspace.external_skill_roots,
                (ExternalSkillRoot(alias="psmobile", root=external_root),),
            )

    def test_expands_home_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()
            external_root = Path(temp_dir).resolve() / "external_skills"
            external_root.mkdir()
            (workspace_root / "pyproject.toml").write_text(
                _PYPROJECT_HEADER
                + textwrap.dedent(
                    f"""\
                    [tool.rally.workspace.external_skill_roots]
                    psmobile = "{external_root}"
                    """
                ),
                encoding="utf-8",
            )

            roots = load_external_skill_roots_for_repo_root(repo_root=workspace_root)
            self.assertEqual(len(roots), 1)
            self.assertEqual(roots[0].alias, "psmobile")
            self.assertEqual(roots[0].root, external_root)

    def test_rejects_reserved_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()
            (workspace_root / "pyproject.toml").write_text(
                _PYPROJECT_HEADER
                + textwrap.dedent(
                    f"""\
                    [tool.rally.workspace.external_skill_roots]
                    rally = "{workspace_root}"
                    """
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyConfigError, r"alias `rally`.*reserved"):
                workspace_context_from_root(
                    workspace_root,
                    cli_bin=workspace_root / "bin" / "rally",
                )

    def test_rejects_nested_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()
            nested = workspace_root / "skills_shared"
            nested.mkdir()
            (workspace_root / "pyproject.toml").write_text(
                _PYPROJECT_HEADER
                + textwrap.dedent(
                    f"""\
                    [tool.rally.workspace.external_skill_roots]
                    shared = "{nested}"
                    """
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"points inside the workspace",
            ):
                workspace_context_from_root(
                    workspace_root,
                    cli_bin=workspace_root / "bin" / "rally",
                )

    def test_rejects_missing_root_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()
            missing_root = Path(temp_dir) / "nope"
            (workspace_root / "pyproject.toml").write_text(
                _PYPROJECT_HEADER
                + textwrap.dedent(
                    f"""\
                    [tool.rally.workspace.external_skill_roots]
                    psmobile = "{missing_root}"
                    """
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"does not exist or is not a directory",
            ):
                workspace_context_from_root(
                    workspace_root,
                    cli_bin=workspace_root / "bin" / "rally",
                )

    def test_rejects_bad_alias_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()
            external_root = Path(temp_dir).resolve() / "external_skills"
            external_root.mkdir()
            (workspace_root / "pyproject.toml").write_text(
                _PYPROJECT_HEADER
                + textwrap.dedent(
                    f"""\
                    [tool.rally.workspace.external_skill_roots]
                    Ps_Mobile = "{external_root}"
                    """
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"alias `Ps_Mobile`.*must match",
            ):
                workspace_context_from_root(
                    workspace_root,
                    cli_bin=workspace_root / "bin" / "rally",
                )

    def test_returns_empty_tuple_when_pyproject_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir()

            roots = load_external_skill_roots_for_repo_root(repo_root=workspace_root)
            self.assertEqual(roots, ())


if __name__ == "__main__":
    unittest.main()

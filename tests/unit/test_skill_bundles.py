from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.builtin_assets import RallyBuiltinAssets
from rally.services.skill_bundles import (
    MANDATORY_SKILL_NAMES,
    OPTIONAL_BUILTIN_SKILL_NAMES,
    resolve_skill_bundle_source,
    validate_system_skill_name,
)


_MARKDOWN_FRONTMATTER = textwrap.dedent(
    """\
    ---
    name: demo-skill
    description: "A demo markdown skill."
    ---

    # demo-skill
    """
)


def _write_markdown_skill(repo_root: Path, skill_name: str, *, body: str = _MARKDOWN_FRONTMATTER) -> Path:
    skill_dir = repo_root / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    return skill_dir


def _write_doctrine_skill(repo_root: Path, skill_name: str, *, with_build: bool) -> Path:
    skill_dir = repo_root / "skills" / skill_name
    (skill_dir / "prompts").mkdir(parents=True)
    (skill_dir / "prompts" / "SKILL.prompt").write_text(
        f'skill package X: "X"\n    metadata:\n        name: "{skill_name}"\n',
        encoding="utf-8",
    )
    if with_build:
        build_dir = skill_dir / "build"
        build_dir.mkdir()
        (build_dir / "SKILL.md").write_text(_MARKDOWN_FRONTMATTER, encoding="utf-8")
    return skill_dir


class ValidateSystemSkillNameTests(unittest.TestCase):
    # Protects the gate that keeps `system_skills` in `flow.yaml` from
    # accepting unknown or already-mandatory stdlib skills. A regression
    # here would silently allow an agent to request a stdlib skill that
    # Rally cannot resolve at prepare-home time; the operator would only
    # see the downstream "Unknown Rally built-in skill" crash and have to
    # trace it back to `flow.yaml`.

    def test_mandatory_skill_is_rejected_with_clear_guidance(self) -> None:
        for mandatory in MANDATORY_SKILL_NAMES:
            with self.subTest(skill=mandatory):
                with self.assertRaisesRegex(RallyConfigError, r"mandatory Rally stdlib skill"):
                    validate_system_skill_name(mandatory)

    def test_unknown_skill_is_rejected_and_lists_the_available_optionals(self) -> None:
        with self.assertRaises(RallyConfigError) as ctx:
            validate_system_skill_name("not-a-real-skill")
        message = str(ctx.exception)
        self.assertIn("Unknown Rally stdlib skill `not-a-real-skill`", message)
        for optional in OPTIONAL_BUILTIN_SKILL_NAMES:
            self.assertIn(f"`{optional}`", message)

    def test_each_optional_builtin_skill_is_accepted(self) -> None:
        # If this loop is ever empty we want to know: silently accepting
        # nothing would hide a regression that removed every opt-in skill.
        self.assertTrue(OPTIONAL_BUILTIN_SKILL_NAMES)
        for optional in OPTIONAL_BUILTIN_SKILL_NAMES:
            with self.subTest(skill=optional):
                self.assertIsNone(validate_system_skill_name(optional))


class ResolveSkillBundleSourceTests(unittest.TestCase):
    # Protects the non-external skill resolver that `home_materializer`
    # calls for every `MANDATORY_SKILL_NAMES`, every `agent.allowed_skills`,
    # and every `agent.system_skills`. The silent-miss risk: if any branch
    # of this function returned a `SkillBundleSource` without raising on
    # bad input, an agent could launch with a reduced capability set and
    # no loud error. Every failure mode exercised below must raise
    # `RallyConfigError` with an operator-readable reason.

    def test_missing_skill_directory_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            with self.assertRaisesRegex(RallyConfigError, r"Allowed skill does not exist"):
                resolve_skill_bundle_source(repo_root=repo_root, skill_name="missing-skill")

    def test_markdown_skill_resolves_and_runtime_dir_is_skill_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            skill_dir = _write_markdown_skill(repo_root, "demo-skill")

            bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

            self.assertEqual(bundle.kind, "markdown")
            self.assertEqual(bundle.name, "demo-skill")
            self.assertIsNone(bundle.origin_alias)
            self.assertEqual(bundle.runtime_source_dir(), skill_dir)

    def test_doctrine_skill_resolves_and_runtime_dir_is_build_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            skill_dir = _write_doctrine_skill(repo_root, "demo-skill", with_build=True)

            bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

            self.assertEqual(bundle.kind, "doctrine")
            self.assertEqual(bundle.runtime_source_dir(), skill_dir / "build")

    def test_both_markdown_and_doctrine_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            skill_dir = _write_markdown_skill(repo_root, "demo-skill")
            (skill_dir / "prompts").mkdir()
            (skill_dir / "prompts" / "SKILL.prompt").write_text("x\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyConfigError, r"must define exactly one source kind"):
                resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

    def test_neither_markdown_nor_doctrine_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            (repo_root / "skills" / "demo-skill").mkdir(parents=True)

            with self.assertRaisesRegex(RallyConfigError, r"must define either"):
                resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

    def test_doctrine_skill_without_build_markdown_raises_on_runtime_source_dir(self) -> None:
        # Non-external Doctrine skills use a distinct error message from the
        # external variant — locking the workspace-owned phrasing here.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            _write_doctrine_skill(repo_root, "demo-skill", with_build=False)
            bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

            with self.assertRaisesRegex(
                RallyConfigError,
                r"Doctrine skill `demo-skill` is missing emitted `build/SKILL\.md`",
            ):
                bundle.runtime_source_dir()

    def test_markdown_with_missing_frontmatter_raises_on_runtime_source_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            _write_markdown_skill(repo_root, "demo-skill", body="# just a heading\n\nno frontmatter\n")
            bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

            with self.assertRaisesRegex(RallyConfigError, r"must start with YAML frontmatter"):
                bundle.runtime_source_dir()

    def test_markdown_with_missing_closing_frontmatter_raises_on_runtime_source_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            _write_markdown_skill(
                repo_root,
                "demo-skill",
                body="---\nname: demo-skill\ndescription: open frontmatter never closed\n",
            )
            bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

            with self.assertRaisesRegex(RallyConfigError, r"missing the closing YAML frontmatter marker"):
                bundle.runtime_source_dir()

    def test_too_short_markdown_raises_on_runtime_source_dir(self) -> None:
        # Two-line file trips the "< 3 lines" guard before the scan for the
        # closing `---`, which is a distinct branch worth pinning.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            _write_markdown_skill(repo_root, "demo-skill", body="---\nname: demo-skill\n")
            bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name="demo-skill")

            with self.assertRaisesRegex(RallyConfigError, r"must start with YAML frontmatter"):
                bundle.runtime_source_dir()


class ResolveBuiltinSkillTests(unittest.TestCase):
    # Protects the mandatory-skill path. `rally-kernel` is in
    # `MANDATORY_SKILL_NAMES` and must always resolve at prepare-home time
    # — otherwise every agent launches without Rally's base skill. The
    # silent-miss risk here is a regression in `_resolve_builtin_skill_source`
    # returning a path that doesn't exist on disk; the tests below lock in
    # both the source-checkout branch (SKILL.prompt in the repo) and the
    # installed-distribution branch (runtime_dir from the injected assets).

    def _make_builtin_assets(
        self,
        *,
        workspace_root: Path,
        runtime_root: Path,
    ) -> RallyBuiltinAssets:
        stdlib_root = workspace_root / "stdlib"
        stdlib_prompts_root = stdlib_root / "rally" / "prompts"
        skill_runtime_dirs: dict[str, Path] = {}
        for name in MANDATORY_SKILL_NAMES:
            dir_ = runtime_root / name
            dir_.mkdir(parents=True, exist_ok=True)
            (dir_ / "SKILL.md").write_text(_MARKDOWN_FRONTMATTER, encoding="utf-8")
            skill_runtime_dirs[name] = dir_
        return RallyBuiltinAssets(
            stdlib_root=stdlib_root,
            stdlib_prompts_root=stdlib_prompts_root,
            skill_runtime_dirs=skill_runtime_dirs,
            source_kind="installed_distribution",
            source_root=None,
        )

    def test_mandatory_skill_resolves_via_injected_builtin_assets(self) -> None:
        for mandatory in MANDATORY_SKILL_NAMES:
            with self.subTest(skill=mandatory):
                with tempfile.TemporaryDirectory() as temp_dir:
                    workspace_root = Path(temp_dir).resolve() / "workspace"
                    workspace_root.mkdir()
                    runtime_root = Path(temp_dir).resolve() / "runtime"
                    runtime_root.mkdir()
                    assets = self._make_builtin_assets(
                        workspace_root=workspace_root,
                        runtime_root=runtime_root,
                    )

                    bundle = resolve_skill_bundle_source(
                        repo_root=workspace_root,
                        skill_name=mandatory,
                        builtins=assets,
                    )

                    self.assertEqual(bundle.kind, "builtin")
                    self.assertEqual(bundle.name, mandatory)
                    self.assertEqual(bundle.runtime_source_dir(), runtime_root / mandatory)

    def test_mandatory_skill_from_source_checkout_uses_doctrine_entrypoint(self) -> None:
        for mandatory in MANDATORY_SKILL_NAMES:
            with self.subTest(skill=mandatory):
                with tempfile.TemporaryDirectory() as temp_dir:
                    workspace_root = Path(temp_dir).resolve() / "workspace"
                    workspace_root.mkdir()
                    runtime_root = Path(temp_dir).resolve() / "runtime"
                    runtime_root.mkdir()
                    _write_doctrine_skill(workspace_root, mandatory, with_build=True)
                    # Set source_root to workspace_root to trigger the
                    # "running from the Rally source checkout" branch — the
                    # resolver should then prefer the in-tree SKILL.prompt
                    # over the packaged runtime directory.
                    assets = self._make_builtin_assets(
                        workspace_root=workspace_root,
                        runtime_root=runtime_root,
                    )
                    checkout_assets = RallyBuiltinAssets(
                        stdlib_root=assets.stdlib_root,
                        stdlib_prompts_root=assets.stdlib_prompts_root,
                        skill_runtime_dirs=assets.skill_runtime_dirs,
                        source_kind="source_checkout",
                        source_root=workspace_root,
                    )

                    bundle = resolve_skill_bundle_source(
                        repo_root=workspace_root,
                        skill_name=mandatory,
                        builtins=checkout_assets,
                    )

                    self.assertEqual(bundle.kind, "doctrine")
                    self.assertEqual(
                        bundle.runtime_source_dir(),
                        workspace_root / "skills" / mandatory / "build",
                    )


if __name__ == "__main__":
    unittest.main()

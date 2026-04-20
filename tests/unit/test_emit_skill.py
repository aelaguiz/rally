from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from doctrine.emit_common import load_emit_targets
from doctrine.emit_skill import emit_target_skill


class EmitRallyLearnSkillTests(unittest.TestCase):
    ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.repo_root = Path(__file__).resolve().parents[2]

    def test_rally_learn_public_emit_produces_complete_tree(self) -> None:
        # This protects the public install surface users consume via
        # `npx skills add .`. The emitted tree must carry the SKILL root,
        # the runtime metadata, and every reference the skill map declares.
        target = load_emit_targets(self.repo_root / "pyproject.toml")[
            "rally_learn_public_skill"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir).resolve()
            emitted = emit_target_skill(target, output_dir_override=output_dir)

            expected_paths = (
                output_dir / "SKILL.md",
                output_dir / "agents" / "openai.yaml",
                output_dir / "references" / "authoring-patterns.md",
                output_dir / "references" / "build-and-emit.md",
                output_dir / "references" / "flow-authoring.md",
                output_dir / "references" / "getting-started.md",
                output_dir / "references" / "memory.md",
                output_dir / "references" / "porting-anti-patterns.md",
                output_dir / "references" / "previous-turn-inputs.md",
                output_dir / "references" / "principles.md",
                output_dir / "references" / "release-and-versioning.md",
                output_dir / "references" / "runtime-operations.md",
                output_dir / "references" / "skills-and-scoping.md",
                output_dir / "references" / "turn-results-and-routing.md",
                output_dir / "references" / "verify-and-ship.md",
            )

            self.assertCountEqual(emitted, expected_paths)
            for expected_path in expected_paths:
                self.assertTrue(expected_path.is_file(), expected_path)

            skill_markdown = (output_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("# Rally Learn", skill_markdown)
            self.assertIn("Teach Rally authoring end-to-end.", skill_markdown)
            self.assertFalse((output_dir / "scripts").exists())
            self.assertFalse((output_dir / "schemas").exists())

    def test_rally_learn_internal_emit_produces_complete_tree(self) -> None:
        # The internal (`skills/rally-learn/build/`) emit target must match
        # the public tree shape so authors editing the source see the same
        # bundle a user would install.
        target = load_emit_targets(self.repo_root / "pyproject.toml")[
            "rally_learn_skill"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir).resolve()
            emitted = emit_target_skill(target, output_dir_override=output_dir)

            reference_names = (
                "authoring-patterns.md",
                "build-and-emit.md",
                "flow-authoring.md",
                "getting-started.md",
                "memory.md",
                "porting-anti-patterns.md",
                "previous-turn-inputs.md",
                "principles.md",
                "release-and-versioning.md",
                "runtime-operations.md",
                "skills-and-scoping.md",
                "turn-results-and-routing.md",
                "verify-and-ship.md",
            )

            expected_paths = (
                output_dir / "SKILL.md",
                output_dir / "agents" / "openai.yaml",
                *(output_dir / "references" / name for name in reference_names),
            )
            self.assertCountEqual(emitted, expected_paths)

    def test_pinned_skills_cli_lists_rally_learn(self) -> None:
        # This protects the repo-root discovery story behind
        # `npx skills add .`. Users should see `rally-learn` as a first-party
        # installable skill.
        skills_cli = self._skills_cli(self.repo_root)
        result = subprocess.run(
            [str(skills_cli), "add", ".", "--list"],
            cwd=self.repo_root,
            env=self._skills_env(),
            capture_output=True,
            text=True,
            check=False,
        )

        output = self._strip_ansi(result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("rally-learn", output)

    def test_pinned_skills_cli_installs_rally_learn_into_temp_codex_home(self) -> None:
        # This proves the local repo can act as a real `skills` source and
        # install the public skill for Codex through the same flow users run
        # with `npx skills add . -g -a codex -y`.
        skills_cli = self._skills_cli(self.repo_root)

        # Ensure the curated tree exists before `skills add` tries to read it,
        # since the curated directory is gitignored.
        subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "doctrine.emit_skill",
                "--pyproject",
                str(self.repo_root / "pyproject.toml"),
                "--target",
                "rally_learn_public_skill",
            ],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir).resolve()
            env = self._skills_env()
            env["HOME"] = str(home_dir)
            result = subprocess.run(
                [str(skills_cli), "add", ".", "-g", "-a", "codex", "-y"],
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            output = self._strip_ansi(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, output)
            installed_root = home_dir / ".agents" / "skills" / "rally-learn"
            self.assertTrue((installed_root / "SKILL.md").is_file(), output)
            self.assertTrue(
                (installed_root / "agents" / "openai.yaml").is_file(), output
            )
            self.assertTrue(
                (installed_root / "references" / "principles.md").is_file(),
                output,
            )

    def _skills_cli(self, repo_root: Path) -> Path:
        cli_name = "skills.cmd" if os.name == "nt" else "skills"
        cli_path = repo_root / "node_modules" / ".bin" / cli_name
        if not cli_path.exists():
            self.skipTest("Run `npm ci` first to install the pinned `skills` CLI.")
        return cli_path

    def _skills_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CI"] = "1"
        env["NO_COLOR"] = "1"
        env["FORCE_COLOR"] = "0"
        env["TERM"] = "dumb"
        return env

    def _strip_ansi(self, text: str) -> str:
        return self.ANSI_RE.sub("", text)


if __name__ == "__main__":
    unittest.main()

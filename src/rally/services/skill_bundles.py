from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rally.errors import RallyConfigError

MANDATORY_SKILL_NAMES = ("rally-kernel", "rally-memory")

SkillSourceKind = Literal["markdown", "doctrine"]


@dataclass(frozen=True)
class SkillBundleSource:
    name: str
    kind: SkillSourceKind
    root_dir: Path
    markdown_file: Path | None
    doctrine_entrypoint: Path | None

    def runtime_source_dir(self) -> Path:
        if self.kind == "markdown":
            assert self.markdown_file is not None
            _validate_skill_markdown(skill_file=self.markdown_file, skill_name=self.name)
            return self.root_dir

        build_dir = self.root_dir / "build"
        skill_file = build_dir / "SKILL.md"
        if not skill_file.is_file():
            raise RallyConfigError(
                f"Doctrine skill `{self.name}` is missing emitted `build/SKILL.md`: `{skill_file}`."
            )
        _validate_skill_markdown(skill_file=skill_file, skill_name=self.name)
        return build_dir


def resolve_skill_bundle_source(
    *,
    repo_root: Path,
    skill_name: str,
) -> SkillBundleSource:
    root_dir = repo_root / "skills" / skill_name
    if not root_dir.is_dir():
        raise RallyConfigError(f"Allowed skill does not exist: `{root_dir}`.")

    markdown_file = root_dir / "SKILL.md"
    doctrine_entrypoint = root_dir / "prompts" / "SKILL.prompt"
    has_markdown = markdown_file.is_file()
    has_doctrine = doctrine_entrypoint.is_file()
    if has_markdown and has_doctrine:
        raise RallyConfigError(
            f"Skill `{skill_name}` must define exactly one source kind. "
            f"Found both `{markdown_file}` and `{doctrine_entrypoint}`."
        )
    if not has_markdown and not has_doctrine:
        raise RallyConfigError(
            f"Skill `{skill_name}` must define either `{markdown_file}` or `{doctrine_entrypoint}`."
        )

    if has_markdown:
        return SkillBundleSource(
            name=skill_name,
            kind="markdown",
            root_dir=root_dir,
            markdown_file=markdown_file,
            doctrine_entrypoint=None,
        )
    return SkillBundleSource(
        name=skill_name,
        kind="doctrine",
        root_dir=root_dir,
        markdown_file=None,
        doctrine_entrypoint=doctrine_entrypoint,
    )


def _validate_skill_markdown(*, skill_file: Path, skill_name: str) -> None:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise RallyConfigError(
            f"Skill `{skill_name}` must start with YAML frontmatter so Codex can load it."
        )
    if not any(line.strip() == "---" for line in lines[1:]):
        raise RallyConfigError(
            f"Skill `{skill_name}` is missing the closing YAML frontmatter marker."
        )

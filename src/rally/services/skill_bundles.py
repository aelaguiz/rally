from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rally.errors import RallyConfigError
from rally.services.builtin_assets import (
    RALLY_BUILTIN_SKILL_NAMES,
    RallyBuiltinAssets,
    reject_reserved_builtin_skill_shadow,
    resolve_rally_builtin_assets,
)

MANDATORY_SKILL_NAMES = ("rally-kernel",)
# Optional stdlib skills an agent can opt into through `system_skills` in
# flow.yaml. Rally-kernel is always-on, so it stays out of this tuple.
OPTIONAL_BUILTIN_SKILL_NAMES = tuple(
    name for name in RALLY_BUILTIN_SKILL_NAMES if name not in MANDATORY_SKILL_NAMES
)


def validate_system_skill_name(skill_name: str) -> None:
    if skill_name in MANDATORY_SKILL_NAMES:
        raise RallyConfigError(
            f"`{skill_name}` is a mandatory Rally stdlib skill and is injected automatically; "
            "remove it from `system_skills`."
        )
    if skill_name not in OPTIONAL_BUILTIN_SKILL_NAMES:
        available = ", ".join(f"`{name}`" for name in OPTIONAL_BUILTIN_SKILL_NAMES) or "(none)"
        raise RallyConfigError(
            f"Unknown Rally stdlib skill `{skill_name}` in `system_skills`. "
            f"Available stdlib skills: {available}."
        )

SkillSourceKind = Literal["markdown", "doctrine", "builtin"]

_EXTERNAL_SKILL_QUALIFIED_RE = re.compile(
    r"^(?P<alias>[a-z][a-z0-9_-]*):(?P<skill>[A-Za-z0-9][A-Za-z0-9_-]*)$"
)


@dataclass(frozen=True)
class SkillBundleSource:
    name: str
    kind: SkillSourceKind
    root_dir: Path
    markdown_file: Path | None
    doctrine_entrypoint: Path | None
    origin_alias: str | None = None

    def runtime_source_dir(self) -> Path:
        label = _external_label(name=self.name, origin_alias=self.origin_alias)
        if self.kind in {"markdown", "builtin"}:
            assert self.markdown_file is not None
            _validate_skill_markdown(skill_file=self.markdown_file, skill_name=label)
            return self.root_dir

        build_dir = self.root_dir / "build"
        skill_file = build_dir / "SKILL.md"
        if not skill_file.is_file():
            if self.origin_alias is not None:
                raise RallyConfigError(
                    f"External Doctrine skill `{label}` is missing `build/SKILL.md` at `{skill_file}`. "
                    "Build it inside its own workspace before referencing it from here."
                )
            raise RallyConfigError(
                f"Doctrine skill `{label}` is missing emitted `build/SKILL.md`: `{skill_file}`."
            )
        _validate_skill_markdown(skill_file=skill_file, skill_name=label)
        return build_dir


def _external_label(*, name: str, origin_alias: str | None) -> str:
    if origin_alias is None:
        return name
    return f"{origin_alias}:{name}"


def split_external_skill_name(qualified_name: str) -> tuple[str, str]:
    """Parse `<alias>:<skill>` into (alias, skill). Raise a clear error on malformed input."""
    match = _EXTERNAL_SKILL_QUALIFIED_RE.fullmatch(qualified_name)
    if match is None:
        raise RallyConfigError(
            f"External skill name `{qualified_name}` must be of the form `<alias>:<skill-name>` "
            "(e.g. `psmobile:device-farm`)."
        )
    return match.group("alias"), match.group("skill")


def resolve_skill_bundle_source(
    *,
    repo_root: Path,
    skill_name: str,
    builtins: RallyBuiltinAssets | None = None,
) -> SkillBundleSource:
    if skill_name in RALLY_BUILTIN_SKILL_NAMES:
        return _resolve_builtin_skill_source(
            repo_root=repo_root,
            skill_name=skill_name,
            builtins=builtins,
        )

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


def resolve_external_skill_bundle_source(
    *,
    root: Path,
    alias: str,
    skill_name: str,
) -> SkillBundleSource:
    """Resolve a skill bundle under a registered external workspace skill root.

    `root` is the directory registered under
    `[tool.rally.workspace.external_skill_roots]`; `skill_name` is the
    unqualified skill directory name.
    """
    label = f"{alias}:{skill_name}"
    root_dir = root / skill_name
    if not root_dir.is_dir():
        raise RallyConfigError(
            f"External skill `{label}` does not exist at `{root_dir}`."
        )

    markdown_file = root_dir / "SKILL.md"
    doctrine_entrypoint = root_dir / "prompts" / "SKILL.prompt"
    has_markdown = markdown_file.is_file()
    has_doctrine = doctrine_entrypoint.is_file()
    if has_markdown and has_doctrine:
        raise RallyConfigError(
            f"External skill `{label}` must define exactly one source kind. "
            f"Found both `{markdown_file}` and `{doctrine_entrypoint}`."
        )
    if not has_markdown and not has_doctrine:
        raise RallyConfigError(
            f"External skill `{label}` must define either `{markdown_file}` or `{doctrine_entrypoint}`."
        )

    if has_markdown:
        return SkillBundleSource(
            name=skill_name,
            kind="markdown",
            root_dir=root_dir,
            markdown_file=markdown_file,
            doctrine_entrypoint=None,
            origin_alias=alias,
        )
    return SkillBundleSource(
        name=skill_name,
        kind="doctrine",
        root_dir=root_dir,
        markdown_file=None,
        doctrine_entrypoint=doctrine_entrypoint,
        origin_alias=alias,
    )


def _resolve_builtin_skill_source(
    *,
    repo_root: Path,
    skill_name: str,
    builtins: RallyBuiltinAssets | None,
) -> SkillBundleSource:
    assets = builtins or resolve_rally_builtin_assets(workspace_root=repo_root)
    repo_root = repo_root.resolve()
    if assets.source_root is not None and repo_root == assets.source_root.resolve():
        root_dir = repo_root / "skills" / skill_name
        doctrine_entrypoint = root_dir / "prompts" / "SKILL.prompt"
        if doctrine_entrypoint.is_file():
            return SkillBundleSource(
                name=skill_name,
                kind="doctrine",
                root_dir=root_dir,
                markdown_file=None,
                doctrine_entrypoint=doctrine_entrypoint,
            )

    reject_reserved_builtin_skill_shadow(
        workspace_root=repo_root,
        skill_names=(skill_name,),
        builtins=assets,
    )
    runtime_dir = assets.skill_runtime_dir(skill_name)
    return SkillBundleSource(
        name=skill_name,
        kind="builtin",
        root_dir=runtime_dir,
        markdown_file=runtime_dir / "SKILL.md",
        doctrine_entrypoint=None,
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

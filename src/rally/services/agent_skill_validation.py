from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from rally.domain.flow import flow_agent_key_to_slug
from rally.errors import RallyConfigError
from rally.services.skill_bundles import MANDATORY_SKILL_NAMES

_SKILLS_SECTION_PREFIX = "## Skills"
_SKILL_HEADING_PREFIX = "### "


def expected_agent_skill_names(
    *,
    allowed_skills: Iterable[str],
    system_skills: Iterable[str] = (),
) -> tuple[str, ...]:
    ordered_names: list[str] = []
    seen_names: set[str] = set()
    for skill_name in (*MANDATORY_SKILL_NAMES, *allowed_skills, *system_skills):
        if skill_name in seen_names:
            continue
        seen_names.add(skill_name)
        ordered_names.append(skill_name)
    return tuple(ordered_names)


def validate_flow_agent_skill_surfaces(
    *,
    flow_file: Path,
    build_agents_dir: Path,
    allowed_skills_by_agent_key: Mapping[str, tuple[str, ...]],
    system_skills_by_agent_key: Mapping[str, tuple[str, ...]],
) -> None:
    for agent_key, allowed_skills in allowed_skills_by_agent_key.items():
        agent_slug = flow_agent_key_to_slug(agent_key)
        markdown_path = build_agents_dir / agent_slug / "AGENTS.md"
        if not markdown_path.is_file():
            raise RallyConfigError(
                f"Compiled agent home is missing for `{agent_key}`. Expected `{markdown_path}`."
            )
        system_skills = system_skills_by_agent_key.get(agent_key, ())
        _validate_agent_skill_surface(
            agent_key=agent_key,
            flow_file=flow_file,
            allowed_skills=allowed_skills,
            system_skills=system_skills,
            markdown_path=markdown_path,
        )


def _validate_agent_skill_surface(
    *,
    agent_key: str,
    flow_file: Path,
    allowed_skills: tuple[str, ...],
    system_skills: tuple[str, ...],
    markdown_path: Path,
) -> None:
    expected = expected_agent_skill_names(
        allowed_skills=allowed_skills,
        system_skills=system_skills,
    )
    emitted = _extract_agent_skill_names(markdown_path.read_text(encoding="utf-8"))
    if emitted == expected:
        return
    if len(emitted) == len(set(emitted)) and set(emitted) == set(expected):
        return
    raise RallyConfigError(
        f"Compiled skill readback for agent `{agent_key}` in `{markdown_path}` does not match "
        f"`allowed_skills` + `system_skills` in `{flow_file}`. "
        f"Expected {_render_skill_list(expected)}; found {_render_skill_list(emitted)}. "
        "Bind the live skill surface on the concrete agent so emitted `AGENTS.md` stays "
        "aligned with the runtime allowlist."
    )


def _extract_agent_skill_names(markdown_text: str) -> tuple[str, ...]:
    skill_names: list[str] = []
    in_skills_section = False
    for raw_line in markdown_text.splitlines():
        if raw_line.startswith("## "):
            in_skills_section = raw_line.strip().startswith(_SKILLS_SECTION_PREFIX)
            continue
        if not in_skills_section:
            continue
        if raw_line.startswith(_SKILL_HEADING_PREFIX):
            skill_names.append(raw_line[len(_SKILL_HEADING_PREFIX) :].strip())
    return tuple(skill_names)


def _render_skill_list(skill_names: tuple[str, ...]) -> str:
    if not skill_names:
        return "no skills"
    return ", ".join(f"`{skill_name}`" for skill_name in skill_names)

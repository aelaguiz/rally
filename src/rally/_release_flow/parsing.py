from __future__ import annotations

from pathlib import Path
import re
import tomllib

from rally._package_release import load_package_release_metadata
from rally._release_flow.common import release_error, run_checked
from rally._release_flow.models import (
    CHANGELOG_SECTION_RE,
    COMPILED_CONTRACT_VERSION_RE,
    CURRENT_DOCTRINE_FLOOR_RE,
    CURRENT_DOCTRINE_PACKAGE_LINE_RE,
    CURRENT_PUBLIC_RELEASE_VERSION_RE,
    HEADER_FIELD_ORDER,
    ChangelogSection,
    ReleaseEntry,
    ReleaseTag,
    RELEASE_TAG_RE,
)

PLACEHOLDER_SUBSTRINGS = (
    "fill this in",
    "update for this release",
    "tbd",
    "todo",
    "placeholder",
)
PLACEHOLDER_VALUES = {"...", "n/a", "na", "pending"}


def repo_root() -> Path:
    completed = run_checked(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        code="E527",
        summary="Release tag preflight failed",
        detail="Could not resolve the repo root from git.",
    )
    return Path(completed.stdout.strip()).resolve()


def load_current_public_release_version(repo_root: Path) -> str:
    versioning_path = repo_root / "docs" / "VERSIONING.md"
    text = _read_text(
        versioning_path,
        code="E523",
        summary="Missing current public release version",
        detail="`docs/VERSIONING.md` is required so Rally can read the current public release line.",
    )
    match = CURRENT_PUBLIC_RELEASE_VERSION_RE.search(text)
    if match is None:
        raise release_error(
            "E523",
            "Missing current public release version",
            "`docs/VERSIONING.md` must contain one `Current public Rally release version:` line.",
            location=versioning_path,
        )
    value = _strip_optional_backticks(match.group("version"))
    if value != "none yet" and RELEASE_TAG_RE.match(value) is None:
        raise release_error(
            "E523",
            "Missing current public release version",
            "`Current public Rally release version:` must be `none yet` or a public tag such as `v0.1.0`.",
            location=versioning_path,
        )
    return value


def load_doctrine_floor(repo_root: Path) -> str:
    versioning_path = repo_root / "docs" / "VERSIONING.md"
    text = _read_text(
        versioning_path,
        code="E531",
        summary="Missing Doctrine floor",
        detail="`docs/VERSIONING.md` is required so Rally can read the current Doctrine floor.",
    )
    match = CURRENT_DOCTRINE_FLOOR_RE.search(text)
    if match is None:
        raise release_error(
            "E531",
            "Missing Doctrine floor",
            "`docs/VERSIONING.md` must contain one `Current minimum Doctrine release:` line.",
            location=versioning_path,
        )
    value = _strip_optional_backticks(match.group("version"))
    if RELEASE_TAG_RE.match(value) is None:
        raise release_error(
            "E531",
            "Missing Doctrine floor",
            "`Current minimum Doctrine release:` must be a public tag such as `v1.0.1`.",
            location=versioning_path,
        )
    return value


def load_doctrine_package_line(repo_root: Path) -> str:
    versioning_path = repo_root / "docs" / "VERSIONING.md"
    text = _read_text(
        versioning_path,
        code="E531",
        summary="Missing Doctrine package line",
        detail="`docs/VERSIONING.md` is required so Rally can read the supported Doctrine package line.",
    )
    match = CURRENT_DOCTRINE_PACKAGE_LINE_RE.search(text)
    if match is None:
        raise release_error(
            "E531",
            "Missing Doctrine package line",
            "`docs/VERSIONING.md` must contain one `Current supported Doctrine package line:` line.",
            location=versioning_path,
        )
    return _strip_optional_backticks(match.group("value"))


def load_package_metadata_version(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    try:
        return load_package_release_metadata(repo_root).version
    except RuntimeError as exc:
        raise release_error(
            "E530",
            "Release package metadata version is missing or does not match",
            str(exc),
            location=pyproject_path,
        ) from exc


def load_workspace_version(repo_root: Path) -> int:
    pyproject_path = repo_root / "pyproject.toml"
    raw = _load_pyproject(pyproject_path)
    tool_table = raw.get("tool")
    if not isinstance(tool_table, dict):
        raise release_error(
            "E531",
            "Missing workspace manifest version",
            "`pyproject.toml` must contain `[tool.rally.workspace].version`.",
            location=pyproject_path,
        )
    rally_table = tool_table.get("rally")
    if not isinstance(rally_table, dict):
        raise release_error(
            "E531",
            "Missing workspace manifest version",
            "`pyproject.toml` must contain `[tool.rally.workspace].version`.",
            location=pyproject_path,
        )
    workspace_table = rally_table.get("workspace")
    if not isinstance(workspace_table, dict):
        raise release_error(
            "E531",
            "Missing workspace manifest version",
            "`pyproject.toml` must contain `[tool.rally.workspace].version`.",
            location=pyproject_path,
        )
    version = workspace_table.get("version")
    if not isinstance(version, int):
        raise release_error(
            "E531",
            "Missing workspace manifest version",
            "`[tool.rally.workspace].version` must be an integer.",
            location=pyproject_path,
        )
    return version


def load_compiled_contract_version(repo_root: Path) -> int:
    flow_loader_path = repo_root / "src" / "rally" / "services" / "flow_loader.py"
    text = _read_text(
        flow_loader_path,
        code="E531",
        summary="Missing compiled contract version",
        detail="`src/rally/services/flow_loader.py` is required so Rally can read the compiled contract version.",
    )
    match = COMPILED_CONTRACT_VERSION_RE.search(text)
    if match is None:
        raise release_error(
            "E531",
            "Missing compiled contract version",
            "`src/rally/services/flow_loader.py` must define `SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS = frozenset({...})`.",
            location=flow_loader_path,
        )
    versions = [int(part.strip()) for part in match.group("versions").split(",") if part.strip()]
    if not versions:
        raise release_error(
            "E531",
            "Missing compiled contract version",
            "Rally could not parse any compiled contract version from `SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS`.",
            location=flow_loader_path,
        )
    return max(versions)


def expected_package_metadata_version(release_tag: ReleaseTag) -> str:
    base = f"{release_tag.major}.{release_tag.minor}.{release_tag.patch}"
    if release_tag.channel == "stable":
        return base
    if release_tag.channel == "beta":
        assert release_tag.prerelease_number is not None
        return f"{base}b{release_tag.prerelease_number}"
    assert release_tag.prerelease_number is not None
    return f"{base}rc{release_tag.prerelease_number}"


def describe_package_metadata_status(
    *,
    current_version: str,
    requested_tag: ReleaseTag,
) -> str:
    expected_version = expected_package_metadata_version(requested_tag)
    if current_version == expected_version:
        return f"ready (`{expected_version}`)"
    return f"needs `[project].version = \"{expected_version}\"` in `pyproject.toml`"


def require_matching_package_metadata_version(
    *,
    repo_root: Path,
    release_tag: ReleaseTag,
) -> str:
    current_version = load_package_metadata_version(repo_root)
    expected_version = expected_package_metadata_version(release_tag)
    if current_version != expected_version:
        raise release_error(
            "E530",
            "Release package metadata version is missing or does not match",
            f"`pyproject.toml` package version `{current_version}` does not match requested release `{release_tag.raw}`. "
            f"Set `[project].version = \"{expected_version}\"` before tagging or drafting this release.",
            location=repo_root / "pyproject.toml",
        )
    return current_version


def load_changelog_sections(repo_root: Path) -> tuple[ChangelogSection, ...]:
    changelog_path = repo_root / "CHANGELOG.md"
    text = _read_text(
        changelog_path,
        code="E526",
        summary="Release changelog entry is missing or incomplete",
        detail="`CHANGELOG.md` is required for the release flow.",
    )
    matches = list(CHANGELOG_SECTION_RE.finditer(text))
    sections: list[ChangelogSection] = []
    for index, match in enumerate(matches):
        title = match.group("title").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append(
            ChangelogSection(
                title=title,
                key=normalize_changelog_key(title),
                body=body,
            )
        )
    return tuple(sections)


def normalize_changelog_key(title: str) -> str:
    return title.split(" - ", 1)[0].strip()


def find_release_section(
    sections: tuple[ChangelogSection, ...],
    release: str,
) -> ChangelogSection | None:
    for section in sections:
        if section.key == release:
            return section
    return None


def require_release_entry(repo_root: Path, release_tag: ReleaseTag) -> ReleaseEntry:
    section = find_release_section(load_changelog_sections(repo_root), release_tag.raw)
    if section is None:
        raise release_error(
            "E526",
            "Release changelog entry is missing or incomplete",
            f"`CHANGELOG.md` must contain one `## {release_tag.raw} - YYYY-MM-DD` section before `{release_tag.raw}` can be tagged or drafted.",
            location=repo_root / "CHANGELOG.md",
        )
    metadata, body = parse_release_entry_metadata(section, repo_root / "CHANGELOG.md")
    expected_channel = release_tag.channel_display
    if metadata["Release version"] != release_tag.raw or metadata["Release channel"] != expected_channel:
        raise release_error(
            "E526",
            "Release changelog entry is missing or incomplete",
            f"`CHANGELOG.md` release entry `{section.title}` does not match `{release_tag.raw}` and `{expected_channel}`.",
            location=repo_root / "CHANGELOG.md",
        )
    return ReleaseEntry(section=section, metadata=metadata, body=body)


def require_validated_release_entry(
    *,
    repo_root: Path,
    release_tag: ReleaseTag,
    expected_release_kind: str | None,
) -> ReleaseEntry:
    entry = require_release_entry(repo_root, release_tag)
    error = validate_release_entry_truth(
        entry=entry,
        release_tag=release_tag,
        expected_release_kind=expected_release_kind,
    )
    if error is not None:
        raise release_error(
            "E526",
            "Release changelog entry is missing or incomplete",
            error,
            location=repo_root / "CHANGELOG.md",
        )
    return entry


def parse_release_entry_metadata(
    section: ChangelogSection,
    changelog_path: Path,
) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    lines = section.body.splitlines()
    body_start = 0
    started = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if started:
                body_start = index + 1
                break
            continue
        if ":" not in stripped:
            body_start = index
            break
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key not in HEADER_FIELD_ORDER:
            body_start = index
            break
        metadata[key] = value.strip()
        started = True
    else:
        body_start = len(lines)

    missing = [field for field in HEADER_FIELD_ORDER if field not in metadata]
    if missing:
        raise release_error(
            "E526",
            "Release changelog entry is missing or incomplete",
            f"`CHANGELOG.md` release entry `{section.title}` is missing: {', '.join(missing)}.",
            location=changelog_path,
        )
    return metadata, "\n".join(lines[body_start:]).strip()


def describe_changelog_status(
    *,
    release_section: ChangelogSection | None,
    requested_tag: ReleaseTag,
    release_kind: str,
) -> str:
    if release_section is None:
        return f"missing `## {requested_tag.raw} - YYYY-MM-DD`"

    metadata, body = parse_release_entry_metadata(
        release_section,
        Path("CHANGELOG.md"),
    )
    expected_channel = requested_tag.channel_display
    if metadata["Release channel"] != expected_channel:
        return f"needs `Release channel: {expected_channel}` in `{release_section.title}`"
    if metadata["Release version"] != requested_tag.raw:
        return f"needs `Release version: {requested_tag.raw}` in `{release_section.title}`"
    entry = ReleaseEntry(section=release_section, metadata=metadata, body=body)
    error = validate_release_entry_truth(
        entry=entry,
        release_tag=requested_tag,
        expected_release_kind=release_kind,
    )
    if error is not None:
        return error
    return f"ready (`{release_section.title}`)"


def validate_release_entry_truth(
    *,
    entry: ReleaseEntry,
    release_tag: ReleaseTag,
    expected_release_kind: str | None,
) -> str | None:
    metadata = entry.metadata
    if expected_release_kind is not None and metadata["Release kind"] != expected_release_kind:
        return f"needs `Release kind: {expected_release_kind}`"
    if metadata["Release channel"] != release_tag.channel_display:
        return f"needs `Release channel: {release_tag.channel_display}`"
    if metadata["Release version"] != release_tag.raw:
        return f"needs `Release version: {release_tag.raw}`"

    for field in HEADER_FIELD_ORDER[3:]:
        if _contains_placeholder(metadata[field]):
            return f"`{entry.section.title}` still has placeholder text in `{field}`."

    if metadata["Release kind"] == "Breaking":
        upgrade_steps = metadata["Upgrade steps"].strip().lower()
        if upgrade_steps.startswith("no ") or upgrade_steps in {"none", "not needed"}:
            return "breaking releases must include real upgrade steps"

    if not entry.body.strip():
        return f"`{entry.section.title}` must include real change notes below the release header."
    if _contains_placeholder(entry.body):
        return f"`{entry.section.title}` still has placeholder text in the release notes body."
    return None


def _load_pyproject(pyproject_path: Path) -> dict[str, object]:
    text = _read_text(
        pyproject_path,
        code="E530",
        summary="Release package metadata version is missing or does not match",
        detail="`pyproject.toml` is missing, so Rally cannot read its release metadata.",
    )
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise release_error(
            "E530",
            "Release package metadata version is missing or does not match",
            "Rally could not parse `pyproject.toml` while reading release metadata.",
            location=pyproject_path,
        ) from exc
    if not isinstance(raw, dict):
        raise release_error(
            "E530",
            "Release package metadata version is missing or does not match",
            "`pyproject.toml` must parse to a TOML table.",
            location=pyproject_path,
        )
    return raw


def _read_text(path: Path, *, code: str, summary: str, detail: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise release_error(code, summary, detail, location=path) from exc


def _strip_optional_backticks(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1].strip()
    return stripped


def _contains_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in PLACEHOLDER_VALUES:
        return True
    return any(candidate in lowered for candidate in PLACEHOLDER_SUBSTRINGS)

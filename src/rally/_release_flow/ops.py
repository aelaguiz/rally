from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import time

from rally._release_flow.common import release_error, run_checked
from rally._release_flow.models import HEADER_FIELD_ORDER, ReleaseEntry, ReleasePlan, ReleaseTag
from rally._release_flow.parsing import (
    describe_changelog_status,
    describe_package_metadata_status,
    expected_package_metadata_version,
    find_release_section,
    load_changelog_sections,
    load_compiled_contract_version,
    load_current_public_release_version,
    load_doctrine_floor,
    load_doctrine_package_line,
    load_package_metadata_version,
    load_workspace_version,
    require_matching_package_metadata_version,
    require_validated_release_entry,
)
from rally._release_flow.tags import (
    expected_release_kind_for_tag,
    latest_tag_for_channel,
    load_release_tags,
    parse_release_tag,
    require_clean_worktree,
    require_pushed_public_release_tag,
    require_signing_key,
    resolve_previous_tag,
    validate_release_move,
)


def prepare_release(
    *,
    repo_root: Path,
    release: str,
    release_class: str,
    channel: str,
) -> ReleasePlan:
    requested_tag = parse_release_tag(release, channel=channel)
    current_public_release = load_current_public_release_version(repo_root)
    current_package_version = load_package_metadata_version(repo_root)
    requested_package_version = expected_package_metadata_version(requested_tag)
    current_workspace_version = load_workspace_version(repo_root)
    current_compiled_contract_version = load_compiled_contract_version(repo_root)
    current_doctrine_floor = load_doctrine_floor(repo_root)
    current_doctrine_package_line = load_doctrine_package_line(repo_root)
    tags = load_release_tags(repo_root)
    previous_stable_tag = latest_tag_for_channel(
        tags,
        repo_root=repo_root,
        channel="stable",
        before=requested_tag,
    )
    previous_same_channel_tag = latest_tag_for_channel(
        tags,
        repo_root=repo_root,
        channel=channel,
        before=requested_tag,
    )
    release_kind = "Breaking" if release_class == "breaking" else "Non-breaking"

    validate_release_move(
        requested=requested_tag,
        previous_stable=previous_stable_tag,
        release_class=release_class,
    )

    changelog = load_changelog_sections(repo_root)
    release_section = find_release_section(changelog, requested_tag.raw)
    changelog_status = describe_changelog_status(
        release_section=release_section,
        requested_tag=requested_tag,
        release_kind=release_kind,
    )
    package_version_status = describe_package_metadata_status(
        current_version=current_package_version,
        requested_tag=requested_tag,
    )

    return ReleasePlan(
        release_tag=requested_tag,
        release_class=release_class,
        release_kind=release_kind,
        current_public_release=current_public_release,
        current_package_version=current_package_version,
        requested_package_version=requested_package_version,
        package_version_status=package_version_status,
        current_workspace_version=current_workspace_version,
        current_compiled_contract_version=current_compiled_contract_version,
        current_doctrine_floor=current_doctrine_floor,
        current_doctrine_package_line=current_doctrine_package_line,
        previous_stable_tag=previous_stable_tag,
        previous_same_channel_tag=previous_same_channel_tag,
        changelog_status=changelog_status,
        changelog_header=f"## {requested_tag.raw} - {date.today().isoformat()}",
        release_header_lines=build_release_header_lines(
            release_tag=requested_tag,
            release_kind=release_kind,
        ),
    )


def render_release_worksheet(plan: ReleasePlan) -> str:
    required_updates = [
        "pyproject.toml",
        "docs/VERSIONING.md",
        "CHANGELOG.md",
        "README.md",
        "tests/unit/test_package_release.py",
        "tests/unit/test_release_flow.py",
    ]
    if plan.release_class == "breaking":
        required_updates.extend(
            [
                "affected live docs",
                "proof for the touched public surface",
            ]
        )
    doctrine_source = f"git+https://github.com/aelaguiz/doctrine.git@{plan.current_doctrine_floor}"
    verify_commands = [
        "uv run python tools/sync_bundled_assets.py --check",
        "uv run pytest tests/unit/test_package_release.py -q",
        "uv run pytest tests/unit/test_release_flow.py -q",
        "make build-dist",
        "make verify-package",
        f"RALLY_TEST_DOCTRINE_SOURCE={doctrine_source} uv run pytest tests/integration/test_packaged_install.py -q",
        "uv run pytest tests/unit -q",
        "make verify",
    ]

    lines = [
        "Rally release worksheet",
        "",
        f"Derived release kind: {plan.release_kind}",
        f"Derived release channel: {plan.release_tag.channel_display}",
        f"Current public release version: {plan.current_public_release}",
        f"Previous stable tag: {plan.previous_stable_tag.raw if plan.previous_stable_tag else 'none'}",
        (
            "Previous same-channel tag: "
            f"{plan.previous_same_channel_tag.raw if plan.previous_same_channel_tag else 'none'}"
        ),
        f"Requested release version: {plan.release_tag.raw}",
        f"Current package metadata version: {plan.current_package_version}",
        f"Requested package metadata version: {plan.requested_package_version}",
        f"Package metadata status: {plan.package_version_status}",
        f"Current workspace manifest version: {plan.current_workspace_version}",
        f"Current compiled contract version: {plan.current_compiled_contract_version}",
        f"Current minimum Doctrine release: {plan.current_doctrine_floor}",
        f"Current supported Doctrine package line: {plan.current_doctrine_package_line}",
        f"Changelog entry status: {plan.changelog_status}",
        "Required docs and proof surfaces to update:",
        *[f"- {item}" for item in required_updates],
        "Exact changelog entry header:",
        f"- {plan.changelog_header}",
        "Exact release-note header:",
        *[f"- {line}" for line in plan.release_header_lines],
        "Exact verify commands to run:",
        *[f"- {command}" for command in verify_commands],
        "First package-index publish stop point:",
        "- Before the first real TestPyPI or PyPI publish for `rally-agents`, follow `docs/VERSIONING.md` to create the GitHub Trusted Publishers and matching `testpypi` and `pypi` environments.",
        "Next commands:",
        f"- make release-tag RELEASE={plan.release_tag.raw} CHANNEL={plan.release_tag.channel}",
        (
            "- make release-draft "
            f"RELEASE={plan.release_tag.raw} CHANNEL={plan.release_tag.channel} PREVIOUS_TAG=auto"
        ),
        f"- make release-publish RELEASE={plan.release_tag.raw}",
    ]
    return "\n".join(lines)


def tag_release(*, repo_root: Path, release: str, channel: str) -> None:
    release_tag = parse_release_tag(release, channel=channel)
    require_clean_worktree(repo_root)
    require_signing_key(repo_root)
    release_entry = require_validated_release_entry(
        repo_root=repo_root,
        release_tag=release_tag,
        expected_release_kind=expected_release_kind_for_tag(
            repo_root=repo_root,
            requested_tag=release_tag,
        ),
    )
    require_matching_package_metadata_version(repo_root=repo_root, release_tag=release_tag)
    tag_message = build_tag_message(release_entry)
    run_checked(
        ["git", "tag", "-s", "-a", release_tag.raw, "-m", tag_message],
        cwd=repo_root,
        code="E527",
        summary="Release tag preflight failed",
        detail=f"Could not create signed annotated tag `{release_tag.raw}`.",
    )
    run_checked(
        ["git", "push", "origin", release_tag.raw],
        cwd=repo_root,
        code="E527",
        summary="Release tag preflight failed",
        detail=f"Could not push signed annotated tag `{release_tag.raw}` to `origin`.",
    )
    print(f"Created and pushed signed annotated tag `{release_tag.raw}`.")


def draft_release(
    *,
    repo_root: Path,
    release: str,
    channel: str,
    previous_tag: str,
) -> None:
    release_tag = parse_release_tag(release, channel=channel)
    require_pushed_public_release_tag(repo_root, release_tag)
    release_entry = require_validated_release_entry(
        repo_root=repo_root,
        release_tag=release_tag,
        expected_release_kind=expected_release_kind_for_tag(
            repo_root=repo_root,
            requested_tag=release_tag,
        ),
    )
    require_matching_package_metadata_version(repo_root=repo_root, release_tag=release_tag)
    previous = resolve_previous_tag(
        repo_root=repo_root,
        requested_tag=release_tag,
        previous_tag=previous_tag,
    )
    notes_text = build_release_notes(release_entry)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(notes_text)
        notes_path = Path(handle.name)

    command = [
        "gh",
        "release",
        "create",
        release_tag.raw,
        "--draft",
        "--verify-tag",
        "--title",
        release_tag.release_title,
        "--notes-file",
        str(notes_path),
        "--generate-notes",
    ]
    if previous is not None:
        command.extend(["--notes-start-tag", previous])
    if release_tag.channel != "stable":
        command.extend(["--prerelease", "--latest=false"])

    run_checked(
        command,
        cwd=repo_root,
        code="E529",
        summary="GitHub release command failed",
        detail=f"Could not create GitHub draft release `{release_tag.raw}`.",
        hints=("Make sure `gh auth status` works for this repo.",),
    )
    print(f"Created GitHub draft release `{release_tag.raw}`.")


def publish_release(*, repo_root: Path, release: str) -> None:
    release_tag = parse_release_tag(release)
    require_pushed_public_release_tag(repo_root, release_tag)
    run_checked(
        ["gh", "release", "edit", release_tag.raw, "--draft=false"],
        cwd=repo_root,
        code="E529",
        summary="GitHub release command failed",
        detail=f"Could not publish GitHub release `{release_tag.raw}`.",
        hints=("Make sure `gh auth status` works for this repo.",),
    )
    run_id = wait_for_publish_workflow_run(repo_root=repo_root, release_tag=release_tag)
    run_checked(
        ["gh", "run", "watch", str(run_id), "--exit-status"],
        cwd=repo_root,
        code="E529",
        summary="GitHub release command failed",
        detail=f"`publish.yml` run `{run_id}` did not complete cleanly for `{release_tag.raw}`.",
        hints=("Review the failed workflow run before retrying `make release-publish`.",),
    )
    print(f"Published GitHub release `{release_tag.raw}` and watched `publish.yml` run `{run_id}`.")


def build_release_header_lines(
    *,
    release_tag: ReleaseTag,
    release_kind: str,
) -> tuple[str, ...]:
    return (
        f"Release kind: {release_kind}",
        f"Release channel: {release_tag.channel_display}",
        f"Release version: {release_tag.raw}",
        "Affected surfaces: update for this release",
        "Who must act: fill this in before tagging",
        "Who does not need to act: fill this in before tagging",
        "Upgrade steps: fill this in before tagging",
        "Verification: fill this in before tagging",
        "Support-surface version changes: none unless a narrow Rally contract changed",
    )


def build_tag_message(release_entry: ReleaseEntry) -> str:
    lines = [f"Rally release {release_entry.metadata['Release version']}", ""]
    for field in HEADER_FIELD_ORDER[:3]:
        lines.append(f"{field}: {release_entry.metadata[field]}")
    lines.extend(
        [
            "",
            "See CHANGELOG.md and docs/VERSIONING.md for the full release record.",
        ]
    )
    return "\n".join(lines)


def build_release_notes(release_entry: ReleaseEntry) -> str:
    header = [f"{field}: {release_entry.metadata[field]}" for field in HEADER_FIELD_ORDER]
    if release_entry.body:
        return "\n".join([*header, "", release_entry.body]).strip() + "\n"
    return "\n".join(header).strip() + "\n"


def wait_for_publish_workflow_run(*, repo_root: Path, release_tag: ReleaseTag) -> int:
    commit_sha = _tag_commit_sha(repo_root=repo_root, release_tag=release_tag)
    for attempt in range(10):
        completed = run_checked(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "publish.yml",
                "--event",
                "release",
                "--commit",
                commit_sha,
                "--json",
                "databaseId,event,headSha,status",
                "-L",
                "20",
            ],
            cwd=repo_root,
            code="E529",
            summary="GitHub release command failed",
            detail=f"Could not inspect `publish.yml` runs after publishing `{release_tag.raw}`.",
            hints=("Make sure `gh auth status` works for this repo.",),
        )
        try:
            payload = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise release_error(
                "E529",
                "GitHub release command failed",
                "GitHub CLI returned invalid JSON while Rally was waiting for `publish.yml`.",
            ) from exc
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                run_id = item.get("databaseId")
                if isinstance(run_id, int):
                    return run_id
        if attempt < 9:
            time.sleep(3)
    raise release_error(
        "E529",
        "GitHub release command failed",
        f"Could not find the `publish.yml` run that should have started after publishing `{release_tag.raw}`.",
        hints=(
            "Check the Actions tab and confirm `publish.yml` is enabled for release events.",
            "If the workflow starts late, rerun `make release-publish` once the run exists.",
        ),
    )


def _tag_commit_sha(*, repo_root: Path, release_tag: ReleaseTag) -> str:
    completed = run_checked(
        ["git", "rev-list", "-n", "1", release_tag.raw],
        cwd=repo_root,
        code="E527",
        summary="Release tag preflight failed",
        detail=f"Could not resolve the commit for `{release_tag.raw}`.",
    )
    return completed.stdout.strip()

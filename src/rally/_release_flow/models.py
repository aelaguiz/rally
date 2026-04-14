from __future__ import annotations

from dataclasses import dataclass
import re

RELEASE_TAG_RE = re.compile(
    r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<channel>beta|rc)\.(?P<prerelease>0|[1-9]\d*))?$"
)
CURRENT_PUBLIC_RELEASE_VERSION_RE = re.compile(
    r"^Current public Rally release version:\s*(?P<version>.+?)\s*$",
    re.MULTILINE,
)
CURRENT_DOCTRINE_FLOOR_RE = re.compile(
    r"^Current minimum Doctrine release:\s*`?(?P<version>[^`\n]+)`?\s*$",
    re.MULTILINE,
)
CURRENT_DOCTRINE_PACKAGE_LINE_RE = re.compile(
    r"^Current supported Doctrine package line:\s*`?(?P<value>[^`\n]+)`?\s*$",
    re.MULTILINE,
)
COMPILED_CONTRACT_VERSION_RE = re.compile(
    r"SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS\s*=\s*frozenset\(\{(?P<versions>[^}]*)\}\)"
)
CHANGELOG_SECTION_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)

HEADER_FIELD_ORDER = (
    "Release kind",
    "Release channel",
    "Release version",
    "Affected surfaces",
    "Who must act",
    "Who does not need to act",
    "Upgrade steps",
    "Verification",
    "Support-surface version changes",
)


@dataclass(frozen=True)
class ReleaseTag:
    raw: str
    major: int
    minor: int
    patch: int
    channel: str
    prerelease_number: int | None = None

    @property
    def base(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    @property
    def channel_display(self) -> str:
        if self.channel == "stable":
            return "stable"
        return f"{self.channel}.{self.prerelease_number}"

    @property
    def release_title(self) -> str:
        return f"Rally {self.raw}"


@dataclass(frozen=True)
class ReleasePlan:
    release_tag: ReleaseTag
    release_class: str
    release_kind: str
    current_public_release: str
    current_package_version: str
    requested_package_version: str
    package_version_status: str
    current_workspace_version: int
    current_compiled_contract_version: int
    current_doctrine_floor: str
    current_doctrine_package_line: str
    previous_stable_tag: ReleaseTag | None
    previous_same_channel_tag: ReleaseTag | None
    changelog_status: str
    changelog_header: str
    release_header_lines: tuple[str, ...]


@dataclass(frozen=True)
class ChangelogSection:
    title: str
    key: str
    body: str


@dataclass(frozen=True)
class ReleaseEntry:
    section: ChangelogSection
    metadata: dict[str, str]
    body: str


def sort_key(tag: ReleaseTag) -> tuple[int, int, int, int]:
    prerelease = tag.prerelease_number if tag.prerelease_number is not None else 0
    return (*tag.base, prerelease)

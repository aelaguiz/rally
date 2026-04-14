from __future__ import annotations

from pathlib import Path
import subprocess


class ReleaseFlowError(RuntimeError):
    """Raised when Rally's release preflight or publish flow fails."""


def run_checked(
    command: list[str],
    *,
    cwd: Path,
    code: str,
    summary: str,
    detail: str,
    hints: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise release_error(
            code,
            summary,
            f"{detail} Missing command: `{command[0]}`.",
            hints=hints,
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail_lines = [detail]
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        if stderr:
            detail_lines.append(stderr)
        elif stdout:
            detail_lines.append(stdout)
        raise release_error(
            code,
            summary,
            "\n".join(detail_lines),
            hints=hints,
        ) from exc


def release_error(
    code: str,
    summary: str,
    detail: str,
    *,
    location: Path | None = None,
    hints: tuple[str, ...] = (),
) -> ReleaseFlowError:
    lines = [f"{code} release error: {summary}", detail]
    if location is not None:
        lines.append(f"Location: `{location}`")
    for hint in hints:
        lines.append(f"Hint: {hint}")
    return ReleaseFlowError("\n".join(lines))

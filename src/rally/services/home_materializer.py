from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

from rally.domain.flow import FlowDefinition
from rally.domain.run import RunRecord
from rally.errors import RallyConfigError, RallyStateError
from rally.services.issue_ledger import snapshot_issue_log
from rally.services.run_store import find_run_dir

_MANDATORY_SKILLS = ("rally-kernel",)


def materialize_run_home(
    *,
    repo_root: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    brief_markdown: str,
) -> Path:
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_record.id)
    run_home = run_dir / "home"
    issue_path = run_home / "issue.md"

    _ensure_run_layout(run_dir=run_dir, run_home=run_home)
    _write_seed_files(run_home=run_home, issue_path=issue_path, brief_markdown=brief_markdown)
    _copy_compiled_agents(run_home=run_home, flow=flow)
    _copy_allowed_skills_and_mcps(repo_root=repo_root, run_home=run_home, flow=flow)
    _write_codex_config(repo_root=repo_root, run_home=run_home, flow=flow)
    _seed_codex_auth(run_home=run_home)
    _run_setup_script(
        repo_root=repo_root,
        flow=flow,
        run_record=run_record,
        run_home=run_home,
        issue_path=issue_path,
    )
    snapshot_issue_log(repo_root=repo_root, run_id=run_record.id)
    return run_home


def _ensure_run_layout(*, run_dir: Path, run_home: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "issue_history").mkdir(parents=True, exist_ok=True)
    run_home.mkdir(parents=True, exist_ok=True)
    for relative_dir in (
        "agents",
        "skills",
        "mcps",
        "sessions",
        "artifacts",
        "repos",
    ):
        (run_home / relative_dir).mkdir(parents=True, exist_ok=True)


def _write_seed_files(*, run_home: Path, issue_path: Path, brief_markdown: str) -> None:
    if not brief_markdown.strip():
        raise RallyStateError("Run brief is empty.")

    normalized_brief = brief_markdown
    if not normalized_brief.endswith("\n"):
        normalized_brief = f"{normalized_brief}\n"

    (run_home / "operator_brief.md").write_text(normalized_brief, encoding="utf-8")
    issue_path.write_text(normalized_brief, encoding="utf-8")


def _copy_compiled_agents(*, run_home: Path, flow: FlowDefinition) -> None:
    for agent in flow.agents.values():
        shutil.copytree(
            agent.compiled.markdown_path.parent,
            run_home / "agents" / agent.slug,
            dirs_exist_ok=True,
        )


def _copy_allowed_skills_and_mcps(*, repo_root: Path, run_home: Path, flow: FlowDefinition) -> None:
    skill_names = sorted(
        {
            *(_MANDATORY_SKILLS),
            *(skill for agent in flow.agents.values() for skill in agent.allowed_skills),
        }
    )
    for skill_name in skill_names:
        source = repo_root / "skills" / skill_name
        if not source.is_dir():
            raise RallyConfigError(f"Allowed skill does not exist: `{source}`.")
        _validate_skill_bundle(source=source, skill_name=skill_name)
        shutil.copytree(source, run_home / "skills" / skill_name, dirs_exist_ok=True)

    mcp_names = sorted({mcp for agent in flow.agents.values() for mcp in agent.allowed_mcps})
    for mcp_name in mcp_names:
        source = repo_root / "mcps" / mcp_name
        if not source.is_dir():
            raise RallyConfigError(f"Allowed MCP does not exist: `{source}`.")
        shutil.copytree(source, run_home / "mcps" / mcp_name, dirs_exist_ok=True)


def _write_codex_config(*, repo_root: Path, run_home: Path, flow: FlowDefinition) -> None:
    project_doc_max_bytes = flow.adapter.args.get("project_doc_max_bytes", 0)
    if not isinstance(project_doc_max_bytes, int) or project_doc_max_bytes < 0:
        raise RallyConfigError("`runtime.adapter_args.project_doc_max_bytes` must be a non-negative integer.")

    mcp_names = sorted({mcp for agent in flow.agents.values() for mcp in agent.allowed_mcps})
    lines = [f"project_doc_max_bytes = {project_doc_max_bytes}", ""]
    for mcp_name in mcp_names:
        server_file = repo_root / "mcps" / mcp_name / "server.toml"
        payload = tomllib.loads(server_file.read_text(encoding="utf-8"))
        lines.append(f'[mcp_servers."{mcp_name}"]')
        for key, value in payload.items():
            lines.append(f"{key} = {_render_toml_value(value)}")
        lines.append("")
    (run_home / "config.toml").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _seed_codex_auth(*, run_home: Path) -> None:
    source_home = Path.home() / ".codex"
    for file_name in ("auth.json", ".credentials.json"):
        source = source_home / file_name
        target = run_home / file_name
        if not source.exists():
            continue
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(source)


def _run_setup_script(
    *,
    repo_root: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    run_home: Path,
    issue_path: Path,
) -> None:
    if flow.setup_home_script is None:
        return

    env = {
        "RALLY_BASE_DIR": str(repo_root.resolve()),
        "RALLY_FLOW_CODE": run_record.flow_code,
        "RALLY_FLOW_HOME": str(run_home.resolve()),
        "RALLY_ISSUE_PATH": str(issue_path.resolve()),
        "RALLY_RUN_HOME": str(run_home.resolve()),
        "RALLY_RUN_ID": run_record.id,
    }
    completed = subprocess.run(
        ["bash", str(flow.setup_home_script)],
        cwd=flow.root_dir,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "setup script failed"
        raise RallyStateError(
            f"Setup script `{flow.setup_home_script}` failed for run `{run_record.id}`: {stderr}"
        )


def _validate_skill_bundle(*, source: Path, skill_name: str) -> None:
    skill_file = source / "SKILL.md"
    if not skill_file.is_file():
        raise RallyConfigError(f"Allowed skill is missing `SKILL.md`: `{skill_file}`.")

    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise RallyConfigError(
            f"Skill `{skill_name}` must start with YAML frontmatter so Codex can load it."
        )
    if not any(line.strip() == "---" for line in lines[1:]):
        raise RallyConfigError(
            f"Skill `{skill_name}` is missing the closing YAML frontmatter marker."
        )


def _render_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_render_toml_value(item) for item in value) + "]"
    raise RallyConfigError(f"Unsupported TOML value in MCP server definition: `{value!r}`.")

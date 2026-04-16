from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rally.domain.flow import (
    EmittedOutputContract,
    FlowAgent,
    FlowDefinition,
    OutputBindingContract,
    PreviousTurnInputContract,
)
from rally.domain.rooted_path import PUBLIC_PATH_ROOTS, parse_rooted_path, resolve_rooted_path
from rally.errors import RallyStateError
from rally.services.final_response_loader import load_turn_result_payload


@dataclass(frozen=True)
class _PreviousTurnContext:
    turn_index: int
    agent: FlowAgent
    turn_dir: Path


@dataclass(frozen=True)
class _ResolvedPreviousTurnValue:
    mode: str
    body_text: str


def render_previous_turn_appendix(
    *,
    workspace_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    agent: FlowAgent,
    turn_index: int,
) -> str:
    # This owner path stays narrow on purpose: one appendix, one previous turn,
    # and only the emitted `io` contract plus exact saved artifacts.
    requests = agent.compiled.io.previous_turn_inputs if agent.compiled.io is not None else ()
    if not requests:
        return ""

    previous_turn = _resolve_previous_turn_context(
        run_home=run_home,
        flow=flow,
        turn_index=turn_index,
    )
    lines = ["## Previous Turn Inputs"]
    for request in requests:
        lines.append("")
        lines.extend(
            _render_previous_turn_input(
                workspace_root=workspace_root,
                run_home=run_home,
                flow=flow,
                request=request,
                previous_turn=previous_turn,
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_previous_turn_input(
    *,
    workspace_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext | None,
) -> list[str]:
    lines = [
        f"### {request.input_name}",
        f"- Selector: {request.selector_text}",
        f"- Requirement: `{request.requirement}`",
        f"- Derived Contract: `{request.derived_contract_mode}`",
    ]
    if previous_turn is None:
        if request.requirement == "Required":
            raise RallyStateError(
                f"Required previous-turn input `{request.input_name}` has no previous turn to reopen."
            )
        lines.append("- Status: No previous turn is available yet.")
        return lines

    lines.append(f"- Previous Turn: `{previous_turn.turn_index}`")
    lines.append(f"- Previous Agent: `{previous_turn.agent.slug}`")
    resolved_value = _resolve_previous_turn_value(
        workspace_root=workspace_root,
        run_home=run_home,
        flow=flow,
        request=request,
        previous_turn=previous_turn,
    )
    lines.append("")
    if resolved_value.mode == "structured_json":
        lines.append("```json")
        lines.append(resolved_value.body_text)
        lines.append("```")
        return lines

    lines.append(f"```{_readable_fence_language(request=request)}")
    lines.append(resolved_value.body_text)
    lines.append("```")
    return lines


def _resolve_previous_turn_context(
    *,
    run_home: Path,
    flow: FlowDefinition,
    turn_index: int,
) -> _PreviousTurnContext | None:
    previous_turn_index = turn_index - 1
    if previous_turn_index < 1:
        return None

    matches = sorted((run_home / "sessions").glob(f"*/turn-{previous_turn_index:03d}"))
    if not matches:
        raise RallyStateError(
            f"Previous turn `{previous_turn_index}` is missing from `{run_home / 'sessions'}`."
        )
    if len(matches) > 1:
        raise RallyStateError(
            f"Previous turn `{previous_turn_index}` is ambiguous under `{run_home / 'sessions'}`."
        )

    turn_dir = matches[0]
    agent_slug = turn_dir.parent.name
    try:
        agent = flow.agent_by_slug(agent_slug)
    except KeyError as exc:
        raise RallyStateError(
            f"Previous turn `{previous_turn_index}` belongs to unknown agent slug `{agent_slug}`."
        ) from exc
    return _PreviousTurnContext(
        turn_index=previous_turn_index,
        agent=agent,
        turn_dir=turn_dir,
    )


def _resolve_previous_turn_value(
    *,
    workspace_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext,
) -> _ResolvedPreviousTurnValue:
    if request.selector_kind == "default_final_output":
        return _resolve_previous_final_output(request=request, previous_turn=previous_turn)
    if request.selector_kind == "output_decl":
        output = _resolve_previous_output_by_decl(request=request, previous_turn=previous_turn)
        return _resolve_previous_output_value(
            workspace_root=workspace_root,
            run_home=run_home,
            flow=flow,
            request=request,
            previous_turn=previous_turn,
            output=output,
        )
    if request.selector_kind == "output_binding":
        output = _resolve_previous_output_by_binding(request=request, previous_turn=previous_turn)
        return _resolve_previous_output_value(
            workspace_root=workspace_root,
            run_home=run_home,
            flow=flow,
            request=request,
            previous_turn=previous_turn,
            output=output,
        )
    raise RallyStateError(
        f"Unsupported previous-turn selector kind `{request.selector_kind}` for `{request.input_name}`."
    )


def _resolve_previous_final_output(
    *,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext,
) -> _ResolvedPreviousTurnValue:
    previous_final_output = previous_turn.agent.compiled.final_output
    if request.resolved_declaration_key != previous_final_output.declaration_key:
        raise RallyStateError(
            f"Previous final output mismatch for `{request.input_name}`: expected "
            f"`{request.resolved_declaration_key}`, found `{previous_final_output.declaration_key}`."
        )
    if request.derived_contract_mode != "structured_json":
        raise RallyStateError(
            f"Previous final output for `{request.input_name}` must stay `structured_json`, "
            f"found `{request.derived_contract_mode}`."
        )
    payload = load_turn_result_payload(last_message_file=previous_turn.turn_dir / "last_message.json")
    return _ResolvedPreviousTurnValue(
        mode="structured_json",
        body_text=json.dumps(payload, indent=2),
    )


def _resolve_previous_output_by_decl(
    *,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext,
) -> EmittedOutputContract:
    output = _find_output_by_declaration_key(
        previous_turn=previous_turn,
        declaration_key=request.resolved_declaration_key,
        input_name=request.input_name,
    )
    return output


def _resolve_previous_output_by_binding(
    *,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext,
) -> EmittedOutputContract:
    io_contract = previous_turn.agent.compiled.io
    if io_contract is None:
        raise RallyStateError(
            f"Previous turn metadata is missing `io` for `{request.input_name}`."
        )
    if request.binding_path is None:
        raise RallyStateError(
            f"Previous-turn binding selector is missing `binding_path` for `{request.input_name}`."
        )
    binding = _find_output_binding(
        bindings=io_contract.output_bindings,
        binding_path=request.binding_path,
        input_name=request.input_name,
    )
    if request.resolved_declaration_key is not None and binding.declaration_key != request.resolved_declaration_key:
        raise RallyStateError(
            f"Previous-turn binding metadata disagrees for `{request.input_name}`: expected "
            f"`{request.resolved_declaration_key}`, found `{binding.declaration_key}`."
        )
    return _find_output_by_declaration_key(
        previous_turn=previous_turn,
        declaration_key=binding.declaration_key,
        input_name=request.input_name,
    )


def _find_output_by_declaration_key(
    *,
    previous_turn: _PreviousTurnContext,
    declaration_key: str | None,
    input_name: str,
) -> EmittedOutputContract:
    if declaration_key is None:
        raise RallyStateError(f"Previous-turn declaration metadata is missing for `{input_name}`.")
    io_contract = previous_turn.agent.compiled.io
    if io_contract is None:
        raise RallyStateError(
            f"Previous turn metadata is missing `io.outputs` for `{input_name}`."
        )
    for output in io_contract.outputs:
        if output.declaration_key == declaration_key:
            return output
    raise RallyStateError(
        f"Previous turn output `{declaration_key}` is missing from emitted `io.outputs` for `{input_name}`."
    )


def _find_output_binding(
    *,
    bindings: tuple[OutputBindingContract, ...],
    binding_path: tuple[str, ...],
    input_name: str,
) -> OutputBindingContract:
    for binding in bindings:
        if binding.binding_path == binding_path:
            return binding
    raise RallyStateError(
        f"Previous turn binding `{'.'.join(binding_path)}` is missing from emitted `io.output_bindings` "
        f"for `{input_name}`."
    )


def _resolve_previous_output_value(
    *,
    workspace_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext,
    output: EmittedOutputContract,
) -> _ResolvedPreviousTurnValue:
    # Rally reopens only exact prior artifacts. It does not scrape notes or
    # invent a second readback format when Doctrine marks a target unsupported.
    if request.derived_contract_mode != output.derived_contract_mode:
        raise RallyStateError(
            f"Previous-turn contract-mode mismatch for `{request.input_name}`: expected "
            f"`{request.derived_contract_mode}`, previous output exposes `{output.derived_contract_mode}`."
        )
    if output.readback_mode == "unsupported":
        if _is_note_backed_target(output.target.key):
            raise RallyStateError(
                f"Note-backed previous output reopen is not supported for `{request.input_name}`."
            )
        raise RallyStateError(
            f"Previous output `{output.declaration_key}` uses unsupported readback mode "
            f"`{output.readback_mode}` for `{request.input_name}`."
        )
    if output.target.key == "TurnResponse":
        return _resolve_previous_turn_response_output(
            request=request,
            previous_turn=previous_turn,
            output=output,
        )
    if output.target.key != "File":
        if _is_note_backed_target(output.target.key):
            raise RallyStateError(
                f"Note-backed previous output reopen is not supported for `{request.input_name}`."
            )
        raise RallyStateError(
            f"Previous output `{output.declaration_key}` uses unsupported target `{output.target.key}` "
            f"for `{request.input_name}`."
        )

    artifact_path = _resolve_previous_output_file_path(
        workspace_root=workspace_root,
        run_home=run_home,
        flow=flow,
        output=output,
        input_name=request.input_name,
    )
    if output.readback_mode == "structured_json":
        return _load_structured_json_file(path=artifact_path, input_name=request.input_name)
    if output.readback_mode == "readable_text":
        return _load_readable_text_file(path=artifact_path, input_name=request.input_name)
    raise RallyStateError(
        f"Previous output `{output.declaration_key}` uses unsupported readback mode "
        f"`{output.readback_mode}` for `{request.input_name}`."
    )


def _resolve_previous_turn_response_output(
    *,
    request: PreviousTurnInputContract,
    previous_turn: _PreviousTurnContext,
    output: EmittedOutputContract,
) -> _ResolvedPreviousTurnValue:
    if not output.requires_final_output:
        raise RallyStateError(
            f"Previous TurnResponse output `{output.declaration_key}` is not the previous final output for "
            f"`{request.input_name}`."
        )
    if previous_turn.agent.compiled.final_output.declaration_key != output.declaration_key:
        raise RallyStateError(
            f"Previous TurnResponse output `{output.declaration_key}` does not match the actual previous final output "
            f"for `{request.input_name}`."
        )
    if output.readback_mode != "structured_json":
        raise RallyStateError(
            f"Previous final output for `{request.input_name}` must reopen as `structured_json`, found "
            f"`{output.readback_mode}`."
        )
    payload = load_turn_result_payload(last_message_file=previous_turn.turn_dir / "last_message.json")
    return _ResolvedPreviousTurnValue(
        mode="structured_json",
        body_text=json.dumps(payload, indent=2),
    )


def _resolve_previous_output_file_path(
    *,
    workspace_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    output: EmittedOutputContract,
    input_name: str,
) -> Path:
    raw_path = output.target.config.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise RallyStateError(
            f"Previous output `{output.declaration_key}` is missing file path metadata for `{input_name}`."
        )
    rooted_path = parse_rooted_path(
        raw_path,
        context=f"previous output `{output.declaration_key}` for `{input_name}`",
        allowed_roots=PUBLIC_PATH_ROOTS,
        example="home:artifacts/result.json",
    )
    artifact_path = resolve_rooted_path(
        rooted_path,
        workspace_root=workspace_root,
        flow_root=flow.root_dir,
        run_home=run_home,
        context=f"previous output `{output.declaration_key}` for `{input_name}`",
    )
    if not artifact_path.is_file():
        raise RallyStateError(
            f"Previous output artifact does not exist for `{input_name}`: `{artifact_path}`."
        )
    return artifact_path


def _load_structured_json_file(*, path: Path, input_name: str) -> _ResolvedPreviousTurnValue:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise RallyStateError(
            f"Previous structured output for `{input_name}` is not valid UTF-8: `{path}`."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RallyStateError(
            f"Previous structured output for `{input_name}` is not valid JSON: `{path}`."
        ) from exc
    if not isinstance(payload, dict):
        raise RallyStateError(
            f"Previous structured output for `{input_name}` must be a JSON object: `{path}`."
        )
    return _ResolvedPreviousTurnValue(
        mode="structured_json",
        body_text=json.dumps(payload, indent=2),
    )


def _load_readable_text_file(*, path: Path, input_name: str) -> _ResolvedPreviousTurnValue:
    try:
        body_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RallyStateError(
            f"Previous readable output for `{input_name}` is not valid UTF-8: `{path}`."
        ) from exc
    return _ResolvedPreviousTurnValue(mode="readable_text", body_text=body_text.rstrip())


def _readable_fence_language(*, request: PreviousTurnInputContract) -> str:
    if request.shape is None:
        return "text"
    if "Markdown" in request.shape.name or "Comment" in request.shape.name:
        return "markdown"
    return "text"


def _is_note_backed_target(target_key: str) -> bool:
    return "Note" in target_key or target_key.endswith("NoteAppend")

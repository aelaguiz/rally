from __future__ import annotations

import json
import os
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Callable

from rally.adapters.codex.launcher import build_codex_launch_env, codex_project_doc_max_bytes
from rally.domain.flow import FlowAgent, FlowDefinition
from rally.domain.interview import InterviewLaunch, InterviewReply, TextDeltaCallback
from rally.domain.run import RunRecord
from rally.errors import RallyStateError
from rally.services.workspace import WorkspaceContext

CodexPopenFactory = Callable[..., subprocess.Popen[str]]


class CodexInterviewSession:
    def __init__(
        self,
        *,
        workspace: WorkspaceContext,
        run_home: Path,
        flow: FlowDefinition,
        run_record: RunRecord,
        agent: FlowAgent,
        interview_prompt: str,
        fork_session: bool,
        source_session_id: str | None,
        popen_factory: CodexPopenFactory = subprocess.Popen,
    ) -> None:
        self._workspace = workspace
        self._run_home = run_home
        self._flow = flow
        self._run_record = run_record
        self._agent = agent
        self._interview_prompt = interview_prompt
        self._fork_session = fork_session
        self._source_session_id = source_session_id
        self._popen_factory = popen_factory
        self._command = ("codex", "app-server", "--listen", "stdio://")
        self._env = {
            **os.environ,
            **build_codex_launch_env(
                workspace_dir=workspace.workspace_root,
                cli_bin=workspace.cli_bin,
                run_home=run_home,
                run_id=run_record.id,
                flow_code=run_record.flow_code,
                agent_slug=agent.slug,
                turn_index=1,
            ),
        }
        self._process: subprocess.Popen[str] | None = None
        self._thread_id: str | None = None
        self._next_request_id = 1
        self._pending_notifications: deque[dict[str, object]] = deque()
        self._pending_responses: dict[int, dict[str, object]] = {}
        self._stderr_lines: list[str] = []
        self._stderr_index = 0
        self._stderr_lock = threading.Lock()
        self._stderr_thread: threading.Thread | None = None

    def describe_launch(self, *, message_index: int) -> InterviewLaunch:
        launch_env = dict(self._env)
        launch_env["RALLY_TURN_NUMBER"] = str(message_index)
        return InterviewLaunch(
            command=self._command,
            cwd=str(self._run_home.resolve()),
            env=launch_env,
        )

    def ask(
        self,
        *,
        question: str,
        message_index: int,
        on_text_delta: TextDeltaCallback | None = None,
    ) -> InterviewReply:
        self._start_process_if_needed()
        raw_lines: list[str] = []
        if self._thread_id is None:
            self._thread_id = self._start_or_fork_thread(raw_lines=raw_lines)
        turn_id = self._start_turn(
            raw_lines=raw_lines,
            user_message=question,
            message_index=message_index,
        )
        assistant_text = self._wait_for_turn_completion(
            raw_lines=raw_lines,
            turn_id=turn_id,
            on_text_delta=on_text_delta,
        )
        return InterviewReply(
            session_id=self._thread_id,
            text=assistant_text,
            command=self._command,
            cwd=str(self._run_home.resolve()),
            env=self._env,
            raw_event_lines=tuple(raw_lines),
            stderr_text=self._take_stderr_text(),
        )

    def close(self) -> str:
        process = self._process
        if process is None:
            return ""
        stdin = process.stdin
        if stdin is not None and not stdin.closed:
            stdin.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        stderr_thread = self._stderr_thread
        if stderr_thread is not None:
            stderr_thread.join(timeout=1)
        return self._take_stderr_text()

    def _start_process_if_needed(self) -> None:
        if self._process is not None:
            return
        process = self._popen_factory(
            list(self._command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._run_home,
            env=self._env,
            text=True,
            bufsize=1,
        )
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise RallyStateError("Codex app-server must expose stdin, stdout, and stderr pipes.")
        self._process = process
        self._stderr_thread = threading.Thread(
            target=self._collect_stderr,
            name="rally-codex-interview-stderr",
            daemon=True,
        )
        self._stderr_thread.start()
        try:
            self._request(
                method="initialize",
                params={
                    "clientInfo": {
                        "name": "rally_cli",
                        "title": "Rally CLI",
                        "version": "0.1.0",
                    }
                },
                raw_lines=None,
            )
            self._send_notification(method="initialized")
        except Exception:
            self.close()
            raise

    def _start_or_fork_thread(self, *, raw_lines: list[str]) -> str:
        if self._fork_session:
            if not self._source_session_id:
                raise RallyStateError("Codex interview fork needs a source session id.")
            result = self._request(
                method="thread/fork",
                params={
                    "threadId": self._source_session_id,
                    "model": _adapter_string_arg(self._flow, "model"),
                    "cwd": str(self._run_home.resolve()),
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "config": {"project_doc_max_bytes": codex_project_doc_max_bytes(flow=self._flow)},
                    "developerInstructions": self._interview_prompt,
                    "ephemeral": False,
                    "persistExtendedHistory": True,
                },
                raw_lines=raw_lines,
            )
            return _response_thread_id(method="thread/fork", result=result)
        # Keep the normal Codex turn runner on `codex exec`. This wider
        # app-server client exists only for diagnostic chat and safe forking.
        result = self._request(
            method="thread/start",
            params={
                "model": _adapter_string_arg(self._flow, "model"),
                "cwd": str(self._run_home.resolve()),
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "config": {"project_doc_max_bytes": codex_project_doc_max_bytes(flow=self._flow)},
                "developerInstructions": self._interview_prompt,
                "ephemeral": False,
                "experimentalRawEvents": False,
                "persistExtendedHistory": True,
            },
            raw_lines=raw_lines,
        )
        return _response_thread_id(method="thread/start", result=result)

    def _start_turn(
        self,
        *,
        raw_lines: list[str],
        user_message: str,
        message_index: int,
    ) -> str:
        if self._thread_id is None:
            raise RallyStateError("Codex interview turn needs a diagnostic thread id.")
        params: dict[str, object] = {
            "threadId": self._thread_id,
            "input": [{"type": "text", "text": user_message, "text_elements": []}],
            "cwd": str(self._run_home.resolve()),
            "approvalPolicy": "never",
            "sandboxPolicy": {
                "type": "readOnly",
                "access": {
                    "type": "restricted",
                    "includePlatformDefaults": True,
                    "readableRoots": [str(self._run_home.resolve())],
                },
                "networkAccess": False,
            },
        }
        model = _adapter_string_arg(self._flow, "model")
        if model is not None:
            params["model"] = model
        reasoning_effort = _adapter_string_arg(self._flow, "reasoning_effort")
        if reasoning_effort is not None:
            params["effort"] = reasoning_effort
        self._env["RALLY_TURN_NUMBER"] = str(message_index)
        result = self._request(method="turn/start", params=params, raw_lines=raw_lines)
        turn = result.get("turn")
        if not isinstance(turn, dict):
            raise RallyStateError("Codex interview `turn/start` did not return a turn object.")
        turn_id = turn.get("id")
        if not isinstance(turn_id, str) or not turn_id.strip():
            raise RallyStateError("Codex interview `turn/start` did not return a turn id.")
        return turn_id

    def _wait_for_turn_completion(
        self,
        *,
        raw_lines: list[str],
        turn_id: str,
        on_text_delta: TextDeltaCallback | None,
    ) -> str:
        message_deltas: list[str] = []
        completed_text: str | None = None
        while True:
            notification = self._next_notification(raw_lines=raw_lines)
            method = notification.get("method")
            params = notification.get("params")
            if not isinstance(method, str) or not isinstance(params, dict):
                continue
            if method == "item/agentMessage/delta" and params.get("turnId") == turn_id:
                delta = params.get("delta")
                if isinstance(delta, str):
                    message_deltas.append(delta)
                    if on_text_delta is not None:
                        on_text_delta(delta)
                continue
            if method == "item/completed" and params.get("turnId") == turn_id:
                item = params.get("item")
                if isinstance(item, dict) and item.get("type") == "agentMessage":
                    text = item.get("text")
                    if isinstance(text, str):
                        completed_text = text
                continue
            if method != "turn/completed":
                continue
            turn = params.get("turn")
            if not isinstance(turn, dict) or turn.get("id") != turn_id:
                continue
            status = turn.get("status")
            if status == "completed":
                return completed_text or "".join(message_deltas).strip()
            raise RallyStateError(f"Codex interview turn failed: {_turn_failure_detail(turn)}")

    def _request(
        self,
        *,
        method: str,
        params: dict[str, object],
        raw_lines: list[str] | None,
    ) -> dict[str, object]:
        request_id = self._send_request(method=method, params=params)
        response = self._await_response(method=method, request_id=request_id, raw_lines=raw_lines)
        error = response.get("error")
        if isinstance(error, dict):
            raise RallyStateError(f"Codex interview `{method}` failed: {_jsonrpc_error_text(error)}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise RallyStateError(f"Codex interview `{method}` did not return a result object.")
        return result

    def _send_request(self, *, method: str, params: dict[str, object]) -> int:
        request_id = self._next_request_id
        self._next_request_id += 1
        self._write_message({"id": request_id, "method": method, "params": params})
        return request_id

    def _send_notification(self, *, method: str, params: dict[str, object] | None = None) -> None:
        payload: dict[str, object] = {"method": method}
        if params is not None:
            payload["params"] = params
        self._write_message(payload)

    def _write_message(self, payload: dict[str, object]) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise RallyStateError("Codex interview app-server is not running.")
        try:
            process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            process.stdin.flush()
        except OSError as exc:
            raise RallyStateError("Codex interview app-server closed stdin unexpectedly.") from exc

    def _await_response(
        self,
        *,
        method: str,
        request_id: int,
        raw_lines: list[str] | None,
    ) -> dict[str, object]:
        cached = self._pending_responses.pop(request_id, None)
        if cached is not None:
            return cached
        while True:
            payload = self._read_message(raw_lines=raw_lines)
            if _is_response(payload):
                seen_id = payload.get("id")
                if seen_id == request_id:
                    return payload
                if isinstance(seen_id, int):
                    self._pending_responses[seen_id] = payload
                    continue
                raise RallyStateError(f"Codex interview `{method}` returned a non-integer response id.")
            if _is_notification(payload):
                self._pending_notifications.append(payload)
                continue
            raise RallyStateError(f"Codex interview `{method}` saw an unexpected JSON-RPC payload.")

    def _next_notification(self, *, raw_lines: list[str]) -> dict[str, object]:
        if self._pending_notifications:
            return self._pending_notifications.popleft()
        while True:
            payload = self._read_message(raw_lines=raw_lines)
            if _is_notification(payload):
                return payload
            if _is_response(payload):
                seen_id = payload.get("id")
                if isinstance(seen_id, int):
                    self._pending_responses[seen_id] = payload
                    continue
                raise RallyStateError("Codex interview saw a response with a non-integer id.")
            raise RallyStateError("Codex interview saw an unexpected JSON-RPC payload.")

    def _read_message(self, *, raw_lines: list[str] | None) -> dict[str, object]:
        process = self._process
        if process is None or process.stdout is None:
            raise RallyStateError("Codex interview app-server is not running.")
        while True:
            raw_line = process.stdout.readline()
            if raw_line == "":
                detail = self._take_stderr_text().strip() or "Codex app-server ended before the interview finished."
                raise RallyStateError(detail)
            stripped = raw_line.strip()
            if not stripped:
                continue
            if raw_lines is not None:
                raw_lines.append(stripped)
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise RallyStateError("Codex app-server wrote invalid JSON during the interview.") from exc
            if not isinstance(payload, dict):
                raise RallyStateError("Codex app-server wrote a non-object JSON payload.")
            if "id" in payload and "method" in payload:
                method = payload.get("method")
                if isinstance(method, str):
                    raise RallyStateError(
                        f"Codex interview received unsupported server request `{method}`."
                    )
            return payload

    def _collect_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        for line in iter(process.stderr.readline, ""):
            with self._stderr_lock:
                self._stderr_lines.append(line)

    def _take_stderr_text(self) -> str:
        with self._stderr_lock:
            if self._stderr_index >= len(self._stderr_lines):
                return ""
            text = "".join(self._stderr_lines[self._stderr_index :])
            self._stderr_index = len(self._stderr_lines)
            return text


def _adapter_string_arg(flow: FlowDefinition, key: str) -> str | None:
    value = flow.adapter.args.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _response_thread_id(*, method: str, result: dict[str, object]) -> str:
    thread = result.get("thread")
    if not isinstance(thread, dict):
        raise RallyStateError(f"Codex interview `{method}` did not return a thread object.")
    thread_id = thread.get("id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise RallyStateError(f"Codex interview `{method}` did not return a thread id.")
    return thread_id


def _is_notification(payload: dict[str, object]) -> bool:
    return "method" in payload and "id" not in payload


def _is_response(payload: dict[str, object]) -> bool:
    return "id" in payload and "method" not in payload


def _jsonrpc_error_text(error: dict[str, object]) -> str:
    message = error.get("message")
    if isinstance(message, str) and message.strip():
        detail = message.strip()
    else:
        detail = "unknown JSON-RPC error"
    data = error.get("data")
    if isinstance(data, dict):
        extra = data.get("message")
        if isinstance(extra, str) and extra.strip():
            return f"{detail}: {extra.strip()}"
    return detail


def _turn_failure_detail(turn: dict[str, object]) -> str:
    error = turn.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            additional = error.get("additionalDetails")
            if isinstance(additional, str) and additional.strip():
                return f"{message.strip()} ({additional.strip()})"
            return message.strip()
    status = turn.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()
    return "unknown turn failure"

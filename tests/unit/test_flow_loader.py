from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.flow_loader import load_flow_definition


class FlowLoaderTests(unittest.TestCase):
    def test_load_flow_definition_uses_compiled_slug_mapping(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        flow = load_flow_definition(repo_root=repo_root, flow_name="single_repo_repair")

        self.assertEqual(flow.name, "single_repo_repair")
        self.assertEqual(flow.code, "SRR")
        self.assertEqual(flow.start_agent_key, "01_scope_lead")
        self.assertEqual(flow.agent("01_scope_lead").slug, "scope_lead")
        self.assertEqual(flow.agent("02_change_engineer").compiled.slug, "change_engineer")
        self.assertEqual(
            flow.adapter.prompt_input_command,
            repo_root / "flows/single_repo_repair/setup/prompt_inputs.py",
        )
        self.assertEqual(
            flow.agent("01_scope_lead").compiled.final_output.schema_file,
            repo_root / "stdlib/rally/schemas/rally_turn_result.schema.json",
        )

    def test_load_flow_definition_rejects_unsupported_contract_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, contract_version=99)

            with self.assertRaisesRegex(RallyConfigError, "Unsupported compiled agent contract version"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_handoff_schema_without_next_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, include_next_owner=False)

            with self.assertRaisesRegex(RallyConfigError, "must require .*next_owner"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_support_files_outside_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                schema_file="../shared/schema.json",
                example_file="../shared/example.json",
            )
            shared = repo_root / "shared"
            shared.mkdir(parents=True)
            (shared / "schema.json").write_text(self._schema_text(include_next_owner=True), encoding="utf-8")
            (shared / "example.json").write_text('{"kind":"done","summary":"ok"}\n', encoding="utf-8")

            with self.assertRaisesRegex(RallyConfigError, "escapes the Rally repo root"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def _write_fixture_repo(
        self,
        *,
        repo_root: Path,
        contract_version: int = 1,
        include_next_owner: bool = True,
        schema_file: str = "stdlib/rally/schemas/rally_turn_result.schema.json",
        example_file: str = "stdlib/rally/examples/rally_turn_result.example.json",
    ) -> None:
        flow_root = repo_root / "flows" / "demo"
        build_root = flow_root / "build" / "agents" / "scope_lead"
        prompts_root = flow_root / "prompts"
        schema_root = repo_root / "stdlib" / "rally" / "schemas"
        example_root = repo_root / "stdlib" / "rally" / "examples"

        build_root.mkdir(parents=True)
        prompts_root.mkdir(parents=True)
        schema_root.mkdir(parents=True)
        example_root.mkdir(parents=True)

        (flow_root / "flow.yaml").write_text(
            textwrap.dedent(
                """\
                name: demo
                code: DEMO
                start_agent: 01_scope_lead
                setup_home_script: setup/prepare_home.sh
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills:
                      - repo-search
                    allowed_mcps:
                      - fixture-repo
                runtime:
                  adapter: codex
                  prompt_input_command: setup/prompt_inputs.py
                  adapter_args:
                    model: gpt-5.4
                """
            ),
            encoding="utf-8",
        )
        (flow_root / "setup").mkdir(parents=True)
        (flow_root / "setup" / "prepare_home.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (flow_root / "setup" / "prompt_inputs.py").write_text("print('{}')\n", encoding="utf-8")
        (prompts_root / "AGENTS.prompt").write_text("agent ScopeLead:\n", encoding="utf-8")
        (build_root / "AGENTS.md").write_text("# Scope Lead\n", encoding="utf-8")
        (build_root / "AGENTS.contract.json").write_text(
            json.dumps(
                {
                    "contract_version": contract_version,
                    "agent": {
                        "name": "ScopeLead",
                        "slug": "scope_lead",
                        "entrypoint": "flows/demo/prompts/AGENTS.prompt",
                    },
                    "final_output": {
                        "exists": True,
                        "declaration_key": "DemoTurnResult",
                        "declaration_name": "DemoTurnResult",
                        "format_mode": "json_schema",
                        "schema_profile": "OpenAIStructuredOutput",
                        "schema_file": schema_file,
                        "example_file": example_file,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        if not schema_file.startswith("../"):
            (schema_root / "rally_turn_result.schema.json").write_text(
                self._schema_text(include_next_owner=include_next_owner),
                encoding="utf-8",
            )
        if not example_file.startswith("../"):
            (example_root / "rally_turn_result.example.json").write_text(
                '{"kind":"done","summary":"ok"}\n',
                encoding="utf-8",
            )

    def _schema_text(self, *, include_next_owner: bool) -> str:
        next_owner_required = '"next_owner",' if include_next_owner else ""
        return textwrap.dedent(
            f"""\
            {{
              "type": "object",
              "required": [
                "kind",
                {next_owner_required}
                "summary",
                "reason",
                "sleep_duration_seconds"
              ],
              "properties": {{
                "kind": {{
                  "type": "string",
                  "enum": ["handoff", "done", "blocker", "sleep"]
                }},
                "next_owner": {{
                  "type": ["string", "null"]
                }},
                "summary": {{
                  "type": ["string", "null"]
                }},
                "reason": {{
                  "type": ["string", "null"]
                }},
                "sleep_duration_seconds": {{
                  "type": ["integer", "null"]
                }}
              }}
            }}
            """
        )


if __name__ == "__main__":
    unittest.main()

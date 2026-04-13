from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.flow_loader import load_flow_code, load_flow_definition


class FlowLoaderTests(unittest.TestCase):
    def test_load_flow_code_reads_flow_yaml_without_compiled_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            flow_root = repo_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            (flow_root / "flow.yaml").write_text(
                textwrap.dedent(
                    """\
                    name: demo
                    code: DMO
                    start_agent: 01_scope_lead
                    agents: {}
                    runtime:
                      adapter: codex
                      max_command_turns: 1
                      adapter_args: {}
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(load_flow_code(repo_root=repo_root, flow_name="demo"), "DMO")

    def test_load_flow_definition_uses_compiled_slug_mapping(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        flow = load_flow_definition(repo_root=repo_root, flow_name="poem_loop")

        self.assertEqual(flow.name, "poem_loop")
        self.assertEqual(flow.code, "POM")
        self.assertEqual(flow.start_agent_key, "01_poem_writer")
        self.assertEqual(flow.max_command_turns, 20)
        self.assertEqual(flow.agent("01_poem_writer").slug, "poem_writer")
        self.assertEqual(flow.agent("02_poem_critic").compiled.slug, "poem_critic")
        self.assertIsNone(flow.setup_home_script)
        self.assertIsNone(flow.adapter.prompt_input_command)
        self.assertEqual(flow.guarded_git_repos, ())
        self.assertEqual(
            flow.agent("01_poem_writer").compiled.final_output.schema_file,
            repo_root / "stdlib/rally/schemas/rally_turn_result.schema.json",
        )
        self.assertEqual(
            flow.agent("02_poem_critic").compiled.final_output.schema_file,
            repo_root / "flows/poem_loop/schemas/poem_review.schema.json",
        )
        self.assertIsNotNone(flow.agent("02_poem_critic").compiled.review)
        self.assertEqual(flow.agent("02_poem_critic").compiled.review.final_response.mode, "carrier")
        self.assertTrue(flow.agent("02_poem_critic").compiled.review.final_response.control_ready)

    def test_load_flow_definition_supports_issue_ledger_first_flow_without_setup_or_prompt_inputs(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        flow = load_flow_definition(repo_root=repo_root, flow_name="poem_loop")

        self.assertEqual(flow.name, "poem_loop")
        self.assertEqual(flow.code, "POM")
        self.assertEqual(flow.start_agent_key, "01_poem_writer")
        self.assertEqual(flow.max_command_turns, 20)
        self.assertEqual(flow.agent("01_poem_writer").slug, "poem_writer")
        self.assertEqual(flow.agent("02_poem_critic").slug, "poem_critic")
        self.assertEqual(flow.agent("01_poem_writer").allowed_skills, ())
        self.assertEqual(flow.agent("02_poem_critic").allowed_mcps, ())
        self.assertIsNone(flow.setup_home_script)
        self.assertIsNone(flow.adapter.prompt_input_command)
        self.assertEqual(flow.guarded_git_repos, ())
        self.assertEqual(
            flow.agent("01_poem_writer").compiled.final_output.schema_file,
            repo_root / "stdlib/rally/schemas/rally_turn_result.schema.json",
        )
        self.assertEqual(
            flow.agent("02_poem_critic").compiled.final_output.schema_file,
            repo_root / "flows/poem_loop/schemas/poem_review.schema.json",
        )

    def test_load_flow_definition_loads_guarded_git_repos(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                guarded_git_repos_yaml='["repos/demo_repo"]',
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.guarded_git_repos, (Path("repos/demo_repo"),))

    def test_poem_loop_compiled_readback_includes_kernel_skill_and_rationale_contract(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        flow = load_flow_definition(repo_root=repo_root, flow_name="poem_loop")
        writer_readback = flow.agent("01_poem_writer").compiled.markdown_path.read_text(encoding="utf-8")
        critic_readback = flow.agent("02_poem_critic").compiled.markdown_path.read_text(encoding="utf-8")

        self.assertIn("## Skills", writer_readback)
        self.assertIn("### rally-kernel", writer_readback)
        self.assertIn("### Issue Note", writer_readback)
        self.assertNotIn("\n### Writer Issue Note\n", writer_readback)
        self.assertIn("Artistic Rationale", writer_readback)
        self.assertIn("### Rally Turn Result", writer_readback)
        self.assertIn('Append With: `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`', writer_readback)
        self.assertNotIn("### Issue Note", critic_readback)
        self.assertIn("## Poem Review", critic_readback)
        self.assertIn("### Poem Review Response", critic_readback)
        self.assertIn("#### Review Summary", critic_readback)
        self.assertIn("#### Findings First", critic_readback)
        self.assertNotIn("### Rally Turn Result", critic_readback)

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

    def test_load_flow_definition_rejects_missing_max_command_turns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, include_max_command_turns=False)

            with self.assertRaisesRegex(RallyConfigError, "max_command_turns"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_non_integer_max_command_turns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, max_command_turns_yaml='"many"')

            with self.assertRaisesRegex(RallyConfigError, "max_command_turns"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_zero_max_command_turns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, max_command_turns_yaml="0")

            with self.assertRaisesRegex(RallyConfigError, "max_command_turns"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_absolute_guarded_git_repo_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                guarded_git_repos_yaml='["/tmp/demo_repo"]',
            )

            with self.assertRaisesRegex(RallyConfigError, "run-home-relative"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_support_files_outside_workspace_root(self) -> None:
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

            with self.assertRaisesRegex(RallyConfigError, "escapes the Rally workspace root"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_accepts_control_ready_review_final_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_review_fixture_repo(repo_root=repo_root, control_ready=True)

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertIsNotNone(flow.agent("01_scope_lead").compiled.review)
            self.assertTrue(flow.agent("01_scope_lead").compiled.review.final_response.control_ready)
            self.assertEqual(flow.agent("01_scope_lead").compiled.review.final_response.mode, "carrier")

    def test_load_flow_definition_rejects_non_control_ready_review_final_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_review_fixture_repo(repo_root=repo_root, control_ready=False)

            with self.assertRaisesRegex(RallyConfigError, "not control-ready"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def _write_fixture_repo(
        self,
        *,
        repo_root: Path,
        contract_version: int = 1,
        include_next_owner: bool = True,
        include_max_command_turns: bool = True,
        max_command_turns_yaml: str = "8",
        schema_file: str = "stdlib/rally/schemas/rally_turn_result.schema.json",
        example_file: str = "stdlib/rally/examples/rally_turn_result.example.json",
        guarded_git_repos_yaml: str = "[]",
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
        max_command_turns_line = f"  max_command_turns: {max_command_turns_yaml}\n" if include_max_command_turns else ""
        guarded_git_repos_line = f"  guarded_git_repos: {guarded_git_repos_yaml}\n"

        flow_yaml = (
            "name: demo\n"
            "code: DEMO\n"
            "start_agent: 01_scope_lead\n"
            "setup_home_script: setup/prepare_home.sh\n"
            "agents:\n"
            "  01_scope_lead:\n"
            "    timeout_sec: 60\n"
            "    allowed_skills:\n"
            "      - repo-search\n"
            "    allowed_mcps:\n"
            "      - fixture-repo\n"
            "runtime:\n"
            "  adapter: codex\n"
            f"{max_command_turns_line}"
            f"{guarded_git_repos_line}"
            "  prompt_input_command: setup/prompt_inputs.py\n"
            "  adapter_args:\n"
            "    model: gpt-5.4\n"
        )
        (flow_root / "flow.yaml").write_text(flow_yaml, encoding="utf-8")
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

    def _write_review_fixture_repo(self, *, repo_root: Path, control_ready: bool) -> None:
        flow_root = repo_root / "flows" / "demo"
        build_root = flow_root / "build" / "agents" / "scope_lead"
        prompts_root = flow_root / "prompts"
        schema_root = flow_root / "schemas"
        example_root = flow_root / "examples"

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
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills: []
                    allowed_mcps: []
                runtime:
                  adapter: codex
                  max_command_turns: 8
                  adapter_args: {}
                """
            ),
            encoding="utf-8",
        )
        (prompts_root / "AGENTS.prompt").write_text("agent ScopeLead:\n", encoding="utf-8")
        (build_root / "AGENTS.md").write_text("# Scope Lead\n", encoding="utf-8")
        (schema_root / "review_response.schema.json").write_text(
            textwrap.dedent(
                """\
                {
                  "type": "object",
                  "additionalProperties": false,
                  "properties": {
                    "verdict": {"type": "string"},
                    "reviewed_artifact": {"type": "string"},
                    "analysis_performed": {"type": "string"},
                    "findings_first": {"type": "string"}
                  },
                  "required": ["verdict", "reviewed_artifact", "analysis_performed", "findings_first"]
                }
                """
            ),
            encoding="utf-8",
        )
        (example_root / "review_response.example.json").write_text(
            '{"verdict":"accept","reviewed_artifact":"artifacts/demo.md","analysis_performed":"ok","findings_first":"ok"}\n',
            encoding="utf-8",
        )
        (build_root / "AGENTS.contract.json").write_text(
            json.dumps(
                {
                    "contract_version": 1,
                    "agent": {
                        "name": "ScopeLead",
                        "slug": "scope_lead",
                        "entrypoint": "flows/demo/prompts/AGENTS.prompt",
                    },
                    "final_output": {
                        "exists": True,
                        "declaration_key": "ReviewResponse",
                        "declaration_name": "ReviewResponse",
                        "format_mode": "json_schema",
                        "schema_profile": "OpenAIStructuredOutput",
                        "schema_file": "flows/demo/schemas/review_response.schema.json",
                        "example_file": "flows/demo/examples/review_response.example.json",
                    },
                    "review": {
                        "exists": True,
                        "comment_output": {
                            "declaration_key": "ReviewResponse",
                            "declaration_name": "ReviewResponse",
                        },
                        "carrier_fields": {
                            "verdict": "verdict",
                            "reviewed_artifact": "reviewed_artifact",
                            "analysis": "analysis_performed",
                            "readback": "findings_first",
                        },
                        "final_response": {
                            "mode": "carrier",
                            "declaration_key": "ReviewResponse",
                            "declaration_name": "ReviewResponse",
                            "review_fields": {},
                            "control_ready": control_ready,
                        },
                        "outcomes": {
                            "accept": {
                                "exists": True,
                                "verdict": "accept",
                                "route_behavior": "never",
                            },
                            "changes_requested": {
                                "exists": True,
                                "verdict": "changes_requested",
                                "route_behavior": "always",
                            },
                            "blocked": {
                                "exists": False,
                                "verdict": "changes_requested",
                                "route_behavior": "never",
                            },
                        },
                    },
                },
                indent=2,
            )
            + "\n",
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

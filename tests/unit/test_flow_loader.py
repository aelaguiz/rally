from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.domain.rooted_path import RootedPath
from rally.errors import RallyConfigError
from rally.services.flow_build import ensure_flow_assets_built
from rally.services.flow_loader import load_flow_code, load_flow_definition


def _render_agent_markdown(
    title: str,
    allowed_skills: tuple[str, ...],
    system_skills: tuple[str, ...] = (),
) -> str:
    skill_lines = ["## Skills", "", "### rally-kernel", ""]
    for skill_name in (*allowed_skills, *system_skills):
        skill_lines.extend((f"### {skill_name}", ""))
    return f"# {title}\n\n" + "\n".join(skill_lines)


class FlowLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.repo_root = Path(__file__).resolve().parents[2]
        ensure_flow_assets_built(repo_root=cls.repo_root, flow_name="poem_loop")

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

    def test_load_flow_definition_rejects_invalid_flow_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, flow_code="DEMO")

            # Flow codes become run ids and memory paths, so the loader must
            # stop bad values before the runtime starts writing files.
            with self.assertRaisesRegex(RallyConfigError, "exactly three uppercase ASCII letters"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_uses_compiled_slug_mapping(self) -> None:
        repo_root = self.repo_root

        flow = load_flow_definition(repo_root=repo_root, flow_name="poem_loop")

        self.assertEqual(flow.name, "poem_loop")
        self.assertEqual(flow.code, "POM")
        self.assertEqual(flow.start_agent_key, "00_muse")
        self.assertEqual(flow.max_command_turns, 20)
        self.assertEqual(flow.agent("00_muse").slug, "muse")
        self.assertEqual(flow.agent("01_poem_writer").slug, "poem_writer")
        self.assertEqual(flow.agent("02_poem_critic").compiled.slug, "poem_critic")
        self.assertIsNone(flow.setup_home_script)
        self.assertEqual(flow.host_inputs.required_env, ())
        self.assertEqual(flow.host_inputs.required_files, ())
        self.assertEqual(flow.host_inputs.required_directories, ())
        self.assertEqual(dict(flow.runtime_env), {})
        self.assertEqual(flow.guarded_git_repos, ())
        self.assertEqual(
            flow.agent("00_muse").compiled.final_output.generated_schema_file,
            repo_root / "flows/poem_loop/build/agents/muse/schemas/muse_turn_result.schema.json",
        )
        self.assertEqual(
            flow.agent("01_poem_writer").compiled.final_output.generated_schema_file,
            repo_root / "flows/poem_loop/build/agents/poem_writer/schemas/poem_writer_turn_result.schema.json",
        )
        self.assertEqual(
            flow.agent("02_poem_critic").compiled.final_output.generated_schema_file,
            repo_root / "flows/poem_loop/build/agents/poem_critic/schemas/poem_review_final_response.schema.json",
        )
        self.assertTrue(flow.agent("00_muse").compiled.route.exists)
        self.assertEqual(
            flow.agent("00_muse").compiled.route.selector.field_path,
            ("next_route",),
        )
        self.assertTrue(flow.agent("01_poem_writer").compiled.route.exists)
        self.assertEqual(
            flow.agent("01_poem_writer").compiled.route.selector.field_path,
            ("next_route",),
        )
        self.assertEqual(len(flow.agent("00_muse").compiled.io.previous_turn_inputs), 1)
        self.assertEqual(
            flow.agent("00_muse").compiled.io.previous_turn_inputs[0].resolved_declaration_name,
            "PoemReviewFinalResponse",
        )
        self.assertEqual(
            flow.agent("00_muse").compiled.io.previous_turn_inputs[0].selector_kind,
            "output_decl",
        )
        self.assertEqual(len(flow.agent("01_poem_writer").compiled.io.previous_turn_inputs), 1)
        self.assertEqual(
            flow.agent("01_poem_writer").compiled.io.previous_turn_inputs[0].resolved_declaration_name,
            "MuseTurnResult",
        )
        self.assertIsNotNone(flow.agent("02_poem_critic").compiled.review)
        self.assertEqual(flow.agent("02_poem_critic").compiled.review.final_response.mode, "split")
        self.assertTrue(flow.agent("02_poem_critic").compiled.review.final_response.control_ready)

    def test_load_flow_definition_supports_issue_ledger_first_flow_without_setup_or_prompt_inputs(self) -> None:
        repo_root = self.repo_root

        flow = load_flow_definition(repo_root=repo_root, flow_name="poem_loop")

        self.assertEqual(flow.name, "poem_loop")
        self.assertEqual(flow.code, "POM")
        self.assertEqual(flow.start_agent_key, "00_muse")
        self.assertEqual(flow.max_command_turns, 20)
        self.assertEqual(flow.agent("00_muse").slug, "muse")
        self.assertEqual(flow.agent("01_poem_writer").slug, "poem_writer")
        self.assertEqual(flow.agent("02_poem_critic").slug, "poem_critic")
        self.assertEqual(flow.agent("00_muse").allowed_skills, ())
        self.assertEqual(flow.agent("01_poem_writer").allowed_skills, ())
        self.assertEqual(flow.agent("02_poem_critic").allowed_mcps, ())
        self.assertIsNone(flow.setup_home_script)
        self.assertEqual(flow.host_inputs.required_env, ())
        self.assertEqual(flow.host_inputs.required_files, ())
        self.assertEqual(flow.host_inputs.required_directories, ())
        self.assertEqual(dict(flow.runtime_env), {})
        self.assertEqual(flow.guarded_git_repos, ())
        self.assertEqual(
            flow.agent("00_muse").compiled.final_output.generated_schema_file,
            repo_root / "flows/poem_loop/build/agents/muse/schemas/muse_turn_result.schema.json",
        )
        self.assertEqual(
            flow.agent("01_poem_writer").compiled.final_output.generated_schema_file,
            repo_root / "flows/poem_loop/build/agents/poem_writer/schemas/poem_writer_turn_result.schema.json",
        )
        self.assertEqual(
            flow.agent("02_poem_critic").compiled.final_output.generated_schema_file,
            repo_root / "flows/poem_loop/build/agents/poem_critic/schemas/poem_review_final_response.schema.json",
        )

    def test_load_flow_definition_loads_emitted_io_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                io_payload={
                    "previous_turn_inputs": [
                        {
                            "input_key": "PreviousRepairPlan",
                            "input_name": "Previous Repair Plan",
                            "selector_kind": "output_binding",
                            "selector_text": "scope_lead.ScopeLeadOutputs:repair_plan",
                            "resolved_declaration_key": "RepairPlan",
                            "resolved_declaration_name": "RepairPlan",
                            "derived_contract_mode": "readable_text",
                            "requirement": "Advisory",
                            "target": {
                                "key": "File",
                                "title": "File",
                                "config": {"path": "home:artifacts/repair_plan.md"},
                            },
                            "shape": {
                                "name": "MarkdownDocument",
                                "title": "Markdown Document",
                            },
                            "binding_path": ["repair_plan"],
                        }
                    ],
                    "outputs": [
                        {
                            "declaration_key": "DemoTurnResult",
                            "declaration_name": "DemoTurnResult",
                            "title": "Demo Turn Result",
                            "target": {
                                "key": "TurnResponse",
                                "title": "Turn Response",
                                "config": {},
                            },
                            "derived_contract_mode": "structured_json",
                            "readback_mode": "structured_json",
                            "requires_final_output": True,
                            "shape": {
                                "name": "DemoTurnJson",
                                "title": "Demo Turn JSON",
                            },
                            "schema": {
                                "name": "DemoTurnSchema",
                                "title": "Demo Turn Schema",
                                "profile": "OpenAIStructuredOutput",
                            },
                        },
                        {
                            "declaration_key": "RepairPlan",
                            "declaration_name": "RepairPlan",
                            "title": "Repair Plan",
                            "target": {
                                "key": "File",
                                "title": "File",
                                "config": {"path": "home:artifacts/repair_plan.md"},
                            },
                            "derived_contract_mode": "readable_text",
                            "readback_mode": "readable_text",
                            "requires_final_output": False,
                            "shape": {
                                "name": "MarkdownDocument",
                                "title": "Markdown Document",
                            },
                        },
                    ],
                    "output_bindings": [
                        {
                            "binding_path": ["turn_result"],
                            "declaration_key": "DemoTurnResult",
                        },
                        {
                            "binding_path": ["repair_plan"],
                            "declaration_key": "RepairPlan",
                        },
                    ],
                },
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            compiled = flow.agent("01_scope_lead").compiled
            self.assertIsNotNone(compiled.io)
            request = compiled.io.previous_turn_inputs[0]
            self.assertEqual(request.selector_kind, "output_binding")
            self.assertEqual(request.binding_path, ("repair_plan",))
            self.assertEqual(request.target.key, "File")
            self.assertEqual(request.target.config["path"], "home:artifacts/repair_plan.md")
            self.assertEqual(compiled.io.outputs[1].declaration_key, "RepairPlan")
            self.assertEqual(compiled.io.outputs[1].readback_mode, "readable_text")
            self.assertEqual(compiled.io.output_bindings[1].binding_path, ("repair_plan",))

    def test_load_flow_definition_rejects_compiled_skill_surface_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root)
            build_root = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead"
            (build_root / "AGENTS.md").write_text(
                _render_agent_markdown("Scope Lead", ()),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyConfigError, "Compiled skill readback"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_loads_system_skills_tier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                allowed_skills_block="    allowed_skills: []\n",
                system_skills_block="    system_skills:\n      - rally-memory\n",
                agents_md_allowed_skills=(),
                agents_md_system_skills=("rally-memory",),
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.agent("01_scope_lead").allowed_skills, ())
            self.assertEqual(flow.agent("01_scope_lead").system_skills, ("rally-memory",))

    def test_load_flow_definition_requires_system_skills_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                system_skills_block="",
            )

            with self.assertRaisesRegex(RallyConfigError, "`system_skills` must be a list"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_unknown_system_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                system_skills_block="    system_skills:\n      - rally-memry\n",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"Unknown Rally stdlib skill `rally-memry`",
            ):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_mandatory_skill_in_system_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                system_skills_block="    system_skills:\n      - rally-kernel\n",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"`rally-kernel` is a mandatory Rally stdlib skill",
            ):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_duplicate_system_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                system_skills_block=(
                    "    system_skills:\n"
                    "      - rally-memory\n"
                    "      - rally-memory\n"
                ),
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"`system_skills` for agent `01_scope_lead` must not repeat",
            ):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_skill_tier_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                allowed_skills_block="    allowed_skills:\n      - rally-memory\n",
                system_skills_block="    system_skills:\n      - rally-memory\n",
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"both `allowed_skills` and `system_skills`",
            ):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_allows_compiler_owned_peer_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root)
            peer_file = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "SOUL.md"
            peer_file.write_text("# Scope Soul\n", encoding="utf-8")

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.agent("01_scope_lead").slug, "scope_lead")
            self.assertTrue(peer_file.is_file())

    def test_load_flow_definition_loads_guarded_git_repos(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                guarded_git_repos_yaml='["home:repos/demo_repo"]',
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.guarded_git_repos, (Path("repos/demo_repo"),))

    def test_load_flow_definition_loads_host_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                host_inputs_yaml=textwrap.dedent(
                    """\
                    host_inputs:
                      required_env: [PSMOBILE_ROOT, PSMOBILE_CONFIG_PACK]
                      required_files:
                        - host:~/.config/psmobile-dev-configs/.env
                      required_directories:
                        - workspace:fixtures/psmobile
                    """
                ),
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.host_inputs.required_env, ("PSMOBILE_ROOT", "PSMOBILE_CONFIG_PACK"))
            self.assertEqual(
                flow.host_inputs.required_files,
                (RootedPath(root="host", path_text="~/.config/psmobile-dev-configs/.env"),),
            )
            self.assertEqual(
                flow.host_inputs.required_directories,
                (RootedPath(root="workspace", path_text="fixtures/psmobile"),),
            )

    def test_load_flow_definition_loads_env_backed_host_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                host_inputs_yaml=textwrap.dedent(
                    """\
                    host_inputs:
                      required_env: [PSMOBILE_SOURCE_REPO]
                      required_directories:
                        - host:$PSMOBILE_SOURCE_REPO
                    """
                ),
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.host_inputs.required_env, ("PSMOBILE_SOURCE_REPO",))
            self.assertEqual(
                flow.host_inputs.required_directories,
                (RootedPath(root="host", path_text="$PSMOBILE_SOURCE_REPO"),),
            )

    def test_load_flow_definition_loads_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                runtime_env_yaml=textwrap.dedent(
                    """\
                      env:
                        PROJECT_ROOT: workspace:fixtures/project
                        FLOW_REPO: home:repos/demo_repo
                        API_BASE_URL: https://example.test
                    """
                ),
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(
                dict(flow.runtime_env),
                {
                    "PROJECT_ROOT": "workspace:fixtures/project",
                    "FLOW_REPO": "home:repos/demo_repo",
                    "API_BASE_URL": "https://example.test",
                },
            )

    def test_load_flow_definition_accepts_legacy_codex_project_doc_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root)

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_path.write_text(
                flow_text.replace(
                    "    model: gpt-5.4\n",
                    "    model: gpt-5.4\n    project_doc_max_bytes: 0\n",
                ),
                encoding="utf-8",
            )

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(flow.adapter.args["project_doc_max_bytes"], 0)

    def test_load_flow_definition_rejects_non_zero_codex_project_doc_setting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root)

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_path.write_text(
                flow_text.replace(
                    "    model: gpt-5.4\n",
                    "    model: gpt-5.4\n    project_doc_max_bytes: 512\n",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyConfigError, "no longer configurable"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_missing_emitted_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "workspace"
            self._write_fixture_repo(repo_root=repo_root, write_schema=False)

            with self.assertRaisesRegex(RallyConfigError, "schemas/rally_turn_result.schema.json"):
                load_flow_definition(
                    repo_root=repo_root,
                    flow_name="demo",
                )

    def test_load_flow_definition_rejects_non_list_host_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                host_inputs_yaml=textwrap.dedent(
                    """\
                    host_inputs:
                      required_env: PSMOBILE_ROOT
                    """
                ),
            )

            with self.assertRaisesRegex(RallyConfigError, "required_env"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_duplicate_host_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                host_inputs_yaml=textwrap.dedent(
                    """\
                    host_inputs:
                      required_files:
                        - host:~/.config/psmobile-dev-configs/.env
                        - host:~/.config/psmobile-dev-configs/.env
                    """
                ),
            )

            with self.assertRaisesRegex(RallyConfigError, "must not repeat"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_invalid_runtime_env_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                runtime_env_yaml=textwrap.dedent(
                    """\
                      env:
                        bad-key: value
                    """
                ),
            )

            with self.assertRaisesRegex(RallyConfigError, "runtime.env"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_reserved_runtime_env_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                runtime_env_yaml=textwrap.dedent(
                    """\
                      env:
                        RALLY_RUN_ID: DMO-1
                    """
                ),
            )

            with self.assertRaisesRegex(RallyConfigError, "reserved"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_poem_loop_compiled_readback_includes_kernel_skill_and_rationale_contract(self) -> None:
        repo_root = self.repo_root

        flow = load_flow_definition(repo_root=repo_root, flow_name="poem_loop")
        muse_readback = flow.agent("00_muse").compiled.markdown_path.read_text(encoding="utf-8")
        writer_readback = flow.agent("01_poem_writer").compiled.markdown_path.read_text(encoding="utf-8")
        critic_readback = flow.agent("02_poem_critic").compiled.markdown_path.read_text(encoding="utf-8")

        self.assertIn("### Previous Poem Review", muse_readback)
        self.assertIn("### Muse Turn Result", muse_readback)
        self.assertIn("one muse, one writer, one critic", muse_readback)
        self.assertIn("## Skills", writer_readback)
        self.assertIn("### rally-kernel", writer_readback)
        self.assertNotIn("### rally-memory", writer_readback)
        self.assertIn("### Saved Run Note", writer_readback)
        self.assertNotIn("\n### Writer Issue Note\n", writer_readback)
        self.assertIn("### Previous Muse Turn", writer_readback)
        self.assertIn("### Issue Ledger", writer_readback)
        self.assertNotIn("### Rally Workspace Dir", writer_readback)
        self.assertNotIn("### Rally Run ID", writer_readback)
        self.assertNotIn("### Rally Flow Code", writer_readback)
        self.assertNotIn("### Rally Agent Slug", writer_readback)
        self.assertIn("## Rally Context", writer_readback)
        self.assertIn("## Read First", writer_readback)
        self.assertIn("## Shared Rules", writer_readback)
        self.assertNotIn("### Read Order", writer_readback)
        self.assertNotIn("### Turn Sequence", writer_readback)
        self.assertIn("Artistic Rationale", writer_readback)
        self.assertIn("### Poem Writer Turn Result", writer_readback)
        self.assertIn("| Delivered Via | `rally-kernel` |", writer_readback)
        self.assertIn("`inspiration`", writer_readback)
        self.assertIn("Always send every field in this schema.", writer_readback)
        self.assertIn(
            "Rally is the shared control plane for this run.",
            writer_readback,
        )
        self.assertIn("Read `home:issue.md` from the top", writer_readback)
        self.assertIn("Use `home:issue.md` as the shared ledger for this run.", writer_readback)
        self.assertNotIn("For this turn, read skills from `home:skills/`.", writer_readback)
        self.assertNotIn("On Codex turns, that same folder is `$CODEX_HOME/skills/`.", writer_readback)
        self.assertNotIn("Many turns use this shared result.", writer_readback)
        self.assertNotIn("**Use When**", writer_readback)
        self.assertNotIn("**Reason**", writer_readback)
        self.assertNotIn("### Saved Run Note", critic_readback)
        self.assertIn("## Poem Review", critic_readback)
        self.assertIn("### Poem Review Response", critic_readback)
        self.assertIn("#### Review Summary", critic_readback)
        self.assertIn("#### Findings First", critic_readback)
        self.assertIn("Use Muse when the poem needs another draft.", critic_readback)
        self.assertNotIn("### Rally Turn Result", critic_readback)
        self.assertIn("### Poem Review Final Response", critic_readback)
        self.assertIn("This final response is control-ready. A host may read it as the review outcome.", critic_readback)

    def test_stdlib_smoke_closeout_uses_inherited_turn_result_family(self) -> None:
        repo_root = self.repo_root

        schema = json.loads(
            (repo_root / "flows/_stdlib_smoke/build/agents/closeout/schemas/closeout_turn_result.schema.json").read_text(
                encoding="utf-8"
            )
        )
        closeout_readback = (repo_root / "flows/_stdlib_smoke/build/agents/closeout/AGENTS.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(schema["title"], "Closeout Turn Result Schema")
        self.assertIn("current_artifact", schema["properties"])
        self.assertEqual(
            schema["properties"]["kind"]["enum"],
            ["handoff", "done", "blocker", "sleep"],
        )
        self.assertIn("### Closeout Turn Result", closeout_readback)
        self.assertIn(
            "| `current_artifact` | string | Yes | Yes | Current artifact path when the smoke test closes out. |",
            closeout_readback,
        )

    def test_stdlib_smoke_route_repair_emits_previous_turn_input_metadata(self) -> None:
        repo_root = self.repo_root

        metadata = json.loads(
            (repo_root / "flows/_stdlib_smoke/build/agents/route_repair/final_output.contract.json").read_text(
                encoding="utf-8"
            )
        )
        route_repair_readback = (repo_root / "flows/_stdlib_smoke/build/agents/route_repair/AGENTS.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(len(metadata["io"]["previous_turn_inputs"]), 1)
        previous_input = metadata["io"]["previous_turn_inputs"][0]
        self.assertEqual(previous_input["selector_kind"], "default_final_output")
        self.assertEqual(previous_input["resolved_declaration_key"], "PlanAuthorTurnResult")
        self.assertEqual(previous_input["derived_contract_mode"], "structured_json")
        self.assertIn("### Previous Plan Author Turn", route_repair_readback)
        self.assertIn("Exact previous final output", route_repair_readback)

    def test_stdlib_smoke_review_probe_uses_split_final_output_on_shared_review_family(self) -> None:
        repo_root = self.repo_root

        metadata = json.loads(
            (repo_root / "flows/_stdlib_smoke/build/agents/repair_plan_reviewer/final_output.contract.json").read_text(
                encoding="utf-8"
            )
        )
        reviewer_readback = (
            repo_root / "flows/_stdlib_smoke/build/agents/repair_plan_reviewer/AGENTS.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(metadata["final_output"]["declaration_name"], "SmokeReviewFinalResponse")
        self.assertEqual(metadata["review"]["comment_output"]["declaration_name"], "SmokeReviewResponse")
        self.assertEqual(metadata["review"]["final_response"]["mode"], "split")
        self.assertTrue(metadata["review"]["final_response"]["control_ready"])
        self.assertIn("### Smoke Review Final Response", reviewer_readback)
        self.assertIn("This final response is control-ready. A host may read it as the review outcome.", reviewer_readback)

    def test_software_engineering_demo_reviewers_use_split_control_ready_final_output(self) -> None:
        repo_root = self.repo_root

        architect_metadata = json.loads(
            (
                repo_root
                / "flows/software_engineering_demo/build/agents/architect_reviewer/final_output.contract.json"
            ).read_text(encoding="utf-8")
        )
        qa_metadata = json.loads(
            (repo_root / "flows/software_engineering_demo/build/agents/qa_reviewer/final_output.contract.json").read_text(
                encoding="utf-8"
            )
        )
        architect_readback = (
            repo_root / "flows/software_engineering_demo/build/agents/architect/AGENTS.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(architect_metadata["review"]["final_response"]["mode"], "split")
        self.assertTrue(architect_metadata["review"]["final_response"]["control_ready"])
        self.assertEqual(
            architect_metadata["final_output"]["declaration_name"],
            "EngineeringReviewFinalResponse",
        )
        self.assertEqual(qa_metadata["review"]["final_response"]["mode"], "split")
        self.assertTrue(qa_metadata["review"]["final_response"]["control_ready"])
        self.assertIn("This flow works in one demo repo at `home:repos/demo_repo`.", architect_readback)
        self.assertNotIn("Read the newest `Rally Turn Result` block before you rely on an older review verdict.", architect_readback)
        self.assertNotIn("Treat the review JSON in that block as the current review truth.", architect_readback)
        self.assertNotIn("rally runtime review", architect_readback)

    def test_framework_owned_memory_prompt_stays_opt_in(self) -> None:
        repo_root = self.repo_root

        flow_skills_source = (
            repo_root / "flows/software_engineering_demo/prompts/shared/skills.prompt"
        ).read_text(encoding="utf-8")
        base_source = (repo_root / "stdlib/rally/prompts/rally/base_agent.prompt").read_text(encoding="utf-8")
        memory_source = (repo_root / "stdlib/rally/prompts/rally/memory.prompt").read_text(encoding="utf-8")

        # Shared base rules stay lean. A flow only teaches memory use when it
        # opts into the memory skill on purpose.
        self.assertNotIn("rally-memory", flow_skills_source)
        self.assertNotIn("rally-memory", base_source)
        self.assertIn("workflow RallyReadFirst", base_source)
        self.assertIn("workflow RallyHowToTakeATurn", base_source)
        self.assertIn('skill RallyMemorySkill: "rally-memory"', memory_source)
        self.assertNotIn("workflow RallyReadFirst", memory_source)
        self.assertNotIn("workflow RallyHowToTakeATurn", memory_source)

    def test_load_flow_definition_rejects_unsupported_contract_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, contract_version=99)

            with self.assertRaisesRegex(RallyConfigError, "Unsupported final-output contract version"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_handoff_schema_without_next_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, include_next_owner=False)

            with self.assertRaisesRegex(
                RallyConfigError,
                "route selector field `next_owner`|missing route selector field `next_owner`",
            ):
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

            with self.assertRaisesRegex(RallyConfigError, "rooted Rally path"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_rejects_support_files_outside_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(
                repo_root=repo_root,
                emitted_schema_relpath="../shared/schema.json",
                write_schema=False,
            )
            shared = repo_root / "shared"
            shared.mkdir(parents=True)
            (shared / "schema.json").write_text(self._schema_text(include_next_owner=True), encoding="utf-8")

            with self.assertRaisesRegex(RallyConfigError, "must not escape its compiled agent directory"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def test_load_flow_definition_accepts_emitted_schema_relpath(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root)

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            self.assertEqual(
                flow.agent("01_scope_lead").compiled.final_output.generated_schema_file,
                repo_root
                / "flows"
                / "demo"
                / "build"
                / "agents"
                / "scope_lead"
                / "schemas"
                / "rally_turn_result.schema.json",
            )
            self.assertEqual(
                flow.agent("01_scope_lead").compiled.final_output.metadata_file,
                repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "final_output.contract.json",
            )

    def test_load_flow_definition_accepts_turn_result_schema_with_extra_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_fixture_repo(repo_root=repo_root, extra_required_fields=("inspiration",))

            flow = load_flow_definition(repo_root=repo_root, flow_name="demo")

            schema = json.loads(
                flow.agent("01_scope_lead").compiled.final_output.generated_schema_file.read_text(
                    encoding="utf-8"
                )
            )
            self.assertIn("inspiration", schema["required"])
            self.assertIn("inspiration", schema["properties"])

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
        flow_code: str = "DMO",
        contract_version: int = 1,
        include_next_owner: bool = True,
        include_agent_issues: bool = False,
        include_max_command_turns: bool = True,
        max_command_turns_yaml: str = "8",
        emitted_schema_relpath: str = "schemas/rally_turn_result.schema.json",
        write_schema: bool = True,
        guarded_git_repos_yaml: str = "[]",
        host_inputs_yaml: str = "",
        runtime_env_yaml: str = "",
        extra_required_fields: tuple[str, ...] = (),
        io_payload: dict[str, object] | None = None,
        allowed_skills_block: str = "    allowed_skills:\n      - repo-search\n",
        system_skills_block: str = "    system_skills: []\n",
        agents_md_allowed_skills: tuple[str, ...] = ("repo-search",),
        agents_md_system_skills: tuple[str, ...] = (),
    ) -> None:
        flow_root = repo_root / "flows" / "demo"
        build_root = flow_root / "build" / "agents" / "scope_lead"
        prompts_root = flow_root / "prompts"
        schema_root = build_root / "schemas"

        build_root.mkdir(parents=True)
        prompts_root.mkdir(parents=True)
        schema_root.mkdir(parents=True)
        max_command_turns_line = f"  max_command_turns: {max_command_turns_yaml}\n" if include_max_command_turns else ""
        guarded_git_repos_line = f"  guarded_git_repos: {guarded_git_repos_yaml}\n"
        runtime_env_block = textwrap.indent(runtime_env_yaml, "  ") if runtime_env_yaml else ""

        flow_yaml = (
            "name: demo\n"
            f"code: {flow_code}\n"
            "start_agent: 01_scope_lead\n"
            "setup_home_script: flow:setup/prepare_home.sh\n"
            f"{host_inputs_yaml}"
            "agents:\n"
            "  01_scope_lead:\n"
            "    timeout_sec: 60\n"
            f"{allowed_skills_block}"
            f"{system_skills_block}"
            "    allowed_mcps:\n"
            "      - fixture-repo\n"
            "runtime:\n"
            "  adapter: codex\n"
            f"{max_command_turns_line}"
            f"{guarded_git_repos_line}"
            f"{runtime_env_block}"
            "  adapter_args:\n"
            "    model: gpt-5.4\n"
        )
        (flow_root / "flow.yaml").write_text(flow_yaml, encoding="utf-8")
        (flow_root / "setup").mkdir(parents=True)
        (flow_root / "setup" / "prepare_home.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (prompts_root / "AGENTS.prompt").write_text("agent ScopeLead:\n", encoding="utf-8")
        (build_root / "AGENTS.md").write_text(
            _render_agent_markdown(
                "Scope Lead",
                agents_md_allowed_skills,
                agents_md_system_skills,
            ),
            encoding="utf-8",
        )
        contract_payload: dict[str, object] = {
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
                "format_mode": "json_object",
                "schema_profile": "OpenAIStructuredOutput",
                "emitted_schema_relpath": emitted_schema_relpath,
            },
            "route": {
                "exists": True,
                "behavior": "conditional",
                "has_unrouted_branch": True,
                "unrouted_review_verdicts": [],
                "selector": {
                    "surface": "final_output",
                    "field_path": ["next_owner"],
                    "null_behavior": "no_route",
                },
                "branches": [
                    {
                        "target": {
                            "key": "change_engineer",
                            "module_parts": [],
                            "name": "ChangeEngineer",
                            "title": "Change Engineer",
                        },
                        "label": "Send the change to ChangeEngineer.",
                        "summary": "Send the change to ChangeEngineer. Next owner: change_engineer.",
                        "choice_members": [
                            {
                                "member_key": "change_engineer",
                                "member_title": "Change Engineer",
                                "member_wire": "change_engineer",
                            }
                        ],
                    }
                ],
            },
        }
        if io_payload is not None:
            contract_payload["io"] = io_payload
        (build_root / "final_output.contract.json").write_text(
            json.dumps(contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )

        schema_path = (build_root / emitted_schema_relpath).resolve()
        try:
            schema_path.relative_to(build_root.resolve())
        except ValueError:
            return
        if write_schema:
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_text(
                self._schema_text(
                    include_next_owner=include_next_owner,
                    extra_required_fields=extra_required_fields,
                ),
                encoding="utf-8",
            )

    def _write_review_fixture_repo(self, *, repo_root: Path, control_ready: bool) -> None:
        flow_root = repo_root / "flows" / "demo"
        build_root = flow_root / "build" / "agents" / "scope_lead"
        prompts_root = flow_root / "prompts"
        schema_root = build_root / "schemas"

        build_root.mkdir(parents=True)
        prompts_root.mkdir(parents=True)
        schema_root.mkdir(parents=True)

        (flow_root / "flow.yaml").write_text(
            textwrap.dedent(
                """\
                name: demo
                code: DMO
                start_agent: 01_scope_lead
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills: []
                    system_skills: []
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
        (build_root / "AGENTS.md").write_text(
            _render_agent_markdown("Scope Lead", ()),
            encoding="utf-8",
        )
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
        (build_root / "final_output.contract.json").write_text(
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
                        "format_mode": "json_object",
                        "schema_profile": "OpenAIStructuredOutput",
                        "emitted_schema_relpath": "schemas/review_response.schema.json",
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

    def _schema_text(
        self,
        *,
        include_next_owner: bool,
        extra_required_fields: tuple[str, ...] = (),
    ) -> str:
        required = ["kind", "summary", "reason", "sleep_duration_seconds"]
        if include_next_owner:
            required.insert(1, "next_owner")
        required.extend(extra_required_fields)
        properties: dict[str, object] = {
            "kind": {
                "type": "string",
                "enum": ["handoff", "done", "blocker", "sleep"],
            },
            "next_owner": {
                "type": ["string", "null"],
            },
            "summary": {
                "type": ["string", "null"],
            },
            "reason": {
                "type": ["string", "null"],
            },
            "sleep_duration_seconds": {
                "type": ["integer", "null"],
            },
        }
        for field_name in extra_required_fields:
            properties[field_name] = {"type": ["string", "null"]}
        return json.dumps({"type": "object", "required": required, "properties": properties}, indent=2) + "\n"


class FlowLoaderRuntimeConfigTests(unittest.TestCase):
    def test_load_flow_definition_rejects_prompt_input_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_runtime_fixture_repo(repo_root=repo_root)

            # Rally should fail loud here instead of keeping a generic per-turn
            # prompt reducer alive in the runtime contract.
            with self.assertRaisesRegex(RallyConfigError, "does not support `runtime.prompt_input_command`"):
                load_flow_definition(repo_root=repo_root, flow_name="demo")

    def _write_runtime_fixture_repo(self, *, repo_root: Path) -> None:
        flow_root = repo_root / "flows" / "demo"
        build_root = flow_root / "build" / "agents" / "scope_lead"
        prompts_root = flow_root / "prompts"
        schema_root = build_root / "schemas"

        build_root.mkdir(parents=True)
        prompts_root.mkdir(parents=True)
        schema_root.mkdir(parents=True)

        (flow_root / "flow.yaml").write_text(
            textwrap.dedent(
                """\
                name: demo
                code: DMO
                start_agent: 01_scope_lead
                setup_home_script: flow:setup/prepare_home.sh
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills: []
                    system_skills: []
                    allowed_mcps: []
                runtime:
                  adapter: codex
                  max_command_turns: 8
                  prompt_input_command: flow:setup/prompt_inputs.py
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
        (build_root / "AGENTS.md").write_text(
            _render_agent_markdown("Scope Lead", ()),
            encoding="utf-8",
        )
        (build_root / "final_output.contract.json").write_text(
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
                        "declaration_key": "DemoTurnResult",
                        "declaration_name": "DemoTurnResult",
                        "format_mode": "json_object",
                        "schema_profile": "OpenAIStructuredOutput",
                        "emitted_schema_relpath": "schemas/rally_turn_result.schema.json",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (schema_root / "rally_turn_result.schema.json").write_text(
            textwrap.dedent(
                """\
                {
                  "type": "object",
                  "required": ["kind", "next_owner", "summary", "reason", "sleep_duration_seconds"],
                  "properties": {
                    "kind": {"type": "string", "enum": ["handoff", "done", "blocker", "sleep"]},
                    "next_owner": {"type": ["string", "null"]},
                    "summary": {"type": ["string", "null"]},
                    "reason": {"type": ["string", "null"]},
                    "sleep_duration_seconds": {"type": ["integer", "null"]}
                  }
                }
                """
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()

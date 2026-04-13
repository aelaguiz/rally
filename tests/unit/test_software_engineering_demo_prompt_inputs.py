from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_prompt_inputs_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "flows"
        / "software_engineering_demo"
        / "setup"
        / "prompt_inputs.py"
    )
    spec = importlib.util.spec_from_file_location("software_engineering_demo_prompt_inputs", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SoftwareEngineeringDemoPromptInputTests(unittest.TestCase):
    def test_review_facts_maps_rally_agent_keys_to_review_mode(self) -> None:
        module = _load_prompt_inputs_module()
        issue_text = """
## Rally Turn Result
- Run ID: `SED-1`
- Turn: `1`
- Time: `2026-04-13T22:43:40.238336Z`
- Source: `rally runtime`
- Agent: `01_architect`
- Result: `handoff`
- Next Owner: `critic`
""".strip()

        facts = module.review_facts(issue_text=issue_text, current_agent_key="02_critic")

        self.assertEqual(facts["selected_mode"], "architect_review")
        self.assertFalse(facts["review_basis_missing"])
        self.assertEqual(facts["last_turn_agent"], "architect")

    def test_review_facts_maps_qa_agent_key_to_qa_review(self) -> None:
        module = _load_prompt_inputs_module()
        issue_text = """
## Rally Turn Result
- Run ID: `SED-2`
- Turn: `4`
- Time: `2026-04-13T23:10:00.000000Z`
- Source: `rally runtime`
- Agent: `04_qa_docs_tester`
- Result: `handoff`
- Next Owner: `critic`
""".strip()

        facts = module.review_facts(issue_text=issue_text, current_agent_key="02_critic")

        self.assertEqual(facts["selected_mode"], "qa_review")
        self.assertFalse(facts["review_basis_missing"])
        self.assertEqual(facts["last_turn_agent"], "qa_docs_tester")

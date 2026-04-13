from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "flows"
    / "single_repo_repair"
    / "setup"
    / "prompt_inputs.py"
)
_SPEC = importlib.util.spec_from_file_location("single_repo_repair_prompt_inputs", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class SingleRepoRepairPromptInputsTests(unittest.TestCase):
    def test_opening_brief_from_issue_returns_initial_brief_only(self) -> None:
        issue_text = (
            "Fix the pagination bug.\n"
            "Make the smallest change.\n"
            "\n"
            "## Rally Note\n"
            "- Run ID: `SRR-1`\n"
            "- Source: `rally issue note`\n"
        )

        brief_text = _MODULE._opening_brief_from_issue(issue_text)

        self.assertEqual(brief_text, "Fix the pagination bug.\nMake the smallest change.")

    def test_opening_brief_from_issue_keeps_full_text_when_no_rally_block_exists(self) -> None:
        issue_text = "Fix the pagination bug.\n"

        brief_text = _MODULE._opening_brief_from_issue(issue_text)

        self.assertEqual(brief_text, "Fix the pagination bug.")


if __name__ == "__main__":
    unittest.main()

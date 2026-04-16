from __future__ import annotations

import unittest
from pathlib import Path


class SharedPromptOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.repo_root = Path(__file__).resolve().parents[2]

    def test_base_agent_owns_shared_run_rules(self) -> None:
        source = (self.repo_root / "stdlib/rally/prompts/rally/base_agent.prompt").read_text(encoding="utf-8")

        self.assertIn("Use `home:issue.md` as the shared ledger for this run.", source)
        self.assertIn("Leave one short saved note through `Saved Run Note` only when later readers need it.", source)
        self.assertIn("End the turn with the final JSON this turn declares.", source)
        self.assertIn("Keep routing, `done`, `blocker`, and `sleep` in final JSON, not in notes.", source)
        self.assertNotIn("rally-memory", source)

    def test_base_agent_owns_shared_note_output(self) -> None:
        source = (self.repo_root / "stdlib/rally/prompts/rally/base_agent.prompt").read_text(encoding="utf-8")

        self.assertIn('output target RallyIssueNoteAppend: "Rally Issue Note Append"', source)
        self.assertIn("delivery_skill: RallyKernelSkill", source)
        self.assertIn('output RallyIssueNote: "Issue Note"', source)
        self.assertNotIn("rally-memory", source)

    def test_rally_kernel_stays_note_focused(self) -> None:
        source = (self.repo_root / "skills/rally-kernel/prompts/SKILL.prompt").read_text(encoding="utf-8")

        self.assertNotIn("Rally loads this skill on every Rally-managed turn.", source)
        self.assertNotIn("Keep notes run-local. Use `rally-memory` for cross-run lessons.", source)
        self.assertNotIn("Keep `next_owner`, `done`, `blocker`, and `sleep` in final JSON, not in notes.", source)
        self.assertIn("This skill is for note work only. It does not replace the turn's declared output.", source)

    def test_rally_memory_stays_memory_focused(self) -> None:
        source = (self.repo_root / "skills/rally-memory/prompts/SKILL.prompt").read_text(encoding="utf-8")

        self.assertNotIn("Rally loads this skill on every Rally-managed turn.", source)
        self.assertNotIn("Final JSON still controls the turn.", source)
        self.assertNotIn("Do not use memory to pass routing, `done`, `blocker`, or `sleep` truth.", source)
        self.assertIn("This skill is for memory work only. It does not replace the turn's declared output.", source)


if __name__ == "__main__":
    unittest.main()

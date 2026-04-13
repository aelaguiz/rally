from __future__ import annotations

import unittest

from rally.domain.flow import flow_agent_key_to_slug


class FlowContractsTests(unittest.TestCase):
    def test_flow_agent_key_to_slug_strips_numeric_prefix(self) -> None:
        self.assertEqual(flow_agent_key_to_slug("01_scope_lead"), "scope_lead")

    def test_flow_agent_key_to_slug_preserves_plain_slug(self) -> None:
        self.assertEqual(flow_agent_key_to_slug("change_engineer"), "change_engineer")


if __name__ == "__main__":
    unittest.main()

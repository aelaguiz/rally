from __future__ import annotations

import unittest

from rally.adapters.registry import get_adapter, supported_adapter_names
from rally.errors import RallyConfigError


class AdapterRegistryTests(unittest.TestCase):
    def test_supported_adapter_names_include_codex_and_claude_code(self) -> None:
        self.assertEqual(supported_adapter_names(), ("claude_code", "codex"))

    def test_get_adapter_returns_registered_adapters(self) -> None:
        self.assertEqual(get_adapter("codex").display_name, "Codex")
        self.assertEqual(get_adapter("claude_code").display_name, "Claude Code")

    def test_get_adapter_rejects_unknown_name(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "Unsupported `runtime.adapter` value `unknown`"):
            get_adapter("unknown")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from rally.adapters.codex.event_stream import CodexEventStreamParser


class CodexEventStreamTests(unittest.TestCase):
    def test_parser_turns_text_tool_and_usage_lines_into_events(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=3,
            agent_key="01_scope_lead",
            agent_slug="scope_lead",
        )

        drafts = []
        drafts.extend(
            parser.consume_stdout_line('{"type":"thread.started","thread_id":"session-1"}\n')
        )
        drafts.extend(
            parser.consume_stdout_line('{"type":"assistant.message.delta","delta":"Looking at the diff\\n"}\n')
        )
        drafts.extend(
            parser.consume_stdout_line('{"type":"reasoning.delta","delta":"Checking the route logic\\n"}\n')
        )
        drafts.extend(
            parser.consume_stdout_line('{"type":"tool.call.started","tool_name":"shell","command":"rg -n bug src"}\n')
        )
        drafts.extend(
            parser.consume_stdout_line('{"type":"tool.call.completed","tool_name":"shell","message":"2 matches"}\n')
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}\n'
            )
        )

        self.assertEqual(parser.session_id, "session-1")
        self.assertEqual([draft.code for draft in drafts], ["SESSION", "ASSIST", "REASON", "TOOL", "TOOL OK", "USAGE"])
        self.assertIn("Looking at the diff", drafts[1].message)
        self.assertIn("rg -n bug src", drafts[3].message)
        self.assertIn("Token use", drafts[5].message)


if __name__ == "__main__":
    unittest.main()

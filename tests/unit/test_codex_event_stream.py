from __future__ import annotations

import unittest

from rally.adapters.codex.event_stream import CodexEventStreamParser


class CodexEventStreamTests(unittest.TestCase):
    def test_parser_normalizes_official_item_events_into_trace_events(self) -> None:
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
            parser.consume_stdout_line(
                '{"type":"item.completed","item":{"id":"item_1","type":"reasoning","text":"Check the route\\nKeep the handoff tight"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.started","item":{"id":"item_2","type":"command_execution","command":"rg -n page src","aggregated_output":"","status":"in_progress"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.completed","item":{"id":"item_2","type":"command_execution","command":"rg -n page src","aggregated_output":"12 matches\\nfile.py:8","exit_code":0,"status":"completed"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.started","item":{"id":"item_3","type":"mcp_tool_call","server":"web","tool":"search","arguments":{"q":"pagination bug"},"status":"in_progress"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.completed","item":{"id":"item_4","type":"file_change","changes":[{"path":"src/app.py","kind":"update"},{"path":"tests/test_app.py","kind":"add"}],"status":"completed"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}\n'
            )
        )

        self.assertEqual(parser.session_id, "session-1")
        self.assertEqual(
            [draft.code for draft in drafts],
            ["SESSION", "THINK", "CMD", "CMD OK", "MCP", "PATCH OK", "USAGE"],
        )
        self.assertEqual(drafts[1].data["trace_class"], "thinking")
        self.assertEqual(drafts[1].data["detail_lines"], ["Keep the handoff tight"])
        self.assertEqual(drafts[3].data["detail_lines"], ["exit code 0", "12 matches", "file.py:8"])
        self.assertEqual(drafts[4].data["item_type"], "mcp_tool_call")
        self.assertIn("args:", drafts[4].data["detail_lines"][0])
        self.assertEqual(drafts[5].data["detail_lines"], ["M src/app.py", "A tests/test_app.py"])
        self.assertIn("Token use", drafts[6].message)

    def test_parser_maps_failed_tool_calls_and_search_events(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=4,
            agent_key="02_change_engineer",
            agent_slug="change_engineer",
        )

        drafts = []
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.started","item":{"id":"item_1","type":"web_search","query":"pytest tmp path"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.completed","item":{"id":"item_1","type":"web_search","query":"pytest tmp path"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.completed","item":{"id":"item_2","type":"mcp_tool_call","server":"fixture","tool":"seed","arguments":{"repo":"demo"},"error":{"message":"bad input"},"status":"failed"}}\n'
            )
        )

        self.assertEqual([draft.code for draft in drafts], ["SEARCH", "SEARCH OK", "MCP ERR"])
        self.assertEqual(drafts[2].level, "error")
        self.assertIn("error: bad input", drafts[2].data["detail_lines"])

    def test_parser_formats_memory_commands_as_memory_events(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=5,
            agent_key="03_proof_engineer",
            agent_slug="proof_engineer",
        )

        drafts = []
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"/bin/zsh -lc \'\\\"$RALLY_CLI_BIN\\\" memory search --run-id \\\"$RALLY_RUN_ID\\\" --query \\\"focus the fix\\\"\'","aggregated_output":"","status":"in_progress"}}\n'
            )
        )
        drafts.extend(
            parser.consume_stdout_line(
                '{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"/bin/zsh -lc \'\\\"$RALLY_CLI_BIN\\\" memory search --run-id \\\"$RALLY_RUN_ID\\\" --query \\\"focus the fix\\\"\'","aggregated_output":"1. mem_dmo_scope_lead_focus_the_fix (0.83)\\n   Focus the fix\\n   Fix the concrete bug before widening scope.","exit_code":0,"status":"completed"}}\n'
            )
        )

        self.assertEqual([draft.code for draft in drafts], ["MEM", "MEM OK"])
        self.assertEqual(drafts[0].message, "Search memory for 'focus the fix'.")
        self.assertEqual(drafts[1].message, "Found 1 memory hit.")
        self.assertEqual(drafts[1].kind, "memory")
        self.assertEqual(drafts[1].data["trace_class"], "memory")
        self.assertEqual(
            drafts[1].data["detail_lines"],
            ["mem_dmo_scope_lead_focus_the_fix: Focus the fix"],
        )

    def test_parser_keeps_legacy_text_and_tool_fallbacks(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=5,
            agent_key="03_proof_engineer",
            agent_slug="proof_engineer",
        )

        drafts = []
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

        self.assertEqual([draft.code for draft in drafts], ["ASSIST", "THINK", "TOOL", "TOOL OK"])
        self.assertEqual(drafts[1].data["trace_class"], "thinking")
        self.assertEqual(drafts[2].data["trace_class"], "tool")


class CodexEventStreamBufferFlushTests(unittest.TestCase):
    # Protects the buffer-drain invariant. Codex streams assistant and reasoning
    # text as incremental deltas; a complete line only emits when a `\n` lands
    # or a non-text event forces `_flush_text_buffers()`. If an adapter turn
    # tears down with trailing text still in the buffer (stream cut, missing
    # terminal event, final chunk without newline), the operator MUST still see
    # that content in the run log — silent loss here looks like a "missing
    # assistant message" bug that is nearly impossible to diagnose after the
    # fact. These tests pin that end-of-stream drain and the mid-stream flush
    # that runs at the head of every non-text event.

    def test_flush_drains_trailing_assistant_delta_without_newline(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=7,
            agent_key="01_scope_lead",
            agent_slug="scope_lead",
        )

        buffered = parser.consume_stdout_line(
            '{"type":"assistant.message.delta","delta":"final words without newline"}\n'
        )
        self.assertEqual(buffered, [])

        drained = parser.flush()
        self.assertEqual(len(drained), 1)
        self.assertEqual(drained[0].code, "ASSIST")
        self.assertEqual(drained[0].kind, "assistant")
        self.assertEqual(drained[0].message, "final words without newline")

        self.assertEqual(parser.flush(), [])

    def test_flush_drains_trailing_reasoning_delta_without_newline(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=8,
            agent_key="02_change_engineer",
            agent_slug="change_engineer",
        )

        buffered = parser.consume_stdout_line(
            '{"type":"reasoning.delta","delta":"still weighing the trade"}\n'
        )
        self.assertEqual(buffered, [])

        drained = parser.flush()
        self.assertEqual(len(drained), 1)
        self.assertEqual(drained[0].code, "THINK")
        self.assertEqual(drained[0].kind, "reasoning")
        self.assertEqual(drained[0].message, "still weighing the trade")
        self.assertEqual(drained[0].data["trace_class"], "thinking")

    def test_non_text_event_flushes_buffered_deltas_before_its_own_draft(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=9,
            agent_key="03_proof_engineer",
            agent_slug="proof_engineer",
        )

        initial = parser.consume_stdout_line(
            '{"type":"assistant.message.delta","delta":"wrap-up without newline"}\n'
        )
        self.assertEqual(initial, [])

        usage = parser.consume_stdout_line(
            '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}\n'
        )

        self.assertEqual([draft.code for draft in usage], ["ASSIST", "USAGE"])
        self.assertEqual(usage[0].message, "wrap-up without newline")
        self.assertIn("Token use", usage[1].message)

        self.assertEqual(parser.flush(), [])

    def test_flush_with_empty_buffers_returns_no_drafts(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=10,
            agent_key="01_scope_lead",
            agent_slug="scope_lead",
        )

        self.assertEqual(parser.flush(), [])

        whitespace_only = parser.consume_stdout_line(
            '{"type":"assistant.message.delta","delta":"   "}\n'
        )
        self.assertEqual(whitespace_only, [])
        self.assertEqual(parser.flush(), [])

    def test_flush_drains_both_buffers_when_both_have_content(self) -> None:
        parser = CodexEventStreamParser(
            turn_index=11,
            agent_key="01_scope_lead",
            agent_slug="scope_lead",
        )

        assistant = parser.consume_stdout_line(
            '{"type":"assistant.message.delta","delta":"summary fragment"}\n'
        )
        reasoning = parser.consume_stdout_line(
            '{"type":"reasoning.delta","delta":"thought fragment"}\n'
        )
        self.assertEqual(assistant, [])
        self.assertEqual(reasoning, [])

        drained = parser.flush()
        self.assertEqual([draft.code for draft in drained], ["ASSIST", "THINK"])
        self.assertEqual(drained[0].message, "summary fragment")
        self.assertEqual(drained[1].message, "thought fragment")


if __name__ == "__main__":
    unittest.main()

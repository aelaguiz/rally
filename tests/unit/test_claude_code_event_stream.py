from __future__ import annotations

import json
import unittest

from rally.adapters.claude_code.event_stream import ClaudeCodeEventStreamParser, extract_structured_output


class ClaudeCodeEventStreamTests(unittest.TestCase):
    def test_parser_emits_session_reasoning_tool_and_usage_events(self) -> None:
        parser = ClaudeCodeEventStreamParser(
            turn_index=3,
            agent_key="01_scope_lead",
            agent_slug="scope_lead",
        )

        init_drafts = parser.consume_stdout_line(
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "session_id": "claude-session-1",
                }
            )
            + "\n"
        )
        thinking_drafts = parser.consume_stdout_line(
            json.dumps(
                {
                    "type": "assistant",
                    "session_id": "claude-session-1",
                    "message": {
                        "content": [
                            {"type": "thinking", "thinking": "Trace the pagination path."},
                            {
                                "type": "tool_use",
                                "id": "toolu_1",
                                "name": "Read",
                                "input": {"file_path": "/tmp/demo.txt"},
                            },
                        ]
                    },
                }
            )
            + "\n"
        )
        result_drafts = parser.consume_stdout_line(
            json.dumps(
                {
                    "type": "user",
                    "session_id": "claude-session-1",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_1",
                                "content": "1\thello\n",
                            }
                        ]
                    },
                }
            )
            + "\n"
        )
        usage_drafts = parser.consume_stdout_line(
            json.dumps(
                {
                    "type": "result",
                    "session_id": "claude-session-1",
                    "usage": {
                        "input_tokens": 3,
                        "output_tokens": 5,
                        "cache_read_input_tokens": 7,
                    },
                    "structured_output": {"kind": "done", "summary": "ok"},
                }
            )
            + "\n"
        )

        self.assertEqual(parser.session_id, "claude-session-1")
        self.assertEqual(init_drafts[0].code, "SESSION")
        self.assertEqual(thinking_drafts[0].code, "THINK")
        self.assertEqual(thinking_drafts[1].message, "Read `/tmp/demo.txt`.")
        self.assertEqual(result_drafts[0].code, "TOOL OK")
        self.assertIn("/tmp/demo.txt", result_drafts[0].message)
        self.assertEqual(usage_drafts[0].code, "USAGE")

    def test_extract_structured_output_prefers_result_event(self) -> None:
        stdout_text = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "StructuredOutput",
                                    "input": {"kind": "done", "summary": "tool"},
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "structured_output": {"kind": "done", "summary": "result"},
                    }
                ),
            ]
        )

        self.assertEqual(
            extract_structured_output(stdout_text),
            {"kind": "done", "summary": "result"},
        )

    def test_extract_structured_output_accepts_json_result_string_when_structured_output_is_missing(self) -> None:
        stdout_text = json.dumps(
            {
                "type": "result",
                "result": '{"kind":"done","summary":"text-result"}',
            }
        )

        self.assertEqual(
            extract_structured_output(stdout_text),
            {"kind": "done", "summary": "text-result"},
        )

    def test_extract_structured_output_accepts_fenced_json_result_string(self) -> None:
        stdout_text = json.dumps(
            {
                "type": "result",
                "result": '```json\n{"kind":"done","summary":"fenced-result"}\n```',
            }
        )

        self.assertEqual(
            extract_structured_output(stdout_text),
            {"kind": "done", "summary": "fenced-result"},
        )

    def test_extract_structured_output_accepts_fenced_json_from_assistant_text(self) -> None:
        stdout_text = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": '```json\n{"kind":"done","summary":"assistant-fenced"}\n```',
                        }
                    ]
                },
            }
        )

        self.assertEqual(
            extract_structured_output(stdout_text),
            {"kind": "done", "summary": "assistant-fenced"},
        )


if __name__ == "__main__":
    unittest.main()

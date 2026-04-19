from __future__ import annotations

import unittest

from rally.services.tool_digest import (
    classify_sub_kind,
    make_input_digest,
    scrub_secrets,
)


class MakeInputDigestTests(unittest.TestCase):
    def test_bash_uses_command_field(self) -> None:
        digest = make_input_digest("Bash", {"command": "ls -la /tmp"})
        self.assertEqual(digest, "ls -la /tmp")

    def test_read_uses_file_path(self) -> None:
        digest = make_input_digest("Read", {"file_path": "/etc/hosts"})
        self.assertEqual(digest, "/etc/hosts")

    def test_glob_uses_pattern(self) -> None:
        digest = make_input_digest("Glob", {"pattern": "**/*.py"})
        self.assertEqual(digest, "**/*.py")

    def test_webfetch_uses_url(self) -> None:
        digest = make_input_digest("WebFetch", {"url": "https://example.com/a"})
        self.assertEqual(digest, "https://example.com/a")

    def test_task_combines_subagent_and_description(self) -> None:
        digest = make_input_digest(
            "Task",
            {"subagent_type": "Explore", "description": "Find all endpoints"},
        )
        self.assertEqual(digest, "Explore: Find all endpoints")

    def test_string_input_is_returned_as_is(self) -> None:
        digest = make_input_digest("shell", "echo hello")
        self.assertEqual(digest, "echo hello")

    def test_zsh_wrapper_is_stripped(self) -> None:
        digest = make_input_digest(
            "Bash",
            {"command": '/bin/zsh -lc "cd /tmp && ls"'},
        )
        self.assertEqual(digest, "cd /tmp && ls")

    def test_zsh_wrapper_single_quoted(self) -> None:
        digest = make_input_digest(
            "Bash",
            {"command": "/bin/zsh -lc 'rally memory refresh'"},
        )
        self.assertEqual(digest, "rally memory refresh")

    def test_truncates_long_input(self) -> None:
        big = "x" * 300
        digest = make_input_digest("Bash", {"command": big}, max_len=40)
        self.assertIsNotNone(digest)
        assert digest is not None  # mypy hint
        self.assertEqual(len(digest), 40)
        self.assertTrue(digest.endswith("…"))

    def test_returns_none_for_empty(self) -> None:
        self.assertIsNone(make_input_digest("Bash", {"command": "   "}))
        self.assertIsNone(make_input_digest("Bash", {}))
        self.assertIsNone(make_input_digest("Bash", None))

    def test_fallback_to_known_keys_for_unknown_tool(self) -> None:
        digest = make_input_digest("SomeTool", {"description": "do a thing"})
        self.assertEqual(digest, "do a thing")

    def test_whitespace_is_collapsed(self) -> None:
        digest = make_input_digest("Bash", {"command": "echo   a\n\n   b"})
        self.assertEqual(digest, "echo a b")


class ScrubSecretsTests(unittest.TestCase):
    def test_scrubs_password_flag(self) -> None:
        self.assertIn("<scrub>", scrub_secrets("mysql --password=hunter2"))
        self.assertNotIn("hunter2", scrub_secrets("mysql --password=hunter2"))

    def test_scrubs_token_flag(self) -> None:
        self.assertIn("<scrub>", scrub_secrets("curl --token=abcd1234"))

    def test_scrubs_authorization_header(self) -> None:
        scrubbed = scrub_secrets('curl -H "Authorization: Bearer abcd"')
        self.assertIn("<scrub>", scrubbed)
        self.assertNotIn("abcd", scrubbed)

    def test_scrubs_env_var_keys(self) -> None:
        scrubbed = scrub_secrets("GH_TOKEN=ghp_xyz rally run")
        self.assertIn("<scrub>", scrubbed)
        self.assertNotIn("ghp_xyz", scrubbed)

    def test_scrubs_aws_access_key(self) -> None:
        scrubbed = scrub_secrets("env AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
        self.assertIn("<scrub-aws-key>", scrubbed)

    def test_scrubs_slack_token(self) -> None:
        scrubbed = scrub_secrets("curl -d xoxb-abcdefghij1234567890")
        self.assertIn("<scrub-slack>", scrubbed)

    def test_scrubs_openai_key(self) -> None:
        scrubbed = scrub_secrets("env OPENAI=sk-abcdefghijklmnopqrstuvwxyz")
        self.assertIn("<scrub-openai>", scrubbed)

    def test_leaves_benign_text_alone(self) -> None:
        text = "ls -la /tmp/foo"
        self.assertEqual(scrub_secrets(text), text)


class ClassifySubKindTests(unittest.TestCase):
    def test_known_tools(self) -> None:
        self.assertEqual(classify_sub_kind("Bash"), "bash")
        self.assertEqual(classify_sub_kind("Shell"), "bash")
        self.assertEqual(classify_sub_kind("Read"), "read")
        self.assertEqual(classify_sub_kind("Edit"), "edit")
        self.assertEqual(classify_sub_kind("Glob"), "search")
        self.assertEqual(classify_sub_kind("WebFetch"), "fetch")
        self.assertEqual(classify_sub_kind("Task"), "sub_agent")

    def test_unknown_tool_returns_other(self) -> None:
        self.assertEqual(classify_sub_kind("NotReal"), "other")
        self.assertEqual(classify_sub_kind(""), "other")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

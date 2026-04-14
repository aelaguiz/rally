from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.domain.rooted_path import (
    FLOW_ROOT,
    HOME_ROOT,
    HOST_ROOT,
    STDLIB_ROOT,
    WORKSPACE_ROOT,
    RootedPath,
    expand_rooted_value,
    parse_rooted_path,
    resolve_rooted_path,
)
from rally.errors import RallyConfigError


class RootedPathTests(unittest.TestCase):
    def test_parse_and_resolve_home_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_home = Path(temp_dir).resolve()
            rooted = parse_rooted_path(
                "home:issue.md",
                context="demo path",
                allowed_roots={HOME_ROOT},
                example="home:issue.md",
            )

            self.assertEqual(rooted, RootedPath(root="home", path_text="issue.md"))
            self.assertEqual(
                resolve_rooted_path(rooted, run_home=run_home, context="demo path"),
                run_home / "issue.md",
            )

    def test_parse_and_resolve_flow_and_stdlib_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)

            flow_path = parse_rooted_path(
                "flow:schemas/review.schema.json",
                context="schema file",
                allowed_roots={FLOW_ROOT, STDLIB_ROOT},
                example="flow:schemas/review.schema.json",
            )
            stdlib_path = parse_rooted_path(
                "stdlib:schemas/rally_turn_result.schema.json",
                context="stdlib schema",
                allowed_roots={FLOW_ROOT, STDLIB_ROOT},
                example="stdlib:schemas/rally_turn_result.schema.json",
            )

            self.assertEqual(
                resolve_rooted_path(
                    flow_path,
                    workspace_root=workspace_root,
                    flow_root=flow_root,
                    context="schema file",
                ),
                flow_root / "schemas" / "review.schema.json",
            )
            self.assertEqual(
                resolve_rooted_path(
                    stdlib_path,
                    workspace_root=workspace_root,
                    flow_root=flow_root,
                    context="stdlib schema",
                ),
                workspace_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json",
            )

    def test_resolve_stdlib_path_from_framework_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            workspace_root = root / "workspace"
            flow_root = workspace_root / "flows" / "demo"
            framework_root = root / "framework"
            flow_root.mkdir(parents=True)
            (framework_root / "stdlib" / "rally" / "schemas").mkdir(parents=True)

            stdlib_path = parse_rooted_path(
                "stdlib:schemas/rally_turn_result.schema.json",
                context="stdlib schema",
                allowed_roots={FLOW_ROOT, STDLIB_ROOT},
                example="stdlib:schemas/rally_turn_result.schema.json",
            )

            self.assertEqual(
                resolve_rooted_path(
                    stdlib_path,
                    workspace_root=workspace_root,
                    flow_root=flow_root,
                    framework_root=framework_root,
                    context="stdlib schema",
                ),
                framework_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json",
            )

    def test_parse_workspace_and_host_paths(self) -> None:
        workspace_path = parse_rooted_path(
            "workspace:fixtures/demo.txt",
            context="workspace file",
            allowed_roots={WORKSPACE_ROOT, HOST_ROOT},
            example="workspace:fixtures/demo.txt",
        )
        host_path = parse_rooted_path(
            "host:/tmp/demo.txt",
            context="host file",
            allowed_roots={WORKSPACE_ROOT, HOST_ROOT},
            example="host:~/demo.txt",
        )

        self.assertEqual(workspace_path, RootedPath(root="workspace", path_text="fixtures/demo.txt"))
        self.assertEqual(host_path, RootedPath(root="host", path_text="/tmp/demo.txt"))

    def test_rejects_bare_relative_paths(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "rooted Rally path"):
            parse_rooted_path(
                "issue.md",
                context="prompt path",
                allowed_roots={HOME_ROOT},
                example="home:issue.md",
            )

    def test_rejects_unknown_roots(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "must start with one of"):
            parse_rooted_path(
                "tmp:issue.md",
                context="prompt path",
                allowed_roots={HOME_ROOT},
                example="home:issue.md",
            )

    def test_rejects_escape_attempts(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "must not escape its root"):
            parse_rooted_path(
                "flow:../outside.json",
                context="schema file",
                allowed_roots={FLOW_ROOT},
                example="flow:schemas/review.schema.json",
            )

    def test_rejects_relative_host_paths(self) -> None:
        with self.assertRaisesRegex(RallyConfigError, "absolute path or `~/...`"):
            parse_rooted_path(
                "host:../outside",
                context="host file",
                allowed_roots={HOST_ROOT},
                example="host:~/outside",
            )

    def test_expand_rooted_value_walks_nested_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            run_home = workspace_root / "runs" / "DMO-1" / "home"

            payload = {
                "args": ["--repo", "home:repos/demo_repo"],
                "cwd": "workspace:fixtures/mcp",
            }

            self.assertEqual(
                expand_rooted_value(
                    payload,
                    workspace_root=workspace_root,
                    flow_root=flow_root,
                    run_home=run_home,
                    context="mcp payload",
                ),
                {
                    "args": ["--repo", str(run_home / "repos" / "demo_repo")],
                    "cwd": str(workspace_root / "fixtures" / "mcp"),
                },
            )


if __name__ == "__main__":
    unittest.main()

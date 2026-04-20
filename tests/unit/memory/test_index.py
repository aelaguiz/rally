from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from rally.errors import RallyStateError
from rally.memory.index import refresh_memory_index, search_memory_index
from rally.memory.models import MemoryScope
from rally.memory.store import save_memory_entry


class MemoryIndexTests(unittest.TestCase):
    def test_refresh_memory_index_uses_repo_local_bridge_and_cache_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            bridge_script = repo_root / "tools" / "qmd_bridge" / "main.mjs"
            bridge_script.parent.mkdir(parents=True, exist_ok=True)
            bridge_script.write_text("// bridge\n", encoding="utf-8")
            scope = MemoryScope(flow_code="POM", agent_slug="poem_writer")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "collections": 1,
                            "indexed": 1,
                            "updated": 0,
                            "unchanged": 0,
                            "removed": 0,
                            "needsEmbedding": 0,
                            "docsProcessed": 0,
                            "chunksEmbedded": 0,
                            "embedErrors": 0,
                        }
                    ),
                    stderr="",
                )

            result = refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)

            self.assertEqual(result.indexed, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["command"], ["node", str(bridge_script), "refresh"])
            self.assertEqual(calls[0]["kwargs"]["cwd"], repo_root / "tools" / "qmd_bridge")
            self.assertEqual(
                calls[0]["kwargs"]["env"]["XDG_CACHE_HOME"],
                str(repo_root / "runs" / "memory" / "qmd" / "cache"),
            )
            payload = json.loads(calls[0]["kwargs"]["input"])
            self.assertEqual(payload["collectionName"], "mem_pom_poem_writer")
            self.assertEqual(
                payload["collectionPath"],
                str(repo_root / "runs" / "memory" / "entries" / "POM" / "poem_writer"),
            )

    def test_search_memory_index_parses_bridge_hits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            bridge_script = repo_root / "tools" / "qmd_bridge" / "main.mjs"
            bridge_script.parent.mkdir(parents=True, exist_ok=True)
            bridge_script.write_text("// bridge\n", encoding="utf-8")
            scope = MemoryScope(flow_code="POM", agent_slug="poem_writer")
            save_memory_entry(
                repo_root=repo_root,
                scope=scope,
                run_id="POM-7",
                memory_markdown=(
                    "# Lesson\n"
                    "Focus the revision.\n\n"
                    "# When This Matters\n"
                    "Use this after a vague critique when the poem still needs one concrete next step.\n\n"
                    "# What To Do\n"
                    "Ask for one clear target before you ask for a rewrite.\n"
                ),
            )

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del kwargs
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=(
                        "Downloading model metadata...\n"
                        + json.dumps(
                            {
                                "results": [
                                    {
                                        "memoryId": "mem-pom-poem-writer-focus-the-revision",
                                        "path": "qmd:/mem_pom_poem_writer/mem-pom-poem-writer-focus-the-revision.md",
                                        "title": "Lesson",
                                        "snippet": (
                                            "--- id: \"mem_pom_poem_writer_focus_the_revision\" "
                                            "flow_code: \"POM\" agent_slug: \"poem_writer\" ---"
                                        ),
                                        "score": 0.87,
                                    }
                                ]
                            }
                        )
                    ),
                    stderr="",
                )

            hits = search_memory_index(
                repo_root=repo_root,
                scope=scope,
                query="clear revision target",
                subprocess_run=fake_run,
            )

            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].memory_id, "mem_pom_poem_writer_focus_the_revision")
            self.assertEqual(hits[0].title, "Focus the revision.")
            self.assertEqual(
                hits[0].snippet,
                "Use this after a vague critique when the poem still needs one concrete next step.",
            )
            self.assertEqual(hits[0].score, 0.87)

    def test_refresh_memory_index_accepts_log_lines_before_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            bridge_script = repo_root / "tools" / "qmd_bridge" / "main.mjs"
            bridge_script.parent.mkdir(parents=True, exist_ok=True)
            bridge_script.write_text("// bridge\n", encoding="utf-8")
            scope = MemoryScope(flow_code="POM", agent_slug="poem_writer")

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del kwargs
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=(
                        "warming qmd...\n"
                        + json.dumps(
                            {
                                "collections": 1,
                                "indexed": 1,
                                "updated": 0,
                                "unchanged": 0,
                                "removed": 0,
                                "needsEmbedding": 0,
                                "docsProcessed": 0,
                                "chunksEmbedded": 0,
                                "embedErrors": 0,
                            }
                        )
                    ),
                    stderr="",
                )

            result = refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)

            self.assertEqual(result.collections, 1)
            self.assertEqual(result.indexed, 1)


class MemoryIndexBridgeFailureTests(unittest.TestCase):
    # Protects every RallyStateError branch in `_run_bridge` and
    # `_decode_bridge_output`. The QMD bridge is a Node subprocess invoked
    # synchronously from every agent's memory.search / memory.refresh call.
    # If any of these failure paths silently regresses (e.g., an unhandled
    # error crashes the runner instead of raising RallyStateError with
    # diagnostic detail), the operator-visible symptom is an agent that
    # crashes mid-turn with no useful message — memory bugs are already hard
    # to diagnose; losing the error text compounds that.
    #
    # IMPORTANT: `_run_bridge` passes no `timeout=` kwarg to `subprocess_run`,
    # so a hung QMD bridge will block Rally indefinitely. That is a real risk
    # but outside RF6 scope — RF6 is P2 and the audit-loop directive preferred
    # proof-only. Tests below lock in the current failure-mode behavior; the
    # hang-guard remains a documented risk in the audit ledger.

    def _scope(self) -> MemoryScope:
        return MemoryScope(flow_code="POM", agent_slug="poem_writer")

    def _prepare_repo(self, temp_dir: str) -> Path:
        repo_root = Path(temp_dir).resolve()
        bridge_script = repo_root / "tools" / "qmd_bridge" / "main.mjs"
        bridge_script.parent.mkdir(parents=True, exist_ok=True)
        bridge_script.write_text("// bridge\n", encoding="utf-8")
        return repo_root

    def _seed_memory_entry(self, repo_root: Path, scope: MemoryScope) -> None:
        save_memory_entry(
            repo_root=repo_root,
            scope=scope,
            run_id="POM-1",
            memory_markdown=(
                "# Lesson\n"
                "Pin the lens.\n\n"
                "# When This Matters\n"
                "When a reader cannot tell which verse earns the title.\n\n"
                "# What To Do\n"
                "Name the lens in the first two lines.\n"
            ),
        )

    def test_missing_bridge_script_raises_with_path_in_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            # No bridge script created on purpose.
            scope = self._scope()

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(
                    repo_root=repo_root,
                    scope=scope,
                    subprocess_run=lambda *a, **kw: self.fail("subprocess must not run when bridge is missing"),
                )
            self.assertIn("QMD bridge script is missing", str(ctx.exception))
            self.assertIn("tools/qmd_bridge/main.mjs", str(ctx.exception).replace("\\", "/"))

    def test_os_error_on_subprocess_spawn_is_translated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def raise_os_error(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                raise OSError("node binary not found")

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(
                    repo_root=repo_root,
                    scope=scope,
                    subprocess_run=raise_os_error,
                )
            self.assertIn("Failed to start the QMD bridge", str(ctx.exception))
            self.assertIn("refresh", str(ctx.exception))
            self.assertIn("node binary not found", str(ctx.exception))

    def test_non_zero_exit_uses_stderr_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=2,
                    stdout="",
                    stderr="qmd: embedding provider unreachable\n",
                )

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)
            self.assertIn("QMD bridge `refresh` failed", str(ctx.exception))
            self.assertIn("embedding provider unreachable", str(ctx.exception))

    def test_non_zero_exit_falls_back_to_stdout_when_stderr_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="bad manifest\n",
                    stderr="",
                )

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)
            self.assertIn("bad manifest", str(ctx.exception))

    def test_non_zero_exit_with_no_detail_uses_generic_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="")

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)
            self.assertIn("unknown QMD bridge failure", str(ctx.exception))

    def test_empty_stdout_on_success_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)
            self.assertIn("returned empty output", str(ctx.exception))

    def test_malformed_json_stdout_raises_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="qmd warming...\nstill warming\nnot json at all\n",
                    stderr="",
                )

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)
            self.assertIn("returned invalid JSON", str(ctx.exception))

    def test_json_that_is_not_a_dict_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="[1, 2, 3]\n",
                    stderr="",
                )

            with self.assertRaises(RallyStateError) as ctx:
                refresh_memory_index(repo_root=repo_root, scope=scope, subprocess_run=fake_run)
            self.assertIn("must return a JSON object", str(ctx.exception))

    def test_search_with_empty_query_raises_without_running_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            with self.assertRaises(RallyStateError) as ctx:
                search_memory_index(
                    repo_root=repo_root,
                    scope=scope,
                    query="   ",
                    subprocess_run=lambda *a, **kw: self.fail("subprocess must not run for empty query"),
                )
            self.assertIn("must not be empty", str(ctx.exception))

    def test_search_with_no_entries_returns_empty_without_running_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()

            hits = search_memory_index(
                repo_root=repo_root,
                scope=scope,
                query="anything",
                subprocess_run=lambda *a, **kw: self.fail("subprocess must not run when entries_dir is empty"),
            )
            self.assertEqual(hits, ())

    def test_search_response_missing_results_field_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()
            self._seed_memory_entry(repo_root, scope)

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=json.dumps({"not_results": []}),
                    stderr="",
                )

            with self.assertRaises(RallyStateError) as ctx:
                search_memory_index(
                    repo_root=repo_root,
                    scope=scope,
                    query="lens",
                    subprocess_run=fake_run,
                )
            self.assertIn("missing `results`", str(ctx.exception))

    def test_search_response_with_non_dict_item_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._prepare_repo(temp_dir)
            scope = self._scope()
            self._seed_memory_entry(repo_root, scope)

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=json.dumps({"results": ["not a dict"]}),
                    stderr="",
                )

            with self.assertRaises(RallyStateError) as ctx:
                search_memory_index(
                    repo_root=repo_root,
                    scope=scope,
                    query="lens",
                    subprocess_run=fake_run,
                )
            self.assertIn("search results must be JSON objects", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

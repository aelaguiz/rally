from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from rally.domain.memory import MemoryScope
from rally.services.memory_store import save_memory_entry
from rally.services.memory_index import refresh_memory_index, search_memory_index


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
            self.assertEqual(
                calls[0]["command"],
                ["node", str(bridge_script), "refresh"],
            )
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
            entry = save_memory_entry(
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
            ).entry

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


if __name__ == "__main__":
    unittest.main()

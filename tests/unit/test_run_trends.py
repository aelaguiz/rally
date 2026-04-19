from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rally.services.run_trends import show_run_trends


def _row(
    *,
    run_id: str,
    flow_code: str,
    wall_ms: int,
    active_ms: int,
    tools_called: int = 10,
    errors: int = 0,
    output_tokens: int = 1000,
    cache_read_input_tokens: int = 0,
    ts: str = "2026-04-01T00:00:00Z",
    run_status: str = "done",
) -> dict:
    return {
        "run_id": run_id,
        "flow_code": flow_code,
        "run_status": run_status,
        "last_turn_index": 1,
        "wall_ms": wall_ms,
        "active_ms": active_ms,
        "idle_ms": max(wall_ms - active_ms, 0),
        "setup_ms": 0,
        "tokens": {
            "input_tokens": 0,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read_input_tokens,
            "cache_creation_input_tokens": 0,
        },
        "tools_called": tools_called,
        "errors": errors,
        "ts": ts,
    }


def _write_rows(repo_root: Path, rows: list[dict]) -> None:
    path = repo_root / "runs"
    path.mkdir(parents=True, exist_ok=True)
    target = path / "timings.ndjson"
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


class RunTrendsTests(unittest.TestCase):
    def test_reports_missing_file_friendly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = show_run_trends(repo_root=Path(tmp))
            self.assertIn("No completed Rally runs", result.message)
            self.assertIn("rally run", result.message)

    def test_reports_empty_file_with_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), [])
            result = show_run_trends(repo_root=Path(tmp), flow_code="CUR")
            self.assertIn("No completed Rally runs", result.message)
            self.assertIn("CUR", result.message)

    def test_renders_recent_runs_and_stats(self) -> None:
        rows = [
            _row(run_id="CUR-1", flow_code="CUR", wall_ms=60_000, active_ms=30_000,
                 ts="2026-04-01T00:00:00Z"),
            _row(run_id="CUR-2", flow_code="CUR", wall_ms=120_000, active_ms=80_000,
                 ts="2026-04-02T00:00:00Z"),
            _row(run_id="CUR-3", flow_code="CUR", wall_ms=240_000, active_ms=200_000,
                 errors=5, ts="2026-04-03T00:00:00Z"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), rows)
            result = show_run_trends(repo_root=Path(tmp))

            self.assertIn("Recent runs:", result.message)
            self.assertIn("CUR-1", result.message)
            self.assertIn("CUR-3", result.message)
            self.assertIn("Stats:", result.message)
            self.assertIn("p50", result.message)
            self.assertIn("p90", result.message)

    def test_filters_by_flow(self) -> None:
        rows = [
            _row(run_id="CUR-1", flow_code="CUR", wall_ms=60_000, active_ms=30_000),
            _row(run_id="DMO-1", flow_code="DMO", wall_ms=500_000, active_ms=100_000),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), rows)
            result = show_run_trends(repo_root=Path(tmp), flow_code="CUR")
            self.assertIn("CUR-1", result.message)
            self.assertNotIn("DMO-1", result.message)

    def test_filter_is_case_insensitive(self) -> None:
        rows = [_row(run_id="CUR-1", flow_code="CUR", wall_ms=1_000, active_ms=1_000)]
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), rows)
            result = show_run_trends(repo_root=Path(tmp), flow_code="cur")
            self.assertIn("CUR-1", result.message)

    def test_last_limits_recent_runs_window(self) -> None:
        rows = [
            _row(
                run_id=f"CUR-{n}",
                flow_code="CUR",
                wall_ms=60_000 + n,
                active_ms=30_000,
                ts=f"2026-04-{n:02d}T00:00:00Z",
            )
            for n in range(1, 11)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), rows)
            result = show_run_trends(repo_root=Path(tmp), limit=3)
            self.assertIn("CUR-10", result.message)
            self.assertIn("CUR-9", result.message)
            self.assertIn("CUR-8", result.message)
            self.assertNotIn("CUR-1 ", result.message)

    def test_unlimited_when_limit_is_none(self) -> None:
        rows = [
            _row(
                run_id=f"CUR-{n}",
                flow_code="CUR",
                wall_ms=1_000,
                active_ms=1_000,
                ts=f"2026-04-{n:02d}T00:00:00Z",
            )
            for n in range(1, 6)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), rows)
            result = show_run_trends(repo_root=Path(tmp), limit=None)
            for n in range(1, 6):
                self.assertIn(f"CUR-{n}", result.message)

    def test_percentile_matches_median_for_odd_sample(self) -> None:
        rows = [
            _row(run_id=f"CUR-{n}", flow_code="CUR", wall_ms=n * 1000, active_ms=n * 1000,
                 ts=f"2026-04-{n:02d}T00:00:00Z")
            for n in range(1, 6)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_rows(Path(tmp), rows)
            result = show_run_trends(repo_root=Path(tmp))
            self.assertIn("p50", result.message)
            # median wall of {1s,2s,3s,4s,5s} is 3s
            self.assertIn("3.0s", result.message)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

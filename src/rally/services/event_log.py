from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping


def append_event(
    *,
    run_dir: Path,
    event_type: str,
    payload: Mapping[str, object],
    now: datetime | None = None,
) -> Path:
    log_file = run_dir / "logs" / "events.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "type": event_type,
        "payload": dict(payload),
    }
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True))
        handle.write("\n")
    return log_file

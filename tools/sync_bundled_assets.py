from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.bundled_assets import sync_bundled_assets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync Rally-owned bundled assets into src/rally/_bundled.")
    parser.add_argument("--check", action="store_true", help="Fail if src/rally/_bundled is stale.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        differences = sync_bundled_assets(repo_root=repo_root, check=args.check)
    except RallyConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.check and differences:
        print("Bundled assets are stale:", file=sys.stderr)
        for difference in differences:
            print(f"- {difference}", file=sys.stderr)
        return 1

    if not args.check:
        print("Bundled assets synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# >>> AUTO-GEN BEGIN: Transit Preflight CLI v1.0
from __future__ import annotations

import argparse
import os
from typing import List, Optional

from astroengine.dev.preflight import preflight_transit_engine


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("astroengine-codex-preflight")
    parser.add_argument("command", choices=["preflight-transit"], help="Which preflight to run")
    parser.add_argument("--repo-root", default=os.getcwd())
    args = parser.parse_args(argv)

    if args.command == "preflight-transit":
        report = preflight_transit_engine(args.repo_root)
        for skipped in report.skipped:
            print(f"SKIP  {skipped}")
        for action in report.actions:
            print(f"WRITE {action}")
        for diff in report.diffs:
            if diff:
                print(diff)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: Transit Preflight CLI v1.0

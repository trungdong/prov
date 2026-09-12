"""Compare a pytest-benchmark JSON run against a committed baseline.

Usage: ``python benchmarks/compare.py BASELINE CURRENT [--max-regression 0.20]``

Exits 1 if any benchmark's mean is slower than the baseline mean by more
than the threshold. Benchmarks present on only one side are reported and
ignored, so adding a benchmark never fails the gate on its own.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text())
    return {b["fullname"]: b["stats"]["mean"] for b in data["benchmarks"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--max-regression", type=float, default=0.20)
    args = parser.parse_args(argv)

    base, cur = load(args.baseline), load(args.current)
    failed = False
    print(f"{'benchmark':60} {'baseline':>10} {'current':>10} {'change':>8}")
    for name in sorted(base.keys() | cur.keys()):
        if name not in base or name not in cur:
            side = "baseline" if name in base else "current"
            print(f"{name:60} only in {side}")
            continue
        change = (cur[name] - base[name]) / base[name]
        flag = ""
        if change > args.max_regression:
            failed = True
            flag = "  REGRESSION"
        print(f"{name:60} {base[name]:10.4f} {cur[name]:10.4f} {change:+7.1%}{flag}")
    print("REGRESSION" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""Measure a base ref and the working tree on one machine and compare them.

Usage: ``python benchmarks/ab.py BASE_REF [--passes 2] [--threshold 0.10]``

The base ref is checked out into a temporary git worktree with its own
locked environment, so a dependency change counts as part of the change
measured. Both sides run this checkout's ``test_bench.py``, in alternating
passes, and the fastest round per benchmark represents each side. Exits 1
if any benchmark is slower on the working tree by more than the threshold.
Benchmarks that ran on one side only are reported and ignored.

``--from-json BASE HEAD`` compares two saved pytest-benchmark runs instead.
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

HEAD_TREE = Path(__file__).resolve().parent.parent
SUITE = HEAD_TREE / "benchmarks" / "test_bench.py"
UV_RUN = (
    *("uv", "run", "--locked"),
    *("--extra", "rdf", "--extra", "xml", "--extra", "dot", "--extra", "graph"),
    *("--group", "bench"),
)
PYTEST_OPTIONS = (
    "-q",
    "--disable-warnings",
    "-p",
    "no:cacheprovider",
    "--benchmark-disable-gc",
    "--benchmark-warmup=on",
    "--benchmark-warmup-iterations=1",
    "--benchmark-min-rounds=3",
    "--benchmark-max-time=0.5",
    "--benchmark-columns=min,median,rounds",
)


@dataclass(frozen=True)
class Row:
    name: str
    base: float | None
    head: float | None
    threshold: float

    @property
    def change(self) -> float | None:
        if self.base is None or self.head is None:
            return None
        return (self.head - self.base) / self.base

    @property
    def regressed(self) -> bool:
        return self.change is not None and self.change > self.threshold


def load_minimums(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text())
    return {b["fullname"]: b["stats"]["min"] for b in data["benchmarks"]}


def fastest(passes: list[dict[str, float]]) -> dict[str, float]:
    names = {name for readings in passes for name in readings}
    return {n: min(p[n] for p in passes if n in p) for n in names}


def compare(
    base: dict[str, float], head: dict[str, float], threshold: float
) -> list[Row]:
    return [
        Row(name, base.get(name), head.get(name), threshold)
        for name in sorted(base.keys() | head.keys())
    ]


def check_measured_tree(run: Path, tree: Path) -> None:
    """Exit unless the run imported ``prov`` from ``tree``."""
    measured = Path(json.loads(run.read_text())["prov_path"]).resolve()
    if not measured.is_relative_to(tree.resolve()):
        sys.exit(f"{run.name} measured {measured}, expected a path under {tree}")


def report(rows: list[Row]) -> int:
    def seconds(value: float | None) -> str:
        return f"{'-':>10}" if value is None else f"{value:10.4f}"

    print(f"{'benchmark':60} {'base min':>10} {'head min':>10} {'change':>8}")
    for row in rows:
        if row.change is None:
            note = "  only in " + ("base" if row.head is None else "head")
        else:
            note = f" {row.change:+7.1%}" + ("  REGRESSION" if row.regressed else "")
        print(f"{row.name:60} {seconds(row.base)} {seconds(row.head)}{note}")
    failed = any(row.regressed for row in rows)
    print("REGRESSION" if failed else "OK")
    return 1 if failed else 0


@contextmanager
def worktree(ref: str) -> Generator[Path]:
    with tempfile.TemporaryDirectory(prefix="prov-bench-") as tmp:
        tree = Path(tmp) / "base"
        git = ("git", "-C", str(HEAD_TREE))
        add = (*git, "worktree", "add", "--detach", str(tree), ref)
        subprocess.run(add, check=True)  # nosec B603 - nosemgrep
        try:
            yield tree
        finally:
            remove = (*git, "worktree", "remove", "--force", str(tree))
            subprocess.run(remove, check=False)  # nosec B603 - nosemgrep


def run_suite(tree: Path, output: Path) -> bool:
    """Time the suite against ``tree``'s source and environment."""
    pytest = ("pytest", str(SUITE), *PYTEST_OPTIONS, f"--benchmark-json={output}")
    command = (*UV_RUN, "--project", str(tree), *pytest)
    done = subprocess.run(command, cwd=HEAD_TREE, check=False)  # nosec B603 - nosemgrep
    if not output.exists() or not output.read_text().strip():
        sys.exit(f"pytest wrote no benchmark results for {tree}")
    check_measured_tree(output, tree)
    return done.returncode == 0


def measure(base_ref: str, passes: int) -> tuple[dict[str, float], dict[str, float]]:
    readings: dict[str, list[dict[str, float]]] = {"base": [], "head": []}
    with worktree(base_ref) as base_tree:
        for number in range(1, passes + 1):
            for side, tree in (("base", base_tree), ("head", HEAD_TREE)):
                print(f"\n== pass {number} of {passes}: {side} ==", flush=True)
                output = base_tree.parent / f"{side}-{number}.json"
                passed = run_suite(tree, output)

                # A benchmark of a new feature cannot pass on the base.
                if not passed and side == "head":
                    sys.exit("the benchmark suite failed on the working tree")
                readings[side].append(load_minimums(output))
    return fastest(readings["base"]), fastest(readings["head"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base_ref", nargs="?", help="git ref to compare against")
    parser.add_argument("--from-json", nargs=2, type=Path, metavar=("BASE", "HEAD"))
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--threshold", type=float, default=0.10)
    args = parser.parse_args(argv)

    if args.from_json:
        base, head = (load_minimums(path) for path in args.from_json)
    elif args.base_ref:
        base, head = measure(args.base_ref, args.passes)
    else:
        parser.error("give a base ref or --from-json")
    return report(compare(base, head, args.threshold))


if __name__ == "__main__":
    sys.exit(main())

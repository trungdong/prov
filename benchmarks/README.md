# Benchmarks

Timing suite for the operations the library's performance work tracks. It is
not part of the test suite and is not shipped.

```bash
uv sync --extra rdf --extra xml --extra dot --extra graph --group dev --group bench
uv run pytest benchmarks/test_bench.py
```

`PROV_BENCH_N` sets the record count (default 10000).

## Comparing two versions

`ab.py` measures a base ref and the working tree on one machine and compares
them. Timings from different machines, or from one machine an hour apart, are
not comparable, and CI runners alone differ in speed by up to a factor of two.

```bash
uv run python benchmarks/ab.py main           # the working tree against main
uv run python benchmarks/ab.py 3.2.2          # against a release tag
uv run python benchmarks/ab.py main --passes 4 --threshold 0.05
```

The script checks the base ref out into a temporary git worktree with its own
locked environment, so a dependency change counts as part of the change
measured. Both sides run the working tree's `test_bench.py`, in alternating
passes, so a slow spell on the machine falls on both. The fastest round per
benchmark represents each side, because interference only ever adds time. The
script exits 1 when a benchmark is more than 10% slower on the working tree.
An unchanged tree reads within about 2% of itself on a quiet machine.

Uncommitted changes in the working tree are measured. Close other applications
first, and on a laptop run on mains power.

CI runs `ab.py HEAD^1` on every push and pull request as a non-blocking job. A
red job is a prompt to repeat the comparison locally, not proof of a
regression.

Run the tests of the comparison logic with `uv run pytest benchmarks/test_ab.py`.

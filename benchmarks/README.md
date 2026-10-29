# Benchmarks

Timing suite for the operations the library's performance work tracks. It is
not part of the test suite and is not shipped.

```bash
uv sync --extra rdf --extra xml --extra dot --extra graph --group bench --group docs
uv run pytest benchmarks/test_bench.py
```

`PROV_BENCH_N` sets the record count (default 10000).

## Comparing two versions

`ab.py` measures a base ref and the working tree on one machine and compares
them. Timings from different machines, or from one machine an hour apart, are
not comparable, and CI runners alone differ in speed by up to a factor of two.

```bash
uv run python benchmarks/ab.py main --python 3.12    # the working tree against main
uv run python benchmarks/ab.py 3.2.2 --python 3.12   # against a release tag
uv run python benchmarks/ab.py main --python 3.12 --passes 4 --threshold 0.05
uv run python benchmarks/ab.py 3.2.3 --python 3.12 --gc   # with garbage collection on
```

Both sides must run on the same interpreter, and the script stops if they did
not. The working tree's environment keeps the interpreter of the last
`uv run --python`, which after the test loop over every supported interpreter
is PyPy, while the base gets uv's default. `--python` pins both sides.

`ab.py` times with garbage collection off on both sides (pytest-benchmark's
`--benchmark-disable-gc`), so a collector pause cannot fall in one round and
not another. A real workload pays those pauses. With collection on,
construction, the PROV-JSON read, `unified()` and `prov_to_graph()` take 10 to
43% longer on Python 3.11 and 3.12 (#693). `--gc` leaves collection on for both
sides. A plain `pytest` run, as in the first block, leaves it on.

The script checks the base ref out into a temporary git worktree with its own
locked environment, so a dependency change counts as part of the change
measured. Both sides run the working tree's `test_bench.py`, in alternating
passes, so a slow spell on the machine falls on both. The fastest round per
benchmark represents each side, because interference only ever adds time.

A process now and then runs one benchmark in a faster mode. On a CI runner
`test_equality` does so in about one pass in ten, by about 20%, and the
fastest round then misstates that side. A result over the threshold therefore
earns one confirmation pass per side, and the median of each side's per-pass
minimums decides, so one odd pass cannot fail the run. The script exits 1 when
a benchmark is still more than 10% slower on the working tree. An unchanged
tree reads within about 2% of itself on a quiet machine.

Uncommitted changes in the working tree are measured. Close other applications
first, and on a laptop run on mains power.

CI runs `ab.py HEAD^1` on every push and pull request as a non-blocking job. A
red job is a prompt to repeat the comparison locally, not proof of a
regression.

Run the tests of the comparison logic with `uv run pytest benchmarks/test_ab.py`.

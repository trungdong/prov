# Benchmarks

Timing suite for the operations the library's performance work tracks. It is
not part of the test suite and is not shipped.

```bash
uv sync --extra rdf --extra xml --extra dot --extra graph --group dev --group bench
uv run pytest benchmarks/ --benchmark-json=/tmp/bench.json
uv run python benchmarks/compare.py benchmarks/baseline.json /tmp/bench.json
```

`PROV_BENCH_N` sets the record count (default 10000). CI runs the suite on
every push as a non-blocking job and fails it on a 20% mean regression against
`baseline.json`.

## Refreshing the baseline

Do this whenever a change is meant to alter speed. Run the CI workflow by hand
so the baseline comes from the runner type CI compares on:

```bash
gh workflow run CI.yml
gh run watch
gh run download --name benchmark-baseline --dir /tmp/bench
cp /tmp/bench/bench.json benchmarks/baseline.json
```

Commit the new baseline in the same PR as the change that motivated it.

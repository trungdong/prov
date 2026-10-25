# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

`prov` is a Python implementation of the W3C PROV Data Model. Downstream projects depend on it, so
treat the public API with care.

## Roadmap and planning

`ROADMAP.md` is the release plan and current status — check it rather than assuming from
memory of past work. Design specs live under `planning/specs/` and are committed;
`planning/README.md` says how to read them (a historical record, status lines kept current).
Implementation plans and their `*.tasks.json` execution state live under
`planning/plans/`, which is gitignored: plans are local working files and are never
committed. Neither goes in `docs/`. Durable rules:

- One focused PR per roadmap step, green CI before merge.
- If a step changes tooling, update the affected sections of this file in the same PR.

## Releasing

`docs/releasing.md` is the runbook, from a green `main` to PyPI and conda-forge. Read it
before starting release work, and add any new gotcha there rather than to a plan.

## Setup

Uses `uv`. RDF/XML support and graphical/graph interop (`dot`, `graph`) are optional
extras — without them many tests fail with `ModuleNotFoundError`:

```bash
uv sync --extra rdf --extra xml --extra dot --extra graph --group bench
```

Sphinx docs need the `docs` group plus all four extras (autodoc imports the serializers
and `prov.dot`/`prov.graph`). CI's `docs` job builds with `-W -n`, so every warning and
every unresolved cross-reference fails; `nitpick_ignore` in `docs/conf.py` lists the
private names public annotations expose. The build command is in the gates below.

```bash
uv sync --group docs --extra rdf --extra xml --extra dot --extra graph
```

`docs/dependencies.md` explains every dependency pin, including the `numpy<2.5` constraint
needed for `mypy --strict` (transitive via `types-networkx`/`matplotlib`).

## Gates every PR must pass

`CONTRIBUTING.md` step 6 is the canonical list; change both together.

```bash
# All supported interpreters (matches the CI matrix). "cpython3.11" stops uv from
# reusing a PyPy 3.11 environment left by the previous run.
for py in cpython3.11 3.12 3.13 3.14 3.15 pypy3.11; do
    uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest || break
done

uv run mypy src                  # strict, library and tests; configured in pyproject.toml
uv run ruff check src/ benchmarks/
uv run ruff format --check src/ benchmarks/
codacy-analysis analyze --files <changed files>   # expect "0 issues found"
git worktree add --detach /tmp/prov-min HEAD && (cd /tmp/prov-min && uv sync --locked --group dev && uv run --no-sync pytest src/prov/tests/test_minimal_install.py); rc=$?; git worktree remove --force /tmp/prov-min; (exit $rc)   # when conftest.py or an import changed
uv run --group docs --extra rdf --extra xml --extra dot --extra graph sphinx-build -W -n -b html docs docs/_build/html   # when a docstring or a page changed
```

mypy checks the tests under the same strict configuration as the library. Test modules that
do not pass yet are listed in the `[[tool.mypy.overrides]]` block in `pyproject.toml` with
`ignore_errors = true`. The list only shrinks. A PR that makes a module pass deletes its
name from the block and from `MYPY_OVERRIDE_LIST` in `src/prov/tests/test_public_api.py`, and
`test_mypy_override_list_only_shrinks` fails if the two differ. A new test module never joins
the list. The PR that empties the list deletes the block, the snapshot and that test.

Codacy analyses every PR on GitHub, markdownlint on Markdown files included, but does not
block a merge. The maintainer reviews its findings by hand and merges with none outstanding.
Run the local analyser on every changed file before pushing. Coveralls
is advisory as long as `uv run coverage report` stays above the 97% floor. CI also runs a
non-blocking `own-warnings` job that fails if `prov` raises a `DeprecationWarning`,
`PendingDeprecationWarning` or `FutureWarning` of its own on the newest interpreter
(#340, #441).

Performance changes also run `uv run python benchmarks/ab.py main --python 3.12`, which
times `main` and the working tree on the same machine and fails on a 10% slowdown that
survives a confirmation pass. `--python` matters after the interpreter loop above, which
leaves the environment on PyPy. CI runs the same script against the first parent of `HEAD`
as a non-blocking job; repeat a red result locally before acting on it. There is no
committed baseline. `benchmarks/README.md` has the details.

## Commits and PRs

- Merge commits, never squash; one focused PR per change with a body that says what and why.
- Commit-message and PR-body paragraphs stay unwrapped (one line each); GitHub soft-wraps.
- No AI attribution lines in commits or PR bodies.
- British English in shipped documentation and changelog text; describe changes by release,
  never by plan task or batch.
- **Maintainability governs.** Added functionality keeps complexity as low as it can be.
  Removed behaviour comes with less code and fewer or consolidated tests, never more. Neither
  is bought with a loss of correctness. A change that simplifies and a change that breaks a
  round trip are two changes, and only the first merges. What got simpler and what got more
  complex, with Lizard CCN and line counts where they moved, goes in the plan's complexity
  ledger and in the report to the maintainer, never in the PR body.

## Architecture

`docs/explanation/architecture.md` is the overview (layers, object model, registry and
auto-detection, extras); `docs/development.md` holds the PROV-N parser internals, the
serializer conventions and the test-suite layout. The rules below are what an agent must
not break.

- **Always import from `prov.model`, never from its submodules.** `prov/model/__init__.py`
  re-exports every public name at its historic location and deletes the submodule
  attributes, and `test_public_api.py` freezes `dir(prov.model)`.
- `prov.graph` and `prov.dot` sit behind the `graph` and `dot` extras and raise
  `ModuleNotFoundError` naming the extra when imported without it.
- `prov.serializers.Registry`'s insertion order is `json, rdf, provn, xml, jsonld`, with
  `jsonld` deliberately last: `prov.read()`'s auto-detection walks that order and
  `test_read_auto_detect_with_broken_tell_degrades_to_no_rewind` pins `json` as the first
  format tried on a non-seekable stream.
- New serializers follow the conventions in `docs/development.md` (Conventions for
  serializers): one error type carrying position, grammar clauses cited on the code,
  tables cross-checked against the model, records through `new_record()`, warnings emitted by
  the serializer.

## Tests (`src/prov/tests/`)

Pytest-native throughout: plain `assert`, module-level `test_*` functions, no
`unittest.TestCase`.

- No fixed pass/skip/xfail count is tracked here — it drifts every time a test is added and
  isn't CI-enforced. Instead, compare `uv run pytest -q -rsx` against the prior run: a skip or
  xfail that's new, gone, or unexplained by your own change is a regression worth investigating;
  one that matches an existing `reason=` tied to a tracked issue is routine.
- Known-lossy cases are permanent, documented limitations — don't "fix" them. RDF's PROV-O gap
  (`docs/reference/conformance.md`, #217) and PROV-JSONLD's missing Mention term (#248) each
  leave the affected target out of the scruffy or mention round trips in `test_statements.py`
  (`SCRUFFY_TARGETS`, `MENTION_TARGETS`); `test_rdf.py` and `test_jsonld.py` assert the raise.
- Shared coverage (`test_statements.py`, `test_attributes.py`, `test_qnames.py`,
  `test_examples.py`) runs once per target via the `roundtrip` fixture. `examples.py` (canonical
  example documents) and `attribute_values.py` (datatype corpus; order significant — some tests
  reference individual values by index) feed those and several other modules.
- `test_json.py`/`test_xml.py`/`test_rdf.py`/`test_jsonld.py` keep only format-specific tests
  (encoder internals, error paths, `find_diff`, fixture-dir round-trips).
- `strategies.py`/`test_property_roundtrip.py` — Hypothesis round-trip property over
  `ROUNDTRIP_FORMATS`; known-lossy constructs excluded at generation time with issue refs.
- `fixtures/written-by-3.2.3/` is written only by its `generate.py` under the published
  `prov==3.2.3` wheel, never by hand or by the working tree. A PR that appends to
  `examples.py` or `ATTRIBUTE_VALUES` reruns it.

New shared record types, attributes, or serializer behaviours go into the shared parametrized
modules so every target is exercised — not into per-format tests.

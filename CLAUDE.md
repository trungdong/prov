# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

`prov` is a Python implementation of the W3C PROV Data Model. Downstream projects depend on
it, so treat the public API with care.

## Roadmap and planning

`ROADMAP.md` is the release plan and current status; check it rather than assuming from past
work. Design specs are committed under `planning/specs/` and read as `planning/README.md`
says. Implementation plans and their `*.tasks.json` state live under `planning/plans/`, which
is gitignored and never committed. Neither goes in `docs/`.

- One focused PR per roadmap step, green CI before merge.
- If a step changes tooling, update the affected sections of this file in the same PR.

## Releasing

`docs/releasing.md` is the runbook, from a green `main` to PyPI and conda-forge. Read it
before release work, and add any new gotcha there rather than to a plan.

## Setup

Uses `uv`. The test suite needs all four extras, the benchmarks the `bench` group and Sphinx
the `docs` group:

```bash
uv sync --extra rdf --extra xml --extra dot --extra graph --group bench --group docs
```

The `pygments` extra (`prov.pygments`, the Pygments lexer) is in no sync command because
pytest already brings Pygments into every test environment. `docs/dependencies.md` explains
every pin.

## Gates every PR must pass

`CONTRIBUTING.md` (Checks every pull request must pass) holds the one list of commands and
the rules around them: the mypy override list that only shrinks, Codacy on every changed
file, the coverage floor and the Sphinx build. Run every applicable line before pushing.

Performance changes also run `uv run python benchmarks/ab.py main --python 3.12`. Repeat a
red CI benchmark locally before acting on it. `benchmarks/README.md` has the details.

## Commits and PRs

- Merge commits, never squash; one focused PR per change with a body that says what and why.
- Commit-message and PR-body paragraphs stay unwrapped (one line each); GitHub soft-wraps.
- No AI attribution lines in commits or PR bodies.
- Describe changes by release, never by plan task or batch. HISTORY entries follow
  `CONTRIBUTING.md` (Changelog entries); a refactor, a test or a CI change never gets one.
- **Maintainability governs.** Added functionality keeps complexity as low as it can be.
  Removed behaviour comes with less code and fewer or consolidated tests, never more. Neither
  is bought with a loss of correctness. A change that simplifies and a change that breaks a
  round trip are two changes, and only the first merges. What got simpler and what got more
  complex, with Lizard CCN and line counts where they moved, goes in the plan's complexity
  ledger and in the report to the maintainer, never in the PR body.

## Architecture

`docs/explanation/architecture.md` is the overview and `docs/development.md` holds the
serializer conventions and the test-suite layout. The PROV-N lexer and parser internals are
in the module docstrings of `provn_lexer.py` and `provn_parser.py`. The rules below are what
an agent must not break.

- **Always import from `prov.model`, never from its submodules.** `prov/model/__init__.py`
  re-exports every public name at its historic location and deletes the submodule
  attributes, and `test_public_api.py` freezes `dir(prov.model)`.
- `prov.graph` and `prov.dot` sit behind the `graph` and `dot` extras and raise
  `ModuleNotFoundError` naming the extra when imported without it.
- `prov.pygments` imports nothing from `prov`, because Pygments imports it on every plugin
  scan. `ProvNLexer` is reached by name through the entry point and is not public API.
  `docs/explanation/architecture.md` (Extras) explains the rule.
- `prov.serializers.Registry`'s insertion order is `json, rdf, provn, xml, jsonld`, with
  `jsonld` deliberately last: `prov.read()`'s auto-detection walks that order and
  `test_read_auto_detect_with_broken_tell_degrades_to_no_rewind` pins `json` as the first
  format tried on a non-seekable stream.
- New serializers follow `docs/development.md` (Conventions for serializers).

## Tests (`src/prov/tests/`)

Pytest-native throughout: plain `assert`, module-level `test_*` functions, no
`unittest.TestCase`.

- No fixed pass/skip/xfail count is tracked. Compare `uv run pytest -q -rsx` against the
  prior run. A skip or xfail that is new, gone or unexplained by your change is a regression;
  one that matches an existing `reason=` tied to a tracked issue is routine.
- Known-lossy cases are permanent, documented limitations; never "fix" them. RDF's PROV-O
  gap (`docs/reference/conformance.md`, #217) and PROV-JSONLD's missing Mention term (#248)
  each leave the affected target out of the scruffy or mention round trips in
  `test_statements.py` (`SCRUFFY_TARGETS`, `MENTION_TARGETS`); `test_rdf.py` and
  `test_jsonld.py` assert the raise.
- Shared coverage (`test_statements.py`, `test_attributes.py`, `test_qnames.py`,
  `test_examples.py`) runs once per target via the `roundtrip` fixture. `examples.py`
  (canonical example documents) and `attribute_values.py` (datatype corpus; order
  significant, some tests reference values by index) feed those and several other modules.
- `test_json.py`, `test_xml.py`, `test_rdf.py` and `test_jsonld.py` keep only
  format-specific tests (encoder internals, error paths, `find_diff`, fixture-dir
  round-trips).
- `strategies.py` and `test_property_roundtrip.py` hold the Hypothesis round-trip property
  over `ROUNDTRIP_FORMATS`; known-lossy constructs are excluded at generation time with
  issue refs.
- `fixtures/written-by-3.2.3/` is written only by its `generate.py` under the published
  `prov==3.2.3` wheel, never by hand or by the working tree. A PR that appends to
  `examples.py` or `ATTRIBUTE_VALUES` reruns it.

New shared record types, attributes or serializer behaviours go into the shared parametrised
modules so every target is exercised, never into per-format tests.

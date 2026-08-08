# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

`prov` is a Python implementation of the W3C PROV Data Model. Used by ProvStore, so treat the
public API with care.

## Modernisation roadmap

`ROADMAP.md` has current status — check it rather than assuming from memory of past work.
Design detail: `docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md`. Durable
rules, regardless of phase:

- One focused PR per roadmap step, green CI before merge.
- If a step changes tooling, update the affected sections of this file in the same PR.

## Releasing

`docs/releasing.md` is the runbook for cutting a release, from a green `main` to PyPI and
conda-forge — read it before starting release work. It is written for Claude Code to execute,
not for the published docs site, so it's excluded from the Sphinx build (`docs/conf.py`'s
`exclude_patterns`) and not in `docs/index.rst`'s toctree. If a release turns up a new gotcha,
add it to that file rather than to a plan document.

## Setup

Uses `uv`. RDF/XML support and graphical/graph interop (`dot`, `graph`) are optional
extras — without them many tests fail with `ModuleNotFoundError`:

```bash
uv sync --extra rdf --extra xml --extra dot --extra graph
```

Sphinx docs need the `docs` group plus all four extras (autodoc imports the serializers
and `prov.dot`/`prov.graph`):

```bash
uv sync --group docs --extra rdf --extra xml --extra dot --extra graph
uv run --group docs --extra rdf --extra xml --extra dot --extra graph sphinx-build -b html docs docs/_build/html
```

`docs/dependencies.md` explains every dependency pin, including the `numpy<2.5` constraint
needed for `mypy --strict` (transitive via `types-networkx`/`matplotlib`).

## Common commands

```bash
# All supported interpreters (matches CI matrix)
for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do
    uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest || break
done
```

## Architecture

### Core object model (`src/prov/model/` package)

- `__init__.py` — re-exports every public name at its historic `prov.model` location and then
  deletes the submodule attributes, freezing `dir(prov.model)` to the pre-split namespace.
  **Always import from `prov.model`, never from the submodules.**

`src/prov/constants.py` is the PROV vocabulary; all identifier↔class translation goes through it.
PROV-N is serialize-only — there is no PROV-N parser.

### Graph interop

Since 3.0.0.dev0 `src/prov/graph.py` and `src/prov/dot.py` sit behind extras (`graph`, `dot`)
— importing either without its extra raises `ModuleNotFoundError` naming the extra to install.

### Serializers

`prov.serializers.Registry`'s insertion order is `json, rdf, provn, xml, jsonld` — `jsonld`
(registry key for PROV-JSONLD) is deliberately appended last, since `prov.read()`'s
auto-detection walks that order and `test_read_auto_detect_with_broken_tell_degrades_to_no_rewind`
pins `json` as the first format tried on a non-seekable stream.

### Tests (`src/prov/tests/`)

Pytest-native throughout: plain `assert`, module-level `test_*` functions, no
`unittest.TestCase`. Design authority: `docs/superpowers/specs/2026-07-06-test-suite-redesign.md`.

- No fixed pass/skip/xfail count is tracked here — it drifts every time a test is added and
  isn't CI-enforced. Instead, compare `uv run pytest -q -rsx` against the prior run: a skip or
  xfail that's new, gone, or unexplained by your own change is a regression worth investigating;
  one that matches an existing `reason=` tied to a tracked issue is routine.
- Known-lossy cases are permanent, documented limitations — don't "fix" them. RDF's PROV-O gap
  (`docs/reference/conformance.md`, #217) and PROV-JSONLD's missing Mention term (#248) are each
  marked via `@pytest.mark.parametrize("fmt", [...])` on only the affected `fmt` param, in
  `test_statements.py`.
- Shared coverage (`test_statements.py`, `test_attributes.py`, `test_qnames.py`,
  `test_examples.py`) runs once per target via the `roundtrip` fixture. `examples.py` (canonical
  example documents) and `attribute_values.py` (datatype corpus; order significant — some tests
  reference individual values by index) feed those and several other modules.
- `test_json.py`/`test_xml.py`/`test_rdf.py`/`test_jsonld.py` keep only format-specific tests
  (encoder internals, error paths, `find_diff`, fixture-dir round-trips). `test_xml.py`'s
  disabled `_perform_round_trip` glob scaffold is intentional (design doc §4).
- `strategies.py`/`test_property_roundtrip.py` — Hypothesis round-trip property over
  `ROUNDTRIP_FORMATS`; known-lossy constructs excluded at generation time with issue refs.

New shared record types, attributes, or serializer behaviors go into the shared parametrized
modules so every target is exercised — not into per-format tests.

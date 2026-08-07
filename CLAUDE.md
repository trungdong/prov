# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

`prov` is a Python implementation of the W3C PROV Data Model. Used by ProvStore, so treat the
public API with care.

## Modernisation roadmap

Plan: `docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md`; public summary:
`ROADMAP.md`. The 2.x→3.0 modernisation programme is code-complete on `master`: every
3.0.0 compatibility change (see ROADMAP.md's "What changes in 3.0") has landed, and the
release itself is pending publication — a separate, later step, not more roadmap work.
The next phase targets **3.1.0** (PROV-JSONLD support, purely additive; see ROADMAP.md).
Rules that stay live across phases:

- One focused PR per roadmap step, green CI before merge.
- If a step changes tooling, update the affected sections of this file in the same PR.
- Never add AI attribution to commits or PRs (no "Co-Authored-By: Claude", no "Generated with
  Claude Code").

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

### Tests (`src/prov/tests/`)

Pytest-native throughout: plain `assert`, module-level `test_*` functions, no
`unittest.TestCase`. Design authority: `docs/superpowers/specs/2026-07-06-test-suite-redesign.md`.

- The suite invariant is **1629 passed, 26 skipped, 0 xfailed** (`uv run pytest -q`); any
  deviation is a regression. `uv run pytest -q -rsx` breaks the 26 skips down as: 4 in
  `test_minimal_install.py` (each extra's degradation test skips itself when that extra
  *is* installed, e.g. "only meaningful without rdflib"), 14 in `test_statements.py` (the
  #217 PROV-O limitation below), 2 more in `test_statements.py` (mentionOf, no Mention term
  in PROV-JSONLD), 3 in `test_unification_constraints.py` (ProvToolbox's `<prov:bundle>`
  dialect, rejected on parse — see the gap analysis it cites), and 3 in `test_xml_schema.py`
  (PROV-XML/XSD spec limits: `xsd:QName` local-name restrictions and
  `prov:InternationalizedString` only being typed on `prov:label`).
- Shared coverage (`test_statements.py`, `test_attributes.py`, `test_qnames.py`,
  `test_examples.py`) runs once per target via the `roundtrip` fixture. **Known-lossy RDF cases
  are intentional** (the 14 `test_statements.py` skips counted above), documented as a
  permanent PROV-O representational limitation in `docs/reference/conformance.md` (closed as
  #217), attached via per-function `@pytest.mark.parametrize("fmt", [...])` so only the `rdf`
  param is marked. **`mentionOf` under PROV-JSONLD is the same kind of permanent, documented
  limitation** — the submission defines no Mention term — marking only the `jsonld` param on
  `test_mention_1`/`test_mention_2`. Don't "fix" either case.
- `examples.py` (canonical example documents) and `attribute_values.py` (datatype corpus;
  order significant — some tests reference individual values by index) feed the shared modules
  and several others.
- `test_json.py`/`test_xml.py`/`test_rdf.py`/`test_jsonld.py` keep only format-specific tests
  (encoder internals, error paths, `find_diff`, fixture-dir round-trips over `json/`, `xml/`,
  `rdf/`, `jsonld/`). `test_xml.py`'s disabled `_perform_round_trip` glob scaffold is
  intentional (design doc §4).
- `strategies.py`/`test_property_roundtrip.py` — Hypothesis round-trip property over
  `ROUNDTRIP_FORMATS`; known-lossy constructs excluded at generation time with issue refs
  (mention-bearing documents are instead assumed away for `jsonld` in the test body — generation
  stays format-agnostic).
- Other modules are self-describing by name (e.g. `test_conformance_dm.py`,
  `test_unification_constraints.py`, `test_malformed.py`, `test_public_api.py`,
  `test_minimal_install.py`); fixture data lives in `json/`, `xml/`, `rdf/`, `jsonld/`,
  `malformed/`, `schemas/`, `unification/`.

New shared record types, attributes, or serializer behaviors go into the shared parametrized
modules so every target is exercised — not into per-format tests.

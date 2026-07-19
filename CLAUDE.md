# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

`prov` is a Python implementation of the W3C PROV Data Model: in-memory classes for building
provenance graphs, serialization to/from PROV-JSON, PROV-XML, PROV-O (RDF), and PROV-N
(write-only), graphical export via Graphviz, and NetworkX conversion. Src-layout package under
`src/prov`, Python 3.10+. Used by ProvStore, so treat the public API with care.

## Modernisation roadmap (in progress)

Plan: `docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md`; public summary:
`ROADMAP.md`. Rules:

- **No public API changes in 2.x.** Every documented name stays importable from its historic
  location; behaviour-changing fixes wait for 3.0. Guarded by `src/prov/tests/test_public_api.py`.
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

`docs/dependencies.md` explains every dependency pin (including why Sphinx is capped `<9`).

## Common commands

```bash
uv run pytest                                     # full suite, as CI runs it
uv run pytest src/prov/tests/test_model.py::test_flattening -v
uv run ruff check src/                            # lint
uv run ruff format src/                           # format
uv run mypy src                                   # strict; tests/ excluded; ships py.typed
uv run coverage run -m pytest && uv run coverage report -m

# All supported interpreters (matches CI matrix)
for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do
    uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest || break
done
```

`prov-convert` / `prov-compare` console scripts (`src/prov/scripts/`) exercise serializers
end-to-end.

## Architecture

### Core object model (`src/prov/model/` package)

Three implementation modules re-exported by `__init__.py`:

- `records.py` — datatype helpers, exceptions, `ProvRecord` and all element/relation classes,
  `PROV_REC_CLS` registry. No runtime dependency on `bundle.py` (TYPE_CHECKING only).
- `namespaces.py` — `NamespaceManager`, `DEFAULT_NAMESPACES`.
- `bundle.py` — `ProvBundle`, `ProvDocument`, `sorted_attributes`.
- `__init__.py` — re-exports every public name at its historic `prov.model` location and then
  deletes the submodule attributes, freezing `dir(prov.model)` to the pre-split namespace.
  **Always import from `prov.model`, never from the submodules.**

Class hierarchy: `ProvRecord` (attribute pairs + per-type `FORMAL_ATTRIBUTES`) →
`ProvElement` (`ProvEntity`, `ProvActivity`, `ProvAgent`) and `ProvRelation` (`ProvGeneration`,
`ProvUsage`, `ProvDerivation`, `ProvAssociation`, ... 15 edge types). `ProvBundle` holds records
with its own `NamespaceManager` and has per-type factory methods (`.entity()`,
`.wasGeneratedBy()`, ...) plus `.flattened()`/`.unified()`. `ProvDocument` is the top-level
bundle — the only kind that may contain named sub-bundles — and owns `serialize()`/`deserialize()`.

`src/prov/identifier.py` — `QualifiedName`/`Namespace`/`Identifier`. `src/prov/constants.py` —
the PROV vocabulary: record-type URIs, `PROV_N_MAP`, `PROV_BASE_CLS`, formal-attribute QNames;
all identifier↔class translation goes through it.

### Serializers (`src/prov/serializers/`)

`Serializer` ABC; `Registry` lazily maps `"json"`/`"xml"`/`"rdf"`/`"provn"` to the four modules
(PROV-N has no parser). `ProvDocument.serialize`/`deserialize` dispatch via
`prov.serializers.get(format)`; `prov.read()` auto-detects by trying each deserializer.
RDF/XML serializers need the `rdflib`/`lxml` extras.

### Graph interop

`src/prov/graph.py`: `prov_to_graph()`/`graph_to_prov()` ↔ NetworkX `MultiDiGraph`.
`src/prov/dot.py`: `prov_to_dot()` → pydot for PDF/PNG/SVG (needs a local `graphviz` binary).
Since 3.0.0.dev0 both modules sit behind extras (`graph`, `dot`) — importing either
without its extra raises `ModuleNotFoundError` naming the extra to install.

### Tests (`src/prov/tests/`)

Pytest-native throughout: plain `assert`, module-level `test_*` functions, no
`unittest.TestCase`. Design authority: `docs/superpowers/specs/2026-07-06-test-suite-redesign.md`.

- `conftest.py` — `ROUNDTRIP_FORMATS = ("json", "xml", "rdf")`, `SHARED_TARGETS = ("model",
  *ROUNDTRIP_FORMATS)`. The `fmt` fixture parametrizes over `SHARED_TARGETS`; `roundtrip`
  returns a `_check(doc)` callable (the `model` target does `get_provn()` + self-equality
  instead of serializing). A `pytest_assertrepr_compare` hook shows which record differs when
  two documents compare unequal. Hypothesis profiles registered here; CI sets
  `HYPOTHESIS_PROFILE=ci`.
- Shared coverage (`test_statements.py`, `test_attributes.py`, `test_qnames.py`,
  `test_examples.py`) runs once per target via the `roundtrip` fixture. **Known-lossy RDF cases
  are intentional**: 14 skips in `test_statements.py` (#217), attached via per-function
  `@pytest.mark.parametrize("fmt", [...])` so only the `rdf` param is marked. Don't "fix" these.
- `examples.py` (canonical example documents) and `attribute_values.py` (datatype corpus;
  order significant — RDF xfails key off indices) feed the shared modules and several others.
- `test_json.py`/`test_xml.py`/`test_rdf.py` keep only format-specific tests (encoder
  internals, error paths, `find_diff`, fixture-dir round-trips over `json/`, `xml/`, `rdf/`).
  `test_xml.py`'s disabled `_perform_round_trip` glob scaffold is intentional (design doc §4).
- `strategies.py`/`test_property_roundtrip.py` — Hypothesis round-trip property over
  `ROUNDTRIP_FORMATS`; known-lossy constructs excluded at generation time with issue refs.
- Other modules are self-describing by name (e.g. `test_conformance_dm.py`,
  `test_unification_constraints.py`, `test_malformed.py`, `test_public_api.py`,
  `test_minimal_install.py`); fixture data lives in `json/`, `xml/`, `rdf/`, `malformed/`,
  `schemas/`, `unification/`.

New shared record types, attributes, or serializer behaviors go into the shared parametrized
modules so every target is exercised — not into per-format tests.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`prov` is a Python implementation of the W3C PROV Data Model (PROV-DM). It provides
in-memory classes for building provenance graphs and serializing/deserializing them as
PROV-JSON, PROV-XML, PROV-O (RDF), and PROV-N, plus export to graphical formats (PDF/PNG/SVG
via Graphviz) and conversion to/from a NetworkX `MultiDiGraph`. Source lives under `src/prov`
(src-layout package), Python 3.10+ only.

This library is used by ProvStore, an external online repository for provenance documents, so
public API changes should be made carefully.

## Modernisation roadmap (in progress)

A staged modernisation/hardening effort is underway; the approved plan lives in
`docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md` and the public summary in
`ROADMAP.md`. Rules while it is in flight:

- **No public API changes in 2.x.** Every documented name must stay importable from its
  historic location; behaviour-changing fixes are deferred to 3.0. The public-API smoke test
  (`src/prov/tests/test_public_api.py`) guards this.
- Work in atomic steps: one focused PR per roadmap step, green CI before merge.
- When a step changes tooling (e.g. flake8/black → ruff, unittest → pytest), update the
  affected sections of this file in the same PR — the commands below describe the current
  state, not the roadmap's target state.
- Never add AI attribution to commit messages or PR descriptions (no "Co-Authored-By:
  Claude", no "Generated with Claude Code").

## Setup

The project uses `uv`. RDF and XML support are optional extras (`rdflib`, `lxml`) — install
them or many tests will fail with `ModuleNotFoundError`:

```bash
uv sync --extra rdf --extra xml
```

Dev tools (ruff, mypy, pytest, ...) live in the `dev` dependency group; building the Sphinx
docs needs the separate `docs` group plus the `rdf`/`xml` extras (autodoc imports the
serializer modules):

```bash
uv sync --group docs --extra rdf --extra xml
uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html
```

See `docs/dependencies.md` for why each runtime dependency, extra, and dev/docs-group
entry exists and why it's pinned the way it is (including why Sphinx is capped `<9`).

## Common commands

Run from the repo root; `uv run` picks up the project's managed venv.

```bash
# Full test suite (as CI runs it) — needs the rdf/xml extras installed
uv run pytest

# Single test module / class / method
uv run pytest src/prov/tests/test_model.py::TestFlattening
uv run pytest src/prov/tests/test_model.py::TestFlattening::test_flattening -v

# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Type check (mirrors the `typecheck` job in CI.yml; `[tool.mypy] strict = true`,
# codebase is strict-clean apart from src/prov/tests/ which is excluded from mypy,
# and the package ships inline types via `py.typed` — PEP 561)
uv run mypy src

# Coverage
uv run coverage run -m pytest
uv run coverage report -m

# Local multi-version testing (all supported interpreters, matches CI.yml's matrix)
for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do
    uv run --python $py --extra rdf --extra xml pytest || break
done
```

There are `prov-convert` and `prov-compare` console scripts (`src/prov/scripts/convert.py`,
`compare.py`) installed with the package, useful for manually exercising serializers end-to-end.

## Architecture

### Core object model (`src/prov/model.py`, ~2800 lines)

Everything revolves around a `ProvBundle`/`ProvDocument` containment hierarchy:

- `ProvRecord` — base class for every PROV statement (element or relation). Holds a set of
  `(QualifiedName, value)` attribute pairs plus formal attributes (defined per record type in
  `FORMAL_ATTRIBUTES`).
  - `ProvElement` — nodes: `ProvEntity`, `ProvActivity`, `ProvAgent`.
  - `ProvRelation` — edges: `ProvGeneration`, `ProvUsage`, `ProvCommunication`, `ProvStart`,
    `ProvEnd`, `ProvInvalidation`, `ProvDerivation`, `ProvAttribution`, `ProvAssociation`,
    `ProvDelegation`, `ProvInfluence`, `ProvSpecialization`, `ProvAlternate`, `ProvMention`,
    `ProvMembership`.
- `ProvBundle` — a named collection of records with its own `NamespaceManager`. Has
  `.get_records()`, `.add_bundle()`, factory methods per record type (`.entity()`,
  `.activity()`, `.wasGeneratedBy()`, etc.), and `.flattened()` / `.unified()` for graph
  simplification (merging records referring to the same real-world thing).
- `ProvDocument` — a `ProvBundle` subclass that is the top-level container; it is the only
  kind of bundle allowed to itself contain other (named) bundles. `is_document()` /
  `is_bundle()` distinguish the two at runtime since they share almost all behavior.
  `ProvDocument.serialize()` / `.deserialize()` are the main entry points for I/O and dispatch
  to the serializer registry by `format`.

`QualifiedName`/`Namespace`/`Identifier` (`src/prov/identifier.py`) implement PROV's namespaced
identifiers; `NamespaceManager` (in `model.py`) tracks registered namespaces per bundle and
resolves prefixes during parsing/serialization.

`src/prov/constants.py` defines the PROV-DM/PROV-O vocabulary: record type URIs (`PROV_ENTITY`,
`PROV_ACTIVITY`, ...), the mapping from record type to PROV-N keyword (`PROV_N_MAP`), the base
class for each record type (`PROV_BASE_CLS`), and formal-attribute QName mappings. Anything that
needs to translate between PROV-N/PROV-O identifiers and the Python classes goes through this
module.

### Serializers (`src/prov/serializers/`)

`Serializer` is an ABC with `serialize()`/`deserialize()`. `Registry` (in
`serializers/__init__.py`) lazily imports and registers the four built-in serializers by format
string: `"json"` → `provjson.py`, `"xml"` → `provxml.py`, `"rdf"` → `provrdf.py`, `"provn"` →
`provn.py` (PROV-N is write-only — there is no PROV-N parser). `prov.serializers.get(format)`
looks a serializer class up by name; `ProvDocument.deserialize`/`serialize` use this registry
based on the `format=` argument (or file extension). `prov.read()` (in `src/prov/__init__.py`)
auto-detects format by trying each registered deserializer in turn.

RDF and XML serializers require the optional `rdflib`/`lxml` dependencies (see the `rdf`/`xml`
extras in `pyproject.toml`); JSON and PROV-N have no extra dependencies.

### Graph interop (`src/prov/graph.py`, `src/prov/dot.py`)

- `graph.py`: `prov_to_graph()` / `graph_to_prov()` convert a `ProvDocument` to/from a NetworkX
  `MultiDiGraph`, one node per element, one edge per relation.
- `dot.py`: `prov_to_dot()` renders a document to a `pydot` Graph for export to PDF/PNG/SVG via
  Graphviz (needs a local `graphviz` install, not just the `pydot` Python package).

### Tests (`src/prov/tests/`)

The suite is **mid-migration** from a plain-`unittest` multiple-inheritance design to a
pytest-native shared matrix (Phase 3 test-suite redesign — authority:
`docs/superpowers/specs/2026-07-06-test-suite-redesign.md`). The runner is `pytest`, which
collects both styles natively (`expectedFailure` surfaces as `xfailed`). **JSON and the `model`
target have been migrated; XML, RDF, and dot still ride the legacy scaffolding.** Expect the two
styles to coexist until that migration completes.

**Pytest-native shared matrix (current target):**

- `conftest.py` — the shared scaffolding. Defines `ROUNDTRIP_FORMATS` (currently `("json",)`;
  xml/rdf join later) and `SHARED_TARGETS = ("model", *ROUNDTRIP_FORMATS)`. The `fmt` fixture is
  parametrized over `SHARED_TARGETS`, so every shared test runs once per serialization format
  **and** once under a non-serializing `model` target (which forces `get_provn()` + a
  self-equality check instead of a round trip). The `roundtrip` fixture returns a `_check(doc)`
  callable that tests call as `roundtrip(doc)`. A `pytest_assertrepr_compare` hook renders the
  record-level symmetric difference when two `ProvDocument`s compare unequal under `assert`, so
  round-trip failures show *which record* differs.
- `test_statements.py`, `test_attributes.py`, `test_qnames.py`, `test_examples.py` — the shared
  body as plain module-level functions taking the `roundtrip` fixture (one node per case × per
  target in `SHARED_TARGETS`). `test_attributes.py` parametrizes the single-type-attribute case
  over `ATTRIBUTE_VALUES`.
- `attribute_values.py` — the importable `ATTRIBUTE_VALUES` datatype corpus (order is
  significant: later RDF datatype-fidelity xfails key off individual indices), shared by the new
  `test_attributes.py` and the legacy `attributes.py` mixin.
- `examples.py` — canonical example PROV documents (built programmatically), consumed by both the
  new `test_examples.py` and the legacy mixins.
- `json/`, `xml/`, `rdf/`, `unification/` — fixture data directories consumed by the
  corresponding test modules (e.g. `TestLoadingProvToolboxJSON` in `test_model.py` round-trips
  every file under `tests/json/`).

**Legacy-during-migration scaffolding (still live, retired in a later step):**

- `utility.py` — `RoundTripTestCase` base (serialize → deserialize → `assertEqual`, keyed off a
  `FORMAT` class attribute). Still subclassed by `test_xml.py`/`test_rdf.py`/`test_dot.py`.
- `attributes.py`, `statements.py`, `qnames.py` — the `TestAttributesBase` / `TestStatementsBase`
  / `TestQualifiedNamesBase` mixins, and `AllTestsBase`/`TestExamplesBase` in `test_model.py`,
  composed into the xml/rdf/dot round-trip suites. These duplicate the coverage now also provided
  by the new pytest-native modules for the model/json targets; the duplication is expected and
  intentional until xml/rdf/dot migrate.

When adding a new shared record type, attribute, or serializer behavior, add it to the
pytest-native shared modules (and, while xml/rdf/dot remain on the mixins, to the corresponding
mixin) so every target is exercised, rather than writing per-format tests from scratch.

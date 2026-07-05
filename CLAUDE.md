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
docs needs the separate `docs` group (`uv sync --group docs`). See `docs/dependencies.md`
for why each runtime dependency, extra, and dev/docs-group entry exists and why it's pinned
the way it is.

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

Test code is plain `unittest` (`TestCase` classes/`assert*` methods, `expectedFailure`, etc.),
not pytest-specific; the runner is `pytest`, which collects and runs unittest-style classes
natively (`expectedFailure` surfaces as `xfailed`). Shared test scaffolding lives in a few
base-class modules rather than being duplicated per format:

- `examples.py` — canonical example PROV documents (built programmatically) reused across
  serializer/model tests.
- `utility.py` — `RoundTripTestCase` base: serializes a document in a format and deserializes
  it back, asserting equivalence. Format-specific test files (`test_json.py`, `test_xml.py`,
  `test_rdf.py`) subclass this together with the shared mixins below.
- `attributes.py`, `statements.py`, `qnames.py` — shared `TestAttributesBase` /
  `TestStatementsBase` / `TestQualifiedNamesBase` mixins exercising attribute/statement/qname
  behavior identically across formats.
- `json/`, `xml/`, `rdf/`, `unification/` — fixture data directories consumed by the
  corresponding test modules (e.g. `TestLoadingProvToolboxJSON` in `test_model.py` round-trips
  every file under `tests/json/`).

When adding a new record type, attribute, or serializer behavior, the common pattern is to add
it once to `examples.py`/the shared mixins so all format serializers are exercised against it,
rather than writing per-format tests from scratch.

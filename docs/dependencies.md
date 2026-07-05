# Dependency audit

Why every runtime dependency, extra, and dev/docs-group entry exists, and why it's pinned
the way it is. Written as part of the Phase 2 dependency audit (T14); re-check pins against
`pyproject.toml` before trusting the version numbers below — they drift.

## Runtime dependencies (`[project.dependencies]`)

These install unconditionally with `pip install prov`.

- **`networkx>=2.0`** — backs `prov.graph` (`prov_to_graph()`/`graph_to_prov()`), the
  NetworkX `MultiDiGraph` interop. Floor is `2.0`, the first release with the API this
  module relies on; no upper bound because the module only uses stable, long-standing
  NetworkX APIs.
- **`pydot>=1.2.0`** — backs `prov.dot` (`prov_to_dot()`), rendering a document to a
  `pydot.Graph` for export via Graphviz (PDF/PNG/SVG). Requires a *local* `graphviz`
  binary install separately; `pydot` alone only builds the DOT representation. Floor
  `1.2.0` predates this project's use of it; no known upper-bound issue.
- **`python-dateutil>=2.2`** — `dateutil.parser.parse()` in `src/prov/model.py` parses
  ISO-8601-ish datetime strings from PROV-JSON/XML/RDF into `datetime` objects. There is a
  long-standing `# TODO: is this really needed?` next to this entry — the stdlib
  `datetime.fromisoformat()` couldn't handle the full range of formats PROV documents use
  when this was added, but nobody has re-verified that against the current stdlib.
  Left as-is; not in scope for this audit (would be a behaviour-risk change deferred to
  3.0 if pursued).

`pydot` and `networkx` are unconditional runtime deps today even though only `dot.py`/
`graph.py` use them; moving them behind optional extras (e.g. `prov[dot]`, `prov[graph]`)
is a tracked 3.0 idea (see the modernisation roadmap design doc), not done here since it
would be a public-API/behaviour change for 2.x users who `import prov.dot`/`prov.graph`
without an extra installed.

## Optional extras (`[project.optional-dependencies]`)

Install with `prov[extra]`; omitting them makes the corresponding serializer/module raise
`ModuleNotFoundError` when used, not at `import prov` time.

- **`rdf` → `rdflib>=4.2.1,<7`** — backs `prov.serializers.provrdf` (PROV-O/RDF
  serialization). Floor `4.2.1` is the oldest version this project has tested against.
  The `<7` ceiling is deliberate, not incidental: rdflib 7.6.0 fails 5 tests
  (`RoundTripRDFTests::test_bundle_1..4`, `::test_default_namespace_inheritance` in
  `src/prov/tests/test_rdf.py`), traced to rdflib 7's `Dataset`/graph-identifier and
  namespace-binding changes (e.g. `bind_namespaces` defaults). Widening to `<8` is T15, a
  separate, explicitly time-boxed investigation — its outcome (fixed-and-widened, or kept
  pinned with a filed issue) is not yet known as of this writing; check T15's PR/issue
  before assuming either way.
- **`xml` → `lxml>=3.3.5`** — backs `prov.serializers.provxml` (PROV-XML). Floor predates
  this project's adoption; no known upper-bound issue.
- **`plot` → `matplotlib>=3.6`** — backs the interactive-display path of
  `ProvBundle.plot()`/`ProvDocument.plot()` in `src/prov/model.py` (lazily imported
  alongside `pydot` so the base install stays light). Floor `3.6` is a defensive modern
  baseline rather than a verified minimum; not exercised in CI (no display backend in the
  test environment), so this path is coverage-`defer`red (see
  `docs/test-gap-checklist.md`).

## Dev dependency group (`[dependency-groups] dev`)

Tools needed to develop/test/lint/typecheck the package locally and in CI; never installed
for end users.

- **`coverage>=7.6.10`** — measures branch coverage for the `fail_under` ratchet enforced
  in CI (see `[tool.coverage]` in `pyproject.toml`).
- **`lxml-stubs>=0.5.1`** — type stubs for `lxml`, needed for `mypy --strict` to type-check
  `provxml.py` without treating `lxml` as `Any`.
- **`mypy>=1.19.1`** — the strict type checker (`[tool.mypy] strict = true`); floor is
  whatever version this project first enforced strict mode + `py.typed` with.
- **`pre-commit>=4.0.1`** — runs ruff (lint + format) and hygiene checks
  (trailing-whitespace/EOF-newline/YAML-TOML validation) automatically at commit time; see
  `CONTRIBUTING.rst` step 4.
- **`pytest>=8.4.2`** — the test runner; collects the `unittest.TestCase`-style test suite
  under `src/prov/tests/` natively.
- **`pytest-cov>=7.1.0`** — pytest's coverage plugin, so `coverage` can attribute hits
  correctly when tests run under pytest instead of `unittest`.
- **`ruff>=0.15.20`** — combined linter (replacing the historic flake8) and formatter
  (replacing the historic black); see `[tool.ruff]` for the enabled rule families.
- **`types-networkx>=3.4.2.20250509`** — type stubs for `networkx`, needed for
  `mypy --strict` on `graph.py`. Pulls in `numpy` transitively (see the `numpy<2.5`
  constraint below).
- **`types-python-dateutil>=2.9.0.20260124`** — type stubs for `python-dateutil`, needed
  for `mypy --strict` on `model.py`'s datetime parsing.

Previously in this group and removed by this audit: `bumpversion` (a release-time-only
tool with no place in the routine dev loop — reintroduce as a dedicated group if release
automation is scripted later), `setuptools`/`wheel` (build-backend concerns declared under
`[build-system]`, not something a dev environment needs to import directly), `tox`
(replaced by direct `uv run --python 3.X pytest` invocations across the supported
interpreter matrix; CI already covers the matrix independently — see "Local multi-version
testing" in `CLAUDE.md`), and `sphinx`/`sphinx-rtd-theme` (moved to the new `docs` group
below, since building the documentation is a separate concern from running/lint/typecheck
tests and the RTD build installs `docs/requirements.txt` directly, not the dev group).

## Docs dependency group (`[dependency-groups] docs`)

Mirrors `docs/requirements.txt` (the file ReadTheDocs actually installs from — kept in
sync manually since RTD does not support `uv`/dependency-groups natively). Use
`uv sync --group docs` for a local Sphinx build.

- **`sphinx>=8.1.3,<9`** — the documentation generator. The `<9` ceiling fixes a
  ReadTheDocs build break (introduced 2026-07-04, see `docs/requirements.txt` history):
  Sphinx 9's autodoc calls `repr()` on class bases while documenting
  `prov.serializers.provrdf`; rdflib's `DefinedNamespaceMeta.__repr__` raises
  `AttributeError` on its abstract base class, crashing the build. Verified: 8.1.3 and
  8.2.3 build fine; 9.0.4 and 9.1.0 crash. Revisit once rdflib fixes `__repr__` on its
  namespace metaclass, or once this project drops the RDF serializer's exposure to
  autodoc.
- **`sphinx_rtd_theme`** — the Sphinx theme used for the published docs (matches
  ReadTheDocs' historic default theme, kept explicit rather than relying on RTD's
  built-in fallback).

## `[tool.uv] constraint-dependencies`

- **`numpy<2.5`** — numpy is never imported by `prov` itself; it arrives transitively via
  `types-networkx` and `matplotlib`. numpy 2.5 switched its inline stubs to unconditional
  PEP 695 `type` statements, which mypy refuses to parse once `[tool.mypy] python_version`
  is below 3.12 (this project's `python_version = "3.10"`), regardless of the interpreter
  actually running mypy. Capping numpy avoids that crash. If a Dependabot bump of
  `matplotlib`/`types-networkx` ever fails to resolve because of this constraint, lift it,
  run `uv run mypy src`, and keep the lift only if mypy stays green (e.g. once numpy gates
  the new stub syntax on `python_version`, or this project's mypy floor rises to 3.12).

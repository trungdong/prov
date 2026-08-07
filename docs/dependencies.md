# Dependency audit

Audit date: 2026-07-05, against `master` @ `185c062` (Phase 2 dependency audit, T14).
Pin rationales re-verified 2026-07-27, against `master` @ `970524f`, ahead of the 3.0.0
release: every rationale below was re-read against `uv.lock`, and the Sphinx and numpy
constraints were re-derived by actually re-resolving and re-running the tooling they
guard (commands and outcomes recorded in their entries below), not by re-asserting the
prior text.

Why every runtime dependency, extra, and dev/docs-group entry exists, and why it's pinned
the way it is. Re-check pins against `pyproject.toml` before trusting the version numbers
below — they drift after the audit date above.

## Runtime dependencies (`[project.dependencies]`)

`prov` has **no unconditional runtime dependencies** as of 3.0.0.dev0. `pydot` and
`networkx` moved behind the `dot`/`graph` extras, and `python-dateutil` was dropped in
3.0 — datetime strings are now parsed by `prov.model.parse_xsd_datetime()`, a stdlib
`datetime.fromisoformat()`-based `xsd:dateTime` parser, resolving the long-standing
`# TODO: is this really needed?` that used to sit next to the `python-dateutil` entry here.

## Optional extras (`[project.optional-dependencies]`)

Install with `prov[extra]`; omitting them makes the corresponding serializer/module raise
`ModuleNotFoundError` when used, not at `import prov` time.

- **`dot` → `pydot>=1.2.0`, `networkx>=2.0`** — backs `prov.dot` (`prov_to_dot()`),
  rendering a document to a `pydot.Graph` for export via Graphviz (PDF/PNG/SVG). Requires
  a *local* `graphviz` binary installed separately; `pydot` alone only builds the DOT
  representation. `prov.dot` renders through `prov.graph` internally, so this extra
  carries `networkx` too, not just `pydot`. `pydot` floor `1.2.0` predates this project's
  use of it; `networkx` floor `2.0` is the first release with the API `prov.graph` relies
  on. Both were unconditional runtime dependencies before 3.0.0.dev0 (see
  `docs/upgrading-3.0.md`).
- **`graph` → `networkx>=2.0`** — backs `prov.graph` (`prov_to_graph()`/
  `graph_to_prov()`), the NetworkX `MultiDiGraph` interop. Same floor/rationale as the
  `networkx` pin under `dot` above.
- **`rdf` → `rdflib>=7.0.0,<8`** — backs `prov.serializers.provrdf` (PROV-O/RDF
  serialization). Floor raised to `7.0.0` 2026-07-18 (roadmap step 35, 3.0.0.dev0): the
  rdflib-6 accidental prefix-carrying behaviour described below is no longer supported,
  and the serializer now depends on `rdflib.graph.Dataset`/`DATASET_DEFAULT_GRAPH_ID`,
  which don't exist before rdflib 7. Internally, `provrdf.py` migrated off the deprecated
  `ConjunctiveGraph` to `Dataset(default_union=True)` plus named `Graph`s — deferred from
  2.x precisely because `Dataset`'s defaults (e.g. `default_union`) are not
  behaviour-neutral, so the switch waited for a 3.0 breaking-change window.
  `default_union=True` reproduces `ConjunctiveGraph`'s union-query semantics, and
  round-trip behaviour (including the bundle-local-namespaces-as-full-IRIs point below)
  is unchanged by the migration. The `rdflib-compat` CI job proves both bounds (`7.0.0`
  floor and newest 7.x); the main matrix uses the locked version. Under rdflib 7,
  bundle-local namespaces serialize as full IRIs instead of their original prefixes
  (round-trips stay equivalent — `QualifiedName` equality is by IRI). Separately, from
  rdflib 7.3.0 onward rdflib's own internals (`ConjunctiveGraph.add()`/`.parse()`, and
  the TriG parser/serializer plugins) call their own now-deprecated `Dataset.contexts()`/
  `Dataset.default_context` under the hood, so a `-W error::DeprecationWarning` run
  against `test_rdf.py` fails on rdflib >=7.3 even though `provrdf.py` no longer
  directly calls a deprecated rdflib name in the document-encoding path (confirmed
  clean against the `7.0.0` floor); this is rdflib's own migration debt, slated for
  cleanup by their 8.0. (`encode_container()` still accepts a caller-supplied `Dataset`
  as its `container` argument for API-compatibility reasons; that path's own `.add()`
  calls do re-trip rdflib's internal warning, since `Dataset` inherits `.add()` from the
  deprecated `ConjunctiveGraph` unchanged — see the method's docstring.)
- **`xml` → `lxml>=3.3.5`** — backs `prov.serializers.provxml` (PROV-XML). Floor predates
  this project's adoption; no known upper-bound issue.
- **`plot` → `matplotlib>=3.6`, `pydot>=1.2.0`, `networkx>=2.0`** — backs the
  interactive-display path of `ProvBundle.plot()`/`ProvDocument.plot()` in
  `src/prov/model/bundle.py`; `plot()` renders through `prov.dot` (lazily imported), so
  this extra pulls in `pydot`/`networkx` alongside `matplotlib` rather than requiring
  `prov[dot]` to be depended on separately. `matplotlib` floor `3.6` is a defensive modern
  baseline rather than a verified minimum; not exercised in CI (no display backend in the
  test environment), so this path is coverage-`defer`red (see
  `docs/test-gap-checklist.md`).

## Dev dependency group (`[dependency-groups] dev`)

Tools needed to develop/test/lint/typecheck the package locally and in CI; never installed
for end users.

- **`coverage>=7.6.10`** — measures branch coverage for the `fail_under` ratchet enforced
  in CI (see `[tool.coverage]` in `pyproject.toml`).
- **`hypothesis>=6.156.1`** — property-based testing; drives the round-trip strategies in
  `src/prov/tests/strategies.py` exercised by `test_property_roundtrip.py` over
  `ROUNDTRIP_FORMATS`. Added when that module was introduced (added to this audit
  2026-07-27; the pin itself predates this note — it was missing from the dev-group list
  above by omission, not by design).
- **`jsonschema>=4`** — validates PROV-JSON output against the vendored member-submission
  schema in `test_json_schema.py`, and PROV-JSONLD output against a second vendored schema
  in `test_jsonld_schema.py` (both under `src/prov/tests/schemas/`). Same omission/backfill
  as `hypothesis` above.
- **`lxml-stubs>=0.5.1`** — type stubs for `lxml`, needed for `mypy --strict` to type-check
  `provxml.py` without treating `lxml` as `Any`.
- **`mypy>=1.19.1`** — the strict type checker (`[tool.mypy] strict = true`); floor is
  whatever version this project first enforced strict mode + `py.typed` with.
- **`pre-commit>=4.0.1`** — runs ruff (lint + format) and hygiene checks
  (trailing-whitespace/EOF-newline/YAML-TOML validation) automatically at commit time; see
  `CONTRIBUTING.md` step 4.
- **`pyld>=2.0.4`** — reference JSON-LD processor used only by `test_jsonld_semantics.py`
  to prove PROV-JSONLD output expands to the intended RDF terms. Test-time only: `prov`
  itself never imports it, so it carries no runtime dependency. Floor `2.0.4` is a
  defensive modern baseline (the resolved/locked version at introduction was `3.1.0`), not
  a verified minimum.
- **`pytest>=8.4.2`** — the test runner; collects the `unittest.TestCase`-style test suite
  under `src/prov/tests/` natively.
- **`pytest-cov>=7.1.0`** — pytest's coverage plugin, so `coverage` can attribute hits
  correctly when tests run under pytest instead of `unittest`.
- **`ruff>=0.15.20`** — combined linter (replacing the historic flake8) and formatter
  (replacing the historic black); see `[tool.ruff]` for the enabled rule families.
- **`types-networkx>=3.4.2.20250509`** — type stubs for `networkx`, needed for
  `mypy --strict` on `graph.py`. Pulls in `numpy` transitively (see the `numpy<2.5`
  constraint below).

Previously in this group and removed by this audit: `bumpversion` (a release-time-only
tool with no place in the routine dev loop — reintroduce as a dedicated group if release
automation is scripted later), `setuptools`/`wheel` (build-backend concerns declared under
`[build-system]`, not something a dev environment needs to import directly), `tox`
(replaced by direct `uv run --python 3.X pytest` invocations across the supported
interpreter matrix; CI already covers the matrix independently — see "Local multi-version
testing" in `CLAUDE.md`), and `sphinx`/`sphinx-rtd-theme` (moved to the new `docs` group
below, since building the documentation is a separate concern from running/lint/typecheck
tests; at that point the RTD build still installed `docs/requirements.txt` directly, not
the dev group — since T21/docs-tooling (2026-07-05) RTD installs the `docs` group directly
via `uv sync`, see below).

## Docs dependency group (`[dependency-groups] docs`)

The single source of truth for docs build dependencies — both local builds
(`uv sync --group docs --extra rdf --extra xml`) and ReadTheDocs (`.readthedocs.yml` runs
`uv sync --frozen --no-dev --group docs --extra rdf --extra xml` directly) install from
this group. `docs/requirements.txt` — a hand-maintained mirror of this list that RTD used
before it could run `uv` in its build image — was deleted 2026-07-05 (T21) once RTD's
`build.jobs.create_environment` could install `uv` itself via `asdf`; keeping two
manually-synced dependency lists was a standing liability.

- **`sphinx>=8.1.3`** — the documentation generator. Was capped `<9` from 2026-07-04:
  Sphinx 9's autodoc calls `repr()` on class bases while documenting
  `prov.serializers.provrdf`, and rdflib's `DefinedNamespaceMeta.__repr__`
  (`rdflib.namespace`) used to raise `AttributeError` on its abstract base class,
  crashing the build; re-verified 2026-07-05 with the furo theme swap, the crash still
  reproduced on 9.1.0. **Cap lifted 2026-07-27**: rdflib fixed it — the currently locked
  rdflib (7.6.0) has `DefinedNamespaceMeta.__repr__` catch that `AttributeError` itself
  and fall back to a placeholder string instead of propagating it (confirmed by reading
  the method's source out of the installed package). Verified end to end by resolving
  Sphinx unconstrained (`uv lock --upgrade-package sphinx`, which now locks 9.0.4 for
  Python 3.11 and 9.1.0 for Python ≥3.12) and then building the docs against that lock
  with `uv run --group docs --extra rdf --extra xml --extra dot --extra graph
  sphinx-build -b html -W docs docs/_build/html`: build succeeds, 0 warnings. If a
  similar autodoc crash resurfaces on a future Sphinx major, re-run that same build
  with `-W` before assuming a new cap is needed.
- **`furo`** — the HTML theme for the published docs, replacing `sphinx_rtd_theme`
  2026-07-05 (T21): actively maintained, accessible defaults, and native light/dark mode
  without extra configuration. No known version constraints yet.
- **`myst-parser`** — lets `.md` sources (in addition to `.rst`) build as Sphinx pages,
  via `source_suffix` in `conf.py`. Added T21 so future docs content (Diátaxis
  restructure, tasks 3–6 of the modernisation roadmap) isn't forced into reStructuredText.
  Enables the `colon_fence`/`deflist` MyST extensions only; no other extensions are
  needed by the current page set.
- **`sphinx-copybutton`** — adds a "copy" button to code blocks in the rendered HTML;
  purely a UX nicety for the many shell/PROV-N/JSON snippets across the docs. Added T21.

Removed T21: `sphinx_rtd_theme` (superseded by `furo`, above).

## `[tool.uv] constraint-dependencies`

- **`numpy<2.5`** — numpy is never imported by `prov` itself; it arrives transitively via
  `types-networkx` and `matplotlib`. numpy 2.5 switched its inline stubs to unconditional
  PEP 695 `type` statements, which mypy refuses to parse once `[tool.mypy] python_version`
  is below 3.12 (this project's `python_version = "3.10"`), regardless of the interpreter
  actually running mypy. Capping numpy avoids that crash. **Re-checked 2026-07-27, still
  needed**: numpy's current PyPI release is 2.5.1. Clearing the constraint and running
  `uv lock --upgrade-package numpy` resolves numpy 2.5.1 for Python ≥3.12; `uv sync` that
  lock and `uv run mypy src` immediately fails with `numpy/__init__.pyi: error: Type
  statement is only supported in Python 3.12 and greater [syntax]`, reproducing the
  original crash. Constraint restored and re-locked. If a Dependabot bump of
  `matplotlib`/`types-networkx` ever fails to resolve because of this constraint, lift it,
  run `uv run mypy src`, and keep the lift only if mypy stays green (e.g. once numpy gates
  the new stub syntax on `python_version`, or this project's mypy floor rises to 3.12).

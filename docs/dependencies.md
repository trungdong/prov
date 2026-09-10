# Dependencies

Why each runtime extra, dev-group and docs-group entry exists, and why it is pinned the
way it is. Last checked 2026-09-10 against `pyproject.toml` and `uv.lock` at 3.1.1. Version
numbers quoted here drift after that date, so check `pyproject.toml` before relying on
them.

## Runtime dependencies

`prov` has no unconditional runtime dependencies. `pydot` and `networkx` moved behind the
`dot` and `graph` extras in 3.0.0, and `python-dateutil` was dropped in the same release in
favour of `prov.model.parse_xsd_datetime()`, an `xsd:dateTime` parser built on the standard
library's `datetime.fromisoformat()`.

## Optional extras

Install with `prov[extra]`. A missing extra raises an error naming it when the capability is
used, not at `import prov` time.

| Extra | Packages | Backs |
|---|---|---|
| `rdf` | `rdflib>=7.0.0,<8` | `prov.serializers.provrdf`, PROV-O (RDF) |
| `xml` | `lxml>=3.3.5` | `prov.serializers.provxml`, PROV-XML |
| `dot` | `pydot>=1.2.0`, `networkx>=2.0` | `prov.dot`, Graphviz rendering |
| `graph` | `networkx>=2.0` | `prov.graph`, NetworkX interop |
| `plot` | `matplotlib>=3.6`, `pydot>=1.2.0`, `networkx>=2.0` | The interactive display in `ProvBundle.plot()` |

### `rdf`

The floor rose from 6.0.0 to 7.0.0 in 3.0.0. The serializer uses `rdflib.graph.Dataset` and
`DATASET_DEFAULT_GRAPH_ID`, which do not exist before rdflib 7, and rdflib 6's accidental
prefix-carrying behaviour is no longer supported. `Dataset(default_union=True)` reproduces
the union-query semantics of the deprecated `ConjunctiveGraph` it replaced, so round-trip
behaviour is unchanged. Under rdflib 7, bundle-local namespaces serialize as full IRIs
rather than their original prefixes; round trips stay equivalent because `QualifiedName`
equality is by IRI.

The `rdflib-compat` CI job runs the RDF tests against both bounds, `==7.0.0` and the newest
7.x. The main matrix uses the locked version.

From rdflib 7.3.0 its own internals call deprecated `Dataset` members, so a
`-W error::DeprecationWarning` run of the RDF tests fails on rdflib 7.3 and later even
though `provrdf.py` calls no deprecated rdflib name in the encoding path. That is rdflib's
migration debt, slated for its 8.0. The `own-warnings` CI job therefore counts only
warnings attributed to `prov` modules. `encode_container()` still accepts a caller-supplied
`Dataset` for API compatibility; that path's `.add()` calls trip the same rdflib warning.

### `xml`

The `lxml` floor predates this project's adoption. No known upper-bound issue. The
deserializer passes its own hardened `XMLParser` at every parse site; see the comment in
`provxml.py` for why the floor matters there.

### `dot`, `graph` and `plot`

`prov.dot` renders through `prov.graph`, so the `dot` extra carries `networkx` as well as
`pydot`. Rendering also needs a local Graphviz binary, which no extra installs. `plot()`
renders through `prov.dot`, so the `plot` extra carries `pydot` and `networkx` alongside
`matplotlib`. The `pydot` floor predates this project's use of it and the `networkx` floor
is the first release with the API `prov.graph` relies on. The `matplotlib` floor is a
defensive modern baseline, not a verified minimum. The interactive `plot()` path is not
exercised in CI because the test environment has no display backend; it is annotated
"defer" in `planning/test-gap-checklist.md`.

## Dev dependency group

Tools for developing, testing, linting and type-checking the package locally and in CI.
Never installed for end users.

| Package | Purpose |
|---|---|
| `coverage>=7.6.10` | Branch coverage for the `fail_under` ratchet in `[tool.coverage]`. |
| `hypothesis>=6.156.1` | Property-based round-trip tests, `strategies.py` and `test_property_roundtrip.py`. |
| `jsonschema>=4` | Validates PROV-JSON and PROV-JSONLD output against the vendored schemas under `src/prov/tests/schemas/`. |
| `lxml-stubs>=0.5.1` | Type stubs so `mypy --strict` can check `provxml.py`. |
| `mypy>=1.19.1` | Strict type checking; the floor is the version strict mode was first enforced with. |
| `pre-commit>=4.0.1` | Runs ruff and the hygiene hooks at commit time; see `CONTRIBUTING.md`. |
| `pyld>=2.0.4` | Reference JSON-LD processor used only by `test_jsonld_semantics.py`; `prov` never imports it. The floor is a defensive baseline, not a verified minimum. |
| `pytest>=8.4.2` | The test runner. |
| `pytest-cov>=7.1.0` | Coverage attribution under pytest. |
| `ruff>=0.15.20` | Linter and formatter; `[tool.ruff]` lists the rule families. |
| `types-networkx>=3.4.2.20250509` | Type stubs for `graph.py` under `mypy --strict`. Pulls in `numpy` transitively, see the constraint below. |

Removed from this group in 2.3.0: `bumpversion`, `setuptools`, `wheel` and `tox`. Build
backend requirements live under `[build-system]`, and the interpreter matrix is run with
`uv run --python 3.X pytest`, as `CONTRIBUTING.md` shows. `sphinx` and `sphinx-rtd-theme`
moved to the docs group below.

## Docs dependency group

The single source of truth for documentation builds. Local builds and Read the Docs both
install it, with all four extras because autodoc imports the serializers, `prov.dot` and
`prov.graph`:

```bash
uv sync --group docs --extra rdf --extra xml --extra dot --extra graph
```

`.readthedocs.yml` runs the same `uv sync` with `--frozen --no-dev`.

| Package | Purpose |
|---|---|
| `sphinx>=8.1.3` | The documentation generator. |
| `furo` | The HTML theme. Actively maintained, accessible defaults, native light and dark mode. |
| `myst-parser` | Builds the `.md` sources; only the `colon_fence` and `deflist` extensions are enabled. |
| `sphinx-copybutton` | A copy button on code blocks. |

Sphinx was capped below 9 from 2.3.0 to 3.0.0 because Sphinx 9's autodoc called `repr()`
on rdflib's `DefinedNamespaceMeta`, which raised `AttributeError` and crashed the build.
rdflib 7.6.0 catches that error itself, so the cap was lifted for 3.0.0 after a clean
`sphinx-build -W` against Sphinx 9. The lock file currently resolves Sphinx 8.1.3. If a
similar autodoc crash appears on a future Sphinx major, rebuild with `-W` before assuming a
new cap is needed.

## `[tool.uv]` constraint

`numpy<2.5`. `prov` never imports numpy; it arrives transitively through `types-networkx`
and `matplotlib`. numpy 2.5 switched its inline stubs to unconditional PEP 695 `type`
statements, which mypy refuses to parse while `[tool.mypy] python_version` is below 3.12,
whatever interpreter runs mypy. Clearing the constraint and re-locking reproduces the crash
(`numpy/__init__.pyi: error: Type statement is only supported in Python 3.12 and greater`).
If a Dependabot bump of `matplotlib` or `types-networkx` fails to resolve because of this
constraint, lift it, run `uv run mypy src`, and keep the lift only if mypy stays green.
That becomes possible once numpy gates the new syntax on `python_version` or this
project's mypy floor rises to 3.12.

# Dependencies

Why each runtime extra and each dev, bench and docs group entry exists, and why it is
pinned the way it is. Last checked 2026-10-23 against `pyproject.toml` and `uv.lock` on
`main` after 3.2.3. Version numbers quoted here drift after that date, so check
`pyproject.toml` before relying on them.

## Runtime dependencies

`prov` has no unconditional runtime dependencies. `pydot` and `networkx` sit behind the
`dot` and `graph` extras, and `xsd:dateTime` parsing is `prov.model.parse_xsd_datetime()`,
built on the standard library's `datetime.fromisoformat()`.

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
| `pygments` | `pygments>=2.18` | `prov.pygments`, PROV-N highlighting through the `pygments.lexers` entry point |

### `rdf`

The floor is 7.0.0 because the serializer uses `rdflib.graph.Dataset` and
`DATASET_DEFAULT_GRAPH_ID`, which do not exist before rdflib 7. The cap below 8 is
precautionary: rdflib's next major is untested here, and the serializer already avoids the
`Dataset` members rdflib has deprecated, so lifting it is a test run, not a rewrite.

The `rdflib-compat` CI job runs the RDF tests against both bounds, `==7.0.0` and the newest
7.x. The main matrix uses the locked version. The `own-warnings` CI job counts only warnings
attributed to `prov` modules, because rdflib's own internals raise deprecation warnings.

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
exercised in CI because the test environment has no display backend.

### `pygments`

The floor is 2.18, the first release with `Lexer.version_added`, which the copy submitted
to Pygments sets. The lexer itself also runs on older releases, so the floor follows the
upstream copy and is not a measured minimum. There is no upper bound. Every test
environment already holds Pygments through pytest, so the gates sync no new extra.

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
| `types-Pygments>=2.21.0.20260819` | Type stubs so `mypy --strict` checks `prov/pygments.py`. `bygroups` is untyped, so the module binds it to a typed alias and carries no `type: ignore`. |

Build backend requirements live under `[build-system]`, and the interpreter matrix is run
with `uv run --python 3.X pytest`, as `CONTRIBUTING.md` shows.

## Bench dependency group

`CLAUDE.md` tells agents to sync this group alongside the four extras, because
`benchmarks/ab.py` and the benchmark suite under `benchmarks/` need it.

| Package | Purpose |
|---|---|
| `pytest-benchmark>=5.1.0` | Times the benchmark suite; `benchmarks/ab.py` compares two versions of the library with it. |

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
| `sphinx>=8.1.3` | The documentation generator. CI's `docs` job builds the site with `-W -n`, so a warning or an unresolved cross-reference fails the PR. |
| `furo` | The HTML theme. Actively maintained, accessible defaults, native light and dark mode. |
| `myst-parser` | Builds the `.md` sources; only the `colon_fence` and `deflist` extensions are enabled. |
| `sphinx-copybutton` | A copy button on code blocks. |

Sphinx has no cap. The lock file resolves Sphinx 9, and `docs/conf.py` carries a small
patch for how its autodoc prints a type alias inside a union; the comment there says when
it goes. If an autodoc crash appears on a future Sphinx major, rebuild with `-W` before
assuming a cap is needed.

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

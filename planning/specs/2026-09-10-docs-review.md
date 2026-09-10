# Public documentation review

Review of every published page for accuracy, cross-page consistency and readability.
Scope is the Sphinx site content plus README, CONTRIBUTING, SECURITY, HISTORY (facts only),
LICENSE and the two CLI script headers. Docstrings, `planning/`, `ROADMAP.md`,
`docs/dependencies.md` and `docs/releasing.md` are out of scope.

## Canonical statements

Every page that states one of these facts states it this way.

| Fact | Canonical statement |
|---|---|
| Python | 3.10 or later. CPython 3.10 to 3.14 and PyPy 3.11 are tested. 3.10 is dropped in the first release after 2026-10-31. |
| Runtime dependencies | None. Every third-party package sits behind an extra. |
| Extras | `rdf` (rdflib), `xml` (lxml), `dot` (pydot, networkx), `graph` (networkx), `plot` (matplotlib, pydot, networkx). |
| `plot()` | Needs `prov[plot]`. |
| Graphviz | The `dot` extra also needs a local Graphviz binary. |
| Formats | `json` (default), `xml`, `rdf`, `provn` (write-only), `jsonld`. |
| Auto-detect order | `json`, `rdf`, `provn`, `xml`, `jsonld`. |
| Support policy | 3.x receives all fixes. 2.x receives security fixes only; 2.5.3 was the last back-port release. Before 2.0 nothing. |
| Next release | 3.2.0 adds a PROV-N parser (#122). |
| `prov-convert` | Input is always PROV-JSON. Output is `json`, `xml`, `rdf`, `jsonld`, `provn` or any Graphviz format. |
| `prov-compare` | Either file may be in any registered format. |
| Copyright | 2026 in LICENSE, `docs/conf.py` and both CLI script headers. |
| Repository links | `https://`, branch `main`. |
| Unpublished repo docs | Link with a full GitHub URL, never a relative path. |
| Example import | `import prov.model as pm`. |

## Defects found and fixed

| Page | Defect |
|---|---|
| `docs/howto/graphics.md` | Calls pydot a core dependency. It needs `prov[dot]` since 3.0. |
| `docs/howto/networkx.md` | Calls networkx a core dependency. It needs `prov[graph]` since 3.0. |
| `docs/howto/provjson.md` | Auto-detect order omits PROV-JSONLD. |
| `docs/upgrading-3.0.md` | Says `plot()` needs `prov[dot]`. It needs `prov[plot]`. |
| `docs/howto/provjsonld.md` | Quoted `mentionOf` error text no longer matches the library. |
| `README.md`, `docs/installation.md` | Say "Python 3" where the floor is 3.10. |
| `README.md` | Links an external short tutorial instead of the site tutorial. `http://` links. |
| `docs/installation.md`, `CONTRIBUTING.md` | Relative link to `docs/dependencies.md`, which is not published. |
| `docs/howto/cli.md` | Format tables copy stale help text. `rdf` and `jsonld` output and any registered compare format work. |
| `src/prov/scripts/*.py` | Help text lists only `json`, `xml`, `provn`; `convert_file` docstring claims input auto-detection; LICENSE URL uses `master`; copyright 2025. |
| `docs/changelog-archive.md` | Dead networkx link; `master` links. |
| `docs/explanation/unification-flattening.md` | `master` link. |
| `docs/whats-new-3.md` | Audit list omits PROV-N. |
| `LICENSE` | Copyright 2025; mixed dash styles in the year ranges. |

## Style brief

- British English. No em dashes in prose. A spaced dash before a gloss in a table cell is fine.
- One idea per sentence. Under about twenty words in instructions and reference text.
- State the fact. No "note that", no "worth noting", no rating of facts.
- No release archaeology in how-to or tutorial pages. Describe present behaviour. Version history belongs in HISTORY.
- Tutorial teaches one path. How-to answers one question per section. Reference states facts. Explanation gives reasons.
- Link a page once per section. Repeat cross-references only where the reader needs to go there.
- Code examples import with `import prov.model as pm`.

## Clusters

1. Entry funnel. `README.md`, `docs/installation.md`, `docs/tutorial/getting-started.md`, `docs/index.rst`.
2. Format how-tos. `docs/howto/*.md`.
3. Reference and explanation. `docs/reference/*.md`, `docs/explanation/*.md`.
4. Project pages. `CONTRIBUTING.md`, `SECURITY.md`, `docs/whats-new-3.md`, `docs/upgrading-3.0.md`, `HISTORY.md`, `docs/changelog-archive.md`, `LICENSE`, `src/prov/scripts/*.py`.

## Gates per PR

- `sphinx-build -W` clean.
- Every Python block in the edited pages runs.
- `codacy-analysis analyze` on each changed file reports no issues.
- Full test matrix for the PR that touches `src/prov/scripts/`.

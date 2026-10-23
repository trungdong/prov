# Public documentation review

**Date:** 2026-09-10
**Status:** Complete; shipped in 3.1.1

Review of every published page for accuracy, cross-page consistency and readability.
Scope is the Sphinx site content plus README, CONTRIBUTING, SECURITY, HISTORY (facts only),
LICENSE and the two CLI script headers. Docstrings, `planning/`, `ROADMAP.md`,
`docs/dependencies.md` and `docs/releasing.md` are out of scope.

## Canonical statements

The table of canonical statements that stood here was removed on 2026-10-23, because it
went out of date at every release. Section 3 of
[the documentation restructure spec](2026-10-23-docs-restructure-design.md) holds the
rules every documentation PR applies.

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

# prov Roadmap

`prov` is a mature Python implementation of the W3C PROV Data Model. This page lists the
releases ahead, in order rather than by date, and the policies that govern them. What
each past release contained is in [HISTORY.md](HISTORY.md) and the
[release notes](https://github.com/trungdong/prov/releases); the design behind each
release is under [`planning/specs/`](planning/specs/).

## Next

| Release | Theme | Contents |
|---|---|---|
| **3.3.0** | Polish | A runtime immutability guard for `Identifier`, `QualifiedName` and `Literal` ([#444](https://github.com/trungdong/prov/issues/444)); parent-aware namespace reconciliation, so bundles stop copying the document's prefixes ([#449](https://github.com/trungdong/prov/issues/449)); PROV-N reader and writer refactors ([#450](https://github.com/trungdong/prov/issues/450)); wrapped, readable PROV-N output ([#131](https://github.com/trungdong/prov/issues/131)); a deduplication option for relations in `unified()` ([#124](https://github.com/trungdong/prov/issues/124)); a structural `diff()` that `prov-compare` reports instead of a bare yes or no; smaller items from the 3.2.1 reviews; follow-ups from the 3.2.2 typing work: a clear error for Python values that have no PROV form ([#482](https://github.com/trungdong/prov/issues/482)), public return types that match the runtime ([#491](https://github.com/trungdong/prov/issues/491)), namespace arguments that accept any mapping ([#492](https://github.com/trungdong/prov/issues/492)), and the whole test suite under strict mypy ([#494](https://github.com/trungdong/prov/issues/494)); PROV-N serialisation speed recovered after the 3.2.1 writer fixes ([#498](https://github.com/trungdong/prov/issues/498)); a Pygments lexer for PROV-N, registered as a `pygments.lexers` entry point. **Python 3.10 support dropped** under the policy below. Additive apart from the floor |
| **3.4.0** | Recording helpers | A recording-session helper that opens an activity, stamps its start and end and yields a scoped bundle; factories for the agent subtypes and `EmptyCollection` ([#260](https://github.com/trungdong/prov/issues/260)); a bundle as a first-class `prov:Bundle` entity ([#261](https://github.com/trungdong/prov/issues/261)); a how-to for recording AI agent runs. Scope to be confirmed by a spec. Additive |
| **3.5.0** | Storage | A store protocol with the in-memory document as its first implementation; `prov.sql`, a SQLite engine on the standard library with a versioned schema, provisional for one minor release; `find()` on bundles and documents, with predicates on record class, asserted type, attribute value and formal endpoint, as the protocol's query method; the canonical SQL mapping as a reference document for other engines. Additive |
| **Unscheduled** | | A PROV-CONSTRAINTS validation engine ([#62](https://github.com/trungdong/prov/issues/62)), once its home is settled; a serializer plugin registry via entry points, when an external format needs it; an optional pyoxigraph RDF backend, on demand |

Releases since 3.0.0 are additive. A 4.0 happens only if a breaking change accrues; none
is queued.

## Support policy

- **Python versions.** `prov` supports every CPython version that has not reached end of
  life and drops a version in the first release after its EOL. Python 3.10 reaches EOL on
  2026-10-31, so the 3.2.x line is the last with a 3.10 floor and 3.3.0 raises it to 3.11.
- **2.x.** Security fixes only, on the `2.x` branch; the latest is
  [2.5.3](https://github.com/trungdong/prov/releases/tag/2.5.3) (2026-08-08). Its public
  API stayed stable throughout the series: every documented name importable from its
  historic location, and no behaviour-changing bug fixes.
- **3.0.** The one release that changed compatibility. The
  [Upgrading to 3.0](docs/upgrading-3.0.md) guide lists every change and what to do
  about it.

## Released

| Version | Date | Theme |
|---|---|---|
| [3.2.2](https://github.com/trungdong/prov/releases/tag/3.2.2) | 2026-09-18 | Point release: attribute arguments type-check for callers under strict mypy and pyright ([#474](https://github.com/trungdong/prov/issues/474)); `add_attributes` accepts a generator; non-`dict` mappings are read through `items()` |
| [3.2.1](https://github.com/trungdong/prov/releases/tag/3.2.1) | 2026-09-13 | Point release: PROV-N parser corrections from a by-eye verification against ProvToolbox and PLEAD documents; `argparse.FileType` removed from the CLI |
| [3.2.0](https://github.com/trungdong/prov/releases/tag/3.2.0) | 2026-09-12 | Two-way PROV-N with `strict`, `default` and `lenient` profiles ([#122](https://github.com/trungdong/prov/issues/122)); benchmark suite with a CI regression check; measured speed-ups |
| [3.1.1](https://github.com/trungdong/prov/releases/tag/3.1.1) | 2026-09-10 | Point release: hardening from the September 2026 audit; community scaffolding; first Zenodo DOI |
| [3.1.0](https://github.com/trungdong/prov/releases/tag/3.1.0) | 2026-08-07 | PROV-JSONLD serialisation |
| [3.0.0](https://github.com/trungdong/prov/releases/tag/3.0.0) | 2026-07-27 | Compatibility release: `unified()` per PROV-CONSTRAINTS, no unconditional runtime dependencies, the behaviour-changing fixes from the conformance audit |
| [2.5.1](https://github.com/trungdong/prov/releases/tag/2.5.1) | 2026-07-13 | `prov.read()` polish; Codacy fixes |
| [2.5.0](https://github.com/trungdong/prov/releases/tag/2.5.0) | 2026-07-13 | Low-risk fixes and additions from the audit triage, including chaining methods ([#154](https://github.com/trungdong/prov/issues/154)) |
| Conformance audit *(not a release)* | 2026-07-11 | The library checked against PROV-DM, PROV-N, PROV-XML, PROV-JSON, PROV-O and PROV-CONSTRAINTS, giving the [conformance matrix](docs/reference/conformance.md) and the 3.0.0 fix list |
| [2.4.0](https://github.com/trungdong/prov/releases/tag/2.4.0) | 2026-07-06 | Documentation overhaul; 3.0 deprecation signposting |
| [2.3.0](https://github.com/trungdong/prov/releases/tag/2.3.0) | 2026-07-05 | Type annotations and `py.typed`; coverage floor; **Python 3.9 dropped** |
| [2.2.0](https://github.com/trungdong/prov/releases/tag/2.2.0) | 2026-07-03 | Tooling modernisation; release automation |

Earlier releases are listed in [HISTORY.md](HISTORY.md).

## Feedback

Comment in [Discussions](https://github.com/trungdong/prov/discussions), or open an issue for a
specific request.

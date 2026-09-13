# prov Roadmap

`prov` is a mature Python implementation of the W3C PROV Data Model. This page lists the
releases ahead, in order rather than by date, and the policies that govern them. What
each past release contained is in [HISTORY.md](HISTORY.md) and the
[release notes](https://github.com/trungdong/prov/releases); the design behind each
release is under [`planning/specs/`](planning/specs/).

## Next

| Release | Theme | Contents |
|---|---|---|
| **3.3.0** | Polish | A runtime immutability guard for `Identifier`, `QualifiedName` and `Literal` ([#444](https://github.com/trungdong/prov/issues/444)); parent-aware namespace reconciliation, so bundles stop copying the document's prefixes ([#449](https://github.com/trungdong/prov/issues/449)); PROV-N reader and writer refactors ([#450](https://github.com/trungdong/prov/issues/450)); wrapped, readable PROV-N output ([#131](https://github.com/trungdong/prov/issues/131)); a deduplication option for relations in `unified()` ([#124](https://github.com/trungdong/prov/issues/124)); a structural `diff()` that `prov-compare` reports instead of a bare yes or no; smaller items from the 3.2.1 reviews. **Python 3.10 support dropped** under the policy below. Additive apart from the floor |
| **Later** *(not yet scheduled)* | Candidates | A serializer plugin registry via entry points; a recording-session helper and agent-subtype factories ([#260](https://github.com/trungdong/prov/issues/260), [#261](https://github.com/trungdong/prov/issues/261)); `find()` with class, type, attribute and endpoint predicates; a PROV-CONSTRAINTS validation engine ([#62](https://github.com/trungdong/prov/issues/62)); a store protocol in the core with SQL realisations outside it. Grouped into releases as each is approved |

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

Comment on the [roadmap tracking issue](https://github.com/trungdong/prov/issues/181) or in
[Discussions](https://github.com/trungdong/prov/discussions).

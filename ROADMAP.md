# prov Roadmap

`prov` is a mature Python implementation of the W3C PROV Data Model. This roadmap
summarises where the library is heading: a staged programme of modernisation and
hardening (tooling, type hints, tests, documentation, standards conformance),
a batch of long-standing bug fixes, and new serialization capabilities.

The full design detail lives in the
[modernisation roadmap design](docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md).
This page is the community-facing summary. The table below shows the **order** of
planned releases, not dates — timelines depend on available effort.

## API-stability promise for 2.x

Throughout the 2.x series, `prov` keeps its public API stable:

- Every documented name stays importable from its historic location. Existing code
  that imports from `prov`, `prov.model`, `prov.serializers`, and friends continues
  to work unchanged.
- No behaviour-changing bug fixes land in 2.x. Where a fix would alter existing
  output or semantics, it is documented and deferred to **3.0**, so upgrading within
  2.x is always safe.

3.0 is the single release allowed to introduce compatibility changes, and they are
signposted in advance (see below). For most users, upgrading to 3.0 should require no
code changes.

## Planned releases

| Release | Theme | Highlights |
|---|---|---|
| **2.2.0** *(released 2026-07-03)* | Tooling & bug fixes | Modernised linting/formatting and test tooling; CI refresh; release automation. Bug fixes: graphics output regression ([#164](https://github.com/trungdong/prov/issues/164)), matplotlib as an optional extra ([#166](https://github.com/trungdong/prov/issues/166)), PROV-XML default-namespace parsing ([#155](https://github.com/trungdong/prov/issues/155)). |
| **2.3.0** *(released 2026-07-05)* | Typing & test coverage | Complete type annotations across the codebase and ship `py.typed` (PEP 561), so downstream projects get real type checking against `prov`'s API. Coverage gaps closed, including the CLI scripts and format auto-detection. Progressively stricter lint and type-check rules enforced in CI as modules are annotated. A dependency audit documents why each runtime dependency exists, aiming for the smallest possible footprint. **Python 3.9 support dropped** (originally planned for 3.0, pulled forward because security fixes in transitive dependencies are only released for Python 3.10+). One sanctioned diagnostic tweak: serializer-lookup and CLI errors now chain the original exception (`__cause__`); exception types and messages are unchanged, so this stays within the 2.x stability promise. |
| **2.4.0** *(released 2026-07-06)* | Documentation & internals | Refreshed, reorganised documentation (tutorials, how-to guides, API reference, explanations), including guides for graphics export ([#141](https://github.com/trungdong/prov/issues/141)) and for the `prov-convert`/`prov-compare` CLI tools ([#83](https://github.com/trungdong/prov/issues/83)). Internal restructuring behind the stable public API, plus deprecation warnings signposting the 3.0 changes. **This is the deprecation-signposting release**: importing `prov.dot`/`prov.graph` now emits a `DeprecationWarning` naming the future `prov[dot]`/`prov[graph]` extras, and `unified()` emits a `FutureWarning` about the PROV-CONSTRAINTS rework below; see the new [Upgrading to 3.0](docs/upgrading-3.0.md) guide for the full list and what to do. |
| **Conformance audit** *(completed 2026-07-11)* | Standards conformance (pre-3.0, not a release) | The pre-3.0 audit of the library against W3C PROV-DM, PROV-N, PROV-XML, PROV-JSON, PROV-O and PROV-CONSTRAINTS. Outcomes: a [conformance matrix](docs/reference/conformance.md) published in the docs and revisited at every release; schema-validation tests added (the W3C PROV-XML XSD closure and the PROV-JSON member-submission schema, both vendored); PROV-N grammar and PROV-O mapping audits; a PROV-CONSTRAINTS unification gap analysis with a 153-case test corpus (the authority for the 3.0 `unified()` rework). 20 new issues filed by the audit ([#235](https://github.com/trungdong/prov/issues/235)–[#240](https://github.com/trungdong/prov/issues/240), [#244](https://github.com/trungdong/prov/issues/244), [#246](https://github.com/trungdong/prov/issues/246), [#248](https://github.com/trungdong/prov/issues/248)–[#251](https://github.com/trungdong/prov/issues/251), [#253](https://github.com/trungdong/prov/issues/253), [#254](https://github.com/trungdong/prov/issues/254), [#256](https://github.com/trungdong/prov/issues/256)–[#261](https://github.com/trungdong/prov/issues/261)), and every finding triaged with maintainer sign-off into the 3.0.0 milestone (behaviour/output-changing fixes), a new 2.5.0 milestone (cheap, non-breaking items), or the post-3.0 `backlog` label. The PROV-CONSTRAINTS validation engine ([#62](https://github.com/trungdong/prov/issues/62)) remains out of scope (backlog). |
| **2.5.0** | Low-risk fixes & additions | Small, non-breaking items carved out by the conformance-audit triage: record-level chaining convenience methods ([#154](https://github.com/trungdong/prov/issues/154)), the agent-subtype `prov:type` documentation fix ([#236](https://github.com/trungdong/prov/issues/236)), `prov.read()` auto-detection of PROV-XML ([#239](https://github.com/trungdong/prov/issues/239)), `serialize()` handling of non-`IOBase` file-likes ([#240](https://github.com/trungdong/prov/issues/240)), and PROV-XML deserializer error handling ([#254](https://github.com/trungdong/prov/issues/254)). All are additive or touch only already-broken paths, staying within the 2.x stability promise. |
| **3.0.0** | Compatibility release | The one release allowed to break compatibility (see the explicit list below). |
| **3.1.0** | PROV-JSONLD support | A new serializer and deserializer for [PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/), the W3C member submission for representing PROV-DM natively in JSON-LD. Purely additive. |
| **3.2.0** | Two-way PROV-N | A parser for [PROV-N](https://www.w3.org/TR/prov-n/), built from the specification's grammar, making the notation readable as well as writable (today `prov` can only write PROV-N). Purely additive. |

## What changes in 3.0

3.0 batches every compatibility-affecting change into a single, clearly signposted
release. It was preceded by a standards-conformance audit against W3C PROV-DM and its
companion specifications (completed 2026-07-11, see the table above), whose findings
feed into this list. The planned changes are:

- ~~**Python floor raised to 3.10**~~ *Moved into 2.3.0* (July 2026): security fixes
  for several transitive dependencies are only published for Python 3.10+, so keeping
  a 3.9 resolution branch pinned the lock file to versions with known CVEs. The support
  policy going forward is to support all non-EOL CPython versions and to drop a version
  in the next release after it reaches end of life.
- **`rdflib` version floor raised**, shedding compatibility shims for older releases.
- **Smaller install footprint**, informed by the 2.3.0 dependency audit:
  `python-dateutil` replaced by the standard library, and the graphics/graph-interop
  dependencies (`pydot`, `networkx`) likely moving behind optional extras, so a plain
  `pip install prov` pulls in only what the core data model needs.
- **Unification reworked to follow [PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/)**:
  `unified()` currently just merges the attributes of records that share an
  identifier; in 3.0 it applies the specification's merging rules (key constraints
  and term unification), rejecting merges the spec disallows instead of silently
  combining records. The
  [gap analysis](docs/superpowers/specs/2026-07-10-unification-gap-analysis.md) was
  produced by the pre-3.0 conformance audit (completed 2026-07-11) and is the authority
  for this rework.
- **Behaviour-changing bug fixes**, each individually reviewed with tests showing the
  old and new behaviour:
  - [#34](https://github.com/trungdong/prov/issues/34) — merging attributes with the
    same value but different types (folded into the unification rework above).
  - [#77](https://github.com/trungdong/prov/issues/77) — comparison of `Decimal`
    literals.
  - [#89](https://github.com/trungdong/prov/issues/89) — handling of literals with and
    without an explicit datatype.
  - [#168](https://github.com/trungdong/prov/issues/168) — `xsd:QName` typing in
    PROV-JSON output (an interop-affecting change).
  - Plus the further fixes surfaced by the conformance audit — now all filed and
    assigned to the 3.0.0 milestone on GitHub (serializer conformance fixes such as
    [#235](https://github.com/trungdong/prov/issues/235),
    [#250](https://github.com/trungdong/prov/issues/250), and the
    [#253](https://github.com/trungdong/prov/issues/253) `unified()` umbrella above).

The [Upgrading to 3.0](docs/upgrading-3.0.md) guide, published starting in 2.4.0, tracks
this list in detail alongside what to do for each change. The intent is that most users
need no code changes; the guide demonstrates the exceptions.

## Feedback

Community input is welcome, especially on the 3.0 compatibility changes and the
priority of open issues. Please share your thoughts on the
[roadmap tracking issue](https://github.com/trungdong/prov/issues/181),
or browse and comment on the
[issue tracker](https://github.com/trungdong/prov/issues).

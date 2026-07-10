# Conformance audit findings — Phase 3.5 (roadmap steps 28–32)

**Status:** In progress. Working document; each audit task appends its section.
**Triage:** Section 6 is filled by the triage task (step 31) after maintainer sign-off.

## 0. Baseline (recorded before any audit work)

- Test suite tally: `932 passed, 16 skipped, 6 xfailed, 95 warnings in 8.09s` (`uv run pytest`,
  2026-07-10, branch `audit/conformance-matrix` at the tip of `master`
  (c195be7)). The 95 warnings are pytest's own capture-warnings summary of `UserWarning`s
  intentionally raised by `provrdf.py:692` inside three existing tests
  (`test_json_to_ttl_match`, `test_membership_{1,2,3}[rdf]`, plus the parametrized statement
  tests) — pre-existing, unrelated to this task, not touched.
- ruff: `uv run ruff check src/` → `All checks passed!`
- mypy: `uv run mypy src` → `Success: no issues found in 17 source files`
- sphinx: `uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html`
  → `build succeeded.` (0 warnings)

## 1. Conformance matrix findings (step 28)

Findings surfaced while building `docs/reference/conformance.md`, verified against source:

- **No dedicated factories for the PROV-DM agent subtypes** (`Person`, `Organization`,
  `SoftwareAgent`, PROV-DM §5.3.1). `ProvBundle.agent()` (`src/prov/model/bundle.py:812`)
  creates a plain `prov:Agent`; the subtype must be added by hand via
  `other_attributes={PROV_TYPE: "prov:Person"}` (or equivalent). This is already documented as
  intentional in `docs/explanation/prov-dm.md:111-114`, and `ADDITIONAL_N_MAP`
  (`src/prov/constants.py:75-84`) does carry PROV-N keywords for all three
  (`person`/`organization`/`softwareAgent`) plus `plan`, so the vocabulary constants exist —
  only the convenience factories are missing. Feature gap, not a defect; candidate for 3.0
  triage (new small factories, or leave as documented `prov:type` idiom).
- **No dedicated factory for `EmptyCollection`** (PROV-DM §5.6). `PROV["EmptyCollection"]` is a
  real constant with a PROV-N keyword (`ADDITIONAL_N_MAP`, `src/prov/constants.py:83`) and a
  `PROV_BASE_CLS` entry mapping it to `PROV_ENTITY` (`src/prov/constants.py:120`), so the
  round-trip machinery understands the type — but `ProvBundle.collection()`
  (`src/prov/model/bundle.py:1221`) has no `empty=` flag or sibling `empty_collection()` method.
  Same shape as the agent-subtype gap above: vocabulary present, convenience factory absent.
  Feature gap, candidate for 3.0 triage.
- **`prov:Bundle` as a first-class entity type (PROV-DM §5.4.2) is not implemented at all** —
  not even as a documented `prov:type` idiom. `PROV_BUNDLE` (`src/prov/constants.py:42`) exists
  as a QualifiedName constant with a PROV-N keyword mapping (`"bundle"`,
  `src/prov/constants.py:69`) and a `PROV_BASE_CLS` entry, but grepping the full source tree
  shows it is consumed only by `src/prov/dot.py` (node styling for the `folder` shape) and is
  never referenced by any serializer (`provjson.py`, `provxml.py`, `provrdf.py`, `provn.py`) or
  by any `ProvBundle`/`ProvDocument` method. `ProvBundle.get_provn()`
  (`src/prov/model/bundle.py:315-350`) emits the PROV-N `bundle <id> ... endBundle` block
  structurally (via `is_document()`/`is_bundle()` branching), not through a `prov:Bundle`-typed
  record and not through the `PROV_N_MAP["bundle"]` keyword — that keyword is present in the
  lookup table but is dead code as far as the current model/serializer implementation goes. In
  other words: `prov` implements bundle *containment* (§5.4.1, `ProvDocument.bundle()` /
  `add_bundle()`) but not the PROV-DM notion of a bundle's identifier also denoting an entity of
  type `prov:Bundle` for provenance-of-provenance assertions (§5.4.2) — a user cannot currently
  attribute a bundle to an agent or otherwise make first-class PROV statements about the bundle
  itself as an entity, because there is no supported path from `ProvBundle.identifier` to a
  `ProvEntity` typed `prov:Bundle` in the same document. Feature gap (and worth flagging the
  unused `PROV_N_MAP` entry as very minor dead-weight); candidate for 3.0 triage.
- **Issue #154 re-read**: title is "Add convenient assertion methods for revision, quotation,
  primary source, mention & influence records". The bundle-level factories it mentions in
  passing (`revision()`, `quotation()`, `primary_source()`, `mention()`, `influence()`) **all
  already exist** on `ProvBundle` (`src/prov/model/bundle.py:1011,1056,1101,1194,935`) with
  camelCase aliases (`wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource`/`mentionOf`/
  `wasInfluencedBy`, `bundle.py:1358-1364`) — but that was never what the issue was asking for.
  Its actual ask is **record-level (`ProvElement`) chaining methods**, the pattern demonstrated
  by the issue's own example, `e1.wasDerivedFrom(e2)`. Checked `records.py` directly:
  `ProvEntity` (`records.py:763-900`) already has `wasGeneratedBy`, `wasInvalidatedBy`,
  `wasDerivedFrom`, `wasAttributedTo`, `alternateOf`, `specializationOf`, `hadMember` as
  self-as-first-argument convenience methods that delegate to `self._bundle.<factory>(self,
  ...)` and return `self` for chaining — but genuinely lacks `wasRevisionOf`, `wasQuotedFrom`,
  `hadPrimarySource`, and `mentionOf`. Likewise `ProvActivity` (`records.py:900-1057`) has
  `used`, `wasInformedBy`, `wasStartedBy`, `wasEndedBy`, `wasAssociatedWith` but lacks
  `wasInfluencedBy`, and `ProvAgent` (`records.py:1131-1163`) has only `actedOnBehalfOf` and
  also lacks `wasInfluencedBy`. So issue #154's five requested methods are **all still
  missing**, exactly as filed: `ProvEntity.wasRevisionOf`, `ProvEntity.wasQuotedFrom`,
  `ProvEntity.hadPrimarySource`, `ProvEntity.mentionOf`, and `wasInfluencedBy` on all three of
  `ProvEntity`/`ProvActivity`/`ProvAgent`. Still open, valid, and narrowly scoped; recommend
  keeping it open and triaging in step 31 as a 2.x-safe additive feature (same shape as the
  agent-subtype/EmptyCollection gaps above — purely additive, no output/behaviour change to
  existing methods).
- **PROV-N metacharacter escaping (#223) applies generically**, not to one row: any concept
  whose identifier's local part contains a PROV-N metacharacter (`'`, `)`, `,`, `(`, `:`, `;`,
  `[`, `]`, `=`) produces invalid PROV-N text regardless of record type, because the bug is in
  `QualifiedName.provn_representation()` (`src/prov/identifier.py`), shared by every record. The
  matrix notes this once under the PROV-N column header rather than repeating it per row.
- **Round-trip skip/xfail counts reconciled exactly against the baseline** (`uv run pytest -q
  -rs -rx`): the `16 skipped` = 14 rdf-target "scruffy" skips in `test_statements.py` (2 each of
  generation/invalidation/usage, 4 each of start/end — `RDF_SCRUFFY_SKIP`, #217) + 2 unrelated
  `test_minimal_install.py` skips that are an artefact of running with both extras installed
  (`test_rdf_unavailable_raises_informative_error` / `test_xml_unavailable_raises_informative_error`
  skip themselves when `rdflib`/`lxml` *are* present — expected, not a conformance finding). The
  `6 xfailed` = 3 in `test_attributes.py` (`test_entity_with_one_type_attribute_decimal` for
  #77, `test_entity_with_multiple_attribute` and `test_entity_with_multiple_value_attribute` for
  #218) + 3 regression-guard xfails in `test_rdf.py`/`test_xml.py`
  (`test_float_precision_survives_rdf_roundtrip` #225,
  `test_qualified_delegation_pair_survives_rdf_roundtrip` #226,
  `test_empty_string_attribute_survives_xml_roundtrip` #224) — i.e. every one of #77/#217/#218/
  #224/#225/#226 has a live characterization test in the suite already; #223 (PROV-N escaping)
  has no dedicated xfail because PROV-N has no parser to round-trip through.
- **`prov:Bundle` PROV-N keyword row aside**: since `PROV_N_MAP["bundle"]` is unused by the
  actual `get_provn()` implementation (see above), the conformance matrix's PROV-N column for
  the "Bundle constructor" row describes the real, hand-written `bundle <id> ... endBundle`
  output rather than citing a keyword lookup.

## 2. Formal attributes & PROV-DM §5 semantics (step 29)
## 3. Serializer mappings (step 30)
### 3.1 PROV-XML vs XSD
### 3.2 PROV-JSON vs member submission
### 3.3 PROV-N vs grammar
### 3.4 PROV-O vs mapping tables
## 4. Unification vs PROV-CONSTRAINTS (step 30b) — summary
See docs/superpowers/specs/2026-07-10-unification-gap-analysis.md (authority for step 36b).
## 5. Issues filed by this audit
| Issue | Finding | Section |
|---|---|---|
## 6. Triage (step 31) — proposed → approved
| Issue | Bucket (2.x / 3.0 / backlog) | Rationale |
|---|---|---|

## Out of scope (step 32)
The PROV-CONSTRAINTS validation engine (#62 — inferences, event ordering,
typing and impossibility checks) stays on the post-3.0 features backlog.
Only the unification/merging rules that back `unified()` are in scope.

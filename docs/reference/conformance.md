# Conformance matrix

This page tracks how each PROV-DM concept maps onto `prov`'s classes and factory methods, and
how well each serializer round-trips it. It is the audit artefact for Phase 3.5 of the
[modernisation roadmap](https://github.com/trungdong/prov/blob/master/ROADMAP.md) (roadmap step
28) and is **revisited at every release** as behaviour changes; a JSON-LD column is planned for
3.1.0 once the PROV-JSONLD serializer lands. For prose background on PROV-DM's six components and
how they group in `prov.model`, see {doc}`../explanation/prov-dm`; this page is the detailed,
verified-against-source reference underneath that explanation.

Every cell below was checked directly against the current source: model classes against
`src/prov/model/records.py`, factory methods and camelCase aliases against
`src/prov/model/bundle.py`, PROV-N keywords against `PROV_N_MAP` / `ADDITIONAL_N_MAP` in
`src/prov/constants.py`, and round-trip status against the shared test matrix
(`src/prov/tests/conftest.py::SHARED_TARGETS`, `test_statements.py`, `test_attributes.py`).

## Round-trip column key

- **JSON** / **XML** / **RDF** — whether the type round-trips (`deserialize(serialize(doc)) ==
  doc`) under the shared `fmt` test matrix (`SHARED_TARGETS = ("model", "json", "xml", "rdf")`
  in `conftest.py`). ✓ means every shared case for that concept passes cleanly; a caveat cites
  the tracking issue and says what still fails.
- **PROV-N** — PROV-N is **output-only**: `prov` has no PROV-N parser (issue
  [#122](https://github.com/trungdong/prov/issues/122), planned for 3.2.0), so there is no
  PROV-N round trip to test, only the keyword `get_provn()` emits.

More caveats apply across many rows rather than to one:

- **PROV-O representational limitation** (RDF, permanent — closed as
  [#217](https://github.com/trungdong/prov/issues/217)): 14 statement-level test cases assert
  two relations that share one identifier but differ only in `prov:time`; PROV-O has no
  conformant way to encode that. PROV-O reifies a relation as a single qualified node (e.g.
  `prov:qualifiedGeneration`) named directly by the relation's own identifier — one identifier
  is one RDF node — so a second relation asserting the same identifier can only add more
  triples to that one node, not create a second, distinguishable node; both `prov:atTime`
  values end up on the same `prov:qualifiedGeneration` node with no way to tell which value
  belongs to which asserted relation. There is no encoding that avoids this without either
  minting a synthetic per-statement IRI (losing the asserted identifier ↔ node correspondence)
  or fabricating unasserted statements by permuting attribute values on decode — both rejected
  as options during the 3.0 audit. Accordingly this is documented as a **permanent** limitation
  of the `rdf` target, not an open bug: the 14 test cases stay skipped for `rdf`
  (`RDF_SCRUFFY_SKIP` in `test_statements.py`), and decoding third-party RDF with this shape
  raises `prov.model.ProvException` naming the limitation and pointing back at this page. The
  historical Java reference implementation (ProvToolbox) collapses identically on encode — its
  own "scruffy" test fixtures produce one qualified node carrying both values as repeated
  triples, with no IRI minting — and dropped RDF support entirely in its 2.x line rather than
  keep the permutation-based decoder it once had. Only this same-identifier/differing-attribute
  construct is affected: `generation`/`usage`/`start`/`end`/`invalidation` round-trip cleanly in
  the general case, JSON/XML/PROV-N and the in-memory model are unaffected (the limitation is
  specific to the PROV-O encoding, not to `prov`'s object model), and plain serialization of
  such documents remains legal in 3.0 (`prov` never enforces structural constraints at
  assertion time, [#257](https://github.com/trungdong/prov/issues/257)) — only `unified()`
  gains conflict detection for records sharing an identifier with conflicting formal attributes,
  as part of the separate PROV-CONSTRAINTS rework described in {doc}`../upgrading-3.0`.
- **XML attribute-name escaping** (XML, permanent convention — closed as
  [#289](https://github.com/trungdong/prov/issues/289)): an attribute name is written as a
  PROV-XML child element tag, but its local part is not guaranteed to be a legal XML NCName
  (prov never enforces structural constraints at assertion time, #257) — it may start with a
  digit or contain characters such as `' ( ) , : ; [ ] =`. Rather than raising, the serializer
  escapes each NCName-illegal character using the `_xHHHH_` convention (the same one used by
  the OpenXML/SQL Server ecosystems for this exact problem: `_x` followed by 4 uppercase hex
  digits — 8 for codepoints beyond the Basic Multilingual Plane — then `_`), and the
  deserializer applies the inverse, so such names round-trip losslessly. A literal run that
  already looks like an escape sequence has its introducing `_` self-escaped as `_x005F_`, so
  the transform is always exactly invertible, including for prov's own output. Names that are
  already legal NCNames (including non-ASCII letters, which are legal NCName characters) are
  emitted unchanged — this is not a behaviour change for existing users. The one caveat: a
  third-party XML document containing a literal `_xHHHH_`-shaped attribute name will be
  unescaped on read, since the convention cannot distinguish an intentional escape sequence
  from one that merely looks like one.

The value-typing and literal-semantics gaps the audit recorded here — #77, #89, #168, #218,
#223, #225, #235, #238, #244, #246, #249, #251, #256, #259 — were fixed in 3.0; see
{doc}`../upgrading-3.0` and `HISTORY.rst` for the details.

## Component 1 — Entities and Activities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Entity §5.1.1 | {py:class}`~prov.model.ProvEntity` | `entity()` | `entity` | ✓ | ✓ | ✓ |
| Activity §5.1.2 | {py:class}`~prov.model.ProvActivity` | `activity()` | `activity` | ✓ | ✓ | ✓ |
| Generation §5.1.3 | {py:class}`~prov.model.ProvGeneration` | `generation()` / `wasGeneratedBy()` | `wasGeneratedBy` | ✓ | ✓ | ✓ (permanent PROV-O representational limitation for the 2 same-id/differing-time cases — see above) |
| Usage §5.1.4 | {py:class}`~prov.model.ProvUsage` | `usage()` / `used()` | `used` | ✓ | ✓ | ✓ (permanent PROV-O representational limitation for the 2 same-id/differing-time cases — see above) |
| Communication §5.1.5 | {py:class}`~prov.model.ProvCommunication` | `communication()` / `wasInformedBy()` | `wasInformedBy` | ✓ | ✓ | ✓ |
| Start §5.1.6 | {py:class}`~prov.model.ProvStart` | `start()` / `wasStartedBy()` | `wasStartedBy` | ✓ | ✓ | ✓ (permanent PROV-O representational limitation for the 4 same-id/differing-time cases — see above) |
| End §5.1.7 | {py:class}`~prov.model.ProvEnd` | `end()` / `wasEndedBy()` | `wasEndedBy` | ✓ | ✓ | ✓ (permanent PROV-O representational limitation for the 4 same-id/differing-time cases — see above) |
| Invalidation §5.1.8 | {py:class}`~prov.model.ProvInvalidation` | `invalidation()` / `wasInvalidatedBy()` | `wasInvalidatedBy` | ✓ | ✓ | ✓ (permanent PROV-O representational limitation for the 2 same-id/differing-time cases — see above) |

{py:class}`~prov.model.ProvEntity` additionally exposes `wasGeneratedBy()`/`wasInvalidatedBy()`
and {py:class}`~prov.model.ProvActivity` exposes
`used()`/`wasInformedBy()`/`wasStartedBy()`/`wasEndedBy()` as self-as-subject chaining
methods (`records.py`) — the table above lists the `ProvBundle` factories, which every relation
also has.

## Component 2 — Derivations

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Derivation §5.2.1 | {py:class}`~prov.model.ProvDerivation` | `derivation()` / `wasDerivedFrom()` | `wasDerivedFrom` | ✓ | ✓ | ✓ |
| Revision §5.2.2 | {py:class}`~prov.model.ProvDerivation` + `prov:Revision` type | `revision()` / `wasRevisionOf()` | `wasDerivedFrom` (plus `[prov:type='prov:Revision']`) | ✓ | ✓ | ✓ |
| Quotation §5.2.3 | {py:class}`~prov.model.ProvDerivation` + `prov:Quotation` type | `quotation()` / `wasQuotedFrom()` | `wasDerivedFrom` (plus `[prov:type='prov:Quotation']`) | ✓ | ✓ | ✓ |
| Primary Source §5.2.4 | {py:class}`~prov.model.ProvDerivation` + `prov:PrimarySource` type | `primary_source()` / `hadPrimarySource()` | `wasDerivedFrom` (plus `[prov:type='prov:PrimarySource']`) | ✓ | ✓ | ✓ |

Revision, quotation, and primary source are PROV-DM *subtypes* of derivation, not separate PROV-N
records: `prov` implements all four with the single {py:class}`~prov.model.ProvDerivation` class,
and the three subtype factories call `derivation()` then add the corresponding `prov:type`
(confirmed by inspection of `bundle.py:1011-1146`, and by running `get_provn()` on a `revision()`
record — it emits `wasDerivedFrom(..., [prov:type='prov:Revision'])`, not a `wasRevisionOf(...)`
keyword). `ADDITIONAL_N_MAP` does carry a `wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource`
keyword mapping for contexts (such as PROV-XML) that treat these as top-level types; PROV-N
output from this library always uses the base `wasDerivedFrom` form.

## Component 3 — Agents, Responsibility, and Influence

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Agent §5.3.1 | {py:class}`~prov.model.ProvAgent` | `agent()` | `agent` | ✓ | ✓ | ✓ |
| Person / Organization / SoftwareAgent §5.3.1 | via `prov:type` on {py:class}`~prov.model.ProvAgent` | none — see finding below | `person` / `organization` / `softwareAgent` (`ADDITIONAL_N_MAP`, not emitted directly by this library) | ✓ | ✓ | ✓ |
| Attribution §5.3.2 | {py:class}`~prov.model.ProvAttribution` | `attribution()` / `wasAttributedTo()` | `wasAttributedTo` | ✓ | ✓ | ✓ |
| Association §5.3.3 | {py:class}`~prov.model.ProvAssociation` | `association()` / `wasAssociatedWith()` | `wasAssociatedWith` | ✓ | ✓ | ✓ |
| Plan §5.3.3 | via `association(plan=...)` | — | — (plan is an ordinary entity referenced by the association's `plan` formal attribute) | ✓ | ✓ | ✓ |
| Delegation §5.3.4 | {py:class}`~prov.model.ProvDelegation` | `delegation()` / `actedOnBehalfOf()` | `actedOnBehalfOf` | ✓ | ✓ | ✓ |
| Influence §5.3.5 | {py:class}`~prov.model.ProvInfluence` | `influence()` / `wasInfluencedBy()` | `wasInfluencedBy` | ✓ | ✓ | ✓ |

**Finding:** PROV-DM defines Person, Organization, and SoftwareAgent as agent subtypes, and Plan
as an entity subtype used with associations. `prov` has no dedicated classes or factories for the
agent subtypes — you express them with `agent("ag", {PROV_TYPE: PROV["Person"]})` — while Plan
needs no special handling at all, since it is just an entity passed as the `plan=` argument to
`association()`. This is a documented, intentional design choice
(`docs/explanation/prov-dm.md:111-117`), not a defect; see finding log for the audit note.
Convenience factories for the three agent subtypes (together with `EmptyCollection`, see
Component 6) are now tracked as
[#260](https://github.com/trungdong/prov/issues/260).

## Component 4 — Bundles

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Bundle constructor §5.4.1 | {py:class}`~prov.model.ProvBundle` | `ProvDocument.bundle()` / `add_bundle()` | `bundle <id> ... endBundle` (structural, hand-emitted by `get_provn()`) | ✓ | ✓ | ✓ |
| Bundle type §5.4.2 | not implemented — see finding below | — | — | — | — | — |

**Finding:** PROV-DM §5.4.1 defines bundle *containment* — a named, nestable set of records —
which `prov` fully implements via `ProvDocument.bundle()`/`add_bundle()`; only a
{py:class}`~prov.model.ProvDocument` may contain named bundles (`is_document()`/`is_bundle()`
in `bundle.py` distinguish the two at runtime). §5.4.2 additionally lets a bundle's identifier
denote a first-class entity of type `prov:Bundle`, so that provenance-of-provenance (e.g. "who
asserted this bundle") can itself be expressed in PROV. That second half is **not implemented**:
the `PROV_BUNDLE` constant and its `PROV_N_MAP["bundle"]` keyword exist in `constants.py` but
are consumed only by `dot.py` (for node styling) — no serializer or
{py:class}`~prov.model.ProvBundle` method ever produces a `prov:Bundle`-typed entity, and
`get_provn()`'s `bundle <id> ... endBundle` output is generated structurally (branching on
`is_document()`), not through that keyword lookup. There is currently no supported way to
attribute a bundle to an agent as a first-class PROV statement. Tracked as
[#261](https://github.com/trungdong/prov/issues/261).

## Component 5 — Alternate Entities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Specialization §5.5.1 | {py:class}`~prov.model.ProvSpecialization` | `specialization()` / `specializationOf()` | `specializationOf` | ✓ | ✓ | ✓ |
| Alternate §5.5.2 | {py:class}`~prov.model.ProvAlternate` | `alternate()` / `alternateOf()` | `alternateOf` | ✓ | ✓ | ✓ (the RDF triple follows the PROV-DM argument order — `alternate(alt1, alt2)` emits `alt1 prov:alternateOf alt2` — since 3.0: [#258](https://github.com/trungdong/prov/issues/258)) |
| Mention (PROV-LINKS) | {py:class}`~prov.model.ProvMention` (subclass of {py:class}`~prov.model.ProvSpecialization`) | `mention()` / `mentionOf()` | `mentionOf` (emitted as a bare keyword, not the `prov:` prefix the PROV-Links grammar requires — this is a deliberate documented deviation: the bare form has been the de-facto output of reference implementations for the last decade and matches ProvToolbox's ANTLR grammar, so `provconvert` keeps parsing prov's output; closed as design decision 2026-07-20, [#248](https://github.com/trungdong/prov/issues/248)) | ✓ | ✓ | ✓ |

## Component 6 — Collections

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Collection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:Collection` type | `collection()` | `entity` (plus `[prov:type='prov:Collection']`) | ✓ | ✓ | ✓ |
| EmptyCollection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:EmptyCollection` type — no dedicated factory | none — see finding below | `entity` (plus `[prov:type='prov:EmptyCollection']`, keyword `emptyCollection` in `ADDITIONAL_N_MAP`, not emitted directly) | ✓ | ✓ | ✓ |
| Membership §5.6 | {py:class}`~prov.model.ProvMembership` | `membership()` / `hadMember()` | `hadMember` | ✓ | ✓ | ✓ |

**Finding:** like collections, `EmptyCollection` is a real PROV-DM type with a real
`ADDITIONAL_N_MAP`/`PROV_BASE_CLS` entry in `constants.py`, so the round-trip machinery
understands it — but there is no `empty_collection()` factory or `empty=` flag on `collection()`
to set the type for you; you would add `prov:type: PROV["EmptyCollection"]` by hand via
`other_attributes`. Tracked (together with the agent-subtype factories, see Component 3) as
[#260](https://github.com/trungdong/prov/issues/260).

## Additional attributes

Five PROV-DM attributes are usable on (almost) any record and are exercised directly by the
shared attribute test matrix (`test_attributes.py`, `ATTRIBUTE_VALUES` in
`attribute_values.py`) and by `test_statements.py`'s `add_label`/`add_locations`/`add_types`/
`add_value` helpers:

| Attribute | Constant (`prov.constants`) | Round-trip notes |
| --- | --- | --- |
| `prov:label` | `PROV_LABEL` | ✓ JSON/XML/RDF, including language-tagged literals and multiple values on one record. |
| `prov:location` | `PROV_LOCATION` | ✓ JSON/XML/RDF across the full `ATTRIBUTE_VALUES` datatype corpus. |
| `prov:role` | `PROV_ROLE` | ✓ JSON/XML/RDF; used throughout the qualified-relation tests (association, usage, generation, ...). |
| `prov:type` | `PROV_TYPE` | ✓ JSON/XML/RDF, including mixed multi-datatype attribute sets on one record (`xsd:decimal` value-space equality and multi-datatype RDF fidelity fixed in 3.0: [#77](https://github.com/trungdong/prov/issues/77), [#218](https://github.com/trungdong/prov/issues/218)). |
| `prov:value` | `PROV_VALUE` | ✓ JSON/XML/RDF. |

## Maintenance

This matrix reflects the codebase as of the Phase 3.5 conformance audit (roadmap steps 28–32,
completed 2026-07-11), refreshed for the 3.0 value-typing and literal-semantics conformance
fixes, and should be revisited at each release as serializers change or issues close. Beyond the per-format round trips above, the audit also confirmed that
`ProvBundle.unified()` performs an identifier-keyed attribute union rather than
[PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/) merging — tracked as the umbrella
issue [#253](https://github.com/trungdong/prov/issues/253), with the full gap analysis in the
audit findings; the rework is scheduled for 3.0. Release 3.1.0 adds a
PROV-JSONLD serializer; when that lands, this page gains a JSON-LD column
alongside JSON/XML/RDF. See {doc}`../explanation/prov-dm` for the conceptual background behind
each component, and {doc}`model` for the full class/method API reference.

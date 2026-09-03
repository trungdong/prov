# Conformance matrix

This page maps each PROV-DM concept onto `prov`'s classes and factory methods, and shows how
well each serializer round-trips it. It's revisited at every release — last revised for the
3.1.0 release (2026-08-07), which added the **PROV-JSONLD** serializer/deserializer
(`format="jsonld"`, {doc}`../howto/provjsonld`) and its JSON-LD column below.

Every cell is checked directly against the current source code and the shared test suite, not
against the spec text alone. For conceptual background on PROV-DM's six components, see
{doc}`../explanation/prov-dm`; this page is the detailed reference underneath that explanation.

## Round-trip column key

- **JSON** / **XML** / **RDF** / **JSON-LD** — ✓ means `deserialize(serialize(doc)) == doc` for
  every shared test case; otherwise a caveat below explains what still fails and why. JSON-LD
  here means [PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/) (a W3C member
  submission), implemented natively with no `rdflib`/JSON-LD-processor dependency. Its decoder
  only accepts the submission's canonical compacted shape, not arbitrary expanded or flattened
  JSON-LD, plus [ProvToolbox](https://lucmoreau.github.io/ProvToolbox/)'s `prov:`-prefixed
  spellings of the type and special terms.
- **PROV-N** — output-only: `prov` has no PROV-N parser (issue
  [#122](https://github.com/trungdong/prov/issues/122), planned for 3.2.0), so there's nothing
  to round-trip — the column would just show what `get_provn()` emits.

More caveats apply across many rows rather than to one:

- **Two relations, same identifier, different `prov:time`** (RDF, permanent —
  [#217](https://github.com/trungdong/prov/issues/217)): PROV-O represents a relation such as
  `wasGeneratedBy` as one RDF node named by the relation's own identifier. If two asserted
  relations share an identifier but differ only in `prov:time`, PROV-O has no way to keep their
  `prov:atTime` values apart — both end up on the same node. This affects only that exact
  construct: a normal document round-trips cleanly, and JSON, XML, PROV-N and the in-memory model
  are unaffected. Decoding third-party RDF shaped this way raises `prov.model.ProvException`
  naming the limitation. This is a permanent limitation, not an open bug — minting a synthetic
  IRI or guessing at attribute values on decode were both considered and rejected. Plain
  serialization of such documents remains legal (`prov` never enforces structural constraints at
  assertion time, [#257](https://github.com/trungdong/prov/issues/257)); `unified()` does detect
  the conflict, as part of PROV-CONSTRAINTS support (see {doc}`../upgrading-3.0`).
- **No `mentionOf` term in PROV-JSONLD** (JSON-LD, permanent —
  [#248](https://github.com/trungdong/prov/issues/248)): the PROV-JSONLD submission defines no
  term for PROV-DM's Mention relation, so there's no shape `prov` could encode it in.
  Serializing or deserializing a document containing a
  {py:class}`~prov.model.ProvMention` record raises
  `prov.serializers.provjsonld.ProvJSONLDException`. Every other relation and element round-trips
  through PROV-JSONLD cleanly, including the same-identifier/differing-time cases above — PROV-O
  is the one that has trouble there, not PROV-JSONLD.
- **RDF's `json-ld` output is not PROV-JSONLD**: `rdf_format="json-ld"` runs the PROV-O graph
  through rdflib's generic RDF→JSON-LD writer, not the PROV-JSONLD submission's compacted shape
  — the two just share a name, and it inherits every PROV-O limitation above. For actual
  PROV-JSONLD, use `format="jsonld"` instead.
- **XML escapes illegal attribute names** (XML, permanent convention —
  [#289](https://github.com/trungdong/prov/issues/289)): an attribute name is written as a
  PROV-XML child element tag, but its local part isn't guaranteed to be a legal XML NCName — it
  may start with a digit or contain characters such as `' ( ) , : ; [ ] =`. `prov` escapes each
  illegal character using the `_xHHHH_` convention (the same one OpenXML/SQL Server use for this
  problem) and reverses it on read, so such names round-trip losslessly; already-legal names are
  emitted unchanged. One caveat: a third-party document that already contains a literal
  `_xHHHH_`-shaped attribute name will be unescaped on read, since the convention can't tell an
  intentional escape from one that merely looks like one.
- **Some attribute keys can fail to round-trip through RDF** (RDF, open bug —
  [#341](https://github.com/trungdong/prov/issues/341)): an attribute key whose local part *ends*
  in one of `= ' , : ; [ ]` can fail to decode from PROV-O, because rdflib can't split that IRI
  into namespace + local part without some other identifier in the same namespace having already
  registered it during decoding. So the failure is order-dependent rather than universal — the
  same key round-trips fine whenever a clean sibling in its namespace happens to decode first.
  Attribute *values* aren't affected, and PROV-N, PROV-JSON and PROV-XML all round-trip these
  keys correctly — PROV-O is the odd one out, as with the same-identifier limitation above.
  Unlike that one, this is not a decided permanent limitation — it remains open for a fix. See
  the issue for the exact conditions and affected code paths.

## Component 1 — Entities and Activities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Entity §5.1.1 | {py:class}`~prov.model.ProvEntity` | `entity()` | `entity` | ✓ | ✓ | ✓ | ✓ |
| Activity §5.1.2 | {py:class}`~prov.model.ProvActivity` | `activity()` | `activity` | ✓ | ✓ | ✓ | ✓ |
| Generation §5.1.3 | {py:class}`~prov.model.ProvGeneration` | `generation()` / `wasGeneratedBy()` | `wasGeneratedBy` | ✓ | ✓ | ✓ (permanent PROV-O limitation for the 2 same-id/differing-time cases — see above) | ✓ |
| Usage §5.1.4 | {py:class}`~prov.model.ProvUsage` | `usage()` / `used()` | `used` | ✓ | ✓ | ✓ (permanent PROV-O limitation for the 2 same-id/differing-time cases — see above) | ✓ |
| Communication §5.1.5 | {py:class}`~prov.model.ProvCommunication` | `communication()` / `wasInformedBy()` | `wasInformedBy` | ✓ | ✓ | ✓ | ✓ |
| Start §5.1.6 | {py:class}`~prov.model.ProvStart` | `start()` / `wasStartedBy()` | `wasStartedBy` | ✓ | ✓ | ✓ (permanent PROV-O limitation for the 4 same-id/differing-time cases — see above) | ✓ |
| End §5.1.7 | {py:class}`~prov.model.ProvEnd` | `end()` / `wasEndedBy()` | `wasEndedBy` | ✓ | ✓ | ✓ (permanent PROV-O limitation for the 4 same-id/differing-time cases — see above) | ✓ |
| Invalidation §5.1.8 | {py:class}`~prov.model.ProvInvalidation` | `invalidation()` / `wasInvalidatedBy()` | `wasInvalidatedBy` | ✓ | ✓ | ✓ (permanent PROV-O limitation for the 2 same-id/differing-time cases — see above) | ✓ |

{py:class}`~prov.model.ProvEntity` additionally exposes `wasGeneratedBy()`/`wasInvalidatedBy()`
and {py:class}`~prov.model.ProvActivity` exposes
`used()`/`wasInformedBy()`/`wasStartedBy()`/`wasEndedBy()` as self-as-subject chaining
methods — the table above lists the `ProvBundle` factories, which every relation also has.

## Component 2 — Derivations

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Derivation §5.2.1 | {py:class}`~prov.model.ProvDerivation` | `derivation()` / `wasDerivedFrom()` | `wasDerivedFrom` | ✓ | ✓ | ✓ | ✓ |
| Revision §5.2.2 | {py:class}`~prov.model.ProvDerivation` + `prov:Revision` type | `revision()` / `wasRevisionOf()` | `wasDerivedFrom` (plus `[prov:type='prov:Revision']`) | ✓ | ✓ | ✓ | ✓ |
| Quotation §5.2.3 | {py:class}`~prov.model.ProvDerivation` + `prov:Quotation` type | `quotation()` / `wasQuotedFrom()` | `wasDerivedFrom` (plus `[prov:type='prov:Quotation']`) | ✓ | ✓ | ✓ | ✓ |
| Primary Source §5.2.4 | {py:class}`~prov.model.ProvDerivation` + `prov:PrimarySource` type | `primary_source()` / `hadPrimarySource()` | `wasDerivedFrom` (plus `[prov:type='prov:PrimarySource']`) | ✓ | ✓ | ✓ | ✓ |

Revision, quotation, and primary source are PROV-DM *subtypes* of derivation, not separate PROV-N
records: `prov` implements all four with the single {py:class}`~prov.model.ProvDerivation` class,
and the three subtype factories call `derivation()` then add the corresponding `prov:type` —
`get_provn()` on a `revision()` record emits `wasDerivedFrom(..., [prov:type='prov:Revision'])`,
not a `wasRevisionOf(...)` keyword. `ADDITIONAL_N_MAP` does carry a
`wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource` keyword mapping for contexts (such as
PROV-XML) that treat these as top-level types, but PROV-N output from this library always uses
the base `wasDerivedFrom` form.

## Component 3 — Agents, Responsibility, and Influence

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agent §5.3.1 | {py:class}`~prov.model.ProvAgent` | `agent()` | `agent` | ✓ | ✓ | ✓ | ✓ |
| Person / Organization / SoftwareAgent §5.3.1 | via `prov:type` on {py:class}`~prov.model.ProvAgent` | none — see finding below | `person` / `organization` / `softwareAgent` (`ADDITIONAL_N_MAP`, not emitted directly by this library) | ✓ | ✓ | ✓ | ✓ |
| Attribution §5.3.2 | {py:class}`~prov.model.ProvAttribution` | `attribution()` / `wasAttributedTo()` | `wasAttributedTo` | ✓ | ✓ | ✓ | ✓ |
| Association §5.3.3 | {py:class}`~prov.model.ProvAssociation` | `association()` / `wasAssociatedWith()` | `wasAssociatedWith` | ✓ | ✓ | ✓ | ✓ |
| Plan §5.3.3 | via `association(plan=...)` | — | — (plan is an ordinary entity referenced by the association's `plan` formal attribute) | ✓ | ✓ | ✓ | ✓ |
| Delegation §5.3.4 | {py:class}`~prov.model.ProvDelegation` | `delegation()` / `actedOnBehalfOf()` | `actedOnBehalfOf` | ✓ | ✓ | ✓ | ✓ |
| Influence §5.3.5 | {py:class}`~prov.model.ProvInfluence` | `influence()` / `wasInfluencedBy()` | `wasInfluencedBy` | ✓ | ✓ | ✓ | ✓ |

**Finding:** PROV-DM defines Person, Organization, and SoftwareAgent as agent subtypes, and Plan
as an entity subtype used with associations. `prov` has no dedicated classes for the agent
subtypes — express them with `agent("ag", {PROV_TYPE: PROV["Person"]})` — and Plan needs no
special handling at all, since it's just an entity passed as the `plan=` argument to
`association()`. This is an intentional design choice, not a defect (see
{doc}`../explanation/prov-dm`). Convenience factories for the three agent subtypes, together
with `EmptyCollection` (see Component 6), are tracked as
[#260](https://github.com/trungdong/prov/issues/260).

## Component 4 — Bundles

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bundle constructor §5.4.1 | {py:class}`~prov.model.ProvBundle` | `ProvDocument.bundle()` / `add_bundle()` | `bundle <id> ... endBundle` (structural, hand-emitted by `get_provn()`) | ✓ | ✓ | ✓ | ✓ |
| Bundle type §5.4.2 | not implemented — see finding below | — | — | — | — | — | — |

**Finding:** PROV-DM §5.4.1 defines bundle *containment* — a named, nestable set of records —
which `prov` fully implements via `ProvDocument.bundle()`/`add_bundle()`; only a
{py:class}`~prov.model.ProvDocument` may contain named bundles. §5.4.2 additionally lets a
bundle's identifier denote a first-class entity of type `prov:Bundle`, so that
provenance-of-provenance (e.g. "who asserted this bundle") can itself be expressed in PROV. That
second half is **not implemented**: no serializer or {py:class}`~prov.model.ProvBundle` method
ever produces a `prov:Bundle`-typed entity, so there is currently no supported way to attribute a
bundle to an agent as a first-class PROV statement. Tracked as
[#261](https://github.com/trungdong/prov/issues/261).

## Component 5 — Alternate Entities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Specialization §5.5.1 | {py:class}`~prov.model.ProvSpecialization` | `specialization()` / `specializationOf()` | `specializationOf` | ✓ | ✓ | ✓ | ✓ |
| Alternate §5.5.2 | {py:class}`~prov.model.ProvAlternate` | `alternate()` / `alternateOf()` | `alternateOf` | ✓ | ✓ | ✓ (`alternate(alt1, alt2)` emits `alt1 prov:alternateOf alt2`, matching PROV-DM's argument order: [#258](https://github.com/trungdong/prov/issues/258)) | ✓ |
| Mention (PROV-LINKS) | {py:class}`~prov.model.ProvMention` (subclass of {py:class}`~prov.model.ProvSpecialization`) | `mention()` / `mentionOf()` | `mentionOf` (emitted as a bare keyword rather than the `prov:`-prefixed form the PROV-Links grammar technically requires — a deliberate deviation matching the de-facto output of reference implementations, so `provconvert` still parses it: [#248](https://github.com/trungdong/prov/issues/248)) | ✓ | ✓ | ✓ | ✗ (permanent PROV-JSONLD Mention gap — see above) |

## Component 6 — Collections

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Collection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:Collection` type | `collection()` | `entity` (plus `[prov:type='prov:Collection']`) | ✓ | ✓ | ✓ | ✓ |
| EmptyCollection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:EmptyCollection` type — no dedicated factory | none — see finding below | `entity` (plus `[prov:type='prov:EmptyCollection']`, keyword `emptyCollection` in `ADDITIONAL_N_MAP`, not emitted directly) | ✓ | ✓ | ✓ | ✓ |
| Membership §5.6 | {py:class}`~prov.model.ProvMembership` | `membership()` / `hadMember()` | `hadMember` | ✓ | ✓ | ✓ | ✓ |

**Finding:** like collections, `EmptyCollection` is a real PROV-DM type that the round-trip
machinery understands, but there's no `empty_collection()` factory or `empty=` flag on
`collection()` to set the type for you — you'd add `prov:type: PROV["EmptyCollection"]` by hand
via `other_attributes`. Tracked (together with the agent-subtype factories, see Component 3) as
[#260](https://github.com/trungdong/prov/issues/260).

## Additional attributes

Five PROV-DM attributes are usable on (almost) any record and are exercised directly by the
shared attribute test matrix:

| Attribute | Constant (`prov.constants`) | Round-trip notes |
| --- | --- | --- |
| `prov:label` | `PROV_LABEL` | ✓ JSON/XML/RDF/JSON-LD, including language-tagged literals and multiple values on one record. |
| `prov:location` | `PROV_LOCATION` | ✓ JSON/XML/RDF/JSON-LD across the full datatype corpus. |
| `prov:role` | `PROV_ROLE` | ✓ JSON/XML/RDF/JSON-LD; used throughout the qualified-relation tests (association, usage, generation, ...). |
| `prov:type` | `PROV_TYPE` | ✓ JSON/XML/RDF/JSON-LD, including mixed multi-datatype attribute sets on one record. |
| `prov:value` | `PROV_VALUE` | ✓ JSON/XML/RDF/JSON-LD. |

## Maintenance

This page should be revisited at each release as serializers change or issues close. For
merge-time conformance (PROV-CONSTRAINTS unification, not covered by the round-trip tables
above), see {doc}`../explanation/unification-flattening`. For conceptual background on each
component, see {doc}`../explanation/prov-dm`, and for the full class/method API reference, see
{doc}`model`.

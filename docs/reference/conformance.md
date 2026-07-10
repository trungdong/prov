# Conformance matrix

This page tracks how each PROV-DM concept maps onto `prov`'s classes and factory methods, and
how well each serializer round-trips it. It is the audit artefact for Phase 3.5 of the
[modernisation roadmap](https://github.com/trungdong/prov/blob/master/ROADMAP.md) (roadmap step
28) and is **revisited at every release** as behaviour changes; a JSON-LD column is planned for
Phase 5 once the JSON-LD serializer lands. For prose background on PROV-DM's six components and
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
- **PROV-N** — PROV-N is **output-only**: `prov` has no PROV-N parser (issue #122, planned for
  Phase 5b), so there is no PROV-N round trip to test, only the keyword `get_provn()` emits.
  Every PROV-N cell below is additionally subject to **issue #223**
  (`QualifiedName.provn_representation()` does not escape PROV-N metacharacters — `'`, `)`,
  `,`, `(`, `:`, `;`, `[`, `]`, `=` — in an identifier's local part), which is a property of
  *identifiers*, not of any one record type; it is noted once here rather than on every row.

Two more caveats apply across many rows rather than to one:

- **#217** (RDF): 14 statement-level test cases assert two relations that share one identifier
  but differ only in `prov:time`; PROV-O has no way to represent that (both times serialize onto
  the same qualified IRI), so those specific *test cases* are skipped for the `rdf` target. This
  is a limitation of same-identifier/differing-time relations, not of the relation types
  themselves — `generation`/`usage`/`start`/`end`/`invalidation` round-trip cleanly in the
  general case.
- **#224** (XML): the PROV-XML serializer silently drops any `other_attributes` entry whose
  value is the empty string `""`, regardless of record type.
- **#225** (RDF): a Python `float` attribute (typed `xsd:float`) can lose precision through RDF,
  regardless of record type, because the RDF serializer canonicalises `xsd:float` to a short
  decimal form.

## Component 1 — Entities and Activities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Entity §5.1.1 | `ProvEntity` | `entity()` | `entity` | ✓ | ✓ | ✓ |
| Activity §5.1.2 | `ProvActivity` | `activity()` | `activity` | ✓ | ✓ | ✓ |
| Generation §5.1.3 | `ProvGeneration` | `generation()` / `wasGeneratedBy()` | `wasGeneratedBy` | ✓ | ✓ | ✓ (#217 for the 2 same-id/differing-time cases) |
| Usage §5.1.4 | `ProvUsage` | `usage()` / `used()` | `used` | ✓ | ✓ | ✓ (#217 for the 2 same-id/differing-time cases) |
| Communication §5.1.5 | `ProvCommunication` | `communication()` / `wasInformedBy()` | `wasInformedBy` | ✓ | ✓ | ✓ |
| Start §5.1.6 | `ProvStart` | `start()` / `wasStartedBy()` | `wasStartedBy` | ✓ | ✓ | ✓ (#217 for the 4 same-id/differing-time cases) |
| End §5.1.7 | `ProvEnd` | `end()` / `wasEndedBy()` | `wasEndedBy` | ✓ | ✓ | ✓ (#217 for the 4 same-id/differing-time cases) |
| Invalidation §5.1.8 | `ProvInvalidation` | `invalidation()` / `wasInvalidatedBy()` | `wasInvalidatedBy` | ✓ | ✓ | ✓ (#217 for the 2 same-id/differing-time cases) |

`ProvEntity` additionally exposes `wasGeneratedBy()`/`wasInvalidatedBy()` and `ProvActivity`
exposes `used()`/`wasInformedBy()`/`wasStartedBy()`/`wasEndedBy()` as self-as-subject chaining
methods (`records.py`) — the table above lists the `ProvBundle` factories, which every relation
also has.

## Component 2 — Derivations

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Derivation §5.2.1 | `ProvDerivation` | `derivation()` / `wasDerivedFrom()` | `wasDerivedFrom` | ✓ | ✓ | ✓ |
| Revision §5.2.2 | `ProvDerivation` + `prov:Revision` type | `revision()` / `wasRevisionOf()` | `wasDerivedFrom` (plus `[prov:type='prov:Revision']`) | ✓ | ✓ | ✓ |
| Quotation §5.2.3 | `ProvDerivation` + `prov:Quotation` type | `quotation()` / `wasQuotedFrom()` | `wasDerivedFrom` (plus `[prov:type='prov:Quotation']`) | ✓ | ✓ | ✓ |
| Primary Source §5.2.4 | `ProvDerivation` + `prov:PrimarySource` type | `primary_source()` / `hadPrimarySource()` | `wasDerivedFrom` (plus `[prov:type='prov:PrimarySource']`) | ✓ | ✓ | ✓ |

Revision, quotation, and primary source are PROV-DM *subtypes* of derivation, not separate PROV-N
records: `prov` implements all four with the single `ProvDerivation` class, and the three
subtype factories call `derivation()` then add the corresponding `prov:type`
(confirmed by inspection of `bundle.py:1011-1146`, and by running `get_provn()` on a `revision()`
record — it emits `wasDerivedFrom(..., [prov:type='prov:Revision'])`, not a `wasRevisionOf(...)`
keyword). `ADDITIONAL_N_MAP` does carry a `wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource`
keyword mapping for contexts (such as PROV-XML) that treat these as top-level types; PROV-N
output from this library always uses the base `wasDerivedFrom` form.

## Component 3 — Agents, Responsibility, and Influence

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Agent §5.3.1 | `ProvAgent` | `agent()` | `agent` | ✓ | ✓ | ✓ |
| Person / Organization / SoftwareAgent §5.3.1 | via `prov:type` on `ProvAgent` | none — see finding below | `person` / `organization` / `softwareAgent` (`ADDITIONAL_N_MAP`, not emitted directly by this library) | ✓ | ✓ | ✓ |
| Attribution §5.3.2 | `ProvAttribution` | `attribution()` / `wasAttributedTo()` | `wasAttributedTo` | ✓ | ✓ | ✓ |
| Association §5.3.3 | `ProvAssociation` | `association()` / `wasAssociatedWith()` | `wasAssociatedWith` | ✓ | ✓ | ✓ |
| Plan §5.3.3 | via `association(plan=...)` | — | — (plan is an ordinary entity referenced by the association's `plan` formal attribute) | ✓ | ✓ | ✓ |
| Delegation §5.3.4 | `ProvDelegation` | `delegation()` / `actedOnBehalfOf()` | `actedOnBehalfOf` | ✓ | ✓ | ✓ (anonymous qualified delegations sharing (delegate, activity): #226) |
| Influence §5.3.5 | `ProvInfluence` | `influence()` / `wasInfluencedBy()` | `wasInfluencedBy` | ✓ | ✓ | ✓ |

**Finding:** PROV-DM defines Person, Organization, and SoftwareAgent as agent subtypes, and Plan
as an entity subtype used with associations. `prov` has no dedicated classes or factories for the
agent subtypes — you express them with `agent("ag", {PROV_TYPE: "prov:Person"})` — while Plan
needs no special handling at all, since it is just an entity passed as the `plan=` argument to
`association()`. This is a documented, intentional design choice
(`docs/explanation/prov-dm.md:111-114`), not a defect; see finding log for the audit note.

## Component 4 — Bundles

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Bundle constructor §5.4.1 | `ProvBundle` | `ProvDocument.bundle()` / `add_bundle()` | `bundle <id> ... endBundle` (structural, hand-emitted by `get_provn()`) | ✓ | ✓ | ✓ |
| Bundle type §5.4.2 | not implemented — see finding below | — | — | — | — | — |

**Finding:** PROV-DM §5.4.1 defines bundle *containment* — a named, nestable set of records —
which `prov` fully implements via `ProvDocument.bundle()`/`add_bundle()`; only a
`ProvDocument` may contain named bundles (`is_document()`/`is_bundle()` in `bundle.py`
distinguish the two at runtime). §5.4.2 additionally lets a bundle's identifier denote a
first-class entity of type `prov:Bundle`, so that provenance-of-provenance (e.g. "who asserted
this bundle") can itself be expressed in PROV. That second half is **not implemented**: the
`PROV_BUNDLE` constant and its `PROV_N_MAP["bundle"]` keyword exist in `constants.py` but are
consumed only by `dot.py` (for node styling) — no serializer or `ProvBundle` method ever
produces a `prov:Bundle`-typed entity, and `get_provn()`'s `bundle <id> ... endBundle` output is
generated structurally (branching on `is_document()`), not through that keyword lookup. There is
currently no supported way to attribute a bundle to an agent as a first-class PROV statement.

## Component 5 — Alternate Entities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Specialization §5.5.1 | `ProvSpecialization` | `specialization()` / `specializationOf()` | `specializationOf` | ✓ | ✓ | ✓ |
| Alternate §5.5.2 | `ProvAlternate` | `alternate()` / `alternateOf()` | `alternateOf` | ✓ | ✓ | ✓ |
| Mention (PROV-LINKS) | `ProvMention` (subclass of `ProvSpecialization`) | `mention()` / `mentionOf()` | `mentionOf` | ✓ | ✓ | ✓ |

## Component 6 — Collections

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF |
| --- | --- | --- | --- | --- | --- | --- |
| Collection §5.6 | `ProvEntity` + `prov:Collection` type | `collection()` | `entity` (plus `[prov:type='prov:Collection']`) | ✓ | ✓ | ✓ |
| EmptyCollection §5.6 | `ProvEntity` + `prov:EmptyCollection` type — no dedicated factory | none — see finding below | `entity` (plus `[prov:type='prov:EmptyCollection']`, keyword `emptyCollection` in `ADDITIONAL_N_MAP`, not emitted directly) | ✓ | ✓ | ✓ |
| Membership §5.6 | `ProvMembership` | `membership()` / `hadMember()` | `hadMember` | ✓ | ✓ | ✓ |

**Finding:** like collections, `EmptyCollection` is a real PROV-DM type with a real
`ADDITIONAL_N_MAP`/`PROV_BASE_CLS` entry in `constants.py`, so the round-trip machinery
understands it — but there is no `empty_collection()` factory or `empty=` flag on `collection()`
to set the type for you; you would add `prov:type: "prov:EmptyCollection"` by hand via
`other_attributes`.

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
| `prov:type` | `PROV_TYPE` | ✓ JSON/XML; RDF is clean for a single value but see #77 (`xsd:decimal` becomes `10.0`) and #218 (mixed multi-datatype attribute sets on one record lose fidelity) — both are strict `xfail`s in `test_attributes.py`, not silent failures. |
| `prov:value` | `PROV_VALUE` | ✓ JSON/XML/RDF. |

Any attribute value (regardless of which of the five above it is) is additionally subject to
**#224** (XML drops the empty string `""`) and **#225** (RDF can lose `xsd:float` precision) —
both are properties of the value's type, not of the attribute name.

## Maintenance

This matrix reflects the codebase as of the Phase 3.5 conformance audit (roadmap step 28) and
should be revisited at each release as serializers change or issues close. Phase 5 of the
roadmap adds a PROV-JSONLD serializer; when that lands, this page gains a JSON-LD column
alongside JSON/XML/RDF. See {doc}`../explanation/prov-dm` for the conceptual background behind
each component, and {doc}`model` for the full class/method API reference.

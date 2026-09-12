# Conformance matrix

This page maps each PROV-DM concept to `prov`'s classes and factory methods and shows how
each serializer round-trips it. It is revised at every release. The last revision was for
3.1.1 (2026-09-10), which changed no round-trip result. The JSON-LD column arrived with
3.1.0's PROV-JSONLD serializer (`format="jsonld"`, {doc}`../howto/provjsonld`).

Every cell is checked against the current source code and the shared test suite, not
against the specification text alone. {doc}`../explanation/prov-dm` gives the conceptual
background for PROV-DM's six components. This page is the detailed reference under it.

## Round-trip column key

- **JSON**, **XML**, **RDF**, **JSON-LD**. A tick means `deserialize(serialize(doc)) == doc`
  for every shared test case. Otherwise a caveat below explains what fails and why. JSON-LD
  means [PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/), a W3C member
  submission, implemented without `rdflib` or a JSON-LD processor. Its decoder accepts the
  submission's compacted shape only, plus
  [ProvToolbox](https://lucmoreau.github.io/ProvToolbox/)'s `prov:`-prefixed spellings of
  the type and special terms.
- **PROV-N** is output only. `prov` has no PROV-N parser
  ([#122](https://github.com/trungdong/prov/issues/122), planned for 3.2.0), so there is
  nothing to round-trip. The column shows the keyword `get_provn()` emits.
  <!-- 3.2.0: corpus exceptions -->

## Caveats that span several rows

### Two relations with the same identifier and different `prov:time` (RDF, permanent)

PROV-O represents a relation such as `wasGeneratedBy` as one RDF node named by the
relation's identifier. If two asserted relations share an identifier and differ only in
`prov:time`, PROV-O has nowhere to keep the two `prov:atTime` values apart. Both land on
the same node. Only that exact construct is affected. A normal document round-trips
cleanly, and JSON, XML, PROV-N and the in-memory model are unaffected. Decoding
third-party RDF shaped this way raises `prov.model.ProvException` naming the limitation.

This is a permanent limitation, not an open bug
([#217](https://github.com/trungdong/prov/issues/217)). Minting a synthetic IRI and
guessing attribute values on decode were both considered and rejected. Serializing such a
document stays legal, because `prov` never enforces structural constraints at assertion
time ([#257](https://github.com/trungdong/prov/issues/257)). `unified()` does detect the
conflict, as part of its PROV-CONSTRAINTS support (see
{doc}`../explanation/unification-flattening`).

### No `mentionOf` term in PROV-JSONLD (JSON-LD, permanent)

The PROV-JSONLD submission defines no term for PROV-DM's Mention relation, so there is no
shape `prov` could encode it in ([#248](https://github.com/trungdong/prov/issues/248)).
Serializing or deserializing a document containing a {py:class}`~prov.model.ProvMention`
record raises `prov.serializers.provjsonld.ProvJSONLDException`. Every other relation and
element round-trips through PROV-JSONLD, including the same-identifier cases above, which
trouble PROV-O only.

### RDF's `json-ld` output is not PROV-JSONLD

`rdf_format="json-ld"` runs the PROV-O graph through rdflib's generic JSON-LD writer. The
result is not the PROV-JSONLD submission's compacted shape, and it inherits every PROV-O
limitation above. Use `format="jsonld"` for PROV-JSONLD.

### XML escapes illegal attribute names (XML, permanent convention)

An attribute name is written as a PROV-XML child element tag, but its local part need not
be a legal XML NCName. It may start with a digit or contain characters such as
`' ( ) , : ; [ ] =`. `prov` escapes each illegal character with the `_xHHHH_` convention,
the same one OpenXML and SQL Server use, and reverses it on read, so such names round-trip
([#289](https://github.com/trungdong/prov/issues/289)). Legal names are written unchanged.
One consequence is that a third-party document whose attribute name already looks like an
`_xHHHH_` escape is unescaped on read.

## Component 1: Entities and Activities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Entity §5.1.1 | {py:class}`~prov.model.ProvEntity` | `entity()` | `entity` | ✓ | ✓ | ✓ | ✓ |
| Activity §5.1.2 | {py:class}`~prov.model.ProvActivity` | `activity()` | `activity` | ✓ | ✓ | ✓ | ✓ |
| Generation §5.1.3 | {py:class}`~prov.model.ProvGeneration` | `generation()` / `wasGeneratedBy()` | `wasGeneratedBy` | ✓ | ✓ | ✓ (same-identifier caveat: 2 cases) | ✓ |
| Usage §5.1.4 | {py:class}`~prov.model.ProvUsage` | `usage()` / `used()` | `used` | ✓ | ✓ | ✓ (same-identifier caveat: 2 cases) | ✓ |
| Communication §5.1.5 | {py:class}`~prov.model.ProvCommunication` | `communication()` / `wasInformedBy()` | `wasInformedBy` | ✓ | ✓ | ✓ | ✓ |
| Start §5.1.6 | {py:class}`~prov.model.ProvStart` | `start()` / `wasStartedBy()` | `wasStartedBy` | ✓ | ✓ | ✓ (same-identifier caveat: 4 cases) | ✓ |
| End §5.1.7 | {py:class}`~prov.model.ProvEnd` | `end()` / `wasEndedBy()` | `wasEndedBy` | ✓ | ✓ | ✓ (same-identifier caveat: 4 cases) | ✓ |
| Invalidation §5.1.8 | {py:class}`~prov.model.ProvInvalidation` | `invalidation()` / `wasInvalidatedBy()` | `wasInvalidatedBy` | ✓ | ✓ | ✓ (same-identifier caveat: 2 cases) | ✓ |

The table lists the {py:class}`~prov.model.ProvBundle` factories, which every relation
has. {py:class}`~prov.model.ProvEntity` also exposes `wasGeneratedBy()` and
`wasInvalidatedBy()`, and {py:class}`~prov.model.ProvActivity` exposes `used()`,
`wasInformedBy()`, `wasStartedBy()` and `wasEndedBy()`, as chaining methods with the
record itself as subject.

## Component 2: Derivations

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Derivation §5.2.1 | {py:class}`~prov.model.ProvDerivation` | `derivation()` / `wasDerivedFrom()` | `wasDerivedFrom` | ✓ | ✓ | ✓ | ✓ |
| Revision §5.2.2 | {py:class}`~prov.model.ProvDerivation` + `prov:Revision` type | `revision()` / `wasRevisionOf()` | `wasDerivedFrom` (plus `[prov:type='prov:Revision']`) | ✓ | ✓ | ✓ | ✓ |
| Quotation §5.2.3 | {py:class}`~prov.model.ProvDerivation` + `prov:Quotation` type | `quotation()` / `wasQuotedFrom()` | `wasDerivedFrom` (plus `[prov:type='prov:Quotation']`) | ✓ | ✓ | ✓ | ✓ |
| Primary Source §5.2.4 | {py:class}`~prov.model.ProvDerivation` + `prov:PrimarySource` type | `primary_source()` / `hadPrimarySource()` | `wasDerivedFrom` (plus `[prov:type='prov:PrimarySource']`) | ✓ | ✓ | ✓ | ✓ |

The three subtypes share the {py:class}`~prov.model.ProvDerivation` class and differ only
in `prov:type` (see {doc}`../explanation/prov-dm`), so `get_provn()` on a `revision()`
record emits `wasDerivedFrom(..., [prov:type='prov:Revision'])` rather than a
`wasRevisionOf(...)` keyword. `ADDITIONAL_N_MAP` carries the `wasRevisionOf`,
`wasQuotedFrom` and `hadPrimarySource` keywords for contexts such as PROV-XML that treat
these as top-level types, but PROV-N output from this library always uses
`wasDerivedFrom`.

## Component 3: Agents, Responsibility and Influence

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agent §5.3.1 | {py:class}`~prov.model.ProvAgent` | `agent()` | `agent` | ✓ | ✓ | ✓ | ✓ |
| Person / Organization / SoftwareAgent §5.3.1 | `prov:type` on {py:class}`~prov.model.ProvAgent` | none (see below) | `person` / `organization` / `softwareAgent` (`ADDITIONAL_N_MAP`, not emitted by this library) | ✓ | ✓ | ✓ | ✓ |
| Attribution §5.3.2 | {py:class}`~prov.model.ProvAttribution` | `attribution()` / `wasAttributedTo()` | `wasAttributedTo` | ✓ | ✓ | ✓ | ✓ |
| Association §5.3.3 | {py:class}`~prov.model.ProvAssociation` | `association()` / `wasAssociatedWith()` | `wasAssociatedWith` | ✓ | ✓ | ✓ | ✓ |
| Plan §5.3.3 | `association(plan=...)` | none | none (the plan is an ordinary entity referenced by the association's `plan` formal attribute) | ✓ | ✓ | ✓ | ✓ |
| Delegation §5.3.4 | {py:class}`~prov.model.ProvDelegation` | `delegation()` / `actedOnBehalfOf()` | `actedOnBehalfOf` | ✓ | ✓ | ✓ | ✓ |
| Influence §5.3.5 | {py:class}`~prov.model.ProvInfluence` | `influence()` / `wasInfluencedBy()` | `wasInfluencedBy` | ✓ | ✓ | ✓ | ✓ |

The agent subtypes and Plan have no dedicated classes. They are expressed through
`prov:type` and the `plan=` argument, as {doc}`../explanation/prov-dm` explains.
Convenience factories for the three agent subtypes and for `EmptyCollection` (Component 6)
are tracked as [#260](https://github.com/trungdong/prov/issues/260).

## Component 4: Bundles

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bundle constructor §5.4.1 | {py:class}`~prov.model.ProvBundle` | `ProvDocument.bundle()` / `add_bundle()` | `bundle <id> ... endBundle` (structural, emitted by `get_provn()`) | ✓ | ✓ | ✓ | ✓ |
| Bundle type §5.4.2 | not implemented (see below) | | | | | | |

PROV-DM §5.4.1 defines bundle containment, a named and nestable set of records, which
`prov` implements through `ProvDocument.bundle()` and `add_bundle()`. Only a
{py:class}`~prov.model.ProvDocument` may contain named bundles. §5.4.2 also lets a
bundle's identifier denote a first-class entity of type `prov:Bundle`, so that the
provenance of the bundle itself can be expressed in PROV. That second half is not
implemented. No serializer or {py:class}`~prov.model.ProvBundle` method produces a
`prov:Bundle`-typed entity, so there is no supported way to attribute a bundle to an agent
as a PROV statement. Tracked as [#261](https://github.com/trungdong/prov/issues/261).

## Component 5: Alternate Entities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Specialization §5.5.1 | {py:class}`~prov.model.ProvSpecialization` | `specialization()` / `specializationOf()` | `specializationOf` | ✓ | ✓ | ✓ | ✓ |
| Alternate §5.5.2 | {py:class}`~prov.model.ProvAlternate` | `alternate()` / `alternateOf()` | `alternateOf` | ✓ | ✓ | ✓ (`alternate(alt1, alt2)` emits `alt1 prov:alternateOf alt2`, PROV-DM's argument order: [#258](https://github.com/trungdong/prov/issues/258)) | ✓ |
| Mention (PROV-LINKS) | {py:class}`~prov.model.ProvMention` (subclass of {py:class}`~prov.model.ProvSpecialization`) | `mention()` / `mentionOf()` | `mentionOf` (see below) | ✓ | ✓ | ✓ | ✗ (no Mention term, see above) |

PROV-N output emits Mention as the bare keyword `mentionOf` rather than the
`prov:mentionOf` form the PROV-LINKS grammar requires. This is a deliberate deviation
matching the reference implementations, so `provconvert` still parses it
([#248](https://github.com/trungdong/prov/issues/248)).

## Component 6: Collections

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Collection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:Collection` type | `collection()` | `entity` (plus `[prov:type='prov:Collection']`) | ✓ | ✓ | ✓ | ✓ |
| EmptyCollection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:EmptyCollection` type | none (see below) | `entity` (plus `[prov:type='prov:EmptyCollection']`; the `emptyCollection` keyword in `ADDITIONAL_N_MAP` is not emitted) | ✓ | ✓ | ✓ | ✓ |
| Membership §5.6 | {py:class}`~prov.model.ProvMembership` | `membership()` / `hadMember()` | `hadMember` | ✓ | ✓ | ✓ | ✓ |

`EmptyCollection` is a PROV-DM type the round-trip machinery understands, but there is no
`empty_collection()` factory or `empty=` flag on `collection()`. Add
`prov:type: PROV["EmptyCollection"]` through `other_attributes`. Tracked, together with
the agent-subtype factories, as [#260](https://github.com/trungdong/prov/issues/260).

## Additional attributes

Five PROV-DM attributes are usable on almost any record. The shared attribute test matrix
exercises each directly.

| Attribute | Constant (`prov.constants`) | Round-trip notes |
| --- | --- | --- |
| `prov:label` | `PROV_LABEL` | ✓ JSON/XML/RDF/JSON-LD, including language-tagged literals and multiple values on one record. |
| `prov:location` | `PROV_LOCATION` | ✓ JSON/XML/RDF/JSON-LD across the full datatype corpus. |
| `prov:role` | `PROV_ROLE` | ✓ JSON/XML/RDF/JSON-LD; used throughout the qualified-relation tests. |
| `prov:type` | `PROV_TYPE` | ✓ JSON/XML/RDF/JSON-LD, including mixed multi-datatype attribute sets on one record. |
| `prov:value` | `PROV_VALUE` | ✓ JSON/XML/RDF/JSON-LD. |

## Related pages

{doc}`../explanation/unification-flattening` covers merge-time conformance
(PROV-CONSTRAINTS unification), which the round-trip tables above do not.
{doc}`../explanation/prov-dm` gives the background for each component, and {doc}`model`
is the class and method reference.

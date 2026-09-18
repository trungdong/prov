# Conformance

`prov` implements the W3C [PROV Data Model](https://www.w3.org/TR/prov-dm/) and five
serialisations of it: PROV-JSON, PROV-XML, PROV-O (RDF), PROV-JSONLD and PROV-N. This page
states what the current release conforms to; it was revised for 3.2.2.

The component tables answer two questions: is a PROV-DM concept implemented and how is it
written, and does each format preserve it on a round trip. Every cell that is not a plain
tick points at a numbered caveat. The values table does the same for literals. "Reading
other producers' output" lists what each reader accepts beyond `prov`'s own output, with
the reason for each allowance. "Corpus evidence" is the test record behind the PROV-N
claims. Every cell is checked against the source and the shared test suite, not against the
specification text alone; {doc}`../explanation/prov-dm` gives the background for the six
components.

## Reading the tables

- A round trip is `deserialize(serialize(doc)) == doc` for every shared test case. ✓ means
  it holds; ✓ C1 means it holds except in the case caveat C1 describes; ✗ C2 means the
  format cannot represent the concept.
- The PROV-N column shows the keyword `get_provn()` writes. Every row round-trips through
  PROV-N under the `default` profile, and under `strict` when written with `strict=True`.
- `prov` enforces no structural constraint at assertion time ([#257](https://github.com/trungdong/prov/issues/257)). Merge-time
  conformance, PROV-CONSTRAINTS unification, is `unified()`'s job and is described in
  {doc}`../explanation/unification-flattening`.

## Component 1: Entities and Activities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Entity §5.1.1 | {py:class}`~prov.model.ProvEntity` | `entity()` | `entity` | ✓ | ✓ | ✓ | ✓ |
| Activity §5.1.2 | {py:class}`~prov.model.ProvActivity` | `activity()` | `activity` | ✓ | ✓ | ✓ | ✓ |
| Generation §5.1.3 | {py:class}`~prov.model.ProvGeneration` | `generation()` / `wasGeneratedBy()` | `wasGeneratedBy` | ✓ | ✓ | ✓ C1 | ✓ |
| Usage §5.1.4 | {py:class}`~prov.model.ProvUsage` | `usage()` / `used()` | `used` | ✓ | ✓ | ✓ C1 | ✓ |
| Communication §5.1.5 | {py:class}`~prov.model.ProvCommunication` | `communication()` / `wasInformedBy()` | `wasInformedBy` | ✓ | ✓ | ✓ | ✓ |
| Start §5.1.6 | {py:class}`~prov.model.ProvStart` | `start()` / `wasStartedBy()` | `wasStartedBy` | ✓ | ✓ | ✓ C1 | ✓ |
| End §5.1.7 | {py:class}`~prov.model.ProvEnd` | `end()` / `wasEndedBy()` | `wasEndedBy` | ✓ | ✓ | ✓ C1 | ✓ |
| Invalidation §5.1.8 | {py:class}`~prov.model.ProvInvalidation` | `invalidation()` / `wasInvalidatedBy()` | `wasInvalidatedBy` | ✓ | ✓ | ✓ C1 | ✓ |

The factories are {py:class}`~prov.model.ProvBundle` methods. {py:class}`~prov.model.ProvEntity`
also has `wasGeneratedBy()` and `wasInvalidatedBy()`, and {py:class}`~prov.model.ProvActivity`
has `used()`, `wasInformedBy()`, `wasStartedBy()` and `wasEndedBy()`, as chaining methods
with the record itself as subject.

## Component 2: Derivations

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Derivation §5.2.1 | {py:class}`~prov.model.ProvDerivation` | `derivation()` / `wasDerivedFrom()` | `wasDerivedFrom` | ✓ | ✓ | ✓ | ✓ |
| Revision §5.2.2 | {py:class}`~prov.model.ProvDerivation` + `prov:Revision` type | `revision()` / `wasRevisionOf()` | `wasDerivedFrom` with `[prov:type='prov:Revision']` | ✓ | ✓ | ✓ | ✓ |
| Quotation §5.2.3 | {py:class}`~prov.model.ProvDerivation` + `prov:Quotation` type | `quotation()` / `wasQuotedFrom()` | `wasDerivedFrom` with `[prov:type='prov:Quotation']` | ✓ | ✓ | ✓ | ✓ |
| Primary Source §5.2.4 | {py:class}`~prov.model.ProvDerivation` + `prov:PrimarySource` type | `primary_source()` / `hadPrimarySource()` | `wasDerivedFrom` with `[prov:type='prov:PrimarySource']` | ✓ | ✓ | ✓ | ✓ |

The three subtypes share one class and differ only in `prov:type`, which is how PROV-N
expresses them: the grammar has no `wasRevisionOf` keyword.

## Component 3: Agents, Responsibility and Influence

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agent §5.3.1 | {py:class}`~prov.model.ProvAgent` | `agent()` | `agent` | ✓ | ✓ | ✓ | ✓ |
| Person / Organization / SoftwareAgent §5.3.1 | `prov:type` on {py:class}`~prov.model.ProvAgent` | none, see "Not implemented" | `agent` with `[prov:type='prov:Person']` and so on | ✓ | ✓ | ✓ | ✓ |
| Attribution §5.3.2 | {py:class}`~prov.model.ProvAttribution` | `attribution()` / `wasAttributedTo()` | `wasAttributedTo` | ✓ | ✓ | ✓ | ✓ |
| Association §5.3.3 | {py:class}`~prov.model.ProvAssociation` | `association()` / `wasAssociatedWith()` | `wasAssociatedWith` | ✓ | ✓ | ✓ | ✓ |
| Plan §5.3.3 | the entity named by `association(plan=...)` | none | none; the plan is the association's third argument | ✓ | ✓ | ✓ | ✓ |
| Delegation §5.3.4 | {py:class}`~prov.model.ProvDelegation` | `delegation()` / `actedOnBehalfOf()` | `actedOnBehalfOf` | ✓ | ✓ | ✓ | ✓ |
| Influence §5.3.5 | {py:class}`~prov.model.ProvInfluence` | `influence()` / `wasInfluencedBy()` | `wasInfluencedBy` | ✓ | ✓ | ✓ | ✓ |

## Component 4: Bundles

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bundle constructor §5.4.1 | {py:class}`~prov.model.ProvBundle` | `ProvDocument.bundle()` / `add_bundle()` | `bundle <id> ... endBundle` | ✓ | ✓ | ✓ | ✓ |
| Bundle as an entity §5.4.2 | not implemented, see below | | | | | | |

Only a {py:class}`~prov.model.ProvDocument` may contain named bundles. A bundle that
declares a default namespace different from the one its identifier lives in is written with
a prefixed identifier, so the identifier's IRI survives re-reading.

## Component 5: Alternate Entities

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Specialization §5.5.1 | {py:class}`~prov.model.ProvSpecialization` | `specialization()` / `specializationOf()` | `specializationOf` | ✓ | ✓ | ✓ | ✓ |
| Alternate §5.5.2 | {py:class}`~prov.model.ProvAlternate` | `alternate()` / `alternateOf()` | `alternateOf` | ✓ | ✓ | ✓ | ✓ |
| Mention (PROV-Links) | {py:class}`~prov.model.ProvMention`, a {py:class}`~prov.model.ProvSpecialization` | `mention()` / `mentionOf()` | `mentionOf`, or `prov:mentionOf` with `strict=True` | ✓ | ✓ | ✓ | ✗ C2 |

`alternate(a, b)` is written as the triple `a prov:alternateOf b`, PROV-DM's argument order.

## Component 6: Collections

| Concept (PROV-DM §) | Model class | Factory / alias | PROV-N keyword | JSON | XML | RDF | JSON-LD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Collection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:Collection` type | `collection()` | `entity` with `[prov:type='prov:Collection']` | ✓ | ✓ | ✓ | ✓ |
| EmptyCollection §5.6 | {py:class}`~prov.model.ProvEntity` + `prov:EmptyCollection` type | none, see "Not implemented" | `entity` with `[prov:type='prov:EmptyCollection']` | ✓ | ✓ | ✓ | ✓ |
| Membership §5.6 | {py:class}`~prov.model.ProvMembership` | `membership()` / `hadMember()` | `hadMember` | ✓ | ✓ | ✓ | ✓ |

## Values and datatypes (PROV-DM §5.7)

The shared attribute corpus exercises every XSD type below in every format, on `prov:label`,
`prov:location`, `prov:role`, `prov:type`, `prov:value` and on ordinary attributes.

| Value | Written as | Round trip |
| --- | --- | --- |
| String, with or without an explicit `xsd:string` | a string | ✓ in every format |
| Language-tagged string | the tag as given; tags compare case-insensitively | ✓ C5 C6 |
| Boolean | `xsd:boolean`, spelled `true` and `false`; the readers also accept `1` and `0` | ✓ |
| Python `int` with no datatype | `xsd:int` when it fits 32 bits, else `xsd:long` when it fits 64, else `xsd:integer`; PROV-N writes `xsd:int` as a bare number | ✓ |
| Integer with an asserted datatype (`xsd:long`, `xsd:short`, `xsd:unsignedByte`, ...) | the asserted datatype, never collapsed to a narrower one | ✓ |
| `xsd:decimal` | as given; compared in value space, so `10`, `10.0` and `"10.00"` are one value | ✓ |
| Python `float` | `xsd:double` at full precision | ✓ |
| Qualified name as a value | `xsd:QName` in PROV-JSON, native elsewhere | ✓ |
| `xsd:dateTime` | ISO 8601 text; a naive `datetime` is written without a zone | ✓ C7 |
| `xsd:anyURI`, `xsd:base64Binary` and the other XSD types in the corpus | lexical form and datatype as given; datatypes other than `xsd:decimal` compare lexically, so `"1"` and `"01"` differ | ✓ |

## Caveats

- **C1. Two relations with the same identifier and different `prov:time` (PROV-O, permanent).**
  PROV-O names a relation by its identifier, so two asserted relations that share one and
  differ only in time land on one node. Only that construct is affected; decoding
  third-party RDF shaped this way raises `prov.model.ProvException`. Minting a synthetic
  IRI and guessing values on decode were both rejected ([#217](https://github.com/trungdong/prov/issues/217)). `unified()` reports the
  conflict.
- **C2. No Mention term in PROV-JSONLD (permanent).** The submission defines none, so
  serialising or deserialising a document with a {py:class}`~prov.model.ProvMention` raises
  `prov.serializers.provjsonld.ProvJSONLDException` ([#248](https://github.com/trungdong/prov/issues/248)).
- **C3. PROV-XML escapes attribute names that are not NCNames.** A name may start with a digit
  or contain `' ( ) , : ; [ ] =`; each illegal character is written as `_xHHHH_`, the OpenXML
  convention, and reversed on read ([#289](https://github.com/trungdong/prov/issues/289)). A third-party name that already looks like
  an escape is therefore unescaped.
- **C4. PROV-N local parts.** A character `PN_LOCAL` cannot express, such as a space, is
  percent-encoded with a `ProvWarning`, and the identifier reads back as the encoded IRI, so
  `ex:a b` becomes `ex:a%20b`. PROV-O rejects an IRI containing a space. A namespace prefix
  must be a valid `PN_PREFIX` (a letter first, then name characters or `.`, not ending in
  `.`); `prov` does not validate or rename one that is not.
- **C5. Empty language tag.** `Literal("hi", langtag="")` survives PROV-XML only, as
  `xml:lang=""`. PROV-N, PROV-JSON and PROV-JSONLD read it back as a plain string and PROV-O
  raises. A future release will treat an empty tag as no tag in the model.
- **C6. Language tag that is not BCP 47.** PROV-N writes an underscore separator as a hyphen,
  so `en_US` reads back as `en-US`; PROV-O raises rdflib's `ValueError`. PROV-JSON, PROV-XML
  and PROV-JSONLD pass the tag through unchanged.
- **C7. Zone offsets that are not whole minutes.** Every format writes such an `xsd:dateTime`
  in UTC, because the datatype allows no seconds in an offset. The instant is unchanged and
  the round trip compares equal; the original offset is not preserved.
- **C8. RDF's `json-ld` syntax is not PROV-JSONLD.** `rdf_format="json-ld"` is rdflib's
  generic JSON-LD writer over the PROV-O graph, with every PROV-O limitation. Use
  `format="jsonld"` for PROV-JSONLD.

## Reading other producers' output

A round trip covers `prov`'s own output. Reading what other tools write is a separate claim.
Each allowance below states its reason; `prov` does not adopt another implementation's
departure from the Recommendations without one.

### PROV-N profiles

| Profile | Accepts |
| --- | --- |
| `strict` | The Recommendation grammar only. Mention is `prov:mentionOf`, as PROV-Links spells it. |
| `default` | The grammar plus the bare `mentionOf` keyword. The Recommendation has no Mention production, and every existing producer, `prov` and ProvToolbox included, writes the bare keyword, so refusing it would refuse every file in circulation. |
| `lenient` | As `default`. A statement that fails to parse, or that the model rejects, is skipped with a `ProvWarning` naming its line and column; a bundle whose identifier duplicates another is skipped whole. Extensibility expressions (`prefix:name(...)`) are skipped this way. |

No profile accepts the keywords `person`, `organization`, `softwareAgent`, `collection`,
`emptyCollection`, `plan`, `wasRevisionOf`, `wasQuotedFrom` or `hadPrimarySource`. They are
not PROV-N. The grammar expresses subtypes through `prov:type`, no producer writes them and
ProvToolbox's reader rejects them; they raise `ProvNSyntaxError` under `strict` and
`default` and are skipped under `lenient`. The PROV-Dictionary set-of-pairs literal
(`{("k1", e1), ...}`) is not supported.

The reader also accepts a leading byte order mark, a carriage return as a line end, an
all-digit local name as an attribute name or datatype, and a `bytearray` stream. A prefix
declared twice in one scope and a duplicate bundle identifier are errors.

### PROV-XML

- A reference element with no `prov:ref` whose child is itself a reference, the shape
  ProvToolbox writes for a `hadMember` member, is resolved with a `ProvWarning`; the intent
  is unambiguous. A reference with neither `prov:ref` nor text raises `ProvXMLException`.
- `<prov:other>` elements and attributes the model cannot represent are skipped with a
  `ProvWarning`.
- Names escaped as in C3 are unescaped.

### PROV-JSONLD

- The decoder accepts the submission's compacted shape only. It is not a JSON-LD processor:
  no expansion, no remote contexts.
- ProvToolbox's `prov:`-prefixed spellings of the type and special terms are accepted.
- An array-valued `entity` on a `Membership` statement, which the submission (section 4.18)
  allows and ProvToolbox always writes, decodes to one `hadMember` per member; an empty
  array raises `ProvJSONLDException`. If the array has several members and the statement
  also carries an `@id`, the resulting records are left unidentified with a `ProvWarning`,
  because records sharing one identifier cannot be unified. If the array has exactly one
  member, the `@id` is kept.

### PROV-O

- An attribute predicate under a namespace declared neither in the document nor in the graph
  gets a minted prefix, with a `ProvWarning`.
- Two relations sharing an identifier raise, as C1 describes.
- `rdf_format` selects the RDF syntax to read.

`prov.read()` detects the format from the content and forwards each reader's own options
(`profile` for PROV-N; `rdf_format`, `relation_mapper` and `predicate_mapper` for PROV-O;
the `json.load` hooks for PROV-JSON and PROV-JSONLD). An option a format does not accept
raises `TypeError` naming the format.

## Corpus evidence

The [PROV-N conformance corpus](https://github.com/trungdong/prov/tree/main/src/prov/tests/provn) runs at every test run.

| Set | Profile | Files | Result |
| --- | --- | --- | --- |
| Every example in the PROV-N and PROV-DM Recommendations | `strict` | 127 | 100 parse and round-trip through the writer. 27 are excluded because the Recommendation's prose presents them as PROV-N but the grammar rejects them: fragments missing a paired argument, bare literals, ellipses, a copy-paste `dateTime` error, and the PROV-Dictionary and extensibility syntax. |
| ProvToolbox's hand-written PROV-N test documents | `default` | 9 | 4 parse. 5 are excluded: bare local names with no default namespace, the PROV-Dictionary set-of-pairs literal, and a bare IRI as a datatype. |
| PROV-N that ProvToolbox's writer produced from the shared test corpus, compared with the PROV-JSON fixture of the same name | `default` | 388 | 229 equal. 159 differ for reasons in ProvToolbox's 2023 generator, not in `prov`: 80 embed a wall-clock timestamp, 79 carry a datatype list that no longer matches the fixture. |

The corpus README names every excluded or differing file with its reason.

## Not implemented

- A bundle as a first-class entity of type `prov:Bundle` (PROV-DM §5.4.2), so the provenance
  of a bundle itself cannot be asserted ([#261](https://github.com/trungdong/prov/issues/261)).
- Factories for the agent subtypes and for `EmptyCollection`; add the `prov:type` through
  `other_attributes` ([#260](https://github.com/trungdong/prov/issues/260)).
- PROV-Dictionary ([#129](https://github.com/trungdong/prov/issues/129)).
- PROV-CONSTRAINTS validation beyond what `unified()` checks ([#62](https://github.com/trungdong/prov/issues/62)).

## Related pages

{doc}`../explanation/unification-flattening` covers merge-time conformance, which the
tables above do not. {doc}`../explanation/prov-dm` gives the background for each component,
{doc}`model` is the class and method reference, and the how-to pages cover each format:
{doc}`../howto/provn`, {doc}`../howto/provjson`, {doc}`../howto/provxml`,
{doc}`../howto/provo-rdf`, {doc}`../howto/provjsonld`.

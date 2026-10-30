# Conformance

`prov` implements the W3C [PROV Data Model](https://www.w3.org/TR/prov-dm/) and five
serialisations of it: PROV-JSON, PROV-XML, PROV-O (RDF), PROV-JSONLD and PROV-N. This page
states what the current release conforms to; it was revised for 3.2.3.

Summary:

- Every concept in the tables below round-trips through every format, with two permanent
  exceptions, C1 and C2.
- The values table says how literals behave.
- Readers accept some output from other producers, listed under "Reading other producers'
  output".

## Reading the tables

- A round trip is `deserialize(serialize(doc)) == doc` for every shared test case. ✓ means
  it holds; ✓ C1 means it holds except in the case caveat C1 describes; ✗ C2 means the
  format cannot represent the concept.
- The PROV-N column shows the keyword `get_provn()` writes. Every row round-trips through
  PROV-N under the `default` profile, and under `strict` when written with `strict=True`.
- `prov` enforces no structural constraint at assertion time ([#257](https://github.com/trungdong/prov/issues/257)),
  except that `hadMember`, `alternateOf`, `specializationOf` and `mentionOf` require their
  parties ([#710](https://github.com/trungdong/prov/issues/710)); general validation is
  [#62](https://github.com/trungdong/prov/issues/62). Merge-time conformance,
  PROV-CONSTRAINTS unification, is `unified()`'s job and is described in
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

Only a {py:class}`~prov.model.ProvDocument` may contain named bundles. A bundle identifier
is resolved in the bundle's own scope (PROV-N section 3.4.1), so a declaration on the bundle
that would change what its identifier reads as, its own default while the identifier is
bare in the document's default, or a rebinding of the identifier's prefix, is refused with a
{py:class}`~prov.model.ProvException`
([#573](https://github.com/trungdong/prov/issues/573)).

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
| Boolean | `xsd:boolean`, spelled `true` and `false`; `1` and `0` read as the same value and keep their text | ✓ |
| Python `int` with no datatype | `xsd:int` when it fits 32 bits, else `xsd:long` when it fits 64, else `xsd:integer`; PROV-N writes `xsd:int` as a bare number | ✓ |
| Integer with an asserted datatype (`xsd:long`, `xsd:short`, `xsd:unsignedByte`, ...) | the asserted datatype, never collapsed to a narrower one | ✓ |
| `xsd:decimal` | as given; compared in value space, so `10`, `10.0` and `"10.00"` are one value | ✓ |
| Python `float` | `xsd:double` at full precision | ✓ |
| Qualified name as a value | `xsd:QName` in PROV-JSON, a node reference in PROV-JSONLD (a bare string under `type`, `location` and `role`), native elsewhere; a `Literal` typed `xsd:QName` or `prov:QUALIFIED_NAME` whose prefix is declared is stored as a qualified name | ✓ |
| `xsd:dateTime` | the `xsd:dateTime` lexical form with at most six fractional digits and a year from 1 to 9999; a naive `datetime` is written without a zone; an offset beyond ±14:00 is rejected, and a typed literal with one, a longer fraction or a year outside the range stays a `Literal`; PROV-O reads a longer fraction truncated (C10) | ✓ C7 C10 |
| `xsd:anyURI`, `xsd:base64Binary` and the other XSD types in the corpus | lexical form and datatype as given; `xsd:boolean`, `xsd:decimal`, `xsd:double`, `xsd:float` and the `xsd:integer` family compare in value space, so `"1"` and `"01"` as `xsd:int` are one value and a text outside the lexical space or the subtype's range compares as text; an `xsd:float` is keyed as a Python `float`, so two texts that differ only beyond single precision are two values; every other datatype compares as text; an `Identifier` value is stored as an `xsd:anyURI` `Literal` | ✓ C10 |
| Python `Decimal`, `date`, `time`, `timedelta`, `UUID`, `bytes`, `bytearray`, `memoryview` | the `Literal` of its XSD datatype, in the lexical form the how-to lists; a value of any other type is rejected | ✓ C10 |

## Permanent limitations

Two constructs cannot round-trip, and no change is planned.

- **C1. Two relations with the same identifier and different `prov:time` (PROV-O, permanent).**
  PROV-O names a relation by its identifier, so two asserted relations that share one and
  differ only in time land on one node. Only that construct is affected; decoding
  third-party RDF shaped this way raises `prov.serializers.provrdf.ProvRDFException`.
  Minting a synthetic IRI and guessing values on decode were both rejected
  ([#217](https://github.com/trungdong/prov/issues/217)). `unified()` reports the
  conflict.
- **C2. No Mention term in PROV-JSONLD (permanent).** The submission defines none, so
  serialising or deserialising a document with a {py:class}`~prov.model.ProvMention` raises
  `prov.serializers.provjsonld.ProvJSONLDException` ([#248](https://github.com/trungdong/prov/issues/248)).

## Format notes

- **C8. RDF's `json-ld` syntax is not PROV-JSONLD.** `rdf_format="json-ld"` is rdflib's
  generic JSON-LD writer over the PROV-O graph, with every PROV-O limitation. Use
  `format="jsonld"` for PROV-JSONLD.

## Not implemented

- A bundle as a first-class entity of type `prov:Bundle` (PROV-DM §5.4.2), so the provenance
  of a bundle itself cannot be asserted ([#261](https://github.com/trungdong/prov/issues/261)).
- Factories for the agent subtypes and for `EmptyCollection`; add the `prov:type` through
  `other_attributes` ([#260](https://github.com/trungdong/prov/issues/260)).
- PROV-Dictionary ([#129](https://github.com/trungdong/prov/issues/129)).
- PROV-CONSTRAINTS validation beyond what `unified()` checks ([#62](https://github.com/trungdong/prov/issues/62)).

## Reading other producers' output

A round trip covers `prov`'s own output. Reading what other tools write is a separate claim.
Each allowance below states its reason; `prov` does not adopt another implementation's
departure from the Recommendations without one.

Every reader warns {py:class}`~prov.model.ProvWarning` and skips a `hadMember`,
`alternateOf`, `specializationOf` or `mentionOf` that is missing a party, naming the
statement as the reader's errors do, and the rest of the document reads. A `mentionOf`
without its bundle reads. A party given as JSON `null` (PROV-JSON, PROV-JSONLD) or as a
blank `<prov:entity/>` still raises the reader's error.

### PROV-N profiles

{doc}`../howto/provn` lists what each of the three profiles, `strict`, `default` and
`lenient`, accepts.

No profile accepts the keywords `person`, `organization`, `softwareAgent`, `collection`,
`emptyCollection`, `plan`, `wasRevisionOf`, `wasQuotedFrom` or `hadPrimarySource`. They are
not PROV-N. The grammar expresses subtypes through `prov:type`, no producer writes them and
ProvToolbox's reader rejects them; they raise `ProvNSyntaxError` under `strict` and
`default` and are skipped under `lenient`.

The reader also accepts a leading byte order mark, a carriage return as a line end, an
all-digit local name as an attribute name or datatype, and a `bytearray` stream. A
prefix declared twice in one scope, a repeated `default`, a declared prefix that is not
a `PN_PREFIX`, a Unicode whitespace character other than space, tab, CR and LF between
tokens, a duplicate bundle identifier, and an attribute named after one of the
statement's own arguments are errors.

`strict` raises at a `-` where the grammar has a plain identifier. `default` and `lenient`
accept the `-`, except that a `hadMember`, `alternateOf`, `specializationOf` or
`mentionOf` missing a party is skipped with a `ProvWarning` under both.

### PROV-XML

- A reference element with no `prov:ref` whose child is itself a reference, the shape
  ProvToolbox writes for a `hadMember` member, is resolved with a `ProvWarning`; the intent
  is unambiguous. A reference with neither `prov:ref` nor text raises `ProvXMLException`.
- A `prov:hadMember` element with several `<prov:entity>` children, which the schema allows,
  reads as one `hadMember` per member, each with the element's `prov:id`, collection and
  attributes. An element with no `<prov:entity>` child is skipped with a `ProvWarning`.
- `<prov:other>` elements and attributes the model cannot represent are skipped with a
  `ProvWarning`.
- Names escaped as in C3 are unescaped.

### PROV-JSONLD

- The decoder accepts the submission's compacted shape only. It is not a JSON-LD processor:
  no expansion, no remote contexts.
- ProvToolbox's `prov:`-prefixed spellings of the type and special terms are accepted.
- An array-valued `entity` on a `Membership` statement, which the submission (section 4.18)
  allows and ProvToolbox always writes, decodes to one `hadMember` per member, each with
  the statement's `@id` and attributes; an empty array raises `ProvJSONLDException`.
- Attribute values follow the 2026-10-14 revision of the PROV-JSONLD schema
  ([openprov/prov-jsonld#7](https://github.com/openprov/prov-jsonld/issues/7)). A node
  reference, such as `{"@id": "ex:shed"}`, is a qualified name under any attribute. A bare
  string is an IRI under `type`, `location` and `role`, which the context coerces to `@id`,
  and a string under any other attribute. A node reference, or a bare string under those
  three terms, whose IRI no declared namespace compacts, raises `ProvJSONLDException`. One
  that names a blank node (`_:`) refers to no record, so the reader drops it with a
  `ProvWarning` and keeps the attribute's other values. A node reference with a key other
  than `@id`, or with an empty `@id`, raises `ProvJSONLDException`. `prov` writes a
  qualified name under any attribute other than `type`, `location` and `role` as a node
  reference. It still reads an `xsd:QName` or `prov:QUALIFIED_NAME` value object, the form
  3.2.x wrote, as a qualified name, although a JSON-LD processor reads that as a typed
  literal. The schema's `label` production admits only strings, so a qualified name
  under `prov:label` does not validate in either form.

### PROV-O

- An attribute predicate under a namespace declared neither in the document nor in the graph
  gets a minted prefix, with a `ProvWarning`.
- Two relations sharing an identifier raise, as C1 describes.
- A relation whose subject is a blank node reads with no identifier; an element's blank-node
  label resolves in the default namespace.
- An attribute whose object is a blank node that names no record, such as a
  `prov:hadGeneration` pointing at an anonymous generation, is dropped with a `ProvWarning`
  naming the subject and the predicate. A blank node that is an element's subject resolves as
  that element's identifier does, so it needs the default namespace the element itself needs.
- The document declares the source's own prefix bindings and the namespaces its names use,
  not rdflib's default prefix bindings. A source declaration identical to one of those
  defaults, such as `@prefix foaf: <http://xmlns.com/foaf/0.1/>`, is kept only when a name,
  or the text of an `xsd:QName` or `prov:QUALIFIED_NAME` literal, uses it, and an unused
  `ex` is kept. The exception is a namespace the reader mints for a short IRI, such as the
  `http://` of `<http://alice.example>`: it also declares every rdflib default binding
  under it, such as `foaf`, whether or not a name uses it. QName text under a prefix
  rdflib renamed, such as `"dc:x"^^xsd:QName` with the source's `dc` bound to another IRI,
  reads under rdflib's IRI for that prefix, because rdflib replaces the source's binding
  at parse. A prefix the source declares and no name uses is not written by `prov`'s
  Turtle, so it does not survive a round trip.
- `rdf_format` selects the RDF syntax to read.

`prov.read()` detects the format from the content and forwards each reader's own options
(`profile` for PROV-N; `rdf_format`, `relation_mapper` and `predicate_mapper` for PROV-O;
the `json.load` hooks for PROV-JSON and PROV-JSONLD, which receive each object after the
check for repeated keys). An option a format does not accept raises `TypeError` naming the
format.

## Edge cases

A table cell that cites a caveat points here. C3, C4, C11 and C12 apply to inputs no row covers.

- **C3. PROV-XML escapes attribute names that are not NCNames.** A name may start with a digit
  or contain `' ( ) , : ; [ ] =`; each illegal character is written as `_xHHHH_`, the OpenXML
  convention, and reversed on read ([#289](https://github.com/trungdong/prov/issues/289)). A third-party name that already looks like
  an escape is therefore unescaped.
- **C4. PROV-N local parts.** A character `PN_LOCAL` cannot express, such as a space, cannot
  be in a local part: `QualifiedName` rejects it when built, from any format or from code,
  since the only PROV-N spelling would be a percent-encoding that reads back as a different
  IRI ([#524](https://github.com/trungdong/prov/issues/524)). PROV-O rejects an IRI containing a space. A namespace prefix
  must be a valid `PN_PREFIX` (a letter first, then name characters or `.`, not ending in
  `.`). `Namespace` rejects one that is not when it is built, from any format or from code,
  and `prov` does not rename it ([#668](https://github.com/trungdong/prov/issues/668)).
- **C5. Empty language tag.** `Literal("hi", langtag="")` is rejected when built;
  PROV-XML's `xml:lang=""` is rejected on read
  ([#472](https://github.com/trungdong/prov/issues/472)).
- **C6. Language tag that is not BCP 47.** A tag such as `en_US` is rejected when the
  `Literal` is built, from any format or from code, so no writer meets one
  ([#472](https://github.com/trungdong/prov/issues/472)).
- **C7. Zone offsets that are not whole minutes.** Every format writes such an `xsd:dateTime`
  in UTC, because the datatype allows no seconds in an offset. The instant is unchanged and
  the round trip compares equal; the original offset is not preserved.
- **C10. Literals rdflib normalises on read.** rdflib rewrites some literal texts when it
  parses them, before `prov` sees them, so PROV-O reads these differently from every other
  format: an `xsd:dateTime` fraction beyond six digits is truncated to microseconds, so such
  a time reads as the truncated `datetime` where the other formats reject it as a time of a
  statement and keep it as a `Literal` as an attribute value
  ([#514](https://github.com/trungdong/prov/issues/514)); an `xsd:decimal` text in exponent
  form, such as `1e1`, which is outside the lexical space and compares as text elsewhere,
  reads as rdflib's decimal text and compares as the value `10`; a numeric spelling such as
  `05` or `1e0` reads as the canonical one, which compares equal; and an `xsd:duration` text
  reads in rdflib's normalised form, so `PT0S` reads as `P0D` and `PT90M` as `PT1H30M`
  ([#620](https://github.com/trungdong/prov/issues/620)), and the zero-duration row of the
  converted-value round trip is skipped for RDF.
- **C11. A `NaN` beside a decimal, or a decimal `NaN` beside a number.** rdflib's Turtle, long
  Turtle (`longturtle`), TriG and N3 writers order the values of one predicate by value. An
  `xsd:decimal` `NaN` or `sNaN` text, which rdflib parses to a `Decimal`, has no order against
  any number, and a well-formed `xsd:decimal` value has none against a NaN of any numeric
  datatype (a well-formed `xsd:double` or `xsd:float`, or a Python `float`). A record that
  holds either pair under one attribute therefore raises `decimal.InvalidOperation` when
  written to PROV-O in those four syntaxes. N-Triples, N-Quads, RDF/XML, JSON-LD, TriX and
  Hext write such a record, as does every other format.
- **C12. A `prov:type` equal to the record's own type.** PROV-O writes `prov:type` as
  `rdf:type`, so an asserted `prov:type` equal to the record's own class, such as `prov:Entity`
  on an entity or `prov:Derivation` on a derivation, is the same triple as the record's type.
  The reader cannot tell the two apart, so the value does not survive a round trip through
  PROV-O, and every other format keeps it. A subject typed with the class of its record type
  and with a subclass of that class, such as `prov:Derivation` and `prov:Revision`, reads
  back with the subclass as a `prov:type` and without the record type's class, in every
  triple order. A subject typed with the classes of two record types, such as
  `prov:Influence` and `prov:Derivation`, takes its record type from whichever of the two
  `rdf:type` triples the reader meets first.

## Corpus evidence

The [PROV-N conformance corpus](https://github.com/trungdong/prov/tree/main/src/prov/tests/provn) runs at every test run.

| Set | Profile | Files | Result |
| --- | --- | --- | --- |
| Every example in the PROV-N and PROV-DM Recommendations | `strict` | 127 | 94 parse and round-trip through the writer; 33 are excluded. |
| ProvToolbox's hand-written PROV-N test documents | `default` | 9 | 6 parse; 3 are excluded. |
| PROV-N that ProvToolbox's writer produced from the shared test corpus, compared with the PROV-JSON fixture of the same name | `default` | 388 | 229 equal; 159 differ for reasons in the generator, not in `prov`. |

The corpus README names every excluded or differing file with its reason.

## Related pages

{doc}`../explanation/unification-flattening` covers merge-time conformance, which the
tables above do not. {doc}`../explanation/prov-dm` gives the background for each component,
{doc}`model` is the class and method reference, {doc}`../howto/read-write` shows how to
read and write in any format, and the how-to pages cover each format: {doc}`../howto/provn`, {doc}`../howto/provjson`, {doc}`../howto/provxml`,
{doc}`../howto/provo-rdf`, {doc}`../howto/provjsonld`.

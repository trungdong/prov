# The PROV Data Model

`prov` is a Python implementation of the [W3C PROV Data Model](https://www.w3.org/TR/prov-dm/)
(PROV-DM). This page explains the concepts that PROV-DM defines, how they map onto the classes
and factory methods in {py:mod}`prov.model`, and how the library thinks about identifiers and
namespaces. It is background reading rather than a step-by-step guide: for a hands-on walk
through building a document see {doc}`../tutorial/getting-started`, and for the exhaustive API
listing see {doc}`../reference/index`.

## What provenance is

The W3C defines provenance as

> a record that describes the people, institutions, entities, and activities involved in
> producing, influencing, or delivering a piece of data or a thing.
>
> — [PROV-DM](https://www.w3.org/TR/prov-dm/), §1

Concretely, that is a record of where something came from: the entities involved in producing
it, the activities that acted on those entities, the agents responsible, and how all of these
relate over time. A provenance record lets a consumer of some data answer questions such as
"which source files was this report derived from?", "who ran the process that generated it?",
and "was it revised after it was first published?". PROV is the W3C's interoperable model for
expressing exactly these facts so that they can be exchanged between systems.

PROV deliberately describes provenance *as asserted* — it captures someone's account of what
happened, not an absolute truth. Two people can make different, even conflicting, assertions
about the same thing, and both are valid PROV. This matters when we come to unification and
flattening (see {doc}`unification-flattening`).

## The core: entities, activities, and agents

Everything in PROV is built from three kinds of thing, which PROV-DM defines as follows
(§5.1.1, §5.1.2, and §5.3.1 of [PROV-DM](https://www.w3.org/TR/prov-dm/)):

- An **entity** is "a physical, digital, conceptual, or other kind of thing with some fixed
  aspects" — a file, a document, a dataset, a physical object. In `prov` an entity is a
  {py:class}`~prov.model.ProvEntity`, created with {py:meth}`~prov.model.ProvBundle.entity`.
- An **activity** is "something that occurs over a period of time and acts upon or with
  entities" — running a program, editing a document, publishing a report. It is a
  {py:class}`~prov.model.ProvActivity`, created with {py:meth}`~prov.model.ProvBundle.activity`.
- An **agent** is "something that bears some form of responsibility for an activity taking
  place, for the existence of an entity, or for another agent's activity" — a person, an
  organisation, or a piece of software. It is a {py:class}`~prov.model.ProvAgent`, created with
  {py:meth}`~prov.model.ProvBundle.agent`.

The wording above is quoted from PROV-DM; the examples and the mapping to `prov` classes are
this library's own.

These three node types are joined by **relations** (edges) such as *wasGeneratedBy*,
*used*, *wasDerivedFrom*, and *wasAssociatedWith*. In `prov`, nodes are subclasses of
{py:class}`~prov.model.ProvElement` and relations are subclasses of
{py:class}`~prov.model.ProvRelation`; both descend from {py:class}`~prov.model.ProvRecord`,
the common base class for every PROV statement. A record carries a set of
`(QualifiedName, value)` attribute pairs, some of which are *formal attributes* fixed per
record type (for example, a generation's formal attributes are the entity and the activity).

## The six components of PROV-DM

PROV-DM organises its vocabulary into six *components*. `prov` mirrors this grouping in the
section structure of {py:mod}`prov.model`. Every PROV-DM type and relation maps to a `prov`
class and to a factory method on {py:class}`~prov.model.ProvBundle` (which
{py:class}`~prov.model.ProvDocument` inherits). Many relation factories have both a canonical
method name and a friendlier PROV-N-style alias; both are shown below and are fully
interchangeable.

### Component 1 — Entities and Activities

The temporal backbone of provenance: entities, activities, and the relations describing how
activities generate, use, start, end, and invalidate entities, and how they communicate.

| PROV-DM concept | `prov` class | `ProvBundle` factory method |
| --- | --- | --- |
| Entity | {py:class}`~prov.model.ProvEntity` | `entity()` |
| Activity | {py:class}`~prov.model.ProvActivity` | `activity()` |
| Generation (*wasGeneratedBy*) | {py:class}`~prov.model.ProvGeneration` | `generation()` / `wasGeneratedBy()` |
| Usage (*used*) | {py:class}`~prov.model.ProvUsage` | `usage()` / `used()` |
| Communication (*wasInformedBy*) | {py:class}`~prov.model.ProvCommunication` | `communication()` / `wasInformedBy()` |
| Start (*wasStartedBy*) | {py:class}`~prov.model.ProvStart` | `start()` / `wasStartedBy()` |
| End (*wasEndedBy*) | {py:class}`~prov.model.ProvEnd` | `end()` / `wasEndedBy()` |
| Invalidation (*wasInvalidatedBy*) | {py:class}`~prov.model.ProvInvalidation` | `invalidation()` / `wasInvalidatedBy()` |

### Component 2 — Derivations

How one entity is derived from another, with three specialised kinds of derivation.

| PROV-DM concept | `prov` class | `ProvBundle` factory method |
| --- | --- | --- |
| Derivation (*wasDerivedFrom*) | {py:class}`~prov.model.ProvDerivation` | `derivation()` / `wasDerivedFrom()` |
| Revision (*wasRevisionOf*) | {py:class}`~prov.model.ProvDerivation` | `revision()` / `wasRevisionOf()` |
| Quotation (*wasQuotedFrom*) | {py:class}`~prov.model.ProvDerivation` | `quotation()` / `wasQuotedFrom()` |
| Primary Source (*hadPrimarySource*) | {py:class}`~prov.model.ProvDerivation` | `primary_source()` / `hadPrimarySource()` |

Revision, quotation, and primary source are, in PROV-DM, *subtypes* of derivation. `prov`
represents all four with the single class {py:class}`~prov.model.ProvDerivation`; the three
subtype factories add the corresponding `prov:type` (`prov:Revision`, `prov:Quotation`,
`prov:PrimarySource`) to the record.

### Component 3 — Agents, Responsibility, and Influence

Who is responsible for what, and the most general relation of all — influence.

| PROV-DM concept | `prov` class | `ProvBundle` factory method |
| --- | --- | --- |
| Agent | {py:class}`~prov.model.ProvAgent` | `agent()` |
| Attribution (*wasAttributedTo*) | {py:class}`~prov.model.ProvAttribution` | `attribution()` / `wasAttributedTo()` |
| Association (*wasAssociatedWith*) | {py:class}`~prov.model.ProvAssociation` | `association()` / `wasAssociatedWith()` |
| Delegation (*actedOnBehalfOf*) | {py:class}`~prov.model.ProvDelegation` | `delegation()` / `actedOnBehalfOf()` |
| Influence (*wasInfluencedBy*) | {py:class}`~prov.model.ProvInfluence` | `influence()` / `wasInfluencedBy()` |

PROV-DM also defines agent *subtypes* — Person, Organization, and SoftwareAgent — and the
Plan entity subtype used with associations. These are not separate classes or factories in
`prov`; you express them by adding a `prov:type` attribute (for example,
`agent("ag", {prov.PROV_TYPE: "prov:Person"})`).

### Component 4 — Bundles

PROV-DM defines a **bundle** as "a named set of provenance descriptions, and is itself an
entity, so allowing provenance of provenance to be expressed"
([PROV-DM](https://www.w3.org/TR/prov-dm/), §5.4.1). A bundle lets you attribute a body of PROV
to whoever asserted it. In `prov`, a bundle is a {py:class}`~prov.model.ProvBundle`, and a
{py:class}`~prov.model.ProvDocument` is the special top-level bundle that may itself contain
named bundles.

| PROV-DM concept | `prov` class | factory method |
| --- | --- | --- |
| Bundle | {py:class}`~prov.model.ProvBundle` | {py:meth}`ProvDocument.bundle() <prov.model.ProvDocument.bundle>` |

Only a {py:class}`~prov.model.ProvDocument` may contain bundles; a plain
{py:class}`~prov.model.ProvBundle` may not nest further. See {doc}`unification-flattening`
for how {py:meth}`~prov.model.ProvDocument.flattened` collapses bundle contents back up into
the document.

### Component 5 — Alternate Entities

Relations that connect different entities that present aspects of the same underlying thing.

| PROV-DM concept | `prov` class | `ProvBundle` factory method |
| --- | --- | --- |
| Specialization (*specializationOf*) | {py:class}`~prov.model.ProvSpecialization` | `specialization()` / `specializationOf()` |
| Alternate (*alternateOf*) | {py:class}`~prov.model.ProvAlternate` | `alternate()` / `alternateOf()` |
| Mention (*mentionOf*) | {py:class}`~prov.model.ProvMention` | `mention()` / `mentionOf()` |

Mention is a specialisation that additionally names the bundle in which the more specific
entity is described; {py:class}`~prov.model.ProvMention` is a subclass of
{py:class}`~prov.model.ProvSpecialization`.

### Component 6 — Collections

Entities that are collections of other entities, and membership in them.

| PROV-DM concept | `prov` class | `ProvBundle` factory method |
| --- | --- | --- |
| Collection | {py:class}`~prov.model.ProvEntity` (typed `prov:Collection`) | `collection()` |
| Membership (*hadMember*) | {py:class}`~prov.model.ProvMembership` | `membership()` / `hadMember()` |

A collection is an ordinary {py:class}`~prov.model.ProvEntity` carrying the
`prov:Collection` type; the `collection()` factory adds that type for you. (PROV-DM's
`EmptyCollection` is likewise expressed as the `prov:EmptyCollection` type rather than a
dedicated class.)

## Qualified names and namespaces

Every identifier in PROV — of a record, and of every attribute name — is a *qualified name*:
a namespace prefix plus a local part, such as `ex:crime`, which expands to a full IRI. This is
the same mechanism as in XML and RDF, and it is what makes PROV documents from different
sources interoperable: two systems agree on meaning by agreeing on IRIs, not on bare local
names.

In `prov` this is modelled by {py:class}`~prov.identifier.Namespace` and
{py:class}`~prov.identifier.QualifiedName` in {py:mod}`prov.identifier`. A namespace bundles a
prefix with a base URI; asking it for a local name yields a qualified name:

```python
from prov.identifier import Namespace

ex = Namespace("ex", "http://example.org/")
qn = ex["crime"]            # a QualifiedName
print(qn)                   # ex:crime
print(qn.uri)               # http://example.org/crime
```

You rarely construct these by hand. A bundle keeps a `NamespaceManager` that records the
namespaces you register and resolves prefixes as you build statements. Declare namespaces on
a document with {py:meth}`~prov.model.ProvBundle.add_namespace` (and an optional *default*
namespace with {py:meth}`~prov.model.ProvBundle.set_default_namespace`), after which any string
you pass as an identifier or attribute name — `"ex:crime"`, `"crime"` — is resolved to a
{py:class}`~prov.identifier.QualifiedName` against the registered namespaces:

```python
import prov.model as prov

document = prov.ProvDocument()
document.set_default_namespace("http://example.org/")
document.add_namespace("ex", "http://example.org/ns#")

document.entity("crime")               # resolves against the default namespace
document.entity("ex:report")           # resolves against the ex prefix
```

A prefix must be registered before it is used; passing `"ex:report"` before adding the `ex`
namespace raises {py:class}`~prov.model.ProvExceptionInvalidQualifiedName`. The `prov:` prefix
for the PROV vocabulary itself is always available, which is why constants such as
{py:data}`~prov.constants.PROV_TYPE` and {py:data}`~prov.constants.PROV_ROLE` can be used
without registering anything.

## The wider PROV world

PROV-DM is one document in a family of W3C Recommendations. `prov` implements the model and
several of its serialisations:

- [**PROV-DM**](https://www.w3.org/TR/prov-dm/) — the data model described on this page.
- [**PROV-N**](https://www.w3.org/TR/prov-n/) — the human-readable notation, produced by
  {py:meth}`~prov.model.ProvDocument.get_provn` and used throughout these docs. `prov` writes
  PROV-N but does not parse it.
- [**PROV-O**](https://www.w3.org/TR/prov-o/) — the mapping of PROV-DM onto an OWL ontology
  for expression as RDF, handled by the `rdf` serializer.

`prov` additionally supports the PROV-JSON and PROV-XML serialisations. For choosing and using
each format see the how-to guides ({doc}`../howto/provjson`, {doc}`../howto/provo-rdf`,
{doc}`../howto/provxml`, {doc}`../howto/provn`).

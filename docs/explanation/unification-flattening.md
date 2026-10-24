# Unification and flattening

A document built up over time, or merged from several sources, describes one thing in
several statements and splits facts across named bundles. Two transformations tidy this up,
{py:meth}`~prov.model.ProvDocument.flattened` and {py:meth}`~prov.model.ProvDocument.unified`.
This page explains each with an example and says how far `unified()` goes towards
PROV-CONSTRAINTS normalization.

Both transformations leave the original untouched. `unified()` returns a new document.
`flattened()` returns a new document, or the document itself when it has no bundles.

## Flattening

{py:meth}`~prov.model.ProvDocument.flattened` produces a new document in which every
record from every bundle has moved up to the top level, alongside the document's own
records; the bundle structure is discarded. Flattening merges, deduplicates and
reconciles nothing, so an entity described both in the document and inside a bundle ends
up as two statements side by side.

### Worked example

Start with one top-level entity and a bundle holding two records and a relation:

```python
import prov.model as pm

d = pm.ProvDocument()
d.set_default_namespace("http://example.org/")
d.entity("e1")
b = d.bundle("bundle1")
b.entity("e2")
b.activity("a1")
b.wasGeneratedBy("e2", "a1")

print(d.get_provn())
```

```text
document
  default <http://example.org/>

  entity(e1)
  bundle bundle1
    entity(e2)
    activity(a1, -, -)
    wasGeneratedBy(e2, a1, -)
  endBundle
endDocument
```

`flattened()` lifts the bundle's three records up next to `e1` and drops the wrapper:

```python
print(d.flattened().get_provn())
```

```text
document
  default <http://example.org/>

  entity(e1)
  entity(e2)
  activity(a1, -, -)
  wasGeneratedBy(e2, a1, -)
endDocument
```

## Unification

{py:meth}`~prov.model.ProvDocument.unified` addresses the same thing described by
several statements, each carrying a few attributes, and combines the statements into one
record.

### What `unified()` does

For each identifier that appears on more than one record of one base record type,
`unified()` builds a single merged record by term unification of those records' formal
attributes, following the key constraints of the W3C specification. Position by position:

- an absent formal attribute is an existential ("unknown") and unifies with anything,
  except in the non-expandable positions described at the end of the page;
- two equal concrete values unify to that value;
- two different concrete values do not unify, and the merge raises
  {py:class}`~prov.model.ProvUnificationError`.

The records' remaining ("extra") attributes are unioned onto the merged record, as a set,
so identical values are deduplicated and distinct values all accumulate. Records with a
unique identifier, and records with no identifier, are not merged, and neither are
`alternateOf`, `specializationOf`, `mentionOf` and `hadMember` records that share one,
since PROV-DM and PROV-Links give these four relations no identifier. After the merge,
`unified()` keeps each record once. A record equal to an earlier one, by the library's
`==`, is dropped and the earlier one keeps its position. Two anonymous `used` statements
that differ in one attribute are two statements and both stay.

### Worked example

Assert the same entity `e1` twice, each time with a different attribute:

```python
import prov.model as pm

d = pm.ProvDocument()
d.set_default_namespace("http://example.org/")
d.add_namespace("ex", "http://example.org/ns#")
d.entity("e1", {"ex:type": "File"})
d.entity("e1", {"ex:size": 1024})

print(d.get_provn())
```

```text
document
  default <http://example.org/>
  prefix ex <http://example.org/ns#>

  entity(e1, [ex:type="File"])
  entity(e1, [ex:size=1024])
endDocument
```

`unified()` collapses the two `e1` statements into one, with the union of their
attributes:

```python
print(d.unified().get_provn())
```

```text
document
  default <http://example.org/>
  prefix ex <http://example.org/ns#>

  entity(e1, [ex:type="File", ex:size=1024])
endDocument
```

`unified()` is the only place in the model that raises over a same-identifier conflict.
Asserting records never checks for one, by design, because PROV statements are asserted
incomplete, one piece at a time, and a later `unified()` call, if any, reconciles them.

{py:meth}`ProvDocument.unified() <prov.model.ProvDocument.unified>` applies this to the
document's top-level records and, independently, to each bundle. Nothing merges across a
bundle boundary, as [PROV-CONSTRAINTS requires](https://www.w3.org/TR/prov-constraints/#bundle-constraints).

`flattened().unified()` is a different, deliberate tool. `flattened()` has discarded the
bundle structure, so `unified()` then merges same-identifier records across former bundle
boundaries, which no PROV-CONSTRAINTS rule licenses and which may conflate two bundles'
unrelated uses of one local name. Use plain `document.unified()` when scoping matters.

### Relation to PROV-CONSTRAINTS

[PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/) defines normalization as
inference plus term unification driven by uniqueness constraints, and validity as a
separate check that rejects documents breaking constraints such as type disjointness or
event ordering. `unified()` implements the term-unification part, keyed on the record
identifier, within these limits:

- **Only identifiers drive merging.** Two records merge if and only if they carry the same
  qualified-name identifier and neither is one of the four relations above. Most relations
  are asserted without an identifier, so relations are almost never unified.
- **Records of incompatible types raise; permitted overlaps stay separate.** Across types
  sharing one identifier, `unified()` applies the specification's
  [impossibility constraints](https://www.w3.org/TR/prov-constraints/#impossibility-constraints). An
  `entity(x)` and an `activity(x)` raise {py:class}`~prov.model.ProvUnificationError`,
  because entities and activities are disjoint, while an `agent(x)` and an `entity(x)` are
  not and stay as two independently merged records.
- **Absent means unknown, with exceptions.** PROV-N's explicit `-` placeholder is not
  represented, so an absent formal attribute behaves as an existential. In the positions
  the specification makes [non-expandable](https://www.w3.org/TR/prov-constraints/#optional-identifiers-and-attributes), the
  plan of an association, the activity of a derivation, and the generation and usage of a
  derivation with no activity, an absent value against a present one raises the same error.
- **No inference.** The [uniqueness constraints](https://www.w3.org/TR/prov-constraints/#uniqueness-constraints) keyed on
  something other than the record identifier (for example, that two generations of one entity by one activity are the same
  generation) are not applied, so `unified()` never concludes that two differently
  identified records denote the same thing.
- **Not a validator.** `unified()` checks nothing unrelated to merging, such as event
  ordering. Do not rely on it to certify that a document is valid PROV, or to reconcile
  records that do not already share an identifier. Validation is a separate, opt-in
  concern, tracked as [#62](https://github.com/trungdong/prov/issues/62).

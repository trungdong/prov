# Unification and flattening

A PROV document is an *account* — a set of assertions someone makes about what happened. Real
documents accumulate structure that is convenient to build but awkward to consume: the same
entity described in two separate statements, or facts split across named bundles. `prov`
offers two transformations that tidy this up: {py:meth}`~prov.model.ProvDocument.flattened`
and {py:meth}`~prov.model.ProvBundle.unified`. This page explains what each one does, shows a
worked example of each, and explains how the current `unified()` diverges from the
W3C specification.

Both transformations are **non-destructive**: they return a new document (or bundle) and leave
the original untouched.

## Flattening

A {py:class}`~prov.model.ProvDocument` may contain named bundles, each holding its own
records. {py:meth}`~prov.model.ProvDocument.flattened` produces a new document in which every
record from every bundle has been moved up to the top level, alongside the document's own
records. The bundle *structure* is discarded — only the statements survive.

This is a purely structural move. Flattening does not merge, deduplicate, or reconcile anything;
if the same entity is described both in the document and inside a bundle, both statements simply
end up side by side at the top level. (If the document has no bundles, `flattened()` returns the
document itself unchanged.)

### Worked example

Start with a document that has one top-level entity and a bundle containing two more records
and a relation:

```python
import prov.model as prov

d = prov.ProvDocument()
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

Calling `flattened()` lifts the bundle's three records up next to `e1` and drops the
`bundle … endBundle` wrapper:

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

{py:meth}`~prov.model.ProvBundle.unified` addresses a different kind of redundancy: the same
thing described by more than one statement. When a document is built incrementally, or merged
from several sources, an entity or activity may be asserted several times, each assertion
carrying a few attributes. Unification combines those into one record.

### What `unified()` does today

The current implementation is deliberately simple. For each **identifier** that appears on more
than one record, `unified()` builds a single merged record: it starts from a copy of the first
record with that identifier and adds ("unions") the attributes of every other record sharing
the identifier. Records with a unique identifier, and records with no identifier at all, pass
through untouched. Because attributes are held in a set, identical attribute values are
deduplicated, but distinct values all accumulate on the merged record.

{py:meth}`ProvDocument.unified() <prov.model.ProvDocument.unified>` applies this to the
document's top-level records and, recursively, to each contained bundle, **preserving** the
bundle structure (unlike `flattened()`). {py:meth}`ProvBundle.unified() <prov.model.ProvBundle.unified>`
does it for a single bundle.

Three consequences of this simplicity are:

- **Only identifiers drive merging.** Two records merge if and only if they carry the same
  qualified-name identifier. Most PROV relations are asserted without an identifier, so
  relations are almost never unified.
- **No type or attribute conflicts are detected.** The first record's PROV type and class are
  kept; attributes from the other records are unioned in regardless of whether they conflict.
  Asserting `entity(x)` and `activity(x)` with the same identifier, or two entities with
  contradictory values for the same functional attribute, produces a merged record rather than
  an error.
- **No inference or key-based unification.** The model does not use PROV's *keys* (for example,
  the fact that an entity has at most one generation) to unify records that lack a shared
  identifier, and it draws no new conclusions.

### Worked example

Assert the same entity `e1` twice, each time with a different attribute:

```python
import prov.model as prov

d = prov.ProvDocument()
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

`unified()` collapses the two `e1` statements into one, with the union of their attributes:

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

### How this differs from the specification

The W3C [PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/) Recommendation defines
*normalization* precisely, as the combination of several inference and constraint rules:
*term unification* driven by uniqueness constraints (keys), the merging of records that these
rules force to be equal, and the rejection of documents that violate constraints such as
type disjointness or event ordering. A conforming normalization can conclude that two
differently written records denote the same thing, and can declare a document *invalid*.

`prov`'s `unified()` does **none** of that inference or validation. It is a shallow,
identifier-keyed attribute union — useful for tidying up incrementally built documents, but
not a conformant implementation of PROV-CONSTRAINTS normalization. The source itself flags
this, with a `TODO: Check unification rules in the PROV-CONSTRAINTS document` comment above
`_unified_records`.

Fixing this is a **3.0** item: because a spec-conformant `unified()` would change behaviour
(merging or rejecting documents that today pass through unchanged), it cannot land in the 2.x
series under the API-stability promise. See the
[roadmap](https://github.com/trungdong/prov/blob/master/ROADMAP.md) for where this sits among
the planned releases. Until then, treat `unified()` as the convenience it is, and do not rely
on it to validate a document or to reconcile records that do not already share an identifier.

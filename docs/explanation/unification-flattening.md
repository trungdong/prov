# Unification and flattening

A PROV document is an *account* — a set of assertions someone makes about what happened. Real
documents accumulate structure that is convenient to build but awkward to consume: the same
entity described in two separate statements, or facts split across named bundles. `prov`
offers two transformations that tidy this up: {py:meth}`~prov.model.ProvDocument.flattened`
and {py:meth}`~prov.model.ProvBundle.unified`. This page explains what each one does, shows a
worked example of each, and explains how far `unified()` goes towards the W3C
specification's normalization.

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

### What `unified()` does

For each **identifier** that appears on more than one record, `unified()` builds a single
merged record by *term unification* of those records' formal attributes, following the key
constraints of the W3C specification. Position by position:

- an **absent** formal attribute is an existential ("unknown") and unifies with anything;
- two **equal** concrete values unify to that value;
- two **different** concrete values do not unify, and the merge raises
  {py:class}`~prov.model.ProvUnificationError`.

The records' remaining ("extra") attributes are unioned onto the merged record. Because those
are held in a set, identical values are deduplicated while distinct values all accumulate.
Records with a unique identifier, and records with no identifier at all, pass through
untouched.

`unified()` is the *only* place in `prov` that can raise over a same-identifier conflict.
Building or asserting records — `bundle.entity(...)`, `bundle.activity(...)`, and friends —
never checks for one, by design: PROV statements are legitimately asserted incomplete, one
piece at a time, expecting a later `unified()` call (or none at all) to reconcile them.
Validating a document *without* merging it is a separate, opt-in concern, tracked as
[issue #62](https://github.com/trungdong/prov/issues/62).

{py:meth}`ProvDocument.unified() <prov.model.ProvDocument.unified>` applies this to the
document's top-level records and, independently, to each contained bundle, **preserving** the
bundle structure (unlike `flattened()`) — nothing is merged across a bundle boundary, per the
specification's §7.2. {py:meth}`ProvBundle.unified() <prov.model.ProvBundle.unified>` does it
for a single bundle.

Calling `flattened().unified()` — flattening a document first, then unifying the result — is a
different, deliberate tool: because `flattened()` has already discarded the bundle structure,
the subsequent `unified()` sees one scope and merges same-identifier records **across** what
used to be bundle boundaries. No PROV-CONSTRAINTS rule licenses that; it is a single-instance
view for callers who want the broadest possible merge and accept that two bundles asserting the
same local name might describe different real-world things. `prov` keeps this idiom working
(it is exercised in the test suite), but it sits outside PROV-CONSTRAINTS semantics — reach for
plain `document.unified()` when per-bundle scoping matters.

Four limits are worth knowing:

- **Only identifiers drive merging.** Two records merge if and only if they carry the same
  qualified-name identifier. Most PROV relations are asserted without an identifier, so
  relations are almost never unified.
- **Records of incompatible types raise; spec-permitted overlaps stay separate.** Term
  unification as described above applies within a group of records that share both an
  identifier *and* a base record type. Across types sharing one identifier, `unified()`
  consults the PROV-CONSTRAINTS type-compatibility rules (Constraints 53/54/55): an
  `entity(x)` and an `activity(x)` sharing the identifier `x` raise
  {py:class}`~prov.model.ProvUnificationError` naming both types — the specification makes
  entities and activities disjoint — while an `agent(x)` and an `entity(x)` sharing `x` are
  *not* disjoint under the specification, so `unified()` keeps them as two separate,
  independently-merged records rather than combining or rejecting them.
- **The placeholder `-` is not represented.** PROV-N distinguishes an omitted term from an
  explicit `-`, which is a constant and unifies only with itself; `prov`'s model has no way to
  express the latter (every deserializer drops the distinction), so an absent formal attribute
  always behaves as an existential.
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

`prov`'s `unified()` implements the term-unification half of that picture, keyed on the record
identifier, and rejects documents whose same-identifier, same-type records hold irreconcilable
attribute values, or whose same-identifier records span types the specification makes disjoint.
Two things it does *not* do:

- It does not perform the *inference* half. The uniqueness constraints that key on something
  other than the record identifier (Constraints 24–29 — for example, that two generations of
  the same entity by the same activity must be the same generation) are not applied, so
  `unified()` never concludes that two differently identified records denote the same thing.
  Those belong to an opt-in validation engine, tracked as
  [issue #62](https://github.com/trungdong/prov/issues/62).
- It does not check constraints that have nothing to do with merging, such as event ordering.

So `unified()` is a normalization step, not a validator: do not rely on it to certify that a
document is valid PROV, nor to reconcile records that do not already share an identifier. See
the [roadmap](https://github.com/trungdong/prov/blob/master/ROADMAP.md) for where the
validation engine sits among the planned releases.

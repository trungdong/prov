# Upgrading to 3.0

## Summary

3.0 is the only release in the `prov` roadmap allowed to break compatibility. Two changes
matter for most users:

1. **`prov.dot` and `prov.graph` need extras.** Install `prov[dot]` or `prov[graph]` if
   your code imports either module, or calls `prov_to_dot()`, `prov_to_graph()` or
   `graph_to_prov()`.
2. **`unified()` raises instead of silently merging.** `ProvBundle.unified()` and
   `ProvDocument.unified()` raise `prov.model.ProvUnificationError` when records sharing an
   identifier disagree on a formal attribute or have incompatible types. `prov_to_graph()`
   calls `unified()` internally, so it can raise too. `prov_to_dot()` catches the error and
   renders the document without unifying it.

Both were signposted from 2.4.0 with a runtime warning, which every later 2.x release also
carries. **If your test suite ran clean under 2.4.0 or later with
`-W error::DeprecationWarning -W error::FutureWarning`, neither change affects your code.**

Everything else is a set of narrow bug fixes, mostly to serializer output for edge cases,
and one renamed type alias. Those could not be signposted by a warning, because they
change the result of calls that already succeeded. Skim the table below for the ones that
touch your code, or skip to [what's removed](#removed).

## Install the extras you need

| If your code uses | Install |
|---|---|
| `prov.dot`, `prov_to_dot()` | `prov[dot]` |
| `prov.graph`, `prov_to_graph()`, `graph_to_prov()` | `prov[graph]` |
| The interactive display in `ProvBundle.plot()` or `ProvDocument.plot()` | `prov[plot]` |

A plain `pip install prov` still gives you the core data model and the PROV-JSON, PROV-N
and PROV-JSONLD serializers. Extras combine, for example
`pip install "prov[rdf,xml,dot,graph]"`. See {doc}`installation`.

## Dependency changes

- **`python-dateutil` is dropped** in favour of the standard library's
  `datetime.fromisoformat()`. Typical ISO 8601 timestamps are unaffected. Non-standard
  strings that dateutil parsed permissively, such as `"Nov 7, 2011"` or a bare `xsd:date`
  like `"2011-11-16"`, are no longer accepted. An unparseable `time=`, `startTime=` or
  `endTime=` factory argument now raises `prov.model.ProvException` instead of a raw
  `dateutil` error.
- **`rdflib` floor raised to 7.0.0.** Upgrade if you pin rdflib 6.x alongside `prov[rdf]`.
  Output differences are limited to those rdflib 7 already introduced under 2.x.

## Bug fixes that change output or equality

Each of these fixes a real bug, but each also changes output or equality for inputs that
worked without error before, which is why they waited for 3.0. Five need action:

| Issue | What changed | Action |
|---|---|---|
| [#34](https://github.com/trungdong/prov/issues/34) | Attribute sets used to silently drop Python-equal but differently typed values (`2` and `2.0`, `1` and `True`). All distinct values are now kept. `get_attribute()`, `get_asserted_types()` and `.value` keep their 2.x behaviour. | Recheck code that reads attributes through `attributes`, `extra_attributes`, equality or serialization and relied on the old collapsing, or that mutated a `get_asserted_types()` result in place, which no longer writes through. |
| [#77](https://github.com/trungdong/prov/issues/77) | `xsd:decimal` literals now compare and hash by value, not lexical form. `10` and `10.00` are now equal. | Recheck code relying on differently formatted decimals comparing unequal. |
| [#259](https://github.com/trungdong/prov/issues/259) | Language tags now compare and hash case-insensitively. Serialized output keeps the original casing. | Recheck code relying on differently cased tags comparing unequal. |
| [#228](https://github.com/trungdong/prov/issues/228) | Malformed PROV-JSON now raises `prov.serializers.provjson.ProvJSONException` instead of a raw `KeyError`, `AttributeError` or `TypeError`. | **Update exception handlers.** Catch `ProvJSONException` instead of the raw types around PROV-JSON deserialization. |
| [#273](https://github.com/trungdong/prov/issues/273) | PROV-XML parsing now uses a hardened parser. External DTD entities no longer resolve, and affected values come back empty instead of expanded. | If you need to detect rather than neutralise entity use, reject documents containing `<!DOCTYPE` before deserializing. |

The other fixes change what a serializer writes for inputs that already worked, and a few
change what a value decodes to in Python: a `prov:QUALIFIED_NAME` literal becomes a
`QualifiedName`, `xsd:base64Binary` decodes to its base64 text rather than a bytes repr, a
qualified Start or End node's time becomes the relation's formal time, PROV-JSON's typed
`$` value is always a string, and two inputs that raised `ValueError` now succeed. The
3.0.0 section of the {doc}`changelog <history>` lists each with its issue. Recheck byte comparisons of serialized output, and code that
reads those decoded values.

**Documented limitation, not a fix.** Two same-identifier relations that differ in
`prov:time` still cannot round-trip through PROV-O, because PROV-O names a relation by its
identifier; decoding raises a clear, chained error (caveat C1 on
{doc}`reference/conformance`, [#217](https://github.com/trungdong/prov/issues/217)). Give
such relations distinct identifiers if they must survive an RDF round trip.

## `unified()` now enforces PROV-CONSTRAINTS

Before 3.0, `unified()` merged same-identifier records by unioning their attributes with no
conflict detection. 3.0 merges by [PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/)
term unification; {doc}`explanation/unification-flattening` has the full model. In short:

- **Two different concrete values for the same formal attribute raise
  `prov.model.ProvUnificationError`** instead of merging silently. A missing attribute
  still unifies with any concrete value, as before.
- Records sharing an identifier but of **incompatible types**, such as an entity and an
  activity, raise the same error, naming both types, instead of merging into whichever
  record was asserted first. Overlaps the specification permits, such as an agent that is
  also an entity, still merge as separate, per-type records.
- Each bundle unifies independently. Nothing merges across a bundle boundary.
- Non-formal ("extra") attributes keep their set-union behaviour.
- [Uniqueness constraints](https://www.w3.org/TR/prov-constraints/#uniqueness-constraints)
  not keyed on the record identifier are out of scope. They belong to the separate, opt-in
  validation engine tracked as [#62](https://github.com/trungdong/prov/issues/62).

`ProvUnificationError` subclasses `ProvException`, so an existing `except ProvException`
handler around `unified()` keeps working. `prov_to_dot()` catches the error and falls back
to rendering the non-unified bundle. `prov_to_graph()` lets it propagate. Building and
serializing a document with these conflicts is still legal in 3.0, because `prov` performs
no structural validation at assertion or serialization time by design
([#257](https://github.com/trungdong/prov/issues/257)). Only calling `unified()` on such a
document, or decoding its RDF form, raises.

**Action:** if you call `unified()`, directly or through `prov_to_graph()`, on documents
where same-identifier records might disagree on a formal attribute or type, catch
`ProvUnificationError` or fix the document to avoid the conflict.

(removed)=

## Removed

3.0 removes everything 2.4.0 marked deprecated. Nothing else is scheduled for removal.

- The unconditional `pydot` and `networkx` dependencies, superseded by the `dot` and
  `graph` extras above. `import prov.dot` and `import prov.graph` now raise
  `ModuleNotFoundError` naming the extra to install.
- `python-dateutil` as a runtime dependency, and the incidental `prov.model.dateutil`
  re-export that came from importing it.
- `prov.model.GenrationRef`, the misspelled type alias used for the `generation` parameter
  of `wasDerivedFrom()`, `wasRevisionOf()`, `wasQuotedFrom()` and `hadPrimarySource()`. It
  is renamed `GenerationRef`, with no alias kept for the old spelling.

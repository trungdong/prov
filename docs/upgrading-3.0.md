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

## Install the extras you need

A plain `pip install prov` still gives you the core data model and the PROV-JSON, PROV-N
and PROV-JSONLD serializers. {doc}`installation` lists the extra for everything else:
`dot` for `prov.dot`, `graph` for `prov.graph`, `plot` for the interactive display in
`plot()`, and `rdf` and `xml` for those formats.

## Dependency changes

- **`python-dateutil` is dropped** for `datetime.fromisoformat()`. ISO 8601 timestamps are
  unaffected; strings dateutil parsed permissively, such as `"Nov 7, 2011"` or a bare
  `xsd:date`, are not, and an unparseable time argument raises `prov.model.ProvException`.
- **`rdflib` floor raised to 7.0.0.** Upgrade if you pin rdflib 6.x alongside `prov[rdf]`.

## Bug fixes that change output or equality

Everything else is narrow bug fixes, mostly to serializer output for edge cases, and one
renamed type alias, each changing output or equality for inputs that already worked. Five
need action:

| Issue | What changed | Action |
|---|---|---|
| [#34](https://github.com/trungdong/prov/issues/34) | Attribute sets used to silently drop Python-equal but differently typed values (`2` and `2.0`, `1` and `True`). All distinct values are now kept. `get_attribute()`, `get_asserted_types()` and `.value` keep their 2.x behaviour. | Recheck code that reads attributes through `attributes`, `extra_attributes`, equality or serialization and relied on the old collapsing, or that mutated a `get_asserted_types()` result in place, which no longer writes through. |
| [#77](https://github.com/trungdong/prov/issues/77) | `xsd:decimal` literals now compare and hash by value, not lexical form. `10` and `10.00` are now equal. | Recheck code relying on differently formatted decimals comparing unequal. |
| [#259](https://github.com/trungdong/prov/issues/259) | Language tags now compare and hash case-insensitively. Serialized output keeps the original casing. | Recheck code relying on differently cased tags comparing unequal. |
| [#228](https://github.com/trungdong/prov/issues/228) | Malformed PROV-JSON now raises `prov.serializers.provjson.ProvJSONException` instead of a raw `KeyError`, `AttributeError` or `TypeError`. | **Update exception handlers.** Catch `ProvJSONException` instead of the raw types around PROV-JSON deserialization. |
| [#273](https://github.com/trungdong/prov/issues/273) | PROV-XML parsing now uses a hardened parser. External DTD entities no longer resolve, and affected values come back empty instead of expanded. | If you need to detect rather than neutralise entity use, reject documents containing `<!DOCTYPE` before deserializing. |

The other fixes change what a serializer writes, or what a value decodes to, for inputs
that already worked, without changing their meaning; the 3.0.0 section of the changelog
lists each with its issue. Recheck any byte comparison of serialized output.

**Documented limitation, not a fix.** Two same-identifier relations that disagree on a
formal attribute still cannot round-trip through PROV-O, and decoding raises a chained error
([#217](https://github.com/trungdong/prov/issues/217); caveat C1 on
{doc}`reference/conformance`). Give such relations distinct identifiers if they must survive.

## `unified()` now enforces PROV-CONSTRAINTS

Before 3.0, `unified()` merged same-identifier records by unioning their attributes with no
conflict detection. 3.0 merges by [PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/)
term unification; {doc}`explanation/unification-flattening` has the full model. In short:

- **Two different concrete values for the same formal attribute raise
  `prov.model.ProvUnificationError`** instead of merging silently. A missing attribute
  still unifies with any concrete value.
- Records sharing an identifier but of **incompatible types**, such as an entity and an
  activity, raise the same error, naming both types. Overlaps the specification permits,
  such as an agent that is also an entity, merge as separate, per-type records.
- Each bundle unifies independently. Extra attributes keep their set-union behaviour.

`ProvUnificationError` subclasses `ProvException`, so an existing `except ProvException`
handler keeps working. Building and serializing a document with these conflicts is still
legal, because `prov` validates nothing at assertion or serialization time
([#257](https://github.com/trungdong/prov/issues/257)). **Action:** where same-identifier
records might disagree, catch `ProvUnificationError` around `unified()` and
`prov_to_graph()`, or fix the document.

(removed)=

## Removed

3.0 removes everything 2.4.0 marked deprecated. Nothing else is scheduled for removal.

- The unconditional `pydot` and `networkx` dependencies, superseded by the `dot` and
  `graph` extras; `import prov.dot` and `import prov.graph` raise `ModuleNotFoundError`.
- `python-dateutil` as a runtime dependency, and the incidental `prov.model.dateutil`
  re-export that came from importing it.
- `prov.model.GenrationRef`, the misspelled alias for the `generation` parameter of the
  derivation factories, renamed `GenerationRef` with no alias kept for the old spelling.

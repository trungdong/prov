# Upgrading to 3.0

## TL;DR

3.0 is the only release in the `prov` roadmap allowed to break compatibility. Every change
below was signposted in 2.4.0 with a runtime warning, so **if your test suite ran clean under
2.4.0 with `-W error::DeprecationWarning -W error::FutureWarning`, upgrading needs no code
changes.**

The two changes that matter for most users:

1. **`prov.dot` and `prov.graph` need extras now.** Install `prov[dot]` and/or `prov[graph]`
   if your code imports either module, or calls `prov_to_dot()`/`prov_to_graph()`/
   `graph_to_prov()`.
2. **`unified()` now raises instead of silently merging.** `ProvBundle.unified()`/
   `ProvDocument.unified()` raise `prov.model.ProvUnificationError` when records sharing an
   identifier disagree on a formal attribute or have incompatible types.
   `prov_to_dot()`/`prov_to_graph()` call `unified()` internally, so they can raise too.

Everything else is a set of narrow bug fixes (mostly affecting serializer output for edge
cases, listed below) and one renamed type alias. If neither change above applies to your code,
skip straight to [what's removed](#removed).

See [ROADMAP.md](https://github.com/trungdong/prov/blob/master/ROADMAP.md) for the
release-by-release plan and the
[modernisation roadmap design](https://github.com/trungdong/prov/blob/master/docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md)
for the full rationale.

## Install the extras you need

| If your code uses | Install |
|---|---|
| `prov.dot`, `prov_to_dot()` | `prov[dot]` |
| `prov.graph`, `prov_to_graph()`/`graph_to_prov()` | `prov[graph]` |
| `ProvBundle.plot()`/`ProvDocument.plot()`'s interactive display | `prov[dot]` (pulls in `graph` too) |

A plain `pip install prov` still gives you the core data model and the PROV-JSON/PROV-N/
PROV-JSONLD serializers with no extras. Extras combine, e.g. `pip install "prov[rdf,xml,dot,graph]"`.

## Dependency changes

- **`python-dateutil` is dropped** in favour of the standard library's
  `datetime.fromisoformat()`. Typical ISO-8601 timestamps are unaffected. Non-standard strings
  dateutil parsed permissively (e.g. `"Nov 7, 2011"`, or a bare `xsd:date` like
  `"2011-11-16"`) are no longer accepted; an unparseable `time=`/`startTime=`/`endTime=`
  factory argument now raises `prov.model.ProvException` instead of a raw `dateutil` error.
- **`rdflib` floor raised to 7.0.0.** Upgrade if you pin rdflib 6.x alongside `prov[rdf]`.
  Output differences are limited to those rdflib 7 already introduced under 2.x.

## Bug fixes that change output or equality

These fix real bugs, but each one changes output bytes or equality semantics for inputs that
work without error today — that's why they waited for 3.0 rather than shipping in 2.x. Skim
the "Action" column; most users are unaffected by most rows.

| Issue | What changed | Action |
|---|---|---|
| [#89](https://github.com/trungdong/prov/issues/89) | RDF no longer decorates a plain string value with `^^xsd:string`. | Only matters if you byte-compare RDF output — semantic equality is unaffected. |
| [#34](https://github.com/trungdong/prov/issues/34) | Attribute sets used to silently drop Python-equal-but-differently-typed values (e.g. `2`/`2.0`, `1`/`True`); all distinct values are now kept. `get_attribute()`/`get_asserted_types()`/`.value` keep their 2.x behaviour. | Recheck code that reads attributes via `attributes`/`extra_attributes`/equality/serialization and relied on the old collapsing, or that mutated a `get_asserted_types()` result in place (no longer writes through). |
| [#77](https://github.com/trungdong/prov/issues/77) | `xsd:decimal` literals now compare/hash by value, not lexical form (`10` and `10.00` are now equal). | Recheck code relying on differently-formatted decimals comparing unequal. |
| [#259](https://github.com/trungdong/prov/issues/259) | Language tags now compare/hash case-insensitively; serialized output keeps its original casing. | Recheck code relying on differently-cased tags comparing unequal. |
| [#168](https://github.com/trungdong/prov/issues/168) | PROV-JSON now emits `xsd:QName` (not the non-standard `prov:QUALIFIED_NAME`) for qualified-name values; both still decode. | Accept `xsd:QName` if you hand-parse this type yourself. |
| [#238](https://github.com/trungdong/prov/issues/238) | A `prov:QUALIFIED_NAME`-typed `Literal` now resolves to a `QualifiedName` on assertion, restoring round-trip equality. | Recheck code that inspected the raw `Literal` type. |
| [#235](https://github.com/trungdong/prov/issues/235)/[#249](https://github.com/trungdong/prov/issues/249)/[#251](https://github.com/trungdong/prov/issues/251) | A typed integer literal keeps its asserted datatype instead of silently re-typing to `xsd:int`; PROV-N types plain numbers by magnitude instead of truncating. | Recheck byte-comparisons of PROV-N output. |
| [#244](https://github.com/trungdong/prov/issues/244)/[#246](https://github.com/trungdong/prov/issues/246)/[#256](https://github.com/trungdong/prov/issues/256) | Plain ints are typed by magnitude (not always `xsd:int`) in JSON/XML/RDF output; PROV-JSON's typed-literal value is always a JSON string. | Recheck code that parses PROV-JSON's `$` as a JSON number. |
| [#218](https://github.com/trungdong/prov/issues/218)/[#225](https://github.com/trungdong/prov/issues/225) | RDF decoding preserves the original lexical form for datatypes Python can't losslessly round-trip; `xsd:double` values are emitted at full precision. | Recheck byte-comparisons of RDF/turtle output. |
| [#223](https://github.com/trungdong/prov/issues/223) | PROV-N now escapes metacharacters in identifiers and backslashes in string literals. | Recheck any hand-parsing of PROV-N output. |
| [#250](https://github.com/trungdong/prov/issues/250)/[#226](https://github.com/trungdong/prov/issues/226) | Anonymous qualified relations (Communication/Attribution/Delegation/Influence) now always carry their influencer property in PROV-O. | Recheck dedup logic keyed on the old (incomplete) triple shape. |
| [#258](https://github.com/trungdong/prov/issues/258) | `alternate()` now emits PROV-O in the correct (untransposed) subject/object order. | Only matters if you byte-compare output — `alternateOf` is symmetric, so semantic equality is unaffected. |
| [#288](https://github.com/trungdong/prov/issues/288) | `xsd:base64Binary` RDF values decode to their base64 text, not a Python bytes repr. | Recheck code that processes this attribute type. |
| [#299](https://github.com/trungdong/prov/issues/299) | A qualified Start/End node's binary `prov:startedAtTime`/`endedAtTime` predicate now populates the relation's formal `prov:time`, instead of landing as an extra attribute. | Recheck code reading the old extra attribute. |
| [#303](https://github.com/trungdong/prov/issues/303) | Anonymous Communication/Attribution/Influence relations with extra attributes no longer decode into two duplicate records. | None — this only fixes a round-trip bug. |
| [#294](https://github.com/trungdong/prov/issues/294) | A qualified name ending in a PROV-N metacharacter now round-trips through PROV-O instead of raising `ValueError`. | None — this only fixes a round-trip bug. |
| [#96](https://github.com/trungdong/prov/issues/96) | Bundle-local and default namespace prefixes are now bound in RDF output instead of falling back to an rdflib-minted prefix. | Recheck byte-comparisons of turtle/TriG prefixes. |
| [#217](https://github.com/trungdong/prov/issues/217) | **Documented limitation, not a fix:** two same-identifier relations that disagree on a formal attribute still can't round-trip through PROV-O. Decoding now raises a clear, chained error pointing at {doc}`reference/conformance` instead of a raw one. | Give such relations distinct identifiers if you need them to survive an RDF round trip. |
| [#224](https://github.com/trungdong/prov/issues/224) | Empty-string attribute values now survive a PROV-XML round trip (previously dropped). | None — this only fixes a round-trip bug. |
| [#289](https://github.com/trungdong/prov/issues/289) | An attribute name that isn't a legal XML NCName is now escaped instead of raising `ValueError`; see {doc}`reference/conformance` for the escaping rules. | None for already-legal names. Drop any workaround you had for the old `ValueError`. |
| [#228](https://github.com/trungdong/prov/issues/228) | Malformed PROV-JSON now raises `prov.serializers.provjson.ProvJSONException` instead of a raw `KeyError`/`AttributeError`/`TypeError`. | **Update exception handlers**: catch `ProvJSONException` instead of the raw types around PROV-JSON deserialization. |
| [#273](https://github.com/trungdong/prov/issues/273) | PROV-XML parsing now uses a hardened parser; external DTD entities no longer resolve (affected values come back empty instead of expanded). | If you need to *detect* rather than just neutralise entity use, reject documents containing `<!DOCTYPE` before deserializing. |

## `unified()` now enforces PROV-CONSTRAINTS

Before 3.0, `unified()` merged same-identifier records by unioning their attributes with no
conflict detection. 3.0 replaces this with real
[PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/) merging — see the
[unification and flattening explanation](explanation/unification-flattening.md) for the full
model. In short:

- Records sharing an identifier are merged by unifying formal attributes position-by-position.
  **Two different concrete values for the same formal attribute now raise
  `prov.model.ProvUnificationError`** instead of merging silently. A missing attribute still
  unifies with any concrete value, as before.
- Records sharing an identifier but of **incompatible types** (e.g. an entity and an activity)
  now raise the same error, naming both types, instead of merging into whichever record was
  asserted first. Overlaps the spec permits (e.g. an agent that's also an entity) still merge
  as separate, per-type records.
- Each bundle unifies independently — nothing merges across a bundle boundary.
- Non-formal ("extra") attributes still keep their set-union behaviour.
- Out of scope: uniqueness constraints not keyed on the record identifier (Constraints 24–29)
  belong to the separate, opt-in validation engine tracked as
  [#62](https://github.com/trungdong/prov/issues/62).

`ProvUnificationError` subclasses `ProvException`, so an existing `except ProvException`
handler around `unified()` keeps working. `prov_to_dot()` catches the error and falls back to
rendering the non-unified bundle; `prov_to_graph()` lets it propagate. Building and
serializing a document with these conflicts is still legal in 3.0 — `prov` performs no
structural validation at assertion/serialization time by design
([#257](https://github.com/trungdong/prov/issues/257)) — only calling `unified()` on one (or
decoding its RDF form) raises.

**Action:** if you call `unified()` — directly, or via `prov_to_dot()`/`prov_to_graph()` — on
documents where same-identifier records might disagree on a formal attribute or type, catch
`ProvUnificationError` or fix the document to avoid the conflict.

## Removed

3.0 removes everything 2.4.0 marked deprecated — nothing else is scheduled for removal:

- The unconditional `pydot`/`networkx` dependencies — superseded by the `dot`/`graph` extras
  above. `import prov.dot`/`import prov.graph` now raises `ModuleNotFoundError` naming the
  extra to install.
- `python-dateutil` as a runtime dependency, and the incidental `prov.model.dateutil`
  re-export that came from importing it.
- `prov.model.GenrationRef` — the misspelled type alias used in `wasDerivedFrom`/
  `wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource`'s `generation` parameter — is renamed
  `GenerationRef`, with no alias kept for the old spelling.

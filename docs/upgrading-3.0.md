# Upgrading to 3.0

3.0 is the one release in the `prov` roadmap allowed to break compatibility. Every
change below is signposted in 2.4.0 (with a runtime warning where that is feasible), so
most code that only sees a `DeprecationWarning`/`FutureWarning` today needs no change to
keep working right up until 3.0 ships; this page lists what to do for each planned
change. See [ROADMAP.md](https://github.com/trungdong/prov/blob/master/ROADMAP.md) for
the release-by-release plan and the
[modernisation roadmap design](https://github.com/trungdong/prov/blob/master/docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md)
for the full rationale.

## Smaller install footprint

| Change | Signposted in 2.4.0 by | What to do |
|---|---|---|
| **Done in 3.0.0.dev0:** `pydot`/Graphviz support (`prov.dot`, `prov_to_dot()`) moves behind the `dot` extra | Importing `prov.dot` emitted a `DeprecationWarning` (now removed) | Depend on `prov[dot]` instead of (or in addition to) `prov` if your code imports `prov.dot` or calls `prov_to_dot()`. |
| **Done in 3.0.0.dev0:** `networkx` graph interop (`prov.graph`, `prov_to_graph()`/`graph_to_prov()`) moves behind the `graph` extra | Importing `prov.graph` emitted a `DeprecationWarning` (now removed) | Depend on `prov[graph]` instead of (or in addition to) `prov` if your code imports `prov.graph` or calls `prov_to_graph()`/`graph_to_prov()`. Note `prov.dot` itself uses `prov.graph`, so `prov[dot]` pulls in `prov[graph]`'s dependency (`networkx`) too. |
| `python-dateutil` dropped in favour of the standard library's `datetime.fromisoformat()` ([#237](https://github.com/trungdong/prov/issues/237)) | Not separately warned (internal dependency swap) | No action for typical ISO-8601 timestamps. If you rely on `dateutil.parser.parse()`'s more permissive parsing of non-ISO date/time strings inside PROV-JSON/XML/RDF documents, verify those strings still parse under 3.0 — `fromisoformat()` accepts a narrower grammar; bare `xsd:date` strings (e.g. `"2011-11-16"`) and free-form strings like `"Nov 7, 2011"` are no longer accepted. Two behaviour fixes ride along with the swap: factory `time=`/`startTime=`/`endTime=` parameters now raise `prov.model.ProvException` for unparseable strings (previously a raw `dateutil.parser.ParserError` leaked out), and the valid `xsd:dateTime` hour-24 end-of-day lexical form (e.g. `"2011-11-16T24:00:00"`) is now accepted instead of rejected. |
| `rdf` extra floor raised to `rdflib>=7.0.0` | Not separately warned (dependency floor) | If you pin rdflib 6.x alongside `prov[rdf]`, upgrade to rdflib 7. Serialization differences are limited to those already present under rdflib 7 in 2.x (bundle-local namespaces appear as full IRIs in TriG; round-trip equality is unaffected). |

A plain `pip install prov` keeps working for the core data model and the JSON/PROV-N
serializers; add the relevant extra(s) if you use graphics export or graph interop. The
`plot` extra (`ProvBundle.plot()`/`ProvDocument.plot()`) also now carries `pydot` and
`networkx`, since its interactive-display path renders through `prov.dot`.

## Behaviour-changing bug fixes

These fix real bugs, but each one changes output or equality semantics for inputs that
work (without error) today, so none of them can land in the 2.x series under the
API-stability promise. No 2.4.0 runtime warning is feasible for these — the affected
code paths are ordinary attribute/literal handling with no single import or call site to
hook a warning onto — so this table is their only 2.4.0 signpost.

| Issue | Problem today | What changes in 3.0 | What to do |
|---|---|---|---|
| [#89](https://github.com/trungdong/prov/issues/89) | A literal parsed with an explicit `^^xsd:string` datatype and a plain (datatype-less) literal are both stored as a bare `str`, so the original form isn't recoverable on re-serialization, and the RDF/PROV-JSON serializers disagree on which form to emit. | Serializers emit one consistent canonical form for string literals: the plain, undecorated form. RDF output no longer decorates a plain string attribute value with `^^xsd:string`; PROV-JSON was already undecorated. | If you compare serialized RDF output byte-for-byte, re-check it against 3.0 output. Document-level (semantic) equality is unaffected: RDF 1.1 treats a plain literal and an `xsd:string`-typed one as the same value, so deserializing either still yields the same `str`. |
| [#34](https://github.com/trungdong/prov/issues/34) | Extra attribute values are stored in a plain Python `set`, so Python-equal-but-differently-typed values (e.g. `2` and `2.0`, or `1` and `True`) silently collapse to whichever was inserted first — both at record construction and inside `unified()`. | Attribute values gain type-aware (value-space) handling as part of the PROV-CONSTRAINTS unification rework (see below), so distinct PROV values are retained instead of colliding. | If your code depends on same-value-different-type attributes collapsing (or on which of the colliding values survives), re-check it against 3.0; most callers will simply see more attributes preserved. |
| [#77](https://github.com/trungdong/prov/issues/77) | `Literal` stores its value as a string and compares/hashes lexically, so `Literal(10, XSD_DECIMAL)` and `Literal(10.0, XSD_DECIMAL)` compare unequal despite denoting the same `xsd:decimal` value. | `xsd:decimal` literals compare and hash in value space (via Python's `decimal.Decimal`), so `Literal(10, XSD_DECIMAL)`, `Literal(10.0, XSD_DECIMAL)` and `Literal("10.00", XSD_DECIMAL)` are now equal and deduplicate in attribute sets; the literal itself is unchanged (still a `Literal`, not converted to a native `Decimal`). | If you rely on lexical (string) inequality between differently-formatted decimal literals denoting the same value, re-check that code against 3.0. |
| [#259](https://github.com/trungdong/prov/issues/259) | `Literal` language tags compare/hash case-sensitively, so `Literal("hello", langtag="EN")` and `Literal("hello", langtag="en")` compare unequal even though RDF 1.1 language tags are case-insensitive. | Language tags compare and hash case-insensitively; the stored tag itself is left untouched, so serialized output still carries its original case verbatim. | If you rely on differently-cased language tags comparing unequal, re-check that code against 3.0. Serialized output is unaffected. |
| [#168](https://github.com/trungdong/prov/issues/168) | PROV-JSON encodes `QualifiedName` attribute values with the non-standard `prov:QUALIFIED_NAME` type instead of the `xsd:QName` type the PROV-JSON submission specifies. | PROV-JSON emits `{"$": ..., "type": "xsd:QName"}` for `QualifiedName` values; `prov:QUALIFIED_NAME`-typed values in input documents (2.x output, or hand-written) still decode correctly. | If you consume PROV-JSON produced by `prov` and parse the `"type"` of qualified-name attributes yourself, accept `xsd:QName` as well as (or instead of) `prov:QUALIFIED_NAME`. |
| [#238](https://github.com/trungdong/prov/issues/238) | A `Literal` explicitly typed `prov:QUALIFIED_NAME` (for example one decoded from a `prov:QUALIFIED_NAME`-typed PROV-JSON value) is kept as an opaque `Literal` rather than resolved to a `QualifiedName`, so a document built from one and a document round-tripped through PROV-JSON compare unequal. | Asserting a `prov:QUALIFIED_NAME`-typed `Literal` on a record resolves it to a `QualifiedName` using that record's in-scope namespaces, restoring round-trip equality; if the value's prefix has no in-scope namespace it is left as an opaque `Literal` rather than rejected. | If your code inspects the type of an attribute value asserted from a `prov:QUALIFIED_NAME`-typed `Literal`, expect a `QualifiedName` instead where the prefix resolves. |
| [#235](https://github.com/trungdong/prov/issues/235), [#249](https://github.com/trungdong/prov/issues/249), [#251](https://github.com/trungdong/prov/issues/251) | `Literal("42", XSD_LONG)` is silently re-typed `xsd:int` at assertion time; PROV-N renders out-of-`int32` plain ints as bare (invalid) `INT_LITERAL`s and plain floats as `%g`-truncated `xsd:float`. | A typed `Literal` keeps its asserted datatype unless collapsing it to a plain Python value would be lossless; PROV-N types plain ints by magnitude (`xsd:int`/`xsd:long`/`xsd:integer`) and plain floats as full-precision `xsd:double`. | If you byte-compare PROV-N output or relied on an asserted `xsd:long`/`xsd:integer` literal mutating to `xsd:int`, re-check it against 3.0; the underlying document values are unchanged. |
| [#244](https://github.com/trungdong/prov/issues/244), [#246](https://github.com/trungdong/prov/issues/246), [#256](https://github.com/trungdong/prov/issues/256) | PROV-JSON, PROV-XML, and PROV-O always tag a plain Python `int` as `xsd:int` regardless of magnitude, producing schema-invalid output for out-of-`int32` values; PROV-JSON also puts the raw `int`/`float` value straight into the typed-literal `$` property instead of a string, which is schema-invalid per the submission. | Plain ints are typed by magnitude (`xsd:int`/`xsd:long`/`xsd:integer`) across all three serializers, and PROV-JSON's `$` is always a JSON string for typed literals. | If you parse PROV-JSON `$` as a JSON number, or assume every plain int is tagged `xsd:int` in PROV-JSON/PROV-XML/PROV-O output, re-check that code against 3.0. |
| [#218](https://github.com/trungdong/prov/issues/218), [#225](https://github.com/trungdong/prov/issues/225) | PROV-O (RDF) decoding rebuilds a typed `Literal` from rdflib's Python-coerced value, so datatypes without a lossless Python collapse (`xsd:decimal`, `xsd:unsignedInt`, `xsd:positiveInteger`, and similar XSD numeric subtypes) can lose their asserted datatype/lexical form on decode; separately, a plain Python `float` (`xsd:double`) is abbreviated by rdflib's Turtle/TriG writer to ~7 significant digits, so a full-precision value comes back changed. | RDF decoding reconstructs a `Literal` from the RDF term's own lexical form for datatypes without a lossless collapse, so the asserted datatype and lexical form survive; `xsd:double` values are emitted with an explicit datatype tag at full `repr()` precision instead of rdflib's abbreviated bare-literal form. | If you byte-compare PROV-O (RDF) output, expect `xsd:double` values to appear as quoted, explicitly-datatyped literals (e.g. `"0.1"^^xsd:double`) instead of the bare abbreviated form; document-level (semantic) equality and round-trip fidelity both improve. |

## Unification rework (PROV-CONSTRAINTS)

`ProvBundle.unified()` and `ProvDocument.unified()` currently perform a simple,
identifier-keyed attribute union: for each identifier shared by more than one record,
the attributes of all such records are merged onto a copy of the first, with no
conflict detection. See the
[unification and flattening explanation](explanation/unification-flattening.md) for the
full write-up of today's behaviour and how it diverges from the specification.

In 3.0, `unified()` is reimplemented to follow the merging rules of
[W3C PROV-CONSTRAINTS](https://www.w3.org/TR/prov-constraints/) (key constraints and
term unification). Concretely:

- Calling `unified()` today already emits a `FutureWarning` naming this page and
  ROADMAP.md.
- Records sharing an identifier that also have **conflicting formal attributes** will
  **raise a documented exception** in 3.0 instead of having their attributes silently
  unioned.
- The `#34` attribute-merging fix above lands as part of this same rework.

**What to do:** if your code calls `unified()` on documents where records sharing an
identifier can disagree on a formal attribute (for example, two `wasGeneratedBy`
statements for the same identifier asserting different `prov:time` values — the
"scruffy" pattern used in this repo's own test suite), expect that call to raise in 3.0
where it previously merged silently. Catch the new exception (or restructure the
document to avoid conflicting formal attributes) before upgrading. Documents without
this pattern are unaffected.

Note that `prov_to_dot()` (`prov.dot`) and `prov_to_graph()` (`prov.graph`, not
`graph_to_prov()`, which does not unify) call `unified()` internally, so the
`FutureWarning` above also fires on every call to those functions today — regardless of
whether the document actually has conflicting attributes — so graphics/graph-export
users will see it even without calling `unified()` themselves.

## Removal of names deprecated in 2.4.0

3.0 removes everything 2.4.0 marked deprecated:

- The unconditional `pydot`/`networkx` dependencies (superseded by the `dot`/`graph`
  extras above) — `import prov.dot` / `import prov.graph` will raise
  `ModuleNotFoundError` if the corresponding extra isn't installed, rather than working
  out of the box.
- `python-dateutil` as a runtime dependency (superseded by the stdlib swap above), along
  with the incidental `prov.model.dateutil` module re-export that came from importing it
  there.

There are no other 2.4.0-introduced deprecations beyond these two extras moves; nothing
else is scheduled for removal.

## Summary: is my code affected?

If your code:

- Doesn't import `prov.dot`/`prov.graph` (or their `prov_to_dot`/`prov_to_graph`/
  `graph_to_prov` re-exports elsewhere) — unaffected by the extras moves.
- Doesn't compare `xsd:decimal` literals across differing lexical forms, doesn't rely on
  same-value-different-type attribute collapsing, doesn't byte-compare serialized string
  literals, doesn't parse the `"type"` of PROV-JSON qualified-name attribute values, and
  doesn't inspect the type of an attribute value asserted from a `prov:QUALIFIED_NAME`-typed
  `Literal` — unaffected by the bug fixes.
- Doesn't call `unified()` on documents with conflicting formal attributes sharing an
  identifier — unaffected by the unification rework.

then upgrading to 3.0 should require no code changes at all. Where a runtime warning is
feasible (the two extras moves and `unified()`), 2.4.0 already emits it under
`-W error::DeprecationWarning` / `-W error::FutureWarning`, so you can audit your own
call sites for these changes ahead of time.

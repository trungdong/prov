# History

## 3.1.0 (2026-08-07)

- New PROV-JSONLD serializer and deserializer, selected with `format="jsonld"`
  (`src/prov/serializers/provjsonld.py`): implements the W3C member submission
  ["A JSON-LD Representation for the PROV Data Model"](https://www.w3.org/submissions/prov-jsonld/),
  the canonical §4 compacted shape only, with no runtime dependency beyond the
  standard library. Registered in `prov.serializers.Registry` and included in
  `prov.read()`'s format auto-detection. See
  [Work with PROV-JSONLD](https://github.com/trungdong/prov/blob/master/docs/howto/provjsonld.md)
- `serialize(format="jsonld", ...)` takes a `context` keyword: `"url"` (the
  default) references the submission's context by URL; `"embed"` inlines the
  vendored context object for fully self-contained output; any other value
  raises `ValueError`
- The deserializer additionally tolerates ProvToolbox's `prov:`-prefixed
  spellings of the type and special terms, and is exercised against both the
  submission's own example and a vendored ProvToolbox fixture
  (`src/prov/tests/jsonld/`)
- `jsonld` joins `json`/`xml`/`rdf` in the shared round-trip test matrix
  (`SHARED_TARGETS` in `src/prov/tests/conftest.py`); output is additionally
  validated against the submission's vendored JSON Schema
  (`context="url"` mode only — the schema's `Context` production cannot
  describe an embedded context) and, for `context="embed"`, proven valid
  JSON-LD via `pyld` expansion
- **Known limitation:** the PROV-JSONLD submission defines no term for
  `mentionOf` (PROV-DM's Mention relation); `serialize()` raises
  `prov.serializers.provjsonld.ProvJSONLDException` for any document
  containing a `ProvMention` record, and the deserializer raises the same
  exception on an input statement typed `"Mention"`. This is a permanent
  limitation of the submission, not a `prov` defect — see
  `docs/reference/conformance.md`

## 3.0.0 (2026-07-27)

3.0.0 is the compatibility release: the one release the roadmap allows to
change behaviour and drop dependencies, closing out the standards-conformance
work (PROV-DM, PROV-CONSTRAINTS, PROV-O) that a backward-compatible 2.x series
could not fix. See
[Upgrading to 3.0](https://github.com/trungdong/prov/blob/master/docs/upgrading-3.0.md)
for what changed and what to do about it.

### Breaking changes

- `ProvBundle.unified()` / `ProvDocument.unified()` implement
  PROV-CONSTRAINTS key constraints (22/23) with pairwise term unification of
  formal attributes: records sharing an identifier whose formal attributes
  hold different concrete values now raise the new documented
  `prov.model.ProvUnificationError` instead of silently unioning; absent
  formal attributes unify with concrete values; extra attributes keep
  set-union semantics; bundles unify independently (#253)
- `unified()` rejects same-identifier records of incompatible types
  (entity vs activity, distinct relation kinds — PROV-CONSTRAINTS 53/54/55)
  with `ProvUnificationError` instead of merging them order-dependently
  into the first record's type; spec-permitted overlaps (an agent that is
  also an entity or activity) are kept as separate records (#253)
- Attribute values that are Python-equal but differently typed (`2` vs
  `2.0`, `1` vs `True`) are all retained on a record instead of
  collapsing to whichever was asserted first — visible in attribute
  iteration, record equality and hashing, and serialization. Attributes now
  iterate in assertion order rather than an arbitrary hash order, which makes
  `args`, `formal_attributes`, `get_startTime()` and `get_endTime()`
  deterministic. `ProvRecord.get_attribute()`, `get_asserted_types()` and
  the `value` property still return a plain `set`, but it is now built
  fresh on every call, so mutating it no longer writes through to the record:
  `record.get_asserted_types().add(qn)` now silently does nothing (#34)
- `pydot` and `networkx` are no longer unconditional runtime
  dependencies. `import prov.dot` now requires the `dot` extra
  (`pip install "prov[dot]"`) and `import prov.graph` the `graph`
  extra; without them the import raises `ModuleNotFoundError` naming the
  extra to install. The `plot` extra now pulls in `pydot`/`networkx`
  as well, since `plot()` renders through `prov.dot`. See
  `docs/upgrading-3.0.md`.
- The `rdf` extra now requires `rdflib>=7.0.0` (previously `>=6.0.0`);
  round-trip behaviour is unchanged
- `python-dateutil` dropped — `prov` now has no unconditional
  runtime dependencies. Datetime strings are parsed as `xsd:dateTime`
  (ISO 8601 plus the hour-24 end-of-day form) via the standard library;
  factory `time=`/`startTime=`/`endTime=` parameters raise
  `ProvException` on invalid input instead of leaking a raw dateutil
  error, and non-ISO forms previously tolerated by dateutil (e.g.
  `"Nov 7, 2011"`) are no longer accepted (#237)
- The misspelled `prov.model.GenrationRef` type alias is renamed
  `GenerationRef`; the old spelling is removed rather than kept as a
  deprecated alias

### Conformance and correctness fixes

- When an attribute is asserted twice with an equal value of equal type — e.g.
  `Literal("10", XSD_DECIMAL)` and `Literal("10.00", XSD_DECIMAL)` (#77),
  or `Literal("hi", langtag="en")` and `Literal("hi", langtag="EN")`
  (#259) — the record retains the first value asserted, as in 2.x (#34)
- Numeric datatype fidelity: `Literal` values typed `xsd:long` (and the
  rest of the XSD integer family) keep their asserted datatype instead of
  being silently re-typed `xsd:int` (#235); PROV-N output types plain
  integers by magnitude (`xsd:int`/`xsd:long`/`xsd:integer`) so
  out-of-int32 values are no longer emitted as invalid bare int literals
  (#249), and plain floats as full-precision `xsd:double` instead of
  `%g`-truncated `xsd:float` (#251)
- Literal semantics: string literals have one canonical serialized form (RDF
  output no longer decorates plain strings with `^^xsd:string`) (#89);
  `xsd:decimal` literals compare and hash in value space (#77); language
  tags compare case-insensitively per RDF 1.1 while preserving their
  original case in output (#259)
- PROV-XML round trip preserves attributes whose value is the empty string;
  previously they were silently dropped on deserialization (#224)
- PROV-XML serializes attribute names containing characters illegal in an
  XML NCName using the reversible `_xHHHH_` escaping convention instead
  of raising `ValueError`; the deserializer applies the inverse, so such
  names round-trip (#289)
- The PROV-JSON deserializer raises `ProvJSONException` on structurally
  malformed input instead of leaking raw `KeyError`/`AttributeError`
  (#228)
- PROV-JSON typed literals always encode `$` as a string, and plain
  integers are typed by magnitude across PROV-JSON/PROV-XML/PROV-O output
  (`xsd:int`/`xsd:long`/`xsd:integer`), fixing schema-invalid output
  for out-of-int32 values (#244, #246, #256)
- PROV-JSON encodes QualifiedName attribute values as `xsd:QName` typed
  literals per the PROV-JSON submission (previously the non-standard
  `prov:QUALIFIED_NAME`, which remains accepted on input) (#168), and
  `prov:QUALIFIED_NAME`-typed `Literal` values are resolved to
  QualifiedNames at assertion time, restoring round-trip equality (#238)
- PROV-O: documents containing multiple same-identifier relations with
  differing formal attributes ("scruffy" statements) are documented as a
  PROV-O representational limitation — they serialize but do not round-trip
  through RDF, and deserializing such RDF now raises an error naming the
  limitation; all other formats are unaffected (#217)
- PROV-O: a related gap is recorded, not fixed — an attribute key whose local
  part ends in a PROV-N metacharacter (#223) can fail to round-trip through
  RDF when its namespace has not already been registered by another qualified
  name; `docs/reference/conformance.md` documents it as an open defect
  (#341)
- PROV-O (RDF) round-trip fidelity: mixed XSD-datatype attribute sets
  survive deserialization with their asserted datatypes intact (#218), and
  `xsd:double` values are emitted at full precision instead of rdflib's
  6-significant-digit canonical form (#225)
- PROV-O output: anonymous qualified Communication/Attribution/Delegation/
  Influence nodes now carry their influencer property (`prov:activity`/
  `prov:agent`/`prov:agent`/`prov:influencer`) as the PROV-O
  qualification tables require, and the RDF round trip no longer collapses
  distinct anonymous delegations sharing a (delegate, activity) pair
  (#250, #226)
- PROV-O output emits `alternateOf` with the PROV-DM argument order
  (`alt1 prov:alternateOf alt2`); previously subject and object were
  transposed on both write and read (#258)
- PROV-O (RDF) deserialization returns `xsd:base64Binary` literals as
  their base64 text; previously the value was wrapped in a Python bytes
  repr (`b'…'`), corrupting the round trip (#288)
- PROV-O (RDF) deserialization reconciles `prov:startedAtTime`/
  `prov:endedAtTime` asserted directly on a qualified `prov:Start`/
  `prov:End` node into the relation's formal `prov:time` attribute;
  previously the formal attribute was left `None` and the value misfiled as
  an extra attribute (#299)
- PROV-O (RDF) round trip: an anonymous Communication/Attribution/Influence
  relation carrying extra attributes now deserializes back into a single
  record instead of two (#303)
- PROV-O (RDF) round trip: a qualified name whose local part ends in a PROV-N
  metacharacter (`= ' , : ; [ ]`) now deserializes instead of raising
  `ValueError: Can't split ...`; serialized output is unchanged (#294)
- PROV-N output escapes qualified-name local parts per the grammar's
  `PN_CHARS_ESC` production, so identifiers containing `' ( ) , : ; [ ]
  =` no longer produce invalid PROV-N (#223)
- PROV-N continues to emit Mention as bare `mentionOf(...)` — the
  de-facto syntax of the reference implementations for the last decade —
  rather than the `prov:mentionOf` form derivable from the PROV-Links
  note; now documented as a deliberate deviation (#248)

### Improvements

- Bundle-local and default namespace prefixes are now bound into RDF
  serialization alongside document-level ones, so turtle/TriG output uses
  the declared prefixes instead of auto-minted `ns1:`-style fallbacks
  (#96)
- Security: PROV-XML parsing no longer resolves DTD entities and never
  touches the network (`resolve_entities=False`, `no_network=True`),
  closing an XXE surface on untrusted input (#273)
- New public type aliases in `prov.model`, joining the existing
  `NameValuePair`: `AttributePair` (an attribute name/value pair before
  qualified-name resolution), `InfluencerRef` (the `influencer` parameter
  of `wasInfluencedBy()` and `influence()`) and `StreamOrPath` (the
  source and destination parameters of `read()`, `serialize()` and
  `deserialize()`)

### Internal

- The PROV-O (RDF) serializer's encode/decode container functions were
  decomposed into per-record-type dispatch, with byte-identical output (#274)
- Functions across the model, the serializers and `prov.dot` were refactored
  below the project's complexity threshold, with byte-identical behaviour
  (#275)
- Code-quality passes across `src/prov/` — type-alias adoption, removal of a
  permanently-disabled branch in the PROV-O (RDF) encoder, and readability
  clean-ups — with no change in behaviour
- Test infrastructure: the RDF fixture-comparison helper `find_diff()` now
  detects single-triple differences, which it previously missed (#304)

## 2.5.1 (2026-07-13)

- `prov.read()` polish following 2.5.0's #239: seekable streams are now
  rewound between auto-detection attempts (so e.g. a PROV-XML stream
  auto-detects instead of being consumed by the first candidate); rdflib's
  "does not look like a valid URI" logger noise from swallowed candidate
  attempts is suppressed during auto-detection; and when a `str`/`bytes`
  source that is not an existing file path fails to parse, the error now
  carries a hint that it was treated as raw content
- Documentation: the PROV-XML and PROV-JSON how-to pages no longer describe
  the pre-2.5.0 `read()` auto-detection behaviour (exception whitelist,
  "XML never auto-detects")

## 2.5.0 (2026-07-13)

- New record-level chaining convenience methods (#154):
  `ProvEntity.wasRevisionOf()`, `.wasQuotedFrom()`, `.hadPrimarySource()`,
  `.mentionOf()`, and `.wasInfluencedBy()` on `ProvEntity`,
  `ProvActivity` and `ProvAgent` — mirroring the existing
  `e1.wasDerivedFrom(e2)` style for the remaining relation types
- The PROV-XML deserializer now raises `ProvXMLException` when a record's
  child element carries only unrecognised XML attributes, instead of leaking a
  raw `UnboundLocalError` or silently reusing the previous attribute's value
  (#254)
- `ProvDocument.serialize()` and `deserialize()` now accept any writable/
  readable file-like object (e.g. `tempfile.NamedTemporaryFile`), instead of
  only `io.IOBase` instances; previously such destinations were silently
  treated as file paths, writing to a repr-named file in the working
  directory. The serializers' text/binary stream detection now also
  recognises such wrapper objects as text streams (#240)
- `prov.read()` fixes (#239): valid PROV-XML is now auto-detected (the RDF
  parser's `BadSyntax` no longer aborts detection); a `str`/`bytes`
  source that is not an existing file path is parsed as raw content, as the
  documentation always advertised; and input that no deserializer can
  meaningfully parse (e.g. an empty file) now raises `TypeError` instead of
  silently returning an empty document
- Documentation: the agent-subtype idiom now correctly uses qualified names
  (`PROV["Person"]`) for `prov:type` values; the previously documented
  string form asserted a plain string, which does not denote the pre-defined
  PROV type (#236)

## 2.4.0 (2026-07-06)

- **Documentation overhaul**: the documentation has been reorganised along the
  Diátaxis framework (tutorials, how-to guides, reference, explanations), with
  new furo/MyST/napoleon/intersphinx tooling behind the Sphinx build. Closes
  #141 (graphics export how-to) and #83 (`prov-convert`/`prov-compare` CLI
  tools how-to). (#210, #211, #212, #213, #214, #215, #216)
- **Test suite redesigned as pytest-native**: shared statement/attribute/qname
  coverage is now expressed once and parametrized across a document x format
  matrix (json/xml/rdf/model) instead of being copy-pasted per serializer;
  Hypothesis property-based round-trip tests generate documents across the
  full feature set; a malformed-input corpus exercises each deserializer's
  error handling. (#219, #220, #221, #222, #227, #229)
- **`prov.model` split into a package** (`prov.model.records`,
  `prov.model.namespaces`, `prov.model.bundle`) for maintainability, with
  no import-path changes: every historic `from prov.model import X` still
  works identically. (#231)
- Minor Makefile/CLAUDE.md cleanup for contributors. (#209)
- The serializer registry now degrades gracefully when the optional `rdf`
  (`rdflib`) or `xml` (`lxml`) extra is not installed: `import prov`
  and the JSON/PROV-N serializers work in a minimal install, and requesting
  the `rdf`/`xml` format raises an informative `DoNotExist` naming the
  missing extra instead of a bare `ModuleNotFoundError`. (#230)
- Deprecation warnings signposting planned 3.0 changes: importing
  `prov.dot`/`prov.graph` now emits a `DeprecationWarning` naming the
  future `prov[dot]`/`prov[graph]` extras those modules will require, and
  `ProvBundle.unified()`/`ProvDocument.unified()` emit a `FutureWarning`
  about the upcoming PROV-CONSTRAINTS unification rework. Both warnings are
  hidden by default (standard `DeprecationWarning`/`FutureWarning`
  semantics) and link to the new
  [Upgrading to 3.0](https://github.com/trungdong/prov/blob/master/docs/upgrading-3.0.md)
  guide, which tables every planned 3.0 change and what to do about it.

## 2.3.0 (2026-07-05)

- **Dropped Python 3.9 support; minimum is now Python 3.10** (security fixes
  in transitive dependencies are only released for Python 3.10+) (#189)
- **Widened `rdflib` to `>=6.0.0,<8`** (was `>=4.2.1,<7`): rdflib 7 now
  supported; the floor rose because 4.2.1 no longer installs on supported
  Pythons (#207)
- Diagnostic improvement: `DoNotExist` (serializer lookup) and the CLI's
  `CLIError` now set `__cause__` via exception chaining, so tracebacks
  show the original error; exception types and messages are unchanged, so
  existing `except` blocks are unaffected (#200)
- Whole package passes `mypy --strict`; ships a `py.typed` marker
  (PEP 561) so downstream type-checkers see inline types (#192, #193, #194)
- Coverage raised to 97%, enforced in CI; new tests for the CLI scripts,
  `prov.read()` auto-detection, graph interop, and the serializer
  registry (#201, #202, #203, #204)
- Internal code quality: ruff rule families I/C4/SIM/RUF/UP045/UP031 enabled
  and long-standing lint suppressions resolved (#195, #196, #197, #198,
  #199, #200); dependency audit documented in `docs/dependencies.md`; tox
  removed (use `uv run --python 3.X pytest` for local multi-version
  testing) (#205)
- Security hygiene: `SECURITY.md`, Dependabot version updates, and a
  documented support policy (#190)
- Fixed ReadTheDocs build (Sphinx pinned `<9`) (#187)

## 2.2.0 (2026-07-03)

- Fixed graphical output when a filename is supplied (#164)
- Fixed PROV-XML deserialization when prov is the default namespace (#155)
- New `plot` extra: `pip install prov[plot]` for matplotlib support (#166)
- Marked as Production/Stable; added Python 3.14 to the test matrix
- Tooling: ruff (lint+format), pytest runner, uv-based CI, automated PyPI
  releases via Trusted Publishing. No public API changes.

## 2.1.1 (2025-06-24)

- No change - fixing the previous botched release

## 2.1.0 (2025-06-24)

- Added type annotations and mypy checks
- Added support for Python 3.13

## 2.0.2 (2025-06-07)

- Removed support for EOL Python 3.8
- Using pyproject.toml for project configurations (instead of setup.py)

## 2.0.1 (2024-06-10)

- Removed support for EOL Python 3.6 and 3.7
- Minor documentation update (#153)
- Stopped using deepcopy when duplicating Namespace (#158)
- Restricting rdflib package version to "<7" (#156)
- Raise an exception when an empty URI is registered as a namespace (#142)
- Ensure rdflib 6+ returns bytes when serializing tests (fixed #151)
- Removed fancy label output for bundle

## 2.0.0 (2020-11-01)

- Removed support for EOL Python 2
- Testing against Python 3.6+ and Pypy3

## Earlier releases

Releases before 2.0.0 are recorded in the
[changelog archive](https://github.com/trungdong/prov/blob/master/docs/changelog-archive.md).

# Conformance audit findings — Phase 3.5 (roadmap steps 28–32)

**Status:** Complete. Phase 3.5 closed 2026-07-11: the triage in section 6 was approved at
the maintainer checkpoint on 2026-07-11 and applied on GitHub the same day (milestones and
labels set, follow-up issues #256–#261 filed, phase summary posted on
[#181](https://github.com/trungdong/prov/issues/181)).
**Triage:** Section 6 records the approved classification (step 31).

## 0. Baseline (recorded before any audit work)

- Test suite tally: `932 passed, 16 skipped, 6 xfailed, 95 warnings in 8.09s` (`uv run pytest`,
  2026-07-10, branch `audit/conformance-matrix` at the tip of `master`
  (c195be7)). The 95 warnings are pytest's own capture-warnings summary of `UserWarning`s
  intentionally raised by `provrdf.py:692` inside three existing tests
  (`test_json_to_ttl_match`, `test_membership_{1,2,3}[rdf]`, plus the parametrized statement
  tests) — pre-existing, unrelated to this task, not touched.
- ruff: `uv run ruff check src/` → `All checks passed!`
- mypy: `uv run mypy src` → `Success: no issues found in 17 source files`
- sphinx: `uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html`
  → `build succeeded.` (0 warnings)

## 1. Conformance matrix findings (step 28)

Findings surfaced while building `docs/reference/conformance.md`, verified against source:

- **No dedicated factories for the PROV-DM agent subtypes** (`Person`, `Organization`,
  `SoftwareAgent`, PROV-DM §5.3.1). `ProvBundle.agent()` (`src/prov/model/bundle.py:812`)
  creates a plain `prov:Agent`; the subtype must be added by hand via
  `other_attributes={PROV_TYPE: "prov:Person"}` (or equivalent). This is already documented as
  intentional in `docs/explanation/prov-dm.md:111-114`, and `ADDITIONAL_N_MAP`
  (`src/prov/constants.py:75-84`) does carry PROV-N keywords for all three
  (`person`/`organization`/`softwareAgent`) plus `plan`, so the vocabulary constants exist —
  only the convenience factories are missing. Feature gap, not a defect; candidate for 3.0
  triage (new small factories, or leave as documented `prov:type` idiom).
- **No dedicated factory for `EmptyCollection`** (PROV-DM §5.6). `PROV["EmptyCollection"]` is a
  real constant with a PROV-N keyword (`ADDITIONAL_N_MAP`, `src/prov/constants.py:83`) and a
  `PROV_BASE_CLS` entry mapping it to `PROV_ENTITY` (`src/prov/constants.py:120`), so the
  round-trip machinery understands the type — but `ProvBundle.collection()`
  (`src/prov/model/bundle.py:1221`) has no `empty=` flag or sibling `empty_collection()` method.
  Same shape as the agent-subtype gap above: vocabulary present, convenience factory absent.
  Feature gap, candidate for 3.0 triage.
- **`prov:Bundle` as a first-class entity type (PROV-DM §5.4.2) is not implemented at all** —
  not even as a documented `prov:type` idiom. `PROV_BUNDLE` (`src/prov/constants.py:42`) exists
  as a QualifiedName constant with a PROV-N keyword mapping (`"bundle"`,
  `src/prov/constants.py:69`) and a `PROV_BASE_CLS` entry, but grepping the full source tree
  shows it is consumed only by `src/prov/dot.py` (node styling for the `folder` shape) and is
  never referenced by any serializer (`provjson.py`, `provxml.py`, `provrdf.py`, `provn.py`) or
  by any `ProvBundle`/`ProvDocument` method. `ProvBundle.get_provn()`
  (`src/prov/model/bundle.py:315-350`) emits the PROV-N `bundle <id> ... endBundle` block
  structurally (via `is_document()`/`is_bundle()` branching), not through a `prov:Bundle`-typed
  record and not through the `PROV_N_MAP["bundle"]` keyword — that keyword is present in the
  lookup table but is dead code as far as the current model/serializer implementation goes. In
  other words: `prov` implements bundle *containment* (§5.4.1, `ProvDocument.bundle()` /
  `add_bundle()`) but not the PROV-DM notion of a bundle's identifier also denoting an entity of
  type `prov:Bundle` for provenance-of-provenance assertions (§5.4.2) — a user cannot currently
  attribute a bundle to an agent or otherwise make first-class PROV statements about the bundle
  itself as an entity, because there is no supported path from `ProvBundle.identifier` to a
  `ProvEntity` typed `prov:Bundle` in the same document. Feature gap (and worth flagging the
  unused `PROV_N_MAP` entry as very minor dead-weight); candidate for 3.0 triage.
- **Issue #154 re-read**: title is "Add convenient assertion methods for revision, quotation,
  primary source, mention & influence records". The bundle-level factories it mentions in
  passing (`revision()`, `quotation()`, `primary_source()`, `mention()`, `influence()`) **all
  already exist** on `ProvBundle` (`src/prov/model/bundle.py:1011,1056,1101,1194,935`) with
  camelCase aliases (`wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource`/`mentionOf`/
  `wasInfluencedBy`, `bundle.py:1358-1364`) — but that was never what the issue was asking for.
  Its actual ask is **record-level (`ProvElement`) chaining methods**, the pattern demonstrated
  by the issue's own example, `e1.wasDerivedFrom(e2)`. Checked `records.py` directly:
  `ProvEntity` (`records.py:763-900`) already has `wasGeneratedBy`, `wasInvalidatedBy`,
  `wasDerivedFrom`, `wasAttributedTo`, `alternateOf`, `specializationOf`, `hadMember` as
  self-as-first-argument convenience methods that delegate to `self._bundle.<factory>(self,
  ...)` and return `self` for chaining — but genuinely lacks `wasRevisionOf`, `wasQuotedFrom`,
  `hadPrimarySource`, and `mentionOf`. Likewise `ProvActivity` (`records.py:900-1057`) has
  `used`, `wasInformedBy`, `wasStartedBy`, `wasEndedBy`, `wasAssociatedWith` but lacks
  `wasInfluencedBy`, and `ProvAgent` (`records.py:1131-1163`) has only `actedOnBehalfOf` and
  also lacks `wasInfluencedBy`. So issue #154's five requested methods are **all still
  missing**, exactly as filed: `ProvEntity.wasRevisionOf`, `ProvEntity.wasQuotedFrom`,
  `ProvEntity.hadPrimarySource`, `ProvEntity.mentionOf`, and `wasInfluencedBy` on all three of
  `ProvEntity`/`ProvActivity`/`ProvAgent`. Still open, valid, and narrowly scoped; recommend
  keeping it open and triaging in step 31 as a 2.x-safe additive feature (same shape as the
  agent-subtype/EmptyCollection gaps above — purely additive, no output/behaviour change to
  existing methods).
- **PROV-N metacharacter escaping (#223) applies generically**, not to one row: any concept
  whose identifier's local part contains a PROV-N metacharacter (`'`, `)`, `,`, `(`, `:`, `;`,
  `[`, `]`, `=`) produces invalid PROV-N text regardless of record type, because the bug is in
  `QualifiedName.provn_representation()` (`src/prov/identifier.py`), shared by every record. The
  matrix notes this once under the PROV-N column header rather than repeating it per row.
- **Round-trip skip/xfail counts reconciled exactly against the baseline** (`uv run pytest -q
  -rs -rx`): the `16 skipped` = 14 rdf-target "scruffy" skips in `test_statements.py` (2 each of
  generation/invalidation/usage, 4 each of start/end — `RDF_SCRUFFY_SKIP`, #217) + 2 unrelated
  `test_minimal_install.py` skips that are an artefact of running with both extras installed
  (`test_rdf_unavailable_raises_informative_error` / `test_xml_unavailable_raises_informative_error`
  skip themselves when `rdflib`/`lxml` *are* present — expected, not a conformance finding). The
  `6 xfailed` = 3 in `test_attributes.py` (`test_entity_with_one_type_attribute_decimal` for
  #77, `test_entity_with_multiple_attribute` and `test_entity_with_multiple_value_attribute` for
  #218) + 3 regression-guard xfails in `test_rdf.py`/`test_xml.py`
  (`test_float_precision_survives_rdf_roundtrip` #225,
  `test_qualified_delegation_pair_survives_rdf_roundtrip` #226,
  `test_empty_string_attribute_survives_xml_roundtrip` #224) — i.e. every one of #77/#217/#218/
  #224/#225/#226 has a live characterization test in the suite already; #223 (PROV-N escaping)
  has no dedicated xfail because PROV-N has no parser to round-trip through.
- **`prov:Bundle` PROV-N keyword row aside**: since `PROV_N_MAP["bundle"]` is unused by the
  actual `get_provn()` implementation (see above), the conformance matrix's PROV-N column for
  the "Bundle constructor" row describes the real, hand-written `bundle <id> ... endBundle`
  output rather than citing a keyword lookup.

## 2. Formal attributes & PROV-DM §5 semantics (step 29)

Audited 2026-07-10 on branch `audit/prov-dm-section5` against
[PROV-DM (W3C REC 2013-04-30)](https://www.w3.org/TR/prov-dm/) §5. Method: the spec's
per-concept attribute lists were extracted verbatim as the baseline (condensed in §2.0
below), then compared against `FORMAL_ATTRIBUTES` in `src/prov/model/records.py`, the
`ProvBundle` factory signatures in `src/prov/model/bundle.py`, and the datatype machinery
(`parse_xsd_types` / `Literal` / `_auto_literal_conversion` in `records.py`). Every
non-conformance claim below was confirmed by an executed reproduction (snippets inline).
Known issues #34/#77/#89/#96/#154/#168/#217/#218/#223–#228 are used as anchors and not
re-reported.

### 2.0 Baseline: `FORMAL_ATTRIBUTES` vs the spec's attribute lists

Spec signature (id omitted; `*` = spec-optional) vs the class tuple:

| Record type | PROV-DM signature | `FORMAL_ATTRIBUTES` (`records.py`) | Order/content match |
|---|---|---|---|
| Entity §5.1.1 | id only | `()` | yes |
| Activity §5.1.2 | st\*, et\* | `(startTime, endTime)` | yes |
| Generation §5.1.3 | e, a\*, t\* | `(entity, activity, time)` | yes |
| Usage §5.1.4 | a, e\*, t\* | `(activity, entity, time)` | yes |
| Communication §5.1.5 | informed, informant | `(informed, informant)` | yes |
| Start §5.1.6 | a, trigger\*, starter\*, t\* | `(activity, trigger, starter, time)` | yes |
| End §5.1.7 | a, trigger\*, ender\*, t\* | `(activity, trigger, ender, time)` | yes |
| Invalidation §5.1.8 | e, a\*, t\* | `(entity, activity, time)` | yes |
| Derivation §5.2.1 | e2, e1, a\*, g2\*, u1\* | `(generatedEntity, usedEntity, activity, generation, usage)` | yes |
| Agent §5.3.1 | id only | `()` | yes |
| Attribution §5.3.2 | e, ag | `(entity, agent)` | yes |
| Association §5.3.3 | a, ag\*, pl\* | `(activity, agent, plan)` | yes |
| Delegation §5.3.4 | ag2, ag1, a\* | `(delegate, responsible, activity)` | yes |
| Influence §5.3.5 | o2, o1 | `(influencee, influencer)` | yes |
| Specialization §5.5.1 | infra, supra (no id/attrs) | `(specificEntity, generalEntity)` | yes |
| Alternate §5.5.2 | e1, e2 (no id/attrs) | `(alternate1, alternate2)` | yes |
| Membership §5.6.2 | c, e (no id/attrs) | `(collection, entity)` | yes |
| Mention (PROV-Links) | infra, supra, b | `(specificEntity, generalEntity, bundle)` | yes (see §2.5) |

All 18 tuples match the spec's attribute list and order exactly. The
QName-vs-literal partition is also correct: `PROV_ATTRIBUTE_LITERALS`
(`constants.py:182`) contains exactly the three `xsd:dateTime`-typed formals
(`time`, `startTime`, `endTime`); every other formal is in `PROV_ATTRIBUTE_QNAMES`,
matching the spec (all non-time formals are identifiers).

### 2.1 §5.1 Entities and Activities

- **Entity**: mandatory id enforced (`ProvElementIdentifierRequired`, `records.py:735-737`);
  attributes optional. Conformant.
- **Activity**: `activity(identifier, startTime=None, endTime=None, ...)` — both times
  optional, order (st, et) matches. Times are validated as `datetime` (strings parsed);
  a non-datetime raises `ProvException` on the `add_attributes` path. Two time-handling
  findings, both in the shared `_ensure_datetime` helper (`records.py:103-112`) used by
  *every* factory `time=`/`startTime=`/`endTime=` parameter — see §2.7.3 (filed as #237).
- **Generation / Usage / Invalidation**: formal attributes, order, and optionality of the
  factory signatures (`generation(entity, activity=None, time=None, ...)` etc.,
  `bundle.py:588,625,744`) all match. The spec's "at least one of id, activity, time,
  attributes MUST be present" rule is not enforced — `d.generation("ex:e1")` produces
  `wasGeneratedBy(ex:e1, -, -)` silently (executed; see §2.8 validation-gap family).
- **Communication**: both formals required by the factory, matching the spec. Conformant.
- **Start / End**: 4-tuple incl. starter/ender matches; factory optionality
  (`start(activity, trigger=None, starter=None, time=None, ...)`) matches the spec's
  markers (only `activity` mandatory). "At least one MUST be present" unenforced (§2.8).

**Verdict:** Entity, Activity, Generation, Usage, Communication, Start, End,
Invalidation — **conformant** on attributes/order/optionality; findings limited to the
cross-cutting items in §2.7.3 (time datatype handling, #237) and §2.8 (unenforced
"at-least-one" rules, needs maintainer confirmation).

### 2.2 §5.2 Derivations

- **Derivation**: 5-tuple and factory optionality match (`derivation(generatedEntity,
  usedEntity, activity=None, generation=None, usage=None, ...)`, `bundle.py:968`). The
  library permits `generation`/`usage` without `activity`
  (`d.derivation("ex:e2", "ex:e1", None, "ex:g2", "ex:u1")` →
  `wasDerivedFrom(ex:e2, ex:e1, -, ex:g2, ex:u1)`, executed) — PROV-DM §5.2.1 marks each
  individually optional (the grammar allows `-` per slot), so this is grammatically fine;
  the combination rule ("for a generation/usage to be given, the activity must be") lives
  in PROV-CONSTRAINTS 51, which is out of scope (#62 backlog). Recorded in §2.8, no issue.
- **Revision / Quotation / PrimarySource** (§5.2.2–5.2.4): defined by the spec as
  `prov:type`-subtyped derivations with no extra attributes; implemented exactly that way
  (`revision()`/`quotation()`/`primary_source()` add `PROV["Revision"]` etc. via
  `add_asserted_type`, `bundle.py:1044-1146`). The typed-`wasDerivedFrom` PROV-N rendering
  is already recorded in section 1; not repeated.

**Verdict:** Derivation (incl. Revision/Quotation/PrimarySource) — **conformant**;
PROV-CONSTRAINTS-level combination rule intentionally unenforced (§2.8 note).

### 2.3 §5.3 Agents, Responsibility, and Influence

- **Agent**: mandatory id enforced; attributes accepted. Conformant. (Missing
  Person/Organization/SoftwareAgent factories already recorded in section 1.)
- **Attribution**: `(entity, agent)` both mandatory in factory — matches spec. Conformant.
- **Association**: `association(activity, agent=None, plan=None, ...)` — spec marks agent
  and plan optional; matches. Conformant.
- **Delegation**: `delegation(delegate, responsible, activity=None, ...)` — matches spec
  (ag2, ag1, a\*). Conformant.
- **Influence**: `(influencee, influencer)` both mandatory; matches. The spec's
  influencee/influencer correspondence table (§5.3.5) is informational for queries and
  needs no model support.
- **NEW finding (filed #236)** — §5.3.1 says the agent subtype "is expressed using the
  prov:type attribute" whose pre-defined values (§5.7.2.4 table) are *qualified names*
  (`prov:Person` etc.). The library's documented idiom — `agent("ag", {prov.PROV_TYPE:
  "prov:Person"})` in `docs/explanation/prov-dm.md:114`, `docs/tutorial/getting-started.md:52`,
  `docs/reference/conformance.md:97` — passes a plain *string*, which the model stores
  unchanged (strings are never coerced to QualifiedNames, correctly so). The resulting
  record asserts the string `"prov:Person"`, not the type `prov:Person`. Executed:
  ```
  d.agent("ex:derek", {"prov:type": "prov:Person"})   # documented idiom
  # PROV-N: agent(ex:derek, [prov:type="prov:Person"])   <- string, not 'prov:Person'
  # RDF:    ex:derek a prov:Agent, "prov:Person"^^xsd:string .   <- literal as a class!
  d.agent("ex:derek", {"prov:type": PROV["Person"]})  # correct form
  # PROV-N: agent(ex:derek, [prov:type='prov:Person'])
  # RDF:    ex:derek a prov:Agent, prov:Person .
  # the two documents compare UNEQUAL
  ```
  The same string idiom appears in the library's own canonical examples
  (`src/prov/tests/examples.py:266`, `{"prov:type": "prov:Plan"}`). The model behaviour is
  conformant (a string is a legal `prov:type` value per §5.7.2.4); the defect is that the
  documentation and examples teach the string form as *the* way to denote the pre-defined
  subtypes, silently producing records that do not carry the subtype. Docs/examples fix,
  2.x-safe.

**Verdict:** Agent, Attribution, Association, Delegation, Influence — **conformant** at the
model level; **finding listed** (documentation idiom, #236).

### 2.4 §5.4 Bundles

Bundle containment (§5.4.1) is implemented structurally (`ProvDocument.bundle()` /
`add_bundle()`; named bundles only at document level, nesting refused at runtime), matching
the constructor definition. The §5.4.2 `prov:Bundle` entity-type gap (no supported path from
a bundle identifier to a `prov:Bundle`-typed entity for provenance-of-provenance) is already
recorded in full in section 1 and is not repeated here.

**Verdict:** Bundle constructor — **conformant**; Bundle type (§5.4.2) — **finding already
recorded in section 1** (feature gap, 3.0 triage).

### 2.5 §5.5 Alternate Entities

- **Specialization / Alternate**: 2-tuples match; the public factories
  (`specialization()`, `alternate()`, `bundle.py:1148,1172`) correctly accept *neither an
  identifier nor attributes*, matching the spec's explicit "is not ... an influence, and
  therefore does not have an id and attributes". The low-level escape hatch does not
  enforce this: `d.new_record(PROV_SPECIALIZATION, "ex:spec1", {...}, {"ex:note": "extra"})`
  produces `specializationOf(ex:spec1; ex:e2, ex:e1, [ex:note="extra"])` (executed) — text
  that is not derivable from the PROV-N grammar. Requires deliberate misuse of the
  low-level API (or non-conformant serialized input); recorded in §2.8, no issue.
- **Mention**: `ProvMention` (`mentionOf(infra, supra, b)`, 3-tuple, no id/attrs) is **not
  part of PROV-DM §5** — it was dropped from the REC (marked at-risk) and lives in the
  W3C PROV-Links Note. Implementing it is a conformant *extension*; the tuple matches
  PROV-Links' definition (specific, general, bundle, all mandatory in the factory).
  Documentation could label it as PROV-Links rather than PROV-DM; cosmetic, no issue.

**Verdict:** Specialization, Alternate — **conformant** (public API); Mention —
**conformant extension** (PROV-Links, not §5). Low-level `new_record` permissiveness noted
in §2.8.

### 2.6 §5.6 Collections

- **Collection**: `collection()` creates an entity typed `prov:Collection` — matches
  §5.6.1's type-based definition. (`EmptyCollection` factory gap already in section 1.)
- **Membership**: `hadMember(c, e)` — both formals mandatory in `membership()`, no
  id/attrs on the public factory; matches §5.6.2 including its "not an influence" clause
  (same `new_record` caveat as §2.5, see §2.8).

**Verdict:** Collection, Membership — **conformant**.

### 2.7 §5.7 Further elements (values, qualified names, namespace declarations)

#### 2.7.1 Identifier (§5.7.1)

Elements: mandatory id, enforced. Relations: optional id, supported. The spec's equality
rule ("two generations are equal if they have the same identifier") is *stricter* in the
library: `ProvRecord.__eq__` (`records.py:650-658`) also requires equal attribute sets, so
two same-id records with different extra attributes compare unequal (executed). This is the
unification/merging domain — deferred to step 30b (`2026-07-10-unification-gap-analysis.md`),
not re-audited here.

#### 2.7.2 Reserved attributes (§5.7.2)

- `prov:label` "MUST be a string" (§5.7.2.1): not validated — `{PROV_LABEL: 42}` is
  accepted and rendered `prov:label=42` (executed). §2.8 family.
- Multiple `prov:label`s incl. language-tagged (spec example 47): supported;
  `[prov:label="Voiture 01"@fr, prov:label="Car 01"@en]` round-trips through JSON
  (executed). Conformant.
- `prov:location`/`prov:role` "allowed in" lists: the model deliberately does not restrict
  which record types carry which reserved attributes (permissive; consistent with not
  validating). No finding beyond the §2.8 family note.
- `prov:type` (§5.7.2.4): multiple values supported (set-valued); pre-defined type
  constants all exist. String-vs-QualifiedName value distinction is honoured (a string
  stays a string) — the *documentation* defect around this is #236 (§2.3).
- `prov:value` "MAY occur at most once" (§5.7.2.5): not enforced —
  `e = d.entity("ex:e1", {PROV_VALUE: 1}); e.add_attributes({PROV_VALUE: 2})` yields
  `entity(ex:e1, [prov:value=1, prov:value=2])` (executed). The cardinality guard in
  `add_attributes` (`records.py:622-626`) covers only formal attributes
  (`PROV_ATTRIBUTES`), which `prov:value` is not. §2.8 family.

#### 2.7.3 Value / datatypes (§5.7.3)

Anchors: #89 (typed vs untyped literal indistinguishable), #77 (`xsd:decimal` Literal
comparison), #218/#225 (RDF fidelity), #168 (QName typing in PROV-JSON). New siblings found:

- **`xsd:long` literals silently re-typed as `xsd:int` (filed #235).**
  `XSD_DATATYPE_PARSERS` (`records.py:160-168`) maps both `XSD_LONG` and `XSD_INT` to
  Python `int`, so `_auto_literal_conversion` collapses an asserted `xsd:long` literal to a
  bare `int` at `add_attributes` time; every serializer then emits its reverse-map default
  `xsd:int` (`provjson.py:69-74`, `provrdf.py:90ff`). Executed:
  ```
  e = d.entity("ex:e1", {"ex:attr": Literal("42", XSD_LONG)})
  e.extra_attributes  ->  ((ex:attr, 42),)          # datatype gone at assertion time
  JSON: {"ex:attr": {"$": 42, "type": "xsd:int"}}
  RDF:  ex:attr "42"^^xsd:int .    XML: <ex:attr xsi:type="xsd:int">42</ex:attr>
  ```
  The asserted datatype is mutated in all serializations. Note the inconsistency inside
  the XSD integer family: `xsd:integer`, `xsd:short`, `xsd:byte`, `xsd:decimal`,
  unsigned/negative variants have *no* parser, remain opaque `Literal`s, and therefore
  round-trip faithfully (executed for `xsd:integer`/`xsd:decimal`) — only the two parsed
  types (`xsd:long`, `xsd:int`) lose their identity. Root-cause sibling of #89.
- **`prov:QUALIFIED_NAME`-typed literals are not resolved to QualifiedNames, breaking
  round-trip equality (filed #238).** §5.7.3 defines `"ex:value" %% prov:QUALIFIED_NAME`
  and `'ex:value'` as the *same* value. The model stores
  `Literal("ex:v", PROV_QUALIFIEDNAME)` opaquely (no parser), so it compares unequal to
  `QualifiedName(ex, "v")`; the PROV-JSON *decoder* however resolves the type on input, so
  the value mutates across a round trip and `deserialize(serialize(d)) != d`. Executed:
  ```
  d:  entity(ex:e1, [ex:a="ex:v" %% prov:QUALIFIED_NAME])
  JSON: {"ex:a": {"$": "ex:v", "type": "prov:QUALIFIED_NAME"}}
  back: entity(ex:e1, [ex:a='ex:v'])     # now a QualifiedName; back != d
  ```
  Sibling of #89 (same abstract value, two unequal representations); intersects #168.
  By contrast `xsd:QName`-typed literals stay opaque in both directions and round-trip
  stably (executed) — the #168 debate about which type PROV-JSON *should* emit is
  unchanged.
- **`xsd:anyURI`**: parsed to `Identifier` and round-trips through JSON intact (executed).
  Conformant.
- **`xsd:boolean`**: `parse_boolean` accepts exactly the XSD lexical space
  (`true/false/1/0`) and rejects others (stays a `Literal`). Conformant.
- **Time instants (`xsd:dateTime`) — filed #237.** Two defects in the factory time path
  (`_ensure_datetime`, `records.py:103-112`, used by every `time=`/`startTime=`/`endTime=`
  parameter):
  1. Unparseable strings leak a raw `dateutil.parser.ParserError` instead of the
     `ProvException` the equivalent `add_attributes` path raises (executed:
     `d.activity("ex:a1", startTime="not a date")` → `ParserError`; setting
     `PROV_ATTR_STARTTIME` via `add_attributes` → `ProvException`). Same shape as #228's
     raw-exception leak, in the model API.
  2. The valid xsd:dateTime hour-24 lexical form is rejected via that same raw error:
     `startTime="2011-11-16T24:00:00"` → `ParserError: hour must be in 0..23` (executed),
     though XSD Datatypes permits `24:00:00` (midnight end-of-day).
  Timezone handling is otherwise sound: offsets and `Z` parse to aware datetimes, an
  aware `prov:time` round-trips through JSON preserving the offset (executed), and naive
  vs aware values are simply distinct values (matching XSD's partial ordering).
  dateutil's *leniency* (accepting non-XSD forms like `"Nov 7, 2011"`) is documented API
  behaviour ("a string parseable by dateutil.parser.parse") — noted, not a defect.
- **Language-tagged strings**: `Literal(v, langtag=...)` forces
  `prov:InternationalizedString` (matching the PROV-JSON/XML rules), JSON round-trip
  preserves tag and value; RDF round-trip preserves the tag verbatim (`"hello"@EN` stays
  `@EN`, executed). One value-space nit: RDF 1.1 defines language tags as
  case-insensitive (lowercase-normalised in the value space), while `Literal.__eq__`
  compares tags case-sensitively — `Literal("hello", langtag="EN") !=
  Literal("hello", langtag="en")` (executed). Distinct-representation sibling of the #89
  family; cosmetic in practice because the library never normalises tags anywhere, so
  values survive round trips unchanged. Recorded here; **needs maintainer confirmation**
  whether 3.0 should normalise (no issue filed).

#### 2.7.4 Namespace declarations (§5.7.4)

Prefixed declarations, the default namespace (`set_default_namespace`; unprefixed name
resolved against it and round-trips through JSON, executed), and the PROV namespace IRI
(`http://www.w3.org/ns/prov#`, `constants.py:19`) are all conformant.

#### 2.7.5 Qualified names (§5.7.5)

IRI mapping is the required concatenation (`Namespace("ex", "http://example.org/")["foo"]
.uri == "http://example.org/foo"`, executed). Prefix optionality is handled via the default
namespace. Output-side escaping of metacharacters in local parts is #223 (already filed,
applies generically — see section 1); input-side the library accepts arbitrary local parts,
which is the permissive half of the same coin and needs no separate issue.

**Verdict §5.7:** Identifier, namespace declarations, qualified names — **conformant**
(modulo #223, already filed). Attributes — **findings listed** (#236 docs idiom; §2.8
validation family for label/value cardinality). Values/datatypes — **findings listed**
(#235 xsd:long mutation, #237 dateTime handling, #238 prov:QUALIFIED_NAME resolution;
langtag case-sensitivity needs maintainer confirmation).

### 2.8 Cross-cutting: unenforced PROV-DM structural constraints (needs maintainer confirmation)

The model is deliberately permissive — it asserts what it is given and defers validity to
PROV-CONSTRAINTS tooling (#62, backlog). The §5 audit collected every point where that
permissiveness lets *normative PROV-DM (not PROV-CONSTRAINTS)* rules be violated silently,
so the 3.0 triage can decide once, coherently, whether any should warn/raise:

1. Mandatory formal attributes can be omitted: `None` values are skipped by
   `add_attributes` (`records.py:574-576`), so `d.generation(None)` →
   `wasGeneratedBy(-, -, -)` and `d.communication(None, None)` → `wasInformedBy(-, -)`
   (executed) — output not derivable from the PROV-N grammar (which requires the entity /
   both activity identifiers). Reachable only by violating the factory type hints or from
   non-conformant serialized input.
2. "At least one of id/…/attributes MUST be present" (Generation §5.1.3, Usage §5.1.4,
   Start §5.1.6, End §5.1.7, Invalidation §5.1.8, Association §5.3.3): unenforced
   (`d.generation("ex:e1")` → `wasGeneratedBy(ex:e1, -, -)`, executed — grammatically
   valid, normatively incomplete).
3. `prov:value` cardinality (§5.7.2.5) and `prov:label` string-ness (§5.7.2.1): unenforced
   (§2.7.2, executed).
4. Id/attributes accepted on Specialization/Alternate/Membership via low-level
   `new_record` (§2.5, executed) — the public factories are correct.
5. Derivation generation/usage without activity: allowed (PROV-CONSTRAINTS 51 territory,
   §2.2).

Items 1–4 are normative-DM deviations; item 5 is CONSTRAINTS-only. **No issues filed** —
enforcement anywhere here is a behaviour change (2.x-frozen) and whether 3.0 wants
validation, warnings, or the status quo is an API-philosophy decision for the maintainer
(step 31 triage). Characterization tests pinning the current behaviour of items 1–3 are in
`src/prov/tests/test_conformance_dm.py`; items 4–5 are documented here only (they require
deliberate misuse of the low-level `new_record` API or CONSTRAINTS-level analysis, so
issue-body repros and scope notes suffice).

**Triage pointer:** Additional "needs maintainer confirmation" items appear in §2.7.3
(language-tag case-sensitivity for RDF round-trips).

### 2.9 Bugs found en route (not §5 conformance, filed separately)

- **`prov.read()` cannot auto-detect valid PROV-XML (filed #239)** — the Phase-3 loose
  end, confirmed: format detection tries `json → rdf → provn → xml`
  (`src/prov/__init__.py:62-68` catches only
  `TypeError/ValueError/AttributeError/KeyError`), and the RDF deserializer raises
  `rdflib...BadSyntax` — a `SyntaxError` subclass — on PROV-XML input, which propagates
  before the XML deserializer is ever tried (executed: `prov.read(path_to_valid_xml)` →
  `BadSyntax`). Two adjacent modes recorded in the issue: an *empty* source yields a
  silent empty document (rdflib parses empty trig successfully), and a raw content
  *string* — which `read()`'s docstring advertises — raises `FileNotFoundError` because a
  `str` source is always treated as a path (`bundle.py:1686-1691`).
- **`ProvDocument.serialize()` writes to a repr-named junk file (filed #240)** — the
  stream test is `isinstance(destination, IOBase)` (`bundle.py:1626`), which is false for
  common file-likes such as `tempfile.NamedTemporaryFile` (a `_TemporaryFileWrapper`
  proxy); such destinations fall into the file-path branch and the serialization lands in
  a file literally named e.g. `<tempfile._TemporaryFileWrapper object at 0x1052cc170>` in
  the CWD, while the intended file stays empty (executed and observed). On Python 3.14+
  the manifestation changes: `NamedTemporaryFile.__repr__` now embeds the full file path
  (including `/` characters), so the repr-derived `open()` raises `FileNotFoundError`
  instead of silently writing the junk file — same defect, different symptom.

### 2.10 Verification (step 29)

`src/prov/tests/test_conformance_dm.py` adds 6 strict xfails (one per filed defect that is
reproducible in a few lines: #235, #237 ×2, #238, #239, #240) and 4 characterization tests
pinning the §2.8 permissive behaviour. Tally moves from the section-0 baseline
`932 passed, 16 skipped, 6 xfailed` to `936 passed, 16 skipped, 12 xfailed`
(`uv run pytest`, 2026-07-10); ruff check/format, mypy (strict), and the Sphinx docs build
all remain clean.

## 3. Serializer mappings (step 30)
### 3.1 PROV-XML vs XSD

**Method:** vendored the W3C PROV-XML schema closure offline
(`src/prov/tests/schemas/prov.xsd` + `prov-core.xsd` + `prov-dictionary.xsd` +
`prov-links.xsd` + `xml.xsd`; provenance and licence note in
`src/prov/tests/schemas/README.md`) and added
`src/prov/tests/test_xml_schema.py`, which compiles the schema with
`lxml.etree.XMLSchema` and validates the serialized XML of all 8
`examples.tests` documents plus one document per entry of the
`ATTRIBUTE_VALUES` corpus (28 entries, each asserted as a `prov:type` value —
mirroring `test_attributes.py`'s convention) — 36 validation params total.

**Result:** 32 pass; 4 do not. All 4 were triaged individually; none share a
root cause:

1. **`W3C Publication 1` — schema/spec limitation, skipped, not filed.** The
   example (ported from the ProvToolbox test corpus) asserts the identifier
   `chairs:2011OctDec/0004`. PROV-XML types `prov:id`/`prov:ref` as
   `xsd:QName`, whose local part must be a valid NCName (no `/`), which is
   stricter than PROV-N's QualifiedName (arbitrary local-name characters).
   The PROV-XML spec itself documents this gap ("valid identifier values in
   PROV-N serializations have [the] potential to not be valid identifier
   values in PROV-XML", <https://www.w3.org/TR/prov-xml/>) and recommends —
   but does not require — identifier schemes that avoid it. No PROV-XML
   implementation could serialize this identifier validly; not a defect in
   this library. Documented skip in `test_xml_schema.py`
   (`QNAME_LOCAL_PART_SKIP`).
2. **`datatypes` — bug, filed #244, strict xfail.** The example asserts the
   plain Python int `123456789000` (`ex:long`). `provxml.py`'s xsd-type
   inference (`serializers/provxml.py:221-226`) maps every plain `int` to
   `XSD_INT` unconditionally, with no magnitude check, so a value outside the
   `xsd:int` range (±2^31-1) serializes as `<ex:long
   xsi:type="xsd:int">123456789000</ex:long>` — schema-invalid on its own,
   no round trip needed to observe it. Root-cause sibling of #235 (`xsd:long`
   Literals silently re-typed `xsd:int` on ingestion) but a distinct
   manifestation: this needs no explicit `XSD_LONG` annotation at all, and
   the result is invalid XML rather than merely lossy. Any fix changes
   serialized output, so it's 3.0 material under the 2.x output freeze.
   Strict xfail in `test_xml_schema.py` (`INT_MAGNITUDE_XFAIL`,
   `raises=AssertionError`).
3. **`ATTRIBUTE_VALUES[1]`/`[2]` (`Literal("un lieu", langtag="fr")` /
   `Literal("a place", langtag="en")` on `prov:type`) — schema/spec
   limitation, skipped, not filed.** `prov-core.xsd` gives only `prov:label`
   the `prov:InternationalizedString` complex type (string + optional
   `xml:lang`); `prov:type`/`prov:role`/`prov:location`/`prov:value` are all
   plain `xs:anySimpleType`, which does not permit an `xml:lang` attribute at
   all. PROV-DM permits language-tagged values on any attribute, but
   PROV-XML — by schema design — can only represent a language tag on
   `prov:label`. Not something this library's serializer could fix by
   changing how it writes `prov:type`; a genuine expressiveness gap in the
   PROV-XML format itself. Documented skip in `test_xml_schema.py`
   (`LANG_TAG_ON_NON_LABEL_SKIP`), one instance per affected index.

Not already covered by #224 (empty-string attributes dropped by PROV-XML) or
any other previously-filed issue — checked before filing #244.

Package data (`pyproject.toml` `[tool.setuptools.package-data]`,
`"prov.tests"` list) gained `"schemas/*"` so the vendored schema closure
ships in the sdist.

**Verdict:** PROV-XML output is schema-valid except: (a) identifiers whose
local part is not a valid XML NCName, which is an inherent PROV-XML format
limitation (not fixable, not filed); (b) language-tagged values on
attributes other than `prov:label`, also an inherent PROV-XML format
limitation (not fixable, not filed); and (c) plain Python integers outside
the 32-bit `xsd:int` range, which is a genuine defect in this library's XML
type-inference heuristic (filed #244, deferred to 3.0 under the output
freeze).

### 3.2 PROV-JSON vs member submission

**Method:** fetched *A JSON Representation for the PROV Data Model*
(<https://www.w3.org/submissions/prov-json/>, the 2013 W3C Member
Submission), vendored the JSON schema linked from its §2.3 ("Validating
PROV-JSON Documents", <https://www.w3.org/submissions/prov-json/schema>) as
`src/prov/tests/schemas/prov-json.schema.json` (provenance/quirks noted in
that directory's README.md), and audited `src/prov/serializers/provjson.py`
against the submission's §2 (overview: container shape, JSON data typing,
identifiers) and §3 (per-construct mappings: elements §3.1, relations §3.2,
bundles §3.3) sections in turn.

**Schema-draft path taken: the test-module path (not the manual-audit
fallback).** The schema declares `"$schema":
"http://json-schema.org/draft-04/schema#"`; `jsonschema` 4.x still ships
`Draft4Validator`, and `jsonschema.validators.validator_for(schema)` picks it
correctly, so `src/prov/tests/test_json_schema.py` validates all 8
`examples.tests` documents' `format="json"` output against the schema
directly (no upgrade/rewrite of the schema needed).

**Result:** 5 of 8 pass; 3 do not, all one root cause (filed #246, below).

#### 3.2.1 Structural encoding (§2 overview, §3.1–§3.2 one-section-per-record-type)

Compared the container shape built by `encode_json_container`
(`provjson.py:207-277`) against §2's worked skeleton (one top-level property
per PROV-N keyword, indexed by record identifier, plus `prefix`) and against
every one of §3.1's three element mappings (Entity, Agent, Activity) and
§3.2's fourteen relation mappings (Generation through Membership): the
mapping from `PROV_N_MAP` record-type keyword to top-level JSON property
matches every one of the submission's worked examples exactly, and every
formal-attribute name inside a record object (`prov:entity`, `prov:agent`,
`prov:generatedEntity`, etc.) matches `PROV_ATTRIBUTES`/§3.2's per-relation
attribute lists one-for-one, executed against each §3.2.*n* example
individually. Blank-node identifiers (§2.1) are minted via
`AnonymousIDGenerator` (`provjson.py:41-65`) for any record without an
explicit identifier; the submission requires the Turtle `nodeID` production
(`_:name`) — `AnonymousIDGenerator` emits `_:id<n>`, which matches. Multiple
relation instances sharing an identifier are collated into a JSON array
(`provjson.py:263-275`) — a documented `prov` extension beyond what the
submission itself specifies for that case, but consistent with §2.2's
"properties with multiple values" collation rule for attribute values, and
harmless (the schema's `additionalProperties` for each relation type has no
`type` constraint requiring a single object).

**Verdict:** structural encoding — **conformant**.

#### 3.2.2 `$`/`type` value-encoding rules (§2.2 "JSON Data Typing")

Anchors: **#89** (internal representation cannot distinguish a literal with
an explicit datatype from one without — same root cause surfaces here as
`encode_json_representation`/`decode_json_representation`'s asymmetry) and
**#168** (`prov:type='prov:Person'`, a `QualifiedName` value, is encoded as
`{"$": "prov:Person", "type": "prov:QUALIFIED_NAME"}` —
`encode_json_representation`, `provjson.py:427-430` — where every one of the
submission's own worked examples, e.g. §3.1.2, §3.2.7–3.2.9, §3.3, encodes
the identical construct as `{"$": ..., "type": "xsd:QName"}`). Both remain
open, unchanged by this audit; not re-reported.

Executed against the vendored schema's `definitions.typedLiteral` (`$`
required, `string`-typed; `type` optional, `string`-typed; `lang` optional,
`string`-typed; no other properties):

- **`prov:label`/plain strings/booleans**: emitted as native JSON
  string/boolean per §2.2's "MAY be represented using the JSON native data
  types" allowance — conformant, matches every worked example.
- **Language-tagged strings**: `literal_json_representation`
  (`provjson.py:476-491`) omits `type` and sets `lang` when a `Literal` has a
  language tag — matches §2.2's rule ("the `type` property omitted") and its
  worked example (`{"$": "Londres", "lang": "fr"}`) exactly.
- **`xsd:anyURI`/`xsd:dateTime`/other typed `Literal`s**: `$` is always
  `str`-typed (`.isoformat()` for datetime, `value.uri`/`literal.value`
  otherwise) — conformant.
- **NEW finding (filed #246) — plain Python `int`/`float` attribute values
  encode a non-string `$`.** `encode_json_representation`'s
  `LITERAL_XSDTYPE_MAP` branch (`provjson.py:433-434`) is the *only* branch
  of that function that does not stringify its value: `return {"$": value,
  "type": LITERAL_XSDTYPE_MAP[type(value)]}` passes the raw Python
  `int`/`float` straight through. Executed:
  ```
  d.entity("ex:e1", {"ex:count": 100})
  # JSON: {"ex:count": {"$": 100, "type": "xsd:int"}}   <- $ is a JSON number
  ```
  This violates both the submission's prose (§2.2: "The value of a literal is
  stored in the object's special property `$`, represented as a string") and
  its schema's `typedLiteral.$: {"type": "string"}`. Reproduced by 3 of the 8
  `examples.tests` documents — `Bundle1`/`Bundle2` (`ex:version=<int>` inside
  a nested bundle's entity) and `datatypes` (`ex:int`, `ex:float`, `ex:long`)
  — each a schema-validation failure in `test_json_schema.py`, strict-xfailed
  there. Note the submission's own worked examples (e.g. §3.3 Bundles) encode
  the *identical* construct — a bare untyped `ex:version=1`
  — as a bare JSON number (`"ex:version": 1`, no `$`/`type` wrapper at all),
  which is itself in tension with the schema's requirement once a wrapper
  *is* used; see the fix-direction note left on the issue. Sibling of #235
  (`xsd:long`→`xsd:int` mutation) for the `ex:long` case specifically, but
  independent — #235 does not touch `ex:int`/`ex:float`, which this defect
  does. Any fix changes serialized output, so it's 3.0 material under the
  2.x output freeze.
- **Properties with multiple values (§2.2 "Properties with multiple values")**:
  `encode_json_container` emits a JSON array of per-value encodings when an
  attribute has more than one value (`provjson.py:258-262`) — matches the
  submission's worked example (mixed native/typed values in one array)
  exactly, executed against a multi-valued `ex:values` attribute mixing a
  plain string, an `xsd:positiveInteger` `Literal`, and a QualifiedName.

**Verdict:** value encoding — **conformant** for native types, language-tagged
strings, and `Literal`/`Identifier`/`datetime` values; **finding listed**
(new #246, non-string `$` for plain `int`/`float`); pre-existing #89/#168
unchanged.

#### 3.2.3 Bundle encoding (§3.3)

`encode_json_document` (`provjson.py:188-204`) puts each named bundle's own
`encode_json_container` output under `container["bundle"][str(identifier)]`,
alongside the top-level container's own records — matching §3.3's worked
example structure exactly (top-level `entity`/`wasGeneratedBy`/etc. for the
document's own assertions, plus a top-level `bundle` map keyed by bundle
identifier, each value itself a full PROV-JSON container). The "a bundle's
content MUST NOT contain another bundle" constraint (§3.3) is enforced at the
model level (`ProvDocument.bundle()` only permits document-level nesting,
already audited in §2.4) rather than re-checked by the JSON encoder;
consistent with that section's conclusion. Executed round-trip of the
`Bundle1`/`Bundle2` examples (both of which exercise this path) confirms the
shape matches the submission's worked example field-for-field.

One schema-authoring quirk noted while validating (not a `prov` defect, see
`schemas/README.md` for the full note): the vendored schema's top-level
object sets `"additionalProperties": false` but `definitions.bundle` does
not, so a `mentionOf` relation (PROV-Links, postdates this submission and is
absent from the schema's `properties` entirely) only validates when it
appears inside a named bundle — `Bundle2` places its `mentionOf` inside
`alice:bundle5` and validates cleanly; the identical relation at the document
root would be schema-rejected as an unrecognised property. Not reachable by
any of the 8 examples' current shape, so not a test failure; recorded here in
case a future example adds a top-level `mentionOf`.

**Verdict:** bundle encoding — **conformant**.

#### 3.2.4 Namespace/prefix handling (§2, "prefix"/"default")

`encode_json_container` (`provjson.py:224-229`) emits a `prefix` map from
every registered namespace plus, if set, a `default` key for the bundle's
default namespace — matching §2's worked example and its "special prefix
called `default`" rule exactly. `decode_json_container` (`provjson.py:324-331`)
mirrors this on input, routing the `default` key to
`set_default_namespace` and every other key to `add_namespace`. The
submission's implicit `prov`/`xsd` default-prefix bindings (§2, "Default
prefixes") are handled identically on both sides: `prov`/`xsd`-prefixed terms
resolve without an explicit `prefix` entry (`DEFAULT_NAMESPACES`,
`model/namespaces.py`, executed: a document using bare `prov:type`/`xsd:int`
values with no `prefix` block round-trips through JSON unchanged). Per-bundle
`prefix` maps (a named bundle may declare its own namespaces, §3.3's example
shows only document-level prefixes but doesn't prohibit per-bundle ones) are
supported identically to the top-level case, since `encode_json_container`/
`decode_json_container` are the same functions for both.

**Verdict:** namespace/prefix handling — **conformant**.

**Overall §3.2 verdict:** PROV-JSON output is schema-valid except for the
non-string `$` defect on plain `int`/`float` attribute values (filed #246,
deferred to 3.0 under the output freeze); structural encoding, bundle
encoding, and namespace/prefix handling are all conformant; the `$`/`type`
value-encoding rules are conformant apart from the new #246 finding and the
pre-existing #89/#168 anchors (unchanged by this audit). Two schema-authoring
quirks in the *submission's own schema* (not `prov` defects) were noted:
the `wasEndedby`/`wasEndedBy` casing mismatch and the top-level-only
`additionalProperties: false` gap for PROV-Links relations like `mentionOf`
— both documented in `schemas/README.md` and neither reachable by the
current 8-example corpus.

### 3.3 PROV-N vs grammar

**Method:** audit-only, no shipped test code (PROV-N has no parser in `prov` — #122 — so
there is nothing to round-trip; `provconvert` must not become a test dependency). Every
`examples.tests` document's `get_provn()` output, plus a 39-case grammar stress corpus, was
fed to ProvToolbox 2.0.4's `provconvert` (`/usr/local/bin/provconvert`, Java ANTLR-based
PROV-N parser) as an external grammar oracle, checked against the
[PROV-N REC grammar](https://www.w3.org/TR/prov-n/) (production numbers below are the REC's).
All scripts and captured outputs live in the session scratchpad (not committed); the
generator was:

```bash
OUT=<scratchpad>/provn-audit && mkdir -p "$OUT"
uv run python - "$OUT" <<'EOF'
import sys
from pathlib import Path
from prov.tests import examples

out = Path(sys.argv[1])
for name, factory in examples.tests:
    (out / (name.replace(" ", "_") + ".provn")).write_text(factory().get_provn())
EOF
for f in "$OUT"/*.provn; do
    provconvert -infile "$f" -outfile "${f%.provn}.xml" \
        && echo "OK   $(basename "$f")" || echo "FAIL $(basename "$f")"
done
```

**Oracle caveat (matters for reading every transcript below):** `provconvert` exits 0 even
when its ANTLR parser hits syntax errors — it error-recovers, prints
`Parsing not processed for 0` to stderr, and writes whatever survived recovery (possibly an
empty document) to the output file. A meaningful "parses cleanly" verdict therefore required
exit 0 **and** clean stderr **and** the expected records present in the converted output;
every OK below was checked that way (stderr logs swept for `Parsing not processed`; outputs
grepped for the expected identifiers/values).

#### 3.3.1 Examples corpus (8 documents)

```
OK   Bundle1.provn
FAIL Bundle2.provn
OK   collections.provn
FAIL datatypes.provn
OK   Long_literals.provn
OK   Primer.provn
OK   W3C_Publication_1.provn
OK   W3C_Publication_2.provn
```

The six OKs are genuine (clean stderr, records present) — including `W3C_Publication_1`,
whose `chairs:2011OctDec/0004` identifier is invalid in PROV-XML (§3.1) but fine in PROV-N
(`/` is in `PN_CHARS_OTHERS`, production [54]). Both FAILs were triaged individually with
control experiments; they have different causes and neither is a whole-document problem:

1. **`Bundle2` — `mentionOf` line; two distinct facts, one filed (#248).**
   `provconvert` dies post-parse with `UnsupportedOperationException: newMentionOf not
   supported` at `vanilla.ProvFactory.newMentionOf` — the parse itself succeeded (the stack
   is in `TreeTraversal.convert`, i.e. tree-to-bean conversion), so this exit is an **oracle
   limitation** of ProvToolbox 2.0.4's "vanilla" model, not a grammar verdict. Control:
   stripping the single `mentionOf(...)` line makes the rest of `Bundle2` parse cleanly (OK).
   However, checking the construct against the specs directly surfaced a real defect:
   Mention is not in the PROV-N REC grammar at all (dropped to the PROV-Links Note; REC
   change log "Moved feature at Risk mention into a separate note"), the REC's fallback
   `extensibilityExpression` (production [49], §5) requires the predicate to be "a
   qualifiedName with a non-empty prefix", and PROV-Links' own production is
   `mentionExpression ::= "prov:mentionOf" "(" ... ")"` — prefix explicit (its change log:
   "Updated grammar to make prov prefix explicit"). `prov` emits bare `mentionOf(...)`
   (`PROV_N_MAP[PROV_MENTION]`), derivable from neither grammar — **filed #248**. Triage
   nuance recorded on the issue: ProvToolbox's own PROV-N writer
   (`NotationConstructor.newMentionOf`, `modules-core/prov-n/.../NotationConstructor.java:282`)
   and ANTLR grammar (`PROV_N.g:338`) use the same bare keyword, so the deviation is a
   de-facto interop convention with the Java reference implementation, and a spec-exact fix
   would break `provconvert` parsing as currently generated.
2. **`datatypes` — bare out-of-range `INT_LITERAL`; filed #249.** `provconvert` fails with
   `NumberFormatException: For input string: "123456789000"` while converting
   `ex:long=123456789000`. Per §3.7.3 (production [43] `convenienceNotation`, terminal [60]
   `INT_LITERAL`), a bare integer is "syntactic sugar for quoted strings with datatype ...
   xsd:int" — so the text is *grammatical* but asserts a value outside `xsd:int`'s 32-bit
   value space, which the oracle correctly rejects at `Integer.parseInt`. Control: replacing
   the value with a small integer parses the rest of the document cleanly (OK — including
   the `"""..."""` multiline string, the `@en` language tag and the `%% xsd:float`/
   `xsd:boolean`/`xsd:dateTime` typed literals). Root cause is `encoding_provn_value`'s
   final `else: return str(value)` branch (`src/prov/model/records.py:223-225`) — no
   magnitude check on plain `int`s. Same defect family as #244 (XML leg) / #246 (JSON leg) /
   #235 (`xsd:long` collapse feeding all legs); **filed #249** deliberately covering the
   PROV-N leg and the PROV-O leg together (see §3.4) — the two code sites (`records.py`,
   `provrdf.py`) are independently fixable, so step 31 triage may split it into separate
   fix PRs (scope note also left on the issue).

#### 3.3.2 Grammar stress corpus (39 cases)

Generated per category and run through the same oracle-plus-verification procedure:

- **#223 metacharacter local parts (6 cases: `ex:n'ame`, and locals containing `(`, `)`,
  `,`, `=`, `;`) — all 6 mis-parse; all are #223, no new issue.** The violated productions
  are [52] `QUALIFIED_NAME` / [53] `PN_LOCAL` / [55] `PN_CHARS_ESC` (§3.7.1): the spec is
  explicit that these delimiter characters "are not allowed in local parts" unescaped and
  must appear `\`-escaped per `PN_CHARS_ESC`; `QualifiedName.provn_representation()` emits
  them raw. Three distinct oracle failure modes, two of them silent (worth quoting because
  they show the corruption a downstream PROV-N consumer would experience):
  - `,` (`ex:na,me`): hard crash, exit 1 (`NullPointerException` building the mangled
    attribute list) — the only case a naive exit-code check catches.
  - `)` (`ex:na)me`): **exit 0, silent truncation** — the oracle's output contains
    `entity(ex:na)`; the identifier was cut at the unescaped delimiter and the remainder
    discarded by error recovery.
  - `'`, `(`, `=`, `;`: **exit 0, record silently dropped** — parse errors on stderr and an
    empty document out.
- **Non-ASCII identifiers and values (3 cases) — all OK.** `ex:実験データ` (CJK) and
  `ex:ניסוי` (RTL Hebrew) parse and survive into the output verbatim ([53] `PN_LOCAL` builds
  on SPARQL `PN_CHARS`, which spans these ranges); a string attribute value mixing CJK,
  accented Latin, Hebrew and Arabic also round-trips through the oracle intact.
- **Language-tagged literals (1 additional case beyond the `ATTRIBUTE_VALUES[1..2]`
  entries already counted in the 28-entry bullet below) — OK.** `@fr` on
  `prov:label` and `@ja` on an extra attribute both parse ([43]'s `STRING_LITERAL
  (LANGTAG)?`) and come back as `xml:lang`-tagged values in the oracle's XML.
- **`ATTRIBUTE_VALUES` corpus (28 cases, one document per entry asserted on an extra
  attribute) — all 28 OK**, covering every XSD numeric type in the corpus, booleans,
  `xsd:anyURI`, `Identifier`, QualifiedNames across several namespaces, and both `datetime`
  entries. (Index 4, `Literal(1, XSD_LONG)`, is only "OK" because #235 has already collapsed
  it to `xsd:int` before serialization — the value 1 is in range, so the oracle cannot see
  the mutation; the datatype defect is #235's, not a new grammar finding.)
- **Time-zoned datetimes (1 case: `startTime`/`endTime`/`prov:time` carrying +05:30 and
  -07:00 offsets, with microseconds) — OK.** All three render as ISO-8601 with offset inside
  a `time`/`"..." %% xsd:dateTime` slot and parse; offsets survive into the oracle's output.

**En-route finding (filed #251):** while auditing `encoding_provn_value`
(`src/prov/model/records.py:205-225`) against the literal productions, its `float` branch
was found to emit `f'"{value:g}" %% xsd:float'` — the same plain Python float that
JSON/XML/RDF all serialize as `xsd:double` (`provjson.py:69-74`, `provxml.py:221-226`,
`provrdf.py:91-97`) is asserted as `xsd:float` in PROV-N **and** `%g`-truncated to 6
significant digits (executed: `0.123456789` → `"0.123457" %% xsd:float` in PROV-N vs
`{"$": 0.123456789, "type": "xsd:double"}` in PROV-JSON). Grammatical, but the same
document asserts different typed values per format. Sibling of #225/#89; invisible to
round-trip tests because PROV-N is write-only.

**Verdict:** PROV-N output is grammar-valid for the whole examples corpus and the
whole stress corpus **except**: (a) metacharacter local parts — #223, confirmed against
productions [52]/[53]/[55] with three concrete downstream failure modes; (b) bare
`mentionOf` — not derivable from the REC or PROV-Links grammars, **new #248** (with the
ProvToolbox-parity triage note); (c) out-of-int32-range plain ints — grammatical but
value-invalid `INT_LITERAL`s, **new #249**; plus (d) the `%g`/`xsd:float` plain-float
divergence, **new #251**. Non-ASCII/CJK/RTL names, language tags, the full
`ATTRIBUTE_VALUES` datatype corpus and non-UTC-offset datetimes are all conformant.

### 3.4 PROV-O vs mapping tables

**Method:** audited `src/prov/serializers/provrdf.py` (encode side) against
[PROV-O (W3C REC 2013-04-30)](https://www.w3.org/TR/prov-o/) — the two normative
Qualification Pattern tables in §3.1 "Qualified Terms" (7 Starting-Point + 7 Expanded
qualifiable relations, each with its qualification property, qualified class and influencer
property) and the per-term cross reference. Verification was empirical, not code-reading
alone: a scratch script serialized every record type to N-Triples in three variants —
minimal anonymous (binary form), anonymous with all formals + extra attributes (forces the
qualified pattern on a blank node), and identified (forces the qualified pattern on an IRI)
— and the emitted triples were compared against the spec tables per type. Decode-side
round-trip fidelity is anchored by the existing #217/#218/#225/#226 issues and was not
re-audited; #96 (turtle prefix propagation) is the standing anchor for
namespace-into-rdflib quirks.

**A key spec allowance frames the whole table:** PROV-O §3.1 states "It is correct and
acceptable for an implementer to use either qualified or unqualified forms as they choose
(or both) ... When the qualified form is expressed, including the equivalent unqualified
form can facilitate PROV-O consumption, and is thus encouraged." `prov` emits the binary
triple *only* when no qualification is needed for 7 relation types
(the `rec_type not in {...}` set at `provrdf.py:476-491`: Generation, Usage, Start, End,
Invalidation, Derivation, Association) but *always* for the other qualifiable 4
(Communication, Attribution, Delegation, Influence) — inconsistent style, but both patterns
are conformant under that allowance, **except** for the influencer-property omission filed
as #250 (below). Identified relations of every type emit only the qualified form (no binary
triple) — also covered by the allowance.

Per-type verdicts (empirical; "binary" = unqualified property triple, "qualified" =
qualification property + class + node contents):

| Record type | Binary form emitted | Qualified form emitted | Verdict |
|---|---|---|---|
| Entity | `?e a prov:Entity` | n/a | **conformant** (`prov:label`→`rdfs:label`, `prov:type`→`rdf:type`, `prov:location`→`prov:atLocation`, `prov:value` passthrough all verified) |
| Activity | `?a a prov:Activity` + `prov:startedAtTime`/`prov:endedAtTime` (xsd:dateTime) | n/a | **conformant** |
| Agent | `?ag a prov:Agent` | n/a | **conformant** |
| Generation | `e prov:wasGeneratedBy a` (minimal only) | `prov:qualifiedGeneration` → `prov:Generation` [`prov:activity`, `prov:atTime`, `prov:hadRole`] | **conformant** (qualified-only when qualified; spec-allowed) |
| Usage | `a prov:used e` (minimal only) | `prov:qualifiedUsage` → `prov:Usage` [`prov:entity`, `prov:atTime`, `prov:hadRole`] | **conformant** (ditto) |
| Communication | `a2 prov:wasInformedBy a1` (always) | `prov:qualifiedCommunication` → `prov:Communication` [**no `prov:activity` when anonymous** — #250; present when identified] | **finding (#250)** |
| Start | `a prov:wasStartedBy trigger` (minimal only) | `prov:qualifiedStart` → `prov:Start` [`prov:entity`, `prov:hadActivity` (starter), `prov:atTime`] | **conformant** |
| End | `a prov:wasEndedBy trigger` (minimal only) | `prov:qualifiedEnd` → `prov:End` [`prov:entity`, `prov:hadActivity` (ender), `prov:atTime`] | **conformant** |
| Invalidation | `e prov:wasInvalidatedBy a` (minimal only) | `prov:qualifiedInvalidation` → `prov:Invalidation` [`prov:activity`, `prov:atTime`] | **conformant** |
| Derivation | `e2 prov:wasDerivedFrom e1` (minimal only) | `prov:qualifiedDerivation` → `prov:Derivation` [`prov:entity`, `prov:hadActivity`, `prov:hadGeneration`, `prov:hadUsage`]; Revision/Quotation/PrimarySource subtypes re-map to `prov:qualifiedRevision`/`Quotation`/`PrimarySource` + `prov:Revision`/etc. per the Expanded table | **conformant** |
| Attribution | `e prov:wasAttributedTo ag` (always) | `prov:qualifiedAttribution` → `prov:Attribution` [**no `prov:agent` when anonymous** — #250; present when identified] | **finding (#250)** |
| Association | `a prov:wasAssociatedWith ag` (minimal only) | `prov:qualifiedAssociation` → `prov:Association` [`prov:agent`, `prov:hadPlan`, `prov:hadRole`]; agent-less plan-only association emits a valid agent-less qualified node | **conformant** |
| Delegation | `ag2 prov:actedOnBehalfOf ag1` (always) | `prov:qualifiedDelegation` → `prov:Delegation` [`prov:hadActivity` but **no `prov:agent` when anonymous** — #250; present when identified] | **finding (#250)** |
| Influence | `o2 prov:wasInfluencedBy o1` (always) | `prov:qualifiedInfluence` → `prov:Influence` [**no `prov:influencer` when anonymous** — #250; present when identified] | **finding (#250)** |
| Specialization | `sub prov:specializationOf super` | none in PROV-O (not qualifiable) — but see low-level note below | **conformant** (public API) |
| Alternate | `alt2 prov:alternateOf alt1` — **argument order reversed** vs the DM mapping | none in PROV-O | **conformant with note** (see below) |
| Mention | `infra prov:mentionOf supra` + `infra prov:asInBundle b` | none defined | **conformant extension** (PROV-Links; terms removed from the PROV-O REC itself — its change log: "Removed prov:mentionOf and prov:asInBundle, which have been relocated to its own Note") |
| Membership | `c prov:hadMember e` | none in PROV-O (not qualifiable) — but see low-level note below | **conformant** (public API) |

Findings in detail:

- **Filed #250 — anonymous qualified Communication/Attribution/Delegation/Influence nodes
  omit their influencer property.** For these four types the influencer endpoint is consumed
  by the always-emitted binary triple (`used_objects.append(...)`, `provrdf.py:492`) and
  never re-emitted on the qualified node, so the node violates the normative tables' shape
  (`prov:activity`/`prov:agent`/`prov:influencer` respectively) and is uninterpretable in
  isolation. Executed ambiguity proof: two attributed attributions of `ex:e1` to different
  agents emit two `prov:Attribution` bnodes carrying only their extra attributes — no
  consumer can tell which attribution involved which agent. This is the encode-side root
  cause of #226's decode-side collapse (delegations keyed on `(delegate, activity)` because
  `prov:agent` is absent); #250 records the full four-type scope. The identified variants of
  all four types were verified to carry the influencer property correctly, as do the other
  seven qualifiable types in every variant.
- **Filed #249 (shared with §3.3) — plain `int` → `xsd:int` with no magnitude check**
  (`LITERAL_XSDTYPE_MAP`, `provrdf.py:91-97`): `ex:long=123456789000` emits
  `"123456789000"^^xsd:int`, an ill-typed literal (lexical form outside the datatype's value
  space, RDF 1.1 §5.4). Executed. XML leg is #244; JSON leg is #246.
- **Alternate: direction reversed (doc note, needs maintainer confirmation — no issue).**
  `d.alternate(alt1, alt2)` (PROV-N `alternateOf(alt1, alt2)`) emits
  `alt2 prov:alternateOf alt1` — the serializer swaps subject/object for `PROV_ALTERNATE`
  (`provrdf.py:494-495`) and the deserializer swaps back (`provrdf.py:832-833`), so `prov`
  round-trips itself, and PROV-CONSTRAINTS defines `alternateOf` as symmetric, so no false
  statement is produced. But a third-party tool reading `prov`'s RDF reconstructs the
  arguments transposed relative to the PROV-N/PROV-DM statement, which only constraint-aware
  consumers should treat as equivalent. 3.0 triage should decide whether to align with the
  DM argument order.
- **Low-level `new_record` paths emit vocabulary that does not exist in PROV-O (doc-only,
  §2.8-item-4 family — no issue).** PROV-O's normative tables make exactly 14 relations
  qualifiable; Specialization/Alternate/Membership are not, and Mention is not in PROV-O at
  all. The qualifier construction (`PROV["qualified" + rec_type._localpart]`,
  `provrdf.py:534`) is generic, so records reachable only by deliberate low-level misuse
  (id/attributes on the no-id-no-attrs relations, cf. §2.5/§2.8) mint non-existent terms —
  executed: specialization-with-attrs emits `prov:qualifiedSpecialization` +
  `prov:Specialization`; membership-with-attrs emits `prov:qualifiedMembership` +
  `prov:Membership`; an identified mention emits `prov:qualifiedMention` + `prov:Mention` +
  raw formal-attribute predicates `prov:generalEntity`/`prov:bundle` (also non-terms).
  Conversely an alternate given extra attributes **silently drops them** (the
  `PROV_ALTERNATE` `continue` at `provrdf.py:513-514` precedes the qualifier block). None of
  this is reachable through the public factories, which correctly refuse id/attributes on
  these types; recorded for the step 31 triage alongside the §2.8 permissiveness family.
- **Bundles → TriG named graphs (conformant convention).** PROV-O deliberately does not
  specify an RDF encoding for bundles ("this document does not specify how to encode
  Bundles in RDF"; its own examples use TriG named graphs illustratively), so
  `encode_document`'s one-named-graph-per-bundle TriG layout is a legitimate choice —
  consistent with both the spec's illustrations and ProvToolbox. One cosmetic quirk observed
  (adjacent to #96, no new issue): the bundle's graph re-binds an already-bound namespace
  IRI under a fresh `ns1:` prefix in TriG output, so the same IRI carries two prefixes in
  one file.
- **Value encoding on the RDF leg:** plain strings/`bool`s map to native RDF literals,
  `datetime` → `xsd:dateTime` (offsets preserved), `QualifiedName` → IRI, `Identifier` →
  `xsd:anyURI` literal, language-tagged `Literal`s → language-tagged RDF literals, and
  `prov:role`/`prov:plan` extra attributes map to `prov:hadRole`/`prov:hadPlan` (verified
  with QualifiedName values → IRIs). All conformant; the datatype-fidelity losses through
  the *round trip* remain #218/#225 (unchanged), and the string-vs-QualifiedName
  `prov:type` idiom trap remains #236.

**Verdict:** all 3 element types and 11 of the 15 relation types map to PROV-O exactly
as the normative qualification tables require (including the Revision/Quotation/
PrimarySource re-mapping and Mention as a conformant PROV-Links extension);
Communication/Attribution/Delegation/Influence carry a genuine defect in their anonymous
qualified form (**new #250**, root cause of existing #226); plain-int typing is ill-typed
outside int32 (**new #249**, RDF leg); Alternate's reversed argument order and the
low-level-only invented-vocabulary/dropped-attribute paths are recorded as doc-only triage
items. Emitting qualified-form-only (identified/qualified cases) is conformant under
PROV-O §3.1's explicit either-or-both allowance, though the spec encourages also including
the binary triple — a 3.0 consideration.
## 4. Unification vs PROV-CONSTRAINTS (step 30b) — summary

Full rule-by-rule analysis (the authority for the step 36b reimplementation):
`docs/superpowers/specs/2026-07-10-unification-gap-analysis.md`. Audited 2026-07-11 on
branch `audit/unification-constraints` against
[PROV-CONSTRAINTS (W3C REC 2013-04-30)](https://www.w3.org/TR/prov-constraints/) §4
(term unification), §6.1 (uniqueness/key Constraints 22–29), and §7.2 (bundle
scoping), using the 153-case ProvToolbox/W3C unification corpus vendored under
`src/prov/tests/unification/constraints/` (origin/licence in its README) and locked
by `src/prov/tests/test_unification_constraints.py`. Headlines:

- **`_unified_records()` (`src/prov/model/bundle.py:384-414`) is an identifier-keyed
  attribute union, not PROV-CONSTRAINTS merging** — umbrella **filed #253** (fix
  vehicle: step 36b, 3.0). Gap classes, each with an executed example and a
  characterization test: no pairwise term unification of formal attributes
  (Constraints 22/23); concrete-vs-concrete conflicts rejected only *accidentally*
  by `add_attributes`'s cardinality guard (`records.py:622-643` — right outcome
  class, undocumented generic `ProvException`, 25 corpus fail-cases); placeholder
  (`-`) vs concrete merges silently (the model cannot represent `-`; 12 corpus
  fail-cases); incompatible types merge silently (entity + activity sharing an id
  become an *entity* carrying `prov:startTime` as a literal extra attribute — the
  result depends on record order; Constraints 50/55); uniqueness Constraints 24–29
  (keys other than the identifier) are not applied in either direction — invalid
  duplicates pass through *and* valid instances never reach the spec's normal form
  (anonymous records that unique-generation would fold in stay separate).
- **Bundle scoping is the conformant part:** `ProvDocument.unified()`
  (`bundle.py:1455-1480`) unifies the toplevel and each sub-bundle independently of
  each other (§7.2), confirmed by test. The `flattened().unified()` idiom (as
  `test_unifying` uses) merges across bundle boundaries — spec-invalid usage,
  characterized and recorded for 36b to document as outside PROV-CONSTRAINTS.
- **Corpus tally:** 85 success / 68 fail files; 83 parseable success cases all unify
  without complaint; 25 fail-cases hit the accidental guard; 42 fail-cases merge or
  pass silently; 3 files cannot be parsed at all.
- **En-route PROV-XML bug (filed #254):** the 3 unparseable `bundle-*` files crash
  the XML deserializer with a raw `UnboundLocalError`
  (`provxml._extract_attributes`, `provxml.py:456`) — a child element whose only XML
  attributes are unrecognised (here ProvToolbox's `<prov:bundle>` dialect, not the
  XSD's `<prov:bundleContent>`) assigns no value, and a second, worse mode silently
  reuses the *previous sibling's* value (executed: after `<ex:first>hello</ex:first>`,
  `<ex:second ex:junk="x">world</ex:second>` deserializes as `ex:second="hello"`).
  Sibling of
  #228 (JSON leg); the inputs are schema-invalid, but malformed input must raise
  `ProvXMLException`, not corrupt data.
## 5. Issues filed by this audit
| Issue | Finding | Section |
|---|---|---|
| [#235](https://github.com/trungdong/prov/issues/235) | `PROV-DM conformance:` Literal values typed `xsd:long` are silently re-typed as `xsd:int` in every serialization (§5.7.3) | §2.7.3 |
| [#236](https://github.com/trungdong/prov/issues/236) | `PROV-DM conformance:` documented `prov:type` idiom for agent subtypes asserts a plain string, not the `prov:Person` type (§5.7.2.4) | §2.3 |
| [#237](https://github.com/trungdong/prov/issues/237) | `PROV-DM conformance:` factory time parameters leak raw dateutil `ParserError` and reject the valid xsd:dateTime hour-24 form (§5.7.3) | §2.7.3 |
| [#238](https://github.com/trungdong/prov/issues/238) | `PROV-DM conformance:` `prov:QUALIFIED_NAME`-typed Literals are not resolved to QualifiedNames, breaking round-trip equality (§5.7.3) | §2.7.3 |
| [#239](https://github.com/trungdong/prov/issues/239) | `Bug:` `prov.read()` cannot auto-detect valid PROV-XML — RDF deserializer's `BadSyntax` propagates before the XML deserializer is tried (Phase-3 loose end, confirmed) | §2.9 |
| [#240](https://github.com/trungdong/prov/issues/240) | `Bug:` `ProvDocument.serialize()` silently writes to a repr-named CWD file when given a non-`io.IOBase` file object (e.g. `NamedTemporaryFile`) | §2.9 |
| [#244](https://github.com/trungdong/prov/issues/244) | `PROV-XML conformance:` plain Python ints are always typed `xsd:int`, producing schema-invalid output outside the int32 range | §3.1 |
| [#246](https://github.com/trungdong/prov/issues/246) | `PROV-JSON conformance:` numeric attribute values are encoded with a non-string `$`, violating the submission's typed-literal schema | §3.2 |
| [#248](https://github.com/trungdong/prov/issues/248) | `PROV-N conformance:` `mentionOf` is emitted without the `prov:` prefix required by the PROV-Links `mentionExpression` production | §3.3 |
| [#249](https://github.com/trungdong/prov/issues/249) | `PROV-N conformance:` plain Python ints outside the 32-bit range are asserted as `xsd:int` in PROV-N output (originally filed covering the PROV-O leg too; split at the §6 triage checkpoint — the PROV-O leg is now #256) | §3.3 |
| [#250](https://github.com/trungdong/prov/issues/250) | `PROV-O conformance:` anonymous qualified Communication/Attribution/Delegation/Influence nodes omit their influencer property, producing ambiguous PROV-O (root cause of #226) | §3.4 |
| [#251](https://github.com/trungdong/prov/issues/251) | `PROV-N conformance:` plain Python floats serialize as `%g`-formatted `xsd:float`, diverging from the `xsd:double` all other serializers assert and truncating precision | §3.3 |
| [#253](https://github.com/trungdong/prov/issues/253) | `PROV-CONSTRAINTS conformance:` `unified()` does not implement PROV-CONSTRAINTS merging (umbrella; authority: the step-30b gap-analysis doc; fix vehicle: step 36b) | §4 |
| [#254](https://github.com/trungdong/prov/issues/254) | `Bug:` PROV-XML deserializer leaks raw `UnboundLocalError` or silently reuses the previous attribute's value on unrecognised XML attributes (sibling of #228) | §4 |
| [#256](https://github.com/trungdong/prov/issues/256) | `PROV-O conformance:` plain Python ints outside the 32-bit range are asserted as `xsd:int` in RDF output (the PROV-O leg split out of #249) | §3.4 (filed at the §6 triage checkpoint) |
| [#257](https://github.com/trungdong/prov/issues/257) | `PROV-DM conformance:` unenforced normative structural constraints allow silently invalid statements (the §2.8 family — 3.0 API-philosophy umbrella, also covering the §3.4 low-level `new_record` invented-vocabulary/dropped-attribute paths) | §2.8 (filed at the §6 triage checkpoint) |
| [#258](https://github.com/trungdong/prov/issues/258) | `PROV-O conformance:` the `alternateOf` triple is emitted with subject/object transposed relative to the PROV-DM argument order | §3.4 (filed at the §6 triage checkpoint) |
| [#259](https://github.com/trungdong/prov/issues/259) | `PROV-DM conformance:` `Literal` language tags compare case-sensitively, diverging from RDF 1.1's case-insensitive value space (§5.7.3) | §2.7.3 (filed at the §6 triage checkpoint) |
| [#260](https://github.com/trungdong/prov/issues/260) | `Feature:` add convenience factories for the PROV-DM agent subtypes (Person/Organization/SoftwareAgent) and `EmptyCollection` | §1 (filed at the §6 triage checkpoint) |
| [#261](https://github.com/trungdong/prov/issues/261) | `Feature:` support `prov:Bundle` as a first-class entity type for provenance-of-provenance (PROV-DM §5.4.2) | §1 (filed at the §6 triage checkpoint) |

Not filed (findings-doc only): the Mention/PROV-Links labelling nit (§2.5, cosmetic), the
two §3.1 PROV-XML format limitations (QName-incompatible local names; language tags on
non-`prov:label` attributes) — both inherent to the PROV-XML schema itself, not
implementation defects — the two §3.2 PROV-JSON schema-authoring quirks (`wasEndedby`
casing typo; top-level-only `additionalProperties: false` gap for `mentionOf`) — both bugs
in the submission's own vendored schema, not `prov` — the §3.3 metacharacter local-part
failures (all instances of the already-filed #223), and the §3.4 TriG duplicate-prefix
cosmetic quirk (#96-adjacent). Every other item originally held back as findings-doc-only
was promoted to a real issue at the triage checkpoint (2026-07-11): the §2.8 validation-gap
family — including the §3.4 low-level `new_record` invented-vocabulary/dropped-attribute
paths — is now covered by umbrella #257, the `Literal` language-tag case-sensitivity nit is
#259, the §3.4 Alternate argument-order reversal is #258, and the section-1 feature gaps
are #260 (agent-subtype/`EmptyCollection` factories) and #261 (`prov:Bundle` entity type).
## 6. Triage (step 31) — proposed → approved

The classification below was presented at the maintainer checkpoint on 2026-07-11 and
**approved**, with the following checkpoint outcomes (all applied on GitHub the same day):

- **#249 split**: #249 was retitled to cover the PROV-N leg only ("PROV-N conformance:
  plain Python ints outside the 32-bit range are asserted as xsd:int in PROV-N output");
  the PROV-O leg was split out as new issue #256.
- **All five proposed 2.x items confirmed**, and a new **`2.5.0` milestone** was created
  on GitHub to hold them.
- **The backlog bucket is represented as a new `backlog` label** (post-3.0 features carry
  the label rather than a milestone).
- **All four deliberately-unfiled borderline finding groups were promoted to issues,
  yielding five** (the section-1 feature-gap finding split into two): #257
  (§2.8 validation-gap family umbrella), #258 (alternateOf transposition), and #259
  (language-tag case-sensitivity) went to the 3.0.0 milestone; #260
  (agent-subtype/`EmptyCollection` factories) and #261 (`prov:Bundle` entity type) went
  to the `backlog` label.

| Issue | Bucket | Rationale |
|---|---|---|
| [#34](https://github.com/trungdong/prov/issues/34) | 3.0.0 | Pre-existing milestone confirmed — merging attributes across types is behaviour-changing; folds into the `unified()` rework (#253, step 36b). |
| [#77](https://github.com/trungdong/prov/issues/77) | 3.0.0 | Pre-existing milestone confirmed — fixing `Decimal` Literal comparison changes equality semantics. |
| [#89](https://github.com/trungdong/prov/issues/89) | 3.0.0 | Pre-existing milestone confirmed — distinguishing typed from untyped literals changes representation and output. |
| [#168](https://github.com/trungdong/prov/issues/168) | 3.0.0 | Pre-existing milestone confirmed — changing QName typing alters PROV-JSON output. |
| [#217](https://github.com/trungdong/prov/issues/217) | 3.0.0 | Pre-existing milestone confirmed — representing scruffy same-id/differing-time relations in RDF requires output changes. |
| [#218](https://github.com/trungdong/prov/issues/218) | 3.0.0 | Pre-existing milestone confirmed — restoring RDF multi-datatype fidelity changes round-trip output. |
| [#223](https://github.com/trungdong/prov/issues/223) | 3.0.0 | Pre-existing milestone confirmed — escaping metacharacter local parts changes PROV-N output. |
| [#224](https://github.com/trungdong/prov/issues/224) | 3.0.0 | Pre-existing milestone confirmed — preserving empty-string attributes changes PROV-XML output. |
| [#225](https://github.com/trungdong/prov/issues/225) | 3.0.0 | Pre-existing milestone confirmed — preserving `xsd:float` precision changes RDF output. |
| [#226](https://github.com/trungdong/prov/issues/226) | 3.0.0 | Pre-existing milestone confirmed — fixing anonymous qualified delegations changes RDF output (encode-side root cause now #250). |
| [#228](https://github.com/trungdong/prov/issues/228) | 3.0.0 | Pre-existing milestone confirmed — tightening the JSON deserializer's exception contract is a behaviour change. |
| [#96](https://github.com/trungdong/prov/issues/96) | 3.0.0 | Newly milestoned — turtle prefix propagation is an output-changing serializer fix. |
| [#235](https://github.com/trungdong/prov/issues/235) | 3.0.0 | Newly milestoned — undoing the `xsd:long`→`xsd:int` mutation changes output in every serialization (#89 sibling). |
| [#237](https://github.com/trungdong/prov/issues/237) | 3.0.0 | Newly milestoned — raising `ProvException` (and accepting hour-24) in the factory time params is an exception-contract change. |
| [#238](https://github.com/trungdong/prov/issues/238) | 3.0.0 | Newly milestoned — resolving `prov:QUALIFIED_NAME` literals to QualifiedNames changes equality (#89 sibling). |
| [#244](https://github.com/trungdong/prov/issues/244) | 3.0.0 | Newly milestoned — magnitude-aware integer typing changes PROV-XML output (`xsd:int` outside int32). |
| [#246](https://github.com/trungdong/prov/issues/246) | 3.0.0 | Newly milestoned — stringifying the `$` property changes PROV-JSON output. |
| [#248](https://github.com/trungdong/prov/issues/248) | 3.0.0 | Newly milestoned — emitting `prov:mentionOf` changes PROV-N output (ProvToolbox-parity nuance recorded on the issue). |
| [#249](https://github.com/trungdong/prov/issues/249) | 3.0.0 | Newly milestoned — magnitude-aware integer typing changes PROV-N output (split at the checkpoint to the PROV-N leg only; PROV-O leg is #256). |
| [#250](https://github.com/trungdong/prov/issues/250) | 3.0.0 | Newly milestoned — emitting the missing influencer property changes RDF output (root cause of #226). |
| [#251](https://github.com/trungdong/prov/issues/251) | 3.0.0 | Newly milestoned — asserting plain floats as full-precision `xsd:double` changes PROV-N output. |
| [#253](https://github.com/trungdong/prov/issues/253) | 3.0.0 | Newly milestoned — PROV-CONSTRAINTS merging is the behaviour-changing `unified()` rework umbrella (fix vehicle: 3.0 step 36b). |
| [#256](https://github.com/trungdong/prov/issues/256) | 3.0.0 | Filed at the checkpoint (PROV-O leg of #249) — magnitude-aware integer typing changes RDF output. |
| [#257](https://github.com/trungdong/prov/issues/257) | 3.0.0 | Filed at the checkpoint (§2.8 family umbrella) — any enforcement of the unchecked normative constraints is a 3.0 API-philosophy decision. |
| [#258](https://github.com/trungdong/prov/issues/258) | 3.0.0 | Filed at the checkpoint (§3.4) — aligning `alternateOf` with the PROV-DM argument order changes RDF output. |
| [#259](https://github.com/trungdong/prov/issues/259) | 3.0.0 | Filed at the checkpoint (§2.7.3) — normalising language-tag comparison changes equality semantics. |
| [#154](https://github.com/trungdong/prov/issues/154) | 2.5.0 | Purely additive record-level chaining methods — no existing behaviour or output changes. |
| [#236](https://github.com/trungdong/prov/issues/236) | 2.5.0 | Docs-only fix (teach the QualifiedName `prov:type` idiom); any model-side string coercion stays 3.0. |
| [#239](https://github.com/trungdong/prov/issues/239) | 2.5.0 | Fix only touches an already-failing path (`read()` on PROV-XML currently raises), so no working behaviour changes. |
| [#240](https://github.com/trungdong/prov/issues/240) | 2.5.0 | Fix only touches an already-broken path (repr-named junk file), so no working behaviour changes. |
| [#254](https://github.com/trungdong/prov/issues/254) | 2.5.0 | Parse-side only — raising `ProvXMLException` on malformed input changes no serialized output. |
| [#62](https://github.com/trungdong/prov/issues/62) | backlog | PROV-CONSTRAINTS validation engine — the step-32 out-of-scope item; post-3.0 feature. |
| [#122](https://github.com/trungdong/prov/issues/122) | backlog | PROV-N parser — planned as its own post-3.0 release (Phase 5b, release 3.2.0). |
| [#124](https://github.com/trungdong/prov/issues/124) | backlog | Relations-as-set API design question — needs its own post-3.0 design work. |
| [#129](https://github.com/trungdong/prov/issues/129) | backlog | PROV-Dictionary support — post-3.0 feature. |
| [#130](https://github.com/trungdong/prov/issues/130) | backlog | Deterministic PROV-N output — post-3.0 feature. |
| [#131](https://github.com/trungdong/prov/issues/131) | backlog | Pretty PROV-N output — post-3.0 feature. |
| [#260](https://github.com/trungdong/prov/issues/260) | backlog | Filed at the checkpoint (§1 feature gaps) — additive agent-subtype/`EmptyCollection` convenience factories, post-3.0 feature. |
| [#261](https://github.com/trungdong/prov/issues/261) | backlog | Filed at the checkpoint (§1) — first-class `prov:Bundle` entity support for provenance-of-provenance, post-3.0 feature. |

## Out of scope (step 32)
The PROV-CONSTRAINTS validation engine (#62 — inferences, event ordering,
typing and impossibility checks) stays on the post-3.0 features backlog.
Only the unification/merging rules that back `unified()` are in scope.
This scope decision was restated in the Phase 3.5 summary comment posted on
the roadmap tracking issue
[#181](https://github.com/trungdong/prov/issues/181) (2026-07-11).

# Test-gap checklist (Phase 2 audit)

Audit date: 2026-07-04, measured on `master` @ `10b24db` with
`uv run coverage run -m pytest && uv run coverage report -m` (branch coverage on,
954 passed / 17 xfailed).

**Measured totals**

| Scope | Coverage |
|---|---|
| TOTAL as CI measures it (includes `src/prov/tests/`) | **91.218%** |
| Package code only (`--omit='src/prov/tests/*'`) | 87.434% |

The coverage ratchet introduced with this audit is `fail_under = 91`, against the same
measurement CI performs. Note the measurement quirk recorded in the last section: the
configured `omit = ["*/tests*"]` is not actually excluding the test modules, so the
CI-visible TOTAL is inflated by ~3.8 points of near-fully-covered test code. Fixing the
omit pattern is a T13 item and requires re-basing the ratchet at the same time.

Owner tags: **T11** = in-process CLI tests for `prov-convert`/`prov-compare` exercising
`main()` (completed 2026-07-05, PR #202); **T12** = `prov.read()` auto-detection,
`graph.py` branches, serializer registry (completed 2026-07-05, PR #203); **T13** =
remaining gaps + ratchet toward ~95 (completed 2026-07-05, see closing note); **defer**
= documented won't-test (reason given inline). Dates matter here: every "line N" /
"module X%" reference is against the code as of the run recorded next to it, and will
drift in later versions — re-measure rather than trusting old numbers.

Per-module numbers below are from the audit run; re-measure before starting each task —
they will drift.

---

## src/prov/scripts/convert.py — 27% (missed: 80–107, 113–180)

The existing `test_cli_smoke.py` runs the console script in a subprocess, so nothing in
this module is *measured* even though the happy path is smoke-tested. T11 should call
`main()`/`convert_file()` in-process.

- [x] `convert_file()` writes PROV-N output for `-f provn` (the `get_provn().encode()` path) — **T11**
- [x] `convert_file()` routes Graphviz formats (e.g. `dot`) through `prov_to_dot(...).create()` and writes bytes — **T11** (use `-f dot`; it needs a local `graphviz` binary, which CI installs via `setup-graphviz`)
- [x] `convert_file()` dispatches remaining formats to `ProvDocument.serialize()` (e.g. `-f xml`, `-f json`) — **T11**
- [x] `convert_file()` raises `CLIError` (with the format name in the message) for an unsupported output format, and `main()` turns that into exit code 2 plus a message on stderr — **T11**
- [x] `CLIError.__str__` returns the `E: ...` message — **T11** (falls out of the item above)
- [x] `main()` parses `-f/--format` (case-insensitively), positional infile/outfile, and returns 0 on success — **T11**
- [x] `main()` closes infile/outfile in the `finally` block even when conversion fails — **T11**
- [x] `main()` returns 0 on `KeyboardInterrupt` — **T11** (raise from a stub via monkeypatched `convert_file`)
- [x] `--version` prints the version message and exits — **T11**
- [ ] `if __name__ == "__main__"` block incl. `TESTRUN`/`PROFILE` scaffolding — **defer** (dead debug scaffolding, excluded by the `if __name__ == .__main__.:` exclude_lines rule already; not worth executing)

## src/prov/scripts/compare.py — 30% (missed: 41–45, 51–123)

Same subprocess-only situation as `convert.py`.

- [x] `main()` returns 0 for two equivalent documents in different formats (json vs xml) — **T11** (in-process version of the existing smoke test)
- [x] `main()` returns 1 for two non-equivalent documents — **T11** (currently untested anywhere: the smoke test only checks the "equal" outcome)
- [x] `main()` returns 2 and writes to stderr when a file cannot be parsed / wrong `-f`/`-F` format is given — **T11**
- [x] `main()` closes both files in the `finally` block — **T11**
- [x] `--version` prints the version message and exits — **T11**
- [ ] `__main__`/`TESTRUN`/`PROFILE` scaffolding — **defer** (same reason as convert.py)

## src/prov/__init__.py — 39% (missed: 38–56, i.e. the whole body of `read()`)

`prov.read()` is a documented public entry point with zero coverage.

- [x] `read(source, format="json"|"xml"|"rdf")` with an explicit format deserializes via that serializer (and lower-cases the format string) — **T12**
- [x] `read(source)` without a format auto-detects by trying each registered deserializer in turn — one test per detectable format (json, xml, rdf) — **T12** (finding: json and rdf/trig genuinely auto-detect; an xml document does not — the registry tries rdf, as trig, before xml, and rdflib's `BadSyntax` on the xml content is a `SyntaxError` that read()'s except clause doesn't catch, so it propagates before xml is ever tried. Test pins this actual behaviour rather than asserting the aspirational "all three auto-detect")
- [x] `read()` on undetectable/garbage input raises `TypeError` with the "specify the format" message after exhausting all serializers — **T12** (finding: unreachable via any real file — `ProvNSerializer.deserialize()` unconditionally raises uncaught `NotImplementedError` and is tried third, before the loop can ever exhaust normally; test reaches the branch by mocking all four deserializers to raise a caught exception type)
- [x] `read()` accepts both a filename (`str`/`PathLike`) and a file object, matching `ProvDocument.deserialize` — **T12**
- [x] Auto-detection swallows only `(TypeError, ValueError, AttributeError, KeyError)` from candidate deserializers — **T13** (`test_read.py::test_read_auto_detect_only_swallows_the_documented_exception_types` mocks a deserializer to raise `RuntimeError` and asserts it propagates instead of being swallowed)

## src/prov/graph.py — 83% (missed: 88, 90–93, 116–117 + partial branches)

The only existing test is one round-trip over the example documents; the inference and
robustness paths are untested. The mutation spike (below) confirmed these as the real
gaps: 8 of the 9 non-equivalent surviving mutants live here.

- [x] `prov_to_graph()` infers element nodes (with the correct inferred class, e.g. `ProvEntity` vs `ProvActivity`) for relation endpoints that have **no** corresponding element record in the document — **T12**
- [x] `prov_to_graph()` skips a relation whose endpoint attribute is not in `INFERRED_ELEMENT_CLASS` (the `except KeyError: continue` path) and still processes subsequent relations (mutmut: `continue` → `break` survived) — **T12**
- [x] `prov_to_graph()` skips relations where either endpoint QName is `None` — **T12**
- [x] `graph_to_prov()` ignores graph nodes that are not `ProvRecord`s or whose `bundle` is `None` (mutmut: `and` → `or` survived) — **T12**
- [x] `graph_to_prov()` ignores edges without a `"relation"` key in their edge data — **T12**

## src/prov/serializers/__init__.py — 91% (missed: 10, 39, 48)

- [x] `serializers.get()` on an unknown format raises `DoNotExist` with the format name in the message, chained from `KeyError` — **T12** (the chaining itself is already tested by `test_extras.py::test_get_serializer_for_unknown_format_chains_key_error` from T9 — extended in place with the format-name-in-message assertion, one module owns it)
- [x] `serializers.get()` lazily populates `Registry.serializers` on first call (registry starts as `None`, holds exactly the four formats json/rdf/provn/xml) — **T12**
- [x] `Serializer.serialize`/`.deserialize` abstract bodies (lines 39, 48) and the `if TYPE_CHECKING:` import (line 10) — **T13 defer, resolved via config**: added `# pragma: no cover` to both abstract `pass` bodies and `"if TYPE_CHECKING:"` to `[tool.coverage.report] exclude_lines` in `pyproject.toml` (also fixes the matching `prov/__init__.py:7` TYPE_CHECKING guard). Both modules are now 100%.

## src/prov/identifier.py — 87% → 100% (T13)

- [x] `Namespace(prefix, uri)` rejects an empty/whitespace URI with `ValueError` — **T13** (`test_identifier.py::TestNamespace::test_namespace_rejects_empty_uri` / `test_namespace_rejects_whitespace_only_uri`)
- [x] `Namespace.contains()` for a str, an `Identifier`, a non-matching URI, and a non-str/non-Identifier argument (returns False) — **T13** (new `test_identifier.py`)
- [x] `Namespace.qname()` returns a `QualifiedName` for a contained URI (str and `Identifier` inputs) and `None` for a non-contained or non-string input — **T13** (new `test_identifier.py`)

## src/prov/model.py — 90% → 98% (T13)

Large module; misses were scattered single lines, clustering into these behaviours (all
in `test_model.py` unless noted):

- [x] Literal handling: `parse_xsd_datetime` returning `None` on unparseable input; `parse_boolean` on `"true"/"1"/"false"/"0"/other`; `Literal.__eq__`/`__ne__`/`__hash__`; langtag forcing datatype to `prov:InternationalizedString` with a warning (lines 74–85, 167–194, 248–258) — **T13** (`TestLiteralHandling`)
- [x] Attribute validation errors: `ProvException` on a `None`-identifier record used as an attribute value, on unparseable datetime formal attributes, and on conflicting duplicate values for a single-valued PROV attribute (lines 480–537) — **T13** (`TestAttributeValidationErrors`). Line 503 (the "value is None" guard after `_auto_literal_conversion`) is reachable through the generic-attribute path — an anonymous (identifier-less) record used as a plain attribute value converts to `None` — and is covered by `test_identifierless_record_as_generic_attribute_value_raises`. One sub-branch deferred: 521-523 (`except TypeError` on the duplicate-value comparison) is dead for any value this library can construct — no `PROV_ATTRIBUTES` value type (`QualifiedName`/`Identifier`, `datetime.datetime`) raises `TypeError` on `!=` (confirmed empirically, including naive-vs-aware datetimes, which return `True` rather than raising).
- [x] `ProvElement` creation without an identifier raises `ProvElementIdentifierRequired` (line 634) — **T13** (`TestElementIdentifierRequired`, plus both exceptions' `__str__`)
- [x] Element convenience methods not exercised by `examples.py`: `ProvEntity.wasInvalidatedBy`/`hadMember`, `ProvActivity.wasStartedBy`/`wasEndedBy`/`wasInformedBy`, `set_time()` — **T13** (`TestElementConvenienceMethods`)
- [x] `NamespaceManager`: default-namespace-less/with-default construction, `get_namespace()` miss/hit, rename-map reuse of already-renamed namespaces, blank-node (`_:`) and non-str/Identifier inputs to `valid_qualified_name` returning `None`, `get_anonymous_identifier()`, `_get_unused_prefix` counting and its "prefix free" branch, empty `add_namespaces()` — **T13** (`TestNamespaceManagerEdges`)
- [x] `ProvBundle` API edges: `ProvBundle.bundles` raising `ProvException`, `.records`/`.identifier`/`.document`/`.default_ns_uri`/`get_registered_namespaces()`/`has_bundles()` on standalone bundles, `add_namespace` without URI raising, `mandatory_valid_qname` failure, `__eq__` early-outs — **T13** (`TestProvBundleEdges`, `TestRecordMiscProperties`)
- [x] `ProvDocument` bundle management errors: `bundle(None)`, `bundle()` with an unresolvable/duplicate identifier, `add_bundle` of a document with nested bundles, `update()` merging bundles with the same id and skipping the merge block when `other` has no bundles, `__eq__` bundle-mismatch early-outs, `unified()` with no bundles — **T13** (`TestAddBundle`, `TestBundleUpdate`, `TestDocumentEqualityAndUnification`)
- [x] `plot()` (2437–2485): format inference from filename and the unknown-format `ValueError` are covered (`TestPlot`, guarded by `skipUnless(shutil.which("dot"))`). The matplotlib-requiring interactive-display path (2463, 2470–2485) stays **deferred**: matplotlib is an optional `plot` extra not installed in this dev/CI environment, and `test_extras.py::test_plot_without_matplotlib_raises_helpful_error` (pre-existing) already covers the `ImportError`-message branch by mocking the import to fail — line 2463 specifically (`import matplotlib.pylab`) can't be reached without the real package.
- [x] `serialize()` to a file path via the tempfile+move path, and `deserialize()` `TypeError` when neither source nor content given — **T13** (`TestSerializeDeserializeEdgeCases`; natural neighbours of the T12 `read()` tests). The `shutil.move`-missing `else` fallback (2756-2757) stays **deferred**: `shutil.move` always exists on every supported interpreter, so `hasattr(shutil, "move")` is always `True`.

## src/prov/serializers/provrdf.py — 88% → 95% (T13)

- [x] `serialize()`/`deserialize()` datatype corner cases: `xsd:QName`, `xsd:gYear`, `xsd:gYearMonth`, base64Binary decoding — **T13** (`test_rdf.py::TestRDFSerializer::test_decode_xsd_qname_gyear_gyearmonth_round_trip`, `test_literal_rdf_representation_base64binary`). XMLLiteral decoding is a one-line passthrough (`value = literal`, no distinct branch to hit beyond the datatype check already exercised) — no separate test needed.
- [x] `literal_rdf_representation()`: langtag branch, base64 encode branch, `ValueError` on datatype-less literal — **T13** (`test_literal_rdf_representation_langtag`, `test_literal_rdf_representation_base64binary`, `test_literal_rdf_representation_without_datatype_raises`)
- [x] Decode robustness: "attributes not converted" warning path (already exercised by the pre-existing `RoundTripRDFTests::test_membership_*`/`test_json_to_ttl_match`, visible as `UserWarning` output in the suite), multi-valued unique-set walking — **T13** (`test_decode_multi_valued_qualified_relation_produces_cartesian_product`: a hand-authored qualified-`Usage` bnode with two `prov:entity` triples decodes into two separate `Usage` records via `walk()`'s cartesian product). `ValueError` on untransformable objects (line 669, `if obj is not None and obj1 is None: raise ValueError`) is **deferred**: traced `decode_rdf_representation()` exhaustively — for any non-`None` RDF term (`RDFLiteral`, `URIRef`, or the implicit `BNode`/other passthrough) it always returns a non-`None` value, so `obj1 is None` cannot occur for a real triple.
- [x] `ProvRDFException` "No document to serialize." (137) — **T13** (`test_serialize_without_a_document_raises`)
- [x] `encode_container()`'s `container=` parameter (defaults to `None` at every internal call site, so the "reuse a provided container" branch was previously dead code from the test suite's perspective) — **T13** (`test_encode_container_reuses_a_provided_container`, calling the method directly as an external caller would)
- [x] `decode_document()`'s `hasattr(content, "contexts")` `else` branch, for a plain `rdflib.Graph` rather than a `ConjunctiveGraph` — **T13** (`test_decode_document_without_contexts_uses_plain_graph_path`)
- [ ] Known-dead branches, confirmed unreachable via any value this library can construct (traced each, left **deferred**, do not write tests against dead code):
  - the `False and ...`-disabled block (~493, documented in-source as frozen 2.x behaviour scheduled for deletion in 3.0) and the unreachable `rec_type in [PROV_ACTIVITY]` relation branch (~456-459, also documented in-source: unreachable inside the `is_relation()` path)
  - `AnonymousIDGenerator.get_anon_id()` (67-70) and the `isinstance(value, pm.ProvRecord)` branch that would call it (482): `_auto_literal_conversion()` already converts any `ProvRecord` attribute value to its identifier before storage, so `encode_container()` never sees a raw `ProvRecord` value
  - the `IndexError` fallback at 335-336 (`record.formal_attributes[1]`): every relation subclass has ≥2 `FORMAL_ATTRIBUTES`, so the tuple always has a second element
  - the `elif isinstance(attr, pm.QualifiedName): ... else:` fallback at 418 and the `elif attr == PROV["plan"]:` branch at 410: for a formal `prov:plan` attribute, `attr in formal_objects` (line 405) always intercepts first: exercising 410 legitimately would require a non-`Association` relation carrying a generic extra attribute literally named `prov:plan`, which is a contrived construction with no realistic PROV-O source
  - the `except AttributeError` at 586-587: guards a `dict[obj]` lookup already proven present by the enclosing `if obj in PROV_CLS_MAP:`, so a `KeyError` (not `AttributeError`) would be the only possible failure, and it can't happen here either

## src/prov/serializers/provxml.py — 97% → 99% / provjson.py — 96% → 99% / provn.py — 87% → 100% (T13)

- [x] XML: "Non PROV element discovered" `ProvXMLException` (`test_xml.py::ProvXMLSerializerErrorsTestCase::test_non_prov_top_level_element_raises`), "No document to serialize." (`test_serialize_without_a_document_raises`, line 59), ignored-attribute warning (`test_unrepresentable_sub_element_attribute_warns_and_is_ignored`), "Could not create a valid QualifiedName" error (`test_xml_qname_to_qualifiedname_without_colon_or_default_ns_raises`) — **T13**. Two deep partial branches left unaddressed (not explicit checklist items, low value): 109->108 (a bundle reusing a namespace prefix already registered at the document level — needs a contrived multi-namespace nested-bundle fixture) and 398->409 (an XML sub-element with no attributes at all combined with one that has some, in the same `_extract_attributes` call).
- [x] JSON: `ProvJSONException` on multi-valued PROV attributes; encoder fallback for non-document objects; the "attribute touched but never explicitly set" defaultdict-skip (`if not values: continue`, found while writing these tests — accessing `.label`/`.value` auto-vivifies an empty attribute-set entry that the encoder must not emit); the third-or-later record sharing an identifier appending directly to the existing list — **T13** (`test_json.py::TestJSONSerializer`, 4 new tests). One deep partial branch left (not an explicit checklist item): 43->46 in `AnonymousIDGenerator.get_anon_id` (the "already cached" branch, needs the same anonymous record referenced twice during one encode pass).
- [x] PROV-N: "No document to serialize" error (22) — **T13** (`test_extras.py::TestProvNSerializer`). Module now 100%.

## src/prov/dot.py — 89% → 96% (T13)

- [x] `htlm_link_if_uri()` returns an `<a href>` for values with a `.uri` and `str(value)` otherwise — **T13** (`test_dot.py::HtlmLinkIfUriTest`; the function is unused internally by `prov_to_dot()` but is a public module-level helper)
- [x] Invalid `direction` argument falls back to `"BT"` — **T13** (`ProvToDotDirectionTest`)
- [x] `show_element_attributes=False` skips the attribute-annotation node (found while covering this module; every other test left it at its `True` default) — **T13** (`ProvToDotShowElementAttributesTest`)
- [x] `use_labels=True` rendering, `label != identifier` variant (the realistic case) — **T13** (`ProvToDotUseLabelsTest`). The `label == identifier` variant (dot.py:281-282) is **deferred**: `ProvRecord.label` always returns a plain `str`, `.identifier` is always a `QualifiedName`, and `str.__eq__`/`QualifiedName.__eq__` can never consider the two equal regardless of content (confirmed empirically: `entity.label == entity.identifier` is `False` even when their string forms match) — this branch is dead for any real record.
- [ ] Skipping relations with fewer than two endpoint nodes / empty-args records (356, 376) — **defer**: both branches require a `ProvRelation` with `FORMAL_ATTRIBUTES` shorter than the 2 entries every concrete relation subclass in `model.py` declares. The only way to construct such a record is instantiating the abstract base `ProvRelation` directly (bypassing every named subclass), and any document containing it fails earlier: `prov_to_dot()` unconditionally calls `bundle.unified()`, which reconstructs every record via `add_record()` → `record.get_type()`, and `ProvRelation.get_type()` raises `NotImplementedError` (no `_prov_type` set) before the drawing loop is ever reached. Confirmed by tracing the call chain; not worth a contrived monkeypatch-heavy test.

---

## Coverage measurement quirk (found during the audit)

`[tool.coverage.run] omit = ["*/tests*"]` does **not** exclude `src/prov/tests/` — all
28 test modules appear in the report and contribute ~2000 near-fully-covered statements,
lifting TOTAL from 87.4% (package only) to 91.2%. CI has always measured it this way, so
the `fail_under = 91` ratchet set by this task is consistent with what CI enforces, but:

- [x] Fix the omit pattern (e.g. `omit = ["*/prov/tests/*"]`) so the report reflects package code only, and re-base `fail_under` to the package-only number in the same commit — **T13**: changed to `omit = ["*/prov/tests/*"]`; re-measured before doing any further test work (see closing note below for the before/after numbers).

---

## Mutation-testing spike (mutmut, time-boxed)

Setup that worked, with no changes to project dependencies or `pyproject.toml`:

```bash
uvx --python 3.11 --from 'mutmut==2.5.1' mutmut run \
    --paths-to-mutate src/prov/graph.py \
    --runner 'uv run --no-sync python -m pytest -x -q src/prov/tests/test_graphs.py' \
    --tests-dir src/prov/tests/
```

Notes: mutmut 3.x was not attempted for the run itself because it requires `[tool.mutmut]`
config in `pyproject.toml` (off-limits for this spike) and copies sources into a `mutants/`
build dir that fights the src-layout; mutmut 2.5.1 with pure CLI flags worked first try.
It needs Python ≤3.11 (via `uvx --python 3.11`) because its `pony` dependency lags, and it
mutates files in place (restored automatically; keep a clean tree). Cache file
`.mutmut-cache` lands in the repo root — delete it, never commit it.

**Results for `src/prov/graph.py`** (119 lines, the suggested confined target):

| Metric | Value |
|---|---|
| Mutants generated | 25 |
| Killed | 15 |
| Survived | 10 |
| Wall-clock (scoped runner, warm uv cache) | ~5 s + ~3 s baseline |

Survivor analysis — every survivor was informative:

- 8 survivors (mutants 1, 13–19) sit in the inferred-element path of `prov_to_graph()`
  (dangling relation endpoints) — a genuine gap, now checklist items under `graph.py`/T12.
- 1 survivor (mutant 22) flips `and`→`or` in `graph_to_prov()`'s node filter — genuine
  gap, also a T12 item above.
- 1 survivor (mutant 4) mutates a type annotation (`|`→`&` inside `dict[...]`); with
  `from __future__ import annotations` it is never evaluated — an *equivalent mutant*,
  not a test gap.

**Recommendation: adopt in Phase 3, scoped — not as a CI gate.**

- Signal quality was excellent: 9 of 10 survivors mapped to real, previously unnoticed
  test gaps in a module that already had 83% line coverage; mutation testing found what
  coverage numbers hid.
- Cost is fine for small pure modules with a scoped runner (seconds), but it scales with
  (mutants × test-run time): `model.py` (~900 stmts) against the full 27 s suite would be
  hours, and mutmut 2.x cannot parallelise well.
- Therefore: run mutmut ad hoc in Phase 3 against one module at a time (next candidates:
  `identifier.py`, `serializers/provn.py`, `dot.py`) with a per-module `--runner`,
  harvesting survivors into test items. Do not wire it into CI, do not add it to
  project dependencies, and re-evaluate mutmut 3.x (or `cosmic-ray`) only if the ad hoc
  workflow proves too manual.

---

## T13 closing note (2026-07-05)

Every checklist item above is now either ticked or explicitly marked **defer** with a
one-line (or longer, where the reasoning wasn't obvious) rationale; none are left
unresolved.

**Coverage, before/after this task, `uv run coverage run -m pytest && uv run coverage
report -m` (branch coverage on):**

| Scope | Before T13 | After T13 |
|---|---|---|
| TOTAL as CI measured it pre-fix (inflated by `src/prov/tests/`, buggy omit) | 91.218% | n/a, omit fixed |
| Package-only TOTAL (honest, `omit = ["*/prov/tests/*"]`) | 91.458% | **97.42%** |

Per-module: `__init__.py`, `graph.py`, `identifier.py`, `serializers/__init__.py`,
`serializers/provn.py` all reached 100%; `model.py` 98%; `provjson.py`/`provxml.py` 99%;
`dot.py` 96%; `provrdf.py` 95% (the largest/most complex serializer, with several
confirmed-dead branches around 2.x-frozen RDF encoding quirks); `scripts/convert.py`
93% and `scripts/compare.py` 86% (unchanged from T11, already fully ticked there).

The new coverage ratchet is `fail_under = 97` (rounded down from 97.42%, comfortably
above the ≥95 target and the ≥93 floor), measured against the fixed omit pattern — i.e.
package code only, matching what `[tool.coverage.run] source = ["prov"]` +
`omit = ["*/prov/tests/*"]` actually reports. CI's 3.12 job (the only one that runs
`coverage report`) should land within a few hundredths of the same number; the ~0.4
point margin above the 97 floor absorbs the cross-interpreter drift noted in T10.

Test suite: 1084 passed, 17 xfailed (up from the 992 passed / 17 xfailed baseline
recorded before this task — all 92 new tests pass, none of the pre-existing ones were
modified in behaviour). `ruff check`, `ruff format --check`, and `mypy src` all clean.

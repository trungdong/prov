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
`main()`; **T12** = `prov.read()` auto-detection, `graph.py` branches, serializer
registry; **T13** = remaining gaps + ratchet toward ~95; **defer** = documented
won't-test (reason given inline).

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

- [ ] `read(source, format="json"|"xml"|"rdf")` with an explicit format deserializes via that serializer (and lower-cases the format string) — **T12**
- [ ] `read(source)` without a format auto-detects by trying each registered deserializer in turn — one test per detectable format (json, xml, rdf) — **T12**
- [ ] `read()` on undetectable/garbage input raises `TypeError` with the "specify the format" message after exhausting all serializers — **T12**
- [ ] `read()` accepts both a filename (`str`/`PathLike`) and a file object, matching `ProvDocument.deserialize` — **T12**
- [ ] Auto-detection swallows only `(TypeError, ValueError, AttributeError, KeyError)` from candidate deserializers — **T13** (behavioural pin: a deserializer raising something else, e.g. the PROV-N serializer's `NotImplementedError`, must propagate — document the intended behaviour when writing the test)

## src/prov/graph.py — 83% (missed: 88, 90–93, 116–117 + partial branches)

The only existing test is one round-trip over the example documents; the inference and
robustness paths are untested. The mutation spike (below) confirmed these as the real
gaps: 8 of the 9 non-equivalent surviving mutants live here.

- [ ] `prov_to_graph()` infers element nodes (with the correct inferred class, e.g. `ProvEntity` vs `ProvActivity`) for relation endpoints that have **no** corresponding element record in the document — **T12**
- [ ] `prov_to_graph()` skips a relation whose endpoint attribute is not in `INFERRED_ELEMENT_CLASS` (the `except KeyError: continue` path) and still processes subsequent relations (mutmut: `continue` → `break` survived) — **T12**
- [ ] `prov_to_graph()` skips relations where either endpoint QName is `None` — **T12**
- [ ] `graph_to_prov()` ignores graph nodes that are not `ProvRecord`s or whose `bundle` is `None` (mutmut: `and` → `or` survived) — **T12**
- [ ] `graph_to_prov()` ignores edges without a `"relation"` key in their edge data — **T12**

## src/prov/serializers/__init__.py — 91% (missed: 10, 39, 48)

- [ ] `serializers.get()` on an unknown format raises `DoNotExist` with the format name in the message, chained from `KeyError` — **T12** (the chaining itself is already tested by `test_extras.py::test_get_serializer_for_unknown_format_chains_key_error` from T9 — dedupe with it, one module owns it; only the format-name-in-message assertion is new)
- [ ] `serializers.get()` lazily populates `Registry.serializers` on first call (registry starts as `None`, holds exactly the four formats json/rdf/provn/xml) — **T12**
- [ ] `Serializer.serialize`/`.deserialize` abstract bodies (lines 39, 48) and the `if TYPE_CHECKING:` import (line 10) — **defer** (never executed at runtime by design; consider `pragma: no cover` in T13 instead of tests)

## src/prov/identifier.py — 87% (missed: 119, 141–146, 156–164)

- [ ] `Namespace(prefix, uri)` rejects an empty/whitespace URI with `ValueError` — **T13**
- [ ] `Namespace.contains()` for a str, an `Identifier`, a non-matching URI, and a non-str/non-Identifier argument (returns False) — **T13**
- [ ] `Namespace.qname()` returns a `QualifiedName` for a contained URI (str and `Identifier` inputs) and `None` for a non-contained or non-string input — **T13**

## src/prov/model.py — 90% (79 missed lines, 31 partial branches)

Large module; misses are scattered single lines, but they cluster into these behaviours:

- [ ] Literal handling: `parse_xsd_datetime` returning `None` on unparseable input; `parse_boolean` on `"true"/"1"/"false"/"0"/other`; `Literal.__eq__`/`__ne__`/`__hash__`; langtag forcing datatype to `prov:InternationalizedString` with a warning (lines 74–85, 167–194, 248–258) — **T13**
- [ ] Attribute validation errors: `ProvException` on a `None`-identifier record used as an attribute value, on unparseable datetime formal attributes, on `None` literal conversion, and on conflicting duplicate values for a single-valued PROV attribute (lines 480–537) — **T13**
- [ ] `ProvElement` creation without an identifier raises `ProvElementIdentifierRequired` (line 634) — **T13**
- [ ] Element convenience methods not exercised by `examples.py`: `ProvEntity.wasInvalidatedBy`, `ProvActivity.wasStartedBy`/`wasEndedBy` fluent wrappers, membership helper (712–713, 779–780, 861–908) — **T13**
- [ ] `NamespaceManager`: default-namespace-less construction, `get_namespace()` miss/hit, rename-map reuse of already-renamed namespaces, blank-node (`_:`) and non-str/Identifier inputs to `valid_qualified_name` returning `None`, `get_anonymous_identifier()`, `_get_unused_prefix` counting (1159–1181, 1219, 1320–1373) — **T13**
- [ ] `ProvBundle` API edges: `ProvBundle.bundles` raising `ProvException`, `.records`/`.identifier`/`.document` properties on standalone bundles, `add_namespace` without URI raising, `mandatory_valid_qname` failure, `__eq__` early-outs (1429–1517, 1570–1630) — **T13**
- [ ] `ProvDocument` bundle management errors: `bundle(None)`, invalid/duplicate bundle identifier, `add_bundle` of a document with nested bundles, `update()` merging bundles with the same id (2664–2704) — **T13**
- [ ] `plot()` (2437–2485): format inference from filename, unknown format `ValueError`, matplotlib `ImportError` message — **defer** for the interactive/matplotlib display path (needs matplotlib + a display; not in the test env); the filename-based save path and the `ValueError` are testable if graphviz is present, park under **T13** as optional
- [ ] `serialize()` to a file path via the tempfile+move path, and `deserialize()` `TypeError` when neither source nor content given (2756–2757, 2801) — **T12** (natural neighbours of the `read()` tests)

## src/prov/serializers/provrdf.py — 88% (40 missed lines, 18 partial branches)

- [ ] `serialize()`/`deserialize()` datatype corner cases: `xsd:QName`, `xsd:gYear`, `xsd:gYearMonth`, XMLLiteral, base64Binary decoding (221–231, 754–771) — **T13**
- [ ] `literal_rdf_representation()`: langtag branch, base64 encode branch, `ValueError` on datatype-less literal (754–771) — **T13**
- [ ] Decode robustness: `ValueError` on untransformable objects, "attributes not converted" warning path, multi-valued unique-set walking (690–730) — **T13**
- [ ] `ProvRDFException` "No document to serialize." (137) — **T13**
- [ ] Known-dead branches: the `False and ...`-disabled block (~549) and the unreachable `rec_type in [PROV_ACTIVITY]` relation branch (~493–506) — **defer** (documented in-source as frozen 2.x behaviour, scheduled for deletion in 3.0; do not write tests against dead code)

## src/prov/serializers/provxml.py — 97% / provjson.py — 96% / provn.py — 87%

- [ ] XML: "Non PROV element discovered" `ProvXMLException`, ignored-attribute warning, "Could not create a valid QualifiedName" error (59, 271, 377, 423) — **T13**
- [ ] JSON: `ProvJSONException` on multi-valued PROV attributes; encoder fallback for non-document objects (103, 254–259) — **T13**
- [ ] PROV-N: "No document to serialize" error (22) — **T13**

## src/prov/dot.py — 89% (missed: 183–187, 216, 281–287, 356, 376)

- [ ] `htlm_link_if_uri()` returns an `<a href>` for values with a `.uri` and `str(value)` otherwise — **T13**
- [ ] Invalid `direction` argument falls back to `"BT"` — **T13**
- [ ] `use_labels=True` rendering, both label==identifier and label!=identifier variants (281–287) — **T13**
- [ ] Skipping relations with fewer than two endpoint nodes / empty-args records (356, 376) — **T13**

---

## Coverage measurement quirk (found during the audit)

`[tool.coverage.run] omit = ["*/tests*"]` does **not** exclude `src/prov/tests/` — all
28 test modules appear in the report and contribute ~2000 near-fully-covered statements,
lifting TOTAL from 87.4% (package only) to 91.2%. CI has always measured it this way, so
the `fail_under = 91` ratchet set by this task is consistent with what CI enforces, but:

- [ ] Fix the omit pattern (e.g. `omit = ["*/prov/tests/*"]`) so the report reflects package code only, and re-base `fail_under` to the package-only number in the same commit — **T13** (do this *before* ratcheting toward 95, otherwise the target is measured against inflated numbers)

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

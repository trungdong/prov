# prov Test-Suite Redesign — Design

**Date:** 2026-07-06
**Status:** Maintainer-reviewed; decisions incorporated (2026-07-06). Authority for Tasks 10–12.
All three open questions resolved (see end): keep the 185 model self-tests as a `model` axis;
scruffy cases → `skip` (#217); fidelity cases → strict `xfail` (#77/#218); disabled XML
file-globs stay disabled.
**Scope:** Redesign `src/prov/tests/` around pytest-native idioms without losing coverage.
This document decides *what the target suite looks like* and *how we migrate to it while
proving parity*. It writes no test code and changes no tests — Tasks 10–12 execute against it.

## Context

The suite is plain `unittest` (`TestCase` subclasses, `assert*`, `expectedFailure`) run under
pytest. Its defining feature is **heavy multiple inheritance**: a large body of format-agnostic
test methods lives in mixin base classes and is re-run against each serializer by composing
those mixins with a `RoundTripTestCase`.

### Parity baseline (measured on this branch)

```
$ uv run pytest --collect-only -q 2>/dev/null | tail -1
1102 tests collected in 0.18s
```

**1102** is the parity baseline. Every migration PR is measured against it (§4).

Per-module breakdown (`pytest <module> --collect-only -q`):

| Module | Collected | Notes |
|---|---:|---|
| `test_model.py` | 252 | 185 shared-mixin + 67 model-specific |
| `test_xml.py` | 200 | 185 shared-mixin + 15 xml-specific |
| `test_rdf.py` | 196 | 185 shared-mixin + 11 rdf-specific |
| `test_dot.py` | 191 | 185 shared-mixin + 6 dot-specific |
| `test_json.py` | 190 | 185 shared-mixin + 5 json-specific |
| `test_extras.py` | 19 | |
| `test_scripts.py` | 18 | |
| `test_read.py` | 12 | |
| `test_identifier.py` | 10 | |
| `test_graphs.py` | 8 | |
| `test_cli_smoke.py` | 3 | |
| `test_public_api.py` | 3 | |
| **Total** | **1102** | |

### The shared-mixin body (185 tests, copied 5×)

`AllTestsBase` composes four mixins whose method counts are:

| Mixin (module) | `def test_*` methods | What it exercises |
|---|---:|---|
| `TestStatementsBase` (`statements.py`) | 147 | one document per PROV statement kind/variant → `do_tests` |
| `TestAttributesBase` (`attributes.py`) | 30 | 28 single-type-attribute datatypes + multi-attr + multi-value-attr |
| `TestQualifiedNamesBase` (`qnames.py`) | 7 | namespace inheritance + bundle flattening |
| `TestExamplesBase` (`test_model.py`/`test_rdf.py`) | 1 | loops over the 8 `examples.tests` documents |
| **Shared body** | **185** | |

`do_tests` is the single point of variation. `RoundTripTestCase.do_tests` serializes to
`self.FORMAT`, deserializes, and asserts equality; `RoundTripModelTest` overrides it to only
check self-equality (no serialization); the dot `SVGDotOutputTest` renders instead. The **same
185 methods are collected 5 times** — under `RoundTripModelTest` (model, no serialize),
`RoundTripJSONTests`, `RoundTripXMLTests`, `RoundTripRDFTests`, and the dot `SVGDotOutputTest`
— accounting for **925 of the 1102 collected tests (84%)**. `test_rdf.py` additionally
re-declares its own `AllTestsBase` whose only purpose is to wrap 17 of those inherited methods
in `@unittest.expectedFailure` (§2).

This is the redundancy the redesign targets: one canonical parametrized body, run once per
format, instead of five hand-composed inheritance stacks. The 185-test count is **not** waste —
each is a real assertion and must survive parametrization (§4 parity rule).

## 1. Assessment of every inherited pattern

Firm verdicts. This is a design authority, not a menu.

### `RoundTripTestCase` / `utility.py` — **REPLACE**

It is a `TestCase` base whose entire job is to funnel `do_tests` into a serialize→deserialize→
`assertEqual` cycle keyed off a class attribute `FORMAT`. In pytest this is a **fixture plus a
helper**, not a base class. Replace with a `roundtrip` fixture parametrized over format (§3) and
a module-level `assert_roundtrip_equivalent(doc, fmt)` helper. The `io.BytesIO` dance and the
`.format()`-not-f-string workaround (utility.py:41) are subsumed by the helper. Retire the
`DocumentBaseTestCase`/`RoundTripTestCase`/`FORMAT` machinery entirely once no module inherits
it.

### `attributes.py` / `statements.py` / `qnames.py` mixins — **ADAPT (convert, do not discard)**

These hold the real coverage (184 of the 185 shared tests) and must be preserved test-for-test.
But the *mechanism* (abstract mixins that only work when multiply-inherited with a
`RoundTripTestCase` providing `do_tests`) is replaced. Convert each mixin class into a **module
of plain parametrized test functions** that take the `roundtrip` fixture:

- `statements.py` → `test_statements.py`: the 147 methods become test functions (or a smaller
  number of `@pytest.mark.parametrize`-d functions where the bodies are near-identical, e.g. the
  scruffy families). Each still builds its document and calls `roundtrip(doc)`.
- `attributes.py` → `test_attributes.py`: the 28 `test_entity_with_one_type_attribute_N`
  collapse into **one** function parametrized over `attribute_values` (28 cases), preserving 28
  collected node IDs. `multiple` / `multiple_value` stay as two functions.
- `qnames.py` → `test_qnames.py`: 7 functions; the flattening ones parametrize over bundle count.

The `do_tests`/`new_document` indirection disappears — functions call the fixture directly.

### Per-format module duplication (`test_json` / `test_xml` / `test_rdf`) — **REPLACE with parametrization**

Today the shared body is physically re-instantiated per format by subclassing. Replace with a
single copy of the body parametrized over a `format` fixture spanning `json`/`xml`/`rdf` (§3).
What remains **per-format** is only the genuinely format-specific material:

- `test_json.py`: keep the 5 `TestJSONSerializer` tests (encoder internals, multi-valued-attr
  rejection, duplicate-identifier list handling) as functions.
- `test_xml.py`: keep the 15 XML-specific tests (c14n comparison via `compare_xml`, example
  6/7/8 serialization, `<prov:other>`, default-namespace edge cases, serializer error paths,
  the file-glob round-trip scaffold — currently **disabled**, see §4). `compare_xml` becomes a
  helper.
- `test_rdf.py`: keep the 11 `TestRDFSerializer` tests (`find_diff`, `test_json_to_ttl_match`,
  literal representation, decode edge cases) as functions.

The format-specific keepers are NOT parametrized — they assert format-specific bytes.

### Fixture-directory round-trips (`tests/json`, `xml`, `rdf`, `unification`) — **KEEP, re-mechanise**

The corpora are valuable and stay. Their **drivers** become parametrized:

- `tests/json/*.json` (currently round-tripped by `TestLoadingProvToolboxJSON` in `test_model`,
  and cross-checked against `tests/rdf/*.ttl|trig` by `test_json_to_ttl_match`) → a function
  parametrized over `glob("json/*.json")`, one node ID per file, so a single corrupt fixture
  names itself instead of failing an opaque loop. The large hard-coded `skip`/`skip_match`
  index lists in `test_json_to_ttl_match` become per-`pytest.param` `xfail`/`skip` marks keyed
  by filename, not by list-position integers (which silently drift when files are added).
- `tests/xml/*.xml` → the file-glob scaffold in `test_xml.py` (currently metaprogrammed with
  `setattr`, and commented out at lines 483–519) is rebuilt as `@pytest.mark.parametrize` over
  the glob. Whether to re-enable the disabled comparisons is a §4 decision, not automatic.
- `tests/unification/` → keep as-is under the (already pytest-friendly) `TestUnification` driver;
  low priority, migrate last.

### `examples.py` — **KEEP verbatim**

The 8 canonical documents (`examples.tests`) are the backbone of cross-format coverage and are
correct. Do not touch the builders. Only their consumer changes: `TestExamplesBase`'s single
`test_all_examples` loop becomes a function **parametrized over `examples.tests`** (8 node IDs ×
formats) so each example×format is an independently reported case instead of one loop that stops
at the first failure. Note the current loop no longer skips `datatypes` in `test_model.py`
(line 48) but the RDF/JSON copies still `continue` past it (test_rdf.py:75, 94) — the
parametrized version makes this skip explicit and per-format via a mark, removing the divergence.

### Bare document-equality assertions — **REPLACE with a diffing comparator**

`assertEqual(prov_doc, prov_doc_new)` (utility.py:46) on failure prints
`<ProvDocument> != <ProvDocument>` plus a dump of the whole serialized blob — you cannot see
*which record* differs. Every round-trip failure in this suite today is this useless diff.
Replace with a `pytest_assertrepr_compare` hook in `conftest.py` (§3) that, when two
`ProvDocument`s compare unequal under a plain `assert a == b`, emits the **set-symmetric-
difference of their records** (records in expected-only vs actual-only). This turns all 925
round-trip assertions into readable diffs for free, and it is why the target uses bare
`assert doc == reloaded` rather than a custom assert helper.

## 2. Re-justification of the 17 `expectedFailure` markers

All 17 live in `test_rdf.py` (`TestStatementsBase2`, `TestAttributesBase2`). I ran them as
normal tests to capture the real failure:

```
uv run pytest src/prov/tests/test_rdf.py::RoundTripRDFTests --runxfail -q
→ 17 failed, 168 passed
```

They fall into three root causes. **All 17 are kept** (they document real, still-open
behaviours). Their marker *type* now differs by root cause (maintainer decision):

- **scruffy (rows 1–14)** are a *fundamental* PROV-O representational limit → converted to
  **`pytest.mark.skip(reason="…#217")`**. A `skip` (not `xfail`) is correct because this is not
  a bug slated for a fix — it documents that the mapping cannot represent two same-identifier
  relations, and running the case would raise a genuine `ProvException`.
- **fidelity (rows 15–17)** are *fixable bugs* slated for 3.0 → kept as
  **`pytest.mark.xfail(strict=True)`**, so when the fix lands the marker flips XFAIL→XPASS and
  fails the run, forcing removal.

| # | Test | Real failure (captured) | Root cause | Disposition |
|---|---|---|---|---|
| 1 | `test_scruffy_generation_1` | `ProvException: Cannot have more than one value for attribute prov:time` | scruffy | **skip → #217** |
| 2 | `test_scruffy_generation_2` | same | scruffy | skip → #217 |
| 3 | `test_scruffy_invalidation_1` | same | scruffy | skip → #217 |
| 4 | `test_scruffy_invalidation_2` | same | scruffy | skip → #217 |
| 5 | `test_scruffy_usage_1` | same | scruffy | skip → #217 |
| 6 | `test_scruffy_usage_2` | same | scruffy | skip → #217 |
| 7 | `test_scruffy_start_1` | same | scruffy | skip → #217 |
| 8 | `test_scruffy_start_2` | same | scruffy | skip → #217 |
| 9 | `test_scruffy_start_3` | same | scruffy | skip → #217 |
| 10 | `test_scruffy_start_4` | same | scruffy | skip → #217 |
| 11 | `test_scruffy_end_1` | same | scruffy | skip → #217 |
| 12 | `test_scruffy_end_2` | same | scruffy | skip → #217 |
| 13 | `test_scruffy_end_3` | same | scruffy | skip → #217 |
| 14 | `test_scruffy_end_4` | same | scruffy | skip → #217 |
| 15 | `test_entity_with_one_type_attribute_8` | `AssertionError: <ProvDocument> != <ProvDocument>` — `Literal(10, XSD_DECIMAL)` round-trips to plain `10.0`, losing the `xsd:decimal` datatype | decimal fidelity | **xfail(strict) → #77** |
| 16 | `test_entity_with_multiple_attribute` | `AssertionError` — serialized blob shows `ex:v_8 10.0` (decimal collapsed) and int-subtype losses across the 28-value attribute set | datatype-set fidelity | **xfail(strict) → #218** (xref #77, #89) |
| 17 | `test_entity_with_multiple_value_attribute` | `AssertionError` — `"10"^^xsd:unsignedInt, "10"^^xsd:positiveInteger` in a value *set* fail to compare equal after round-trip | datatype-set fidelity | xfail(strict) → #218 (xref #77, #89) |

**Root-cause detail**

- **scruffy (rows 1–14) → skip, #217.** Each scruffy document deliberately adds **two relations
  sharing one identifier** (e.g. `ex:gen1`) with *different* `prov:time` values
  (statements.py:1198–1214). PROV-DM permits this; PROV-O cannot represent it — both times
  serialize onto the one qualified IRI, and on deserialization the decoder rebuilds a single
  record and rejects the second `prov:time` because formal attributes are single-valued
  (`ProvException`). This is a fundamental representational limit of the RDF mapping, not a
  bug on a fix path — so these are **skips**, not xfails, tracked by **#217**.
- **decimal fidelity (row 15) → xfail(strict), #77.** Index 8 of `attribute_values` is
  `Literal(10, XSD_DECIMAL)`; it re-reads as `10.0` and compares unequal. This is exactly
  **issue #77 ("Literal comparison for Decimal values", milestone 3.0.0)** — a fixable bug, so
  a strict xfail referencing #77.
- **datatype-set fidelity (rows 16–17) → xfail(strict), #218.** The multi-attribute documents
  pack the whole `attribute_values` list (many XSD numeric subtypes + plain-vs-`xsd:string`)
  into one entity/one `prov:value` set. RDF round-trip loses several datatype distinctions at
  once (decimal→double per #77; typed-vs-untyped string per **#89**;
  `unsignedInt`/`positiveInteger` collapse). Fixable in 3.0, tracked by **#218** (xref #77, #89).

### Issues filed: #217, #218

**#217** — *PROV-O round-trip cannot represent multiple same-identifier relations with
differing formal attributes ("scruffy" statements)*
> The 14 `test_scruffy_*` RDF round-trips fail because a document with two relations sharing an
> identifier but differing `prov:time` (or other formal attribute) collapses to one qualified
> IRI in PROV-O; deserialization then raises `ProvException: Cannot have more than one value for
> attribute prov:time`. Treated as an accepted PROV-O representational limitation: the 14 cases
> are `pytest.mark.skip`-ped referencing this issue. Reopen if a distinct-IRI-per-relation
> encoding is pursued.

**#218** — *RDF round-trip loses XSD datatype fidelity for multi-datatype attribute sets*
> `test_entity_with_multiple_attribute` and `test_entity_with_multiple_value_attribute` fail
> because an attribute set mixing XSD numeric subtypes and typed/untyped strings does not
> survive an RDF round-trip (decimal→double, `unsignedInt`/`positiveInteger` collapse,
> typed-vs-untyped string). Superset of #77 (decimal) and #89 (typed/untyped string). Slated for
> a 3.0 fix; the two cases are strict xfails referencing this issue. `test_entity_with_one_type_
> attribute_8` is the isolated decimal case, xfailed against #77 directly.

Net: **2 issues filed (#217, #218)**; row 15 maps to existing **#77**. No case is retired —
each has a real disposition (skip or strict xfail against a tracked issue), eliminating the
silent-bug status the plain `expectedFailure` decorators had.

## 3. Target pytest design

### `conftest.py` (fixtures + assertrepr hook) — the artefact Task 10 implements

```python
# src/prov/tests/conftest.py
import io
import pytest
from prov.model import ProvDocument

# Formats that support a full serialize -> deserialize -> compare round trip.
ROUNDTRIP_FORMATS = ("json", "xml", "rdf")
# The full target axis: the three round-trip formats PLUS a "model" target
# that constructs the document, exercises PROV-N generation, and checks the
# self-equality invariant WITHOUT serialization. The model axis is what keeps
# RoundTripModelTest's coverage alive (see Decision, §4): every shared
# statement/attribute variant proves prov.model supports that statement type
# and that get_provn() runs on it.
SHARED_TARGETS = ("model", *ROUNDTRIP_FORMATS)


def roundtrip_document(doc: ProvDocument, fmt: str) -> ProvDocument:
    """Serialize `doc` to `fmt` and read it back."""
    with io.BytesIO() as stream:
        doc.serialize(destination=stream, format=fmt, indent=4)
        stream.seek(0)
        return ProvDocument.deserialize(source=stream, format=fmt)


@pytest.fixture(params=SHARED_TARGETS)
def fmt(request) -> str:
    """The target under test — "model" or a serialization format.

    Parametrizes every shared statement/attribute/qname/example case, so each
    runs once per round-trip format AND once under the non-serializing model
    target.
    """
    return request.param


@pytest.fixture
def roundtrip(fmt):
    """Assert `doc` survives its target unchanged.

    For a serialization format: serialize -> deserialize -> `doc == reloaded`.
    For the "model" target: no serialization — assert self-equality and force
    PROV-N generation (proving model support for the statement + PROV-N output).
    Returns a callable so tests read `roundtrip(doc)`. On inequality the
    pytest_assertrepr_compare hook below renders which records differ.
    """
    def _check(doc: ProvDocument) -> ProvDocument:
        if fmt == "model":
            doc.get_provn()          # exercises PROV-N generation
            assert doc == doc        # self-equality invariant, no serialization
            return doc
        reloaded = roundtrip_document(doc, fmt)
        assert doc == reloaded  # readable diff via the hook below
        return reloaded
    return _check


def pytest_assertrepr_compare(config, op, left, right):
    """Readable diff for `assert doc == reloaded` on two ProvDocuments."""
    if op != "==" or not (
        isinstance(left, ProvDocument) and isinstance(right, ProvDocument)
    ):
        return None
    left_recs, right_recs = set(left.get_records()), set(right.get_records())
    only_left = left_recs - right_recs
    only_right = right_recs - left_recs
    lines = [
        "ProvDocument == ProvDocument failed:",
        f"  records: {len(left_recs)} left, {len(right_recs)} right",
        f"  in left only  ({len(only_left)}):",
        *(f"    - {r.get_provn()}" for r in sorted(map(str, only_left))),
        f"  in right only ({len(only_right)}):",
        *(f"    + {r.get_provn()}" for r in sorted(map(str, only_right))),
    ]
    return lines
```

*(The exact record-rendering — `get_provn()` vs `str(r)` — is a Task-10 implementation detail;
the contract is "show the symmetric difference of records", which is what today's blob dump
fails to do.)*

### Parametrized shared body — the `attributes` example

The 28 `test_entity_with_one_type_attribute_N` methods collapse to one function that keeps 28
node IDs and multiplies across the format fixture:

```python
# test_attributes.py
import pytest
from prov.tests.attribute_values import ATTRIBUTE_VALUES  # moved out of the mixin
from prov.model import ProvDocument, Namespace

EX = Namespace("ex", "http://example.org/")


@pytest.mark.parametrize(
    "value",
    [pytest.param(v, id=f"attr-{i}") for i, v in enumerate(ATTRIBUTE_VALUES)],
)
def test_entity_with_one_type_attribute(roundtrip, value):
    doc = ProvDocument()
    doc.entity(EX["et"], {"prov:type": value})
    roundtrip(doc)
```

The `examples` body becomes:

```python
# test_examples.py
import pytest
from prov.tests import examples

@pytest.mark.parametrize(
    "build", [pytest.param(fn, id=name) for name, fn in examples.tests]
)
def test_example_roundtrips(roundtrip, build):
    roundtrip(build())
```

### File I/O uses `tmp_path`

Every test that writes an intermediate file (`test_scripts.py`, `test_read.py`, XML file
round-trips) uses the `tmp_path` fixture instead of `tempfile.mkdtemp`/`shutil.rmtree`/manual
`os.path` bookkeeping (currently in `test_model.py` imports `tempfile`, `shutil`). In-memory
round-trips keep using `io.BytesIO` inside `roundtrip_document`; only real on-disk cases take
`tmp_path`.

### Per-format skip/xfail marks attach to parametrized cases

The 17 markers move from subclass method overrides to marks on the offending `pytest.param`.
Because each case only misbehaves **for `format == "rdf"`**, the RDF axis is made explicit for
the affected functions and the mark lives on the `rdf` param. Two marker types, per §2:

**Fidelity bugs (rows 15–17) → strict `xfail`.** These are fixable and slated for 3.0, so a
strict xfail forces the marker's removal once fixed:

```python
RDF_DATATYPE_XFAIL = pytest.mark.xfail(
    reason="RDF loses XSD datatype fidelity across a mixed attribute set — issue #218",
    strict=True,
    raises=AssertionError,
)

@pytest.mark.parametrize("fmt", [
    "model", "json", "xml",
    pytest.param("rdf", marks=RDF_DATATYPE_XFAIL),
])
def test_entity_with_multiple_attribute(fmt):
    doc = ...
    assert doc == roundtrip_document(doc, fmt)
```

Row 15 (`test_entity_with_one_type_attribute_8`) uses the same pattern referencing **#77**.

**Scruffy representational limit (rows 1–14) → `skip`.** These document a limitation with no fix
on the roadmap; running them would raise a genuine `ProvException`, so they are skipped (not
xfailed) on the `rdf` axis referencing **#217**:

```python
RDF_SCRUFFY_SKIP = pytest.mark.skip(
    reason="PROV-O cannot represent same-identifier relations differing "
           "by prov:time — accepted limitation, issue #217",
)

@pytest.mark.parametrize("fmt", [
    "model", "json", "xml",
    pytest.param("rdf", marks=RDF_SCRUFFY_SKIP),
])
def test_scruffy_generation_1(fmt):
    ...
```

Design commitments:

- **`strict=True`** on every fidelity xfail — an accidental fix flips XFAIL→XPASS and *fails* the
  run, so a silently-fixed bug can never rot behind a stale marker (the exact failure mode of
  today's bare `@expectedFailure`). Skips have no strict analogue by design: they mark
  *won't-fix* limitations, not pending bugs.
- **`raises=…`** on each xfail pins the *specific* known failure, so a *new, different* breakage
  surfaces as a real failure instead of being absorbed by the xfail.

These functions opt out of the module-wide `fmt` fixture and use their own explicit
`@pytest.mark.parametrize("fmt", [...])` (as above) so the mark stays local to the `rdf` case
while `model`/`json`/`xml` still run normally. This is the one place shared functions opt out of
the global `fmt` fixture.

### The `model` target, PROV-N, and dot

- **The `model` target is a first-class member of the shared `fmt` fixture** (`SHARED_TARGETS =
  ("model", "json", "xml", "rdf")`). Every shared statement/attribute/qname/example case runs
  under it, exactly as the three round-trip formats do. Under `model`, `roundtrip(doc)` performs
  no serialization: it forces `doc.get_provn()` (proving PROV-N generation works for that
  statement) and asserts the self-equality invariant. This preserves, test-for-test, the
  coverage that `RoundTripModelTest` provided today — 185 shared cases under a non-serializing
  target — without a fifth hand-composed inheritance stack. It is **not** retired (Decision, §4).
- **PROV-N (write-only) golden output.** The `model` target already exercises that
  `get_provn()` runs; where we additionally assert *specific* PROV-N bytes, a small
  `test_provn.py` holds golden-string checks over `examples.tests`. (PROV-N has no parser, so it
  is not a round-trip format.)
- **The dot `SVGDotOutputTest`** (renders each shared document to SVG) stays as a
  `pytest.importorskip("pydot")`-guarded parametrization over `examples.tests`; it is a
  render-smoke, not a round trip, so it lives in `test_dot.py`, not the shared body.

## 4. Migration plan

### Order

1. **Task 10 — JSON as pattern-setter.** Build `conftest.py` (fixtures + assertrepr hook),
   convert the shared body (`statements`/`attributes`/`qnames`/`examples`) to parametrized
   functions, and wire JSON through the new `fmt` fixture. Move `ATTRIBUTE_VALUES` and the
   example list into import-friendly modules. This PR establishes the pattern the rest copy.
2. **Task 11 — XML + RDF.** Add `xml` and `rdf` to `ROUNDTRIP_FORMATS`; port the format-specific
   keepers (`compare_xml`, `find_diff`, `test_json_to_ttl_match`, serializer error paths);
   attach the 14 scruffy **skip** marks (#217) and the 3 fidelity **xfail(strict)** marks
   (#77/#218) per §3. The disabled XML file-glob scaffold stays disabled (§4, Decision 3).
3. **Task 12 — the rest + retire scaffolding.** Migrate `test_model` model-specific tests,
   `test_extras`, `test_scripts`, `test_dot`, `test_graphs`, `test_read`, `test_identifier`,
   `test_cli_smoke`, `test_public_api`; delete `utility.py`, the mixin *classes*
   (`TestStatementsBase`/`TestAttributesBase`/`TestQualifiedNamesBase`/`TestExamplesBase`), and
   the `RoundTrip*Tests`/`AllTestsBase` composition once nothing references them.

### Parity procedure (mandatory, every migration PR)

```
uv run pytest --collect-only -q 2>/dev/null | tail -1   # before  (baseline 1102)
# ... perform the migration ...
uv run pytest --collect-only -q 2>/dev/null | tail -1   # after
```

Rule: **the collected total is identical before and after each PR, except for the explicit,
doc-authorised retirements/merges listed below (of which there are none that change the count —
see the table).** Because parametrization preserves one node ID per original case (`id=` on each
`pytest.param`) and the `model` self-tests are kept (not retired), a straight conversion is
count-neutral. Any delta blocks the PR until reconciled.

**Skip vs xfail tally shift (expected, Task 11).** Converting the 14 scruffy cases from
`expectedFailure` to `pytest.mark.skip` moves them from the *xfailed* bucket to the *skipped*
bucket in the pytest run summary. This does **not** change the collected count — skipped tests
are still collected — so the **1102 parity baseline holds**. What changes is the run tally:
before Task 11 the RDF module reports 17 xfailed; after, expect **3 xfailed** (the fidelity
cases, #77/#218) + **14 skipped** (scruffy, #217), with **0 unexpected xpass**. Task 11's parity
check must expect exactly this shift, not treat it as a regression. Run `uv run pytest -q` and
confirm: same pass count, xfailed 17→3, skipped +14.

Because a pure convert-and-reparametrize keeps every node, the running total stays at 1102
throughout — a migration PR that *reduces the collected count* without a listed authorisation is
a coverage regression by definition.

### Tests explicitly retired or merged (with reason)

| Case(s) | Action | Reason | Count effect |
|---|---|---|---|
| `DocumentBaseTestCase`, `RoundTripTestCase` (`utility.py`) | Retire (delete class) | Pure scaffolding, collects **0** tests | none |
| `RoundTripModelTest.test_*` self-equality copies (185, model target) | **KEEP** — becomes the `model` axis of the `fmt` fixture | Construction of all 185 variants proves `prov.model` supports every statement type, and `get_provn()` exercises PROV-N generation — genuine coverage, not just `doc == doc`. Preserved as a first-class `model` target (§3), not retired. | none (185 stay, now `…[model]` node IDs) |
| 28 `test_entity_with_one_type_attribute_N` | Merge → 1 parametrized fn (28 params) | Node IDs preserved (`attr-0..27`); pure mechanism change | none |
| `TestExamplesBase.test_all_examples` loop | Merge → 1 parametrized fn (8 params) | Per-example node IDs; also removes the `datatypes`-skip divergence between the model copy (no skip) and json/rdf copies (skip) | none (net +7 node IDs, still one per example×format) |
| `test_json_to_ttl_match` integer `skip`/`skip_match` lists | Re-key to per-`param` marks | Position-indexed skips silently drift when fixtures are added; filename-keyed marks do not | none |
| Disabled XML file-glob round-trip block (`test_xml.py:483–519`, commented `setattr`) | **Leave disabled** (Decision 3) | Currently collects **0** tests (commented out); re-enabling is a separate coverage *addition*, not part of a parity-neutral migration. Logged as a possible future coverage chore for the 2.4.0 window / conformance phase, out of scope for Tasks 10–12. | none (0→0) |

Every other case is a mechanical 1:1 conversion.

### Function-local import normalisation

During the rewrite, the ~23 function-local imports flagged in Phase 2 are **normalised to
module level** (top-of-file imports). They are in `test_rdf.py` (12: `provrdf` symbols, rdflib
`Graph`/`ConjunctiveGraph`/`RDF`/`URIRef`), `test_extras.py` (6: serializer classes, `builtins`),
`test_xml.py` (3: `provxml` symbols), and `test_cli_smoke.py` (2: `scripts.compare`/`convert`
mains) — plus the `pydot` import in `test_dot.py` stays function/module-guarded via
`importorskip`. Where an import must stay local because it exercises an optional dependency's
absence (e.g. the `builtins`-patching import-failure test in `test_extras.py`), it is left local
with a comment; otherwise all move to module scope.

## 5. Acceptance-criteria checklist

- [x] Assessment + verdict + reason for every inherited pattern (§1: RoundTripTestCase→REPLACE,
      mixins→ADAPT, per-format dup→REPLACE, fixture dirs→KEEP/re-mechanise, examples→KEEP,
      bare-equality→REPLACE with diff hook).
- [x] All 17 `expectedFailure` markers re-justified with captured real failures + dispositions
      (§2 table): 14→skip/#217, 1→xfail/#77, 2→xfail/#218. Issues #217 and #218 filed.
- [x] Target pytest design with code sketches: parametrized `fmt` fixture over the
      document×target matrix (incl. `model` axis), `tmp_path` for file I/O,
      `pytest_assertrepr_compare` diff hook, per-param `skip`/`xfail(strict=True, raises=…)`,
      and the `conftest.py` Task 10 implements (§3).
- [x] Migration plan: order (JSON→XML+RDF→rest), parity procedure (`--collect-only -q` before/
      after, total constant bar authorised retirements), retirement/merge list with reasons (§4).
- [x] Function-local imports normalised to module level (§4).
- [x] Baseline recorded: **1102** collected (§Context).

## Open questions for the maintainer — ALL RESOLVED

1. **~~Retiring the 185-test model self-equality copy.~~ RESOLVED — DO NOT RETIRE; keep as a
   `model` axis.** The construction of all 185 statement/attribute variants is genuine coverage
   (proves `prov.model` supports every statement type; `get_provn()` exercises PROV-N
   generation), so it is preserved as a first-class **`model` target** in the shared `fmt`
   fixture (`SHARED_TARGETS = ("model", "json", "xml", "rdf")`) — count-neutral, no −185. The
   retirement list (§4) no longer includes `RoundTripModelTest`; baseline stays **1102**.
2. **~~Issue A scope.~~ RESOLVED — scruffy = skip-with-reason.** The scruffy
   same-identifier-relation case is an accepted PROV-O representational limitation, tracked by
   **#217**; the 14 tests use `pytest.mark.skip(reason=…#217)`, not xfail. Fidelity bugs
   (#77/#218) remain strict xfails (fixable, slated for 3.0). Both issues are filed.
3. **~~Re-enabling the disabled XML file-glob round-trips~~ RESOLVED — leave disabled.**
   `test_xml.py:483–519` stays disabled for a parity-neutral migration; logged as a possible
   future coverage chore (2.4.0 window / conformance phase), out of scope for Tasks 10–12.

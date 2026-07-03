# Triage: behaviour bugs #34, #77, #89

Date: 2026-07-03 (roadmap step 15). All repros run against current `master`
(f540778) with `uv run python`.

Triage rule applied (2.x freeze): a fix qualifies for 2.x only if it changes
behaviour solely for inputs that previously FAILED (raised) or produced
corrupt/meaningless output. Anything that alters currently-"working" observable
output or equality semantics goes to 3.0.

ROADMAP.md currently lists all three under the 3.0 "behaviour-changing bug
fixes" batch, with #34 folded into the PROV-CONSTRAINTS unification rework
(roadmap step 36b). **This triage confirms all three placements.**

---

## Issue #34 — Merging of attributes of the same value but different types

**Problem.** Extra attribute-value pairs are stored in a Python `set`
(`ProvRecord._attributes`, `src/prov/model.py:289`, populated at
`src/prov/model.py:531`). Python considers `2 == 2.0 == hash(2) == hash(2.0)`
(and `1 == True`), so attribute values that are equal across Python types
silently collapse to a single value — whichever was inserted first. The same
collapse happens when `unified()` merges records sharing an identifier
(`_unified_records`, `src/prov/model.py:1654`).

**Repro (current master).**

```python
from prov.model import ProvDocument

d = ProvDocument()
d.add_namespace("ex", "http://example.org/")
e1 = d.entity("ex:a", [("ex:v", 2), ("ex:v", 2.0)])
print([(str(k), repr(v)) for k, v in e1.attributes])

e2 = d.entity("ex:b", [("ex:w", 1), ("ex:w", True)])
print([(str(k), repr(v)) for k, v in e2.attributes])

e3 = d.entity("ex:c", [("ex:v", 2.0), ("ex:v", 2)])
print([(str(k), repr(v)) for k, v in e3.attributes])

d2 = ProvDocument()
d2.add_namespace("ex", "http://example.org/")
d2.entity("ex:u", [("ex:v", 2)])
d2.entity("ex:u", [("ex:v", 2.0)])
print([(str(k), repr(v)) for k, v in next(iter(d2.unified().get_records())).attributes])
```

Output:

```
[('ex:v', '2')]
[('ex:w', '1')]
[('ex:v', '2.0')]
[('ex:v', '2')]
```

**Analysis.** Still reproduces exactly as reported (including satra's
`1`/`True` variant), and the surviving value is insertion-order dependent
(`e1` vs `e3`). Root cause is that native Python values are used directly as
set members, so Python's cross-type numeric equality/hashing — not PROV's
value-space semantics — decides deduplication. Under PROV, `ex:v=2`
(xsd:int/long) and `ex:v=2.0` (xsd:double) are distinct attribute-value pairs
and both should be retained; deciding when two literal values are *the same
term* is exactly the term-unification question that PROV-CONSTRAINTS answers
and that step 36b reimplements. A fix requires a typed value representation
(or a type-aware set key) in the attribute store, which changes record
equality, hashing, serialization output, and `unified()` results.

**Verdict: 3.0**, folded into the step-36b unification rework — the roadmap
placement is correct and this triage explicitly agrees with it. Not
2.x-fixable: although the current behaviour is lossy, every affected input is
accepted today and produces well-formed output that downstream users (e.g.
ProvStore) may rely on; the fix changes which attribute values a record
reports, and thus record/document equality, for inputs that do not fail today.

**What changes in 3.0 / who is affected.** Records constructed with
type-distinct but Python-equal attribute values will retain all values;
documents that previously compared equal (after collapse) may compare unequal;
serialized output gains attribute pairs; `unified()` follows PROV-CONSTRAINTS
merging rules and may reject merges instead of silently combining.

---

## Issue #77 — Literal comparison for Decimal values

**Problem.** `prov.model.Literal` coerces its value to `str` on construction
(`self._value: str = str(value)`, `src/prov/model.py:153`) and `__eq__`/
`__hash__` compare that string lexically (`src/prov/model.py:180-195`). So two
literals denoting the same xsd:decimal value compare unequal when their
lexical forms differ.

**Repro (current master).**

```python
import prov.model as pm
from prov.constants import XSD_DECIMAL

a = pm.Literal(10, datatype=XSD_DECIMAL)
b = pm.Literal(10.0, datatype=XSD_DECIMAL)
print(repr(a), repr(b), a == b)
```

Output:

```
<Literal: "10" %% xsd:decimal> <Literal: "10.0" %% xsd:decimal> False
```

The inequality propagates to record equality: two entities identical except
for `Literal(10, XSD_DECIMAL)` vs `Literal(10.0, XSD_DECIMAL)` compare
unequal, and both store the raw `Literal` (as `xsd:decimal` is not in
`XSD_DATATYPE_PARSERS`, `src/prov/model.py:96-104`, so
`_auto_literal_conversion`, `src/prov/model.py:415`, leaves it unconverted).

**Analysis.** Still reproduces. Root cause is lexical (string-space) rather
than value-space comparison, plus the absence of an `xsd:decimal` entry in
`XSD_DATATYPE_PARSERS`. The natural fix — parse `xsd:decimal` to
`decimal.Decimal` in `XSD_DATATYPE_PARSERS` and/or make `Literal.__eq__`/
`__hash__` value-space-aware for numeric XSD types — changes the Python type
exposed via `record.attributes` (from `Literal` to `Decimal`), serializer
output for decimal literals, deduplication inside attribute sets, and
document-equality/round-trip results. All of those are observable behaviours
of currently-accepted inputs.

**Verdict: 3.0** — confirms the ROADMAP.md placement. Not 2.x-fixable: a
`False` comparison result today is wrong-but-consistent semantics, not a
failure or corrupt output, and making the pair compare equal changes equality
and hashing for values users can already construct and compare. It should be
fixed alongside (or as part of the literal groundwork for) the step-36b
unification rework, since term unification needs the same value-space
comparison.

**What changes in 3.0 / who is affected.** Literals with the same XSD numeric
value but different lexical forms become equal (and hash together, so
attribute sets deduplicate them); `record.attributes` may expose native
`Decimal` values instead of `Literal` objects; serialized lexical forms may be
normalised. Affects any code relying on lexical inequality or on receiving
`Literal` instances for `xsd:decimal` attributes.

---

## Issue #89 — Internal representation does not distinguish literals with and without datatype

**Problem.** A literal parsed with an explicit `^^xsd:string` datatype and a
plain (datatype-less) literal are both stored internally as a bare Python
`str`, so on re-serialization the original form cannot be recovered.

**Repro (current master).**

```python
from prov.model import ProvDocument

ttl = """
@prefix ex: <http://example.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:a9 a prov:Entity ;
    ex:tag1 "hello"^^xsd:string ;
    ex:tag2 "hello" .
"""
d = ProvDocument.deserialize(content=ttl, format="rdf", rdf_format="turtle")
for r in d.get_records():
    for k, v in r.attributes:
        print(str(k), "->", repr(v), type(v).__name__)
print(d.serialize(format="rdf", rdf_format="turtle"))
```

Output (excerpt):

```
ex:tag1 -> 'hello' str
ex:tag2 -> 'hello' str

ex:a9 a prov:Entity ;
    ex:tag1 "hello"^^xsd:string ;
    ex:tag2 "hello"^^xsd:string .
```

The PROV-JSON path behaves the same way: `{"$": "hello", "type":
"xsd:string"}` and `"hello"` both deserialize to `str` and both re-serialize
as the bare JSON string `"hello"` (the explicit `type` marker is dropped).

**Analysis.** Still reproduces. The normalisation happens in
`_auto_literal_conversion` (`src/prov/model.py:415-439`): a `Literal` with
datatype `xsd:string` is parsed via `XSD_DATATYPE_PARSERS[XSD_STRING] = str`
and a datatype-less literal falls through to plain `str`, so both forms
converge on the same internal value; each serializer then applies its own
default form on output (the RDF serializer always emits an explicit
`xsd:string` datatype via `LITERAL_XSDTYPE_MAP`, PROV-JSON always emits the
bare form). Note that under RDF 1.1 — as stain pointed out on the issue —
`"hello"` and `"hello"^^xsd:string` are the *same* literal, so the
normalisation is semantically sound; what is lost is only lexical round-trip
fidelity, and the two serializers are inconsistent about which canonical form
they emit.

**Verdict: 3.0** — confirms the ROADMAP.md placement. Not 2.x-fixable: both
input forms are accepted today and produce well-formed, semantically correct
output, so any change (preserving the distinction internally, or picking one
canonical output form across serializers) alters observable serialization
output and potentially equality for currently-working inputs. The likely 3.0
resolution, subject to the pre-3.0 conformance audit, is to *document* the
RDF 1.1 normalisation as intended behaviour and make the serializers emit one
consistent canonical form (plain string, per RDF 1.1 guidance), rather than
to preserve the input distinction — preserving it would break value-space
equality and reintroduce the #34/#77 term-identity problem in reverse.

**What changes in 3.0 / who is affected.** Serialized output for string
literals becomes consistent across serializers (e.g. RDF output may drop the
explicit `^^xsd:string`); anyone doing byte-level comparison of serialized
output is affected; semantic (document-level) equality is unchanged.

---

## Summary

| Issue | Reproduces on master | Verdict | Landing place |
|---|---|---|---|
| #34 | Yes | 3.0 (behaviour change) | Step 36b unification rework, milestone 3.0.0 |
| #77 | Yes | 3.0 (equality-semantics change) | 3.0 behaviour-fix batch (literal value-space comparison, shared groundwork with 36b), milestone 3.0.0 |
| #89 | Yes | 3.0 (output-format change; likely "normalise per RDF 1.1 and document") | 3.0 behaviour-fix batch, informed by the conformance audit, milestone 3.0.0 |

Recommended milestone assignment (none of the three currently has one): all
three to the existing **3.0.0** milestone (GitHub milestone #4).

Side observation (out of scope for this triage): the #89 repro shows that RDF
deserialization imports all of rdflib's default namespace bindings (brick,
csvw, dc, …) into the resulting `ProvDocument`, which then appear in PROV-N
output. Worth a separate look during the serializer-focused roadmap steps.

---

## Draft issue comments (pending maintainer approval)

**#34:**

> Thanks for the report — this is confirmed and still reproduces on current
> master: because extra attributes are stored in a plain Python set, values
> like `2`/`2.0` (or `1`/`True`) collapse to whichever was inserted first,
> both at record construction and during `unified()`. Fixing it requires
> type-aware (value-space) handling of attribute values, which is exactly the
> term-unification question answered by W3C PROV-CONSTRAINTS, so this fix is
> folded into the unification rework planned for the 3.0 release — see
> [ROADMAP.md](https://github.com/trungdong/prov/blob/master/ROADMAP.md) and
> the roadmap tracking issue #181. It is deliberately not being changed in
> 2.x, since the fix alters record equality and serialized output for
> documents that load without error today.

**#77:**

> Confirmed, and still the case on current master: `Literal` stores its value
> as a string and compares lexically, so `Literal(10, XSD_DECIMAL)` and
> `Literal(10.0, XSD_DECIMAL)` compare unequal even though they denote the
> same xsd:decimal value. The fix is to compare (and parse) decimal literals
> in value space, but that changes equality/hashing — and therefore attribute
> deduplication, record equality, and round-trip results — for inputs that
> work today, so it is scheduled for the 3.0 release alongside the
> PROV-CONSTRAINTS unification rework rather than a 2.x patch. See
> [ROADMAP.md](https://github.com/trungdong/prov/blob/master/ROADMAP.md) and
> the roadmap tracking issue #181.

**#89:**

> Confirmed on current master: both `"hello"^^xsd:string` and plain `"hello"`
> deserialize to a bare Python `str`, so the original form is not recoverable
> on re-serialization (and the serializers differ in which form they emit —
> RDF output adds an explicit `^^xsd:string`, PROV-JSON drops the `type`
> marker). As noted above, under RDF 1.1 the two forms denote the same
> literal, so the internal normalisation is semantically sound; the plan for
> the 3.0 release is to resolve this as part of the batched
> behaviour-affecting fixes — most likely by documenting the normalisation
> and making all serializers emit one consistent canonical form, subject to
> the pre-3.0 conformance audit. See
> [ROADMAP.md](https://github.com/trungdong/prov/blob/master/ROADMAP.md) and
> the roadmap tracking issue #181.

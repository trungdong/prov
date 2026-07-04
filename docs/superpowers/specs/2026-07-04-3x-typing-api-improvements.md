# 3.x API improvements surfaced by the Phase-2 typing work

**Status:** proposal backlog for the 3.0 compatibility release (and 2.4.0 deprecation
warnings where noted). Collected 2026-07-04 while making the codebase pass
`mypy --strict` (Phase 2, Tasks 1–3) and moving to the Python 3.10 typing idioms.

**Why this document:** strict typing forced us to write down what the API actually
accepts and returns. In several places the honest annotation is `Any`, a wide
union, or a `# type: ignore` — not because the typing work was lazy, but because the
*runtime contract* is loose. Those places are API-design debt. We must not change them
in 2.x (frozen public API), so this list records what to change in 3.0, with rationale,
while the evidence is fresh. Items marked **[2.4.0-deprecate]** should get
`DeprecationWarning`s in the 2.4.0 "signposting" release per `ROADMAP.md`.

Ordering within each group is by expected impact.

---

## A. Attribute value model (the biggest win)

### A1. Replace `Any`-typed attribute storage with a closed `ProvAttributeValue` union

**Evidence:** `ProvRecord._attributes: dict[QualifiedName, set[Any]]`;
`get_attribute() -> set[Any]`; `attributes -> list[tuple[QualifiedName, Any]]`;
`args -> tuple[Any, ...]` (`model.py` ~289–360). Strict mypy could only be satisfied
by writing `Any`, which means `py.typed` (shipped in 2.3.0) gives downstream users
**no** checking on the single most-used part of the API.

**Change (3.0):** define one closed union and use it everywhere:

```python
type ProvAttributeValue = (
    str | int | float | bool | datetime.datetime
    | QualifiedName | Identifier | Literal
)
```

Storage becomes `dict[QualifiedName, set[ProvAttributeValue]]`; `get_attribute`,
`attributes`, `formal_attributes`, `extra_attributes` all return the union instead of
`Any`. `_auto_literal_conversion` gets the same return type, which will *prove* the
conversion funnel is total (today its "no conversion possible, return the original
value" fall-through can leak arbitrary objects into the store — see A2).

**Rationale:** the set of value types is already de-facto closed (it's whatever the
four serializers can round-trip); the type system just doesn't say so. Making it
explicit turns serializer crashes on exotic values into type errors at the user's
desk, and is a prerequisite for every other item in this group.

### A2. Make the literal-conversion funnel total — reject what can't round-trip

**Evidence:** `_auto_literal_conversion` (`model.py` ~410–437) ends with
`return literal` for anything it doesn't recognise, so `entity(..., {qn: object()})`
is stored happily and only fails later, inside a serializer, far from the user's bug.
The strict-typing pass had to type this path `Any -> Any`.

**Change (3.0):** after A1, raise `ProvException` (or a new `ProvValueError`) at
`add_attributes` time for values outside `ProvAttributeValue` (after the existing
coercions). Validation errors then point at the line that asserted the bad value.

**Rationale:** "parse, don't validate" at the boundary; every serializer stops
needing defensive handling for impossible values. Behaviour-changing → 3.0 only.

### A3. Fix the `value` / `label` accessor asymmetry

**Evidence:** `ProvRecord.value` returns `self._attributes[PROV_VALUE]` — the whole
**set** — while `label` returns `first(...)` (a single value) (`model.py` ~395–405).
The honest strict annotation for `value` is `set[Any]`, which is how the
inconsistency was noticed.

**Change (3.0):** `value -> ProvAttributeValue | None` (single value, like `label`),
and provide a uniform `get_values(name) -> frozenset[ProvAttributeValue]` /
`get_value(name) -> ProvAttributeValue | None` pair for the general case. Return
frozen sets so callers can't mutate record internals through the accessor
(`get_attribute` today hands out the live inner `set`, and even *creates* an empty
bucket on lookup because the store is a `defaultdict`).

**Rationale:** one obvious way to read attributes; no aliasing of internal state;
`defaultdict` read-side pollution goes away.

---

## B. Input coercion and the alias zoo

### B1. One coercion point: strict core, convenient edges

**Evidence:** the alias block at the top of `model.py` (`QualifiedNameCandidate`,
`EntityRef`, `ActivityRef`, `AgentRef`, `GenrationRef`, `UsageRef`,
`RecordAttributesArg`, `DatetimeOrStr`, …) exists because *every* layer — factories,
`new_record`, `ProvRecord.__init__`, `add_attributes`, even `get_attribute` — accepts
`str | Identifier | QualifiedName | ProvRecord` and re-coerces via
`mandatory_valid_qname`. Ten-plus wide-union signatures for what is one design
decision applied everywhere.

**Change (3.0):** keep the broad unions only on the ergonomic factory layer
(`ProvBundle.entity()`, `.wasGeneratedBy()`, the `ProvEntity` fluent methods — that
convenience is a feature). Below that line, `ProvRecord.__init__`,
`add_attributes`, and lookups accept **only** `QualifiedName` (and
`ProvAttributeValue`). Coercion happens exactly once, at the factory.

**Rationale:** honest one-type signatures in the core; validation failures surface at
the public entry point instead of deep inside `add_attributes`; equality/`__hash__`
never have to worry about un-normalised values; most of the alias zoo becomes
implementation detail of one module-level `_coerce_qname` helper.

### B2. Drop string datetimes from the core; drop `dateutil` with them **[2.4.0-deprecate]**

**Evidence:** `DatetimeOrStr` on every `time=`/`startTime=`/`endTime=` parameter,
funnelled through `_ensure_datetime`/`parse_xsd_datetime` → `dateutil.parser.parse`,
whose leniency accepts strings like `"5"` and whose failure mode inside
`add_attributes` is a `None` that turns into a generic `ProvException`.

**Change (3.0):** parameters become `datetime.datetime | None`. If string input stays
supported at the factory edge, restrict it to ISO-8601 via
`datetime.fromisoformat` (3.11+ parses the full format; our floor will allow it by
3.0). This is the same move `ROADMAP.md` already promises ("`python-dateutil`
replaced by the standard library") — this item adds the *typing contract* side of it.

**Rationale:** smaller dependency footprint (roadmapped), deterministic parsing, and
`time: datetime | None` is self-documenting where `DatetimeOrStr` is not.

### B3. Rename the misspelled `GenrationRef` alias

**Evidence:** `model.py` ~49: `GenrationRef = Union["ProvGeneration", ...]` (sic).
It is module-level and therefore technically importable, so under the 2.x freeze we
only add the correctly-spelled `GenerationRef` alongside; the typo name is removed
in 3.0.

**Rationale:** trivial, but it is exactly the kind of thing the freeze exists to
protect and 3.0 exists to fix.

---

## C. Class design the type checker objected to

### C1. `NamespaceManager` should wrap a dict, not be one

**Evidence:** `class NamespaceManager(dict)` (`model.py` ~1130) needed
parametrising as `dict[str, Namespace]` for strict mypy — which spotlighted that the
entire mutable `MutableMapping` interface (`__setitem__`, `pop`, `clear`,
`update`, …) is public API. None of those maintain the four parallel structures
(`_namespaces`, `_uri_map`, `_rename_map`, `_prefix_renamed_map`), so
`manager["ex"] = ns` silently corrupts prefix-renaming and URI lookup.

**Change (3.0):** composition — private `dict[str, Namespace]`, public read-only
`Mapping` view, mutations only through `add_namespace`/`add_namespaces`/
`set_default_namespace`. Also fixes `get_namespace(uri)`, which today does an O(n)
scan over `self.values()` reading the *private* `namespace._uri`, even though
`_uri_map` exists for exactly this lookup.

**Rationale:** classic inherit-vs-compose smell; invariants become enforceable, and
the class's real interface (five methods) becomes visible instead of being buried
under forty inherited dict methods.

### C2. Typed factories instead of `new_record` + per-call-site `# type: ignore`

**Evidence:** every factory ends in
`return self.new_record(PROV_X, ...)  # type: ignore` (~20 sites, `model.py`
1788–2403) because `new_record` dispatches through `PROV_REC_CLS[record_type]` and
can only promise `ProvRecord`. The strict pass converts these to `cast(...)`, which
is tidier but still unchecked.

**Change (3.0):** make the class, not the QName, the dispatch key:
`def _new_record(self, cls: type[R], identifier: ..., ...) -> R` with
`R = TypeVar("R", bound=ProvRecord)`; factories call
`self._new_record(ProvEntity, ...)`. `PROV_REC_CLS` stays for deserializers, which
genuinely map wire-format QNames to classes.

**Rationale:** deletes ~20 casts, and the checker then *verifies* that
`entity()` returns `ProvEntity` rather than being told so.

### C3. Honest return types for asserted-subtype conveniences

**Evidence:** `primary_source(...)` calls `derivation(...)`, adds an asserted type,
and does `return record  # type: ignore` because the runtime object is a
`ProvDerivation`, never the promised narrower type (`model.py` ~2307; same pattern
at ~2386).

**Change (3.0):** declare what actually comes back (`-> ProvDerivation`), or — if the
distinction matters — introduce real subclasses. Prefer honest annotations; the
subtype distinction lives in `prov:type` assertions, not the Python type system.

**Rationale:** a return annotation that the implementation can only satisfy with an
`ignore` is a documentation bug wearing a types costume.

### C4. Non-optional identifiers on elements

**Evidence:** `ProvRecord.identifier -> QualifiedName | None`, yet `ProvElement`
*requires* an identifier (`ProvElementIdentifierRequired` is raised without one). The
strict pass forced `None`-guards in `graph.py`/`dot.py` for a case that cannot occur
for elements.

**Change (3.0):** `ProvElement.identifier -> QualifiedName` (override with the
narrowed type); relations keep `QualifiedName | None`. Enforce in
`ProvElement.__init__` instead of a separate late check.

**Rationale:** encode the invariant where the checker can use it; downstream code
(ours included) drops a whole class of dead `is None` branches.

### C5. Decide bundle hashability explicitly

**Evidence:** `__hash__ = None  # type: ignore[assignment]` on `ProvBundle`
(`model.py` ~1649) — correct runtime behaviour (mutable container with value
equality must be unhashable), inexpressible cleanly in types.

**Change (3.0):** keep unhashable, but consider a `frozen()`/finalised state or
identity-equality for bundles as part of the PROV-CONSTRAINTS unification rework
(already roadmapped). At minimum, document the choice. Low priority; listed for
completeness because it will keep needing an `ignore` until decided.

---

## D. I/O surface

### D1. Split the dual-mode `serialize()` **[2.4.0-deprecate]**

**Evidence:** `ProvDocument.serialize(destination=None, ...) -> str | None`
(`model.py` ~2715): returns a string *or* writes to a stream *or* writes to a path
*or* — if the path looks like a non-local URL — prints
`"WARNING: not saving as location is not a local file reference"` and returns
`None`. The union return type and the untypeable print-path are both smells strict
mode made unmissable.

**Change (3.0):** two methods with single contracts —
`serialize(destination: IO[bytes] | str | os.PathLike[str], format=...) -> None` and
`serializes(format=...) -> str` (mirroring `json.dump`/`json.dumps`). The URL case
raises `ValueError`. Drop `bytes` paths from `PathLike` (no test exercises them; a
`str | os.PathLike[str]` parameter is what every modern API takes). Same split for
`deserialize` / `read`'s `source`/`content` duality.

**Rationale:** callers today must narrow `str | None` on every use; the
tempfile+move dance and the print-warning are 2012-era ergonomics. Overloads could
paper over the return type in 2.x, but the print-path behaviour needs 3.0.

### D2. `prov.read()` auto-detection by trial-and-error

**Evidence:** `prov.read()` tries each registered deserializer in turn, catching
exceptions as control flow; its parameter is correspondingly typed as the
everything-union. Not a strict-mypy failure per se, but the contract ("whichever
parser doesn't crash wins") is unstatable.

**Change (3.0):** sniff content (leading `{` / `<?xml` / RDF syntaxes) to choose a
parser, with the trial loop as fallback only; raise a dedicated
`ProvUnrecognisedFormat` carrying the per-format errors.

**Rationale:** deterministic behaviour when a file is *almost* valid in two formats,
and actionable errors instead of whichever parser happened to fail last.

---

## E. Module surface

### E1. Retire the `from prov.constants import *` re-export **[2.4.0-deprecate]**

**Evidence:** `model.py` does `from prov.constants import *`, so ~100 vocabulary
constants are re-exported from `prov.model` as public names. Strict mypy happens to
tolerate star-imports (it treats them as re-exports), which is the *only* reason this
didn't need fixing in Phase 2 — the surface is accidental, unauditable, and pins us
to keeping every constant name forever.

**Change (3.0):** explicit imports in `model.py`; users import vocabulary from
`prov.constants` (its documented home). 2.4.0 can't easily warn per-name without
module `__getattr__` tricks — a `ProvDeprecationWarning` note in docs/changelog may
have to do.

**Rationale:** the public-API smoke test currently has to guard names nobody chose
to publish. A deliberate surface is smaller, documentable, and testable.

### E2. Typing-only imports and `if TYPE_CHECKING:` — policy, not blanket adoption

**Evidence:** the strict pass added imports used only in annotations (e.g.
`QualifiedName` in `graph.py`, `Node`/`Graph` in `provrdf.py`). The natural question
is whether these belong under `if TYPE_CHECKING:`. Assessment: mostly no —
`model.py`'s alias zoo is *runtime-evaluated* (`QualifiedName | str` executes at
import), so its imports must stay real; `provrdf.py` already imports rdflib wholesale
at runtime, so guarding two extra names saves nothing; and no import cycle currently
forces the guard. The one honest use case is annotation-only imports in light modules
(`graph.py`'s `QualifiedName`), where the win is documentation ("this name is not
used at runtime"), not performance.

**Change (3.0):** adopt ruff's `TC` (flake8-type-checking) rule family once the 3.x
value-model work lands (after A1/B1, which decide which aliases remain runtime
objects), and let it mechanically police the split. Until then, don't hand-maintain
`TYPE_CHECKING` blocks — a half-applied policy is worse than none.

**Rationale:** `TYPE_CHECKING` guards pay off for expensive/optional/cyclic imports;
none of those pressures exist here today. Deferring to a lint rule makes the policy
enforceable instead of aspirational.

---

## F. Serializer layer (evidence from the provrdf strict pass, Task 2)

### F1. `Serializer.document` should not be `Optional`

**Evidence:** the `Serializer` ABC (`serializers/__init__.py`) stores
`document: ProvDocument | None`, so *every* `self.document.<anything>` in every
serializer is a strict-mypy `union-attr` error. provrdf alone carries four
`# type: ignore[union-attr]` sites for this one design choice; the other three
serializers only avoid it because their access patterns are simpler. At runtime a
serializer without a document only makes sense for `deserialize()`, which *produces*
the document.

**Change (3.0):** split the roles: serialization requires a document
(`__init__(self, document: ProvDocument)`), deserialization is a classmethod/factory
that returns one. Or, minimally, a non-optional `_document` property that raises a
clear error when unset. Either kills all four ignores at the root.

**Rationale:** one Optional in a base class radiates ignores through every subclass
forever; the None state is not a real state of a *serializer*, it's an artifact of
one class serving two directions of I/O (cf. D1's serialize/deserialize split).

### F2. Delete provrdf's provably-dead code

**Evidence:** two spots the typing pass had to annotate *around* rather than fix
(deleting code was out of scope for a typing-only task):
- `provrdf.py:455-461` — a `rec_type in [PROV_ACTIVITY]` branch inside the
  `is_relation()` path. Unreachable (`ProvActivity` is an element, never a relation),
  and ill-typed if it ever ran (`QualifiedName in URIRef` raises `TypeError`); it now
  wears two `# type: ignore[operator]` with an explanatory comment.
- `provrdf.py:491` — `if False and isinstance(value, (URIRef, pm.QualifiedName)):`
  — explicitly disabled logic kept as a fossil.

**Change (3.0):** delete both (with a round-trip test run proving no fixture notices).

**Rationale:** dead branches cost every future reader the analysis we just paid;
the ignores now marking them are tombstones, not fixes.

### F3. Make the relation-identifier invariant explicit in `encode_container`

**Evidence:** in provrdf's relation-encoding path, `identifier` is `None`-able until
the qualifier/bnode block conditionally assigns it; three
`cast("URIRef | BNode", identifier)` sites then assert it's non-None where it's
passed to `container.add()`. The casts are correct today, but the invariant lives in
the reviewer's head — reorder the qualifier block and mypy stays silent while `None`
flows into rdflib.

**Change (3.0):** restructure so the invariant is structural: compute the identifier
unconditionally before the add-sites (or `assert identifier is not None` at the join
point), and drop the casts.

**Rationale:** a cast asserting "always set by this point" is the type-system
equivalent of a TODO; one assert converts a silent latent bug into a loud one.

### F4. Honest `None` contract for `valid_qualified_name` (feeds B1)

**Evidence:** `NamespaceManager.valid_qualified_name` is annotated as taking a
non-optional candidate but actually implements `if not qname: return None` — provrdf
passes `literal.datatype` (optional) into it via `valid_identifier`, needing a
`# type: ignore[arg-type]`. The signature and the behaviour disagree; strict mode
noticed.

**Change (3.0):** as part of the B1 single-coercion-point rework, give the coercion
helper an honest signature (`candidate: QualifiedNameCandidate | None ->
QualifiedName | None`) and a strict companion that raises instead of returning None
(most callers immediately treat None as an error anyway).

**Rationale:** every caller currently re-derives "can this be None?" from folklore;
two small functions with true signatures end that.

### F5. Retire `walk()`'s untypeable sentinel

**Evidence:** `provrdf.py:736-739` — `path: dict[Any, Any] = None
# type: ignore[assignment]`, with the "is this the first call?" test keyed on
`level == 0` rather than `path is None`. The idiom is a pre-annotations mutable-default
workaround that cannot be typed honestly; the strict pass had to keep the ignore
because switching the guard to `path is None` would (theoretically) change behaviour.

**Change (3.0):** internal helper — retype as `path: dict[Any, Any] | None = None`
with a `path is None` guard, or fold the recursion's seed into a small wrapper
function. Also parametrise properly once A1's value union exists.

**Rationale:** the current shape needs a permanent ignore *and* a paragraph of
explanation; the fixed shape needs neither.

---

## Out of scope here (already roadmapped elsewhere)

- Unification per PROV-CONSTRAINTS (`unified()` semantics) — `ROADMAP.md` 3.0 list.
- `pydot`/`networkx` behind extras; `rdflib` floor raise — `ROADMAP.md` 3.0 list.
- PROV-N parser, PROV-JSONLD — 3.1/3.2.

## Suggested sequencing

1. **2.4.0:** deprecation warnings for B2 (string datetimes), D1 (dual-mode
   serialize + URL print-path), E1 (star re-export, docs-level); add `GenerationRef`
   alias next to the B3 typo.
2. **3.0, first wave (mechanical):** B3 removal, C3 honest returns, C4 identifier
   narrowing, C2 typed factories, F2 dead-code deletion, F3 identifier invariant,
   F5 walk() sentinel — internal, low-risk, delete most remaining casts/ignores.
3. **3.0, second wave (design):** A1→A2→A3 as one arc (value model), then B1+F4
   (coercion point with honest None contracts), C1 (NamespaceManager), D1/D2+F1
   (I/O split and non-optional serializer document), E2 (TC lint rules last) — each
   needs a short design note + tests showing old vs new behaviour, per the roadmap's
   rule for behaviour-changing fixes.

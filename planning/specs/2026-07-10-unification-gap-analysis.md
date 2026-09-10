# Unification gap analysis — `unified()` vs PROV-CONSTRAINTS (roadmap step 30b)

**Status:** Complete (audited 2026-07-11, branch `audit/unification-constraints`).
**Authority for:** the 3.0 `unified()` reimplementation (roadmap step 36b).
**Umbrella issue:** [#253](https://github.com/trungdong/prov/issues/253).
**Characterization tests:** `src/prov/tests/test_unification_constraints.py` over the
vendored corpus `src/prov/tests/unification/constraints/` (provenance/licence in that
directory's README).

Spec: [PROV-CONSTRAINTS (W3C REC 2013-04-30)](https://www.w3.org/TR/prov-constraints/).
Constraint numbers below are the REC's; the relevant sections are §4 (terms,
substitution, unification), §6.1 (uniqueness and key constraints, Constraints 22–29),
and §7.2 (bundles and documents). The pre-existing hand-made fixtures
(`src/prov/tests/unification/*.json`, untouched by this audit) already cite these
numbers in their names (`...-PASS-c22`, `-c23`, `-c28`, `-c29`); the vendored
ProvToolbox corpus uses `<category>-successN`/`-failN` names instead and covers the
full rule surface, including cases 2.x gets wrong.

## 1. Spec baseline

### 1.1 Terms and unification (§4)

A PROV term is a constant identifier, a **placeholder `-`**, a literal value, or an
**existential variable**. Unification of two terms:

- constant/literal (including `-`) vs constant/literal: succeeds with the empty
  substitution iff they are **equal**, otherwise **fails** — in particular, `-` does
  *not* unify with a concrete identifier;
- existential variable vs anything: succeeds, binding the variable.

Omitted optional parameters are generally expanded to existential variables
("unknown"), but §5.1's expansion definitions leave `-` in specific positions
(derivation's activity/generation/usage, association's plan, delegation's activity,
start/end's trigger...) meaning "definitely nothing" — a constant that only unifies
with itself or a variable.

### 1.2 Merging and key constraints (§6.1)

Uniqueness constraints are enforced by **merging**: given two statements of the same
relation whose key fields are equal, unify corresponding parameters pairwise; on
success, replace both statements with one carrying the unified parameters and the
**union of the attribute lists**, and apply the substitution to the rest of the
instance; on failure, **constraint application fails and the instance is invalid**
(there is no valid normal form). The worked example (§6.1):
`activity(a, 2011-11-16T16:00:00, _t1, [a=1])` + `activity(a, _t2,
2011-11-16T18:00:00, [b=2])` → `activity(a, 2011-11-16T16:00:00,
2011-11-16T18:00:00, [a=1, b=2])`.

The key constraints:

- **Constraint 22 (key-object):** `id` is a KEY for `entity(id, attrs)`,
  `activity(id, t1, t2, attrs)`, and `agent(id, attrs)`.
- **Constraint 23 (key-properties):** `id` is a KEY for all eleven identified
  relations — `wasGeneratedBy(id; e, a, t, attrs)`, `used(id; a, e, t, attrs)`,
  `wasInformedBy(id; a2, a1, attrs)`, `wasStartedBy(id; a2, e, a1, t, attrs)`,
  `wasEndedBy(id; a2, e, a1, t, attrs)`, `wasInvalidatedBy(id; e, a, t, attrs)`,
  `wasDerivedFrom(id; e2, e1, a, g2, u1, attrs)`, `wasAttributedTo(id; e, ag,
  attrs)`, `wasAssociatedWith(id; a, ag, pl, attrs)`, `actedOnBehalfOf(id; ag2, ag1,
  a, attrs)`, `wasInfluencedBy(id; o2, o1, attrs)`.
  (Specialization/Alternate/Membership/Mention have no identifier and no key
  constraint.)
- **Constraints 24–27 (unique-generation / unique-invalidation / unique-wasStartedBy
  / unique-wasEndedBy):** the generation/invalidation events per (entity, activity)
  pair, and the start/end events per (activity, starter/ender-activity) pair, have
  equal identifiers — i.e. the key is *not* the identifier, and two records with
  distinct constant identifiers for the same pair make the instance invalid, while an
  anonymous record (existential identifier) merges into the identified one.
- **Constraints 28–29 (unique-startTime / unique-endTime):** an activity's
  `startTime`/`endTime` equals the time of its `wasStartedBy`/`wasEndedBy` event —
  a cross-record-type uniqueness constraint.

Related non-merging constraints exercised by the corpus's fail-cases: Constraint 50
(typing), Constraint 52 (impossible-specialization-reflexive), Constraint 55
(entity-activity-disjoint), the event-ordering constraints (§6.2), and the §5.1
definitions that make a placeholder in a mandatory position ill-formed.

### 1.3 Bundle scoping (§7.2)

Each bundle (named instance) and the toplevel instance are normalized and validated
**independently**: "there is no interaction between bundles from the perspective of
applying definitions, inferences, or constraints". Nothing ever merges across bundle
boundaries; a document is valid iff each instance is valid and bundle names are
distinct.

## 2. Current implementation

`ProvBundle._unified_records()` (`src/prov/model/bundle.py:384-414`): group records
by identifier via `_id_map`; for each identifier held by more than one record, copy
the **first** record and `add_attributes()` every other record's attributes onto the
copy; return the records with each same-id group replaced by its merged copy.
Records without an identifier, or whose identifier is unique, pass through untouched.
There is no term unification, no placeholder representation (an absent formal
attribute is simply absent), no type compatibility check, and no application of
Constraints 24–29.

One accident does reject some invalid merges: `ProvRecord.add_attributes`'s
formal-attribute cardinality guard (`src/prov/model/records.py:622-643`) raises a
generic `ProvException("Cannot have more than one value for attribute prov:X")` when
the merge would give a formal attribute two *different concrete* values. That is the
right outcome class for concrete-vs-concrete conflicts, but it is an undocumented
side effect with a misleading message (cardinality, not non-unifiability), and it
covers only that one conflict shape.

`ProvDocument.unified()` (`src/prov/model/bundle.py:1455-1480`) applies
`_unified_records()` to the document's own records, then calls
`bundle.unified()` on each sub-bundle and adds the results to the new document —
i.e. the toplevel instance and every bundle are unified **independently of each
other**, matching §7.2. Confirmed by test
(`test_document_unified_scopes_unification_per_bundle`): a document whose top level
and two bundles all assert `entity(e)` unifies each scope separately; b1's two
same-id records merge within b1 only, and neither b2 nor the top level absorbs
anything from another scope.

Both methods emit a `FutureWarning` (2.4.0 signpost) announcing the 3.0 rework.

## 3. Rule-by-rule gaps

Format per rule: spec statement → current behaviour → executed example → 36b
requirement. All examples were executed on this branch and are locked by
characterization tests in `test_unification_constraints.py`.

### 3.1 Term unification and the placeholder `-`

- **Spec (§4, §5.1):** `-` is a constant ("definitely nothing"); it unifies only
  with itself or an existential variable. A record asserting a concrete plan and a
  record asserting *no* plan, under the same identifier, cannot merge.
- **Current:** the model has no representation of `-` at all — deserializers drop
  the distinction (an XML/JSON absent attribute, whether the source meant `-` or
  "unknown", becomes an absent attribute), and the attribute union then treats
  absent-vs-concrete as trivially compatible.
- **Example (corpus `association-fail4` analogue, executed):**
  `wasAssociatedWith(assoc1; a1, ag1, pl1)` + `wasAssociatedWith(assoc1; a1, ag1, -)`
  → silently merges to `wasAssociatedWith(assoc1; a1, ag1, pl1)` (1 record). Spec:
  merge failure, instance invalid. Same shape: `delegation-fail4/5`,
  `derivation-fail1/2/3/4`, `generation-fail7`, `invalidation-fail7`, `usage-fail7`,
  `start-fail7`, `association-fail5` — 12 corpus fail-cases merge silently for this
  reason.
- **36b:** decide the placeholder story for the model (represent `-` distinctly
  from "omitted", or document that `prov` treats deserialized input as scruffy) and,
  wherever `-` is representable, make placeholder-vs-concrete unification raise the
  documented merge-failure exception. This interacts with the §5.1 expansion rules
  (which positions default to `-` vs an existential) — 36b must implement that table.

### 3.2 Constraint 22 (key-object): entity / activity / agent

- **Spec:** same-id element statements merge; merging fails if formal parameters
  (activity's `startTime`/`endTime`) hold different concrete values.
- **Current:** attribute union; a concrete `startTime` conflict trips the
  cardinality guard (accidental rejection, undocumented generic exception); extra
  attributes union (correct — the spec unions attribute lists).
- **Example (executed):** `activity(a1, 2011-11-16T16:00:00, -)` +
  `activity(a1, 2012-01-01T00:00:00, -)` → `ProvException: Cannot have more than one
  value for attribute prov:startTime` raised from inside `unified()`. Right outcome
  class, wrong API: the exception is the generic cardinality guard, undocumented for
  this purpose, raised mid-merge. Corpus: the compatible cases
  (`activity-success1..4`, `attributes-*-success*`) all merge correctly, e.g. the
  §6.1 worked example reproduces exactly:
  `activity(a, 2011-11-16T16:00:00, -, [ex:a=1])` + `activity(a, -,
  2011-11-16T18:00:00, [ex:b=2])` → `activity(a, 2011-11-16T16:00:00,
  2011-11-16T18:00:00, [ex:a=1, ex:b=2])` (executed;
  `test_compatible_partial_information_merges_like_the_spec_example`).
- **36b:** replace the accidental guard with explicit pairwise unification of formal
  attributes; merge failure raises the documented exception.

### 3.3 Constraint 23 (key-properties): the eleven identified relations

- **Spec:** same-id relation statements merge by pairwise unification of all formal
  parameters; any concrete-vs-concrete disagreement is a merge failure.
- **Current:** as 3.2 — concrete-vs-concrete conflicts accidentally raise the
  cardinality guard (25 corpus fail-cases across
  association/delegation/end/generation/invalidation/start/usage — the
  `CARDINALITY_GUARD_REJECTS` set in the test module); placeholder-vs-concrete
  conflicts merge silently (3.1); compatible merges union correctly.
- **Example:** `generation-fail2` (`wasGeneratedBy(gen1; e1, a1, -)` +
  `wasGeneratedBy(gen1; e2, a1, -)` with distinct concrete entities) →
  `ProvException: Cannot have more than one value for attribute prov:entity`.
  Versus `derivation-fail2` (`wasDerivedFrom(der1; e2, e1, a, -, -)` +
  `wasDerivedFrom(der1; e2, e1, -, -, -)`) → silent merge to
  `wasDerivedFrom(der1; e2, e1, a, -, -)` where the spec fails the merge (the
  second statement's `-` asserts *no* activity).
- **36b:** as 3.2, plus the placeholder handling of 3.1.

### 3.4 Constraints 24–27: uniqueness keyed on formal-attribute pairs

- **Spec:** e.g. Constraint 24: IF `wasGeneratedBy(gen1; e, a, _t1)` and
  `wasGeneratedBy(gen2; e, a, _t2)` THEN `gen1 = gen2`. Two *distinct constant*
  identifiers for the same (entity, activity) pair fail unification → invalid.
  An anonymous generation (existential id) merges into the identified one — the
  spec's §6.1 closing example normalizes `wasGeneratedBy(id1; e, a, -, [...])` +
  `wasGeneratedBy(-; e, a, -, [...])` into a single statement.
- **Current:** not implemented in either direction. `unified()` keys on the record
  identifier only: differently-identified duplicates pass through untouched (no
  rejection), and anonymous records never merge with identified ones (no
  normalization).
- **Examples (executed):** `generation-fail1` (`gen1` vs `gen1-other`, same pair)
  → 4 records in, 4 out, no error (spec: invalid). `generation-success7`
  (`gen1` twice plus one *anonymous* generation of the same pair) → the two `gen1`
  records merge, the anonymous one stays separate (3 generations in, 2 out; spec
  normal form: 1). So the gap is visible on the success side too: `unified()` does
  not reach the spec's normal form even for valid instances. Same families:
  `invalidation-fail1`, `usage-fail1` (also invalid under Constraint 50 — its
  entity/activity arguments swap types), `start-fail4`, `end-fail4`,
  `generation/invalidation/usage-fail5/6` (anonymous records with conflicting
  times), `mention-fail4` (PROV-LINKS' analogous unique-mention rule).
- **36b:** decide scope: a spec-complete `unified()` must apply Constraints 24–27
  (merging anonymous records and failing on distinct-id duplicates); alternatively
  36b documents `unified()` as Constraint-22/23-only and defers 24–29 to the #62
  validation engine. Either way the behaviour must be documented and deliberate.

### 3.5 Constraints 28–29: activity times vs start/end event times

- **Spec:** IF `activity(a2, t1, _t2)` and `wasStartedBy(_start; a2, _e, _a1, t)`
  THEN `t1 = t` (and the endTime dual). Conflicting concrete times → invalid.
- **Current:** not implemented — the constraint spans two *record types*, which an
  identifier-keyed union can never see.
- **Example (corpus `activity-start-fail1`, executed):** `activity(a1,
  2012-11-16T16:05:00, -)` + `activity(a1, -, 2012-11-16T17:05:00)` +
  `wasStartedBy(start1; a1, -, -, 2111-11-11T11:11:11)` → the two activity records
  merge (times compatible), the wildly different start-event time is never compared:
  3 records in, 2 out, no error. Spec: invalid.
- **36b:** same scope decision as 3.4.

### 3.6 Incompatible record types (Constraints 50 typing / 55 entity-activity-disjoint)

- **Spec:** `typeOf(e, entity)` and `typeOf(e, activity)` for the same identifier is
  an impossibility — the instance is invalid. Key constraints only ever merge
  statements of the *same* relation.
- **Current:** `_id_map` keys on identifier alone, so records of *different types*
  sharing an identifier are merged into a copy of whichever record came **first**;
  the other record's formal attributes are demoted to extra attributes on the wrong
  type.
- **Example (executed, `test_entity_and_activity_sharing_an_id_currently_merge_into_an_entity`):**
  `entity(thing)` + `activity(thing, 2011-11-16T16:00:00, -)` → one record:
  `entity(thing, [prov:startTime="2011-11-16T16:00:00" %% xsd:dateTime])` — an
  entity wearing an activity's start time as a literal. Reversing assertion order
  yields an activity instead: the merge result depends on record order.
- **36b:** same-identifier records of incompatible base types must raise the
  documented merge-failure exception (entity/activity disjointness at minimum;
  agent/entity and agent/activity overlaps are *permitted* by the spec — Constraint
  54 only forbids overlaps among entity/activity/generation/usage/... object kinds —
  so 36b needs the spec's exact compatibility table, not a blanket "same class"
  check).

### 3.7 Fail-cases outside merging scope (for completeness)

The corpus also contains fail-cases whose invalidity is *not* a merge failure:
mandatory-position placeholders (`attribution-fail1/2`, `communication-fail1/2`,
`influence-fail1/2`, `membership-fail1`, `mention-fail1/2/3`,
`specialization-fail1/2`, `association-fail6`, `delegation-fail6` — ill-formed under
the §5.1 expansion definitions; `prov` accepts them per the documented §2.8
permissiveness family in the findings doc), impossibility
(`specialization-fail3`, Constraint 52 reflexive) and ordering
(`specialization-fail4`, Constraints 45/46 cycle) violations. `unified()` passes all
of them through untouched today, and even a spec-complete 36b `unified()` would:
these belong to the #62 validation engine. They are characterized as silent passes
and must *remain* out of `unified()`'s documented scope (or 36b must say otherwise
explicitly).

## 4. Bundle scoping (§7.2)

- **Spec:** every bundle and the toplevel instance normalize independently; no
  cross-instance constraint application.
- **`ProvDocument.unified()` — conformant.** Confirmed by code reading
  (`bundle.py:1455-1480`: `_unified_records()` on the toplevel `_records` only —
  `_id_map` is per-bundle — then `bundle.unified()` per sub-bundle) and by test
  (`test_document_unified_scopes_unification_per_bundle`): sub-bundles are unified
  independently of the parent document and of each other, even when all scopes share
  record identifiers.
- **`flattened().unified()` — spec-invalid usage, worth calling out.** `flattened()`
  hoists every bundle's records into one instance, so the subsequent `unified()`
  merges across bundle boundaries — executed: a document whose top level, `b1`, and
  `b2` each assert `entity(e, [prov:label=...])` flattens+unifies to a single
  `entity(e, [prov:label="top level", prov:label="in b1", prov:label="in b2"])`.
  No PROV-CONSTRAINTS rule licenses this; two bundles describing different
  real-world things under the same local name are silently conflated. This is
  exactly what `test_unifying` (`src/prov/tests/test_model.py:83-97`) exercises over
  the `unification/*.json` fixtures (which are single-instance documents, so it
  happens to be harmless there). Characterized in
  `test_flattened_unified_merges_across_bundle_boundaries`; kept working in 2.x.
- **36b:** keep the per-bundle scoping of `ProvDocument.unified()`; document
  `flattened()` composition as outside PROV-CONSTRAINTS semantics (a deliberate
  "single-instance view" tool, not part of normalization).

## 5. Corpus import and characterization summary

153 files vendored from ProvToolbox (85 `-success`, 68 `-fail`; README in the corpus
directory records origin, licence, naming convention). Observed behaviour, locked by
`test_unified_corpus_characterization` — every non-raising case asserts the *exact*
post-`unified()` record count implied by the identifier-keyed union (one record per
distinct identifier per scope, plus every anonymous record unchanged: anonymous
records never enter `_id_map`, `bundle.py:469-475`, so not even exact anonymous
duplicates deduplicate); the formula matched the observed count for all 125
non-raising cases with zero deviations:

| Class | Count | Current behaviour |
|---|---|---|
| Parse failure (skip) | 3 | `bundle-fail1`, `bundle-success1`, `bundle-success2`: raw `UnboundLocalError` in `provxml._extract_attributes` on the `<prov:bundle>` container — **filed [#254](https://github.com/trungdong/prov/issues/254)** (new defect class: XML sibling of #228, with a second, silent-corruption mode where a previous sibling's value is reused; the files themselves are ProvToolbox-dialect, not XSD-valid PROV-XML) |
| Success, parseable | 83 | `unified()` succeeds on all; same-id merges union attributes; **but** anonymous records that Constraints 24–27 would fold in stay separate (normal form not reached, §3.4) |
| Fail, accidental rejection | 25 | concrete-vs-concrete formal-attribute conflicts raise the generic cardinality `ProvException` (`CARDINALITY_GUARD_REJECTS` set, §3.2/§3.3) |
| Fail, silent merge/pass | 42 | placeholder-vs-concrete merges (12, §3.1/§3.3), uniqueness-constraint violations untouched (§3.4/§3.5), mandatory-placeholder / impossibility / ordering cases untouched (§3.7) |

Every corpus case is asserted (pass) or skipped with a reason; nothing is hidden.

## 6. Requirements for step 36b (3.0)

1. **Documented merge-failure exception.** `unified()` merge failures raise a
   dedicated, documented exception type (the 2.4.0 `FutureWarning` already promises
   this); the accidental `add_attributes` cardinality guard stops being the
   rejection mechanism.
2. **Pairwise term unification of formal attributes** for same-id records of the
   same relation/element type (Constraints 22/23), replacing the attribute union
   for formal attributes; extra (non-formal) attributes keep set-union semantics
   (that part of current behaviour matches the spec's `attrs1 ∪ attrs2`).
3. **Placeholder semantics** (§3.1): decide the model representation of `-` vs
   "unknown" and implement the §5.1 expansion table; placeholder-vs-concrete
   unification fails.
4. **Type compatibility** (§3.6): same-id records of incompatible base types fail
   the merge, per the spec's object-overlap table (Constraints 54/55), not a naive
   same-class check.
5. **Scope decision for Constraints 24–29** (§3.4/§3.5): implement them in
   `unified()` (both the anonymous-record merges and the failure cases) or document
   `unified()` as key-constraint-only and defer to the #62 validation engine.
   Explicitly out of scope either way: ordering, impossibility, and
   mandatory-placeholder validation (§3.7).
6. **Bundle scoping stays per-instance** (§4 above); `flattened()` composition is
   documented as outside PROV-CONSTRAINTS semantics.
7. **Corpus flip:** the fail-cases in `test_unification_constraints.py` covered by
   the chosen scope flip from characterizing silent merges/accidental exceptions to
   asserting the documented merge-failure exception; success-cases additionally
   assert the spec's normal form where Constraints 24–27 apply (anonymous-record
   folding, §3.4).

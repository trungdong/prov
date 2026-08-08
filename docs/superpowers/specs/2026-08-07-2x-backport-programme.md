# Back-porting 3.x Bug Fixes to the 2.x Maintenance Line — Design

**Date:** 2026-08-07
**Status:** **Complete, 2026-08-08.** Stages 0–2 shipped (2.5.2, 2.5.3). Stage 3 was declined
on the compatibility promise; see "Stage 3 outcome" at the end for what that means per item.
The programme is closed — this document is now a record, not a work queue.
**Scope:** Decides *which* fixes merged into `master` after the 2.5.1 tag are portable to
`origin/2.x`, *in what order*, and *under which release*. This document ships no code; each
stage below is executed as its own PR series.

## Context

`origin/2.x` (`e99fc6b`) is the 2.5.x maintenance line, still stamped `2.5.1`, carrying only
Dependabot commits since the tag. `master` (`67f0c77`) is 3.1.0. Between them sit 73 merged
PRs, 31 of which carry a user-visible fix.

The source layout is identical on both lines, so every fix lands in the same file. The contents
diverge substantially — `src/prov/serializers/provrdf.py` is 1010 lines on 2.x (pre-refactor,
monolithic) against 1808 on `master` after the PR #290 per-record-type dispatch decomposition.

### Parity baseline (measured on `origin/2.x`)

```
$ uv run --extra rdf --extra xml pytest -q
1160 passed, 22 skipped, 14 xfailed, 4047 warnings in 10.06s
```

**1160 / 22 / 14** is the invariant. Every stage below is measured against it, and any stage
that changes it must say so in its PR description with the reason.

Note that 2.x predates the extras split (PR #278): `dot` and `graph` are not optional
extras there, so `pydot`/`networkx` are unconditional dependencies and `--extra dot --extra
graph` is an error. Use `--extra rdf --extra xml` only.

CI on 2.x is live (`.github/workflows/CI.yml`, triggering on `[main, master, 2.x]`, matrix
3.10–3.14 + pypy3.11), so each stage gets the same gate as `master`.

### The policy contradiction this document resolves

`SECURITY.md` and `README.md` on `master` currently state that the most recent `2.x` release
receives **"security fixes only — no bug fixes, no new features."** That text landed in PR #359
on 2026-07-27. Stages 2 and 3 below are, by definition, bug fixes. Stage 0 amends the policy
first so the branch and the published support statement agree at every point in the programme.

## Classification method

Portability was assessed per PR by simulating the back-port without touching a working tree:

```
git merge-tree --write-tree --merge-base=$(git rev-parse <merge>^1) origin/2.x <merge>
```

Two systematic sources of *false* conflict were identified and must be discounted when reading
those results:

1. **Doc-file divergence.** 2.x has `HISTORY.rst`/`README.rst`; `master` converted both to
   Markdown in PR #358. Every back-port conflicts on them. Stage 0 removes this permanently.
2. **Stacking artifacts.** A PR conflicts in a source file when an *earlier* PR touching the
   same file is absent from 2.x, even though the later PR's own logic ports fine. #301
   (conflicts via #283/#284) and #310 (conflicts via #308/#309) are both this case, not genuine
   incompatibility.

Mechanical cleanliness is necessary but never sufficient — each fix was additionally read
against the actual 2.x code to confirm it targets a defect that exists there.

## Stage 0 — Preconditions

No fix ships until these three land. They are independent of each other and can be one PR each
or one combined PR.

### 0.1 Amend the support policy

Rewrite the support statement in `SECURITY.md` and `README.md` to admit backported bug fixes on
the 2.x line. The current table's `2.x` row reads "Security fixes only"; it becomes "Security
fixes, plus back-ported bug fixes until `2.6.0`".

**End condition (decided):** the widening is *scope-bounded, not time-bounded*. 2.x receives
back-ported bug fixes up to and including the 2.6.0 release described in this document, then
reverts to security fixes only. State plainly that new features and behaviour-breaking
corrections are never back-ported, so the widening cannot read as open-ended.

Note this amendment lands on `master` (that is where the published `SECURITY.md`/`README.md`
live), unlike 0.2 and 0.3 which land on `2.x`. Stage 0 therefore spans two branches and cannot
be a single PR.

### 0.2 Migrate `HISTORY.rst` to Markdown

Port `master`'s PR #358 conversion to 2.x for `HISTORY.rst` → `HISTORY.md`, matching `master`'s
heading structure and link style so the two changelogs stay diffable. None of the retained
entries change wording — the conversion is mechanical.

**Pre-2.0.0 entries (decided):** mirror `master` and split everything before 2.0.0 out into
`docs/changelog-archive.md`, rather than converting all 354 lines in place. This is a small
editorial change on a maintenance branch, accepted so that the two lines end up with the same
file structure and the overlapping 2.x entries stay directly diffable against `master`'s
`HISTORY.md`.

Do the same for `README.rst` → `README.md` in the same PR. Both files feed packaging metadata,
so check `pyproject.toml`'s `readme = "README.rst"` and update it, and confirm
`uv build` still renders the long description.

This is listed as a precondition rather than housekeeping because it removes the doc-conflict
noise from every subsequent stage, making `git merge-tree` output directly trustworthy.

### 0.3 Port the `find_diff` test-helper fix (PR #307, `111c107`)

`master`'s #307 fixed `find_diff()` in `src/prov/tests/test_rdf.py` being blind to
single-triple differences. It ships no library code — it is entirely test infrastructure.

It must land **before** any RDF fix in Stages 2 and 3, because those stages' verification
depends on `find_diff` actually detecting the differences they claim to fix. Porting RDF
changes while the comparison helper is blind would produce green runs that prove nothing.

### 0.4 Restate the support policy on the 2.x branch itself

0.1 amends the *published* policy, which lives on `master`. The 2.x branch carries its own
`SECURITY.md` and `README.md`, and both still describe 2.x as the only actively maintained
line with 1.x and earlier unsupported — text that predates the 3.0.0 release entirely.

Restate both to match what 0.1 publishes. Without this, 2.5.2 ships advertising a support
policy that contradicts `master`'s, which is worse than either statement alone. Must land
before the Stage 1 release, and after 0.2, since it edits `README.md` rather than
`README.rst`.

## Stage 1 — 2.5.2, security only

The one fix that is shippable under the *existing* policy, and the only genuinely urgent item.

Note the stage's independence is qualified in practice. The fix itself depends on nothing, but
shipping a 2.5.2 that carries a changelog entry requires 0.2 (which creates `HISTORY.md`), and
shipping one that does not contradict `master`'s published policy requires 0.4. If the release
is urgent enough to skip those, the fix can be cherry-picked onto `2.x` directly.

| PR | Merge | Issue | Fix |
|---|---|---|---|
| #302 | `4d8cab1` | #273 | Harden PROV-XML parsing against XXE and entity expansion |

**Why it matters on 2.x.** `origin/2.x:src/prov/serializers/provxml.py:269` and `:271` both call
bare `etree.parse(...)` with no parser argument, inheriting lxml's process-global default.
Both lines pin `lxml>=3.3.5`; lxml's own default for `resolve_entities` only became safe
(`'internal'`) in 5.0, and even on lxml ≥ 5.0 a co-loaded library can repoint the global default
via `etree.set_default_parser()`. Since `prov` is embedded in other applications (ProvStore),
this is a live exposure on 2.x, not a theoretical one.

**Port shape.** Verified zero source conflicts. Pure addition: one module-level
`_XML_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)`, plus `parser=_XML_PARSER`
on the two `etree.parse` call sites. Leave `huge_tree` at its default `False` so libxml2's own
entity-amplification limits stay intact. No behaviour change for legitimate documents — DTD
entity resolution and network fetches have no legitimate use in this library.

**Also port** the CI hardening from PR #271 (`41a2b9b`): pin third-party Actions to commit SHAs
and add top-level `permissions: contents: read` in 2.x's workflows. It is supply-chain
hardening in `.github/` only, but it belongs with the security release.

**Release gate.** Full matrix green at the 1160/22/14 baseline; a regression test asserting an
external-entity document does not resolve.

## Stage 2 — 2.5.3, strictly non-regressive fixes

Every fix here corrects behaviour that is *currently broken* without altering output for any
document that already works. That property is what makes the stage patch-safe, and it is the
admission criterion — a fix that changes already-valid output belongs in Stage 3, however small.

Ordered by dependency, then by risk.

| # | PR | Merge | Issue | Fix | Port effort |
|---|---|---|---|---|---|
| 2.1 | #353 | `dccff00` | — | `read()` populates the serializer registry lazily instead of rebuilding it per call | trivial |
| 2.2 | #287 | `e91746d` | #223 | Escape PROV-N metacharacters in qualified-name local parts | clean |
| 2.3 | #300 | `ea7b9d8` | #224, #289 | PROV-XML round-trips empty-string values and non-NCName attribute names | clean |
| 2.4 | #301 | `e64b794` | #228 | PROV-JSON deserializer raises `ProvJSONException` on malformed input | hand-apply |
| 2.5 | #310 | `41eae62` | #294 | Qualified names ending in a PROV-N metacharacter round-trip through PROV-O | hand-apply |
| 2.6 | #308 | `8870cad` | #299 | Decode `prov:startedAtTime`/`endedAtTime` on qualified Start/End into formal `prov:time` | small rewrite |
| 2.7 | #291 | `48738dc` | #250, #226 | Anonymous qualified nodes carry their influencer property | small–moderate rewrite |
| 2.8 | #309 | `3f1fe8c` | #303 | Reconcile anonymous Communication/Attribution/Influence relations on RDF decode | moderate rewrite |

### Notes per item

**2.1 (#353)** — `origin/2.x:src/prov/__init__.py:68` calls `Registry.load_serializers()`
unconditionally on every `read()`, discarding and rebuilding the registry, while
`prov.serializers.get()` already guards with `if Registry.serializers is None`. One-line guard;
no observable behaviour change.

**2.2 (#287)** — Verified zero source conflicts across `identifier.py`, `model/bundle.py`,
`model/records.py`. The safest fix in the programme: PROV-N is serialize-only here (no parser),
so this converts previously *invalid* output into valid output and touches nothing else.

**2.3 (#300)** — Verified zero source conflicts; `_extract_attributes`/`_ns` match 2.x's
pre-fix shape exactly. Legal-NCName names and non-empty values are byte-identical after the
fix.

**2.4 (#301)** — Conflicts in `provjson.py` only because #283/#284 touched that file on
`master` first and are excluded from this stage. The new guards (`_expect_json_object`,
`_json_record_elements`, two try/excepts) sit in regions those PRs never touch. Hand-apply.
The only behaviour change is the exception *type* raised on malformed input — an error-path
contract change, which is why it sits at the boundary of this stage rather than in Stage 3.

**2.5 (#310)** — Conflicts only via #308/#309 ordering; port after 2.6. The fix is a
self-contained new `_resolve_iri()` helper, and both call sites it replaces exist byte-identical
on 2.x (`provrdf.py:345` and `:778`, both `graph.namespace_manager.compute_qname(...)`). Purely
additive crash fix — the previous behaviour was a `ValueError`.

**2.6 (#308)** — The bug is confirmed present on 2.x. `master`'s fix lives in the
`_DECODE_PREDICATE_REWRITES` dict introduced by PR #290; 2.x still has the pre-#290 flat
`if`-chain (~lines 875–880) with STARTER/ENDER special-casing but no time rewrite. Re-implement
as two branches following the existing pattern; the generic `unique_sets` duplicate handling
already covers the rest.

**2.7 (#291)** — Encode side: `master` depends on #290's `_encode_relation`/
`_encode_qualification_node` split, but the equivalent gate maps onto 2.x's monolithic
`encode_document` loop — the `used_objects.append(...)` call (~line 492) and the generic
`if value is not None and attr not in used_objects:` emission loop already exist and will pick
up the un-consumed influencer attribute. Decode side: ~10 lines adapting `state.formal_attributes`
to 2.x's local dict at the `"actedOnBehalfOf"/"wasAssociatedWith"` branch (~line 843).

Note this **adds triples** to RDF output for anonymous qualified nodes. It is admitted to Stage 2
on the grounds that the previous output was non-conformant with the PROV-O qualification tables
— the added triples are required, not optional. If review disagrees, move it and 2.8 to Stage 3.

**2.8 (#309)** — Depends on 2.7 landing first; both touch the same qualifier-disambiguation
block. The duplicate-record bug is confirmed present on 2.x, but 2.x special-cases only
delegation/association, so attribution/communication/influence currently fall through to the
generic `else: getattr(bundle, relation_mapper[pred])(subj, str(obj))` branch. Fixing means
three new `elif` branches — new code, not adaptation. Largest single item in the stage.

**Release gate.** Full matrix green; baseline unchanged except for tests added by each fix.
Each PR carries its own regression test ported from `master`'s corresponding test additions.

## Stage 3 — 2.6.0, output-changing conformance fixes

> **DECLINED, 2026-08-08 — not implemented.** Everything below is the plan as designed, kept
> for the record. Only 3B.1 (#345) shipped, and in an additive shape rather than the one
> described here. See "Stage 3 outcome" at the end of this document for the decision and the
> per-item reasoning. Do not execute this section.

Everything here changes output or decoded values for documents that already round-trip today.
That is why it cannot ride in a patch release.

**Semver note, stated plainly:** strict semver would call several of these major-version
changes. Shipping them in a 2.6.0 minor is a pragmatic maintenance-line call, justified on the
grounds that each corrects a documented non-conformance rather than changing a designed
behaviour. The mitigation is that 2.5.x remains available for consumers who need byte-stable
output, and 2.6.0 ships with upgrade notes enumerating every output change. If that trade is
unacceptable on review, the alternative is to leave Stage 3 unported and direct affected users
to 3.x.

### Stage 3A — fidelity corrections

| # | PR | Merge | Issue | Fix | Output change |
|---|---|---|---|---|---|
| 3A.1 | #282 | `7f85592` | #235, #249, #251 | Preserve asserted integer datatypes; magnitude-aware PROV-N numerics | Plain floats emit as full-precision `xsd:double` instead of `%g`-truncated `xsd:float`; out-of-int32 ints stop emitting as invalid bare literals |
| 3A.2 | #285 | `727fbfc` | #89, #77, #259 | One canonical literal form and value-space semantics | RDF output no longer decorates plain strings with `^^xsd:string`; `xsd:decimal` compares in value space; language tags compare case-insensitively |
| 3A.3 | #286 | `6ff32e0` | #218, #225 | RDF round-trip datatype fidelity and `xsd:double` precision | Mixed-datatype attribute sets survive deserialization; doubles emit at full precision instead of rdflib's 6-significant-digit form |
| 3A.4 | #296 | `5c10dab` | #96 | Bind bundle-local and default namespace prefixes into RDF output | Turtle/TriG uses declared prefixes instead of auto-minted `ns1:` fallbacks — cosmetic, semantically identical graphs |

3A.1 and 3A.3 both merge with zero source conflicts. 3A.2 needs a two-minute manual edit:
`master`'s `LITERAL_XSDTYPE_MAP` had already dropped its `int` entry via 3A.1, so the diff
context does not match 2.x's map — drop the `str: XSD["string"]` entry, leave `int: XSD["int"]`
alone. Order 3A.1 before 3A.2.

3A.4 needs a genuinely different implementation, not a port: `master`'s fix is written against
the rdflib `Dataset` API introduced by PR #279, while 2.x still uses `ConjunctiveGraph` +
`container.addN(bundle.quads())`, building each sub-bundle as an independent graph with its own
namespace manager. Same root cause (prefixes bound on a manager never merged into the parent);
fix with a `for prefix, uri in bundle.namespaces(): container.bind(prefix, uri, override=False)`
loop after the existing `addN` call.

### Stage 3B — additive API correction

| # | PR | Merge | Fix |
|---|---|---|---|
| 3B.1 | #345 | `90f5a4d` | Correct the misspelled `GenrationRef` type alias |

The typo exists on 2.x (`origin/2.x:src/prov/model/records.py:91`, plus four call sites in the
`wasDerivedFrom`/`wasRevisionOf`/`wasQuotedFrom`/`hadPrimarySource` signatures, re-exported from
`prov.model`). `master` fixed it as a hard rename with no back-compat alias — **do not port that
shape.** On 2.x, add `GenerationRef` as the correct spelling and keep `GenrationRef` as an alias
so existing annotations keep resolving. That makes this additive rather than breaking.

### Stage 3C — reclassified, needs a decision

Both were assessed NOT-PORTABLE, but *only* under the patch-release constraint that Stage 3
lifts. They become viable here, and are listed for an explicit maintainer decision rather than
folded in silently.

| # | PR | Merge | Issue | Why it was excluded, and what changes |
|---|---|---|---|---|
| 3C.1 | #283 | `08a3e64` | #244, #246, #256 | Needs `canonical_xsd_datatype()`, absent from 2.x — but 3A.1 supplies it. Remaining objection: PROV-JSON `"$"` becomes a string for *every* int/float, where 2.x emits a native JSON number. Broad wire-format change. |
| 3C.2 | #284 | `aab7fdd` | #168, #238 | No missing symbols; merges clean. Objection is compatibility only: QualifiedName-valued attributes emit `"type": "xsd:QName"` instead of 2.x's long-standing `prov:QUALIFIED_NAME`. Decode accepts both spellings, so only fresh output changes. |

Recommendation: take **3C.2** (decode stays backward compatible, so the blast radius is
consumers keyed on the emitted `type` string) and **hold 3C.1** (changing `"$"` from a JSON
number to a string affects essentially every numeric attribute and will break naive consumers
silently). If 3C.1 is taken, it must land after 3A.1.

### Stage 3D — migration-requiring fixes, isolated

Ported last, in their own PRs, each with an explicit upgrade note. These are correct fixes whose
change is visible to any existing consumer.

| # | PR | Merge | Issue | Fix | Migration impact |
|---|---|---|---|---|---|
| 3D.1 | #292 | `0fef491` | #258 | Emit `alternateOf` with PROV-DM argument order | **Reverses the RDF triple direction.** Previously-serialized 2.x data read back by fixed code, or vice versa, transposes `alt1`/`alt2`. Trivially small change (two one-line deletions at 2.x `provrdf.py` ~494 and ~832), disproportionately large consequence. |
| 3D.2 | #293 | `6980beb` | #288 | Decode `xsd:base64Binary` as base64 text | **Changes the decoded Python value from `bytes` to `str`.** One-line `.decode("ascii")` after `standard_b64encode(...)` (2.x ~line 320). Callers expecting `bytes` see a type change — though the previous `b'…'` repr wrapping could not round-trip through PROV-JSON anyway. |

Both need entries in the 2.6.0 upgrade notes naming the exact before/after, not just a
changelog line.

## Explicitly not ported

| PR | Issue | Reason |
|---|---|---|
| #323 | #34 | Typed attribute storage rework (`TypedValueSet`); explicit 3.0 breaking change threaded through every attribute accessor |
| #321, #322, #324, #326 | #253 | `unified()` raises `ProvUnificationError` where it silently merged. Mechanically and semantically clean against 2.x, but `master` gated it behind a `FutureWarning` as a deliberate break — an existing working call would start raising |
| #280 | #237 | Merges with zero source conflicts, but narrows accepted input: non-ISO date strings dateutil used to accept (`"Nov 7, 2011"`) now raise `ProvException` |
| #298 | #217 | Built on PR #290's dispatch helpers, and delivers only a clearer message for an error 2.x already raises — no functional fix to gain |
| #278, #279 | — | Extras split and rdflib ≥ 7 floor; dependency-contract changes, not fixes |
| #339 | — | Removes an `if False and ...` dead branch. Byte-identical on 2.x and zero-risk, but fixes no defect; maintenance branches do not take pure cleanup |
| #295, #306, #342 | #294, #341 | Hypothesis generation exclusions that *mask* defects rather than fix them. #341 remains open and unfixed on `master` |
| #271 (src portion) | — | Bandit/pylint cleanup; behaviour identical except under `python -O`. The CI portion ships in Stage 1 |
| #272, #277, #297, #305, #346, #347, #349, #351, #368, #281 | — | Test-only, docs-only, comment-only, refactors, or the additive PROV-JSONLD feature. Every "Fix" commit inside #368 touches only the new serializer |

## Execution rules

- One PR per numbered item, full matrix green before merge, no PR spanning stages.
- Each PR ports the corresponding regression tests from `master`'s PR alongside the fix. A
  ported fix without its ported test does not merge.
- Ordering constraints that are hard requirements: 0.3 before any RDF fix in Stage 2 or 3A;
  2.7 before 2.8; 3A.1 before 3A.2 and before 3C.1.
- Where this document says "rewrite" rather than "port", the PR description states what
  differed on 2.x and why the implementation diverges from `master`'s — so the two lines stay
  auditable against each other.
- Stage 1 is independent. If the programme stalls after review, 2.5.2 still ships.

## Open questions for review

1. **Stage 3 at all?** The alternative to 2.6.0 is leaving 2.x on Stage 1 + Stage 2 and pointing
   users needing conformance corrections at 3.x. Stage 3 is the largest share of the work and
   carries all of the migration risk.
2. **2.7/2.8 placement.** Both are admitted to Stage 2 on the argument that adding
   PROV-O-required triples corrects non-conformance rather than changing behaviour. Reviewer may
   reasonably move them to Stage 3A.
3. **3C.1 (#283).** Recommended to hold; confirm or overturn.

**Resolved 2026-08-07:** the 2.x support window is bounded by scope, not time — back-ported
fixes through 2.6.0, then security-only (see 0.1). The migrated 2.x changelog mirrors
`master`'s structure, archiving pre-2.0.0 entries (see 0.2).

**Resolved 2026-08-08:** question 1 is answered **no** — Stage 3 is declined and there is no
2.6.0. Question 3 is moot. Question 2 is settled by events: 2.7/2.8 shipped in 2.5.3 and no
Stage 3A exists to move them to. See below.

## Stage 3 outcome — declined, 2026-08-08

Stage 3 was planned, then declined by the maintainer before implementation, on the grounds
that it breaks the API-stability promise published in `ROADMAP.md` §"API-stability promise
for 2.x" (identical text on both branches):

> - Every documented name stays importable from its historic location.
> - No behaviour-changing bug fixes land in 2.x. Where a fix would alter existing output or
>   semantics, it is documented and deferred to **3.0**, so upgrading within 2.x is always safe.

Stage 3 was *defined* as "everything that changes output or decoded values for documents that
already round-trip today", so the promise excludes it almost by construction. This is the
alternative the Stage 3 preamble already named: leave it unported and direct affected users
at 3.x. The semver stretch argued for there was never reached — the blocker is the published
compatibility promise, which is a stronger commitment than semver alone and was not the
maintainer's to trade away quietly.

**One item survived and shipped:** 3B.1 (#345), because the 2.x port is additive rather than
a rename. Merged to `2.x` unreleased ([PR #390](https://github.com/trungdong/prov/pull/390));
its changelog entry sits under `## Unreleased` in `HISTORY.md` for whatever ships next.

### Per-item reasons for not porting

| # | PR | What it changes for a working document | Verdict |
|---|---|---|---|
| 3A.1 | #282 | PROV-N floats go from `%g`-truncated `xsd:float` to full-precision `xsd:double`; out-of-int32 ints gain explicit datatype suffixes; `Literal("42", XSD_LONG)` stops collapsing to `int` | Declined — output *and* decoded values |
| 3A.2 | #285 | RDF stops decorating plain strings with `^^xsd:string` (81 of 2.x's own `.ttl` fixtures carry it); `xsd:decimal` compares in value space; language tags compare case-insensitively | Declined — already listed in `docs/upgrading-3.0.md`'s "Behaviour-changing bug fixes" table as deferred to 3.0, so the promise had already committed to holding it |
| 3A.3 | #286 | `xsd:double` emits at full precision instead of rdflib's 6-significant-digit form; datatypes without a lossless collapse decode from the RDF term's lexical form | Declined — output *and* decoded values |
| 3A.4 | #296 | Turtle/TriG uses declared prefixes instead of rdflib-minted `ns1:` fallbacks, and renders a default namespace as `:local` | Declined, and the closest call. The RDF graph is isomorphic — identical IRIs, identical triples, round-trip equality untouched — so only byte-comparers see it. Declined on the strict reading: "existing output" means bytes |
| 3B.1 | #345 | Nothing — additive on 2.x | **Shipped**, PR #390 |
| 3C.1 | #283 | PROV-JSON `"$"` becomes a JSON string for every int and float, where 2.5.x emits a native JSON number | Declined. Was briefly taken during planning (overturning this document's hold recommendation), then moot once Stage 3 was declined |
| 3C.2 | #284 | PROV-JSON emits `"type": "xsd:QName"` instead of `prov:QUALIFIED_NAME`; `prov:QUALIFIED_NAME` literals resolve to `QualifiedName`s at assertion time | Declined — output and decoded values. The decode-widening half alone (also accepting `xsd:QName` on input) is close to additive, but it still changes what an already-parsing document decodes to |
| 3D.1 | #292 | Reverses the `alternateOf` RDF triple direction | Declined — the most visible break in the set |
| 3D.2 | #293 | `xsd:base64Binary` decodes to `str` instead of `bytes` | Declined — decoded value type |

### Consequences

- **No 2.6.0.** The back-port programme ends at 2.5.3.
- **`ROADMAP.md` needs no amendment.** Stage 3 would have contradicted the API-stability
  promise on both branches — an amendment Stage 0 never contemplated, since 0.1/0.4 covered
  only `SECURITY.md`/`README.md`. Declining Stage 3 leaves the promise intact and true.
- **The support-policy text now overshoots.** `SECURITY.md` and `README.md` on both branches
  promise back-ported bug fixes "until `2.6.0`" / "up to and including 2.6.0", written when a
  substantive 2.6.0 was expected. With no 2.6.0 coming, that wording should be revisited to
  say the window closed at 2.5.3. Not done here — it is a user-facing policy edit, separate
  from this record.
- **Users needing the conformance corrections go to 3.x**, which is exactly what the promise
  told them would happen.

# Test-suite audit rubric

The audit asks one question of each test function in `src/prov/tests/`. Does the test earn its place, or is it there only because it was there before?

The unit is the test function. A parametrised test is one unit, and each of its parameter axes is a separate question. `README.md` in this folder describes how an audit runs. This file holds the rules every layer of the audit follows.

## The two checks

A test stays as it is when it passes both checks.

1. **Reason.** The test pins a contract that someone can name. A contract is one of these:
   - a row on `docs/reference/conformance.md` or a rule of a PROV specification;
   - a promise of the public API (a documented behaviour, an exception class, a frozen name);
   - a tracked issue or advisory whose fix the test guards;
   - a compatibility fixture (for example, files written by an earlier release);
   - a settled ruling recorded in a spec under `planning/specs/`.
2. **Unique job.** A fault exists that this test catches and no other test catches. Name the fault in one clause.

## Verdicts

| Verdict | When to give it |
|---|---|
| `keep` | The test passes both checks. |
| `merge` | A sibling pins the same behaviour with different input. The functions become rows of one parametrised test, or the test moves to a shared module (`test_statements.py`, `test_attributes.py`, `test_qnames.py`, `test_examples.py`). Every input and every assertion stays. |
| `narrow` | The test is sound, but one parameter axis or several rows do not change the behaviour under test. Name the axis or the rows. |
| `delete` | Another named test fails whenever this test fails. Name that test. |
| `rewrite` | The test pins an incidental detail (exact message wording that no document promises, a private attribute, an internal call order) and not the contract, or it passes with and without the code it guards. Say what the assertion misses. The audit records it and does not act on it. |
| `query` | The test does a unique job, but no contract can be found, or the code it reaches is unreachable through the public API. The maintainer names the contract, or the test and its code go together in a separate change. |
| `protected` | The test is in a protected class below. Do not judge it. |

Give `delete` only when you can name the test that takes over the job. When in doubt between `delete` and `merge`, give `merge`. When in doubt between `merge` and `keep`, give `keep` with confidence `low`.

## Protected classes

Do not propose a change to these. Mark them `protected`.

- A test that asserts a known-lossy raise or skip: the PROV-O gap and the PROV-JSONLD Mention gap (C1 and C2 on the conformance page), `SCRUFFY_TARGETS`, `MENTION_TARGETS`.
- Every test in `test_public_api.py`.
- `test_read_auto_detect_with_broken_tell_degrades_to_no_rewind` and any test that pins the serializer registry order.
- `test_written_by_3_2_3.py` and `fixtures/written-by-3.2.3/`.
- The order and the content of `ATTRIBUTE_VALUES` in `attribute_values.py`, and of `examples.py`.
- `strategies.py` and `test_property_roundtrip.py`.

## Rules for reading the evidence

- Coverage shows that a line ran. It does not show that a test checked the result. A test whose arcs sit inside another test's arcs is a candidate, and you must still read both tests. Most of the suite's test functions cover no arc of their own.
- The round-trip tests and the Hypothesis property test run most of the package. They are never, on coverage alone, the test that takes over the job of a specific test. A specific test names its behaviour and gives a clear failure, and that has value.
- `provenance.tsv` has two reference columns. A reference in `text_refs` is a lead. It counts as a Reason only when the test's text, its first commit or the issue itself describes the test's input. A reference in `history_refs` comes from a commit message alone and often belongs to another change in that commit, so check it against the issue's title first.
- When an issue lists several input shapes as separate defects, each shape keeps its own test or row.
- A test that guards a tracked issue keeps its place unless a sibling guards the same issue with an assertion at least as strict.
- Two tests that reach the same code through different public entry points (for example a reader and the CLI) are not duplicates.
- An error-path test is a duplicate only when the sibling raises from the same statement for the same cause.

## Rules for each verdict

1. **A contract reached through a private name.** When the behaviour is a real contract and the test reaches it through a private function or class, give `keep` and name the private name in Note. Give `rewrite` only when the thing pinned is itself incidental.
2. **How close a takeover test must be.** A takeover test must give the code the same input shape as the candidate. These differences can hide a fault, so they block `delete` and block dropping a row: which attribute holds the value, a list against a single value, the list length, the order of items, the depth of a repeated key, a second key beside the first.
3. **When a row may go.** A row may go only when it differs from a kept row in the record type or the section name alone, and the source has no branch on that name between the entry point and the statement under test. A row with its own message format, its own branch or its own input shape stays.
4. **When separate functions merge.** Functions merge into one parametrised test when their bodies are the same apart from the input values and the expected values. The merged body has no branch on a parameter. Every input and every assertion of the originals stays, in its original form. When a merge needs a branch, the verdict is `keep`. When an existing parametrised test has the same body, prefer adding rows to it over a new function, as long as the result still passes rule 5.
5. **A merge must be better, not only shorter.** A reader finds the behaviour as quickly as before, a failure still names the case that broke, and the merged function does not mix behaviours that deserve their own names. A merge that saves lines and hides intent is a `keep`.
6. **Tests that assert only "does not raise".** Give `keep` when the test sits beside a rejecting rule and guards against over-rejection. Name the rule in Reason.
7. **A test in the wrong module.** A test that calls a different entry point from the rest of its module gets the verdict its content earns. Note the module it belongs in. The audit does not move tests.
8. **No removal without an attempted refutation.** A `delete`, a `merge` or a dropped row goes to the judge only after a verifier tried to show that something is lost. The verifier reports every fault that the candidate alone catches and says whether a maintainer could plausibly write it. A fault is plausible when a real edit to today's code could introduce it. A fault is contrived when it needs new code that has no purpose except to break the candidate. A plausible separating fault refutes the proposal.

## Ledger row

The classifier writes one row for each test function, in file order.

| Column | Content |
|---|---|
| Test | The function name |
| Items | The number of collected items |
| Pins | The behaviour the test pins, in one sentence, in terms the test itself shows (the call, the input and the expected result) |
| Reason | The contract and its source (issue number, conformance row, spec section, docs page), or `none found` |
| Sibling | The nearest test that covers similar ground, as `module::function`, or `-` |
| Verdict | One verdict from the table above |
| Confidence | `high`, `medium` or `low` |
| Note | For `merge`, `narrow` and `delete`: what to do, and the fault that stays covered. Otherwise empty |

For a `keep` or a `protected` that no later layer examines, the Pins and Reason cells become the register reason word for word. So neither cell says which internal code the input reaches, and neither says that the test alone catches a fault. Nobody has planted a fault to show either. An argument about the code belongs in the proposal, where the verifier tests it.

## The layers of judgement

Each module passes through these layers in order. A later layer reads everything the earlier layers wrote.

| Layer | Who | What it produces |
|---|---|---|
| 1. Evidence | Scripts | `provenance.tsv`, `coverage-nominations.tsv` and `item-arcsets.tsv` for the whole suite |
| 2. Classifier | Sonnet agent | The ledger: one verdict for each test function, and a proposal for each `merge`, `narrow` and `delete` |
| 3. Verifier | Sonnet agent in its own worktree | For each `delete` and each dropped row, the faults planted and whether the suite without the candidate catches them. For each `merge`, the merged test built as a patch, with proof that its inputs, assertions and covered arcs equal those of the originals |
| 4. Coverage and mutation check | Sonnet agent with coverage contexts and mutmut | For the proposals the verifier did not refute: the arcs in `src/prov` that only the candidates cover (there must be none), and whether any detected mutant becomes undetected (items deselected for a removal, the patch applied for a merge) |
| 5. Judge | Opus agent, read-only | The final list, with a ruling and a recorded reason for every proposal |
| 6. Maintainer | The maintainer | Accepts or amends the judge's list. Nothing changes in the suite before this |
| 7. Register | Script and a Sonnet agent | One row for each test function of the module in `register/`, with the ruling, the reason and a fingerprint. The script copies the classifier's row for a test no later layer examined, and the agent writes the rows a later layer ruled |

Rules for the judge:

- The judge rules on every proposal the classifier made, including the ones the verifier refuted. Each ruling comes with one reason a later reader can check against the code.
- The judge reads the tests and the source itself. It does not take the classifier's or the verifier's description as fact.
- A removal needs all four of these. The verifier found no plausible separating fault. The candidates cover no arc of their own. The mutation check found no newly undetected mutant. The judge can name the test or the rows that keep the behaviour pinned.
- A merge needs all three of these. The verifier found no lost input or assertion. The mutation check found no mutant that changed status. The judge confirms rules 4 and 5 from the patch.
- When the verifier called a separating fault contrived, the judge decides whether it is.
- The judge may keep a test that every earlier layer cleared, for example because an issue or a document promises exactly that input. It gives the source.
- The judge may flag a `keep` it doubts. It does not add a removal that has not been through the verifier.
- When in doubt, the judge rules `keep`.

## The register

`register/<module>.tsv` holds the standing ruling for each test function, so that a later audit judges only the tests that are new or changed.

| Column | Content |
|---|---|
| `function` | The test function |
| `ruling` | `keep`, `merged`, `narrowed`, `rewrite`, `query`, `protected` or `removed` |
| `ruled_by` | The layer whose ruling stands: `classifier` when no later layer examined the test, `judge` when the maintainer accepted the judge's ruling, `maintainer` when the maintainer ruled differently from the layer whose ruling would otherwise stand, or added the test. When the maintainer extends a ruling that stands, for example by adding a row to a judge-ruled merge, `ruled_by` keeps the layer whose ruling stands, and the reason says what the maintainer added and why |
| `confidence` | The classifier's confidence for a ruling no later layer examined, otherwise `-` |
| `audit_commit` | The commit at which the row's test, and the tests its reason names, were last confirmed. It is stamped after the change that applies the ruling is committed |
| `fingerprint` | A hash of the function's source and of its collected item ids. Empty for `removed` |
| `reason` | What the test pins and the contract behind it. A row a later layer ruled also gives the evidence for the ruling |

The fingerprint covers the function's own text and its collected item ids. A change to a module-level case list, a helper or a fixture that the test uses goes unnoticed unless the item ids change.

A register holds two kinds of row.

- **A row the classifier ruled** (`ruled_by` is `classifier`). No proposal touched the test and no later layer examined it. `scripts/register.py draft` copies its reason from the ledger's Pins and Reason cells. The row records what the test pins and the contract behind it. It records that the classifier, by reading, found no sibling that does the same job, and that is not proof. The register check does not follow the names in such a row, so a later change to the code that makes the test redundant goes unreported.
- **A row a later layer ruled** (`ruled_by` is `judge` or `maintainer`). A proposal touched the test, or the judge or the maintainer examined it. An agent writes its reason from the judge's table. The ruling depends on how the code is written, so the register check follows the code and the tests the reason names.

The registers of `test_json`, `test_read`, `test_provn_lexer`, `test_jsonld` and `test_statements` give their classifier rows the longer form, with code names. Those reasons were reviewed in their pull requests and stay as they are. The check no longer follows them.

Rules for every register row:

- Write the reason for a reader who has not seen the ledger.
- Cite the issue, the conformance row or the document that underpins the test, as `#532`, whenever one exists. A reader can then follow the reason to its source. Cite an issue only when its title or body describes the test's input. A reference that comes only from a commit message often belongs to another change in that commit.
- Write a follow-up for a later audit as a sentence that opens with `Later audit:`, for example a pair to send to the verifier. The register check lists those rows.
- A later audit that judges a row again empties its `audit_commit` and `fingerprint`, so that `stamp` anchors the row at the new commit. A row whose ruling stands keeps both. Without this, the check reports a re-affirmed "source moved" row again on every run.

Rules for a row a later layer ruled:

- Say what would go unnoticed without the test, or why nothing is lost without it.
- A claim about which code a test reaches, or that a test alone catches a fault, rests on a fault someone planted and ran, in the verifier's, the mutation check's or the judge's file or in the apply step's own run. Without one, name the fault the test guards and do not claim it is the only guard.
- Name in backticks every function or class the argument passes through, not only the first and the last, for example `_decode_time` (methods as `Class.method`). A module-level constant may stay in backticks, but name the function that applies it too. The register check compares each named definition with its text at `audit_commit` and flags the row when the code changed. It tracks only a function or a class under `src/prov`, outside the tests. A constant, a test helper, a standard-library name or a misspelt name matches nothing, and the check stays silent about it. A bare common word, such as `identifier`, matches every definition of that name and flags the row for unrelated changes, so write it without backticks. `check --names` prints what each row follows.
- Name a sibling, takeover or folded-in test as `module.py::function`, each one in full. The register check compares that test's text with its text at `audit_commit` and flags the row when it changed or was removed. It follows only `test_` functions in `test_*.py` modules, and ignores a test that did not exist at `audit_commit`, such as a function the same change folded in. A helper or a module outside the tests matches nothing.
- A test that was proposed for removal and kept records the fault that kept it. This stops a later audit from proposing the same removal.
- A `narrowed` row and a `merged` row say what went or what was folded in, and why nothing was lost.
- A `removed` row stays in the register with its reason, so that nobody adds the test back without reading it. It names the test that took over its job and the code the ruling rests on, so that the check reports the row when either changes.

`scripts/register.py check` sorts every test function into one of these groups.

| Group | Meaning | What a later audit does |
|---|---|---|
| Unchanged | The fingerprint matches. For a row a later layer ruled, no definition or test the reason names changed | Nothing. The ruling stands |
| Changed | The fingerprint differs | The test goes through the layers again |
| New | The function has no row | The test goes through the layers |
| Source moved | A row a later layer ruled, `removed` rows included, names a definition or a test that changed since `audit_commit` | The classifier reads the diff and answers one question: does it undo the recorded reason? For a `removed` row, a yes brings the test back |
| Gone | A row has no function and its ruling is not `removed` | Mark the row `removed` with the reason, or delete it when the test was renamed |

After the groups, the check lists the rows that still wait for someone to act: each row ruled `rewrite` or `query`, and each row with a `Later audit:` follow-up.

A new test that duplicates an old one is the test that fails the unique-job check, so an old ruling is not reopened because a test was added.

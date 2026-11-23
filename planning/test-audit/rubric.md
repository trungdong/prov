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
   - a settled ruling recorded in a spec under `planning/specs/`;
   - a convention in `docs/development.md`.

   A test's own docstring or a comment in the source is not a contract source. When nothing else names the behaviour, give `query`. A docstring on a source definition counts when a page under `docs/reference/` renders it.
2. **Unique job.** A fault exists that this test catches and no other test catches. Name the fault in one clause.

## Verdicts

| Verdict | When to give it |
|---|---|
| `keep` | The test passes both checks. |
| `merge` | A sibling pins the same behaviour with different input. The functions become rows of one parametrised test, or the test moves to a shared module (`test_statements.py`, `test_attributes.py`, `test_qnames.py`, `test_examples.py`) or into another module's parametrised test with the same body. Every input and every assertion stays. A test that only gains rows or functions in a merge also gets `merge`, with the incoming test as its Sibling. |
| `narrow` | The test is sound, but one parameter axis, several rows or an independent section of its body (a block with its own setup and assertions) does not change the behaviour under test. Name the axis, the rows or the section. A dropped section is a removal. The verifier and the mutation check run with the section patched out in place of a deselected item. |
| `delete` | Another named test fails whenever this test fails. Name that test. |
| `rewrite` | The test pins an incidental detail (exact message wording that no document promises and that does not tell one cause from another of the same class, a private attribute, an internal call order, object identity (`is`) that no document promises, such as the object a cache or a fast path returns) and not the contract, or it passes with and without the code it guards, for example because its input never reaches the branch its name claims. Say what the assertion misses. The audit records it and does not act on it. |
| `query` | The test does a unique job, but no contract can be found, or the code it reaches is unreachable through the public API. The maintainer names the contract, or the test and its code go together in a separate change. |
| `protected` | The test is in a protected class below. Do not judge it. |

Give `delete` only when you can name the test that takes over the job. When in doubt between `delete` and `merge`, give `merge`. When in doubt between `merge` and `keep`, give `keep` with confidence `low`.

When a sibling has the same input as a test and asserts less, give the test that asserts more `keep`. When the same classifier judges the sibling too, give the sibling `delete` with this test as the takeover, named in full as `module.py::function`. Otherwise, end this test's Reason with a `Later audit:` sentence that names the sibling as a `delete` candidate, with this test as the takeover.

When two tests each assert something the other does not, neither is a `delete`, because neither fails whenever the other fails. Give each of the two that this classifier judges `keep`, and name the other as its Sibling. They merge only when rule 4 allows it.

## Protected classes

A test is protected when it asserts a permanent limitation on the conformance page, pins a frozen compatibility promise, or belongs to the generated round-trip property. Do not propose a change to it. Mark it `protected`. A parametrised test is protected when any of its rows is. The list below names the current members. A test does not become protected because its rows come from a protected corpus. Only the corpus itself is frozen.

- A test that asserts a known-lossy raise or skip: the PROV-O gap and the PROV-JSONLD Mention gap (C1 and C2 on the conformance page), `SCRUFFY_TARGETS`, `MENTION_TARGETS`. Only C1 and C2 are permanent. A test that pins another caveat is judged like any other, with the caveat as its Reason.
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
- Two tests that reach the same code through different public entry points (for example a reader and the CLI) are not duplicates. An entry point is public when `test_public_api.py` freezes it or a page under `docs/reference/` documents it. A name in a module's `__all__` alone, such as `ProvNParser`, is a private name, and rule 1 of Rules for each verdict applies.
- An error-path test is a duplicate only when the sibling raises from the same statement for the same cause.
- A message substring that tells one cause of an exception from another is an assertion, not incidental wording, when the code raises the same class for more than one cause. Without it, a fault that sends the input to another check of the same class goes unnoticed.
- A row of a vendored corpus test may take over a hand-written test when it raises from the same statement for the same cause and asserts at least as much. A corpus row that raises nothing takes over under the same rules as any other test. The register check follows the corpus test's text, not its corpus files, so the `removed` row names the corpus file its takeover reads.
- An `assert_type` line, or another check that only mypy evaluates, is an assertion when the module is not on the mypy override list in `pyproject.toml`, because the mypy gate checks it on every pull request. Coverage and mutation testing cannot see it, so name the annotation it pins in Reason. A takeover must carry the same check.
- A warning filter is one of a test's assertions. A takeover, or the named takeovers together, must turn into an error every warning category that the candidate's filter does. A takeover whose filter catches only `ProvWarning` does not take over from a test that catches every category.

## Rules for each verdict

1. **A contract reached through a private name.** When the behaviour is a real contract and the test reaches it through a private function or class, give `keep` and name the private name in Note. Give `rewrite` only when the thing pinned is itself incidental. When no public call reaches the private code at all, give `query`.
2. **How close a takeover test must be.** An input difference between the candidate and the takeover blocks `delete` and blocks dropping a row when the source branches on it between the entry point and the statement under test, or when a plausible fault (rule 8) could treat the two inputs differently. These differences usually block: which attribute holds the value, a list against a single value, the list length, the order of items, the depth of a repeated key, a second key beside the first. A difference that meets neither condition blocks nothing. That often holds for another value of the same type, another type of the same kind (a JSON float against an int as a formal attribute's value), the record type, the section name, or a record inside a bundle against one at the top level, but the source decides each case. When reading cannot settle it, give `merge` or `keep`.
3. **When a row may go.** A row is held to rule 2 against the rows that stay. A row whose expected message has its own format stays.
4. **When separate functions merge.** Functions merge into one parametrised test when their bodies are the same apart from the input values and the expected values. The merged body has no branch on a parameter. Every input and every assertion of the originals stays, in its original form. A row that joins an existing parametrised test takes that test's assertions. They may be stricter than the original's, as long as they hold today. When they change the form of an original assertion, another test must still pin that form, and the verifier names it. In a row that joins an existing parametrised test, an assertion rewritten into a form the verifier shows equal for every row's own values keeps its form. In a new merged test, a truth test stays a truth test. Turning `assert x` and `assert not x` into `assert f(x) is expected` makes both stricter, so such inputs split across two parametrised tests, one for each form. When a merge needs a branch, the verdict is `keep`. When an existing parametrised test has the same body, prefer adding rows to it over a new function, as long as the result still passes rule 5. A function's inputs may split across two parametrised tests when each part meets this rule against the test it joins. An item id is not an input. A merge may change it when the new id still names the case.
5. **A merge must be better, not only shorter.** A reader finds the behaviour as quickly as before, a failure still names the case that broke, and the merged function does not mix behaviours that deserve their own names. A merge that saves lines and hides intent is a `keep`. A merge passes when its body reads as plainly as one of the originals and only its parameter table grows. It fails when it needs extra machinery, such as `getattr` lookups over string columns or lines that matter only for some rows, or when its non-blank lines come to nearly twice those of the originals together. A row that names the call it makes, for example as a lambda, keeps the intent that a method name in a string hides.
6. **Tests that assert only "does not raise".** Such a test is held to the two checks like any other, and the only fault it can catch is a raise. A rejecting rule beside it counts as its contract, because the test guards against over-rejection. Name the rule in Reason.
7. **A test in the wrong module.** A test that calls a different entry point from the rest of its module gets the verdict its content earns. Note the module it belongs in. The audit moves a test only as part of a merge.
8. **No removal without an attempted refutation.** A `delete`, a `merge`, a dropped row or a dropped section goes to the judge only after a verifier tried to show that something is lost. The verifier reports every fault that the candidate alone catches and says whether a maintainer could plausibly write it. A fault is plausible when a real edit to today's code could introduce it. A fault is contrived when it needs new code that has no purpose except to break the candidate. A plausible separating fault refutes the proposal.

## Ledger row

The classifier writes one row for each test function, in file order.

| Column | Content |
|---|---|
| Test | The function name |
| Items | The number of collected items |
| Pins | The behaviour the test pins, in one sentence ending in a full stop, in terms the test itself shows (the call, the input and the expected result). A private function the test calls directly is the call |
| Reason | The contract and its source (issue number, conformance row, spec section, docs page), as a sentence, or `No source found.` |
| Sibling | The nearest test that covers similar ground, as `module.py::function`, or `-` |
| Verdict | One verdict from the table above |
| Confidence | `high`, `medium` or `low` |
| Note | For `merge`, `narrow` and `delete`: what to do, and the fault that stays covered. Otherwise empty |

For a `keep` or a `protected` that no later layer examines, the Pins and Reason cells become the register reason word for word, Pins first. So neither cell says which internal code the input reaches, and neither says that the test alone catches a fault. Nobody has planted a fault to show either. An argument about the code belongs in the proposal, where the verifier tests it.

## The layers of judgement

Each module passes through these layers in order. A later layer reads everything the earlier layers wrote.

| Layer | Who | What it produces |
|---|---|---|
| 1. Evidence | Scripts | `provenance.tsv`, `coverage-nominations.tsv` and `item-arcsets.tsv` for the whole suite |
| 2. Classifier | Sonnet agent | The ledger: one verdict for each test function, and a proposal for each merge and each `narrow` and `delete` |
| 3. Verifier | Sonnet agent in its own worktree | For each `delete`, each dropped row and each dropped section, the faults planted and whether the suite without the candidate catches them. For each merge, the merged test built as a patch, with proof that it keeps every input, assertion and covered arc of the originals, and a list of each assertion a joining row gains |
| 4. Coverage and mutation check | Sonnet agent with coverage contexts and mutmut | For the proposals the verifier did not refute: the arcs in `src/prov` that only the candidates cover (there must be none), and whether any detected mutant becomes undetected (items deselected for a removal, the patch applied for a merge or a dropped section) |
| 5. Judge | Opus agent, read-only apart from a restored planted fault | The final list, with a ruling and a recorded reason for every proposal |
| 6. Maintainer | The maintainer | Accepts or amends the judge's list. Nothing changes in the suite before this |
| 7. Register | Script and a Sonnet agent | One row for each test function of the module in `register/`, with the ruling, the reason and a fingerprint. The script copies the classifier's row for a test no later layer examined, and the agent writes the rows a later layer ruled |

Rules for the judge:

- The judge rules on every proposal the classifier made, including the ones the verifier refuted. Each ruling comes with one reason a later reader can check against the code.
- The judge reads the tests and the source itself. It does not take the classifier's or the verifier's description as fact.
- A removal needs all four of these. The verifier found no plausible separating fault. The candidates cover no arc of their own. The mutation check found no newly undetected mutant. The judge can name the test or the rows that keep the behaviour pinned, and none of them is removed in the same change.
- A merge needs all three of these. The verifier found no lost input or assertion. The mutation check found no newly undetected mutant. The judge confirms rules 4 and 5 from the patch.
- When the verifier called a separating fault contrived, the judge decides whether it is.
- The judge may keep a test that every earlier layer cleared, for example because an issue or a document promises exactly that input. It gives the source.
- The judge may flag a `keep` it doubts. It does not add a removal that has not been through the verifier.
- When in doubt, the judge rules `keep`.

## The register

`register/<module>.tsv` holds the standing ruling for each test function, so that a later audit judges only the tests that are new or changed.

| Column | Content |
|---|---|
| `function` | The test function |
| `ruling` | `keep`, `merged`, `narrowed`, `rewrite`, `query`, `protected` or `removed`. A test that keeps its name and loses rows or a section is `narrowed`. A test that gains rows or functions in a merge is `merged`, also when it loses rows, and its reason names both changes. A function that no longer exists, a split one included, is `removed` |
| `ruled_by` | The layer whose ruling stands: `classifier` when no later layer examined the test, `judge` when the maintainer accepted the judge's ruling, `maintainer` when the maintainer ruled differently from the layer whose ruling would otherwise stand, added the test, or accepted a classifier's `rewrite` or `query`. When the maintainer extends a ruling that stands, for example by adding a row to a judge-ruled merge, `ruled_by` keeps the layer whose ruling stands, and the reason says what the maintainer added and why |
| `confidence` | The classifier's confidence for a ruling no later layer examined, otherwise `-` |
| `audit_commit` | The commit at which the row's test was last confirmed, and for a row a later layer ruled, the tests its reason names. It is stamped after the change that applies the ruling is committed |
| `fingerprint` | A hash of the function's source, of the module-level assignments its decorators name and of its collected item ids. Empty for `removed` |
| `reason` | What the test pins and the contract behind it. A row a later layer ruled also gives the evidence for the ruling |

The fingerprint covers the function's own text, its collected item ids and the text of each module-level assignment in the test's own module that its decorators name, such as a case list passed to `parametrize` or a constant in a `pytest.param`. A value change in such a list moves the fingerprint even when the item ids stay the same. A name imported from another module, a module-level name the test's body reads, a list that a named list draws from, a helper and a fixture go unnoticed unless the item ids change.

A register holds two kinds of row.

- **A row the classifier ruled** (`ruled_by` is `classifier`). No proposal touched the test and no later layer examined it. `scripts/register.py draft` copies its reason from the ledger's Pins and Reason cells. The row records what the test pins and the contract behind it. It records that the classifier, by reading, found no sibling that does the same job, and that is not proof. The register check does not follow the names in such a row, so a later change to the code that makes the test redundant goes unreported.
- **A row a later layer ruled** (`ruled_by` is `judge` or `maintainer`). A proposal touched the test, or the judge or the maintainer examined it. An agent writes its reason from the judge's table, or from the maintainer's answer when no judge ran. The ruling depends on how the code is written, so the register check follows the code and the tests the reason names.

The registers of `test_json`, `test_read`, `test_provn_lexer`, `test_jsonld` and `test_statements` give their classifier rows the longer form, with code names. Those reasons were reviewed in their pull requests and stay as they are. The check no longer follows them.

Rules for every register row:

- Write the reason for a reader who has not seen the ledger.
- A reason names no label from a layer's report, such as F1 or M1, because the reports are not committed. Describe the fault or the merge in words.
- Cite the issue, the conformance row or the document that underpins the test, as `#532`, whenever one exists. A reader can then follow the reason to its source. Cite an issue only when its title or body describes the test's input. A reference that comes only from a commit message often belongs to another change in that commit.
- Write a follow-up for a later audit as a sentence that opens with `Later audit:`, for example a pair to send to the verifier. The register check lists those rows. Put it on a live row, never on a `removed` row, because an audit reopens a `removed` row only to ask whether to restore the test. A follow-up about a removed test's job goes on the row of the test that took the job over, or follows `README.md` step 3 when that module has no register.
- A later audit that judges a row again empties its `audit_commit` and `fingerprint`, so that `stamp` anchors the row at the new commit. A row whose ruling stands keeps both. Without this, the check reports a re-affirmed "source moved" row again on every run.

Rules for a row a later layer ruled:

- Say what would go unnoticed without the test, or why nothing is lost without it.
- A claim about which code a test reaches, or that a test alone catches a fault, rests on a fault someone planted and ran, in the verifier's, the mutation check's or the judge's file or in the apply step's own run. Without one, name the fault the test guards and do not claim it is the only guard.
- Name in backticks every function or class the argument passes through, not only the first and the last, for example `_decode_time` (methods as `Class.method`). A module-level constant may stay in backticks, but name the function that applies it too. The register check compares each named definition with its text at `audit_commit` and flags the row when the code changed. It tracks only a function or a class under `src/prov`, outside the tests. A constant, a test helper, a standard-library name or a misspelt name matches nothing. The check stays silent about it, and `check --names` marks it `(matches nothing)`. A bare common word, such as `identifier`, matches every definition of that name and flags the row for unrelated changes, so write it without backticks. Backtick a function's name alone, because the check follows no backticked call with arguments and `check --names` does not list one, and the check reads empty brackets as the bare name, which matches every definition with that trailing name. `check --names` prints what each row follows.
- Name a sibling, takeover or folded-in test as `module.py::function`, each one in full. The register check compares that test's text, with the module-level assignments its decorators name, with its text at `audit_commit` and flags the row when it changed or was removed. It follows only `test_` functions in `test_*.py` modules, and ignores a test that did not exist at `audit_commit`, such as a function the same change folded in. A helper or a module outside the tests matches nothing.
- A test that was proposed for removal and kept records the fault that kept it. This stops a later audit from proposing the same removal.
- A `narrowed` row and a `merged` row say what went or what was folded in, and why nothing was lost. A `merged` row also names in full, as `module.py::function`, each test that still pins a form a joining row replaced.
- A `removed` row stays in the register with its reason, so that nobody adds the test back without reading it. It names the test that took over its job and the code the ruling rests on, so that the check reports the row when either changes. When a corpus row took over, it also names the corpus file.
- The row of a test that went, or that lost rows or a section, also names each second catcher the judge's `## Final list` names by function, as `module.py::function`, with the planted fault it catches. A second catcher is a test, other than the takeover, that fails under a fault the judge planted against the test, rows or section that went. It gets no row of its own.

`scripts/register.py check` sorts every test function into one of these groups.

| Group | Meaning | What a later audit does |
|---|---|---|
| Unchanged | The fingerprint matches. For a row a later layer ruled, no definition or test the reason names changed | Nothing. The ruling stands |
| Changed | The fingerprint differs | The test goes through the layers again, unless a small pull request extended its ruling, made an edit that changes no input value and no assertion, or carried out a ruled `rewrite` (`README.md`, For the coordinator) |
| New | The function has no row | The test goes through the layers |
| Source moved | A row a later layer ruled, `removed` rows included, names a definition or a test that changed since `audit_commit` | The classifier reads the diff and answers one question: does it undo the recorded reason? For a `removed` row, a yes is a proposal to restore the test, which goes to the maintainer |
| Gone | A row has no function and its ruling is not `removed` | Mark the row `removed`, `ruled_by` `maintainer`, with the reason and the test that took over its job, or delete it when the test was renamed |

A row with the note `unknown audit commit` names a commit that git cannot resolve. The row was never stamped, or a rebase lost its commit. The note appears under Changed for a row whose function exists and under Source moved for a `removed` row. Stamp the row. It needs no new judgement.

After the groups, the check lists the rows that still wait for someone to act: each row ruled `rewrite` or `query`, and each row with a `Later audit:` follow-up.

A new test that duplicates an old one is the test that fails the unique-job check, so an old ruling is not reopened because a test was added.

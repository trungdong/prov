# Test-suite audit

This folder holds the rules, the tools and the standing results of the test-suite audit. Unlike the specs beside it, it is a living record: a later audit updates it.

| Path | Content |
|---|---|
| `rubric.md` | The rules: the two checks, the verdicts, the protected classes, the layers of judgement and the register format |
| `register/<module>.tsv` | The standing ruling and reason for each test function of an audited module |
| `scripts/provenance.py` | Writes `provenance.tsv`: the first commit and the issue references of each test function |
| `scripts/coverage_nominations.py` | Writes `coverage-nominations.tsv` and `item-arcsets.tsv` from a coverage run with per-test contexts |
| `scripts/register.py` | `draft` copies the classifier's rows into a module's register. `stamp` fills the fingerprints of the rows. `check` lists the tests a new audit must judge |
| `mutation.md` | The mutmut configuration and commands for the mutation check |
| `briefs/` | The brief template for each layer's agent |

## What an audit decides

A test earns its place when it pins a contract someone can name and catches a fault no other test catches. The audit merges, narrows or deletes the tests that fail those checks, and records why every other test stays.

A module with no file in `register/` has not been audited.

## How to run an audit

Working files (evidence, ledgers, verifier and judge reports) go in a dated folder under `planning/plans/`, which is gitignored. Only the register and a change to the rules are committed.

1. Run the register check. It prints the tests that are new, changed or whose source moved since their ruling. It also lists the rows ruled `rewrite` or `query` and the rows whose reason carries a `Later audit:` follow-up.

   ```bash
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py check
   ```

2. Build the evidence for the whole suite. Run the suite once with per-test coverage contexts and list the collected items. Then run the two evidence scripts. Each script's docstring gives its arguments. The output folder must exist.

   ```bash
   COVERAGE_FILE=<work>/evidence/coverage-contexts.sqlite uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider --cov=prov --cov-branch --cov-context=test --cov-report=
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest --collect-only -q -p no:cacheprovider > <work>/evidence/collected-items.txt
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/provenance.py <work>/evidence
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/coverage_nominations.py <work>/evidence/coverage-contexts.sqlite <work>/evidence/collected-items.txt <work>/evidence
   ```

3. Take one module at a time through layers 2 to 6 of `rubric.md`: the classifier, the verifier, the mutation check, the judge and the maintainer. For a module that has a register file, the classifier reads only the tests the check listed, and takes each `Later audit:` follow-up as a proposal to examine. Put a follow-up for a module with no register in that module's classifier brief, as `<follow-ups>`. A judge may flag a test that no earlier layer proposed. A flag is a new proposal, so take it through layers 3 to 5 again before the maintainer rules on it. A `rewrite` that rests on "passes with and without the code it guards" goes to the removal verifier for one planted fault, the guarded code removed, before the maintainer rules on it.
4. Apply the maintainer's rulings for the whole batch on one branch. A batch is the modules one coordinator session audits, about five.
   - Dispatch the apply agent for each module the maintainer ruled on, one module at a time. The maintainer rules on each proposal the judge listed and on each `rewrite` or `query` verdict. The agent changes the tests and writes the register rows a later layer ruled. Commit each module's test change before the next dispatch, and give the next agent the suite counts of the branch at that commit. Otherwise its counts include a change it did not make. A module with no proposal and no `rewrite` or `query` verdict has nothing to apply. Run `draft` for it yourself. It writes the classifier's `keep` and `protected` rows and names the tests it left out.

     ```bash
     uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py draft <module> <work>/ledger/<module>.md
     ```

   - When every test change of the batch is committed, one commit for each module whose tests changed, run the suite with coverage on the branch and on `main`, and compare the `TOTAL` line of the two reports. The statements missed and the branches partly covered must be equal. Each apply agent ran the same comparison for its own module, and this run covers the batch as a whole.
   - Give each test commit and the register commit its final message when you make it, and name no batch in it (`CLAUDE.md`, Commits and PRs), for example "The audit found ...".
   - Then stamp every module of the batch, and every other module whose register an apply agent corrected, and commit the register files. Each stamped row names the commit that was `HEAD` at that moment, and the check compares the tests a reason names with their text at that commit, so stamp after every test change of the batch is committed. That commit must stay in the branch's history. So commit the register files as a new commit, and never reword, amend or rebase a commit the rows name, because that rebuilds it and every later commit and orphans every row anchored at any of them. If the branch is rebased all the same, stamp again and commit the register files again.

     ```bash
     uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py stamp <module>
     ```

   - Run the check after the stamp. `stamp` keeps the anchor of a row whose own text is unchanged. So a row of an existing register that names a test this batch removed, merged or edited still comes out `source moved`. Re-read each such reason against the change and correct it if it no longer holds.
   - Run `check --names` over the batch's modules. A row written in this batch was anchored after every change of the batch, so the check cannot see a sibling test that a later apply step changed. Re-read each row written in this batch that names a test in another test file the batch changed, whether or not that file has a register. Re-read each line marked `(no such test)` too.
   - Empty the `audit_commit` and `fingerprint` of each row you corrected or re-read, stamp again and commit the register files as a new commit.
5. Open one pull request for the batch. It holds the test changes and the register files of every module in it. The pull request needs no `HISTORY.md` entry.
6. The rows the check lists under `rewrite and query` and `later audit` are the audit's standing backlog. Report the rows this batch added to the maintainer with the pull request. A row leaves the lists when a later change carries out the rewrite or answers the query or the follow-up, and an audit rules on the row again.

## For the coordinator

An Opus session coordinates an audit. It reads this file and `rubric.md`, dispatches one agent for each layer from the templates in `briefs/`, and brings each judge's list to the maintainer. It leaves the reading of test modules to the agents, apart from the rows the check reports after a stamp.

| Layer | Brief | Model |
|---|---|---|
| 2. Classifier | `briefs/classifier.md` | Sonnet |
| 3. Verifier, removals | `briefs/verifier-removal.md` | Sonnet, own worktree |
| 3 and 4. Verifier, merges | `briefs/verifier-merge.md` | Sonnet, scratch worktree |
| 4. Coverage and mutation check, removals | `briefs/mutation-check.md` | Sonnet, scratch worktree |
| 5. Judge | `briefs/judge.md` | Opus, read-only |
| 7. Apply and register | `briefs/apply.md` | Sonnet |

Rules that keep the cost down and the result sound:

- Set the model on every agent. No agent inherits the coordinator's model.
- Every brief you send, from a template or not, carries two rules, and you add whichever one it lacks. The agent never runs `git stash`, and `conftest.py` imports nothing that needs an extra (`provrdf`, `provxml`, `prov.dot`, `prov.graph`), so a shared map that needs one lives in a test helper module.
- Build the evidence once for the whole suite, not once for each module.
- Give one classifier several small modules, up to about 60 test functions in all. Run classifiers for different modules in parallel.
- A module with no proposal skips layers 3 to 5, apart from the removal verifier's planted fault for a `rewrite` (step 3). `draft` writes its `keep` and `protected` rows. Bring its `rewrite` and `query` verdicts to the maintainer with the batch's lists, and send the apply agent the answer.
- Run one mutation check at a time, and never beside the gate runner.
- Do not tell the judge what anyone expects it to rule.
- Stop for the maintainer after each judge's list. Apply nothing before the ruling.
- A takeover claim in a question to the maintainer copies the judge's `## Final list` line for that item, never a summary of it and never the ledger's description.
- When a classifier or a judge reports a rubric problem, propose a rule to the maintainer. Add it to `rubric.md` only after the maintainer agrees.
- When a layer reports a suspected defect in the library, probe it, then report it to the maintainer. A fix is a separate change with its own issue.
- Check for leftover processes after each agent that ran mutmut.
- Settle each row the check reports as gone. Mark it `removed`, `ruled_by` `maintainer`, with the reason and the test that took over its job, or delete it when the test was renamed.
- Three kinds of small pull request need no question to the maintainer:
  - One that adds a row or a case to a test a later layer ruled extends that ruling. Its register row follows the `ruled_by` cell of `rubric.md` (The register).
  - One that makes an edit that changes no input value and no assertion, such as a literal replaced by a constant of equal value or a renamed local, also extends the ruling. The commit message says why the edit changes neither, and the pre-PR regime reviews the diff.
  - One that adds a test writes the test's row in the same pull request, as `keep` ruled by the `maintainer`, with a reason that names the fault the test guards. A claim about which code the test reaches rests on a fault the pull request planted (`rubric.md`, The register). `stamp` refuses a module with a test that has no row.
- Before any stamp outside a full audit, such as after a small pull request or a change to the fingerprint, run `check` on the base, before the change, and settle every row of the module it reports as source moved or changed. Then stamp the rows again. `check` reports a row as changed before it looks for source moved, and a stamp moves `audit_commit` past any change still pending.
- When a judge or a classifier asks for a fault to be planted before anyone proposes removing a test it keeps, put the request on that test's row as a `Later audit:` sentence at apply time. A request left only in a ledger is lost.
- When a ruling routes work to a layer, trace one case through every brief from the classifier to the register before the commit: the send condition, the method, the verdict and the file each agent hands on.

## What the first audit found about the method

- Coverage cannot decide anything on its own. Most test functions cover no arc that another test does not also cover, because the round-trip tests run most of the package.
- A classifier's `delete` is a hypothesis. The verifier refuted every deletion the first classifier proposed, each time with a plausible fault that only the candidate caught.
- Most of the overlap is in how tests are written (one body repeated for each format), not in what they cover. A merge keeps every case and removes the repetition.
- A register reason written from reading is often wrong about which code a test reaches. So a row for a test no proposal touched says only what the test itself shows, and a claim about the code rests on a planted fault.
- mutmut's instrumentation adds a stack frame. A test that checks which caller a warning is attributed to fails under it and must be deselected from a mutation run. `mutation.md` lists the tests.

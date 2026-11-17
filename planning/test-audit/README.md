# Test-suite audit

This folder holds the rules, the tools and the standing results of the test-suite audit. Unlike the specs beside it, it is a living record: a later audit updates it.

| Path | Content |
|---|---|
| `rubric.md` | The rules: the two checks, the verdicts, the protected classes, the layers of judgement and the register format |
| `register/<module>.tsv` | The standing ruling and reason for each test function of an audited module |
| `scripts/provenance.py` | Writes `provenance.tsv`: the first commit and the issue references of each test function |
| `scripts/coverage_nominations.py` | Writes `coverage-nominations.tsv` and `item-arcsets.tsv` from a coverage run with per-test contexts |
| `scripts/register.py` | `stamp` fills the fingerprints of a module's register rows. `check` lists the tests a new audit must judge |
| `mutation.md` | The mutmut configuration and commands for the mutation check |
| `briefs/` | The brief template for each layer's agent |

## What an audit decides

A test earns its place when it pins a contract someone can name and catches a fault no other test catches. The audit merges, narrows or deletes the tests that fail those checks, and records why every other test stays.

A module with no file in `register/` has not been audited.

## How to run an audit

Working files (evidence, ledgers, verifier and judge reports) go in a dated folder under `planning/plans/`, which is gitignored. Only the register and a change to the rules are committed.

1. Run the register check. It prints the tests that are new, changed or whose source moved since their ruling.

   ```bash
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py check
   ```

2. Build the evidence for the whole suite. Run the suite once with per-test coverage contexts, then run the two evidence scripts. Each script's docstring gives its arguments.

   ```bash
   COVERAGE_FILE=<work>/evidence/coverage-contexts.sqlite uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider --cov=prov --cov-branch --cov-context=test --cov-report=
   ```

3. Take one module at a time through layers 2 to 6 of `rubric.md`: the classifier, the verifier, the mutation check, the judge and the maintainer. For a module that has a register file, the classifier reads only the tests the check listed. A judge may flag a test that no earlier layer proposed. A flag is a new proposal, so take it through layers 3 to 5 again before the maintainer rules on it.
4. Apply the maintainer's rulings on a branch. Run the suite with coverage on the branch and on `main`, and compare the `TOTAL` line of the two reports. The statements missed and the branches partly covered must be equal. Write or update the module's register file, then stamp it. Each stamped row names the commit that was `HEAD` at that moment, and that commit must stay in the branch's history. So commit the test change and the register file as new commits, and never amend or rebase a commit the rows name. If the branch is rebased all the same, stamp again and commit the register file again.

   ```bash
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py stamp <module>
   ```

5. Open one pull request for the module. It holds the test change and the register file. The pull request needs no `HISTORY.md` entry.

## For the coordinator

An Opus session coordinates an audit. It reads this file and `rubric.md`, dispatches one agent for each layer from the templates in `briefs/`, and brings each judge's list to the maintainer. It does not read test modules itself.

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
- Build the evidence once for the whole suite, not once for each module.
- Give one classifier several small modules, up to about 60 test functions in all. Run classifiers for different modules in parallel.
- A module with no proposal skips layers 3 to 5. Its classifier verdicts go straight to the register, with `ruled_by` set to `classifier`.
- Run one mutation check at a time.
- Do not tell the judge what anyone expects it to rule.
- Stop for the maintainer after each judge's list. Apply nothing before the ruling.
- When a classifier or a judge reports a rubric problem, propose a rule to the maintainer. Add it to `rubric.md` only after the maintainer agrees.
- When a layer reports a suspected defect in the library, probe it, then report it to the maintainer. A fix is a separate change with its own issue.
- Check for leftover processes after each agent that ran mutmut.

## What the first audit found about the method

- Coverage cannot decide anything on its own. Most test functions cover no arc that another test does not also cover, because the round-trip tests run most of the package.
- A classifier's `delete` is a hypothesis. The verifier refuted every deletion the first classifier proposed, each time with a plausible fault that only the candidate caught.
- Most of the overlap is in how tests are written (one body repeated for each format), not in what they cover. A merge keeps every case and removes the repetition.
- mutmut's instrumentation adds a stack frame. A test that checks which caller a warning is attributed to fails under it and must be deselected from a mutation run. `mutation.md` lists the tests.

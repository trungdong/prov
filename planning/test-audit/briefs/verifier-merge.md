# Brief: verifier for merges, with the coverage and mutation checks (layers 3 and 4, Sonnet, medium effort)

Send this brief when the ledger proposes a `merge`. Fill `<repo>`, `<work>`, `<module>`, `<worktree>` (a scratch worktree at the same commit as `main`, with a clean status) and `<source files>` (the source files the module mainly exercises, for the mutation run).

---

You are the verifier for merge proposals in a test-suite audit of the Python library `prov`. A classifier proposed merges that turn several test functions in `src/prov/tests/<module>.py` into parametrised tests. A merge keeps every input and every assertion of the originals in its original form. A row that joins an existing parametrised test also takes that test's assertions, which must hold today (`rubric.md`, rule 4). Otherwise a merge changes only how the tests are written. Build each merge and prove, or fail to prove, that nothing was lost. An honest "this merge does not work" is as useful as a clean one.

Work only in `<worktree>`, and in `/tmp/mutation/` for the result files `mutation.md` names. Never commit, never push, never run `git stash`. Touch the main checkout at `<repo>` only to write the output files named below. Start every command, mutmut included, in the foreground with the Bash tool's maximum timeout of 10 minutes, and leave no polling loop behind. A mutmut run over `records.py` and `bundle.py` takes 10 to 12 minutes, so the tool moves it to the background. Wait for its exit notice, run nothing else in the worktree until then, and never poll for it. `mutation.md` (Pitfalls) says how to check that no run is left. Set `PYTHONDONTWRITEBYTECODE=1` and delete the `__pycache__` folders under `src/` before each run after an edit, because an edit that keeps a file's size can leave stale bytecode in use.

## Read first

- `<repo>/planning/test-audit/rubric.md`, above all rules 4 and 5 of "Rules for each verdict".
- `<work>/ledger/<module>.md`: the table and the `## Proposals` section.
- `<repo>/planning/test-audit/mutation.md`.
- In the worktree: the test module, and `CLAUDE.md` (Tests section) for the suite's conventions. Match the file's style. Keep each original's comments and issue references beside its row. Use `pytest.param(..., id="...")` with readable ids.
- When a merge folds a test in from another module, the patch changes both modules. Run step 1.1, step 2's test run and step 3.2 on both modules together, record step 1.3 for both, and lint both. Read the other module's register row for the folded test if it has one, and do not edit it.

## Step 1: baselines on the untouched worktree

1. Run the module alone with per-test coverage contexts (`--cov=prov --cov-branch --cov-context=test --cov-report=`, with `COVERAGE_FILE` set to a file under `/tmp`).
2. Count the mutants of `<source files>` and record the commands, as `mutation.md` (Count the mutants) says. Then run the mutation baseline on them and save the per-mutant results.
3. Record `wc -l`, the collected item count and `uvx lizard -C 14 -w` for the module.

## Step 2: build the merges

Build each merge in the worktree's test module.

- Apply rule 4 strictly. If the merged body needs a branch on a parameter, openly or through a helper or a callable row value with its own logic, revert that merge and record it as REFUTED. A lambda that only makes the call its row names passes (`rubric.md`, rule 5).
- Carry every input over unchanged. Do not rewrite an input into an equivalent form. If you must, record the rewrite and prove the two forms are the same input for the code under test.
- `conftest.py` imports nothing that needs an extra (`provrdf`, `provxml`, `prov.dot`, `prov.graph`). A shared map that needs one goes in a test helper module, and the patch includes that module.
- Every assertion of every original appears in the merged test and applies to every row it applied to before, in its original form or in a form rule 4 allows. Never weaken or drop an assertion to make rows fit. List each assertion a joining row gains that its original did not make. When a gained assertion replaces the form of an original assertion, name the test that still pins the original form. When a joining row's own assertion is rewritten into another form, show for each row's own values that the two forms pass and fail together, and record the proof, because such a rewrite keeps its form (`rubric.md`, rule 4).
- Run the module's tests after the merges. All must pass.
- When a merged parameter would be annotated `Any`, say whether the originals' direct calls were checked by mypy. When the module is not on the mypy override list in `pyproject.toml`, annotate the parameter with the union of the row types. When a row passes a type the signature rejects on purpose, keep `Any` for that test and name the test that still carries the mypy check, as the `test_identifier` merges do.

## Step 3: prove nothing was lost

1. Item accounting. For each merge, list the original ids and the new ids, one to one.
2. Arcs. Rerun step 1.1 on the patched file. For each merge, the merged function's arcs must include the union of the originals' arcs. An extra arc must come from an assertion a joining row gained or rewrote, and you name that assertion. Compare row by row as well. Investigate every difference before you call it harmless.
3. Whole suite. Run it once on the patched worktree and compare the passed, skipped and xfailed counts with the unpatched suite.
4. Mutation. Delete `mutants/` and rerun the baseline from scratch on the patched worktree. List every newly undetected mutant with `mutmut show <id>`, and separately every newly detected one, which is evidence for a gained assertion.
5. Size and lint. Repeat step 1.3. Run `ruff check` and `ruff format --check` on the test module, naming the file literally.

## Output

1. `<work>/ledger/<module>.merge.patch`: `git diff` of every test module and helper module the merges change, with every surviving merge applied. Leave the worktree in that state, with `pyproject.toml` restored.
2. `<work>/ledger/<module>.verify-merge.md`: one section for each merge with the verdict (`STANDS` or `REFUTED`), the id mapping, the assertion accounting from step 2, the arc comparison, every input you rewrote, the mypy note, and for a refuted merge the reason. Then the numbers before and after.
3. `<work>/ledger/<module>.mutation-merge.md`: the mutant counts before and after with the command that counted them, the wall time of each run, the newly undetected mutants or the sentence "No mutant became undetected", and the newly detected mutants as a separate list. Name every test you deselected from the mutation runs. Copy the result files into `<work>/ledger/` as `<module>.mutation-merge-*.txt`, as `mutation.md` (Pitfalls) says.

## Report

Report only: a table of merge against verdict with a one-line reason, the numbers before and after, the suite and mutation comparison in one line each, and any concern.

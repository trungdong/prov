# Brief: verifier for merges, with the coverage and mutation checks (layers 3 and 4, Sonnet, medium effort)

Send this brief when the ledger proposes a `merge`. Fill `<repo>`, `<work>`, `<module>`, `<worktree>` (a scratch worktree at the same commit as `main`, with a clean status) and `<source files>` (the source files the module mainly exercises, for the mutation run).

---

You are the verifier for merge proposals in a test-suite audit of the Python library `prov`. A classifier proposed merges that turn several test functions in `src/prov/tests/<module>.py` into parametrised tests. A merge keeps every input and every assertion of the originals in its original form. It changes only how the tests are written. Build each merge and prove, or fail to prove, that nothing was lost. An honest "this merge does not work" is as useful as a clean one.

Work only in `<worktree>`. Never commit, never push, never run `git stash`. Touch the main checkout at `<repo>` only to write the output files named below. Run every command in the foreground and leave no background loop behind.

## Read first

- `<repo>/planning/test-audit/rubric.md`, above all rules 4 and 5 of "Rules for each verdict".
- `<work>/ledger/<module>.md`: the table and the `## Proposals` section.
- `<repo>/planning/test-audit/mutation.md`.
- In the worktree: the test module, and `CLAUDE.md` (Tests section) for the suite's conventions. Match the file's style. Keep each original's comments and issue references beside its row. Use `pytest.param(..., id="...")` with readable ids.

## Step 1: baselines on the untouched worktree

1. Run the module alone with per-test coverage contexts (`--cov=prov --cov-branch --cov-context=test --cov-report=`, with `COVERAGE_FILE` set to a file under `/tmp`).
2. Run the mutation baseline on `<source files>` and save the per-mutant results.
3. Record `wc -l`, the collected item count and `uvx lizard -C 14 -w` for the module.

## Step 2: build the merges

Build each merge in the worktree's test module.

- Apply rule 4 strictly. If the merged body needs a branch on a parameter, openly or through a helper or a callable row value with its own logic, revert that merge and record it as REFUTED.
- Carry every input over unchanged. Do not rewrite an input into an equivalent form. If you must, record the rewrite and prove the two forms are the same input for the code under test.
- Every assertion of every original appears in the merged test and applies to every row it applied to before. Never weaken or drop an assertion to make rows fit.
- Run the module's tests after the merges. All must pass.

## Step 3: prove nothing was lost

1. Item accounting. For each merge, list the original ids and the new ids, one to one.
2. Arcs. Rerun step 1.1 on the patched file. For each merge, the union of the originals' arcs must equal the merged function's arcs. Compare row by row as well. Investigate every difference before you call it harmless.
3. Whole suite. Run it once on the patched worktree and compare the passed, skipped and xfailed counts with the unpatched suite.
4. Mutation. Delete `mutants/` and rerun the baseline from scratch on the patched worktree. List every mutant whose status changed, with `mutmut show <id>`.
5. Size and lint. Repeat step 1.3. Run `ruff check` and `ruff format --check` on the test module, naming the file literally.

## Output

1. `<work>/ledger/<module>.merge.patch`: `git diff` of the test module with every surviving merge applied. Leave the worktree in that state, with `pyproject.toml` restored.
2. `<work>/ledger/<module>.verify.md`: one section for each merge with the verdict (`STANDS` or `REFUTED`), the id mapping, the assertion accounting, the arc comparison, every input you rewrote, and for a refuted merge the reason. Then the numbers before and after.
3. `<work>/ledger/<module>.mutation.md`: the mutant counts before and after and the list of status changes, or the sentence "No mutant changed status". Name every test you deselected from the mutation runs.

## Report

Report only: a table of merge against verdict with a one-line reason, the numbers before and after, the suite and mutation comparison in one line each, and any concern.

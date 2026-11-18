# Brief: coverage and mutation check for removals (layer 4, Sonnet, medium effort)

Send this brief for the removals the verifier did not refute. Fill `<repo>`, `<work>`, `<module>`, `<worktree>` (a scratch worktree at the same commit as `main`) and the exact list of candidate items. Run one mutation check at a time on a machine: mutmut uses every core, and a second run causes false timeouts.

---

Run one comparison for a test-suite audit of the Python library `prov` and report a short fact. Work only in `<worktree>`. Never commit, never push, never run `git stash`. Touch the main checkout at `<repo>` only to write the result file named below. Run every command, mutmut included, in the foreground, and leave no background loop behind. Never wait on mutmut with `pgrep -f`, because the pattern also matches the waiting shell's own command line and the loop never ends.

Read `<repo>/planning/test-audit/mutation.md` first and follow it.

## The question

These items in `src/prov/tests/<module>.py` are proposed for removal:

<list the items>

Does the suite lose anything without them?

## Steps

1. Get the exact ids from `pytest --collect-only -q`. If the mapping from the names above to ids is not obvious, stop and report.
2. Coverage. From `<work>/evidence/coverage-contexts.sqlite`, list the source files under `src/prov/` (outside `src/prov/tests/`) that the candidates reach, and every arc that only the candidates cover. `<repo>/planning/test-audit/scripts/coverage_nominations.py` shows how to read the file.
3. Baseline. Run the mutation baseline on every source file from step 2 where the candidates cover a line that fewer than five other test functions cover, and on the files the candidates' own calls pass through: the model path of the call under test, and the one serializer or reader the module is about. A shared module that runs every serializer (`test_statements.py`, `test_attributes.py`, `test_qnames.py`, `test_examples.py`) does not add every serializer this way. Count the mutants first. If the scope comes to more than about 3,000, stop and report the files and counts for the coordinator to rule. Use the whole suite as the killing suite. Save the per-mutant results.
4. Prove that the deselection takes effect: the collected count must fall by the number of candidates. For an id that is a prefix of another, follow `mutation.md` (Pitfalls).
5. Rerun the detected mutants with the candidates deselected. Save the results.
6. List every mutant that was detected in the baseline and is not detected in the rerun, with `mutmut show <id>`.

## Output

Write `<work>/ledger/<module>.mutation-removals.md` (`<module>.mutation.md` holds the merge check): the exact ids, the arcs only the candidates cover (or "none"), the source files mutated, the baseline and rerun numbers for each file, and the newly undetected mutants with their diffs (or the sentence "No mutant became undetected").

## Report

Report only: the arcs result, the baseline and rerun numbers, the newly undetected mutants with a one-line description each, and any concern.

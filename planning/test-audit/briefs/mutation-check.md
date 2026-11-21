# Brief: coverage and mutation check for removals (layer 4, Sonnet, medium effort)

Send this brief for the removals the verifier did not refute. A dropped section is a removal, so give the path of its patch, `<work>/ledger/<module>.section.patch`, in place of candidate items. Fill `<repo>`, `<work>`, `<module>`, `<worktree>` (a scratch worktree at the same commit as `main`) and the exact list of candidate items. Run one mutation check at a time on a machine: mutmut uses every core, and a second run causes false timeouts.

---

Run one comparison for a test-suite audit of the Python library `prov` and report a short fact. Work only in `<worktree>`, and in `/tmp/mutation/` for the result files `mutation.md` names. Never commit, never push, never run `git stash`. Touch the main checkout at `<repo>` only to write the result files named below. Start every command, mutmut included, in the foreground with the Bash tool's maximum timeout of 10 minutes, and leave no polling loop behind. A run that takes longer moves to the background. Wait for its exit notice, run nothing else in the worktree until then, and never poll for it. `mutation.md` (Pitfalls) says how to check that no run is left.

Read `<repo>/planning/test-audit/mutation.md` first and follow it.

## The question

These items in `src/prov/tests/<module>.py` are proposed for removal:

<list the items>

Does the suite lose anything without them?

## Steps

For a dropped section, apply its patch wherever a step deselects the candidates, and in step 2 compare the suite's covered arcs with and without the patch.

1. Get the exact ids from `pytest --collect-only -q`. If the mapping from the names above to ids is not obvious, stop and report.
2. Coverage. From `<work>/evidence/coverage-contexts.sqlite`, list the source files under `src/prov/` (outside `src/prov/tests/`) that the candidates reach, and every arc that only the candidates cover. `<repo>/planning/test-audit/scripts/coverage_nominations.py` shows how to read the file.
3. Baseline. Take the files the Scope section of `mutation.md` gives for a removal. Count their mutants and record the commands before the baseline runs, as the section Count the mutants of `mutation.md` says. Then run the mutation baseline on them. Use the whole suite as the killing suite. Save the per-mutant results.
4. Prove that the deselection takes effect: the collected count must fall by the number of candidates. For an id that is a prefix of another, follow `mutation.md` (Pitfalls).
5. Rerun the killed and the timed-out mutants with the candidates deselected, as `mutation.md` (Compare a removal) says. Save the results.
6. List every mutant that was killed or timed out in the baseline and is not detected in the rerun, with `mutmut show <id>`.

## Output

Write `<work>/ledger/<module>.mutation-removal.md`: the exact ids, the arcs only the candidates cover (or "none"), the source files mutated, the mutant count of each file and the command that counted it, the baseline and rerun numbers for each file, the wall time of each run, and the newly undetected mutants with their diffs (or the sentence "No mutant became undetected"). Copy the result files into `<work>/ledger/` as `<module>.mutation-removal-*.txt`, as `mutation.md` (Pitfalls) says.

## Report

Report only: the arcs result, the baseline and rerun numbers, the newly undetected mutants with a one-line description each, and any concern.

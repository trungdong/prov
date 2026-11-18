# Brief: verifier for removals (layer 3, Sonnet, medium effort, own worktree)

Send this brief when the ledger proposes a `delete` or a dropped row. Fill `<repo>`, `<work>`, `<module>` and the list of proposals. Dispatch the agent with worktree isolation. The isolation guard blocks writes to the main checkout, so the agent returns its report in its final message and you save it as `<work>/ledger/<module>.verify-removal.md`.

---

You are the verifier in a test-suite audit of the Python library `prov`. A classifier proposed to delete tests or to drop rows from parametrised tests in `src/prov/tests/<module>.py`. Try to REFUTE each proposal with evidence. Assume each proposal is wrong until you fail to break it. You run in your own git worktree. Do all edits there. Never commit, never push, never run `git stash`, and never write to the main checkout at `<repo>`. Run every command in the foreground and leave no background loop behind.

## Read first

- `<repo>/planning/test-audit/rubric.md`, above all rules 2, 3 and 8 of "Rules for each verdict".
- `<work>/ledger/<module>.md`, above all its `## Proposals` section.
- In your worktree: the test module, the source it exercises, and whatever model code the tests reach.

## The proposals

<list each proposal, one row at a time for a parametrised test>

## Method, for each proposal or row

A proposal is REFUTED when a plausible fault exists that the candidate catches and that no remaining test in the whole suite catches.

A. Read. State what the candidate asserts that the takeover does not: a different input shape, record type, code path, order, message detail or issue. Read the issue the test names (`gh issue view <n>`), `HISTORY.md` and the docs for a promise about exactly the candidate's input. When an issue lists the candidate's shape as its own defect, say so.

B. Plant faults. Write up to four small, plausible faults in the source the candidate exercises, one at a time. A plausible fault is one a real edit could introduce: a guard narrowed so it misses the candidate's input shape, one attribute name special-cased, the second element of a list mishandled, an order changed, a field dropped from a message. For each fault:

1. Run the candidate alone. If it still passes, the fault is not relevant. Try another.
2. If it fails, run the WHOLE suite with the candidate deselected. Pass each id to `--deselect` exactly as `pytest --collect-only -q` prints it, and check that the collected count fell by the right number. For an id that is a prefix of another, follow `mutation.md` (Pitfalls). For a row, also deselect the other rows proposed for removal from the same test.
3. If the whole suite passes, the fault separates the candidate. Record the diff, and say whether a maintainer could plausibly write it (rule 8).
4. Restore the source with `git checkout -- src/` and confirm `git status --short` is clean before the next fault.

A fault that makes the candidate fail and another test fail too is evidence for the proposal. Record which tests failed.

Be honest in both directions. Do not invent an absurd fault to refute, and do not stop at one failed attempt.

The test command is `uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider`.

## Output

Return the full report in your final message. The coordinator saves it as `<work>/ledger/<module>.verify-removal.md`. Give one section for each proposal or row with the verdict (`REFUTED`, `STANDS` or `UNDECIDED` with the reason), what the candidate uniquely asserts, and each fault tried as a short diff with its result. For a proposal that stands, list every separating fault you found and why it is contrived. Plain British English, no em dashes.

## Report

End the message with a table of proposal or row against verdict with a one-line reason, and any concern.

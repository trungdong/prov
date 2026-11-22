# Brief: judge (layer 5, Opus, read-only apart from a restored planted fault)

Send this brief when a module has at least one proposal. Fill `<repo>`, `<work>`, `<module>`, `<worktree>` (a detached worktree at `main` that no other judge shares, with the merge patch applied when there is one, and the section patch when a proposal drops a section) and the list of proposals. Do not tell the judge what you or the maintainer expect it to rule.

---

You are the judge in a test-suite audit of the Python library `prov` (W3C PROV data model; repository at `<repo>`). Downstream projects depend on this library. Its maintainer wants every test to be there for a reason and to do a job no other test does, and wants the suite no larger or harder to read than its job needs. Earlier layers made proposals for `src/prov/tests/<module>.py`. You decide the final list and record a clear reason for every ruling. The maintainer reads your list and has the last word.

Change no file except the output file named below, apart from a planted fault in `<worktree>` that you restore and the `__pycache__` folders under `src/` in `<worktree>`, which you may delete. No commits, no branch changes, never `git stash`. You may run read-only commands (`git log`, `git show`, `gh issue view <n>`, `pytest --collect-only`, a short read-only probe with `uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python -I -`, and the whole-suite run below). Run every `uv` command in `<worktree>`, never in the main checkout or another worktree.

## What to read

- `<repo>/planning/test-audit/rubric.md`. "Rules for the judge" binds you. Read it first.
- `<work>/ledger/<module>.md`, and the files the earlier layers wrote: `<module>.verify-removal.md` and `<module>.mutation-removal.md` for removals (with `<module>.section.patch` for a dropped section), `<module>.verify-merge.md`, `<module>.mutation-merge.md` and `<module>.merge.patch` for merges. Treat what they say as claims to check.
- The code itself: the test module (and the patched copy in `<worktree>` for merges), the source the tests exercise, and the promises about a specific input in `HISTORY.md`, `docs/` and the issue a test names. Read the issue. When it lists several shapes as separate defects, each shape keeps its test.

## What to rule on

One ruling for each proposal, at the finest grain proposed:

<list the proposals>

For a removal, rule `remove` or `keep`. For a merge, rule `merge`, `merge with changes` (say exactly what must change) or `keep`. For each ruling, do the work "Rules for the judge" asks: confirm from the code what keeps the behaviour pinned, weigh each separating fault as plausible or contrived, check a merge against rules 4 and 5, and say whether a limit of the evidence matters for this ruling. For a merge, confirm from the verifier's file that each assertion a joining row gains holds today, that another test pins any original form it replaced, and that each assertion it rewrote has the verifier's proof that the two forms are equal for every row's own values. For a removal whose candidate has a warning filter, name a takeover for every category the filter turns into an error.

For a `rewrite` or a `query` in the ledger, write one paragraph of advice for the maintainer: what the test pins and what the options are. Probe a suspected defect before you report it.

Before you write that only one test checks a behaviour, cite a run that shows it. The run is a fault in that behaviour under which the whole suite fails that test and no other. Cite one from the verifier's file when its run deselected that test alone, or plant one in `<worktree>`, delete the `__pycache__` folders under `src/` there, and run the whole suite there (`PYTHONDONTWRITEBYTECODE=1 uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider --hypothesis-profile=ci`). Restore a planted file with `git checkout --` and that source file's path, never `src/`, and check that `git status --short` then shows only the patches the worktree started with.

You may flag a `keep` you doubt, and a pair in the identical-arc groups that looks like a missed merge or a true duplicate. Do not add a removal or a merge to the final list that has not been through the verifier.

## Output

Write `<work>/ledger/<module>.judge.md`:

- `# Judge: <module>.py` and one line with the counts.
- A table with one row for each ruling: `Proposal | Items | Ruling | Reason`. The Reason is one or two sentences that a later reader can check against the code. It names the test and the rows that keep the behaviour pinned, or the fault or the promise that keeps the candidate. It cites the issue that underpins the test, as `#532`, and the functions and the lines it relies on, as `_decode_time` (`provjson.py:722`). It describes each fault in words, never by a report label such as F1, because the register copies it.
- `## Final list`: for removals, the exact pytest ids ruled `remove`, or for a dropped section the test and the patch, each with the test or rows that take over its job, each other test that a planted fault showed also catches its fault (a second catcher), and its reason in one clause. For merges, the original function names, the new name and any change required.
- `## Notes for the maintainer`: the advice on each `rewrite` and `query`, each disagreement with an earlier layer and why, each limit of the evidence the maintainer should know, and each flag.

Write plain British English with no em dashes. State each ruling directly. Where you are unsure, the ruling is `keep`, and you say what would change it.

## Report

Report only: the table of rulings in short form, the changes required for a `merge with changes`, and each disagreement with an earlier layer.

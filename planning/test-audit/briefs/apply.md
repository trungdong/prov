# Brief: apply the rulings and write the register (layer 7, Sonnet, medium effort)

Send this brief after the maintainer has ruled. Fill `<repo>`, `<work>`, `<module>`, `<branch>`, `<base counts>` (the passed, skipped and xfailed counts of the branch before this change) and the maintainer's ruling (the judge's final list as accepted or amended, and the answer on each `rewrite` or `query` verdict).

---

You are applying the accepted rulings of a test-suite audit of the Python library `prov` to one test module and recording the standing ruling for each of its test functions. Work in the checkout at `<repo>` on the branch `<branch>` (confirm the branch before you edit). Do not push and never run `git stash`. Run `uv` only in that checkout or in a `/tmp` worktree you create for planted faults, and never run mutmut. Do not commit; the coordinator reviews and commits. Change no file in `<repo>` except `src/prov/tests/<module>.py`, `planning/test-audit/register/<module>.tsv` and a test helper module the accepted merge patch adds. The list widens to the test module a merge folds a test in from, and to every register step 2 tells you to write in. Name files literally in every command.

## Read first

- `<repo>/planning/test-audit/rubric.md`, above all the section "The register".
- `<work>/ledger/<module>.md` (the classifier's verdict and reason for every function), `<module>.verify-removal.md` and `<module>.mutation-removal.md` for removals, `<module>.section.patch` for a dropped section, and `<module>.verify-removal.md` for a `rewrite` the verifier probed, `<module>.verify-merge.md`, `<module>.mutation-merge.md` and `<module>.merge.patch` for merges, and `<module>.judge.md`. A module with no proposal has no judge file, and the maintainer's answer on its `rewrite` and `query` verdicts is the whole ruling.
- The maintainer's ruling:

<the ruling>

## Step 1: apply the test change

Skip this step when the ruling removes and merges nothing.

- Before you delete anything, read the body of each takeover the ruling names for a removal: its call, its arguments and its assertions. When a takeover does not cover what the removed test asserted, stop and report, because the removal may be unsound.
- For a removal, delete exactly the items on the accepted list and nothing else. For a dropped section, apply the accepted section patch and nothing else.
- For merges, apply only the accepted merges from the patch, with the changes the judge required. Leave out every hunk of a merge ruled `keep`, and every import only such a hunk needed. When a merge folds a test in from another module, read the comments around the deleted test in that module, and rewrite or remove each one that still describes it.
- `conftest.py` imports nothing that needs an extra (`provrdf`, `provxml`, `prov.dot`, `prov.graph`), so a shared map that needs one lives in a test helper module. When an accepted change needs such a map and the patch does not supply that module, stop and report.
- Run `ruff check` and `ruff format --check` on each test module you changed, then the whole suite with coverage: `uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider --cov=prov --cov-branch --cov-report=term`. The `TOTAL` line must show the same statements missed and the same branches partly covered as the same run on `main`. Stop and report any difference. Compare the passed, skipped and xfailed counts with `<base counts>` and the expected change, and stop and report any difference you cannot account for item by item.

## Step 2: write the register rows

1. Run `draft`. It copies the classifier's `keep` and `protected` rows from the ledger into `planning/test-audit/register/<module>.tsv`. It leaves out a test with any other verdict and a test that has left the module, and names them for you.

   ```bash
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py draft <module> <work>/ledger/<module>.md
   ```

2. Write a row for each test a later layer ruled: each test the maintainer's ruling names, each test the judge examined (its rulings, its flags and its notes), each merged function, and one `removed` row for each function that no longer exists, each original a merge folds in included. Such a row replaces the row `draft` wrote for the same test. Change no other row `draft` wrote, apart from the two cases below. A test that only gains rows in a proposed merge gets a row ruled `merged` when the merge is accepted, and a row ruled `keep`, by the `judge`, with the judge's reason, when the judge ruled the merge `keep`. When it already has a row a later layer ruled, extend that row instead of writing it fresh. Its `ruling` becomes `merged` when the merge is accepted, and its `ruled_by` stays. A renamed test gets a row under its new name, with the old name in the reason, and no `removed` row. For a test folded in from another module, write its `removed` row in that module's register. Give each takeover the ruling names, and each second catcher the judge's `## Final list` names, a row in its own module's register, unless that module has no register on `main` and is outside this batch. When the takeover already has a row a later layer ruled, keep its `ruling` and `ruled_by`, and add to its reason the removed test whose job it took over and the planted faults it catches, from the verifier's or the judge's file. Otherwise keep the ruling its row has, `keep` when it has no row, and write it as ruled by the `judge`, or by the `maintainer` when the maintainer named a different takeover, and add the same sentences to its reason. For a second catcher, write instead that a planted fault showed it also catches the removed test's fault, and name that fault, because it took over no job. When that register does not exist yet, start it with the header line of any other register. `draft` keeps the row when that module's own apply step runs. Search every register, this module's included, with one grep over `planning/test-audit/register/*.tsv` for a reason that names a test this change renames, merges or removes, and correct each one. When the judge or the classifier asked for a fault to be planted before anyone proposes removing a test it keeps, add the request to that test's row as a `Later audit:` sentence. Empty `audit_commit` and `fingerprint` on every row you change in any register.
   - `draft` names the rows it kept as ruled. Each is a row a later layer ruled, in an earlier audit or by an earlier apply step of this batch, for a test this audit's classifier judged again. Re-read its reason against the test as it is now and against the classifier's new row. Correct the reason, or write the row again from the classifier's verdict, and empty its `audit_commit` and `fingerprint` either way. Keep each sentence that records a removed test whose job this test took over, and keep that row's `ruled_by`. Follow the rules for every register row and for a row a later layer ruled, in `rubric.md` (The register), and leave `audit_commit` and `fingerprint` empty.
   - Set `ruling`, `ruled_by` and `confidence` as the rubric's register table says. The `ruling` cell of that table says which ruling a narrowed, merged or removed test gets. A test the judge examined is `judge` with confidence `-`. A test the maintainer ruled on differently, or added, is `maintainer` with confidence `-`, and so is a `rewrite` or `query` verdict the maintainer accepted.
   - Put a `Later audit:` follow-up on a live row, never on a `removed` row (`rubric.md`, The register).
   - Take the reason from the judge's table when the judge examined the test, otherwise from the maintainer's answer, not from the classifier alone.
   - Check every takeover claim you copy from the judge, the verifier or the ledger against the takeover's body. When a claim overstates what the body does, correct the wording and report the correction.
   - Take every claim about which code a test reaches, or which fault it catches, from a fault that the verifier's, the mutation check's or the judge's file records. When the reason needs a claim that none of them records, plant the fault yourself or leave the claim out. Plant faults only in a `/tmp` worktree (`git worktree add --detach /tmp/<name> HEAD`), restore each one, and remove the worktree at the end. Set `PYTHONDONTWRITEBYTECODE=1` and delete the worktree's `__pycache__` folders under `src/` before each run, because a fault that keeps a file's size can leave stale bytecode in use. Run the whole suite for any claim about other tests. A fault run over one merged test supports "fails this row and not the other", never "fails this row only", because a claim that only one test catches a fault needs a whole-suite run. Never state a probe result you did not run.
   - Check every issue number you cite with `gh issue view <n> --json title,body`.
   - Write British English, with no em dashes and no sentence hinged on a colon.

3. Do not stamp. The coordinator commits the test change and then stamps. Check your work with these two commands, once for each module whose register you changed.

   ```bash
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py check <module>
   uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py check --names <module>
   ```

   The first must show no function as `new` or `gone`, apart from the functions of a register you started for a takeover, which stay `new` until that module's own apply step runs, and no `changed` line with a note. An unstamped row shows as `changed`, and an unstamped `removed` row as `source moved` with the note `unknown audit commit`. The second prints what each row a later layer ruled follows, from earlier audits too. Check the rows you wrote. Each must follow at least one definition, unless its test runs no `src/prov` code. No token may match an unrelated definition. A token marked `(matches nothing)` must be a constant or a name outside `src/prov`, never a misspelt definition. Only a test this change removed or folded in may show `(no such test)`.

## Report

Report only: the diff stat, the suite counts and the coverage `TOTAL` line against `main`, the summary line of `draft`, the number of register rows by ruling and by `ruled_by`, the output of the two checks, each fault you planted with its result, each takeover claim you corrected, each follow-up for a test outside `<module>` for the coordinator to place, and any concern.

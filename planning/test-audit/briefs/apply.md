# Brief: apply the rulings and write the register (layer 7, Sonnet, medium effort)

Send this brief after the maintainer has ruled. Fill `<repo>`, `<work>`, `<module>`, `<branch>` and the maintainer's ruling (the judge's final list as accepted or amended).

---

You are applying the accepted rulings of a test-suite audit of the Python library `prov` to one test module and recording the standing ruling for each of its test functions. Work in the checkout at `<repo>` on the branch `<branch>` (confirm the branch before you edit). Do not push and never run `git stash`. Run `uv` only in that checkout or in a `/tmp` worktree you create for planted faults, and never run mutmut. Do not commit; the coordinator reviews and commits. Change no file in `<repo>` except `src/prov/tests/<module>.py` and `planning/test-audit/register/<module>.tsv`. Name files literally in every command.

## Read first

- `<repo>/planning/test-audit/rubric.md`, above all the section "The register".
- `<work>/ledger/<module>.md` (the classifier's verdict and reason for every function), `<module>.verify-removal.md` and `<module>.mutation-removal.md` for removals, `<module>.verify-merge.md`, `<module>.mutation-merge.md` and `<module>.merge.patch` for merges, and `<module>.judge.md`.
- The maintainer's ruling:

<the ruling>

## Step 1: apply the test change

- For a removal, delete exactly the items on the accepted list and nothing else.
- For merges, apply only the accepted merges from the patch, with the changes the judge required. Leave out every hunk of a merge ruled `keep`, and every import only such a hunk needed.
- Run `ruff check` and `ruff format --check` on the module, then the whole suite with coverage: `uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider --cov=prov --cov-branch --cov-report=term`. The `TOTAL` line must show the same statements missed and the same branches partly covered as the same run on `main`. Stop and report any difference. Compare the passed, skipped and xfailed counts with the expected change, and stop and report any difference you cannot account for item by item.

## Step 2: write the register file

Write `planning/test-audit/register/<module>.tsv` with one row for each test function now in the module, and one `removed` row for each function that left it. Follow "Rules for a register row" in `rubric.md`. Leave `audit_commit` and `fingerprint` empty on every row you add or change.

- Set `ruling`, `ruled_by` and `confidence` as the rubric's register table says. A test the judge examined, including one it discussed beyond the proposals (its flags or notes), is `judge` with confidence `-`. A test only the classifier judged is `classifier` with the classifier's confidence. A test the maintainer ruled on differently, or added, is `maintainer` with confidence `-`.
- Take the reason of a row that a later layer judged from the judge's table, not from the classifier.
- Treat every reason as a claim about the code, and check it before you write it, by "Rules for a register row" in `rubric.md`. The classifier's reason was written from reading and is often wrong about which code an input reaches.
  - Trace each input through the code it reaches before you describe it.
  - Back every claim about which code a test reaches, and every claim that a test catches a fault, with a fault you planted and ran. Plant faults only in a `/tmp` worktree (`git worktree add --detach /tmp/<name> HEAD`), restore each one, and remove the worktree at the end. Run the whole suite for any claim about other tests. Never state a probe result you did not run.
  - Check every issue number with `gh issue view <n> --json title,body`.
  - Write British English, with no em dashes and no sentence hinged on a colon.

Do not stamp. The coordinator commits the test change, then stamps the register, so that each row names the commit where its test and the tests its reason names reached their final form. To see that nothing else is off before you report, stamp a copy in a `/tmp` worktree of the branch with your test change applied, and run `check` there:

```bash
uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py stamp <module>
uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py check <module>
```

Every function must come out `unchanged` there, except a row whose named sibling your own change removed or edited. List those rows in your report. Stop and report anything else.

For the coordinator: `stamp` keeps the anchor of a row whose own text is unchanged, so a row that names a test this change removed, merged or edited still comes out `source moved` after the stamp. Re-read each such reason against the change, correct it if it no longer holds, then empty its `audit_commit` and `fingerprint` and stamp again.

Then list, for each row, the backticked tokens that `register.named()` matches against `register.tree_definitions()` (with `planning/test-audit/scripts` on `sys.path`). Every row must track at least one definition unless its test runs no `src/prov` code, and no token may match an unrelated definition.

## Report

Report only: the diff stat, the suite counts and the coverage `TOTAL` line against `main`, the number of register rows by ruling and by `ruled_by`, the output of `check`, the tracked-name result, each planted fault with its result, and any concern.

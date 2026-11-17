# Brief: apply the rulings and write the register (layer 7, Sonnet, medium effort)

Send this brief after the maintainer has ruled. Fill `<repo>`, `<work>`, `<module>`, `<branch>` and the maintainer's ruling (the judge's final list as accepted or amended).

---

You are applying the accepted rulings of a test-suite audit of the Python library `prov` to one test module and recording the standing ruling for each of its test functions. Work in the checkout at `<repo>` on the branch `<branch>` (confirm the branch before you edit). Do not push and never run `git stash`. Do not commit; the coordinator reviews and commits. Change no file except `src/prov/tests/<module>.py` and `planning/test-audit/register/<module>.tsv`. Name files literally in every command.

## Read first

- `<repo>/planning/test-audit/rubric.md`, above all the section "The register".
- `<work>/ledger/<module>.md` (the classifier's verdict and reason for every function), `<module>.verify.md`, `<module>.mutation.md`, `<module>.judge.md`, and for merges `<module>.merge.patch`.
- The maintainer's ruling:

<the ruling>

## Step 1: apply the test change

- For a removal, delete exactly the items on the accepted list and nothing else.
- For merges, apply only the accepted merges from the patch, with the changes the judge required. Leave out every hunk of a merge ruled `keep`, and every import only such a hunk needed.
- Run `ruff check` and `ruff format --check` on the module, then the whole suite with coverage: `uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph pytest -q -p no:cacheprovider --cov=prov --cov-branch --cov-report=term`. Compare the `TOTAL` line (statements missed, branches partly covered) with the same run on `main`, and the passed, skipped and xfailed counts with the expected change. Stop and report any difference you cannot account for item by item.

## Step 2: write the register file

Write `planning/test-audit/register/<module>.tsv` with one row for each test function now in the module, and one `removed` row for each function that left it. Leave `audit_commit` and `fingerprint` empty.

- `ruling` and `ruled_by` follow the highest layer that examined the test. A classifier `keep` nobody else examined is `keep`, `classifier`, with the classifier's confidence. A test the judge ruled on is `judge`. A test the maintainer ruled on differently from the judge is `maintainer`. The confidence is `-` for every row a later layer examined.
- Write each `reason` for a reader who has not seen the ledger: what the test pins, and what would go unnoticed without it. One or two sentences, no tab and no newline.
- Cite the issue, the conformance row or the document that underpins the test, as `#532`, whenever one exists.
- When the reason depends on how the code is written, name the function or the class in backticks, as `_decode_time`.
- A test that was proposed for removal and kept records the fault that kept it. A `narrowed` or `merged` row says what went or what was folded in, and why nothing was lost. Take these reasons from the judge's table, not from the classifier.

Then stamp and check:

```bash
uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py stamp <module>
uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph python planning/test-audit/scripts/register.py check <module>
```

Every function must come out `unchanged`. A row reported as `source moved` straight after stamping means the reason names a definition ambiguously; reword it.

## Report

Report only: the diff stat, the suite counts and the coverage `TOTAL` line against `main`, the number of register rows by ruling and by `ruled_by`, the output of `check`, and any concern.

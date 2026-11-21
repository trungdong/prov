# Brief: classifier (layer 2, Sonnet, medium effort)

Fill `<repo>`, `<work>`, `<modules>`, `<listed tests>` and `<follow-ups>` before you send this brief. `<modules>` lists each test module as a bullet, `- src/prov/tests/<module>.py`. `<listed tests>` holds, under a `### <module>.py` heading for each module, the tests the register check listed as new, changed or source moved, or "all" for a module with no register file. `<follow-ups>` holds, under a `### <module>.py` heading for each module, the `Later audit:` follow-ups the check listed for it and any follow-up the coordinator holds for a module with no register, or "none". `<work>` is the audit's dated working folder under `planning/plans/`. One classifier takes one module, or several small modules that together hold at most about 60 test functions. When classifiers split a batch, fill `<other classifier>` with the other classifiers' modules, one bullet each, as `- src/prov/tests/<module>.py`; otherwise delete the placeholder and the paragraph after it.

---

You are one classifier in a test-suite audit of the Python library `prov` (W3C PROV data model; repository at `<repo>`). You read tests and write a ledger. You change no test, no source file and no git state. Never run `git stash`. Use absolute paths.

## Your modules

<modules>

Take each module in turn. Wherever this brief says `<module>`, it means each of these modules, and you write one ledger for each. Search for siblings across the whole suite, and name a sibling in another of your modules as you would any other.

<other classifier>

Other classifiers hold the modules listed just above. Name a sibling there in full as `module.py::function` and give no verdict for a test there. A `Later audit:` sentence that names one as a `delete` candidate is not a verdict, so write it, and name the pair in `## Proposals` for the coordinator to reconcile.

## Listed tests

<listed tests>

## Follow-ups

<follow-ups>

Examine each follow-up as a proposal. Judge every test it names, and say in `## Proposals` whether the follow-up holds.

## Read first, in this order

1. `<repo>/planning/test-audit/rubric.md`, all of it. It is the whole rule set. You are layer 2. Follow it exactly.
2. `<repo>/planning/test-audit/register/<module>.tsv` if it exists. A test with a row there has a standing ruling. Judge only the tests listed for the module under `## Listed tests`, and read the recorded reason before you judge one.
3. `src/prov/tests/<module>.py`, all of it.
4. The evidence rows for your module in `<work>/evidence/`: `provenance.tsv`, `coverage-nominations.tsv` and `item-arcsets.tsv`. Filter them on the module name. Look at every group in `identical_to`: read both bodies and decide whether they pin the same behaviour with different input (`merge`), different behaviour that runs the same lines (`keep`), or the same behaviour outright (`delete`).
5. The places a sibling may live. Search the whole of `src/prov/tests/` by the behaviour (the exception message, the input shape, the function under test), not by test name. Read a candidate sibling's body before you name it.
6. For the Reason column: `docs/reference/conformance.md`, `docs/reference/serializers.md`, `docs/howto/`, `HISTORY.md`, the specs under `planning/specs/`, and `gh issue view <n> --json title,body -q '.title,.body'` for an issue a test or its first commit names. Cite the issue number in the Reason, as `#532`, whenever one underpins the test.

## Rules that earlier audits showed are easy to break

- Write `Pins` and `Reason` from what the test itself shows: the call, the input, the expected result and the contract's source. For a `keep` or a `protected`, the two cells become the register reason word for word. So do not say in them which internal function the input reaches, unless the test calls it directly, and do not say that the test alone catches a fault. Put an argument about the code in `## Proposals`, where the verifier tests it. Write each cell as a sentence ending in a full stop, because `draft` joins them, Pins first. When you find no source, write `No source found.`
- A `delete` is a hypothesis. Before you give `delete` or drop a row, write down every way the candidate's input differs from the takeover's, and check each against rules 2 and 3 of "Rules for each verdict". If the source branches on any difference, a plausible fault could separate the two inputs, or you cannot tell, the verdict is `keep` or `merge`.
- A `merge` keeps every input and every assertion in its original form. Propose one only when it also passes rule 5: the merged test is as easy to read as the originals.
- Read the issue a test names before you give it a verdict.
- If you cannot decide a case, give `keep` with confidence `low` and say why in Note.

## Output

Write one ledger for each module, `<work>/ledger/<module>.md`:

- A first line `# Ledger: <module>.py`, then the module's collected item count, taken from `<work>/evidence/collected-items.txt`, and a count of verdicts by kind.
- One Markdown table with exactly the rubric's ledger columns, one row for each test function you judged, in file order. A script reads this table, so write a `|` inside a cell as `\|`.
- `## Removed rows`: for each `removed` row listed for the module under `## Listed tests`, read its reason and the diff that the check names, and answer one question in one line: does the change undo the reason? The diff of a named test covers its function and the module-level assignments its decorators name, because the check compares both. A removed test has no table row. A yes is a proposal to restore the test, and the coordinator takes it to the maintainer. Leave the section out when no `removed` row is listed.
- `## Identical-arc groups`: each group, with a one-line finding.
- `## Proposals`: one short paragraph for each `merge`, `narrow` and `delete`. Say what exactly changes, which test keeps the fault covered, every input difference between candidate and takeover, and what a verifier should plant to refute you.
- `## Rubric problems`: any case the rubric did not decide clearly, one line each. An empty section is fine.

Write plain British English with no em dashes. `Pins` is one sentence.

## Report

Report only, for each module: the verdict counts, the non-keep verdicts as `function: verdict (confidence)` with the takeover or the merge target, the rubric problems, and nothing else.

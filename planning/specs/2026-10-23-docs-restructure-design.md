# Documentation restructure between specs 2 and 3

**Date:** 2026-10-23
**Status:** Approved; decisions Q1 to Q7 settled 2026-10-23
**Written against:** `main` 5edd0ff, with every PR of 3.3.0 spec 2 merged
**Scope:** Eight documentation PRs, D1 to D8. They land after spec 2 and before any spec 3
PR. No library behaviour changes, apart from docstrings and the `#:` comments in
`constants.py`.

## 1. Purpose

Many PRs each added a sentence to the documentation, so the facts are mostly correct but
the pages no longer serve their readers. A typical reader of each page has to work through
rare cases, error-path detail, version history and specification clause numbers before
reaching the few points they came for. Separately from that, parts of the API reference
render nothing useful, and the gate commands are copied onto four pages that no longer
agree.

These PRs land now, not at the release, for two reasons:

- **Spec 3 rewrites some of these pages.** Spec 3 (#449, #450, #131, #573, #609, #620)
  is not yet written. If the pages are restructured first, spec 3 is written against the
  new layout, and its PRs add to lean pages instead of adding more caveats to the old
  ones.
- **Some defects already cause harm.** The docs-review brief's "Canonical statements"
  table is wrong and would put errors back into any page edited by the brief. The constants
  reference shows none of the constants the tutorial uses. The gate commands differ
  between `CONTRIBUTING.md`, `CLAUDE.md`, the PR template and the runbook.

A pre-release audit on the 3.3.0 freeze commit checks the result. This spec does not cover
that audit.

## 2. Evidence

Everything below was measured on `main` 5edd0ff.

**Inventory.** There are 47 tracked Markdown files outside `planning/`, plus 15 specs, a
triage file and the test-gap checklist inside it.

| Group | Files | Readers |
|---|---|---|
| Published site | 26 pages of their own (`docs/`, excluding the four include stubs and the two excluded pages), plus `README.md`, `HISTORY.md`, `AUTHORS.md` and `CONTRIBUTING.md` through includes | Library users |
| Project pages at the root | `ROADMAP.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CLAUDE.md`, the PR template | Users, contributors, agents |
| Maintainer pages | `docs/releasing.md`, `docs/dependencies.md`, `benchmarks/README.md`, five fixture READMEs under `src/prov/tests/` | Maintainer, contributors |
| `planning/` | 15 specs, the triage file and the test-gap checklist | Historical record |

**Findings that still hold after spec 2:**

| # | Page | Finding |
|---|---|---|
| E1 | `README.md` | There is no install command and no code. 19 of the 52 lines are the "Status" and "Supported versions" sections, which tell release history and repeat `SECURITY.md`. |
| E2 | `docs/reference/constants.md` | It promises "one `QualifiedName` constant per record type and per formal attribute (`PROV_ENTITY`, …)". None of the 84 `PROV_*`/`XSD_*` constants renders, and neither do the `PROV`, `XSD` and `XSI` namespaces, because none has a docstring or a `#:` comment. |
| E3 | `docs/reference/model.md` | 18 `:inherited-members:` options repeat every `ProvRecord` method on each subclass. The rendered page is about 30,000 words, with `get_attribute` appearing 198 times. `ProvRecord`, `ProvElement`, `ProvRelation`, the `*Ref` aliases, `OptionalID`, `RecordAttributesArg` and `parse_xsd_datetime` have no entry, although all of them are in `test_public_api.py`. |
| E4 | Whole site | `sphinx-build -n` reports about 300 unresolved references to `prov` names, without counting standard-library names, because the intersphinx inventories could not be fetched. No CI job builds the docs, and `.readthedocs.yml` does not fail on warnings. |
| E5 | `docs/reference/conformance.md` | Spec 2 added C9 to C11, so the page now has eleven caveats. Two are permanent losses (C1 and C2), and the rest are edge cases, but all are listed together. Before the caveats, the intro spends a paragraph on how the page is organised. About 100 of the 269 lines cover reading other producers' files and the test corpus. |
| E6 | `docs/explanation/unification-flattening.md` | Line 12 says both transformations "return a new document"; line 25 says `flattened()` returns the document itself. The worked example comes after about 70 lines of rules and limits. "Four limits" and "How this differs from the specification" repeat the inference point. |
| E7 | `docs/explanation/architecture.md` | About half the page is for contributors: PROV-N lexer internals (lines 63 to 107), serializer conventions (109 to 130) and tests (139 to 152). Line 39 repeats the "new documents" claim. Line 105 cites the internal `provn_lexer.ProvNSyntaxError` path, where the public path is `prov.serializers.provn.ProvNSyntaxError`. |
| E8 | Format how-tos | Five pages repeat the same file, string and stream round trip. Each restates its own position in the auto-detection order. `provjsonld.md` repeats the conformance page's input scope, gives a 22-line `mentionOf` example and a media-type section. `provo-rdf.md` gives a worked example of C1. `provn.md` quotes memory and throughput figures ("4 KiB per statement on CPython 3.12… 2023 laptop") and has an "Attribute order is stable" section that applies to every format. |
| E9 | `docs/howto/graphics.md` | It ends with an "All together" block that restates the defaults, and it never mentions `ProvBundle.plot()` or `prov[plot]`. |
| E10 | `docs/howto/typing.md` | Line 6 says "It describes `prov` 3.2.2 and later". The `Iterable` caveat sits in the middle of the main path. |
| E11 | `docs/upgrading-3.0.md` | 24 table rows, most of which say "None" or "only if you byte-compare". Five need action: #34, #77, #259, #228 and #273. The `#removed` link on line 24 is broken. |
| E12 | `docs/whats-new-3.md` | A paragraph of benchmark percentages. A section on `2.1.1`/`1.5.1` pins that overlaps "Moving from 2.x". |
| E13 | Gate commands | The commands appear in `CONTRIBUTING.md`, `CLAUDE.md`, `docs/releasing.md` and the PR template. The template runs `ruff` on `src/` only and omits Codacy. The runbook's pre-flight also runs `ruff` on `src/` only. `CLAUDE.md` says Codacy blocks on "any severity", while the runbook says "at least minor". `CONTRIBUTING.md` never mentions Codacy. The template says "Pull Request Guidelines", but the heading is "Pull request guidelines". |
| E14 | `docs/releasing.md` | Section 2 says "Five files", but the 2.x appendix says "§2's four stamped files". Section 2 quotes the conformance sentence as "last revised for the X.Y.Z release (YYYY-MM-DD)", but the page says "it was revised for 3.2.3". About 70 lines tell stories from past releases inside the procedure: a 504 response, a dropped `pull_request` event, a Graphviz stall, simple-index lag, `VIRTUAL_ENV` leakage and token expiry. |
| E15 | `HISTORY.md` | The switch from the 20% baseline check (3.2.0, line 644) to the 10% A/B check in `benchmarks/ab.py` (commit cbacfec, shipped in 3.2.3) is recorded nowhere. 3.2.2's one behaviour change (`Iterable[...]` is reported) is halfway through an 18-line bullet. The link to the changelog archive is a GitHub URL, although both pages are on the site. |
| E16 | `planning/` | There is no README saying the folder is a historical record. Shipped specs still say "Draft for maintainer review" (3.1.1, 3.2.0), "Approved design, pending implementation planning" (modernisation roadmap) or have no status line (docs review, spec 2). The docs review's "Canonical statements" table says PROV-N is write-only, `prov-convert` input is always PROV-JSON and the next release is 3.2.0. `CLAUDE.md` names the July test-suite migration spec as the "Design authority" for tests. |
| E17 | `docs/explanation/prov-dm.md` | It is fit for purpose. The only problem is scattered § citations and "The quoted wording is PROV-DM's". |

**Pages that are fit for purpose and stay out of scope:**

- `installation.md`
- `howto/cli.md`
- `howto/networkx.md`, apart from the references D3 fixes
- `provxml.md`, apart from D6's shared-page change
- `prov-dm.md`, apart from E17
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, `AUTHORS.md` and `ROADMAP.md`
- `changelog-archive.md`, apart from its return link

## 3. Rules every PR applies

These rules extend the style brief in `2026-09-10-docs-review.md`. D1 marks that brief as
historical, and these rules replace its "Canonical statements" table.

1. **Most readers first.** Each page and each section opens with what most of its readers
   need. A rare case goes in the docstring, in the conformance page, or in an "Edge cases"
   section at the bottom of the page. It never goes in the middle of the main path.
2. **One home per fact.** Every other page links to that home and does not restate the
   fact. The homes:

   | Fact | Home |
   |---|---|
   | Extras | `installation.md` |
   | Auto-detection | D6's shared page |
   | Format limitations | `conformance.md` |
   | Support policy | `SECURITY.md` and `ROADMAP.md` |
   | Gate commands | `CONTRIBUTING.md` |
   | Equality rules | `reference/model.md` |

3. **No release history outside `HISTORY.md` and the two 3.0 pages.** This means no
   "since X.Y", no "3.2.0 added", and no benchmark percentages.
4. **Nothing that dates.** No measured figures tied to a machine or an interpreter, and no
   dates that will pass, except the dates of the support policy and the per-release
   conformance sentence.
5. **Spec references are links, not clause numbers.** A section number is cited only where
   the page's job is conformance, which means `conformance.md` and code comments.
6. **Issue links are for open limitations and decisions a reader may want to follow.**
   They are not for the history of a fix.
7. **No change to behaviour.** A sentence that turns out to be wrong is corrected against
   the code and noted in the PR body. The code is never changed to match the sentence.

## 4. The PRs

### D1. Mark `planning/` as a historical record (E16)

- Add `planning/README.md`. It says what the folder holds and that a spec is a record of
  how a decision was made, not maintained after its release ships. It says current truth
  lives in `ROADMAP.md`, `docs/` and `CLAUDE.md`, and that plans are local and gitignored,
  as `CLAUDE.md` says. It indexes each spec, the triage file and the checklist with one
  line each: date, release and status.
- Correct each status line and leave the spec bodies alone:
  - Shipped specs read `**Status:** Complete; shipped in X.Y.Z`.
  - `2026-07-04-3x-typing-api-improvements.md` reads "Closed", naming what shipped and
    linking the issues still open.
  - Spec 2 gains a status line.
  - Spec 1 and spec 2 of 3.3.0 read "In progress".
- The "Canonical statements" table in `2026-09-10-docs-review.md` goes. In its place, one
  sentence points to section 3 of this spec (Q1).
- `CLAUDE.md`'s "Design authority: `planning/specs/2026-07-06-test-suite-redesign.md`"
  goes. The bullets that follow already hold the rules agents need.

**Acceptance.** No spec of a shipped release reads "Draft", "pending" or "Approved" without
"Complete". `grep -rn "write-only" planning/` finds nothing outside a quoted history.

### D2. Contributor material has one home (E7, E13)

- `CONTRIBUTING.md` step 6 becomes the canonical list of gates:
  - Add the `codacy-analysis analyze --files <changed files>` line.
  - Add one sentence: Codacy's Cloud gate blocks on a single finding, markdownlint
    included. The severity wording depends on Q2.
  - Add the advisory `own-warnings` job in one sentence.
  - "Pull request guidelines" gains the `HISTORY.md` entry under the unreleased version.
- `CLAUDE.md`'s "Gates every PR must pass" block keeps its commands, since agents read
  `CLAUDE.md` and not `CONTRIBUTING.md`. It must match step 6 character for character, and
  it gains the sentence "`CONTRIBUTING.md` step 6 is the canonical list; change both
  together." The severity contradiction is settled by Q2.
- The PR template's command checkbox becomes "The checks in CONTRIBUTING.md step 6 pass
  locally", and the guidelines heading is cited exactly.
- `docs/explanation/architecture.md` keeps the user overview: layers, object model,
  serializers and format detection, and extras. Line 39 is corrected:
  - `unified()` returns a new document.
  - `flattened()` returns a new document, or the document itself when it has no bundles.
- Three sections move unchanged to a new page for contributors (Q3): "The PROV-N parser",
  "Conventions for serializers" and "Tests". The `ProvNSyntaxError` reference changes to
  the public path. Spec 3's #450 later moves the parser section into the module
  docstrings or edits it there.
- `CLAUDE.md`'s two pointers to `architecture.md` ("is the overview … tests" and
  "Conventions for serializers") point to where each section now lives.

**Acceptance.**

- `diff` of the command blocks in `CONTRIBUTING.md` and `CLAUDE.md` is empty.
- `architecture.md` is under 80 lines.
- `sphinx-build -W` is clean.
- `grep -rn "architecture.md" CLAUDE.md docs/` resolves every pointer to a section that
  exists.

### D3. The API reference documents the public API (E2, E3, E4)

- **`constants.py`.** Each public constant gets a one-line `#:` comment, grouped under the
  existing comments: namespaces, record types, formal attributes, XSD datatypes and lookup
  tables (Q4). `constants.md`'s intro then describes what renders.
- **`model.md`.**
  - Add `ProvRecord`, `ProvElement` and `ProvRelation` with `:members:`, under a "Records"
    section before "Elements".
  - Remove every `:inherited-members:` and keep `:show-inheritance:`.
  - Add the public aliases that signatures name (`EntityRef`, `ActivityRef`, `AgentRef`,
    `GenerationRef`, `UsageRef`, `InfluencerRef`, `OptionalID` and `RecordAttributesArg`)
    under "Type aliases", using `autodata` with `:no-value:` and a one-line docstring each.
  - Add `parse_xsd_datetime` under a "Functions" heading.
  - Spec 2's "Equality" paragraph stays where it is.
- **`serializers.md`.**
  - `ProvNSyntaxError` is documented from `prov.serializers.provn`.
  - The "Reading documents" paragraph keeps its first two sentences. The rest (keyword
    pass-through and the `TypeError` reasoning) moves into the `prov.read` docstring,
    which spec 2's text already partly covers.
- **`docs/conf.py`.** Set `nitpicky = True`, with a `nitpick_ignore` list for the private
  names that public annotations expose (`_SupportsItems`, `_R`), each with a comment.
  `prov.graph.INFERRED_ELEMENT_CLASS`, which `graph.md` references, gets an entry there. Add a docs build to CI with `-W -n` (Q5). This changes tooling, so
  update the Setup section of `CLAUDE.md` and `docs/dependencies.md` in the same PR.
- Fix the references in the how-tos that the build then reports. Expect the ones in
  `networkx.md`, `typing.md` and `graphics.md`.

**Acceptance.**

- `sphinx-build -W -n` is clean on a machine that can reach the intersphinx inventories.
- The rendered `constants.html` lists `PROV_ENTITY`, `PROV_TYPE` and `XSD_STRING`.
- The rendered `model.html` is under 12,000 words, and the PR body gives the number.
- `test_public_api.py` is unchanged.

### D4. README for someone deciding whether to use `prov` (E1)

- Add an "Install" section: `pip install prov`, one sentence that formats other than
  PROV-JSON, PROV-N and PROV-JSONLD need an extra, and a link to the installation page.
- Add a "Quick start" example of at most ten lines: build an entity, an activity and a
  generation, then print `get_provn()` and save PROV-JSON. Show the output. Use
  `import prov.model as pm`.
- Replace "Status" and "Supported versions" with two lines that link to
  "What's new in 3", `ROADMAP.md` and `SECURITY.md`. The announcement-post link moves into
  the first of those two lines.
- Keep the feature list, the badges and the dependents line. The runbook's section 2 relies
  on the feature list for PyPI.

**Acceptance.**

- The example runs and prints the shown output.
- `uv build` succeeds, and `twine check dist/*` passes if `twine` is available.
- The README is no longer than it is now.

### D5. Conformance and explanation pages (E5, E6, E17)

**`conformance.md`:**

- The intro shrinks to the first paragraph, including the per-release "revised for"
  sentence, followed by a three-line "Summary":
  - Every concept round-trips through every format, with two permanent exceptions, C1
    and C2.
  - The values table says how literals behave.
  - Readers accept some output from other producers, listed at the end.
- "Caveats" becomes three groups. The numbers C1 to C11 stay fixed, because table cells,
  issues and other pages cite them:
  - "Permanent limitations": C1 and C2.
  - "Format notes": C8.
  - "Edge cases": C3 to C7 and C9 to C11, at the end of the page.
- New order: Summary, Reading the tables, the six components, Values, Permanent
  limitations, Format notes, Not implemented, Reading other producers' output, Edge cases,
  Corpus evidence, Related pages.
- The PROV-N profiles table moves to `provn.md` "Choose a parsing profile", which already
  explains profiles. The conformance page keeps one sentence and a link.
- The "Result" cells of the corpus table keep their counts and drop the lists of reasons.
  The corpus README already names every file and its reason.

**`unification-flattening.md`:**

- Line 12 is corrected the same way as `architecture.md`.
- The `unified()` worked example moves directly after the rules in "What `unified()`
  does".
- "Four limits" and "How this differs from the specification" merge into one closing
  section, "Relation to PROV-CONSTRAINTS". It keeps:
  - only identifiers drive merging;
  - the type-compatibility rule;
  - no inference;
  - not a validator.

  The `-` placeholder point shrinks to two sentences there. #62 is linked once.

**`prov-dm.md`:** remove the § citations from the prose and the "quoted wording" lines.
The table headers that cite PROV-DM sections stay.

**Acceptance.**

- The C1 and C2 summary appears within the first 15 lines of `conformance.md`.
- Every `C<n>` cited in a table cell still resolves to a caveat.
- `unification-flattening.md` is under 180 lines.
- Every Python block on an edited page runs.

### D6. One page for reading and writing, lean format pages (E8, E9)

- Add `docs/howto/read-write.md`, "Read and write documents", first in the how-to
  toctree. It holds:
  - serialise to a file, a string and a stream;
  - deserialise from each;
  - `prov.read()` and auto-detection, moved from `provjson.md` with its `(auto-detect)=`
    label, so existing `{ref}` links resolve;
  - the format table: name, extra, read, write, usual file extension and media type;
  - how errors surface: each format raises its own exception, and malformed JSON raises
    the standard library's;
  - "Attribute order is stable", moved from `provn.md`.
- Each format page then holds:
  - one paragraph on the format and its extra;
  - a minimal round trip that links to the shared page;
  - its own options: `context` for PROV-JSONLD, `rdf_format` for PROV-O, `force_types`
    for PROV-XML, and `get_provn()`, `profile` and `strict` for PROV-N;
  - a "Limitations" line that links to the conformance caveat.
- These sections go from the format pages:
  - `provjsonld.md`: "Input scope", the `JSONDecodeError` demo and the `mentionOf` example
    (one sentence and a link to C2 instead), and "Media type and file extension", which
    moves into the format table.
  - `provo-rdf.md`: the `BadSyntax` and shared-identifier examples (one sentence and a link
    to C1 instead).
  - `provn.md`: "Large documents" (Q6) and the lenient-mode details in the profile section,
    since the profile table D5 moves there already says what each profile accepts.
- Spec 3 rewrites the PROV-N output examples in `provn.md` and the tutorial (#131 and
  #449), so D6 leaves those examples as they are. The tutorial's Bundles section is spec
  3's to rewrite, with #449 and #573.
- `graphics.md`:
  - Delete "All together".
  - Add "Plot in a notebook or window" for `ProvBundle.plot()`, which needs `prov[plot]`.
    `installation.md` already lists that extra.
- `serializers.md` and `conformance.md` "Related pages" link the shared page.

**Acceptance.**

- Each of `provjson.md`, `provjsonld.md`, `provxml.md` and `provo-rdf.md` is under 80
  lines.
- Every Python block on every edited page runs.
- `sphinx-build -W -n` is clean.

### D7. Upgrade, what's new, typing and changelog (E10, E11, E12, E15)

**`upgrading-3.0.md`:**

- The table keeps the rows that need action: #34, #77, #259, #228 and #273. #217 moves out
  of the table into a short "Documented limitation" paragraph that links C1.
- One sentence replaces the other 18 rows: they change serialised bytes, not meaning, and
  HISTORY's 3.0.0 section lists each one.
- The `#removed` link becomes a MyST target, `(removed)=`, above the heading.
- The page is otherwise kept as the stable migration record.

**`whats-new-3.md`:**

- Delete the benchmark paragraph under "Two-way PROV-N".
- Merge the `2.1.1`/`1.5.1` section into "Moving from 2.x".
- The extras list links `installation.md` instead of restating the table.
- "What comes next" stays for the release PR (spec 1, 7.2).

**`typing.md`:**

- Delete "It describes `prov` 3.2.2 and later".
- The `Iterable`/`Collection` paragraph and its example move to an "Edge cases" section at
  the bottom.
- The link to `prepare-for-3-3` stays for the release PR, which decides what that page
  becomes (spec 1, 7.2).

**`HISTORY.md`:**

- 3.2.3's "Project" section gains the bullet it is missing: "The benchmark check compares
  each change with its parent on one runner and fails on a confirmed 10% slowdown;
  `benchmarks/ab.py` replaces the committed baseline." 3.2.0's line stays, since it was
  true of 3.2.0.
- 3.2.2's `Iterable[...]` sentence becomes its own bullet, headed "Type checking".
- The link to the changelog archive and the archive's link back become `{doc}` links.
  `HISTORY.md` is also rendered on GitHub, so keep a plain-text fallback sentence if `{doc}`
  shows raw (Q7).
- The released entries are otherwise left alone. Spec 1, 7.2 already sets 3.3.0's
  structure.

**Acceptance.**

- The `#removed` link resolves.
- `upgrading-3.0.md` is under 90 lines.
- `grep -n "3\.2\.2 and later" docs/` finds nothing.

### D8. The release runbook is a checklist (E13, E14)

- Add a "Checklist" at the top: one line per step of sections 1 to 7, each with its
  command or the file it touches, so the runbook can be followed without the prose.
- Section 1's gate commands match `CONTRIBUTING.md` step 6 (`ruff` on `src/ benchmarks/`),
  plus the steps only a release runs: `own-warnings`, `ab.py <previous tag>` and the wheel
  contents.
- The stories from past releases move into a closing "Troubleshooting" section, keyed by
  symptom:
  - `Error: Unauthorized` from `codacy`;
  - a Cloud-only Codacy finding;
  - "no checks" on a new PR;
  - a stalled "Setup Graphviz" step;
  - `no version of prov==X.Y.Z` after a release;
  - `VIRTUAL_ENV` leakage;
  - mypy on PyPy;
  - a feedstock merge refused for "base branch policy".

  Each entry gives the symptom, the cause and the fix, and names no past release.
- The 2.x appendix says "§2's stamped files", without a number, and says which of them
  apply on 2.x.
- Section 2's quote of the conformance sentence matches the page's actual sentence. If D5
  changes the sentence, both change together.
- `docs/dependencies.md`:
  - Refresh the "Last checked" line.
  - Add the `bench` group, which `CLAUDE.md` tells agents to sync.
  - Remove the history of pins that no longer bind: rdflib 6, the rdflib 7.3 warnings,
    "Removed in 2.3.0" and the Sphinx 9 cap history. Keep each pin's current reason.

**Acceptance.**

- The runbook's checklist names every command in its sections.
- No troubleshooting entry names a release number.
- `grep -n "four stamped" docs/releasing.md` finds nothing.

## 5. Sequence

| PR | Depends on | Why this order |
|---|---|---|
| D1 | none | It removes the stale brief before other docs PRs consult it |
| D2 | D1 | `CLAUDE.md` edits in D1 and D2 touch neighbouring lines |
| D3 | none | Nitpicky references then catch broken links in D5 to D7 |
| D4 | none | Independent |
| D5 | D3 | It moves the PROV-N profiles table that D6 receives |
| D6 | D5 | Its pages link the restructured caveats |
| D7 | D3 | `typing.md` references resolve once D3 lands |
| D8 | D2 | Its gate block matches the canonical one |

D3 and D4 may run in parallel with D1 and D2. Spec 3 is written after D6 merges, and it
names the pages it edits by their new sections.

**Left for spec 3:**

- the PROV-N output examples on every page (#131);
- the parser section on the contributor page, or its move into module docstrings (#450);
- the tutorial's Bundles section (#449, #573);
- the PROV-JSONLD node-reference rejection on the conformance page and in `provjsonld.md`
  (#609);
- the #620 row.

**Left for the release PR (spec 1, 7.2):**

- the 3.3.0 `HISTORY.md` structure;
- "What comes next";
- `SECURITY.md`;
- the ROADMAP rows;
- the "revised for" sentence;
- what `prepare-for-3-3.md` becomes once 3.3.0 is current.

## 6. Gates

The gates in `CLAUDE.md` apply. On top of those, each PR:

- builds the docs with `sphinx-build -W -n` from D3 on, and with `-W` before it;
- runs every Python block on the pages it edits;
- runs `codacy-analysis analyze --files <changed files>` and gets 0 issues;
- states in its body the line counts of the pages it edits, before and after.

D3 is the only PR that touches Python files, for docstrings and the `#:` comments. It runs
the full interpreter loop and `mypy`.

## 7. Out of scope

- The fixture READMEs under `src/prov/tests/`. They are long but rarely read; trimming
  them waits for a PR that touches their fixtures.
- Removing the leftover incident notes from `CLAUDE.md`, beyond D1 and D2.
- Rewriting released `HISTORY.md` entries into a new structure.
- Moving `releasing.md` and `dependencies.md` out of `docs/`. The exclusion in
  `docs/conf.py` is deliberate.
- The pre-release audit itself. It runs on the freeze commit.

## 8. Decisions

All settled 2026-10-23 by the maintainer. Section 2 was re-verified against `main`
5edd0ff before the rulings: every finding holds; E11's sentence replaces 16 rows of the
bug-fix table (22 rows, less the five action rows and #217), and E16 covers ten specs,
not four. The nitpicky build reports 301 unresolved references with the inventories
fetched; beyond the names D3 lists it reports `StreamOrPath`, `XSDQName`,
`nx.MultiDiGraph`, `pydot.Dot`, `pydot.core.Dot`, the `prov.serializers.provxml` and
`provrdf` module references and `ProvRecord.get_provn`, which D3 documents or ignores.

| # | Question | Recommendation | Decision |
|---|---|---|---|
| Q1 | What happens to the docs-review brief's "Canonical statements" table? | Delete it and point to section 3 here. A table of facts outside the pages that state them goes out of date at every release | As recommended |
| Q2 | Does Codacy's Cloud gate block on any severity or on "at least minor"? | The maintainer checks the Codacy gate setting. Both pages then say the same | Neither. Codacy's check is not a required status check on `main`; branch protection requires only the six pytest jobs. The maintainer reviews the Codacy findings on every PR by hand and merges with none outstanding, and does not want the check to block. `CONTRIBUTING.md`, `CLAUDE.md` and the runbook say that, quote no severity, and keep the local `codacy-analysis analyze` line with its "0 issues" expectation |
| Q3 | Where does the contributor material from `architecture.md` go? | A new published page, `docs/development.md`, "Developer guide", in the Project toctree next to Contributing. `CONTRIBUTING.md` stays about process and gates | As recommended |
| Q4 | `#:` comments in `constants.py`, or a hand-written list of `autodata` entries in `constants.md`? | `#:` comments. One source, and editors show them on hover | As recommended |
| Q5 | Should a docs build join CI, blocking or not? | Blocking, `-W -n`, in `CI.yml`. ReadTheDocs does not fail on warnings, and nothing else catches a broken reference | As recommended |
| Q6 | The PROV-N memory and throughput figures: move or delete? | Move a figure-free sentence to `provn.md` ("the parser reads the whole document into memory first; memory grows with the number of statements") and the figures to `benchmarks/README.md` | The sentence moves to `provn.md`; the figures are deleted, not moved. Rule 4 bans measurements tied to a machine, and `benchmarks/README.md` documents a tool, not results |
| Q7 | Do `{doc}` links in `HISTORY.md` render acceptably on GitHub? | Check one on GitHub before D7 merges. If they show raw, keep the full URL and add the `{doc}` link only in `docs/history.md` | No `{doc}` links. GitHub renders a MyST role as literal text, and `docs/history.md` is a bare include of `HISTORY.md`, so there is no place for a `{doc}` link GitHub does not also show. Both archive links keep their full GitHub URLs |

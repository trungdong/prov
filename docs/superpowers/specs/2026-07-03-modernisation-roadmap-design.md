# prov Modernisation & Hardening Roadmap — Design

**Date:** 2026-07-03
**Status:** Approved design, pending implementation planning
**Scope:** Modernise and harden the `prov` package (tooling, typing, tests, docs, standards conformance) plus known bug fixes, followed by one new feature: a PROV-JSONLD serializer (Phase 5). Other large features (PROV-N parser, PROV-Dictionary, PROV-CONSTRAINTS validation) are out of scope, tracked as a separate post-3.0 features backlog.

## Context

`prov` is a mature (10+ years), widely-used Python implementation of W3C PROV-DM.
It is a dependency of ProvStore and other community projects, so public API
stability is paramount. Current state at the time of writing:

- 961 tests passing, ~90% source coverage (but `scripts/` at 0%, `__init__.py` at 40%)
- Modern-ish `pyproject.toml`, src layout, CI matrix 3.9–3.13, separate mypy workflow, RTD docs
- Legacy remnants: `setup.py`, `setup.cfg`, `MANIFEST.in`, `python setup.py check` in tox
- black + flake8; partial type annotations; 8 mypy errors; no `py.typed`
- `model.py` is a 2,837-line monolith
- Python 3.9 past EOL; `rdflib` pinned `<7`; no release automation
- 17 open issues, several genuine bugs; open community PR #167

## Decisions (agreed with maintainer)

| Decision | Choice |
|---|---|
| Compatibility policy | Staged: non-breaking 2.x releases first; compatibility changes batched into a signposted 3.0 |
| Lint/format | ruff for both, replacing black + flake8 |
| Test framework | Full pytest migration, staged: runner first, idiom rewrite later |
| Issue scope | Modernisation + bug fixes; large features deferred (exception: PROV-JSONLD, added as Phase 5) |
| Docs | Stay on Sphinx/RTD; modernise (furo, MyST, napoleon) and reorganise along Diátaxis |
| Internal refactor | Split `model.py` late in the roadmap, behind full test/typing safety net, with re-exports |
| Sequencing | Foundation-first ladder; release when there is user-visible value (~2.2.0, 2.3.0, 2.4.0, 3.0, 3.1) |
| Conformance | Dedicated audit phase against W3C PROV-DM and companion specs before 3.0 |
| Community visibility | Public `ROADMAP.md` + GitHub milestones + pinned tracking issue, maintained at each release |

## Guiding principles

- Every step is one focused PR landing on `master` with green CI; each independently revertable.
- Nothing changes the public API in 2.x. A public-API smoke test (added in Phase 1)
  asserts every documented name is importable from its historic location and guards
  every subsequent step.
- The public surface includes the `prov-convert`/`prov-compare` console scripts
  (declared in `[project.scripts]`): downstream packagers (Debian, Fedora, Arch/AUR,
  conda-forge) ship them, so their entry points and CLI behaviour stay stable through
  2.x and the sdist remains buildable for distro packaging. A CLI smoke test (Phase 1,
  step 7b) guards the entry points; full CLI test coverage lands in Phase 2 (step 18).
- Advisory CI (coverage upload, Codacy) must never block required checks: external
  service outages are not build failures (`continue-on-error: true` on upload steps).
- Ratchets, not aspirations: mypy strictness and coverage thresholds are enforced
  per-module/globally in CI as they are achieved, so regressions are impossible.
- Releases cut when there is user-visible value; 3.0 is the only release allowed to break.
- No AI attribution in commit messages or PR descriptions.

## Phase 0 — Housekeeping (no release)

1. Commit `uv.lock` and `CLAUDE.md`; extend `.gitignore` (`.eggs/`, `.ruff_cache/`,
   `.pytest_cache/`, `.idea/`, `build/`).
2. Delete `setup.py`, `setup.cfg`, `MANIFEST.in`; replace `python setup.py check` +
   `check-manifest` in tox with `uv build` + `twine check`.
3. Tidy `[tool.mypy] exclude`: the current `prov/tests/*` works (mypy regex-search
   semantics) but reads like a broken glob; make it an explicit anchored regex
   (`^src/prov/tests/`) and verify the checked-file count stays at 14.
4. Consolidate `CHANGES.txt` + `HISTORY.rst` into one changelog.
5. Bump Trove classifier `4 - Beta` → `5 - Production/Stable`.
6. Publish the public-facing roadmap: `ROADMAP.md` in the repo root (phase/release
   summary derived from this spec, without internal detail), GitHub milestones for
   2.2.0 / 2.3.0 / 2.4.0 / 3.0.0 / 3.1.0 with issues assigned to them, and a pinned
   tracking issue inviting community feedback. Linked from README and docs; updated
   as part of every release step below.

## Phase 1 — Tooling, CI, bug fixes → release 2.2.0

7. Add the public-API smoke test (imports + one round-trip per serializer) before
   any other change.
7b. Add a CLI smoke test for `prov-convert`/`prov-compare`: entry-point functions
   exist and an end-to-end convert/compare of a small document succeeds (full CLI
   coverage remains Phase 2, step 18).
8. Adopt ruff lint replacing flake8: conservative rule set first (E/F/W, bugbear,
   pyupgrade-for-3.9); config + mechanical autofixes in one PR.
9. Adopt ruff format replacing black (near-zero diff expected from black 24).
10. Add pre-commit (ruff, ruff-format, whitespace hygiene).
11. Adopt pytest as runner (`pytest`, `pytest-cov`; config in `pyproject.toml`;
    tox/CI switch from `unittest discover`). Test code untouched.
12. Modernise CI: `astral-sh/setup-uv`; add Python 3.14 to the matrix; merge the
    mypy workflow into CI.yml; fix the 8 mypy errors (missing stubs:
    `types-python-dateutil`, `lxml-stubs`, networkx stubs); pin mypy in the dev
    group so local and CI agree.
13. Release automation: `release.yml` using PyPI Trusted Publishing (OIDC),
    triggered by GitHub release tags, with `twine check` and a TestPyPI dry-run path.
14. Bug fixes for 2.2.0: #164 graphics fix (already merged, unreleased);
    #166/PR #167 matplotlib as optional `[plot]` extra with helpful error (review
    the community PR rather than duplicating); #155 XML default-namespace parsing;
    triage #34/#77/#89 — behaviour-changing fixes are documented and deferred to 3.0.
15. Cut 2.2.0 via the new pipeline (its first real test).

## Phase 2 — Typing & coverage → release 2.3.0

16. Type annotations module-by-module, smallest first, each its own PR:
    `identifier.py` → `constants.py` → `graph.py` → `dot.py` → `serializers/*` →
    `model.py` (2–3 PRs by class group). Each PR flips that module to strict mypy
    (per-module `disallow_untyped_defs` ratchet).
17. Ship `py.typed` (PEP 561) once mypy is clean and strict across `src/prov` —
    downstream users get real type checking against prov's API.
18. Close coverage gaps: `scripts/convert.py` and `compare.py` (0% — add CLI tests
    with tmp files across formats); `prov/__init__.py` `read()` auto-detection (40%);
    `graph.py` (82%). The #164 regression shipped precisely because nothing exercised
    the file-output path.
19. Coverage ratchet in CI: `fail_under` at current figure, raised as gaps close
    (target ~95% source coverage).
20. Cut 2.3.0.

## Phase 3 — Docs, pytest idioms, structural refactor → release 2.4.0

21. Docs tooling modernisation (one PR): furo theme, MyST (new pages in Markdown),
    napoleon, intersphinx (Python/rdflib/networkx), sphinx-copybutton. Keep RTD
    hosting and URLs; `.readthedocs.yml` builds with uv.
22. Docs reorganisation along Diátaxis:
    - **Tutorial:** first provenance document → serialize → visualise (replaces `usage.rst`).
    - **How-to guides:** per serialization format (incl. PROV-N write-only quirk),
      graphics export incl. local Graphviz install (closes #141), CLI tools
      `prov-convert`/`prov-compare` (closes #83), NetworkX interop.
    - **Reference:** API docs from completed type hints/docstrings, organised by
      module (replaces `modules.rst` dump); plus the conformance matrix (Phase 3.5).
    - **Explanation:** PROV-DM primer mapping W3C concepts to the class model;
      unification/flattening semantics.
23. Docstring pass over the public API (napoleon style, consistent with type hints).
24. pytest idiom migration, module-by-module: convert shared mixins
    (`RoundTripTestCase`, `attributes.py`, `statements.py`) to parametrized
    fixtures; one format's test module first as pattern-setter. Test count and
    assertions provably preserved (`pytest --collect-only` before/after).
25. Split `model.py` into a package: ~`records.py` (ProvRecord/elements/relations),
    `bundle.py` (ProvBundle/ProvDocument), `namespaces.py` (NamespaceManager);
    `prov/model/__init__.py` re-exports everything at historic names. Pure moves,
    no behaviour edits in the same PR.
26. Add deprecation warnings for anything 3.0 will change — 2.4.0 is the
    signposting release.
27. Cut 2.4.0.

## Phase 3.5 — Standards conformance audit (feeds 3.0 triage)

Audit `prov` against W3C PROV-DM (https://www.w3.org/TR/prov-dm/) and companion
specs. Already-open issues #89, #168, #154 are conformance findings; expect more.

28. Build a conformance matrix: one row per PROV-DM type/relation across the six
    components (Entities/Activities, Derivations, Agents/Responsibility, Bundles,
    Alternates, Collections); columns: model class exists, factory/convenience
    method on `ProvBundle`, correct round-trip in JSON/XML/RDF/PROV-N output.
    Published as a docs reference page.
29. Audit formal attributes and semantics against PROV-DM §5: each record type's
    attributes, optionality, datatypes vs `FORMAL_ATTRIBUTES`/`constants.py`.
    §5.7 (Values, Qualified Names, Namespace Declarations) is where siblings of
    #89/#77 likely live.
30. Check serializer mappings against normative companion specs: PROV-N grammar
    (W3C test files exist), PROV-O mapping tables (PROV-DM Appendix A), PROV-JSON
    member submission, PROV-XML XSD (add lxml schema-validation test).
31. Triage findings: cheap non-breaking fixes → 2.x; behaviour/output-changing
    fixes → Phase 4 list; feature gaps (PROV-Dictionary #129, convenience methods
    #154, PROV-N parser #122) → post-3.0 features backlog.
32. Out of scope: PROV-CONSTRAINTS validation engine (#62) — features backlog.

## Phase 4 — prov 3.0: the compatibility release

33. Python floor → 3.10 (3.9 is 9 months past EOL; if 3.0 ships after Oct 2026,
    consider `>=3.11`). Policy: support all non-EOL CPython; drop in the next
    minor/major after EOL. One PR: `requires-python`, classifiers, CI matrix, tox.
34. Ruff pyupgrade ratchet to the new floor: native `X | Y` unions, modern stdlib
    idioms; mechanical PR.
35. rdflib 7, two-step: attempt widening to `<8` in 2.x (non-breaking if the suite
    passes — try as early as Phase 2; unblocks downstream users stuck on the `<7`
    pin). In 3.0, raise the floor (`>=6` or `>=7`) to shed shims; real rdflib-7
    fixes land here.
36. Behaviour-changing bug fixes, individually triaged, each with tests showing
    old vs new behaviour: #89 (literals with/without explicit datatype), #34
    (merging same-value/different-type attributes), #77 (Decimal literal
    comparison), #168 (`xsd:QName` typing in PROV-JSON — interop-affecting output
    change), plus Phase 3.5 findings.
37. Remove everything deprecated in 2.4.0.
38. Migration guide docs page ("Upgrading to 3.0") — most users should need zero
    code changes; the guide demonstrates it.
39. Cut 3.0.0.

## Phase 5 — PROV-JSONLD serializer → release 3.1.0

Add support for PROV-JSONLD (https://www.w3.org/submissions/prov-jsonld/), the
W3C member submission for representing PROV-DM natively in JSON-LD. Placed after
3.0 deliberately: it is written once against the typed, refactored, conformance-
audited codebase; the parametrized round-trip fixtures make adding a format cheap;
and its output reflects 3.0 semantics (e.g. #89/#168 fixes) rather than pre-audit
behaviour. It is a purely additive feature, so it ships in a minor release.

40. Design note: native JSON serializer/deserializer (`serializers/provjsonld.py`,
    format name `"jsonld"`), following the submission's §4 schema (one section per
    PROV-DM record type) and §5 contexts (the qualification pattern). No rdflib
    dependency — implemented like `provjson.py`. Decide context handling:
    reference the W3C-hosted context vs embed it (embedding is self-contained and
    offline-safe; recommended default with an option to reference).
41. Implement serializer + deserializer record-type group by record-type group
    (mirroring the submission's structure), registered in the serializer
    `Registry` and `prov.read()` auto-detection; fully typed and docstringed from
    day one; round-trip tests via the shared parametrized fixtures (new format
    column in the existing matrix).
42. Validate against the submission's own examples and cross-check interop with
    ProvToolbox's PROV-JSONLD output; optionally verify emitted documents parse
    as valid JSON-LD with an off-the-shelf JSON-LD processor in tests.
43. Extend the conformance matrix and docs: JSON-LD column in the reference
    matrix, a how-to page for the format, changelog and `ROADMAP.md` updates.
44. Cut 3.1.0.

## Cross-cutting (start early, maintain throughout)

- Dependabot for GitHub Actions and Python dev-dependency updates.
- SECURITY.md and a stated version-support policy in the README.
- CONTRIBUTING refresh once tooling settles: uv + ruff + pytest instructions.
- `ROADMAP.md`, milestones, and the pinned tracking issue updated at every release.

## Effort feel

Phase 0 ~half a day; Phase 1 ~2–3 days; Phase 2 the biggest chunk (typing
`model.py` dominates; weeks of part-time effort); Phase 3 ~a week; Phase 3.5
~2–3 days of focused spec reading; Phase 4 ~2–3 days plus behaviour-bug triage;
Phase 5 ~1–2 weeks part-time (new serializer + deserializer + interop tests).

## Error handling & risk

- Public-API smoke test + full suite guard every PR; any import or round-trip
  regression fails CI before merge.
- Behaviour-affecting changes are quarantined to 3.0 and individually reviewable.
- The `model.py` split happens only after typing + coverage ratchets are in place.
- Release pipeline is exercised first on a low-risk release (2.2.0) with a
  TestPyPI dry-run path.

## Testing strategy

- Existing 961 tests retained throughout; pytest runner adopted before any test
  code changes; idiom migration preserves collected-test counts.
- New tests added where coverage is absent (CLI scripts, `read()`, graphics file
  output) and for every bug fixed (regression test per issue number).
- XSD validation test for PROV-XML output; conformance matrix backed by
  round-trip tests per record type per format; PROV-JSONLD validated against the
  submission's examples and ProvToolbox interop.

# Phase 2: Typing, Coverage & Dependency Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute roadmap Phase 2 (spec steps 16–20, plus step 35's early rdflib attempt): module-by-module strict mypy + `py.typed`, ruff rule-family expansion (I/C4/SIM/RUF/UP045/UP031, B904/B028 resolution), a test-gap audit with mutation-testing spike, coverage ratchet toward ~95%, dependency audit (docs group split, drop tox), and the 2.3.0 release. Task 0 is an urgent out-of-band ReadTheDocs build hotfix.

**Architecture:** No public API changes (2.x freeze). Typing work is annotation/config-only with `import X as X` re-exports preserving every historic import location; ruff families land one PR each; coverage work is tests + config only. The only intentional observable change is exception chaining (`__cause__`) on two `raise` sites (T9), noted in the changelog.

**Tech Stack:** uv, mypy (`--strict`), ruff, pytest, coverage.py (branch mode, `fail_under` ratchet), mutmut (spike only), GitHub Actions, PyPI Trusted Publishing.

**Spec:** `docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md`

## Baseline facts (verified 2026-07-04)

- `uv run mypy src` is green today; the **strict** gap is ~95 errors: ~32 outside `provrdf.py`, 63 in `provrdf.py` (35 of them currently masked by a `disable_error_code` override in pyproject).
- `mypy --strict` config note: `strict = true` is **global-only** (rejected inside `[[tool.mypy.overrides]]`), so per-task verification runs `uv run mypy --strict src` and filters by module; the config flip happens once at the end (T3).
- Coverage today: 91% total, branch mode already enabled. Weakest: `scripts/convert.py` 26%, `scripts/compare.py` 30%, `__init__.py` 39%, `graph.py` 82%.
- Ruff family sizing (current codebase): I=23, C4=19, SIM=18, RUF=25, UP045=114, UP031=74. Five modules lack `from __future__ import annotations`: `constants.py`, `graph.py`, `scripts/convert.py`, `scripts/compare.py`, `serializers/provn.py`.
- B904 noqa sites: `serializers/__init__.py:91`, `scripts/convert.py:105`. B028 noqa sites: `serializers/provrdf.py:700`, `serializers/provxml.py:281`, `serializers/provxml.py:385`.
- rdflib 7.6.0 breaks 5 tests (`test_rdf.py` `RoundTripRDFTests::test_bundle_1..4`, `::test_default_namespace_inheritance`) — widening is an investigation (T15), not a pin bump.
- RTD build failure (user-reported): Sphinx ≥9.0 autodoc crashes on rdflib's `DefinedNamespaceMeta.__repr__` (raises without `_NS`) when documenting modules importing `provrdf`. Bisected: 8.1.3/8.2.3 OK, 9.0.4/9.1.0 FAIL. `docs/requirements.txt` currently pins nothing but `sphinx_rtd_theme`.

## User decisions

- **Drop tox** (T14): delete `tox.ini`, remove tox from the dev group; local multi-interpreter testing via `uv run --python 3.X pytest`. CI matrix is unaffected.
- **RTD fix** = pin `sphinx>=8.1.3,<9` in `docs/requirements.txt`, shipped immediately as Task 0.
- **Python floor → 3.10 in 2.3.0** (decided 2026-07-04, supersedes spec step 33's Phase-4 timing): the 12 Dependabot alerts are all vulnerable versions kept in `uv.lock` solely by the `python_full_version < '3.10'` marker (patched releases dropped 3.9). User chose to pull the floor bump forward rather than dismiss the alerts. T17 implements it; T16's changelog must call the support change out prominently.

## Model assignment

| Task | Branch | What | Tier |
|---|---|---|---|
| 0 | fix/rtd-sphinx-pin | RTD hotfix: pin sphinx <9 | mechanical |
| 1 | typing/strict-core | Strict mypy fixes, all modules except provrdf | standard |
| 2 | typing/strict-provrdf | provrdf strict typing (63 errors, drop override) | frontier |
| 3 | typing/strict-flip | Global `strict = true` + ship py.typed | standard |
| 4 | ruff/isort | ruff family I | mechanical |
| 5 | ruff/c4 | ruff family C4 | mechanical |
| 6 | ruff/sim | ruff family SIM | standard |
| 7 | ruff/ruf | ruff family RUF | standard |
| 8 | ruff/up045-up031 | UP045 + UP031 un-ignore | standard |
| 9 | ruff/b904-b028 | Resolve B904/B028 noqa sites | standard |
| 10 | tests/gap-audit | Test-gap audit + mutmut spike + fail_under=91 | frontier |
| 11 | tests/cli | In-process CLI tests (convert/compare) | standard |
| 12 | tests/read-graph-registry | Tests: read(), graph.py, serializer registry | standard |
| 13 | tests/close-gaps | Close audit gaps, ratchet fail_under → ~95 | standard |
| 14 | chore/dependency-audit | Dependency audit, docs group, drop tox | standard |
| 15 | deps/rdflib-7 | rdflib <8 widening investigation (time-boxed) | frontier |
| 16 | release/2.3.0 | Cut release 2.3.0 | standard + maintainer |

**Conventions for every task:**
- Branch from up-to-date `master`: `git checkout master && git pull && git checkout -b <branch>`.
- Full suite green before each commit: `uv run pytest` (needs `uv sync --extra rdf --extra xml`).
- Lint/format clean: `uv run ruff check src/ && uv run ruff format --check src/`.
- No AI attribution in commits or PRs.
- One PR per task; merge before starting a dependent task. Order: T0 first (hotfix); T1→T2→T3 (typing chain); T4→T5→T6→T7→T8→T9 (ruff chain, after T3); T10→{T11,T12}→T13 (coverage chain); T14 after T9; T15 anytime; T16 last.
- When a task changes tooling or commands, update the affected CLAUDE.md sections in the same PR.

---

### Task 0: RTD hotfix — pin Sphinx below 9 (mechanical)

**Goal:** Unbreak the readthedocs.io build, which fails on Sphinx 9.x.

**Files:**
- Modify: `docs/requirements.txt`

- [ ] **Step 1:** Replace the contents of `docs/requirements.txt` with:

```
sphinx>=8.1.3,<9
sphinx_rtd_theme
```

(Root cause: Sphinx 9's autodoc calls `repr()` on class bases; `rdflib.namespace.DefinedNamespaceMeta.__repr__` raises `AttributeError` on the abstract base, crashing the build via `provrdf`'s rdflib imports. Verified locally: 8.1.3 and 8.2.3 build, 9.0.4 and 9.1.0 crash.)

- [ ] **Step 2:** Verify locally with the pinned Sphinx: create a scratch venv, `uv pip install --python <venv> -r docs/requirements.txt lxml rdflib "pydot" networkx .` and run `sphinx-build -b html docs <scratch>/out` — must exit 0.
- [ ] **Step 3:** PR, merge, confirm the RTD build for master goes green.

**Acceptance criteria:**
- `docs/requirements.txt` pins `sphinx>=8.1.3,<9`.
- Local sphinx-build with the pinned version exits 0; RTD build passes after merge.

**Verify:** `grep 'sphinx>=8.1.3,<9' docs/requirements.txt` and a local `sphinx-build -b html docs <tmp>` under the pinned Sphinx.

---

### Task 1: Strict mypy — all modules except provrdf (standard)

**Goal:** `uv run mypy --strict src` reports errors only in `src/prov/serializers/provrdf.py`. No runtime behaviour change; every historic import location keeps working.

**Files:**
- Modify: `src/prov/model.py`, `src/prov/__init__.py`, `src/prov/graph.py`, `src/prov/dot.py`, `src/prov/identifier.py`, `src/prov/serializers/__init__.py`, `src/prov/serializers/provjson.py`, `src/prov/serializers/provxml.py`, `src/prov/serializers/provn.py`, `src/prov/scripts/convert.py`, `src/prov/scripts/compare.py`, `pyproject.toml`

- [ ] **Step 1:** Run `uv run mypy --strict src` and save the error list; ~32 errors outside provrdf are in scope (provrdf's are Task 2).
- [ ] **Step 2 — re-exports (`no_implicit_reexport`):** `prov.model` publicly re-exports identifier classes (`from prov.model import Namespace, QualifiedName, Identifier` is documented API). Use the PEP 484 explicit re-export idiom in `model.py` — `from prov.identifier import Identifier as Identifier, QualifiedName as QualifiedName, Namespace as Namespace` — and do **not** add `__all__` (that would change `import *` behaviour = forbidden API change). Star-imports from `constants` are already treated as re-exported by mypy; leave them. Where internal modules (e.g. `provxml.py`) import identifier classes *via* `prov.model`, switch them to import from `prov.identifier` directly.
- [ ] **Step 3 — known model.py fixes:**
  - `PathLike = Union[str, bytes, os.PathLike]` (~line 59) → `Union[str, bytes, "os.PathLike[str]"]` (subscripting is legal at runtime on 3.9+, quotes optional).
  - `self._attributes: dict[QualifiedName, set]` (~289) → `dict[QualifiedName, set[Any]]`.
  - `def get_attribute(...) -> set` (~324) → `-> set[Any]`; `def args(self) -> tuple` (~355) → `-> tuple[Any, ...]`.
  - `class NamespaceManager(dict)` (~1132) → `class NamespaceManager(dict[str, Namespace])`.
  - Three `no-any-return` sites (~1180, ~1331, ~1341 in `get_namespace` / `valid_qualified_name`): tighten internal annotations or `cast(...)` — never change runtime logic.
  - Two `unused-ignore` warnings (~1653 `__hash__ = None  # type: ignore`, ~2309 `return record  # type: ignore`): narrow to the specific error code mypy still needs (e.g. `# type: ignore[assignment]`) or delete if truly unused.
- [ ] **Step 4 — `src/prov/__init__.py`:** `os.PathLike` in `read()`'s signature → `os.PathLike[str]`.
- [ ] **Step 5 — `graph.py`:** add `from __future__ import annotations`; parametrise the three bare `nx.MultiDiGraph` generics as `nx.MultiDiGraph[Any]`(annotation-only); annotate `node_map: dict[...] = {}` as strict requires. Replace the `# type: nx.MultiDiGraph` comment with a real annotation.
- [ ] **Step 6 — scripts:** in both `convert.py` and `compare.py`, `__all__ = []  # type: ignore` → `__all__: list[str] = []`; `Optional[list]` → `Optional[list[str]]`. In `convert.py`, `content = dot.create(format=output_format)` → `content = cast(bytes, dot.create(format=output_format))` (pydot's stub says `str`; runtime returns `bytes`) and **remove the `prov.scripts.convert` override block from pyproject.toml**.
- [ ] **Step 7:** Fix any remaining strict errors outside provrdf using the same idioms (annotations, `cast`, narrowed ignores). Rule: if a fix would change runtime behaviour, stop and use a `# type: ignore[<code>]` with a comment instead.
- [ ] **Step 8:** `uv run mypy --strict src 2>&1 | grep -v provrdf` shows zero errors; `uv run mypy src` (current config) stays green; `uv run pytest` green (public-API smoke test guards the import surface); ruff clean. Commit, PR.

**Acceptance criteria:**
- `uv run mypy --strict src` reports errors only in files matching `provrdf`.
- Existing non-strict config still green; full test suite green (incl. public-API smoke test); no runtime logic changed.
- `prov.scripts.convert` mypy override removed from pyproject.

**Verify:** `uv run mypy --strict src 2>&1 | grep -v provrdf | grep -c 'error:'` → 0, and `uv run pytest`.

---

### Task 2: Strict mypy — provrdf refactor (frontier)

**Goal:** `src/prov/serializers/provrdf.py` passes `mypy --strict` with its `disable_error_code` override removed. Zero behaviour change — the RDF round-trip suite is the safety net.

**Files:**
- Modify: `src/prov/serializers/provrdf.py`, `pyproject.toml`

- [ ] **Step 1:** Remove the provrdf `[[tool.mypy.overrides]]` block (the one with `disable_error_code = ["arg-type", "assignment", "operator", "index"]`) from pyproject.toml. `uv run mypy --strict src` now shows ~63 provrdf errors — this is the work list.
- [ ] **Step 2:** If `no_implicit_reexport` flags `from rdflib.namespace import RDF, RDFS, XSD`, import from `rdflib` top level instead (`from rdflib import RDF, RDFS, XSD` — rdflib's `__init__` declares `__all__`).
- [ ] **Step 3:** Fix the errors mechanically, preferring in order: (a) precise local annotations / type aliases for rdflib terms (`URIRef | BNode`, `Node`, etc.); (b) `isinstance` narrowing that mirrors what the code already assumes; (c) `cast()` where rdflib's own types are imprecise; (d) `# type: ignore[<code>]` with a one-line reason as last resort. **Never** reorder logic, change comparisons, or "simplify" while typing — this file has subtle Literal/datatype handling.
- [ ] **Step 4:** Full verification: `uv run mypy --strict src` → zero errors in provrdf; `uv run pytest` fully green with special attention to `test_rdf.py`; ruff clean. Commit, PR.

**Acceptance criteria:**
- provrdf override gone from pyproject; `uv run mypy --strict src` reports 0 provrdf errors.
- Full suite green; `git diff` shows only annotations/casts/imports in provrdf (no logic changes).

**Verify:** `uv run mypy --strict src` (expect 0 errors total, given T1) and `uv run pytest src/prov/tests/test_rdf.py -q && uv run pytest -q`.

---

### Task 3: Flip config to strict, ship py.typed (standard)

**Goal:** Spec steps 16 (finish) + 17: `[tool.mypy] strict = true` becomes the enforced default and the wheel/sdist advertise inline types per PEP 561.

**Files:**
- Modify: `pyproject.toml`, `CLAUDE.md`
- Create: `src/prov/py.typed` (empty file)

- [ ] **Step 1:** In pyproject `[tool.mypy]`: add `strict = true`; delete the now-redundant `[[tool.mypy.overrides]] module = "prov.*"` block (`disallow_untyped_defs`/`check_untyped_defs` are implied by strict). Keep `python_version` and the tests `exclude`.
- [ ] **Step 2:** Create empty `src/prov/py.typed` and register it:

```toml
[tool.setuptools.package-data]
prov = ["py.typed"]
```

- [ ] **Step 3:** Build and inspect both artifacts: `uv build`, then `unzip -l dist/prov-*.whl | grep py.typed` and `tar tzf dist/prov-*.tar.gz | grep py.typed` — both must list it.
- [ ] **Step 4:** Downstream check from the wheel: in a scratch venv, `uv pip install dist/prov-*.whl mypy` and run mypy on a 3-line script importing `prov.model.ProvDocument` — must type-check without "missing library stubs" errors.
- [ ] **Step 5:** Update CLAUDE.md's mypy bullet (remove the "some untyped-3rd-party-stub errors are pre-existing" caveat; note the codebase is strict-clean and `py.typed` ships). Note the typing milestone in `ROADMAP.md` if it tracks step status.
- [ ] **Step 6:** `uv run mypy src` (now strict) green, `uv run pytest` green, PR.

**Acceptance criteria:**
- `strict = true` global; no `prov.*` override; `uv run mypy src` green under it.
- `py.typed` present in both wheel and sdist; downstream mypy check passes.
- CLAUDE.md updated in the same PR.

**Verify:** `uv run mypy src && uv build && unzip -l dist/prov-*.whl | grep py.typed && tar tzf dist/prov-*.tar.gz | grep py.typed`

---

### Task 4: ruff family I — import sorting (mechanical)

**Goal:** Enable isort-style rules; autofix the 23 findings.

**Files:**
- Modify: `pyproject.toml`, plus autofixed source files

- [ ] **Step 1:** Add `"I"` to `[tool.ruff.lint] select` in pyproject.toml.
- [ ] **Step 2:** `uv run ruff check --fix src/` (expect ~23 fixes), then `uv run ruff format src/`.
- [ ] **Step 3:** `uv run ruff check src/` clean; `uv run pytest` green (import order can matter — the suite must confirm it doesn't here); commit, PR.

**Acceptance criteria:** `"I"` selected; zero I findings; suite green; diff contains only import reordering + config.

**Verify:** `uv run ruff check src/ && uv run pytest -q`

---

### Task 5: ruff family C4 — comprehensions (mechanical)

**Goal:** Enable flake8-comprehensions; autofix the 19 findings.

**Files:**
- Modify: `pyproject.toml`, plus autofixed source files

- [ ] **Step 1:** Add `"C4"` to select.
- [ ] **Step 2:** `uv run ruff check --fix src/` (expect ~19 fixes); `uv run ruff format src/`.
- [ ] **Step 3:** ruff clean, `uv run pytest` green, `uv run mypy src` green, commit, PR.

**Acceptance criteria:** `"C4"` selected; zero C4 findings; suite + mypy green.

**Verify:** `uv run ruff check src/ && uv run pytest -q && uv run mypy src`

---

### Task 6: ruff family SIM — simplifications (standard)

**Goal:** Enable flake8-simplify; resolve the 18 findings with judgment (autofix where safe, targeted `noqa` where the "simplification" would hurt clarity or risk behaviour).

**Files:**
- Modify: `pyproject.toml`, plus touched source files

- [ ] **Step 1:** Add `"SIM"` to select; run `uv run ruff check src/` to list the 18 findings.
- [ ] **Step 2:** Apply safe autofixes; review every diff hunk. For any rule instance where the rewrite changes semantics (e.g. `SIM105` try/except-pass → `contextlib.suppress` in hot paths, ternary collapses in serializer logic), either verify equivalence or keep the original with `# noqa: SIM1xx` + reason. A per-rule ignore in pyproject is acceptable if a whole rule misfires repeatedly — document why in the PR.
- [ ] **Step 3:** ruff clean, `uv run pytest` green, `uv run mypy src` green, commit, PR.

**Acceptance criteria:** `"SIM"` selected; zero unaddressed findings; every suppression carries a reason; suite + mypy green.

**Verify:** `uv run ruff check src/ && uv run pytest -q && uv run mypy src`

---

### Task 7: ruff family RUF — ruff-specific rules (standard)

**Goal:** Enable the RUF family; resolve the 25 findings (typically RUF012 mutable class defaults, RUF005 concatenation, docstring/noqa hygiene).

**Files:**
- Modify: `pyproject.toml`, plus touched source files

- [ ] **Step 1:** Add `"RUF"` to select; list findings.
- [ ] **Step 2:** Fix each: `ClassVar` annotations for RUF012 on class-level dict/list constants (e.g. `FORMAL_ATTRIBUTES` maps) are annotation-only and safe; review any fix touching runtime values. Suppress with reason where a rule conflicts with the frozen public API.
- [ ] **Step 3:** ruff clean, `uv run pytest` green, `uv run mypy src` green (ClassVar interacts with strict mypy — both must pass), commit, PR.

**Acceptance criteria:** `"RUF"` selected; zero unaddressed findings; suite + mypy green.

**Verify:** `uv run ruff check src/ && uv run pytest -q && uv run mypy src`

---

### Task 8: UP045 + UP031 revisit (standard)

**Goal:** Spec 19b: drop the deferred `UP045` (`Optional[X]` → `X | None`, 114 sites) and `UP031` (printf-style formatting, 74 sites) from the ignore list and fix all findings.

**Files:**
- Modify: `pyproject.toml`, `src/prov/constants.py`, `src/prov/scripts/convert.py`, `src/prov/scripts/compare.py`, `src/prov/serializers/provn.py`, plus autofixed files

- [ ] **Step 1:** Add `from __future__ import annotations` to the four listed modules that still lack it (graph.py got it in T1). `X | None` in *annotations* is then fine on 3.9. Watch for `Optional[...]` used in **runtime** positions (e.g. cast targets, variable aliases) — those must keep a runtime-valid spelling on 3.9 (`Union`/`Optional`), so exempt them individually if ruff flags them.
- [ ] **Step 2:** Remove `"UP045"` and `"UP031"` from `[tool.ruff.lint] ignore`.
- [ ] **Step 3:** `uv run ruff check --fix src/` for UP045 (safe, annotation-only). For UP031, apply fixes (some need `--unsafe-fixes`) **and review every hunk**: %-formatting builds serialized PROV-N/dot output in places — the round-trip suite must prove byte-identical behaviour. Any `%` use on user-supplied patterns stays with `# noqa: UP031` + reason.
- [ ] **Step 4:** ruff clean, `uv run pytest` green (round-trip tests are the behaviour check), `uv run mypy src` green, commit, PR.

**Acceptance criteria:** UP045/UP031 out of the ignore list; zero findings; suite + mypy green on 3.9-compatible runtime syntax.

**Verify:** `uv run ruff check src/ && uv run pytest -q && uv run mypy src` (CI matrix confirms 3.9).

---

### Task 9: Resolve B904 / B028 noqa debts (standard)

**Goal:** Spec 19b tail: replace the 5 inline suppressions with real fixes. Intentional, changelog-worthy behaviour tweak: two exceptions gain `__cause__`.

**Files:**
- Modify: `src/prov/serializers/__init__.py`, `src/prov/scripts/convert.py`, `src/prov/serializers/provrdf.py`, `src/prov/serializers/provxml.py`
- Test: `src/prov/tests/test_extras.py` or nearest suitable module

- [ ] **Step 1 (B904):** `serializers/__init__.py:91` — chain the `DoNotExist` raise with `from e` (or `from err`, matching the local name) and drop the noqa. `scripts/convert.py:105` — `raise CLIError(...) from e`, drop the noqa and the "revisit in a follow-up" comment. CLI behaviour (exit code 2, message) is unchanged; only `__cause__` is now set.
- [ ] **Step 2 (B028):** add `stacklevel=2` to the `warnings.warn` calls at `provrdf.py:700`, `provxml.py:281`, `provxml.py:385`; drop their noqas.
- [ ] **Step 3 (test):** add a unit test asserting `prov.serializers.get("no-such-format")` raises `DoNotExist` **and** that its `__cause__` is a `KeyError`.
- [ ] **Step 4:** Confirm no `noqa: B904` / `noqa: B028` remain (`grep -rn 'noqa: B9\|noqa: B028' src/`); ruff/pytest/mypy green; note the `__cause__` change in the PR body so T16 picks it up for HISTORY.rst. Commit, PR.

**Acceptance criteria:** zero B904/B028 noqas; new `__cause__` test passes; suite + mypy + ruff green.

**Verify:** `grep -rn 'noqa: B9' src/ ; uv run pytest -q && uv run ruff check src/`

---

### Task 10: Test-gap audit, mutation spike, first coverage ratchet (frontier)

**Goal:** Spec 17b + 19 (first notch): a written per-module gap analysis driving T11–T13, a time-boxed mutmut spike with an adopt/defer recommendation, and `fail_under = 91` enforced in CI.

**Files:**
- Create: `docs/test-gap-checklist.md`
- Modify: `pyproject.toml`, `.github/workflows/CI.yml` (only if needed to enforce the threshold)

- [ ] **Step 1:** `uv run coverage run -m pytest && uv run coverage report -m` (branch mode is already on). Capture per-module line+branch numbers and the actual missed lines.
- [ ] **Step 2:** Write `docs/test-gap-checklist.md`: one section per under-covered module (`scripts/convert.py` 26%, `scripts/compare.py` 30%, `__init__.py` 39%, `graph.py` 82%, plus any model/serializer branch clusters), each with a checkbox list of *behaviours* (not lines) that lack tests, and an owner column mapping each item to T11 / T12 / T13 / "defer (document why)".
- [ ] **Step 3 (mutation spike, time-box ~90 min):** run mutmut against one confined target (suggest `src/prov/graph.py`, small and pure) using a temporary install (`uvx mutmut` or `uv pip install mutmut` in a scratch venv) — do **not** add it to project deps. Record in the checklist: mutants generated/killed/survived, runtime, and a recommendation (adopt in Phase 3 / don't adopt, with reasons). Surviving mutants that reveal real gaps become checklist items.
- [ ] **Step 4 (ratchet):** set `fail_under = 91` under `[tool.coverage.report]`. Ensure CI actually enforces it: the tests job must run `uv run coverage run -m pytest && uv run coverage report` (report fails <91) as a hard step — the coveralls upload keeps its `continue-on-error`.
- [ ] **Step 5:** Full suite + a deliberate check that CI fails when under threshold is *not* required (don't break CI to prove it); reason from config. Commit, PR.

**Acceptance criteria:**
- `docs/test-gap-checklist.md` exists, behaviour-oriented, every item mapped to T11/T12/T13/defer.
- Mutation spike results + recommendation recorded; no mutmut in project dependencies.
- `fail_under = 91` in pyproject and CI enforces it via a non-optional `coverage report` step.

**Verify:** `uv run coverage run -m pytest && uv run coverage report` exits 0 with TOTAL ≥ 91%, and the checklist file exists.

---

### Task 11: In-process CLI tests for convert/compare (standard)

**Goal:** Close the biggest gaps (convert 26%, compare 30%) with in-process tests that exercise `main()` under coverage (subprocess tests in `test_cli_smoke.py` don't count toward coverage — keep them, add a new module).

**Files:**
- Create: `src/prov/tests/test_scripts.py`
- Reference: `src/prov/tests/test_cli_smoke.py` (unchanged), `docs/test-gap-checklist.md`

- [ ] **Step 1:** Test pattern — patch argv and call `main()` with no argument (passing `argv` *extends* `sys.argv`, a historic quirk; don't fight it):

```python
with unittest.mock.patch.object(sys, "argv", ["prov-convert", "-f", "xml", infile, outfile]):
    rc = convert_main()
```

Build inputs from `prov.tests.examples.primer_example()` in `tempfile.TemporaryDirectory()`.
- [ ] **Step 2:** convert cases: json→xml (rc 0, non-empty output); json→provn (`get_provn()` path); json→dot **and** one rendered graphviz format (e.g. svg) guarded by `@unittest.skipUnless(shutil.which("dot"), ...)`; unsupported format → rc 2 and `E: Output format ...` on captured stderr (patch `sys.stderr` with `io.StringIO`); unreadable/missing input file → rc 2; `--version` → `SystemExit` code 0 (argparse exits — use `assertRaises(SystemExit)`).
- [ ] **Step 3:** compare cases: equivalent json vs its xml round-trip → rc 0 (with `-f json -F xml`); genuinely different docs → rc 1; bad/missing file → rc 2; `--version` → SystemExit 0.
- [ ] **Step 4:** Tick the corresponding items in `docs/test-gap-checklist.md`. Run `uv run coverage run -m pytest && uv run coverage report -m` — `scripts/convert.py` and `scripts/compare.py` each ≥ 85%. Full suite, ruff, mypy green (tests are mypy-excluded but keep them clean). Commit, PR.

**Acceptance criteria:** new tests all pass in-process; convert.py & compare.py ≥ 85% line coverage; smoke test module untouched; checklist ticked.

**Verify:** `uv run coverage run -m pytest && uv run coverage report -m | grep -E 'convert|compare'`

---

### Task 12: Tests for read(), graph.py, serializer registry (standard)

**Goal:** Close the remaining named gaps: `prov/__init__.py` 39% → ~100%, `graph.py` 82% → ≥95%, registry error path.

**Files:**
- Create/extend: `src/prov/tests/test_read.py` (new), `src/prov/tests/test_graphs.py` (extend existing graph tests if present — check first), plus a registry test near the T9 `__cause__` test
- Reference: `docs/test-gap-checklist.md`

- [ ] **Step 1 (`read()`):** with a doc serialized to json/xml/rdf files: explicit `format=` for each; auto-detection (no format) for each; garbage input without format → `TypeError` with the "specify the format" message; `format="nonexistent"` → `DoNotExist` propagates. Use `os.PathLike` (a `pathlib.Path`) as source at least once.
- [ ] **Step 2 (`graph.py`):** `prov_to_graph`: relation with a missing end (e.g. generation with no activity) is skipped/handled per the `if qn1 and qn2` branch; relation referencing identifiers with no corresponding element gets **inferred** nodes of the right class (exercise `INFERRED_ELEMENT_CLASS`); `graph_to_prov`: round-trip a document (`prov_to_graph` → `graph_to_prov`, compare unified docs), a graph with a non-record node and an edge lacking the `relation` key is tolerated (the KeyError-pass branch).
- [ ] **Step 3 (registry):** `prov.serializers.get()` for all four formats returns classes; unknown → `DoNotExist` (dedupe with the T9 test — one module owns it).
- [ ] **Step 4:** Tick checklist items; coverage: `__init__.py` ≥ 95%, `graph.py` ≥ 92%. Full suite, ruff green. Commit, PR.

**Acceptance criteria:** targets met in `coverage report -m`; checklist ticked; suite green.

**Verify:** `uv run coverage run -m pytest && uv run coverage report -m | grep -E '__init__|graph'`

---

### Task 13: Close remaining gaps, final ratchet toward 95% (standard)

**Goal:** Spec 18/19 completion: work through every remaining unticked checklist item, then raise `fail_under` to the achieved floor (~95 target).

**Files:**
- Modify: `pyproject.toml`, `docs/test-gap-checklist.md`, test modules as needed

- [ ] **Step 1:** For each unticked, non-deferred checklist item, add a behaviour test (shared mixins in `examples.py`/`attributes.py`/`statements.py` where the behaviour is cross-format). Items that would need contrived tests (defensive branches, `__main__` blocks) get marked "defer" with one line of rationale.
- [ ] **Step 2:** Run coverage; set `fail_under` to the achieved TOTAL rounded **down** to an integer (target ≥ 95; if the honest ceiling is lower, say 93, set that and record why in the checklist — do not write junk tests to hit a number).
- [ ] **Step 3:** Checklist fully resolved (ticked or defer-annotated); suite/ruff/mypy green; commit, PR.

**Acceptance criteria:** no unresolved checklist items; `fail_under` ≥ 93 (95 target) matching real coverage; suite green.

**Verify:** `uv run coverage run -m pytest && uv run coverage report` exits 0; `grep fail_under pyproject.toml`.

---

### Task 14: Dependency audit — docs group, prune dev, drop tox (standard)

**Goal:** Spec 19c with the user's decision applied: documented dependency rationale, a separate docs group, lean dev group, tox removed.

**Files:**
- Create: `docs/dependencies.md`
- Modify: `pyproject.toml`, `Makefile`, `CLAUDE.md`, `docs/requirements.txt`, `CONTRIBUTING.rst` (if it mentions tox)
- Delete: `tox.ini`

- [ ] **Step 1:** Write `docs/dependencies.md`: every runtime dep, extra (`rdf`, `xml`, `plot`, `dot`…), and dev-group entry with one line each: why it's needed, why the pin (include the rdflib `<7` story referencing T15's outcome, and the sphinx `<9` pin from T0).
- [ ] **Step 2:** pyproject changes: add a `docs` dependency group mirroring `docs/requirements.txt` (`sphinx>=8.1.3,<9`, `sphinx_rtd_theme`) and move any sphinx entries out of dev; remove `bumpversion`, `wheel`, `setuptools`, and `tox` from the dev group (wheel/setuptools are build-backend concerns under `[build-system]`, not dev deps). Run `uv lock` and commit the updated `uv.lock`.
- [ ] **Step 3:** Delete `tox.ini`. Update `Makefile` `test-all` to iterate uv interpreters (e.g. `for py in 3.9 3.10 3.11 3.12 3.13 3.14; do uv run --python $py --extra rdf --extra xml pytest || exit 1; done` — adapt to Makefile syntax) or drop the target if redundant with CI. Update CLAUDE.md: remove the tox command bullet, document `uv run --python 3.X pytest` for local multi-interpreter runs. Fix any CONTRIBUTING.rst tox references. Keep `docs/requirements.txt` (RTD installs from it) with a comment pointing at the docs group as the source of truth.
- [ ] **Step 4:** Sanity: `uv sync --extra rdf --extra xml` then `uv run pytest` green; `uv sync --group docs` + local `sphinx-build` works; `grep -ri tox` across the repo returns only historic changelog mentions. Commit, PR.

**Acceptance criteria:** dependencies.md exists and covers everything; docs group works; dev group pruned; tox.ini gone with all doc references cleaned in the same PR; lock file updated; suite green.

**Verify:** `test ! -f tox.ini && uv sync --extra rdf --extra xml && uv run pytest -q && grep -L tox CLAUDE.md Makefile`

---

### Task 15: rdflib <8 widening investigation — time-boxed (frontier)

**Goal:** Spec step 35 pulled forward: determine whether the `rdflib>=4.2.1,<7` pin can widen to `<8` in 2.x without behaviour changes. Known: rdflib 7.6.0 fails 5 tests (`RoundTripRDFTests::test_bundle_1..4`, `::test_default_namespace_inheritance`). Time-box ~3 hours; a documented "no" is a valid outcome.

**Files:**
- Possibly modify: `src/prov/serializers/provrdf.py`, `pyproject.toml`, `.github/workflows/CI.yml`
- Fallback: a GitHub issue instead of code

- [ ] **Step 1:** Reproduce: scratch venv with `rdflib==7.*`, run `pytest src/prov/tests/test_rdf.py`. Diagnose the 5 failures (bundle handling + default-namespace inheritance point at rdflib 7's Dataset/graph-identifier and namespace-binding changes — e.g. `bind_namespaces` defaults).
- [ ] **Step 2 (decision gate):** If the fix is confined to provrdf, version-agnostic (still green on rdflib 6), and behaviour-preserving → implement it, widen the pin to `rdflib>=4.2.1,<8`, `uv lock`, and add a CI job/matrix entry running the rdf tests against the **minimum supported** rdflib and latest 7.x.
- [ ] **Step 3 (fallback):** If not cleanly fixable in the box: keep the `<7` pin, file a GitHub issue titled "rdflib 7 support" containing the full diagnosis (failing tests, root cause, sketch of the 3.0 fix), label it for the 3.0 milestone, and record the outcome + issue link in `docs/dependencies.md` (or the checklist if T14 hasn't run).
- [ ] **Step 4:** Either way: full suite green on the locked rdflib; PR (code path) or issue link reported (fallback path).

**Acceptance criteria:** a definitive, recorded outcome — widened pin with dual-version CI proof, **or** a filed issue with root-cause analysis and the pin untouched. No half-applied changes.

**Verify:** code path: `uv run pytest -q` + CI green on both rdflib versions; fallback: issue URL exists and pin unchanged (`grep 'rdflib' pyproject.toml`).

---

### Task 17: Raise Python floor to 3.10 and clear the Dependabot alerts (standard) — rescoped 2026-07-04

**Goal:** Spec step 33 pulled forward by user decision: `requires-python >= 3.10`, classifiers, CI matrix, ruff target — then re-lock so the 12 Dependabot alerts (all pinned to the `< '3.10'` resolution branch of `uv.lock`) actually clear. First attempt as a plain lock refresh failed (PR #188, closed): every patched release (pillow 12.2+, urllib3 2.7+, requests 2.33+, filelock 3.20.3+, pytest 9.0.3+) dropped Python 3.9.

**Files:** `pyproject.toml`, `.github/workflows/CI.yml`, `tox.ini`, `CLAUDE.md`, `uv.lock`.

- [ ] **Step 1:** Branch `chore/python-3.10-floor`. In `pyproject.toml`: `requires-python = ">=3.10"` (line ~32); delete the `"Programming Language :: Python :: 3.9"` classifier (line ~19); `[tool.ruff] target-version = "py310"` (line ~99). Do NOT touch the ruff ignore list or the UP045/UP031 ignores (T8 owns those rules); adjust the "(3.9-safe)" comment wording only if it becomes false.
- [ ] **Step 2:** `.github/workflows/CI.yml`: drop `"3.9"` from the test matrix (line ~17) and `Python3.9,` from the coveralls `carryforward` list (line ~78). `tox.ini`: drop `py39` from envlist and the `3.9: py39` gh-actions mapping (file is deleted later in T14; keep it consistent meanwhile).
- [ ] **Step 3:** `CLAUDE.md`: "Python 3.9+ only" → "Python 3.10+ only".
- [ ] **Step 4:** `uv lock --upgrade` (re-resolves for ≥3.10 — the dual-marker entries collapse to patched versions), `uv sync --extra rdf --extra xml`.
- [ ] **Step 5:** Confirm no vulnerable versions remain in `uv.lock`: no pillow 11.x, no urllib3 <2.7, no requests <2.33, no filelock <3.20.3, no pytest <9.0.3, and no `python_full_version < '3.10'` resolution markers left for these packages. `uv run pytest -q`, `uv run mypy src`, `uv run ruff check src/` all green.
- [ ] **Step 6:** Commit (`chore: raise Python floor to 3.10 and refresh lock`), PR explaining the support change + alert rationale, merge after CI; confirm the Dependabot alert count drops to 0 after the default-branch rescan.

**Acceptance criteria:** floor raised consistently across pyproject/CI/tox/CLAUDE.md; lock has no vulnerable 3.9-marker entries; suite/mypy/ruff green; prominent "Python 3.9 support dropped" entry flagged for T16's changelog.

**Verify:** `grep 'requires-python' pyproject.toml && uv run pytest -q && uv run mypy src && uv run ruff check src/`; post-merge alert count 0.

---

### Task 18: Security hygiene — Dependabot updates, SECURITY.md, support policy (standard) — added 2026-07-04

**Goal:** Implement the spec's "Cross-cutting (start early, maintain throughout)" security items that no phase plan had scheduled: automated dependency updates and a security policy.

**Files:**
- Create: `.github/dependabot.yml`, `SECURITY.md`
- Modify: `README.rst` (version-support statement)

- [ ] **Step 1:** `.github/dependabot.yml` with two ecosystems: `github-actions` (weekly) and `uv` (weekly, so lockfile bumps arrive as PRs; if GitHub rejects the `uv` ecosystem, fall back to `pip`). Group minor/patch updates to cut PR noise.
- [ ] **Step 2:** `SECURITY.md`: supported versions table (2.x current; 1.x unsupported; note Python ≥3.10 as of 2.3.0 per T17), private reporting via GitHub security advisories, expected response window.
- [ ] **Step 3:** README: short "Supported versions" note linking SECURITY.md.
- [ ] **Step 4:** Consider pyup.io/safety overlap: it scans manifests, not `uv.lock` (it reported green while 12 lock alerts were open). Recommend removal of the pyup integration in the PR description — but **do not** remove its config/badge without maintainer approval; flag it for T14/T16 review.
- [ ] **Step 5:** Suite green (no code changes expected); PR.

**Acceptance criteria:** dependabot.yml valid (GitHub accepts it after merge); SECURITY.md + README statement present; pyup overlap flagged, not unilaterally removed.

**Verify:** post-merge, GitHub shows Dependabot version updates enabled; files exist.

---

### Task 16: Cut release 2.3.0 (standard + maintainer)

**Goal:** Spec step 20: ship everything above as 2.3.0 via the Trusted Publishing pipeline established in Phase 1.

**Files:**
- Modify: `src/prov/__init__.py` (`__version__`), `HISTORY.rst`, `ROADMAP.md`

- [ ] **Step 1:** Branch `release/2.3.0`. Bump `__version__ = "2.3.0"`. Write the `HISTORY.rst` entry following the 2.2.0 format: strict typing + `py.typed` (PEP 561), ruff families I/C4/SIM/RUF/UP045/UP031, exception chaining on `DoNotExist`/`CLIError` (`__cause__` now set — from T9), coverage ratchet + CI enforcement, dependency audit + tox removal (local testing via `uv run --python`), the RTD sphinx pin, and the rdflib 7 outcome from T15 (widened or deferred-with-issue). Tick Phase 2 in `ROADMAP.md`.
- [ ] **Step 2:** Verify milestone #2 on GitHub: all Phase-2 issues closed or explicitly moved out; note any moves in the PR description.
- [ ] **Step 3:** Open the release PR; full CI green; merge.
- [ ] **Step 4: STOP — maintainer confirmation required before publishing.** Then: TestPyPI dry-run via the release workflow's `workflow_dispatch`; verify the upload; create the GitHub release tagged **`2.3.0`** (no `v` prefix — matches existing tags) targeting master, with the HISTORY.rst entry as release notes. The `release published` trigger publishes to PyPI.
- [ ] **Step 5:** Verify `pip index versions prov` / the PyPI page shows 2.3.0 and that the wheel on PyPI contains `py.typed`. Close milestone #2.

**Acceptance criteria:** 2.3.0 on PyPI with py.typed in the wheel; tag `2.3.0` exists; HISTORY.rst/ROADMAP.md updated; milestone closed. Publishing steps executed only after explicit maintainer go-ahead.

**Verify:** `git tag -l 2.3.0` post-release; PyPI shows 2.3.0; `unzip -l` on the published wheel lists `prov/py.typed`.

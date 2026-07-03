# Phases 0–1: Foundation, Tooling, CI & Bug Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute roadmap Phases 0–1 (spec steps 1–15): housekeeping, public roadmap, ruff/pytest/CI/release-automation adoption, and the 2.2.0 bug fixes — culminating in the 2.2.0 release.

**Architecture:** No production-code restructuring. Each task is a small, independently revertable change grouped into 12 PRs (A–L). The public-API smoke test (Task 6) lands before any tooling swap. Behaviour-changing fixes are out of scope (deferred to 3.0 per spec).

**Tech Stack:** uv, ruff (lint+format), pytest (runner only), pre-commit, GitHub Actions, PyPI Trusted Publishing, tox (local multi-interpreter testing).

**Spec:** `docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md`

## Model assignment

Each task names the model to execute it. Rationale: **Haiku** for purely mechanical steps with a complete recipe in the plan and objective pass/fail verification (run a formatter, drop in a config file); **Sonnet** for well-specified config/tooling work that still needs to resolve fallout across the codebase or touch CI/release machinery; **Opus** for tasks needing judgment (API-surface design, community-facing writing/triage, the XML namespace bug).

| Task | PR | What | Model |
|---|---|---|---|
| 1 | A | Housekeeping commit (.gitignore, uv.lock, CLAUDE.md) | Sonnet ✅ done |
| 2 | A | Remove legacy packaging; tidy tox/mypy config | Sonnet ✅ done |
| 3 | A | Changelog consolidation + classifier bump | Sonnet ✅ done |
| 4 | B | ROADMAP.md + milestones + pinned issue | Opus |
| 5 | C | Public-API smoke test | Opus |
| 6 | D | ruff lint (replace flake8) | Sonnet |
| 7 | E | ruff format (replace black) | Haiku |
| 8 | F | pre-commit | Haiku |
| 9 | G | pytest as runner | Sonnet |
| 10 | H | CI modernisation (uv, 3.14, merge mypy job) | Sonnet |
| 11 | H | Remaining mypy stub fixes (the 2 real type errors were fixed in PR A) | Sonnet |
| 12 | I | Release workflow (Trusted Publishing) | Sonnet |
| 13 | J | matplotlib `[plot]` extra (#166, supersedes PR #167 approach) | Sonnet |
| 14 | K | XML default-namespace fix (#155) | Opus |
| 15 | — | Triage #34 / #77 / #89 (analysis only) | Opus |
| 16 | L | Cut release 2.2.0 | Sonnet + maintainer |

**Conventions for every task:**
- Branch from up-to-date `master`: `git checkout master && git pull && git checkout -b <branch>`.
- Full suite must pass before each commit: `uv run python -m unittest discover -s src/` (Tasks 1–8) or `uv run pytest` (Task 9 onward).
- No AI attribution in commits or PRs.
- Open a PR per the group letter; merge order is A → B → C → D → E → F → G → H → I → J → K → L (Task 15 has no PR).

---

### Task 1: Housekeeping commit — PR A (Sonnet 5)

**Files:**
- Modify: `.gitignore` (already updated in working tree — verify content below)
- Add: `uv.lock`, `CLAUDE.md` (currently untracked)

- [ ] **Step 1: Verify .gitignore contains the new block** (appended 2026-07-03; if missing, append):

```gitignore
# Tool caches and local environments
__pycache__/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.venv/
.coverage.*

# Claude Code local settings
.claude/settings.local.json
```

- [ ] **Step 2: Create branch and commit**

```bash
git checkout -b chore/housekeeping
git add .gitignore uv.lock CLAUDE.md
git commit -m "chore: track uv.lock and CLAUDE.md, ignore tool caches"
```

- [ ] **Step 3: Verify nothing unwanted is now tracked**

Run: `git status --short` — expect no staged leftovers; `.eggs/`, `.mypy_cache/` etc. must not appear as untracked.

### Task 2: Remove legacy packaging; tidy tox & mypy config — PR A (Sonnet 5)

**Files:**
- Delete: `setup.py`, `setup.cfg`, `MANIFEST.in`
- Create: `.flake8` (temporary, deleted again in Task 6)
- Modify: `tox.ini`, `pyproject.toml`

- [ ] **Step 1: Preserve flake8 config before deleting setup.cfg.** Create `.flake8`:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
```

- [ ] **Step 2: Delete legacy files**

```bash
git rm setup.py setup.cfg MANIFEST.in
```

- [ ] **Step 3: Replace tox.ini test env** (drops `check-manifest` and the deprecated `python setup.py check`; packaging checks move to CI in Task 12):

```ini
[tox]
envlist = python3.9, python3.10, python3.11, python3.12, python3.13, pypy3
minversion = 4.0
isolated_build = true

[testenv]
commands =
    coverage run -m unittest discover -s src/
    coverage xml
deps =
    coverage
    rdflib>=4.2.1,<7
    lxml>=3.3.5
```

Note: the old `PYTHONPATH` setenv and `allowlist_externals` are unnecessary (isolated build installs the package; coverage is a dep) — remove them.

- [ ] **Step 4: Tidy mypy exclude in pyproject.toml.** The current value works via regex-search semantics but is misleading. Replace:

```toml
[tool.mypy]
python_version = "3.12"
exclude = ["^src/prov/tests/"]
```

- [ ] **Step 5: Verify everything still works**

```bash
uv run mypy src 2>&1 | tail -1        # expect: "Found 8 errors in 5 files (checked 14 source files)" — same 14
uv build                               # expect: dist/prov-2.1.1.tar.gz + .whl built without setup.py
uv run python -m unittest discover -s src/   # expect: OK (expected failures=17)
uv run flake8 src/                     # expect: clean, config picked up from .flake8
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove setup.py/setup.cfg/MANIFEST.in, tidy tox and mypy config"
```

### Task 3: Changelog consolidation + classifier bump — PR A (Sonnet 5)

**Files:**
- Modify: `HISTORY.rst`, `pyproject.toml`
- Delete: `CHANGES.txt`

- [ ] **Step 1: Append pre-1.0 history to HISTORY.rst.** At the end of `HISTORY.rst`, add a section header followed by the entries from `CHANGES.txt` (its `- ` bullets are already valid rst; convert each `vX.Y.Z, date -- title` line to a `^^^`-underlined heading matching the file's existing style):

```rst
Pre-1.0 change log
------------------

0.5.3 (2013-12-13)
^^^^^^^^^^^^^^^^^^
- Changed: Allowed namespaces at bundle level
...
```

(Continue mechanically for every version block in `CHANGES.txt`.)

- [ ] **Step 2: Delete CHANGES.txt and verify docs still build**

```bash
git rm CHANGES.txt
uv run --group dev sphinx-build -W docs docs/_build/html 2>&1 | tail -3   # expect: build succeeded
```

If `-W` fails on pre-existing warnings unrelated to this change, drop `-W` and compare warning count before/after instead.

- [ ] **Step 3: Bump classifier in pyproject.toml**

```toml
    "Development Status :: 5 - Production/Stable",
```

(replacing `"Development Status :: 4 - Beta"`)

- [ ] **Step 4: Commit and open PR A**

```bash
git add -A
git commit -m "chore: consolidate changelog into HISTORY.rst, mark as Production/Stable"
git push -u origin chore/housekeeping
gh pr create --title "Housekeeping: modern packaging config only" --body "Roadmap Phase 0 (steps 1-5): track uv.lock/CLAUDE.md, remove setup.py/setup.cfg/MANIFEST.in, tidy tox/mypy config, consolidate changelog, bump Development Status classifier. No runtime changes. See docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md."
```

Wait for CI green, then merge.

### Task 4: Public roadmap — PR B (Opus)

**Files:**
- Create: `ROADMAP.md`
- Modify: `README.rst` (add a Roadmap section linking to ROADMAP.md)
- GitHub: milestones + pinned tracking issue

- [ ] **Step 1: Write `ROADMAP.md`.** Summarise the spec's phases for a community audience: table of planned releases (2.2.0 tooling/bugfixes, 2.3.0 typing/py.typed, 2.4.0 docs/internals, 3.0.0 compatibility changes with explicit list — Python floor 3.10, rdflib floor raise, behaviour fixes #34/#77/#89/#168, 3.1.0 PROV-JSONLD), the 2.x API-stability promise, and how to give feedback (the tracking issue). Do **not** copy internal effort estimates or agent/tooling details. Link to the design spec for detail.

- [ ] **Step 2: Add a short "Roadmap" section to README.rst** before the existing badges/usage content ends, linking to `ROADMAP.md` and the tracking issue.

- [ ] **Step 3: Create milestones and assign in-scope issues**

```bash
for m in 2.2.0 2.3.0 2.4.0 3.0.0 3.1.0; do gh api repos/trungdong/prov/milestones -f title="$m"; done
gh issue edit 164 --milestone "2.2.0"   # graphics regression (fix already merged)
gh issue edit 166 --milestone "2.2.0"   # matplotlib extra
gh issue edit 155 --milestone "2.2.0"   # XML default namespace
gh issue edit 141 --milestone "2.4.0"   # graphviz install docs
gh issue edit 83  --milestone "2.4.0"   # CLI manpages/docs
gh issue edit 168 --milestone "3.0.0"   # xsd:QName in PROV-JSON
```

Leave #34/#77/#89 unassigned until Task 15's triage decides 2.x vs 3.0.

- [ ] **Step 4: STOP — maintainer review.** Show the maintainer the drafted ROADMAP.md and the tracking-issue text (title: "Modernisation roadmap — tracking & feedback"; body: release table, invitation for comments). **Do not create the public issue until approved.** After approval:

```bash
gh issue create --title "Modernisation roadmap — tracking & feedback" --body-file /tmp/tracking-issue.md
gh issue pin <new-issue-number>
```

- [ ] **Step 5: Commit and PR**

```bash
git checkout -b docs/public-roadmap
git add ROADMAP.md README.rst
git commit -m "docs: add public modernisation roadmap"
git push -u origin docs/public-roadmap
gh pr create --title "Add public roadmap" --body "Roadmap Phase 0 step 6. Adds ROADMAP.md, README link, GitHub milestones, pinned tracking issue."
```

### Task 5: Public-API smoke test — PR C (Opus)

**Files:**
- Create: `src/prov/tests/test_public_api.py`

This test freezes the import surface for the whole 2.x line. Judgment needed on what belongs in the guaranteed list: include everything documented/used by downstream code (ProvStore-style usage), not typing aliases that happen to be module attributes.

- [ ] **Step 1: Write the test**

```python
"""Guards the public API surface for the 2.x line.

Every name listed here must remain importable from its historic location.
Additions are fine; removals or moves are a breaking change (3.0 only).
"""
import importlib
import io
import unittest

PUBLIC_API = {
    "prov": ["Error", "read"],
    "prov.model": [
        # containers
        "ProvDocument", "ProvBundle",
        # base classes
        "ProvRecord", "ProvElement", "ProvRelation",
        # elements
        "ProvEntity", "ProvActivity", "ProvAgent",
        # relations
        "ProvGeneration", "ProvUsage", "ProvCommunication", "ProvStart",
        "ProvEnd", "ProvInvalidation", "ProvDerivation", "ProvAttribution",
        "ProvAssociation", "ProvDelegation", "ProvInfluence",
        "ProvSpecialization", "ProvAlternate", "ProvMention", "ProvMembership",
        # exceptions
        "ProvException", "ProvWarning", "ProvExceptionInvalidQualifiedName",
        "ProvElementIdentifierRequired",
        # identifiers & literals (historically importable from prov.model too)
        "Namespace", "QualifiedName", "Identifier", "Literal",
        "NamespaceManager", "PROV", "XSD", "XSI",
        "parse_xsd_datetime", "sorted_attributes",
    ],
    "prov.identifier": ["Identifier", "QualifiedName", "Namespace"],
    "prov.constants": [
        "PROV_ENTITY", "PROV_ACTIVITY", "PROV_AGENT", "PROV_GENERATION",
        "PROV_USAGE", "PROV_COMMUNICATION", "PROV_START", "PROV_END",
        "PROV_INVALIDATION", "PROV_DERIVATION", "PROV_ATTRIBUTION",
        "PROV_ASSOCIATION", "PROV_DELEGATION", "PROV_INFLUENCE",
        "PROV_SPECIALIZATION", "PROV_ALTERNATE", "PROV_MENTION",
        "PROV_MEMBERSHIP", "PROV_BUNDLE", "PROV_N_MAP", "PROV_BASE_CLS",
        "PROV_TYPE", "PROV_LABEL", "PROV_VALUE", "PROV_LOCATION", "PROV_ROLE",
    ],
    "prov.serializers": ["get", "Serializer", "Registry", "DoNotExist"],
    "prov.dot": ["prov_to_dot"],
    "prov.graph": ["prov_to_graph", "graph_to_prov"],
}


class TestPublicAPI(unittest.TestCase):
    def test_names_importable(self):
        missing = []
        for module_name, names in PUBLIC_API.items():
            module = importlib.import_module(module_name)
            for name in names:
                if not hasattr(module, name):
                    missing.append(f"{module_name}.{name}")
        self.assertEqual(missing, [], "Public API names missing: %s" % missing)

    def test_serializer_registry_formats(self):
        import prov.serializers
        for fmt in ("json", "xml", "rdf", "provn"):
            self.assertIsNotNone(prov.serializers.get(fmt))

    def test_round_trip_each_format(self):
        from prov.tests.examples import primer_example
        document = primer_example()
        for fmt in ("json", "xml", "rdf"):
            with self.subTest(format=fmt):
                stream = io.StringIO()
                document.serialize(destination=stream, format=fmt)
                stream.seek(0)
                from prov.model import ProvDocument
                round_tripped = ProvDocument.deserialize(
                    source=stream, format=fmt
                )
                self.assertEqual(document, round_tripped, fmt)
        # PROV-N is write-only: serialize must succeed
        self.assertTrue(document.serialize(format="provn"))
```

Before finalising, verify each listed name actually exists today (`python -c "import prov.model as m; ..."`) and check `prov.tests.examples` for the exact example-builder names (`primer_example` exists; confirm signature). Adjust the RDF round-trip if document equality needs `unified()` (check how `test_rdf.py`'s `RoundTripTestCase` asserts equivalence and mirror it).

- [ ] **Step 2: Run the new test — must pass against current master**

```bash
uv run python -m unittest prov.tests.test_public_api -v
```

Expected: all pass. If a name fails, decide: mistyped name (fix the list) — never add code to make a name exist.

- [ ] **Step 3: Run full suite, commit, PR**

```bash
uv run python -m unittest discover -s src/
git checkout -b test/public-api-guard
git add src/prov/tests/test_public_api.py
git commit -m "test: add public API surface guard for the 2.x line"
git push -u origin test/public-api-guard
gh pr create --title "Add public-API smoke test" --body "Roadmap Phase 1 step 7. Freezes the importable API surface before tooling changes begin."
```

### Task 6: ruff lint replacing flake8 — PR D (Sonnet 5)

**Files:**
- Modify: `pyproject.toml` (add ruff config + dev dep, remove flake8 dev dep)
- Delete: `.flake8`
- Modify: `CLAUDE.md` (lint command), `Makefile` (if it references flake8)

- [ ] **Step 1: Add ruff, remove flake8**

```bash
uv add --group dev ruff
uv remove --group dev flake8
```

- [ ] **Step 2: Add config to pyproject.toml** (conservative start, matching current flake8 behaviour plus bugbear/pyupgrade):

```toml
[tool.ruff]
line-length = 88
target-version = "py39"
extend-exclude = ["build", "dist", ".eggs"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
    "B",   # flake8-bugbear
    "UP",  # pyupgrade (3.9-safe)
]
ignore = [
    "E203",  # whitespace before ':' (black/ruff-format compatible)
    "E501",  # line length handled by the formatter
]
```

- [ ] **Step 3: Run and auto-fix**

```bash
uv run ruff check src/ --statistics       # review what fires first
uv run ruff check src/ --fix
uv run ruff check src/                    # remaining issues: fix manually if trivial,
                                          # else add a targeted per-file ignore with a comment
```

Judgment rule: `--fix` output must be reviewed hunk-by-hunk (`git diff`); any fix that changes semantics (not just style) is reverted and noted for manual handling.

- [ ] **Step 4: Delete `.flake8`; update CLAUDE.md** ("Lint: `uv run ruff check src/`") and `Makefile` if it has a lint target.

- [ ] **Step 5: Verify, commit, PR**

```bash
uv run python -m unittest discover -s src/    # OK (expected failures=17)
uv run python -m unittest prov.tests.test_public_api
git checkout -b chore/ruff-lint
git add -A
git commit -m "chore: replace flake8 with ruff lint"
git push -u origin chore/ruff-lint
gh pr create --title "Adopt ruff lint" --body "Roadmap Phase 1 step 8. Replaces flake8; rule set E/F/W/B/UP; mechanical autofixes only."
```

### Task 7: ruff format replacing black — PR E (Haiku)

**Files:**
- Modify: `pyproject.toml` (remove `[tool.black]` and black dev dep), `CLAUDE.md`, `Makefile` (if referencing black)

- [ ] **Step 1: Swap the tools**

```bash
uv remove --group dev black
```

Remove the entire `[tool.black]` section from `pyproject.toml`. Also remove the now-dead `[tool.pylint.messages_control]` and `[tool.pylint.format]` sections (pylint is not used anywhere in CI or docs).

- [ ] **Step 2: Format and inspect the diff**

```bash
uv run ruff format src/
git diff --stat     # expect: near-zero changes coming from black 24 conventions
```

If the diff is more than trivial whitespace/quote normalisation, stop and report before committing.

- [ ] **Step 3: Update CLAUDE.md** ("Format: `uv run ruff format src/`").

- [ ] **Step 4: Verify, commit, PR**

```bash
uv run python -m unittest discover -s src/
git checkout -b chore/ruff-format
git add -A
git commit -m "chore: replace black with ruff format"
git push -u origin chore/ruff-format
gh pr create --title "Adopt ruff format" --body "Roadmap Phase 1 step 9. Replaces black; formatting diff reviewed and minimal."
```

### Task 8: pre-commit — PR F (Haiku)

**Files:**
- Create: `.pre-commit-config.yaml`
- Modify: `pyproject.toml` (add pre-commit to dev group), `CONTRIBUTING.rst` (one paragraph: how to enable)

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0   # placeholder — immediately run `pre-commit autoupdate` to pin latest
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0   # placeholder — pinned by autoupdate
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-toml
```

- [ ] **Step 2: Install, pin, and run against the whole tree**

```bash
uv add --group dev pre-commit
uv run pre-commit autoupdate
uv run pre-commit run --all-files    # expect: all hooks pass (tree is already ruff-clean)
```

If end-of-file/trailing-whitespace fix files, include those fixes in this commit.

- [ ] **Step 3: Add a "pre-commit" paragraph to CONTRIBUTING.rst** (`uv run pre-commit install` once after cloning).

- [ ] **Step 4: Commit, PR**

```bash
git checkout -b chore/pre-commit
git add -A
git commit -m "chore: add pre-commit with ruff and hygiene hooks"
git push -u origin chore/pre-commit
gh pr create --title "Add pre-commit" --body "Roadmap Phase 1 step 10."
```

### Task 9: pytest as runner — PR G (Sonnet 5)

**Files:**
- Modify: `pyproject.toml` (pytest config + dev deps), `tox.ini`, `CLAUDE.md`, `.coveragerc`

Test *code* is untouched — pytest runs unittest-style classes natively.

- [ ] **Step 1: Record the baseline count**

```bash
uv run python -m unittest discover -s src/ 2>&1 | tail -3
```

Expected: `Ran 961 tests ... OK (expected failures=17)`. Note the exact number.

- [ ] **Step 2: Add pytest**

```bash
uv add --group dev pytest pytest-cov
```

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["src/prov/tests"]
```

- [ ] **Step 3: Verify identical collection and results**

```bash
uv run pytest --collect-only -q | tail -1   # expect: exactly 961 tests collected
uv run pytest -q | tail -3                  # expect: 944 passed, 17 xfailed (unittest expectedFailure maps to xfail)
```

Any discrepancy in counts must be explained before proceeding (e.g. a module unittest discovers but pytest doesn't); do not continue with a mismatch.

- [ ] **Step 4: Move coverage config into pyproject.toml and switch runners.** Port `.coveragerc` verbatim into `[tool.coverage.run]`/`[tool.coverage.paths]`/`[tool.coverage.report]` tables, delete `.coveragerc`, and update `tox.ini`:

```ini
[testenv]
commands =
    coverage run -m pytest
    coverage xml
deps =
    coverage
    pytest
    rdflib>=4.2.1,<7
    lxml>=3.3.5
```

- [ ] **Step 5: Update CLAUDE.md Common commands** (test suite: `uv run pytest`; single test: `uv run pytest src/prov/tests/test_model.py::TestFlattening::test_flattening -v`; coverage: `uv run coverage run -m pytest && uv run coverage report -m`).

- [ ] **Step 6: Verify via tox for one env, commit, PR**

```bash
uv run tox -e python3.13 | tail -5   # expect green
git checkout -b chore/pytest-runner
git add -A
git commit -m "chore: adopt pytest as the test runner (test code unchanged)"
git push -u origin chore/pytest-runner
gh pr create --title "Adopt pytest as test runner" --body "Roadmap Phase 1 step 11. Collection count verified identical (961); unittest-style tests unchanged."
```

### Task 10: CI modernisation — PR H (Sonnet 5)

**Files:**
- Modify: `.github/workflows/CI.yml`
- Delete: `.github/workflows/mypy.yml` (merged into CI.yml)

- [ ] **Step 1: Rewrite CI.yml** (uv-based, matrix runs pytest directly — tox stays for local multi-interpreter use; check latest major versions of the actions before committing):

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master, dev]
  workflow_dispatch:

jobs:
  tests:
    name: pytest on ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "pypy3.11"]
    steps:
      - uses: actions/checkout@v4
      - name: Setup Graphviz
        uses: ts-graphviz/setup-graphviz@v2
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: ${{ matrix.python-version }}
      - name: Run tests
        run: |
          uv sync --extra rdf --extra xml --group dev
          uv run coverage run -m pytest
          uv run coverage xml
      - name: Coveralls Parallel
        uses: coverallsapp/github-action@v2
        with:
          flag-name: Python${{ matrix.python-version }}
          parallel: true

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: |
          uv sync --group dev
          uv run ruff check src/
          uv run ruff format --check src/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: |
          uv sync --extra rdf --extra xml --group dev
          uv run mypy src

  package:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: |
          uv build
          uvx twine check dist/*

  finish:
    needs: tests
    if: ${{ always() }}
    runs-on: ubuntu-latest
    steps:
      - name: Coveralls Finished
        uses: coverallsapp/github-action@v2
        with:
          parallel-finished: true
          carryforward: "Python3.9,Python3.10,Python3.11,Python3.12,Python3.13,Python3.14,Pythonpypy3.11"
```

Notes: the `typecheck` job will FAIL until Task 11 lands — Tasks 10 and 11 are one PR (H) and merge together. Add `mypy` to the dev group in Task 11. Update the pypy env name in tox.ini if needed for consistency.

- [ ] **Step 2: Delete mypy.yml**

```bash
git rm .github/workflows/mypy.yml
```

- [ ] **Step 3: Add 3.14 to tox envlist and pyproject classifiers**

```toml
    "Programming Language :: Python :: 3.14",
```

- [ ] **Step 4: Commit (PR opened after Task 11 on the same branch)**

```bash
git checkout -b chore/ci-uv
git add -A
git commit -m "ci: switch to uv, add Python 3.14, merge lint/typecheck/package jobs"
```

### Task 11: Remaining mypy stub fixes — PR H (Sonnet)

> **Scope note (post-PR A):** the two genuine type errors listed in Steps 2–3 below were already fixed in PR A (#169). What remains is Step 1 (add mypy + stub packages to the dev dependency group) and handling any new errors surfaced by `types-networkx`.

**Files:**
- Modify: `pyproject.toml` (dev deps), `src/prov/serializers/__init__.py:58`, `src/prov/model.py:~455-500`

- [ ] **Step 1: Add mypy + stubs to the dev group**

```bash
uv add --group dev mypy types-python-dateutil lxml-stubs types-networkx
```

This clears the 5 `import-untyped` errors (dateutil ×3 across model.py/provrdf.py, networkx, lxml). Note `types-networkx` may surface *new* errors in `graph.py`/`dot.py` — fix any that are trivial annotations; if a stub conflict is non-trivial, use a targeted `# type: ignore[<code>]` with a comment.

- [ ] **Step 2: Fix `serializers/__init__.py:58`** (old type-comment None assignment). Replace:

```python
    serializers = None  # type: dict[str, type[Serializer]]
```

with:

```python
    serializers: ClassVar[dict[str, type[Serializer]] | None] = None
```

Add `from typing import ClassVar` and ensure `from __future__ import annotations` is at the top (needed for `|` on 3.9). Then fix the fallout: wherever `Registry.serializers` is subscripted after `load_serializers()` (see `get()` around line 75), mypy now knows it may be `None` — add:

```python
    if Registry.serializers is None:
        Registry.load_serializers()
    serializers = Registry.serializers
    assert serializers is not None
```

(match the actual code shape found in `get()`; keep runtime behaviour identical).

- [ ] **Step 3: Fix `model.py:487`.** The local `value` is first bound as a `QualifiedName` in one branch and as `datetime | None` in another. Declare it with an explicit union before the branch chain (find the first assignment in that method, around line 460):

```python
    value: QualifiedName | datetime.datetime | Literal | str | None
```

Use the actual set of types assigned across all branches of that method — read the whole method first; do not guess. No runtime change.

- [ ] **Step 4: Verify zero errors, full suite, commit, push, open PR H**

```bash
uv run mypy src               # expect: Success: no issues found in 14 source files
uv run pytest -q | tail -2    # expect: 944 passed, 17 xfailed (+ public-api tests)
git add -A
git commit -m "chore: fix all mypy errors; pin mypy and stubs in dev group"
git push -u origin chore/ci-uv
gh pr create --title "Modernise CI and fix mypy errors" --body "Roadmap Phase 1 step 12. uv-based CI, Python 3.14, lint/typecheck/package jobs, mypy clean."
```

### Task 12: Release workflow with Trusted Publishing — PR I (Sonnet 5)

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release.yml**

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:   # dry-run to TestPyPI

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: |
          uv build
          uvx twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    if: github.event_name == 'workflow_dispatch'
    needs: build
    runs-on: ubuntu-latest
    environment: testpypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    if: github.event_name == 'release'
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 2: STOP — maintainer actions (cannot be done by the agent):**
  1. On PyPI: project `prov` → Publishing → add GitHub publisher (owner `trungdong`, repo `prov`, workflow `release.yml`, environment `pypi`).
  2. Same on TestPyPI with environment `testpypi`.
  3. On GitHub: create environments `pypi` and `testpypi` (Settings → Environments); optionally add required reviewers on `pypi`.

- [ ] **Step 3: Commit, PR, then dry-run**

```bash
git checkout -b ci/release-automation
git add .github/workflows/release.yml
git commit -m "ci: add release workflow with PyPI trusted publishing"
git push -u origin ci/release-automation
gh pr create --title "Automated releases via PyPI Trusted Publishing" --body "Roadmap Phase 1 step 13. Publishes on GitHub release; workflow_dispatch dry-runs to TestPyPI."
```

After merge: `gh workflow run release.yml` and verify the TestPyPI upload succeeds end-to-end before Task 16 relies on it.

### Task 13: matplotlib `[plot]` extra (#166) — PR J (Sonnet 5)

**Files:**
- Modify: `pyproject.toml`, `src/prov/model.py` (~line 2455, the lazy matplotlib import in `plot()`)
- Test: `src/prov/tests/test_extras.py`

Decision context (from spec + maintainer policy): PR #167 moves `pydot` out of core deps, which would break `prov.dot` for existing plain installs — **not acceptable in 2.x**. Instead: keep `pydot` core, add a `plot` extra for matplotlib only, give a helpful error. The pydot→extra move is 3.0 material. The maintainer will comment on PR #167 crediting the contributor and explaining (draft the comment for them; do not post).

- [ ] **Step 1: Write the failing test** (in `test_extras.py`):

```python
    def test_plot_without_matplotlib_raises_helpful_error(self):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("matplotlib"):
                raise ImportError("No module named %r" % name)
            return real_import(name, *args, **kwargs)

        document = prov.model.ProvDocument()
        document.entity(EX_NS["e1"])
        builtins.__import__ = fake_import
        try:
            with self.assertRaises(ImportError) as ctx:
                document.plot()   # no filename -> interactive path -> needs matplotlib
            self.assertIn("prov[plot]", str(ctx.exception))
        finally:
            builtins.__import__ = real_import
```

Adapt namespace setup to the conventions already in `test_extras.py` (check its imports/fixtures first).

- [ ] **Step 2: Run it — expect FAIL** (current code raises a bare ImportError without the hint):

```bash
uv run pytest src/prov/tests/test_extras.py -k helpful_error -v
```

- [ ] **Step 3: Implement.** In `model.py` `plot()`, wrap the matplotlib import:

```python
            try:
                import matplotlib.pylab as plt
                import matplotlib.image as mpimg
            except ImportError as e:
                raise ImportError(
                    "The plot() method requires matplotlib when no filename is"
                    " provided. Install it with: pip install prov[plot]"
                ) from e
```

And in `pyproject.toml`, add the extra (keep pydot in core deps — do NOT take PR #167's removal):

```toml
[project.optional-dependencies]
plot = [
    "matplotlib>=3.6",
]
```

- [ ] **Step 4: Run test (PASS), full suite, commit, PR; draft the #167 comment**

```bash
uv run pytest src/prov/tests/test_extras.py -k helpful_error -v   # PASS
uv run pytest -q | tail -2
git checkout -b fix/matplotlib-extra
git add -A
git commit -m "fix: add [plot] extra and helpful error when matplotlib is missing (#166)"
git push -u origin fix/matplotlib-extra
gh pr create --title "Add [plot] extra for matplotlib (#166)" --body "Fixes #166. Keeps pydot as a core dependency (moving it is a breaking change deferred to 3.0). Supersedes the approach in #167 - thanks @Benjamin2107 for the report and PR."
```

Write the draft comment for PR #167 into the PR J description or hand it to the maintainer; the maintainer posts it and closes #167.

### Task 14: XML default-namespace deserialization fix (#155) — PR K (Opus)

**Files:**
- Modify: `src/prov/serializers/provxml.py` (`_extract_attributes` ~line 358, `xml_qname_to_QualifiedName` ~line 393)
- Test: `src/prov/tests/test_xml.py`

Root cause (verified 2026-07-03): for a sub-element in the default namespace, `subel.prefix` is `None`, so line 361 builds the string `"None:value"`; additionally the default-namespace branch of `xml_qname_to_QualifiedName` does not map the PROV/XSD URIs onto the canonical `PROV`/`XSD` namespace objects.

- [ ] **Step 1: Write the failing round-trip test** (in `test_xml.py`, alongside the other `ProvXMLSerializer` tests — mirror their style):

```python
    def test_deserialization_with_prov_as_default_namespace(self):
        # https://github.com/trungdong/prov/issues/155
        xml_string = """<document xmlns="http://www.w3.org/ns/prov#"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:prov="http://www.w3.org/ns/prov#"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:ex="https://example.org/">
          <entity prov:id="ex:e">
            <value xsi:type="xsd:int">1</value>
          </entity>
        </document>"""
        document = prov.model.ProvDocument.deserialize(
            content=xml_string, format="xml"
        )
        entity = list(document.get_records(prov.model.ProvEntity))[0]
        # the <value> element is in the default (PROV) namespace:
        # it must parse as prov:value, not "None:value"
        values = list(entity.get_attribute(PROV["value"]))
        self.assertEqual(len(values), 1)
        # and the document must serialize back to XML without error
        self.assertTrue(document.serialize(format="xml"))
```

Check `ProvDocument.deserialize`'s parameter name for string input (`content=`) and `get_attribute`'s exact name/signature in `model.py` before finalising; adjust to the real API.

- [ ] **Step 2: Run — expect FAIL** (attribute comes back as `None:value` and/or re-serialization raises `ValueError: Invalid tag name 'None:value'`):

```bash
uv run pytest src/prov/tests/test_xml.py -k default_namespace -v
```

- [ ] **Step 3: Fix.** In `_extract_attributes` (line ~360), don't fabricate a `"None:..."` qname:

```python
        _t = xml_qname_to_QualifiedName(
            subel,
            "%s:%s" % (subel.prefix, sqname.localname)
            if subel.prefix
            else sqname.localname,
        )
```

In `xml_qname_to_QualifiedName`, make the default-namespace branch consistent with the prefixed branch (canonical PROV/XSD namespaces):

```python
    if None in element.nsmap:
        ns_uri = element.nsmap[None]
        if ns_uri == XML_XSD_URI:
            ns = XSD
        elif ns_uri == PROV.uri:
            ns = PROV
        else:
            ns = Namespace("", ns_uri)
        return ns[qname_str]
```

- [ ] **Step 4: Run the new test (PASS) and the FULL suite** — this function is on the hot path for all XML fixtures; any regression in `test_xml.py`'s fixture round-trips means the fix is wrong, not the fixtures:

```bash
uv run pytest src/prov/tests/test_xml.py -v 2>&1 | tail -5
uv run pytest -q | tail -2
```

- [ ] **Step 5: Commit, PR**

```bash
git checkout -b fix/xml-default-namespace
git add -A
git commit -m "fix: handle default-namespace elements in PROV-XML deserialization (#155)"
git push -u origin fix/xml-default-namespace
gh pr create --title "Fix XML deserialization with prov as default namespace" --body "Fixes #155. Elements without a prefix produced 'None:value' qualified names, breaking round-trips of ProvToolbox output."
```

### Task 15: Triage #34, #77, #89 — no PR (Opus)

**Files:**
- Create: `docs/superpowers/triage/2026-07-behaviour-bugs.md`

- [ ] **Step 1: For each issue, reproduce.** Write a minimal script per issue against the current code, using the scenario from the issue thread (#34 merging same-value/different-type attributes; #77 Decimal literal comparison; #89 literal with vs without explicit datatype). Record actual behaviour.

- [ ] **Step 2: For each, decide and document:** Can it be fixed without changing any currently-correct observable output? If yes → candidate for 2.x, note the fix sketch. If no (output/equality semantics change) → 3.0, note what changes and who is affected. Write all three verdicts with repro snippets into the triage doc.

- [ ] **Step 3: Assign milestones per verdict and comment on each issue** with a one-paragraph status (drafts reviewed by maintainer before posting — STOP for approval):

```bash
gh issue edit 34 --milestone "3.0.0"   # (or 2.2.0/2.3.0 per verdict)
gh issue edit 77 --milestone "3.0.0"
gh issue edit 89 --milestone "3.0.0"
```

- [ ] **Step 4: Commit the triage doc to master via a docs PR or fold into PR L.**

### Task 16: Cut release 2.2.0 — PR L (Sonnet 5 + maintainer)

**Files:**
- Modify: `src/prov/__init__.py` (`__version__`), `HISTORY.rst`

Precondition: PRs A–K merged; TestPyPI dry-run (Task 12 step 3) verified.

- [ ] **Step 1: Write the changelog entry** at the top of `HISTORY.rst`:

```rst
2.2.0 (2026-XX-XX)
^^^^^^^^^^^^^^^^^^
* Fixed graphical output when a filename is supplied (#164)
* Fixed PROV-XML deserialization when prov is the default namespace (#155)
* New ``plot`` extra: ``pip install prov[plot]`` for matplotlib support (#166)
* Marked as Production/Stable; added Python 3.14 to the test matrix
* Tooling: ruff (lint+format), pytest runner, uv-based CI, automated PyPI
  releases via Trusted Publishing. No public API changes.
```

(Adjust to what actually merged; date = release day.)

- [ ] **Step 2: Bump version**

In `src/prov/__init__.py`: `__version__ = "2.2.0"`.

- [ ] **Step 3: PR, merge, then STOP — maintainer creates the release** (outward-facing; triggers publication):

```bash
git checkout -b release/2.2.0
git add HISTORY.rst src/prov/__init__.py
git commit -m "Release 2.2.0"
git push -u origin release/2.2.0
gh pr create --title "Release 2.2.0" --body "Changelog + version bump. Milestone: 2.2.0."
# after merge, MAINTAINER runs:
gh release create 2.2.0 --title "2.2.0" --notes-file <(sed -n '/^2.2.0/,/^2.1.1/p' HISTORY.rst)
```

- [ ] **Step 4: Verify publication**

```bash
# wait for release.yml to go green, then:
uvx --with prov==2.2.0 python -c "import prov; print(prov.__version__)"   # expect 2.2.0
```

Close milestone 2.2.0; update `ROADMAP.md` status line (can ride in the next PR).

---

## Self-review notes

- Spec coverage: steps 1–15 of the spec map to Tasks 1–16 (spec step 3 folded into Task 2; spec step 12 split into Tasks 10+11; spec step 14 split into Tasks 13/14/15). rdflib `<8` widening is spec'd as "try as early as Phase 2" — intentionally not in this plan.
- Verification counts (961 tests / 17 expected failures / 8 mypy errors / 14 checked files) recorded from a live run on 2026-07-03.
- Tasks 4, 12, 15, 16 contain explicit STOP points for maintainer-only actions (public posts, PyPI configuration, release creation).

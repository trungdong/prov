# Phase 3: Docs, pytest Idioms & Structural Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute roadmap Phase 3 (spec steps 21–27): docs tooling modernisation (furo/MyST/napoleon) and Diátaxis reorganisation, a docstring accuracy-then-style pass, the pytest-native test redesign plus hardening (Hypothesis, malformed-input corpus, minimal-install CI), the `model.py` package split, 3.0 deprecation signposting — culminating in the 2.4.0 release.

**Architecture:** No public API changes (2.x freeze). Docs work is additive/reorganising; the test redesign is gated on a design doc and proves collected-test parity at every migration PR; the `model.py` split is pure moves with `prov/model/__init__.py` re-exporting every historic name (verified by a captured before/after `dir()` diff plus the public-API smoke test). The only intentional observable changes: deprecation/future warnings (spec step 26 — 2.4.0 is the signposting release) and serializer-registry clean degradation when optional extras are missing (spec step 24b — previously a hard crash, so strictly improving).

**Tech Stack:** uv, Sphinx 8 + furo + MyST + napoleon + intersphinx + sphinx-copybutton, ReadTheDocs (uv build), pytest (parametrized fixtures, `tmp_path`), Hypothesis, ruff, mypy `--strict`, GitHub Actions, PyPI Trusted Publishing.

**Spec:** `docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md` (steps 21–27)

**User decisions (already made):**
- Docs stay on Sphinx/RTD; modernise with furo, MyST, napoleon; reorganise along Diátaxis (spec decision table).
- Docstring pass is accuracy-first, then napoleon style — added 2026-07-05 at maintainer request (spec step 23).
- Test redesign starts with a design doc deliberately NOT constrained by the legacy structure; migrate one format first as pattern-setter; test count/assertions provably preserved via `pytest --collect-only` before/after (spec step 24).
- `model.py` splits into `records.py` / `bundle.py` / `namespaces.py` with `prov/model/__init__.py` re-exporting historic names; pure moves, no behaviour edits in the same PR (spec steps 25, 30).
- 2.x freeze holds: behaviour-changing fixes deferred to 3.0; 2.4.0 only signposts them (spec steps 26, 31, 36).
- Release gate pattern from Phase 2: merge the release PR, then STOP and AskUserQuestion before any publishing.
- Loose ends from Phase 2 folded in: dead Makefile targets, stale CLAUDE.md parentheticals, `docs/requirements.txt` sync risk (deleted in T1). The test-module function-local-imports chore the maintainer never green-lit standalone is subsumed by the spec-sanctioned test rewrite (T9–T11) — imports get normalised as those files are rewritten, no separate chore PR.

## Model assignment

Per the routing config: **mechanical** → haiku, **standard** → sonnet, **frontier** → inherit (session model).

| Task | Branch | What | Tier |
|---|---|---|---|
| 1 | chore/makefile-claude-md | Makefile rewrite + CLAUDE.md stale text | mechanical |
| 2 | docs/tooling | furo/MyST/napoleon/intersphinx/copybutton; RTD builds with uv | standard |
| 3 | docs/diataxis-tutorial | Diátaxis index restructure + tutorial (replaces usage.rst) | frontier |
| 4 | docs/howto | How-to guides: formats, graphics (#141), CLI (#83), NetworkX | standard |
| 5 | docs/reference | Per-module API reference replacing modules.rst dump | standard |
| 6 | docs/explanation | PROV-DM primer + unification/flattening semantics | frontier |
| 7 | docs/docstrings-modules | Docstring accuracy+napoleon pass: everything except model.py | standard |
| 8 | docs/docstrings-model | Docstring accuracy+napoleon pass: model.py | frontier |
| 9 | tests/redesign-spec | Test methodology design doc | frontier |
| 10 | tests/pytest-json | Pattern-setter: shared pytest matrix + JSON migration | frontier |
| 11 | tests/pytest-xml-rdf | Migrate XML + RDF test modules | standard |
| 12 | tests/pytest-rest | Migrate remaining test modules, retire legacy scaffolding | standard |
| 13 | tests/hypothesis | Property-based round-trip tests | frontier |
| 14 | tests/malformed-corpus | Malformed-input corpus per deserializer | standard |
| 15 | ci/minimal-install | Registry clean degradation + minimal-install CI job | standard |
| 16 | refactor/model-package | Split model.py into a package with re-exports | frontier |
| 17 | chore/deprecations-3.0 | Deprecation warnings + "Upgrading to 3.0" signposting | standard |
| 18 | release/2.4.0 | Cut release 2.4.0 | standard + maintainer |

**Conventions for every task** (Phase 2 process rules that worked):
- Branch from up-to-date `master`: `git checkout master && git pull && git checkout -b <branch>`. Single shared checkout, no worktrees, strictly sequential.
- Before every commit: `uv run ruff check src/ && uv run ruff format --check src/ && uv run mypy src && uv run pytest` all green.
- One focused PR per task; merge only after CI green (`gh run list --branch X --workflow CI` for the head SHA, then `gh run watch <id> --exit-status`).
- No AI attribution in commits or PRs.
- When a task changes tooling or structure that CLAUDE.md describes, update CLAUDE.md in the same PR.
- Baseline at plan time: 1085 passed / 17 xfailed, coverage floor 97 (thin margin: 97.42% — new tests help, deletions need care), mypy strict clean on 14 files.

---

### Task 1: Makefile rewrite + CLAUDE.md stale text — chore/makefile-claude-md (mechanical)

**Goal:** Clear the two Phase 2 housekeeping loose ends: dead `setup.py`-era Makefile targets and two stale CLAUDE.md parentheticals.

**Files:**
- Modify: `Makefile`
- Modify: `CLAUDE.md:20` and `CLAUDE.md:24`

**Acceptance Criteria:**
- [ ] `make test`, `make coverage`, `make lint`, `make dist` all run successfully via uv; `release` target removed (Trusted Publishing owns releases); no target references `setup.py`.
- [ ] CLAUDE.md no longer says "(once created)" or "once added".

**Verify:** `make test` → full pytest run passes; `grep -c "setup.py" Makefile` → 0.

**Steps:**

- [ ] **Step 1: Replace `Makefile` wholesale with:**

```makefile
.PHONY: help clean clean-build clean-pyc lint format test test-all coverage docs dist

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with ruff"
	@echo "format - format code with ruff"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every supported Python version via uv"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation"
	@echo "dist - build sdist and wheel"

clean: clean-build clean-pyc
	rm -fr htmlcov/ .coverage coverage.xml

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr src/*.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

test:
	uv run pytest

test-all:
	for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do \
		uv run --python $$py --extra rdf --extra xml pytest || exit 1; \
	done

coverage:
	uv run coverage run -m pytest
	uv run coverage report -m
	uv run coverage html
	open htmlcov/index.html

docs:
	uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html
	open docs/_build/html/index.html

dist: clean
	uv build
	ls -l dist
```

(The old `docs` target ran `sphinx-apidoc` regenerating `docs/prov.rst`/`modules.rst`; those files are checked in and will be replaced in Task 5, so apidoc regeneration goes now.)

- [ ] **Step 2: CLAUDE.md edits.** In `CLAUDE.md`, change `` `ROADMAP.md` (once created)`` → `` `ROADMAP.md` `` and "The public-API smoke test guards this once added." → "The public-API smoke test (`src/prov/tests/test_public_api.py`) guards this."

- [ ] **Step 3: Verify:** `make lint && make test && make dist` all succeed. Commit `chore: rewrite Makefile around uv; fix stale CLAUDE.md notes`, open PR, merge after CI green.

---

### Task 2: Docs tooling modernisation — docs/tooling (standard)

**Goal:** Spec step 21 — furo theme, MyST, napoleon, intersphinx, sphinx-copybutton in one PR; ReadTheDocs builds with uv; `docs/requirements.txt` deleted (kills the manual-sync loose end).

**Files:**
- Modify: `pyproject.toml` (docs group)
- Modify: `docs/conf.py` (full rewrite)
- Modify: `.readthedocs.yml`
- Delete: `docs/requirements.txt`
- Modify: `CLAUDE.md` (docs build command if it changes)

**Acceptance Criteria:**
- [ ] `uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html` exits 0 with furo theme; record the warning count as baseline for later docs tasks.
- [ ] `docs/requirements.txt` gone; `.readthedocs.yml` installs via uv from the `docs` dependency group.
- [ ] Existing pages (usage, modules, history, …) still render — reorganisation is NOT this task.

**Verify:** sphinx-build exits 0; `grep furo docs/_build/html/index.html` finds the theme's assets.

**Steps:**

- [ ] **Step 1: Update the docs group in `pyproject.toml`:**

```toml
docs = [
    "sphinx>=8.1.3,<9",
    "furo",
    "myst-parser",
    "sphinx-copybutton",
]
```

Drop `sphinx-rtd-theme`. Then attempt lifting the `<9` cap (it existed for the RTD/rtd-theme breakage, PR #187): `uv lock --upgrade-package sphinx`, rebuild docs; keep the cap only if the build fails, and update `docs/dependencies.md` either way (it documents the pin rationale).

- [ ] **Step 2: Rewrite `docs/conf.py` wholesale:**

```python
"""Sphinx configuration for the prov documentation."""

import os
import sys

# Make the src-layout package importable so autodoc and `prov.__version__` work.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import prov  # noqa: E402

project = "prov"
copyright = "2026, Trung Dong Huynh"
author = "Trung Dong Huynh"
version = prov.__version__
release = prov.__version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
}

autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

myst_enable_extensions = ["colon_fence", "deflist"]

html_theme = "furo"
html_static_path = ["_static"]
htmlhelp_basename = "provdoc"

latex_documents = [
    ("index", "prov.tex", "PROV Python Package Documentation", "Trung Dong Huynh", "manual"),
]
man_pages = [
    ("index", "prov", "PROV Python Package Documentation", ["Trung Dong Huynh"], 1)
]
texinfo_documents = [
    ("index", "prov", "PROV Python Package Documentation", "Trung Dong Huynh",
     "prov", "A Python library for the W3C PROV Data Model", "Documentation"),
]
```

(If `docs/_static/` does not exist, create it with a `.gitkeep` or drop `html_static_path` — sphinx warns on a missing dir.)

- [ ] **Step 3: Rewrite `.readthedocs.yml`** (RTD's documented uv pattern):

```yaml
version: 2

build:
  os: ubuntu-24.04
  tools:
    python: "3.13"
  jobs:
    create_environment:
      - asdf plugin add uv
      - asdf install uv latest
      - asdf global uv latest
      - uv venv "$READTHEDOCS_VIRTUALENV_PATH"
    install:
      - UV_PROJECT_ENVIRONMENT="$READTHEDOCS_VIRTUALENV_PATH" uv sync --frozen --no-dev --group docs --extra rdf --extra xml

sphinx:
  configuration: docs/conf.py

formats: all
```

Delete `docs/requirements.txt`.

- [ ] **Step 4: Build, record baseline warning count, update CLAUDE.md** (docs build now `uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html`). If `formats: all` breaks the RTD build with furo (PDF builder), drop to `formats: [htmlzip]` and note it in the PR.

- [ ] **Step 5: Commit, PR, watch the RTD PR preview build** (RTD builds PRs for this repo since #187) — it must go green before merge; that is the real test of the uv build recipe.

---

### Task 3: Diátaxis restructure + tutorial — docs/diataxis-tutorial (frontier)

**Goal:** Spec step 22 (structure + Tutorial quadrant): rewrite `docs/index.rst` into the four Diátaxis sections and write the tutorial (first provenance document → serialize → visualise), replacing `usage.rst`.

**Files:**
- Modify: `docs/index.rst`
- Create: `docs/tutorial/getting-started.md`
- Delete: `docs/usage.rst`

**Acceptance Criteria:**
- [ ] `docs/index.rst` has four content toctrees — Tutorial, How-to guides, Reference, Explanation — plus a Project section (readme, installation, contributing, authors, history). How-to/Reference/Explanation entries may point at pages created in Tasks 4–6; until then keep the existing `modules` entry under Reference so the build stays green.
- [ ] Tutorial is a single runnable narrative in MyST Markdown: build a document (entities, activity, agent, relations), print PROV-N, serialize to JSON file, deserialize it back, render a PNG with `prov.dot` — every code block copy-pasteable in order.
- [ ] `usage.rst` deleted and no dangling references (`sphinx-build` reports no broken toctree entries).

**Verify:** `uv run --group docs --extra rdf --extra xml sphinx-build -b html docs docs/_build/html` exits 0, warning count ≤ Task 2 baseline; manually run the tutorial's code blocks top-to-bottom in `python` (graphviz is installed locally) — no errors.

**Steps:**

- [ ] **Step 1: New `docs/index.rst` toctrees:**

```rst
Prov Python package's documentation
===================================

.. toctree::
   :maxdepth: 1
   :caption: Tutorial

   tutorial/getting-started

.. toctree::
   :maxdepth: 1
   :caption: Reference

   modules

.. toctree::
   :maxdepth: 1
   :caption: Project

   readme
   installation
   contributing
   authors
   history

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

(How-to and Explanation captions are added by Tasks 4/6 when their pages exist; `modules` is swapped for the reference pages in Task 5.)

- [ ] **Step 2: Write `docs/tutorial/getting-started.md`.** Skeleton (flesh out the prose; keep all code runnable):

````markdown
# Getting started

<!-- What you'll build: a small provenance document describing a file edit,
     saved as PROV-JSON and rendered as a PNG. -->

## Install

```bash
pip install prov[rdf,xml]
```

## Your first provenance document

<!-- Adapt the article example from usage.rst: ProvDocument(),
     set_default_namespace / add_namespace, document.entity('e2', ...) with
     PROV_TYPE / ex:* attributes, activity, wasGeneratedBy,
     wasAssociatedWith, agent — then document.get_provn() with expected
     output shown, exactly as usage.rst did. -->

## Save it and load it back

```python
document.serialize("article-prov.json")          # PROV-JSON by default
from prov.model import ProvDocument
loaded = ProvDocument.deserialize("article-prov.json")
assert loaded == document
```

## Visualise it

```python
from prov.dot import prov_to_dot
dot = prov_to_dot(document)
dot.write_png("article-prov.png")   # needs a local Graphviz install
```

<!-- Include the generated PNG via a checked-in image, or describe it;
     link to the graphics how-to (Task 4) for Graphviz installation. -->

## Bundles in two minutes

<!-- The bundle example from usage.rst, trimmed. -->

## Where next

<!-- Links: how-to guides per format, reference, PROV-DM primer. -->
````

- [ ] **Step 3:** `git rm docs/usage.rst`; grep the repo for `usage` references in docs (`grep -rn "usage" docs/*.rst README.rst`) and fix any.

- [ ] **Step 4:** Build docs, run tutorial code blocks manually, commit, PR, merge after CI + RTD preview green.

---

### Task 4: How-to guides — docs/howto (standard)

**Goal:** Spec step 22 (How-to quadrant): task-oriented guides per serialization format, graphics export (closes #141), CLI tools (closes #83), NetworkX interop.

**Files:**
- Create: `docs/howto/provjson.md`, `docs/howto/provxml.md`, `docs/howto/provo-rdf.md`, `docs/howto/provn.md`, `docs/howto/graphics.md`, `docs/howto/cli.md`, `docs/howto/networkx.md`
- Modify: `docs/index.rst` (add the How-to guides toctree)

**Acceptance Criteria:**
- [ ] One page per format: how to serialize + deserialize (`format=` argument, file-extension dispatch, `prov.read()` auto-detection), the extra required (`prov[rdf]` / `prov[xml]`), and format-specific notes (RDF: TriG for bundles; PROV-N: **write-only — no parser exists**, stated prominently).
- [ ] `graphics.md` covers `prov_to_dot()` → PNG/SVG/PDF, and the local Graphviz system-install requirement per OS (macOS `brew install graphviz`, Debian/Ubuntu `apt install graphviz`, Windows installer) — the exact confusion in #141.
- [ ] `cli.md` documents `prov-convert` and `prov-compare`: synopsis, options (read them from `src/prov/scripts/convert.py`/`compare.py` argparse definitions — do not invent), examples, exit codes — the reference #83 asks for.
- [ ] `networkx.md` covers `prov_to_graph()`/`graph_to_prov()` round-trip with a runnable example.
- [ ] PR description says `Closes #141` and `Closes #83`.

**Verify:** sphinx-build exits 0, warning count ≤ baseline; every code block executed manually once.

**Steps:**

- [ ] **Step 1:** Read `src/prov/scripts/convert.py`, `compare.py` (argparse), `src/prov/dot.py` (`prov_to_dot` signature), `src/prov/graph.py`, and `prov.read()` in `src/prov/__init__.py` so every documented flag/behaviour is real.
- [ ] **Step 2:** Write the seven pages. Each page: one task per H2 ("Serialize a document to X", "Read X from a file/string", "Common errors"), code blocks first, prose minimal (Diátaxis how-to style). For deserialization error cases, show the actual exception a bad file raises today.
- [ ] **Step 3:** Add to `docs/index.rst`:

```rst
.. toctree::
   :maxdepth: 1
   :caption: How-to guides

   howto/provjson
   howto/provxml
   howto/provo-rdf
   howto/provn
   howto/graphics
   howto/cli
   howto/networkx
```

- [ ] **Step 4:** Build, commit, PR (`Closes #141`, `Closes #83`), merge after CI + RTD preview green.

---

### Task 5: Reference reorganisation — docs/reference (standard)

**Goal:** Spec step 22 (Reference quadrant): replace the `modules.rst` autodoc dump with per-module API pages driven by the now-strict type hints.

**Files:**
- Create: `docs/reference/index.md`, `docs/reference/model.md`, `docs/reference/identifier.md`, `docs/reference/constants.md`, `docs/reference/serializers.md`, `docs/reference/graph.md`, `docs/reference/dot.md`
- Modify: `docs/index.rst` (Reference toctree swaps `modules` for `reference/index`)
- Delete: `docs/modules.rst`, `docs/prov.rst`, `docs/prov.serializers.rst`

**Acceptance Criteria:**
- [ ] Each page uses MyST + autodoc (```{eval-rst} blocks) with a short orientation paragraph before the class dump; `model.md` groups by concept: document/bundle first, then elements, then relations, then `NamespaceManager`/`Literal` — not alphabetical.
- [ ] All autodoc'd names render with type hints; no autodoc import errors in the build log.
- [ ] Old dump files deleted; no broken references.

**Verify:** sphinx-build exits 0, warning count ≤ baseline; `docs/_build/html/reference/model.html` exists and documents `ProvDocument`.

**Steps:**

- [ ] **Step 1:** Page template (adjust members per module):

````markdown
# prov.model

One paragraph: what lives here, entry points, link to the tutorial/primer.

```{eval-rst}
.. autoclass:: prov.model.ProvDocument
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvBundle
   :members:
   :show-inheritance:
```

## Elements

```{eval-rst}
.. autoclass:: prov.model.ProvEntity
   :members:
...
````

`constants.md` documents the vocabulary (`PROV_*` qualified names, `PROV_N_MAP`) with `automodule`-level docs; `serializers.md` covers `Serializer`, `Registry`, `get()`, `Error`/`DoNotExist` and points at the how-to pages per format.

- [ ] **Step 2:** `docs/reference/index.md` is a landing page listing the modules in a toctree. Swap `modules` → `reference/index` in `docs/index.rst`; `git rm docs/modules.rst docs/prov.rst docs/prov.serializers.rst`.
- [ ] **Step 3:** Build; fix any autodoc warnings introduced (missing members, bad cross-refs). Commit, PR, merge after CI + RTD preview green.

---

### Task 6: Explanation pages — docs/explanation (frontier)

**Goal:** Spec step 22 (Explanation quadrant): a PROV-DM primer mapping W3C concepts to the class model, and an honest account of unification/flattening semantics.

**Files:**
- Create: `docs/explanation/prov-dm.md`, `docs/explanation/unification-flattening.md`
- Modify: `docs/index.rst` (Explanation toctree)

**Acceptance Criteria:**
- [ ] `prov-dm.md`: what provenance is; the entity/activity/agent triangle; a table mapping all PROV-DM types and relations across the six components (Entities/Activities, Derivations, Agents/Responsibility, Bundles, Alternates, Collections) to `prov` classes and the `ProvBundle` factory methods; qualified names/namespaces explained via `Namespace`/`QualifiedName`; links to the W3C specs (https://www.w3.org/TR/prov-dm/, prov-o, prov-n).
- [ ] `unification-flattening.md`: what `flattened()` does (bundle contents pulled into the document) and what `unified()` does **today** (records sharing an identifier get their attributes unioned), stating plainly that this is simpler than W3C PROV-CONSTRAINTS merging and that 3.0 will reimplement it per spec (link ROADMAP.md and the Phase 3.5/4 roadmap steps). Include one worked example of each with input/output PROV-N.
- [ ] No behaviour claims that contradict the code — verify each claim against `model.py` (`flattened`, `unified`, `_unified_records`).

**Verify:** sphinx-build exits 0, warning count ≤ baseline.

**Steps:**

- [ ] **Step 1:** Read `ProvBundle.flattened()`, `unified()`, `_unified_records()` in `src/prov/model.py` and `src/prov/constants.py` (`PROV_BASE_CLS`, record-type tables) before writing a word.
- [ ] **Step 2:** Write the two pages per the AC. The component/class table can be generated from `constants.py` knowledge but is written as static Markdown.
- [ ] **Step 3:** Add the Explanation toctree to `docs/index.rst` (`explanation/prov-dm`, `explanation/unification-flattening`). Build, commit, PR, merge after CI + RTD preview green.

---

### Task 7: Docstring accuracy + napoleon pass, non-model modules — docs/docstrings-modules (standard)

**Goal:** Spec step 23 first half: for every public name outside `model.py`, verify the docstring against the strict type hints and actual behaviour (fix lies first), then normalise to Google-style (napoleon).

**Files:**
- Modify: `src/prov/__init__.py`, `src/prov/identifier.py`, `src/prov/constants.py`, `src/prov/graph.py`, `src/prov/dot.py`, `src/prov/serializers/__init__.py`, `src/prov/serializers/provjson.py`, `src/prov/serializers/provxml.py`, `src/prov/serializers/provrdf.py`, `src/prov/serializers/provn.py`, `src/prov/scripts/convert.py`, `src/prov/scripts/compare.py`

**Acceptance Criteria:**
- [ ] Every public function/class/method in these modules: parameter meanings, return value, raised exceptions, and side effects in the docstring match the code and the annotations (e.g. "returns X or None" only where the annotation says `| None`).
- [ ] All docstrings in these modules use Google style (`Args:` / `Returns:` / `Raises:`); no `:param:`/`:returns:` reST fields remain (`grep -rn ":param" <files>` → 0).
- [ ] Zero code changes — docstrings/comments only (`git diff` shows no executable-line edits).

**Verify:** `uv run pytest && uv run mypy src` green; sphinx-build exits 0 with warning count ≤ baseline; `grep -rn ":param\|:returns:\|:rtype:" src/prov --include="*.py" | grep -v model.py | grep -v tests` → empty.

**Steps:**

- [ ] **Step 1:** Module by module, for each public name: read the implementation, compare against the docstring, fix factual errors first (commit these as they're found — they are review-relevant), e.g. stale claims about dateutil-lenient parsing, wrong exception names, undocumented `format=` dispatch in `serialize`/`deserialize`.
- [ ] **Step 2:** Convert style. Target shape:

```python
def get(format_name: str) -> type[Serializer]:
    """Return the serializer class registered for a format.

    Args:
        format_name: Registry key, e.g. ``"json"``, ``"xml"``, ``"rdf"``,
            ``"provn"``.

    Returns:
        The :class:`Serializer` subclass for the format.

    Raises:
        DoNotExist: If no serializer is registered under ``format_name``.
    """
```

- [ ] **Step 3:** Rebuild docs and eyeball the reference pages (Task 5) for these modules. Commit per module or per small group, PR, merge after CI green.

---

### Task 8: Docstring accuracy + napoleon pass, model.py — docs/docstrings-model (frontier)

**Goal:** Spec step 23 second half: the same accuracy-first, style-second pass over `model.py`'s ~90 public names — the core API where stale prose does the most damage.

**Files:**
- Modify: `src/prov/model.py` (docstrings only)

**Acceptance Criteria:**
- [ ] Every public class and method in `model.py` (all `Prov*` classes, `ProvBundle`/`ProvDocument` and their factory methods, `NamespaceManager`, `Literal`, module-level functions) verified against behaviour and annotations; factual fixes listed in the PR description (they are the review payload).
- [ ] Google style throughout; `grep -c ":param" src/prov/model.py` → 0.
- [ ] Zero executable-code changes; must land **before** Task 16's split (so the split moves the corrected text).

**Verify:** `uv run pytest && uv run mypy src` green; sphinx-build warning count ≤ baseline; `git diff master -- src/prov/model.py` touches only strings/comments (spot-check with `git diff -w`).

**Steps:**

- [ ] **Step 1:** Work through `model.py` top-to-bottom in its section order (datatype helpers/Literal → exceptions → ProvRecord → elements → relations → NamespaceManager → ProvBundle → ProvDocument → `sorted_attributes`). For every docstring: check parameter prose against `FORMAL_ATTRIBUTES` semantics, check documented exceptions actually raised, check "returns" against annotations. Particular suspects (typing changed under them in Phase 2): `parse_xsd_datetime`, `ProvBundle.add_record`/`new_record` attribute-pair handling, `serialize`/`deserialize` format dispatch, `unified`/`flattened`, `NamespaceManager.get_registered_namespaces`.
- [ ] **Step 2:** Style conversion to Google style, same shape as Task 7.
- [ ] **Step 3:** Rebuild docs; verify `reference/model.html` renders the new text. Commit in a few reviewable chunks (elements/relations/bundle), PR, merge after CI green.

---

### Task 9: Test methodology design doc — tests/redesign-spec (frontier)

**Goal:** Spec step 24 first deliverable: a short design doc for the pytest-native test suite, deliberately not constrained by the legacy structure — it is the authority Tasks 10–12 execute against.

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-test-suite-redesign.md` (use the actual date)

**Acceptance Criteria:**
- [ ] Assesses each inherited pattern on its merits with a keep/replace verdict + reason: `RoundTripTestCase`/`utility.py`; the `attributes.py`/`statements.py`/`qnames.py` mixins; per-format test-module duplication (`test_json.py`/`test_xml.py`/`test_rdf.py`); the fixture-directory round-trips (`tests/json/`, `xml/`, `rdf/`, `unification/`); bare document-equality assertions.
- [ ] Re-justifies **each of the 17 `expectedFailure` markers** (all in `test_rdf.py`: 14 scruffy-statement + 3 multi-value-attribute RDF round-trip cases): for each, why it fails, and either a tracking issue reference (file one if none exists) or a decision to fix/retire — an expected failure with no tracking issue is a silent bug.
- [ ] Specifies the target design: parametrized fixtures over the document×format matrix (e.g. a `format` fixture spanning json/xml/rdf and provn-serialize-only, applied to shared statement/attribute/qname test functions), `tmp_path` for file I/O, a ProvDocument equality-diff helper (`pytest_assertrepr_compare` in `conftest.py`) so failures show *which records differ*, and how per-format xfails attach to parametrized cases (`pytest.param(..., marks=pytest.mark.xfail(reason=..., raises=...))`).
- [ ] Defines the migration order (JSON as pattern-setter, then XML+RDF, then the rest), the parity procedure (see Tasks 10–12), and any tests explicitly retired or merged, each with a stated reason.
- [ ] States that function-local imports in test modules are normalised to module level during the rewrite.

**Verify:** doc exists, covers every bullet above; PR merged (maintainer review of the design happens on this PR, before any migration starts).

**Steps:**

- [ ] **Step 1:** Read all of `src/prov/tests/` (structure, not just names): `utility.py`, the three mixin modules, the three format modules, `test_model.py`, `examples.py`. Run `uv run pytest --collect-only -q | tail -3` and record the exact collected count in the doc as the parity baseline.
- [ ] **Step 2:** For the 17 xfails: run each without the marker (`uv run pytest "src/prov/tests/test_rdf.py::AllTests::test_scruffy_end_1" --runxfail` style) to capture the real failure; search the issue tracker for existing coverage (`gh issue list --search "rdf roundtrip"`); write the per-marker table.
- [ ] **Step 3:** Write the doc with concrete code sketches for the target conftest (fixtures + assertrepr hook) — Task 10 implements them.
- [ ] **Step 4:** Commit, PR, merge after maintainer-visible review (this PR is the design checkpoint; do not start Task 10 until it is merged).

---

### Task 10: Pattern-setter migration — shared pytest matrix + JSON — tests/pytest-json (frontier)

**Goal:** Spec step 24 second deliverable: implement the design doc's shared pytest infrastructure and migrate the JSON format tests to it, proving collected-test parity.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `src/prov/tests/conftest.py` (fixtures + ProvDocument diff hook, per design doc)
- Modify: `src/prov/tests/test_json.py` (rewritten pytest-native)
- Modify: `CLAUDE.md` (Tests section: describe the emerging pytest-native structure)
- Possibly create: shared parametrized statement/attribute/qname test modules per the design doc (naming per the doc)

**Acceptance Criteria:**
- [ ] Baseline captured BEFORE any change: `uv run pytest --collect-only -q src/prov/tests/test_json.py | tail -1` and the full-suite count, saved into the PR description.
- [ ] After migration: full-suite collected count and pass/xfail totals are identical to baseline, except for deltas the design doc explicitly authorises (each named in the PR description with the doc's reason).
- [ ] JSON tests use the new fixtures (`tmp_path`, parametrization); no `RoundTripTestCase` usage remains in `test_json.py`; assertion failures on document equality show a record-level diff (demonstrate by temporarily breaking one assertion locally and pasting the output in the PR).
- [ ] Coverage stays ≥ 97 (`uv run coverage run -m pytest && uv run coverage report`) — the ratchet margin is thin.

**Verify:** `uv run pytest --collect-only -q | tail -1` before == after (± authorised deltas); `uv run pytest` → same pass/xfail totals as baseline.

**Steps:**

- [ ] **Step 1:** Capture the before evidence (labelled `baseline`): full-suite `--collect-only` count + `pytest` summary line.
- [ ] **Step 2:** Implement `conftest.py` exactly as sketched in the design doc — fixtures for example documents (wrapping `examples.py`), a serializer round-trip helper parametrized by format (only json enabled this task), and `pytest_assertrepr_compare` for `ProvDocument`.
- [ ] **Step 3:** Rewrite `test_json.py` against it; module-level imports only.
- [ ] **Step 4:** Capture the after evidence (labelled `migrated`): same two commands; diff against baseline; reconcile every delta against the design doc.
- [ ] **Step 5:** Update CLAUDE.md's Tests section (old text describes the unittest mixins as current state — mark them legacy-during-migration). Commit, PR with both evidence blocks, merge after CI green.

```json
Evidence axes for close: baseline vs migrated collect/pass counts.
```

---

### Task 11: Migrate XML + RDF test modules — tests/pytest-xml-rdf (standard)

**Goal:** Extend the pattern to `test_xml.py` and `test_rdf.py`, converting the 17 `expectedFailure` wrappers to parametrized `pytest.mark.xfail` with reasons/issue links per the design doc's table.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Modify: `src/prov/tests/test_xml.py`, `src/prov/tests/test_rdf.py`, `src/prov/tests/conftest.py` (enable xml/rdf in the format matrix)

**Acceptance Criteria:**
- [ ] Baseline (before) and migrated (after) `--collect-only` counts and pass/xfail totals captured in the PR; identical except design-doc-authorised deltas.
- [ ] Every xfail carries `reason=` with the failure cause and tracking-issue reference from the design doc's table; `strict` left False only where the doc says the failure is flaky, otherwise `strict=True` so silent fixes surface.
- [ ] The XML fixture-directory tests (`tests/xml/*.xml`) and RDF ones (`tests/rdf/`) still run, via `tmp_path`-based rewrites where they wrote temp files.
- [ ] Coverage ≥ 97; xfail count in the suite summary equals the design doc's post-migration expectation (17 unless the doc retired/fixed some).

**Verify:** `uv run pytest` summary: same totals as pre-task baseline (± authorised deltas); `grep -c "expectedFailure" src/prov/tests/test_rdf.py` → 0.

**Steps:**

- [ ] **Step 1:** Capture baseline evidence (labelled `baseline`).
- [ ] **Step 2:** Enable `"xml"` and `"rdf"` in the conftest format matrix; migrate `test_xml.py` then `test_rdf.py` following `test_json.py`'s shape; convert xfails to `pytest.param(..., marks=pytest.mark.xfail(reason="...", strict=...))` or function-level markers per the doc.
- [ ] **Step 3:** Capture migrated evidence, reconcile deltas, update CLAUDE.md if the structure description shifts. Commit, PR with evidence, merge after CI green.

```json
Evidence axes for close: baseline vs migrated collect/pass/xfail counts.
```

---

### Task 12: Migrate remaining test modules, retire legacy scaffolding — tests/pytest-rest (standard)

**Goal:** Finish spec step 24: migrate `test_model.py`, `test_extras.py`, `test_dot.py`, `test_graphs.py`, `test_identifier.py`, `test_read.py`, `test_scripts.py`, `test_cli_smoke.py`, `test_public_api.py` to pytest idioms and retire `utility.py` + the mixin modules per the design doc.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Modify: the nine test modules above; `src/prov/tests/conftest.py`
- Delete (per design doc): `src/prov/tests/utility.py`, and `attributes.py`/`statements.py`/`qnames.py` once their content lives in the shared parametrized modules
- Modify: `pyproject.toml` (`python_classes = []` comment likely stale once mixins are gone; ruff per-file-ignores for `attributes.py`/`statements.py`/`test_extras.py` F403/F405 removed as those files go), `CLAUDE.md` (Tests section rewritten to describe the final structure)

**Acceptance Criteria:**
- [ ] Baseline/migrated evidence pair captured as in Tasks 10–11; totals identical except authorised deltas; every retired/merged test named in the PR with the design doc's reason.
- [ ] No `unittest` imports remain under `src/prov/tests/` (`grep -rn "import unittest" src/prov/tests/` → 0); no function-local imports without a stated reason.
- [ ] Coverage ≥ 97; `uv run mypy src` still green (tests excluded, but config edits can break it).
- [ ] CLAUDE.md Tests section describes the new structure (conftest fixtures, parametrized format matrix, fixture dirs) and drops the mixin description.

**Verify:** `uv run pytest` totals == baseline (± authorised deltas); `grep -rn "import unittest" src/prov/tests/` → empty.

**Steps:**

- [ ] **Step 1:** Capture baseline evidence (labelled `baseline`).
- [ ] **Step 2:** Migrate module-by-module in the design doc's order, committing per module; `test_public_api.py` moves last and changes least (it is the freeze guard — keep its assertions byte-for-byte where possible).
- [ ] **Step 3:** Delete retired scaffolding; update `pyproject.toml` per-file-ignores and the `python_classes` comment; rewrite CLAUDE.md Tests section.
- [ ] **Step 4:** Capture migrated evidence, reconcile, PR with evidence, merge after CI green.

```json
Evidence axes for close: baseline vs migrated collect/pass/xfail counts.
```

---

### Task 13: Property-based round-trip tests with Hypothesis — tests/hypothesis (frontier)

**Goal:** Spec step 24b first item: a Hypothesis strategy generating random valid PROV documents, round-tripped across all deserializable formats.

**Files:**
- Create: `src/prov/tests/strategies.py`, `src/prov/tests/test_property_roundtrip.py`
- Modify: `pyproject.toml` (add `hypothesis` to the dev group), `src/prov/tests/conftest.py` (Hypothesis CI profile), `CLAUDE.md` (mention the property tests)

**Acceptance Criteria:**
- [ ] Strategy generates documents with: multiple namespaces, entities/activities/agents with mixed attribute types (str incl. non-ASCII, int, float, bool, datetime, QualifiedName), the full relation set among generated ids, and optionally one bundle.
- [ ] Property: for each of json/xml/rdf, `deserialize(serialize(doc)) == doc` (provn excluded — write-only). Known-lossy constructs identified in the Task 9 xfail table are excluded from generation, each exclusion commented with the issue link.
- [ ] CI profile: `max_examples` modest (≤ 50), `deadline=None`, `derandomize=True` so CI is deterministic; local default profile stays exploratory.
- [ ] Suite time increase < ~60s on the CI matrix.

**Verify:** `uv run pytest src/prov/tests/test_property_roundtrip.py -v` passes; full suite green; coverage ≥ 97.

**Steps:**

- [ ] **Step 1:** `uv add --group dev hypothesis`.
- [ ] **Step 2:** Implement `strategies.py`. Starting shape (refine as failures teach):

```python
"""Hypothesis strategies generating valid PROV documents."""
import string
from datetime import datetime, timezone

from hypothesis import strategies as st

from prov.model import ProvDocument

EX_URI = "http://example.org/"

local_part = st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=8)
qnames = local_part.map(lambda s: f"ex:{s}")

attr_values = st.one_of(
    st.text(max_size=30),
    st.integers(min_value=-(2**31), max_value=2**31),
    st.booleans(),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.datetimes(
        min_value=datetime(1970, 1, 1), max_value=datetime(2100, 1, 1)
    ).map(lambda dt: dt.replace(tzinfo=timezone.utc)),
)


@st.composite
def prov_documents(draw: st.DrawFn) -> ProvDocument:
    doc = ProvDocument()
    doc.add_namespace("ex", EX_URI)
    entity_ids = draw(st.lists(qnames, min_size=1, max_size=4, unique=True))
    for eid in entity_ids:
        attrs = draw(st.dictionaries(qnames.map(lambda s: f"ex:attr_{s[3:]}"), attr_values, max_size=3))
        doc.entity(eid, attrs or None)
    # ... activities, agents, then relations drawn over the generated ids,
    # then optionally one bundle with its own records (same pattern).
    return doc
```

- [ ] **Step 3:** `test_property_roundtrip.py` parametrized over formats via the Task 10 matrix; register the `ci` profile in `conftest.py` and select it via `HYPOTHESIS_PROFILE=ci` env in `CI.yml`'s test job (add the env line).
- [ ] **Step 4:** Run 500 examples locally once (`--hypothesis-profile default -x`) to shake out strategy bugs before pinning the CI profile. Commit, PR, merge after CI green. Any genuine round-trip bug found: capture as a regular xfail test + GitHub issue — do **not** fix serializer behaviour in this PR (2.x freeze; triage to 3.0 unless clearly non-breaking).

---

### Task 14: Malformed-input corpus — tests/malformed-corpus (standard)

**Goal:** Spec step 24b second item: characterization tests for every deserializer's error paths, which are nearly untested today.

**Files:**
- Create: `src/prov/tests/malformed/` fixture dir + files; `src/prov/tests/test_malformed.py`
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]` add `"malformed/*"` under `"prov.tests"`)

**Acceptance Criteria:**
- [ ] Corpus covers per format — JSON: syntactically invalid, top-level list, record value of wrong shape (`{"entity": "notadict"}`), bad prefix map, empty file; XML: not well-formed, well-formed but wrong root element, empty; RDF: unparsable Turtle, valid-Turtle-wrong-vocabulary, empty; plus `prov.read()` on garbage and `deserialize(format="nope")`.
- [ ] Each test asserts the **current** exception type (characterization — 2.x freeze forbids "improving" the raised exceptions here); any raw `KeyError`/`TypeError` surfaced gets a `# 3.0 triage:` comment and one consolidated GitHub issue listing them for the Phase 4 list.
- [ ] Coverage of the deserializer error branches visibly rises (`uv run coverage report -m` before/after for `serializers/*` pasted in the PR).

**Verify:** `uv run pytest src/prov/tests/test_malformed.py -v` green; full suite green; coverage ≥ 97.

**Steps:**

- [ ] **Step 1:** Write the corpus files (a few lines each) and a parametrized test:

```python
import pytest
from prov.model import ProvDocument

MALFORMED = Path(__file__).parent / "malformed"

@pytest.mark.parametrize(
    ("filename", "fmt", "expected_exc"),
    [
        pytest.param("not_json.json", "json", <observed>, id="json-syntax"),
        # ... one row per corpus file; fill expected_exc from observed behaviour
    ],
)
def test_malformed_input_raises(filename, fmt, expected_exc):
    with (MALFORMED / filename).open() as f, pytest.raises(expected_exc):
        ProvDocument.deserialize(f, format=fmt)
```

Determine each `<observed>` by running the case interactively first; the test then locks it in.

- [ ] **Step 2:** Add the package-data glob; `uv build` and check the sdist contains the corpus (`tar -tf dist/*.tar.gz | grep malformed`).
- [ ] **Step 3:** File the consolidated "deserializer error types to clean up in 3.0" issue if any raw exceptions were found. Commit, PR, merge after CI green.

---

### Task 15: Registry clean degradation + minimal-install CI job — ci/minimal-install (standard)

**Goal:** Spec step 24b third item: without the rdf/xml extras, `import prov` and JSON/PROV-N work, and asking for rdf/xml raises an informative `DoNotExist` naming the extra — instead of today's `ModuleNotFoundError` from `Registry.load_serializers()` (which currently imports all four serializers unconditionally, so a missing `rdflib` breaks even `get("json")`). A CI job proves it.

**Files:**
- Modify: `src/prov/serializers/__init__.py`
- Create: `src/prov/tests/test_minimal_install.py`
- Modify: `.github/workflows/CI.yml` (new `minimal-install` job)
- Modify: `HISTORY.rst` (unreleased-note: degradation fix; new exception type in previously-crashing configs)

**Acceptance Criteria:**
- [ ] With no extras installed: `import prov`, `import prov.model` succeed; `prov.serializers.get("json")` works; JSON round-trip works; `get("rdf")`/`get("xml")` raise `DoNotExist` whose message names the missing extra (`prov[rdf]` / `prov[xml]`); `prov.read()` auto-detection skips unavailable serializers instead of crashing.
- [ ] With extras installed (the normal matrix): behaviour unchanged — all four formats register; full suite totals unchanged.
- [ ] New CI job `minimal-install` syncs without extras and runs `test_minimal_install.py`; it is a required-style normal job (not `continue-on-error`).

**Verify:** `uv run pytest` green (extras env); then locally `uv run --no-extra rdf --no-extra xml --isolated pytest src/prov/tests/test_minimal_install.py` equivalent via a temp venv (`uv venv /tmp/minv && uv pip install -e . --python /tmp/minv && ...`) or simply push and watch the new CI job pass.

**Steps:**

- [ ] **Step 1: Rewrite `Registry.load_serializers()` and `get()`:**

```python
class Registry:
    """Registry of serializers."""

    serializers: ClassVar[dict[str, type[Serializer]] | None] = None
    """Property caching all available serializers in a dict."""

    @staticmethod
    def load_serializers() -> None:
        """Load all serializers whose dependencies are installed."""
        from prov.serializers.provjson import ProvJSONSerializer
        from prov.serializers.provn import ProvNSerializer

        serializers: dict[str, type[Serializer]] = {
            "json": ProvJSONSerializer,
            "provn": ProvNSerializer,
        }
        try:
            from prov.serializers.provrdf import ProvRDFSerializer
        except ImportError:  # rdflib not installed (the "rdf" extra)
            pass
        else:
            serializers["rdf"] = ProvRDFSerializer
        try:
            from prov.serializers.provxml import ProvXMLSerializer
        except ImportError:  # lxml not installed (the "xml" extra)
            pass
        else:
            serializers["xml"] = ProvXMLSerializer
        Registry.serializers = serializers


#: Formats provided by optional extras, for error messages in :func:`get`.
_OPTIONAL_FORMAT_EXTRAS = {"rdf": "rdf", "xml": "xml"}


def get(format_name: str) -> type[Serializer]:
    """Return the serializer class registered for a format. ..."""
    if Registry.serializers is None:
        Registry.load_serializers()
    serializers = Registry.serializers
    assert serializers is not None  # load_serializers() always populates it
    try:
        return serializers[format_name]
    except KeyError as e:
        extra = _OPTIONAL_FORMAT_EXTRAS.get(format_name)
        if extra is not None:
            raise DoNotExist(
                f'Serializer for the "{format_name}" format requires the '
                f'"{extra}" extra; install it with: pip install "prov[{extra}]"'
            ) from e
        raise DoNotExist(
            f'No serializer available for the format "{format_name}"'
        ) from e
```

Check `prov.read()` in `src/prov/__init__.py`: it iterates registered deserializers, so with the dict now only containing available ones it degrades naturally — verify, don't assume.

- [ ] **Step 2: Write `src/prov/tests/test_minimal_install.py`:**

```python
"""Degradation behaviour when optional extras are missing.

Run by the `minimal-install` CI job (no rdf/xml extras). Under the normal
matrix (extras installed) the skipif-guarded tests are skipped and the
availability tests assert all formats register.
"""
import importlib.util

import pytest

import prov.serializers
from prov.model import ProvDocument

HAS_RDFLIB = importlib.util.find_spec("rdflib") is not None
HAS_LXML = importlib.util.find_spec("lxml") is not None


def test_core_import_and_json_roundtrip() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")
    assert ProvDocument.deserialize(content=doc.serialize(format="json")) == doc


@pytest.mark.skipif(HAS_RDFLIB, reason="only meaningful without rdflib")
def test_rdf_unavailable_raises_informative_error() -> None:
    with pytest.raises(prov.serializers.DoNotExist, match=r"prov\[rdf\]"):
        prov.serializers.get("rdf")


@pytest.mark.skipif(HAS_LXML, reason="only meaningful without lxml")
def test_xml_unavailable_raises_informative_error() -> None:
    with pytest.raises(prov.serializers.DoNotExist, match=r"prov\[xml\]"):
        prov.serializers.get("xml")


@pytest.mark.skipif(not (HAS_RDFLIB and HAS_LXML), reason="extras installed case")
def test_all_formats_available_with_extras() -> None:
    for fmt in ("json", "provn", "rdf", "xml"):
        assert prov.serializers.get(fmt) is not None
```

(Adapt `deserialize(content=...)` to the real signature — check it.)

- [ ] **Step 3: Add the CI job** (mirror the `lint` job's checkout/setup-uv boilerplate in `CI.yml`):

```yaml
  minimal-install:
    name: minimal install (no extras)
    runs-on: ubuntu-latest
    steps:
      # same checkout + astral-sh/setup-uv steps as the lint job
      - name: Sync without extras
        run: uv sync
      - name: Degradation tests
        run: uv run pytest src/prov/tests/test_minimal_install.py -v
```

- [ ] **Step 4:** HISTORY.rst unreleased entry; commit, PR, merge after CI green (including the new job).

---

### Task 16: Split model.py into a package — refactor/model-package (frontier)

**Goal:** Spec step 25: `src/prov/model.py` (2,843 lines) becomes `src/prov/model/` — `records.py`, `namespaces.py`, `bundle.py`, with `__init__.py` re-exporting everything at historic names. Pure moves; zero behaviour edits.

**Files:**
- Delete: `src/prov/model.py`
- Create: `src/prov/model/__init__.py`, `src/prov/model/records.py`, `src/prov/model/namespaces.py`, `src/prov/model/bundle.py`
- Modify: `pyproject.toml` (ruff per-file-ignores key `src/prov/model.py` → `src/prov/model/__init__.py`), `CLAUDE.md` (architecture section)

**Acceptance Criteria:**
- [ ] Public-name parity proven: `python -c "import prov.model; print('\n'.join(sorted(n for n in dir(prov.model) if not n.startswith('_'))))"` captured on master BEFORE the split and on the branch AFTER — `diff` empty.
- [ ] Content split: `records.py` = datatype helpers (`parse_xsd_datetime`, `parse_boolean`, `parse_xsd_types`, `first`, `encoding_provn_value`, …), `Literal`, exceptions (`ProvException`, `ProvWarning`, …), `ProvRecord`/`ProvElement`/`ProvRelation` and all concrete element/relation classes, `PROV_REC_CLS`; `namespaces.py` = `NamespaceManager`; `bundle.py` = `ProvBundle`, `ProvDocument`, `sorted_attributes`. `__init__.py` re-exports all of these plus the existing `from prov.constants import *` surface (today's `model.py` star-imports constants; `prov.model.PROV_TYPE` etc. must keep working).
- [ ] No executable-logic diffs: the bodies moved verbatim (verify by re-running the full suite + `git diff --stat` shows only the four new files and deletions).
- [ ] Full suite, mypy strict, ruff, and the public-API smoke test all green; coverage ≥ 97.
- [ ] Circular-import handling documented in the PR: `bundle.py` imports from `records.py`/`namespaces.py`; `records.py` refers to `ProvBundle` only under `TYPE_CHECKING`.
- [ ] PR description notes the pickle nuance: classes' `__module__` becomes e.g. `prov.model.records`; old pickles still load (module attribute lookup goes through the re-exports), new pickles won't load in prov < 2.4.0 (cross-version pickling was never promised).

**Verify:** `diff /tmp/model-names-before.txt /tmp/model-names-after.txt` → empty; `uv run pytest && uv run mypy src && uv run ruff check src/` all green; `uv run pytest src/prov/tests/test_public_api.py -v` passes.

**Steps:**

- [ ] **Step 1:** On master, capture `/tmp/model-names-before.txt` with the command above.
- [ ] **Step 2:** Create the package; move sections verbatim following model.py's own section comments (lines 46–260 helpers/Literal/exceptions → `records.py` top; 261–1130 record classes + `PROV_REC_CLS` → `records.py`; 1132–1377 `NamespaceManager` → `namespaces.py`; 1378–2843 → `bundle.py`). Each module gets only the imports it needs; `from __future__`/typing imports replicated as required.
- [ ] **Step 3:** Write `__init__.py`: explicit `from prov.model.records import X as X, ...` blocks for every public name (build the list from `/tmp/model-names-before.txt`), plus `from prov.constants import *` with the same `F403`/`F405` per-file-ignore moved to the new path. Also re-export any historically-reachable module-level names that appear in the before-list even if they look internal (e.g. `logger` if present) — the freeze covers what was importable, and the smoke test will tell you.
- [ ] **Step 4:** Capture `/tmp/model-names-after.txt`, diff, fix until empty. Run the full gate battery. Update CLAUDE.md's architecture section ("Core object model (`src/prov/model/`)…").
- [ ] **Step 5:** Commit (single commit is fine — reviewers diff against the deleted file), PR, merge after CI green.

---

### Task 17: Deprecation warnings + "Upgrading to 3.0" signposting — chore/deprecations-3.0 (standard)

**Goal:** Spec step 26: 2.4.0 signposts everything 3.0 changes — runtime warnings where feasible, a docs page for the rest.

**Files:**
- Modify: `src/prov/dot.py`, `src/prov/graph.py` (module-level `DeprecationWarning`), `src/prov/model/bundle.py` (`FutureWarning` in `unified()`)
- Create: `docs/upgrading-3.0.md`; `src/prov/tests/test_deprecations.py`
- Modify: `docs/index.rst` (Project toctree), `pyproject.toml` (pytest `filterwarnings`), `ROADMAP.md`, `HISTORY.rst`

**Acceptance Criteria:**
- [ ] `import prov.dot` / `import prov.graph` emit one `DeprecationWarning` naming the future extra (`prov[dot]` / `prov[graph]`, per spec step 36c) and linking ROADMAP.md; hidden by default for end users (DeprecationWarning semantics), visible under `-W error::DeprecationWarning`.
- [ ] `ProvBundle.unified()` / `ProvDocument.unified()` emit a `FutureWarning` that 3.0 reimplements unification per W3C PROV-CONSTRAINTS (records with conflicting formal attributes will raise instead of silently merging).
- [ ] `docs/upgrading-3.0.md` tables every planned 3.0 change with "what to do": the extras moves + dateutil drop (spec 36c), the behaviour-bug fixes #89/#34/#77/#168 (spec 36), the unification rework (36b), removal of 2.4.0-deprecated names (37).
- [ ] `test_deprecations.py` asserts each warning with `pytest.warns`; suite output stays clean via `filterwarnings` ignores scoped to the exact messages.
- [ ] No other behaviour changes.

**Verify:** `uv run pytest src/prov/tests/test_deprecations.py -v` green; `uv run pytest` green with no warning spam in the summary; `python -W error::DeprecationWarning -c "import prov.dot"` raises.

**Steps:**

- [ ] **Step 1:** In `src/prov/dot.py`, after the imports:

```python
warnings.warn(
    "In prov 3.0, graphical export (prov.dot) will require the optional "
    '"dot" extra; install "prov[dot]" to keep using it after upgrading. '
    "See https://github.com/trungdong/prov/blob/master/ROADMAP.md",
    DeprecationWarning,
    stacklevel=2,
)
```

Same in `graph.py` with `"graph"`/`prov[graph]`. Add `import warnings` if absent.

- [ ] **Step 2:** In `ProvBundle.unified()` (and `ProvDocument.unified()` if it does not delegate — check):

```python
warnings.warn(
    "prov 3.0 will change unified() to merge records per the W3C "
    "PROV-CONSTRAINTS rules; records sharing an identifier but having "
    "conflicting formal attributes will then raise an error instead of "
    "having their attributes silently unioned. See "
    "https://github.com/trungdong/prov/blob/master/ROADMAP.md",
    FutureWarning,
    stacklevel=2,
)
```

- [ ] **Step 3:** pytest config:

```toml
filterwarnings = [
    "ignore:In prov 3.0:DeprecationWarning",
    "ignore:prov 3.0 will change unified:FutureWarning",
]
```

- [ ] **Step 4:** `test_deprecations.py` with `pytest.warns(DeprecationWarning, match="prov\\[dot\\]")` around a fresh `importlib.reload(prov.dot)` (module-level warnings fire once per import — reload to observe) and `pytest.warns(FutureWarning, match="PROV-CONSTRAINTS")` around `doc.unified()`.
- [ ] **Step 5:** Write `docs/upgrading-3.0.md`, add to the Project toctree; update ROADMAP.md (2.4.0 row: "signposting release" note) and HISTORY.rst unreleased entry. Commit, PR, merge after CI green.

---

### Task 18: Cut release 2.4.0 — release/2.4.0 (standard + maintainer)

**Goal:** Spec step 27: release everything above as 2.4.0 via the established gated pipeline.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Modify: `src/prov/__init__.py` (`__version__ = "2.4.0"`), `HISTORY.rst`, `ROADMAP.md`

**Acceptance Criteria:**
- [ ] Release PR merged: version bump, HISTORY.rst 2.4.0 entry (headline items bolded: docs overhaul, pytest-native suite, model package split with unchanged imports, 3.0 deprecation signposting, minimal-install degradation), ROADMAP.md 2.4.0 rows marked released.
- [ ] Publishing happened ONLY after explicit maintainer go-ahead via AskUserQuestion (the Phase 2 gate pattern).
- [ ] TestPyPI dry-run verified before the real publish; GitHub release tagged `2.4.0` (no `v` prefix) targeting master with the HISTORY entry as notes; PyPI publish succeeded; wheel spot-checked (`py.typed` present, `prov/model/` package present, `tests/malformed/` in sdist); milestone #3 (2.4.0) closed.

**Verify:** `pip index versions prov` (or PyPI page) shows 2.4.0; `python -m zipfile -l <downloaded wheel> | grep -E "py.typed|model/__init__"` shows both.

**Steps:**

- [ ] **Step 1:** Branch `release/2.4.0`; bump `__version__`; write the HISTORY.rst entry referencing PR numbers; update ROADMAP.md. Full gate battery green.
- [ ] **Step 2:** Open the release PR, merge after CI green.
- [ ] **Step 3: STOP — maintainer confirmation required before publishing.** AskUserQuestion, exactly as Phase 2's T16. Then: TestPyPI dry-run via `release.yml`'s `workflow_dispatch`; verify the upload; create GitHub release `2.4.0`; the `release published` trigger publishes to PyPI; verify wheel/sdist contents; close milestone #3.
- [ ] **Step 4:** Post-release: update the pinned tracking issue; record Phase 3 completion + loose ends in memory.

```json
Evidence axes for close: pre-publish (TestPyPI dry-run verified) vs published (PyPI 2.4.0 live, wheel verified).
```

---

## Dependency graph

```
T1 ─────────────────────────────┐
T2 → T3 → {T4, T5, T6}          │
T2 → T7 → T8 ───────────────────┤→ T16 → T17 → T18
T9 → T10 → T11 → T12 → {T13,T14}│
          T10 → T15 ────────────┘
(T16 also blocked by T12; T18 blocked by everything)
```

Sequential execution order: T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18.

## Self-review notes

- Spec coverage: step 21 → T2; step 22 → T3–T6; step 23 → T7–T8; step 24 → T9–T12; step 24b → T13–T15; step 25 → T16; step 26 → T17; step 27 → T18. Loose ends → T1 (Makefile, CLAUDE.md), T2 (requirements.txt), T9–T12 (local imports).
- The 2.x freeze exceptions in this plan are exactly the spec-sanctioned ones: warnings (step 26) and registry degradation (step 24b), both changelog-disclosed.
- Names used consistently: `conftest.py` fixtures introduced in T10 are consumed in T11–T14; `records.py`/`namespaces.py`/`bundle.py` appear only in T16–T17 (T17 edits `bundle.py` post-split — T17 is blocked by T16).

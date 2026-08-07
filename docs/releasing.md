# Releasing

How a `prov` release is cut, from a green `master` to PyPI and conda-forge. Written after
the 3.1.0 release and validated against it; the 3.0.0 release followed the same sequence.

Substitute the version being released for `X.Y.Z` throughout.

## What publishes what

Two things are worth knowing before you start, because neither is obvious from the outside:

- **The GitHub release is the trigger.** `.github/workflows/release.yml` runs its
  `publish-pypi` job on `release: types: [published]`. There is no separate "publish"
  button and no manual `twine upload` — creating the GitHub release *is* how a version
  reaches PyPI.
- **`workflow_dispatch` only ever reaches TestPyPI.** The same workflow's
  `publish-testpypi` job is gated on `github.event_name == 'workflow_dispatch'`, so a
  manual run is always a dry run. It cannot publish to PyPI by accident.

Both publish jobs use PyPI Trusted Publishing through the `testpypi` and `pypi` GitHub
environments — there are no API tokens to rotate.

## 1. Pre-flight

Run on the commit you intend to release, before stamping anything.

```bash
# Full interpreter matrix, matching the CI matrix
for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do
    uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest -q || break
done

uv run mypy src
uv run ruff check src/
uv run ruff format --check src/
```

The suite must match the invariant recorded in `CLAUDE.md` exactly — pass count, skip
count, and zero xfails. A deviation is a regression, not a new baseline.

Check the build, including any package data the release depends on at runtime:

```bash
uv build
unzip -l dist/prov-*.whl | grep -E "py.typed|prov-jsonld-context"
```

`mypy` cannot run under PyPy. If the matrix loop left `.venv` on `pypy3.11`, `uv run mypy`
fails with "Running mypy on PyPy is not supported yet" — that is the interpreter, not a
type error. Re-run it pinned:
`uv run --python 3.13 --extra rdf --extra xml --extra dot --extra graph mypy src`.

## 2. Stamp the release

Four files, in one commit:

| File | Change |
|---|---|
| `src/prov/__init__.py` | `__version__ = "X.Y.Z"` — the single source of truth; `pyproject.toml` reads it via `dynamic = ["version"]` and `docs/conf.py` imports it, so nothing else carries the number |
| `HISTORY.md` | Date the heading: `## X.Y.Z (YYYY-MM-DD)`, matching the style of the entries below it |
| `ROADMAP.md` | Stamp the row: `**X.Y.Z** *(released YYYY-MM-DD)*` |
| `docs/reference/conformance.md` | Per-release revisit — the page states it is "revisited at every release"; verify its claims still hold and update the "last revised for the X.Y.Z release (YYYY-MM-DD)" sentence |

If the release adds or changes a serializer, check the parts of the packaging metadata that
face users on PyPI: `pyproject.toml`'s `description` and `keywords`, and `README.md`'s
one-liner and feature list. `README.md` is the PyPI long description, and it is easy to
ship a release whose front page never mentions its headline feature.

## 3. Release PR

One PR, green CI before merge — the same rule as any other change. Two gates need
interpreting:

- **Codacy blocks.** Its gate is "0 issues of at least minor severity", so a single
  markdownlint nit reds the PR. Query findings without leaving the terminal:
  `codacy pr gh trungdong prov <PR#>` — it names file, line and rule. In Markdown, write
  bare URLs as `<https://…>`. Note that new code can push an existing function over the
  Lizard cyclomatic-complexity threshold of 15 even when the function itself looks
  untouched.
- **Coveralls is advisory.** A "Coverage decreased" failure is non-blocking *provided* the
  local gate passes: `uv run coverage run -m pytest && uv run coverage report` must exit 0
  against the `fail_under = 97` floor in `pyproject.toml`. Defensive `raise` branches in
  new code routinely cost a fraction of a percent on the delta while the floor still holds.

## 4. Publish

**Confirm with the maintainer before this step.** Everything up to here is reversible;
nothing below is. A PyPI version number can never be reused, even after deletion.

```bash
# Dry run to TestPyPI
gh workflow run release.yml --repo trungdong/prov --ref master
gh run watch <run-id> --repo trungdong/prov --exit-status
curl -s https://test.pypi.org/pypi/prov/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

Expect `publish-pypi` to be skipped in that run — that is the `if:` guard working.

Then cut the release, which fires the real publish. Take the notes from the `HISTORY.md`
section you just dated, so the release page and the changelog cannot drift:

```bash
gh release create X.Y.Z --repo trungdong/prov --target master \
    --title X.Y.Z --notes-file <notes.md>
gh run watch <run-id> --repo trungdong/prov --exit-status
```

## 5. Verify what shipped

Check the metadata, then actually install it:

```bash
curl -s https://pypi.org/pypi/prov/X.Y.Z/json | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(d['info']['version'], [u['packagetype'] for u in d['urls']])
print(d['info']['requires_dist'])"
```

`requires_dist` must show **every** dependency gated behind an extra
(`; extra == "rdf"` and friends). Since 3.0.0, core `prov` has no unconditional runtime
dependencies, and an ungated entry here means that contract has been broken.

```bash
uv venv .v && uv pip install --python .v/bin/python prov==X.Y.Z
.v/bin/python -c "import prov; print(prov.__version__)"
```

Then exercise the release's headline feature through the installed package, not the
checkout — that is what catches package-data that was never added to
`[tool.setuptools.package-data]`. A serializer that reads a vendored file at runtime works
perfectly from a source tree and fails from a wheel.

## 6. conda-forge

The autotick-bot opens a bump PR against
[`conda-forge/prov-feedstock`](https://github.com/conda-forge/prov-feedstock) within a few
hours of the PyPI release. **Check for it and reuse it** rather than opening your own:

```bash
gh pr list -R conda-forge/prov-feedstock --state open
```

The bot supplies the version, sha256 and build number and re-renders. Review the run
dependencies: conda has no extras, so by convention the recipe stays full-featured and
mirrors the `rdf`/`xml`/`dot`/`graph` extras as hard dependencies.

**The trap that cost time on 3.0.0:** if the bot's rerender touched
`.github/workflows/`, `gh pr merge` fails with "the base branch policy prohibits the
merge". That message is wrong. The real cause is a `gh` token without the `workflow`
scope, which the merge REST API reports as a 403. Fix with
`gh auth refresh -h github.com -s workflow`, or merge in the web UI.

## 7. Close out

- Close the release's GitHub milestone.
- Confirm <https://pypi.org/project/prov/> and the conda-forge feed both show the new
  version.

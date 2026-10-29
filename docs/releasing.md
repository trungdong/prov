# Releasing

How a `prov` release is cut, from a green `main` to PyPI and conda-forge.

Substitute the version being released for `X.Y.Z` throughout.

## Checklist

1. Pre-flight on the release commit: the gate block of §1, then the own-warnings run,
   `uv run python benchmarks/ab.py <previous tag> --python 3.12` run twice, the second time
   with `--gc`, the suite-count comparison, and `uv build` with the wheel listing.
2. Stamp, in one commit: `src/prov/__init__.py`, `HISTORY.md`, `ROADMAP.md`,
   `docs/reference/conformance.md`, `CITATION.cff`; the status lines and index rows of the
   specs the release ships; `pyproject.toml` and `README.md` if a serializer changed (§2).
3. Release PR, green CI, Codacy findings reviewed, local coverage gate passing (§3).
4. Publish: `gh workflow run release.yml` as the TestPyPI dry run, then
   `gh release create X.Y.Z` with notes from `HISTORY.md`, each followed by
   `gh run watch`, then the Zenodo lookup (§4).
5. Verify: the PyPI metadata `curl`, a clean `uv venv` install, and the headline feature
   from the installed package (§5).
6. conda-forge: `gh pr list -R conda-forge/prov-feedstock --state open`, review and merge
   the bot's bump (§6).
7. Close out: milestone, PyPI and conda-forge feeds (§7).

## What publishes what

Two things are not obvious from the outside:

- **The GitHub release is the trigger.** `.github/workflows/release.yml` runs its
  `publish-pypi` job on `release: types: [published]`. There is no separate "publish"
  button and no manual `twine upload`. Creating the GitHub release *is* how a version
  reaches PyPI.
- **`workflow_dispatch` only ever reaches TestPyPI.** The same workflow's
  `publish-testpypi` job is gated on `github.event_name == 'workflow_dispatch'`, so a
  manual run is always a dry run. It cannot publish to PyPI by accident.

Both publish jobs use PyPI Trusted Publishing through the `testpypi` and `pypi` GitHub
environments, so there are no API tokens to rotate.

## 1. Pre-flight

Run on the commit you intend to release, before stamping anything. Releasing from `2.x`
rather than `main`? Read "Releasing from the `2.x` maintenance branch" at the end first, since
some of the steps below change.

Run the gates every pull request passes, listed in `CONTRIBUTING.md` under "Checks every
pull request must pass". For the Codacy line, the changed files are those since the previous
release: `git diff --name-only <previous tag>`.

Then the checks only a release runs:

```bash
# prov must raise no DeprecationWarning, PendingDeprecationWarning or FutureWarning
# of its own (#340, #441); the ini-style filter is deliberate, the -W form silently
# ignores submodules
uv run --python 3.15 --extra rdf --extra xml --extra dot --extra graph pytest -q -o $'filterwarnings=\nerror::DeprecationWarning:prov\nerror::PendingDeprecationWarning:prov\nerror::FutureWarning:prov'

# Speed against the previous release, on one machine; advisory, but a release should
# not ship an unexplained regression. The per-change CI job compares each change with
# its parent only, so slowdowns under its threshold can add up across a release unseen.
uv run python benchmarks/ab.py <previous tag> --python 3.12

# The same comparison with garbage collection on. The run above times with it off and
# this one with it on. The release's HISTORY figure quotes this run beside the first
# only where a benchmark's change differs between the two by more than 4 percentage
# points, because each run's figure carries the 2% spread an unchanged tree shows on a
# quiet machine.
uv run python benchmarks/ab.py <previous tag> --python 3.12 --gc

# The build, including any package data the release depends on at runtime
uv build
unzip -l dist/prov-*.whl | grep -E "py.typed|prov-jsonld-context"
```

Compare the suite's pass, skip and xfail counts against the previous run and against the
count the release PR states; `CLAUDE.md` deliberately records no fixed number. A skip or
xfail that is new, gone, or unexplained by the release's own changes is a regression, not a
new baseline.

## 2. Stamp the release

The stamped files, in one commit:

| File | Change |
|---|---|
| `src/prov/__init__.py` | `__version__ = "X.Y.Z"`, the single source of truth; `pyproject.toml` reads it via `dynamic = ["version"]` and `docs/conf.py` imports it, so nothing else carries the number |
| `HISTORY.md` | Date the heading: `## X.Y.Z (YYYY-MM-DD)`, matching the style of the entries below it |
| `ROADMAP.md` | Move the release's row from **Next** to the top of **Released**, as `[X.Y.Z](…/releases/tag/X.Y.Z) \| YYYY-MM-DD \| theme`. An unplanned point release has no row under **Next**; add its row under **Released** directly |
| `docs/reference/conformance.md` | Per-release revisit; the page states it is "revisited at every release"; verify its claims still hold and update the "it was revised for X.Y.Z" sentence |
| `CITATION.cff` | `version: "X.Y.Z"`; `src/prov/tests/test_citation.py` fails the suite if it disagrees with `prov.__version__` |

Also set the status line of each spec under `planning/specs/` that the release ships to
"Complete; shipped in X.Y.Z", and its row in `planning/README.md` to "Complete" with the
release in the Release column.

If the release adds or changes a serializer, check the parts of the packaging metadata that
face users on PyPI: `pyproject.toml`'s `description` and `keywords`, and `README.md`'s
one-liner and feature list. `README.md` is the PyPI long description, and it is easy to
ship a release whose front page never mentions its headline feature.

## 3. Release PR

One PR, green CI before merge, the same rule as any other change. Two checks need
interpreting:

- **Codacy reports, the maintainer decides.** Its GitHub check is not a required status
  check. Review its findings and merge with none outstanding; `codacy pr gh trungdong prov
  <PR#>` lists them with file, line and rule without leaving the terminal. In Markdown,
  write bare URLs as `<https://…>`. New code can push an existing function over the Lizard
  cyclomatic-complexity threshold of 15 even when the function itself looks untouched.
- **Coveralls is advisory.** A "Coverage decreased" failure is non-blocking *provided* the
  local gate passes: `uv run coverage run -m pytest && uv run coverage report` must exit 0
  against the `fail_under = 97` floor in `pyproject.toml`. Defensive `raise` branches in
  new code routinely cost a fraction of a percent on the delta while the floor still holds.

A PR that shows "no checks", or a matrix job stalled in "Setup Graphviz", is a CI hiccup;
see Troubleshooting.

## 4. Publish

Everything up to here is reversible; nothing below is. A PyPI version number can never be
reused, even after deletion.

```bash
# Dry run to TestPyPI
gh workflow run release.yml --repo trungdong/prov --ref main
gh run watch <run-id> --repo trungdong/prov --exit-status
curl -s https://test.pypi.org/pypi/prov/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

Expect `publish-pypi` to be skipped in that run; that is the `if:` guard working. A second dry
run for the same version fails at `publish-testpypi` with `400 File already exists`, because
TestPyPI never accepts a filename twice; judge a repeat by its `build` job, which is the part
that matters.

Then cut the release, which fires the real publish. Take the notes from the `HISTORY.md`
section you just dated, so the release page and the changelog cannot drift:

```bash
gh release create X.Y.Z --repo trungdong/prov --target main \
    --title X.Y.Z --notes-file <notes.md>
gh run watch <run-id> --repo trungdong/prov --exit-status
```

The tag also mints a Zenodo DOI through the repository's Zenodo webhook, within about a
minute. Look the record up by the tag's related identifier rather than by free text:

```bash
curl -s "https://zenodo.org/api/records?q=metadata.related_identifiers.identifier:%22https://github.com/trungdong/prov/tree/X.Y.Z%22" \
    | python3 -c "import json,sys; h=json.load(sys.stdin)['hits']['hits'][0]; print(h['doi'], h['conceptdoi'])"
```

The README badge carries the concept DOI (`10.5281/zenodo.22696001`), which resolves to the
newest version, so no README change is needed per release. Do not switch it to the
`zenodo.org/badge/latestdoi/<repo-id>` form, which is unreliable.

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
# or, in one line
env -u VIRTUAL_ENV uv run --with prov==X.Y.Z --no-project python -c "import prov; print(prov.__version__)"
```

If the install reports `no version of prov==X.Y.Z`, see Troubleshooting before re-running
anything. Run these checks with `env -u VIRTUAL_ENV` in front of `uv`.

Then exercise the release's headline feature through the installed package, not the
checkout; that is what catches package-data that was never added to
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
mirrors the `rdf`/`xml`/`dot`/`graph`/`pygments` extras as hard dependencies.

If `gh pr merge` refuses the bot's PR for "base branch policy", see Troubleshooting.

## 7. Close out

- Create the release's GitHub milestone if it does not exist, assign the issues the release
  closed, and close it. Check the previous release's milestone is closed too.
- Confirm <https://pypi.org/project/prov/> and the conda-forge feed both show the new
  version.

## Raising the Python floor

Raise the floor once per interpreter end of life, in its own PR, first in the release's
series, so that every later PR builds on the new floor. The places that name the floor:

- `pyproject.toml`: `requires-python`, the classifier line for the dropped version,
  ruff's `target-version` and the comment on its `UP` rules, and mypy's
  `python_version`; then `uv lock`, and `ruff check --fix src/ benchmarks/` with a
  review of what the `UP` rules rewrite.
- `pyrightconfig.json`: `pythonVersion`.
- `.github/workflows/CI.yml`: the matrix and the Coveralls `carryforward` list.
- The interpreter loops in `Makefile` and `CONTRIBUTING.md`, and the sentence in
  `CONTRIBUTING.md` on the versions a pull request must pass on.
- `README.md`, `docs/installation.md`, `docs/whats-new-3.md` and the `HISTORY.md` entry.
- `ROADMAP.md`'s support-policy paragraph, in the release PR.
- `SECURITY.md`, which says what each supported line requires, in the release PR.
- `main`'s branch protection, which requires the dropped version's `pytest` check until
  the PR that removes it from the matrix is about to merge.

Code that worked around the old interpreter goes in the same PR, with its tests.

On conda-forge, the bot's bump PR changes the version, not the floor. On that PR, set
`{% set python_min = "X.Y" %}` at the top of `recipe/meta.yaml` to the new floor and
rerender; if the recipe has no such line, add it, since without one it inherits
conda-forge's global pin.

After publishing, two checks beyond section 5:

```bash
curl -s https://pypi.org/pypi/prov/X.Y.Z/json | python3 -c "
import json,sys; print(json.load(sys.stdin)['info']['requires_python'])"
```

must print the new floor (`>=3.11`), and on an interpreter below it

```bash
uv venv --python 3.10 .v310 && uv pip install --python .v310/bin/python prov==X.Y.Z
```

must fail, because the release's `requires-python` excludes that interpreter. An
unpinned `pip install prov` there installs the last release that supported it, which is
what the floor change intends.

## Releasing from the `2.x` maintenance branch

The steps above assume `main`. A back-port release cut from `2.x` follows the same shape,
with these deviations, established on earlier 2.x releases and expected to hold for any
later one.

**No `benchmarks/` directory.** Run `ruff check` and `ruff format --check` on `src/` alone,
and skip the `ab.py` comparison.

**Only two extras exist.** `2.x` predates the extras split, so it has no `dot` or `graph`
extra and errors out if you pass them. Every command in §1 that names four extras takes two
on `2.x`:

```bash
uv run --extra rdf --extra xml pytest -q
```

**`2.x` has its own suite counts**, including, unlike main, a non-zero xfail count. Compare
against the previous release's numbers on `2.x` itself, and treat a moved skip or xfail the
same way you would on main: a regression to investigate unless the release's own changes
explain it.

**Not all of §2's stamped files apply.** Stamp `src/prov/__init__.py`, the `HISTORY.md`
heading and `CITATION.cff` if the branch has one. `2.x` has no per-release row in
`ROADMAP.md`, since its table stops at the last release stamped before the branch diverged, and
`docs/reference/conformance.md` carries no "revised for" sentence; confirm those two
absences rather than assuming them, and if either has since gained the line, stamp it.

**The release must target the branch.** `gh release create X.Y.Z --target 2.x`. The
workflow triggers on `release: types: [published]` repo-wide and is not gated to a branch,
so publishing from `2.x` needs nothing else. conda-forge, however, gets no bump PR: the
feedstock tracks the newest release, and the autotick-bot only moves forward. §6 does not
apply to a 2.x release unless a maintainer wants a dedicated 2.x conda label.

## Troubleshooting

Each entry gives the symptom, the cause and the fix.

- **`Error: Unauthorized` from `codacy`.** The CLI's stored token has expired. Re-login in a
  real terminal with `codacy login --token <token>`, never inside an agent session.
- **A Codacy finding on the Cloud that the local analyser does not reproduce.** The local
  CLI skips a tool whose binary is not installed, Pylint and Lizard among them, so
  `codacy-analysis analyze --files <changed files>` can be clean while the Cloud reports a
  Pylint rule or a Lizard complexity threshold. Install the tool, or run the CLI with
  `--install-dependencies`, and fix a real finding; clear a false positive with
  `codacy pr gh trungdong prov <PR#> -I <issue-id>` followed by
  `codacy pr gh trungdong prov <PR#> --reanalyze`, and the check turns green a minute or
  so later.
- **`gh pr checks` reports "no checks" on a freshly opened PR.** GitHub dropped the
  `pull_request` event. `gh pr close <PR#> && gh pr reopen <PR#>` fires the `reopened` event
  and CI starts.
- **A matrix job stalls in its "Setup Graphviz" step** for half an hour or more while its
  siblings finish. The cause is unknown. `gh run cancel <run-id>` and then
  `gh run rerun <run-id> --failed` repeats only the stalled job and keeps the green results.
- **`no version of prov==X.Y.Z` after a release.** Two causes, neither a failed upload. uv
  caches index responses, so for several minutes it keeps insisting the version does not
  exist while PyPI already serves it; pass `--refresh` (`uv pip install --refresh …`, or
  `uv run --with prov==X.Y.Z --refresh …`). In the first minute or two `--refresh` does not
  help either, because the JSON API at `pypi.org/pypi/prov/X.Y.Z/json` serves a new version
  before the simple index that installers read; poll the index and install once it names
  both files:

  ```bash
  curl -s -H 'Accept: application/vnd.pypi.simple.v1+json' https://pypi.org/simple/prov/ \
      | python3 -c "import json,sys; print([f['filename'] for f in json.load(sys.stdin)['files'] if 'X.Y.Z' in f['filename']])"
  ```

  A genuine upload failure looks different: the metadata `curl` of §5 returns 404 rather
  than the new version, and the release workflow's `publish-pypi` job is red.
- **The one-line post-release check passes for the wrong code.** A `VIRTUAL_ENV` inherited
  from another checkout makes `uv run --with prov==X.Y.Z --no-project` import that
  checkout's `prov` instead of the published wheel, silently. Run it with
  `env -u VIRTUAL_ENV` in front of `uv`, as §5 shows.
- **"Running mypy on PyPy is not supported yet".** The interpreter loop left `.venv` on
  `pypy3.11`; that is the interpreter, not a type error. Re-run pinned:
  `uv run --python 3.13 --extra rdf --extra xml --extra dot --extra graph mypy src`.
- **A feedstock merge refused for "base branch policy".** The message is wrong. The bot's
  rerender touched `.github/workflows/`, and the `gh` token lacks the `workflow` scope,
  which the merge REST API reports as a 403. Fix with
  `gh auth refresh -h github.com -s workflow`, or merge in the web UI.

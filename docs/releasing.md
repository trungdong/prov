# Releasing

How a `prov` release is cut, from a green `main` to PyPI and conda-forge.

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

Run on the commit you intend to release, before stamping anything. Releasing from `2.x`
rather than `main`? Read "Releasing from the `2.x` maintenance branch" at the end first —
four of the steps below change.

```bash
# Full interpreter matrix, matching the CI matrix
for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do
    uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest -q || break
done

uv run mypy src
uv run ruff check src/
uv run ruff format --check src/

# prov must raise no DeprecationWarning, PendingDeprecationWarning or FutureWarning
# of its own (#340, #441); the ini-style filter is deliberate, the -W form silently
# ignores submodules
uv run --python 3.14 --extra rdf --extra xml --extra dot --extra graph pytest -q -o $'filterwarnings=\nerror::DeprecationWarning:prov\nerror::PendingDeprecationWarning:prov\nerror::FutureWarning:prov'
```

Run the benchmark suite and compare it with the committed baseline; a regression
here is advisory, but a release should not ship one unexplained:

```bash
uv run pytest benchmarks/ --benchmark-json=/tmp/bench.json -q
uv run python benchmarks/compare.py benchmarks/baseline.json /tmp/bench.json
```

Compare the suite's pass, skip and xfail counts against the previous run and against the
count the release PR states; `CLAUDE.md` deliberately records no fixed number. A skip or
xfail that is new, gone, or unexplained by the release's own changes is a regression, not a
new baseline.

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

Five files, in one commit:

| File | Change |
|---|---|
| `src/prov/__init__.py` | `__version__ = "X.Y.Z"` — the single source of truth; `pyproject.toml` reads it via `dynamic = ["version"]` and `docs/conf.py` imports it, so nothing else carries the number |
| `HISTORY.md` | Date the heading: `## X.Y.Z (YYYY-MM-DD)`, matching the style of the entries below it |
| `ROADMAP.md` | Stamp the row: `**X.Y.Z** *(released YYYY-MM-DD)*` |
| `docs/reference/conformance.md` | Per-release revisit — the page states it is "revisited at every release"; verify its claims still hold and update the "last revised for the X.Y.Z release (YYYY-MM-DD)" sentence |
| `CITATION.cff` | `version: "X.Y.Z"` — `src/prov/tests/test_citation.py` fails the suite if it disagrees with `prov.__version__` |

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
  untouched. The `codacy` CLI's stored token expires: `Error: Unauthorized` means re-login
  in a real terminal (`codacy login --token <token>`, never inside a Claude Code session).
  A Cloud-only finding that `codacy-analysis analyze --files <changed files>` does not
  reproduce locally (seen: an Opengrep "lxml.etree DoS" pattern on a test parsing prov's own
  XML output) is cleared with `codacy pr gh trungdong prov <PR#> -I <issue-id>` followed by
  `codacy pr gh trungdong prov <PR#> --reanalyze`; the GitHub check turns green a minute
  or so later.
- **Coveralls is advisory.** A "Coverage decreased" failure is non-blocking *provided* the
  local gate passes: `uv run coverage run -m pytest && uv run coverage report` must exit 0
  against the `fail_under = 97` floor in `pyproject.toml`. Defensive `raise` branches in
  new code routinely cost a fraction of a percent on the delta while the floor still holds.
- **Two CI hiccups that look like failures and are not.** GitHub occasionally drops the
  `pull_request` event on a freshly opened PR, so `gh pr checks` reports "no checks";
  `gh pr close <PR#> && gh pr reopen <PR#>` fires the `reopened` event and CI starts. A matrix
  job can also stall in its "Setup Graphviz" step for half an hour or more while its siblings
  finish; `gh run cancel <run-id>` and then `gh run rerun <run-id> --failed` repeats only the
  stalled job and keeps the green results.

## 4. Publish

Everything up to here is reversible; nothing below is. A PyPI version number can never be
reused, even after deletion.

```bash
# Dry run to TestPyPI
gh workflow run release.yml --repo trungdong/prov --ref main
gh run watch <run-id> --repo trungdong/prov --exit-status
curl -s https://test.pypi.org/pypi/prov/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

Expect `publish-pypi` to be skipped in that run — that is the `if:` guard working. A second dry
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
`zenodo.org/badge/latestdoi/<repo-id>` form; that endpoint answered 504 when 3.1.1 was cut.

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

**If that install fails with `no version of prov==X.Y.Z`, do not treat it as a failed
upload.** uv caches index responses, so for several minutes after a release it keeps
insisting the version does not exist while PyPI is already serving it. Pass `--refresh` to
bust the cache — `uv pip install --refresh …`, or `uv run --with prov==X.Y.Z --refresh …`
for the one-liner form. A genuine upload failure looks different: the `curl` metadata query
above returns 404 rather than the new version, and the release workflow's `publish-pypi`
job is red. Check those two before re-running anything.

Run these checks with `env -u VIRTUAL_ENV` in front of `uv`. A `VIRTUAL_ENV` inherited from
another checkout makes `uv run --with prov==X.Y.Z --no-project` import that checkout's `prov`
instead of the published wheel, silently, so the check passes for the wrong code.

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

**Known trap:** if the bot's rerender touched `.github/workflows/`, `gh pr merge` fails
with "the base branch policy prohibits the merge". That message is wrong. The real cause
is a `gh` token without the `workflow` scope, which the merge REST API reports as a 403.
Fix with `gh auth refresh -h github.com -s workflow`, or merge in the web UI.

## 7. Close out

- Create the release's GitHub milestone if it does not exist, assign the issues the release
  closed, and close it. Check the previous release's milestone is closed too; 3.1.0's was
  still open when 3.1.1 was cut.
- Confirm <https://pypi.org/project/prov/> and the conda-forge feed both show the new
  version.

## Releasing from the `2.x` maintenance branch

The steps above assume `main`. A back-port release cut from `2.x` follows the same shape,
with four deviations — established across 2.5.2 and 2.5.3, and expected to hold for any
later 2.x release.

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

**Two of §2's four stamped files do not apply.** `2.x` has no per-release row in
`ROADMAP.md` — its table stops at the last release stamped before the branch diverged — and
`docs/reference/conformance.md` carries no "last revised for the X.Y.Z release" sentence.
Stamp `src/prov/__init__.py` and the `HISTORY.md` heading, and confirm those two absences
rather than assuming them; if either has since gained the relevant line, stamp it.

**The release must target the branch.** `gh release create X.Y.Z --target 2.x`. The
workflow triggers on `release: types: [published]` repo-wide and is not gated to a branch,
so publishing from `2.x` needs nothing else. conda-forge, however, gets no bump PR: the
feedstock tracks the newest release, and the autotick-bot only moves forward. §6 does not
apply to a 2.x release unless a maintainer wants a dedicated 2.x conda label.

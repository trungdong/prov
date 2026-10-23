# Contributing

Contributions are welcome. Every little bit helps, and credit is always given.

## Ways to contribute

### Report bugs

Report bugs at <https://github.com/trungdong/prov/issues>. Include your operating system
and version, any details about your local setup that might help, and the steps to
reproduce the bug.

### Fix bugs or implement features

Look through the [issues](https://github.com/trungdong/prov/issues). Anything tagged
"bug" or "feature" is open to whoever wants to work on it.

### Write documentation

More documentation is always useful, whether in the official docs, in docstrings, or as
blog posts and articles elsewhere.

### Propose a feature

File an issue at <https://github.com/trungdong/prov/issues>. Explain how the feature would
work and keep the scope as narrow as possible, so that it is easier to implement. This is
a volunteer-driven project.

## Set up for development

1. Fork the `prov` repository on GitHub.
2. Clone your fork:

   ```bash
   git clone git@github.com:your_name_here/prov.git
   ```

3. Create the development environment with [uv](https://docs.astral.sh/uv/), which
   manages the project virtualenv for you:

   ```bash
   cd prov/
   uv sync --extra rdf --extra xml --extra dot --extra graph
   ```

   The full test suite needs all four extras.
   [docs/dependencies.md](https://github.com/trungdong/prov/blob/main/docs/dependencies.md)
   explains what each dependency is for.

4. Install the pre-commit hooks:

   ```bash
   uv run pre-commit install
   ```

   The hooks run ruff (lint and format) and hygiene checks (trailing whitespace,
   end-of-file newlines, YAML and TOML validation) on every commit.

5. Create a branch:

   ```bash
   git checkout -b name-of-your-bugfix-or-feature
   ```

6. Make your changes, then run the checks that every pull request must pass:

   ```bash
   # All supported interpreters (matches the CI matrix). "cpython3.11" stops uv from
   # reusing a PyPy 3.11 environment left by the previous run.
   for py in cpython3.11 3.12 3.13 3.14 3.15 pypy3.11; do
       uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest || break
   done

   uv run mypy src                  # strict, library and tests; configured in pyproject.toml
   uv run ruff check src/ benchmarks/
   uv run ruff format --check src/ benchmarks/
   codacy-analysis analyze --files <changed files>   # expect "0 issues found"
   ```

   The first run downloads any interpreter you do not already have cached.

   mypy checks the tests under the same strict settings as the library, so a new test
   module needs type annotations, including `-> None` on each test function. Older test
   modules that do not pass yet are listed under `[[tool.mypy.overrides]]` in
   `pyproject.toml`. Do not add a module to that list. If your change makes a listed module
   pass, delete its name.

   The last line runs the [Codacy CLI](https://github.com/codacy/codacy-analysis-cli) on
   the files you changed, Markdown included. Install it once with
   `npm install -g @codacy/analysis-cli`. Codacy also analyses
   every pull request on GitHub. That check does not block a merge. The maintainer reviews
   its findings and merges with none outstanding.

   CI also runs an advisory `own-warnings` job, which fails if `prov` raises a
   `DeprecationWarning`, `PendingDeprecationWarning` or `FutureWarning` of its own on the
   newest interpreter.

7. Commit and push your branch:

   ```bash
   git add .
   git commit -m "Your detailed description of your changes."
   git push origin name-of-your-bugfix-or-feature
   ```

8. Open a pull request on GitHub.

## Pull request guidelines

1. Include tests.
2. If the pull request adds functionality, update the docs. Give new functions a docstring
   and add the feature to the list in README.md.
3. The pull request must pass on CPython 3.11 to 3.15 and on PyPy 3.11. The automated
   checks at the bottom of the pull request run the full matrix.
4. The `benchmark` check times your change and the target branch on one CI runner. It is
   advisory and never blocks a merge. If it is red, or if your change is meant to alter
   speed, run `uv run python benchmarks/ab.py main --python 3.12` and put its table in the
   pull request. `benchmarks/README.md` describes the script.
5. Add an entry to `HISTORY.md` under the unreleased version.

## Licensing

`prov` is released under the MIT licence (see `LICENSE`). By submitting a contribution you
agree that it is licensed under the same terms, with no additional restrictions. The
licence that applies to your contribution inbound is the licence the project applies
outbound. There is no contributor licence agreement to sign.

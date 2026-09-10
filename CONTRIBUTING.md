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

6. Make your changes, then run the tests on every supported interpreter:

   ```bash
   for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do uv run --python $py --extra rdf --extra xml --extra dot --extra graph pytest || break; done
   ```

   The first run downloads any interpreter you do not already have cached.

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
3. The pull request must pass on Python 3.10 and later and on PyPy. The automated checks
   at the bottom of the pull request run the full matrix.

## Licensing

`prov` is released under the MIT licence (see `LICENSE`). By submitting a contribution you
agree that it is licensed under the same terms, with no additional restrictions. The
licence that applies to your contribution inbound is the licence the project applies
outbound. There is no contributor licence agreement to sign.

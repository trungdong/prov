============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/trungdong/prov/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub `issues <https://github.com/trungdong/prov/issues>`_ for bugs.
Anything tagged with "bug" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub `issues <https://github.com/trungdong/prov/issues>`_
for features. Anything tagged with "feature" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

We could always use more documentation, whether as part of the
official prov docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/trungdong/prov/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `prov` for local development.

1. Fork the `prov` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/prov.git

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ mkvirtualenv prov
    $ cd prov/
    $ pip install -r requirements-dev.txt

(NOTE: To be updated. The above step is no longer correct.)

4. Set up pre-commit hooks to ensure code quality checks run automatically::

    $ uv run pre-commit install

   This installs the pre-commit framework hooks that will run ruff (linting and
   formatting) and hygiene checks (trailing whitespace, end-of-file newlines,
   YAML/TOML validation) on every commit, catching issues before they're pushed.

5. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

6. When you're done making changes, check that your changes pass the tests, including testing other supported Python versions via uv::

    $ for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do uv run --python $py --extra rdf --extra xml pytest || break; done

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.10+ and for PyPy3.
   Look for the automated checks at the bottom of your pull request and make sure that
   the tests pass for all supported Python versions.

.PHONY: clean-pyc clean-build docs clean

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with ruff"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every supported Python version via uv"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"

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
	ruff check src/

test:
	python setup.py test

test-all:
	for py in 3.10 3.11 3.12 3.13 3.14 pypy3.11; do \
		uv run --python $$py --extra rdf --extra xml pytest || exit 1; \
	done

coverage:
	coverage run --source prov setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

docs:
	rm -f docs/prov.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ src/prov
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	open docs/_build/html/index.html

release: clean
	python setup.py sdist upload
	python setup.py bdist_wheel upload

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

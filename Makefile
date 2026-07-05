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

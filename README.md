# Introduction

[![Latest Release](https://badge.fury.io/py/prov.svg)](http://badge.fury.io/py/prov)
[![License](https://img.shields.io/pypi/l/prov.svg)](https://pypi.python.org/pypi/prov/)
[![CI Status](https://github.com/trungdong/prov/workflows/CI/badge.svg)](https://github.com/trungdong/prov/actions?workflow=CI)
[![Coverage Status](https://img.shields.io/coveralls/trungdong/prov.svg)](https://coveralls.io/r/trungdong/prov?branch=master)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/73bdf6dda3884abf9f5e79352c07e66c)](https://app.codacy.com/gh/trungdong/prov/dashboard)
[![Supported Python version](https://img.shields.io/pypi/pyversions/prov.svg)](https://pypi.python.org/pypi/prov/)

A library for W3C Provenance Data Model supporting PROV-O (RDF), PROV-XML, PROV-JSON and PROV-JSONLD import/export

- Free software: MIT license
- Documentation: <http://prov.readthedocs.io/>.
- Python 3 only.

## Features

- An implementation of the [W3C PROV Data Model](http://www.w3.org/TR/prov-dm/) in Python.
- In-memory classes for PROV assertions, which can then be output as [PROV-N](http://www.w3.org/TR/prov-n/)
- Serialization and deserialization support: [PROV-O](http://www.w3.org/TR/prov-o/) (RDF), [PROV-XML](http://www.w3.org/TR/prov-xml/), [PROV-JSON](http://www.w3.org/Submission/prov-json/) and [PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/).
- Exporting PROV documents into various graphical formats (e.g. PDF, PNG, SVG).
- Convert a PROV document to a [Networkx MultiDiGraph](https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html) and back.

### Uses

See [a short tutorial](http://trungdong.github.io/prov-python-short-tutorial.html) for using this package.

This package is used extensively by [ProvStore](https://openprovenance.org/store/),
a free online repository for provenance documents.

## Roadmap

3.0.0 has been released, completing the staged modernisation (tooling, type hints,
tests, documentation, standards conformance). See
[ROADMAP.md](https://github.com/trungdong/prov/blob/master/ROADMAP.md) for the plan
and the 3.x API-stability promise.
Feedback is welcome on the [issue tracker](https://github.com/trungdong/prov/issues).

## Supported versions

The latest 3.x release receives all fixes. The most recent 2.x release
receives security fixes, plus bug fixes back-ported from 3.x up to and
including 2.6.0, after which it reverts to security fixes only; 1.x and
earlier no longer receive fixes. See
[SECURITY.md](https://github.com/trungdong/prov/blob/master/SECURITY.md)
for the full support table and how to report a vulnerability.

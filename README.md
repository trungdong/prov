# prov

[![Latest Release](https://badge.fury.io/py/prov.svg)](https://badge.fury.io/py/prov)
[![License](https://img.shields.io/pypi/l/prov.svg)](https://pypi.org/project/prov/)
[![CI Status](https://github.com/trungdong/prov/workflows/CI/badge.svg)](https://github.com/trungdong/prov/actions?workflow=CI)
[![Coverage Status](https://img.shields.io/coveralls/trungdong/prov.svg)](https://coveralls.io/r/trungdong/prov?branch=main)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/73bdf6dda3884abf9f5e79352c07e66c)](https://app.codacy.com/gh/trungdong/prov/dashboard)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22696001.svg)](https://doi.org/10.5281/zenodo.22696001)
[![Supported Python version](https://img.shields.io/pypi/pyversions/prov.svg)](https://pypi.org/project/prov/)

A Python implementation of the [W3C PROV Data Model](https://www.w3.org/TR/prov-dm/), with
import and export in PROV-JSON, PROV-JSONLD, PROV-XML and PROV-O (RDF).

- Documentation: <https://prov.readthedocs.io/>
- Licence: MIT
- Python 3.10 or later

## Features

- In-memory classes for every PROV-DM record type, printable as
  [PROV-N](https://www.w3.org/TR/prov-n/).
- Serialization to and from [PROV-JSON](https://www.w3.org/submissions/prov-json/),
  [PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/),
  [PROV-XML](https://www.w3.org/TR/prov-xml/) and [PROV-O](https://www.w3.org/TR/prov-o/) (RDF).
- Export to graphical formats such as PDF, PNG and SVG through Graphviz.
- Conversion to and from a [NetworkX](https://networkx.org/) `MultiDiGraph`.
- Command-line tools, `prov-convert` and `prov-compare`.

Start with the [tutorial](https://prov.readthedocs.io/en/latest/tutorial/getting-started.html).
Over 7,000 public repositories on GitHub
[depend on this package](https://github.com/trungdong/prov/network/dependents).

## Status

3.0.0 completed the modernisation programme (tooling, type hints, tests, documentation and
standards conformance) and 3.1.0 added PROV-JSONLD.
[What's new in 3](https://prov.readthedocs.io/en/latest/whats-new-3.html) summarises the 3.x
line for projects still on 2.x.
[ROADMAP.md](https://github.com/trungdong/prov/blob/main/ROADMAP.md) lists the planned
releases and the API-stability promise. Feedback is welcome on the
[issue tracker](https://github.com/trungdong/prov/issues).

## Supported versions

The latest 3.x release receives all fixes. The most recent 2.x release receives security
fixes only; 2.5.3 was the last release to carry bug fixes back-ported from 3.x. Releases
before 2.0 receive no fixes.
[SECURITY.md](https://github.com/trungdong/prov/blob/main/SECURITY.md) has the support table
and how to report a vulnerability.

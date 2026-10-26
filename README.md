# prov

[![Latest Release](https://badge.fury.io/py/prov.svg)](https://badge.fury.io/py/prov)
[![License](https://img.shields.io/pypi/l/prov.svg)](https://pypi.org/project/prov/)
[![CI Status](https://github.com/trungdong/prov/workflows/CI/badge.svg)](https://github.com/trungdong/prov/actions?workflow=CI)
[![Coverage Status](https://img.shields.io/coveralls/trungdong/prov.svg)](https://coveralls.io/r/trungdong/prov?branch=main)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/73bdf6dda3884abf9f5e79352c07e66c)](https://app.codacy.com/gh/trungdong/prov/dashboard)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22696001.svg)](https://doi.org/10.5281/zenodo.22696001)
[![Supported Python version](https://img.shields.io/pypi/pyversions/prov.svg)](https://pypi.org/project/prov/)

A Python implementation of the [W3C PROV Data Model](https://www.w3.org/TR/prov-dm/), with
import and export in PROV-N, PROV-JSON, PROV-JSONLD, PROV-XML and PROV-O (RDF). It is
MIT-licensed, needs Python 3.11 or later, and is documented at <https://prov.readthedocs.io/>.

## Install

```bash
pip install prov
```

PROV-JSON, PROV-N and PROV-JSONLD need nothing else; PROV-XML, PROV-O and the graph tools
each need an extra, listed on the [installation page](https://prov.readthedocs.io/en/latest/installation.html).

## Quick start

```python
import prov.model as pm

doc = pm.ProvDocument()
doc.set_default_namespace("https://example.org/")
doc.entity("report")
doc.activity("analysis")
doc.wasGeneratedBy("report", "analysis")
print(doc.get_provn())
doc.serialize("report.json")
```

```provn
document
  default <https://example.org/>

  entity(report)
  activity(analysis, -, -)
  wasGeneratedBy(report, analysis, -)
endDocument
```

The [tutorial](https://prov.readthedocs.io/en/latest/tutorial/getting-started.html) continues from here.

## Features

- In-memory classes for every PROV-DM record type, readable from and printable as
  [PROV-N](https://www.w3.org/TR/prov-n/).
- Serialization to and from [PROV-N](https://www.w3.org/TR/prov-n/),
  [PROV-JSON](https://www.w3.org/submissions/prov-json/),
  [PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/),
  [PROV-XML](https://www.w3.org/TR/prov-xml/) and [PROV-O](https://www.w3.org/TR/prov-o/) (RDF).
- Export to graphical formats such as PDF, PNG and SVG through Graphviz.
- Conversion to and from a [NetworkX](https://networkx.org/) `MultiDiGraph`.
- Command-line tools, `prov-convert` and `prov-compare`.

Over 7,000 public repositories on GitHub
[depend on this package](https://github.com/trungdong/prov/network/dependents).
[What's new in 3](https://prov.readthedocs.io/en/latest/whats-new-3.html) summarises the 3.x
line, and the [announcement post](https://trungdong.github.io/provpy-3.html) explains the move.
[ROADMAP.md](https://github.com/trungdong/prov/blob/main/ROADMAP.md) lists the planned releases,
[SECURITY.md](https://github.com/trungdong/prov/blob/main/SECURITY.md) the supported versions,
and the [issue tracker](https://github.com/trungdong/prov/issues) takes feedback.

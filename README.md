# prov [![Build Status](https://travis-ci.org/trungdong/prov.svg)](https://travis-ci.org/trungdong/prov) [![Code Coverage](https://coveralls.io/repos/trungdong/prov/badge.png?branch=master)](https://coveralls.io/r/trungdong/prov?branch=master)

prov is a python package for generating and manipulating in-memory structures for the
[PROV Data Model](http://www.w3.org/TR/prov-dm/). It provides classes for PROV assertions
and can be used to serialize provenance documents into PROV-N or
[PROV-JSON](http://www.w3.org/Submission/prov-json/) representations and deserialize
PROV-JSON. The package also provides a module for exporting documents into graphical
formats such as PDF, PNG and SVG.

This package is under active development.

- [PyPi Index Entry](https://pypi.python.org/pypi/provpy)


## Installation
```
pip install prov
```

## Usage

```python
import prov.model as prov
```

### Examples

#### Basic document with bundle

```python
import prov.model as prov

document = prov.ProvDocument()

document.set_default_namespace('http://example.org/0/')
document.add_namespace('ex1', 'http://example.org/1/')
document.add_namespace('ex2', 'http://example.org/2/')

document.entity('e001')

bundle = document.bundle('e001')
bundle.set_default_namespace('http://example.org/2/')
bundle.entity('e001')

document.get_provn() # =>

# document
#   default <http://example.org/0/>
#   prefix ex2 <http://example.org/2/>
#   prefix ex1 <http://example.org/1/>
#   
#   entity(e001)
#   bundle e001
#     default <http://example.org/2/>
#     
#     entity(e001)
#   endBundle
# endDocument

document.serialize() # =>

# {"prefix": {"default": "http://example.org/0/", "ex2": "http://example.org/2/", "ex1": "http://example.org/1/"}, "bundle": {"e001": {"prefix": {"default": "http://example.org/2/"}, "entity": {"e001": {}}}}, "entity": {"e001": {}}}

```

## Uses

### ProvStore

This package is used extensively by [ProvStore](https://provenance.ecs.soton.ac.uk/store/),
a respository for provenance documents. ProvStore can be used to persist your provenance documents
for free via its REST API.
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
```bash
pip install prov
```

## Usage

```python
import prov.model as prov
```

### Examples

#### Basic document

```python
import prov.model as prov
import datetime

document = prov.ProvDocument()

document.set_default_namespace('http://anotherexample.org/')
document.add_namespace('ex', 'http://example.org/')

e2 = document.entity('e2', (
    (prov.PROV_TYPE, "File"),
    ('ex:path', "/shared/crime.txt"),
    ('ex:creator', "Alice"),
    ('ex:content', "There was a lot of crime in London last month"),
))

a1 = document.activity('a1', datetime.datetime.now(), None, {prov.PROV_TYPE: "edit"})
# References can be qnames or ProvRecord objects themselves
document.wasGeneratedBy(e2, a1, None, {'ex:fct': "save"})
document.wasAssociatedWith('a1', 'ag2', None, None, {prov.PROV_ROLE: "author"})
document.agent('ag2', {prov.PROV_TYPE: 'prov:Person', 'ex:name': "Bob"})

document.get_provn() # =>

# document
#   default <http://anotherexample.org/>
#   prefix ex <http://example.org/>
#   
#   entity(e2, [prov:type="File", ex:creator="Alice",
#               ex:content="There was a lot of crime in London last month",
#               ex:path="/shared/crime.txt"])
#   activity(a1, 2014-07-09T16:39:38.795839, -, [prov:type="edit"])
#   wasGeneratedBy(e2, a1, -, [ex:fct="save"])
#   wasAssociatedWith(a1, ag2, -, [prov:role="author"])
#   agent(ag2, [prov:type="prov:Person", ex:name="Bob"])
# endDocument
```

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

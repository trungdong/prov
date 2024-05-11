============
Introduction
============


.. image:: https://badge.fury.io/py/prov.svg
  :target: http://badge.fury.io/py/prov
  :alt: Latest Release
.. image:: https://github.com/trungdong/prov/workflows/CI/badge.svg?branch=master
  :target: https://github.com/trungdong/prov/actions?workflow=CI
  :alt: CI Status
.. image:: https://img.shields.io/coveralls/trungdong/prov.svg
  :target: https://coveralls.io/r/trungdong/prov?branch=master
  :alt: Coverage Status
.. image:: https://img.shields.io/pypi/wheel/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Wheel Status
.. image:: https://img.shields.io/pypi/pyversions/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Supported Python version
.. image:: https://img.shields.io/pypi/l/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: License


A library for W3C Provenance Data Model supporting PROV-O (RDF), PROV-XML, PROV-JSON import/export

* Free software: MIT license
* Documentation: http://prov.readthedocs.io/.
* Python 3 only.

Features
--------

* An implementation of the `W3C PROV Data Model <http://www.w3.org/TR/prov-dm/>`_ in Python.
* In-memory classes for PROV assertions, which can then be output as `PROV-N <http://www.w3.org/TR/prov-n/>`_
* Serialization and deserialization support: `PROV-O <http://www.w3.org/TR/prov-o/>`_ (RDF), `PROV-XML <http://www.w3.org/TR/prov-xml/>`_ and `PROV-JSON <http://www.w3.org/Submission/prov-json/>`_.
* Exporting PROV documents into various graphical formats (e.g. PDF, PNG, SVG).
* Convert a PROV document to a `Networkx MultiDiGraph <https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html>`_ and back.


Uses
^^^^

See `a short tutorial  <http://trungdong.github.io/prov-python-short-tutorial.html>`_ for using this package.

This package is used extensively by `ProvStore <https://openprovenance.org/store/>`_,
a free online repository for provenance documents.

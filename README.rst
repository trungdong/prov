============
Introduction
============


.. image:: https://badge.fury.io/py/prov.svg
  :target: http://badge.fury.io/py/prov
  :alt: Latest Release
.. image:: https://travis-ci.org/trungdong/prov.svg
  :target: https://travis-ci.org/trungdong/prov
  :alt: Build Status
.. image:: https://img.shields.io/coveralls/trungdong/prov.svg
  :target: https://coveralls.io/r/trungdong/prov?branch=master
  :alt: Coverage Status
.. image:: https://landscape.io/github/trungdong/prov/master/landscape.svg?style=flat
  :target: https://landscape.io/github/trungdong/prov/master
  :alt: Code Health
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

Features
--------

* An implementation of the `W3C PROV Data Model <http://www.w3.org/TR/prov-dm/>`_ in Python.
* In-memory classes for PROV assertions, which can then be output as `PROV-N <http://www.w3.org/TR/prov-n/>`_
* Serialization and deserialization support: `PROV-O <http://www.w3.org/TR/prov-o/>`_ (RDF), `PROV-XML <http://www.w3.org/TR/prov-xml/>`_ and `PROV-JSON <http://www.w3.org/Submission/prov-json/>`_.
* Exporting PROV documents into various graphical formats (e.g. PDF, PNG, SVG).
* Convert a PROV document to a `Networkx MultiDiGraph <https://networkx.readthedocs.io/en/stable/reference/classes.multigraph.html>`_ and back.


Uses
^^^^

See `a short tutorial  <http://trungdong.github.io/prov-python-short-tutorial.html>`_ for using this package.

This package is used extensively by `ProvStore <https://provenance.ecs.soton.ac.uk/store/>`_,
a free online repository for provenance documents.
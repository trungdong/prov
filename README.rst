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
.. image:: https://img.shields.io/pypi/wheel/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Wheel Status
.. image:: https://img.shields.io/pypi/dm/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Downloads
.. image:: https://img.shields.io/pypi/pyversions/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Supported Python version
.. image:: https://img.shields.io/pypi/l/prov.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: License


A library for W3C Provenance Data Model supporting PROV-JSON and PROV-XML import/export

* Free software: MIT license
* Documentation: http://prov.readthedocs.org.

Features
--------

* An implementation of the `W3C PROV Data Model <http://www.w3.org/TR/prov-dm/>`_ in Python.
* In-memory classes for PROV assertions, which can then be output as `PROV-N <http://www.w3.org/TR/prov-n/>`_
* Serialization and deserializtion support: `PROV-JSON <http://www.w3.org/Submission/prov-json/>`_ and `PROV-XML <http://www.w3.org/TR/prov-xml/>`_.
* Exporting PROV documents into various graphical formats (e.g. PDF, PNG, SVG).


Uses
^^^^

See `a short tutorial  <http://trungdong.github.io/prov-python-short-tutorial.html>`_ for using this package.

This package is used extensively by `ProvStore <https://provenance.ecs.soton.ac.uk/store/>`_,
a free online repository for provenance documents.

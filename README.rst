============
Introduction
============


.. image:: https://badge.fury.io/py/prov.svg
  :target: http://badge.fury.io/py/prov
  :alt: Latest Release
.. image:: https://travis-ci.org/trungdong/prov.svg
  :target: https://travis-ci.org/trungdong/prov
  :alt: Build Status
.. image:: https://coveralls.io/repos/trungdong/prov/badge.png?branch=master
  :target: https://coveralls.io/r/trungdong/prov?branch=master
  :alt: Coverage Status
.. image:: https://pypip.in/wheel/prov/badge.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Wheel Status
.. image:: https://pypip.in/download/prov/badge.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Downloads
.. image:: https://pypip.in/py_versions/prov/badge.svg
  :target: https://pypi.python.org/pypi/prov/
  :alt: Supported Python version
.. image:: https://pypip.in/license/prov/badge.svg
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
This package is used extensively by `ProvStore <https://provenance.ecs.soton.ac.uk/store/>`_,
a repository for provenance documents.

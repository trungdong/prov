===============================
prov
===============================


.. image:: https://badge.fury.io/py/prov.svg
  :target: http://badge.fury.io/py/prov
  :alt: Latest Release
.. image:: https://travis-ci.org/trungdong/prov.svg
  :target: https://travis-ci.org/trungdong/prov
  :alt: Build Status
.. image:: https://coveralls.io/repos/trungdong/prov/badge.png?branch=master
  :target: https://coveralls.io/r/trungdong/prov?branch=master
  :alt: Coverage Status
.. image:: https://pypip.in/wheel/prov/badge.png
  :target: https://pypi.python.org/pypi/prov/
  :alt: Wheel Status
.. image:: https://pypip.in/download/prov/badge.png
  :target: https://pypi.python.org/pypi/prov/
  :alt: Downloads


A library for W3C Provenance Data Model supporting PROV-JSON import/export

* Free software: MIT license
* Documentation: http://prov.readthedocs.org.

Features
--------

This package provides an implementation of the `W3C PROV Data Model <http://www.w3.org/TR/prov-dm/>`_ in Python.
It provides in-memory classes for PROV assertions and can be serialized into `PROV-JSON representation <http://www.w3.org/Submission/prov-json/>`_.
In addition, the included `prov.dot` module exports PROV documents into various graphical formats (e.g. PDF, PNG, SVG).


Uses
^^^^
This package is used extensively by `ProvStore <https://provenance.ecs.soton.ac.uk/store/>`_,
a respository for provenance documents.


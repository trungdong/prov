*WARNING*: Under active development

.. image:: https://travis-ci.org/trungdong/prov.svg
    :target: https://travis-ci.org/trungdong/prov
.. image:: https://coveralls.io/repos/trungdong/prov/badge.png?branch=master
  :target: https://coveralls.io/r/trungdong/prov?branch=master


This package provides an implementation of the `PROV Data Model <http://www.w3.org/TR/prov-dm/>`_ in Python.
It provides in-memory classes for PROV assertions and can be serialized into `PROV-JSON representation <http://www.w3.org/Submission/prov-json/>`_.
In addition, the `prov.model.graph` module exports PROV documents into graphical formats (e.g. PDF, PNG, SVG).

Deployment: The package was used to build `ProvStore <https://provenance.ecs.soton.ac.uk/store/>`_, a repository for provenance documents.

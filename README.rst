*WARNING*: Under active development

This package provides an implementation of the `PROV Data Model <http://www.w3.org/TR/prov-dm/>`_ in Python. It contains a number of sub-modules:

* prov.model: In-memory classes for PROV assertions. `ProvBundle.JSONEncoder` and `ProvBundle.JSONDecoder` provide JSON serialisation and deserialisation for a `ProvBundle` in the `PROV-JSON representation <http://www.w3.org/Submission/prov-json/>`_. In addition, the `prov.model.graph` module exports PROV documents into graphical formats (e.g. PDF, PNG, SVG).

* prov.persistence: A Django app for storing and loading `ProvBundle` instances to/from databases using Django ORM

* prov.tracking: a logging-like module to facilitate tracking provenance in Python programs


See `prov/model/test/examples.py <https://github.com/trungdong/prov/blob/master/prov/model/test/examples.py>`_ for example usages.

Deployment: The package was used to build `ProvStore <https://provenance.ecs.soton.ac.uk/store/>`_, a repository for provenance documents.

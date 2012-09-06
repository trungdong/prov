*WARNING*: Under active development

This package provides an implementation of the PROV Data Model (http://www.w3.org/TR/prov-dm/) in Python. It contains a number of sub-modules:
- prov.model: In-memory classes for PROV assertions. `ProvBundle.JSONEncoder` and `ProvBundle.JSONDecoder` provide JSON serialisation and deserialisation for a `ProvBundle` in the PROV-JSON representation.
- prov.persistence: A Django app for storing and loading `ProvBundle` instances to/from databases using Django ORM
- prov.tracking: a logging-like module to facilitate tracking provenance in Python programs
- prov.server: a Django app that provides the functionalities of a provenance repository via a Web interface and a REST API.

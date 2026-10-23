# prov.serializers

`prov.serializers` defines the serializer interface behind
{py:meth}`ProvDocument.serialize() <prov.model.ProvDocument.serialize>` and
{py:meth}`ProvDocument.deserialize() <prov.model.ProvDocument.deserialize>`, and the
registry that maps a format name (`"json"`, `"rdf"`, `"provn"`, `"xml"`, `"jsonld"`) to
its serializer class. {doc}`../howto/read-write` shows how to read and write in any
format, and the format guides ({doc}`../howto/provjson`,
{doc}`../howto/provxml`, {doc}`../howto/provo-rdf`, {doc}`../howto/provn`,
{doc}`../howto/provjsonld`) show how to use each format. This page documents the interface,
the registry and PROV-N's error type.

```{eval-rst}
.. py:module:: prov.serializers

.. autoclass:: prov.serializers.Serializer
   :members:
   :show-inheritance:

.. autoclass:: prov.serializers.Registry
   :members:

.. autofunction:: prov.serializers.get

.. autoclass:: prov.serializers.DoNotExist
   :members:
   :show-inheritance:
```

## Reading documents

{py:func}`prov.read` detects the format of a source by trying each registered
deserializer in registry order, `json`, `rdf`, `provn`, `xml`, `jsonld`, and returning the
first non-empty document. The order matters for a non-seekable stream, which only the
first attempt can read.

```{eval-rst}
.. autofunction:: prov.read
```

## PROV-N errors

```{eval-rst}
.. autoclass:: prov.serializers.provn.ProvNSyntaxError
   :members:
   :show-inheritance:
```

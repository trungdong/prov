# prov.serializers

`prov.serializers` defines the serializer interface behind
{py:meth}`ProvDocument.serialize() <prov.model.ProvDocument.serialize>` and
{py:meth}`ProvDocument.deserialize() <prov.model.ProvDocument.deserialize>`, and the
registry that maps a format name (`"json"`, `"rdf"`, `"provn"`, `"xml"`, `"jsonld"`) to
its serializer class. The how-to guides ({doc}`../howto/provjson`,
{doc}`../howto/provxml`, {doc}`../howto/provo-rdf`, {doc}`../howto/provn`,
{doc}`../howto/provjsonld`) show how to use each format. This page documents the interface
and the registry only.

```{eval-rst}
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
first attempt can read. The {doc}`../howto/provjson` guide describes the error behaviour.

```{eval-rst}
.. autofunction:: prov.read
```

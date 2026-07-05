# prov.serializers

`prov.serializers` defines the pluggable serializer interface used by
{py:meth}`ProvDocument.serialize() <prov.model.ProvBundle.serialize>` and
{py:meth}`ProvDocument.deserialize() <prov.model.ProvDocument.deserialize>`, and the registry
that looks up the serializer class for a given format string (`"json"`, `"xml"`, `"rdf"`,
`"provn"`). For how to use each format, see the {doc}`../howto/provjson`,
{doc}`../howto/provxml`, {doc}`../howto/provo-rdf`, and {doc}`../howto/provn` how-to guides;
this page documents the underlying interface and registry only.

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

{py:func}`prov.read` auto-detects the format of a source by trying each registered
deserializer in turn; see {doc}`../howto/provjson` for its caveats around error reporting.

```{eval-rst}
.. autofunction:: prov.read
```

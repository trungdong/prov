# prov.serializers

`prov.serializers` defines the serializer interface behind
{py:meth}`ProvDocument.serialize() <prov.model.ProvDocument.serialize>` and
{py:meth}`ProvDocument.deserialize() <prov.model.ProvDocument.deserialize>`, and the
registry that maps a format name (`"json"`, `"rdf"`, `"provn"`, `"xml"`, `"jsonld"`) to
its serializer class. {doc}`../howto/read-write` shows how to read and write in any
format, and the format guides ({doc}`../howto/provjson`,
{doc}`../howto/provxml`, {doc}`../howto/provo-rdf`, {doc}`../howto/provn`,
{doc}`../howto/provjsonld`) show how to use each format. This page documents the interface,
the registry and the exception classes for reading and writing.

```{eval-rst}
.. py:module:: prov.serializers

.. autoclass:: prov.serializers.Serializer
   :members:
   :show-inheritance:

.. autoclass:: prov.serializers.Registry
   :members:

.. autofunction:: prov.serializers.get
```

## Reading documents

{py:func}`prov.read` detects the format of a source by trying the registered
deserializers in turn, as {ref}`auto-detect` describes.

```{eval-rst}
.. autofunction:: prov.read
```

## Exceptions

Every exception that `prov` raises on purpose derives from {py:class}`prov.Error`. The
model's refusals derive from {py:class}`~prov.model.ProvException`, and a failure to read
or write a document derives from {py:class}`~prov.serializers.ProvSerializationError`.

```text
prov.Error
|-- ProvException                        (prov.model)
|   |-- ProvValueError                   also a ValueError
|   |-- ProvExceptionInvalidQualifiedName
|   |-- ProvElementIdentifierRequired
|   |-- ProvMissingFormalAttribute
|   `-- ProvUnificationError
|-- ProvSerializationError               (prov.serializers)
|   |-- ProvJSONException
|   |-- ProvJSONLDException
|   |-- ProvNSyntaxError                 also a ProvException
|   |-- ProvXMLException
|   |-- ProvRDFException
|   `-- ProvFormatNotDetected            also a TypeError
`-- DoNotExist                           (prov.serializers)
```

A reader raises its format's error for input it cannot represent. When the model rejects
a record or a namespace that the reader builds, the reader raises its own error, whose
message names the record and carries the model's sentence, and sets the model's exception
as `__cause__`. A fault that the reader finds itself has no cause. Code that builds the
record gets the model's exception.

{py:func}`prov.read` raises `ProvFormatNotDetected` when no registered reader produces a
document. When the source starts with `{` or `document` and the reader that names rejected
it with its own error, that error is the `__cause__`. Any other source leaves it empty.

```{eval-rst}
.. autoclass:: prov.serializers.ProvSerializationError
   :members:
   :show-inheritance:

.. autoclass:: prov.serializers.ProvFormatNotDetected
   :members:
   :show-inheritance:

.. autoclass:: prov.serializers.DoNotExist
   :members:
   :show-inheritance:

.. autoclass:: prov.serializers.provn.ProvNSyntaxError
   :members:
   :show-inheritance:
```

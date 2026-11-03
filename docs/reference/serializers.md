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

{ref}`auto-detect` shows how to read a document whose format is not known.

```{eval-rst}
.. autofunction:: prov.read
```

## Exceptions

The exceptions below derive from {py:class}`prov.Error`. The model's refusals derive from
{py:class}`~prov.model.ProvException`, and a failure to read or write a document derives
from {py:class}`~prov.serializers.ProvSerializationError`.

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

{py:class}`~prov.serializers.ProvSerializationError` says what a reader's error carries,
and code that builds the record gets the model's exception itself.
{py:class}`~prov.serializers.ProvFormatNotDetected` says when its `__cause__` is a reader's
error.

With an explicit `format`, input that is not well-formed in the underlying syntax raises the
parsing library's own error, outside the tree: `json.JSONDecodeError` for the two JSON
formats, `lxml`'s `XMLSyntaxError`, and rdflib's parser error for the chosen `rdf_format`,
such as `BadSyntax` for TriG and Turtle.

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

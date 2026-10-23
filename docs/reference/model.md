# prov.model

`prov.model` is the in-memory object model for [PROV-DM](https://www.w3.org/TR/prov-dm/)
documents. A {py:class}`~prov.model.ProvDocument` contains
{py:class}`~prov.model.ProvBundle` objects, which hold records. Records are elements
(entities, activities, agents) and the relations between them. The namespace machinery
that builds and resolves their identifiers lives here too. The
{doc}`../tutorial/getting-started` walks through building a document with this API, and
the [PROV-DM Primer](https://www.w3.org/TR/prov-primer/) covers the concepts behind the
classes.

## Documents and bundles

```{eval-rst}
.. autoclass:: prov.model.ProvDocument
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvBundle
   :members:
   :show-inheritance:
```

## Elements

```{eval-rst}
.. autoclass:: prov.model.ProvEntity
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvActivity
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvAgent
   :members:
   :show-inheritance:
   :inherited-members:
```

## Relations

```{eval-rst}
.. autoclass:: prov.model.ProvGeneration
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvUsage
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvCommunication
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvStart
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvEnd
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvInvalidation
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvDerivation
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvAttribution
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvAssociation
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvDelegation
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvInfluence
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvSpecialization
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvAlternate
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvMention
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: prov.model.ProvMembership
   :members:
   :show-inheritance:
   :inherited-members:
```

## Namespaces and literals

```{eval-rst}
.. autoclass:: prov.model.NamespaceManager
   :members:
   :show-inheritance:
```

### Equality

Records compare by type, identifier and attributes; a record without an identifier equals
only a record without one. Two attribute values are the same value when they have the same
datatype and the same value in that datatype's value space. `xsd:boolean`, `xsd:decimal`,
`xsd:double`, `xsd:float` and `xsd:integer` with its subtypes have a value space here,
every other datatype compares by text, and a text outside its datatype's lexical space
compares as text. A plain Python value takes the datatype the writers give it, so `5` and
`Literal("05", XSD_INT)` are one value and `5` and `Literal("5", XSD_LONG)` are two. A
`NaN` is one value with itself. `hash()` follows `==` on records and literals. A bundle
compares as a set of records, not by its identifier; a document also matches its bundles
by identifier, and a bundle never equals a document.

```{eval-rst}
.. autoclass:: prov.model.Literal
   :members:
   :show-inheritance:
```

## Type aliases

{py:data}`~prov.model.AttributeValue` is the type of the values a dict of attributes may
hold. {doc}`../howto/typing` shows how to use it when a type checker reports a call.

```{eval-rst}
.. autodata:: prov.model.AttributeValue
   :no-value:
```

## Exceptions

```{eval-rst}
.. autoclass:: prov.Error
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvException
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvWarning
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvFutureRejectionWarning
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvExceptionInvalidQualifiedName
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvElementIdentifierRequired
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvValueError
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvUnificationError
   :members:
   :show-inheritance:
```

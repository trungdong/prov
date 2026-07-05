# prov.model

`prov.model` is the core of the library: the in-memory object model for
[PROV-DM](https://www.w3.org/TR/prov-dm/) documents. A {py:class}`~prov.model.ProvDocument`
contains {py:class}`~prov.model.ProvBundle`\ s of records — elements (entities, activities,
agents) and relations between them — plus the namespace machinery used to build and resolve
their identifiers. See the {doc}`../tutorial/getting-started` for a walk-through of building
a document with this API, and the
[PROV-DM Primer](https://www.w3.org/TR/prov-primer/) for the concepts behind the classes
below.

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

.. autoclass:: prov.model.Literal
   :members:
   :show-inheritance:
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

.. autoclass:: prov.model.ProvExceptionInvalidQualifiedName
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvElementIdentifierRequired
   :members:
   :show-inheritance:
```

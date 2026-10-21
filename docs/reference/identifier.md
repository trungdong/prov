# prov.identifier

`prov.identifier` implements PROV's namespaced identifiers. A
{py:class}`~prov.identifier.Namespace` groups identifiers under a URI and an optional
prefix. A {py:class}`~prov.identifier.QualifiedName` combines a namespace with a local
part to name entities, activities, agents and attributes.
{py:class}`~prov.identifier.Identifier` is the common base class; an `Identifier` given as
an attribute value is stored as an `xsd:anyURI` {py:class}`~prov.model.Literal`.
`prov.model.NamespaceManager` (see {doc}`model`) tracks the namespaces registered on a
bundle and resolves prefixes during parsing and serialization.

```{eval-rst}
.. autoclass:: prov.identifier.Identifier
   :members:
   :show-inheritance:

.. autoclass:: prov.identifier.QualifiedName
   :members:
   :show-inheritance:

.. autoclass:: prov.identifier.Namespace
   :members:
   :show-inheritance:
```

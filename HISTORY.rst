.. :changelog:

History
-------

1.0.1 (2014-08-18)
^^^^^^^^^^^^^^^^^^
* Added: Default namespace inheritance for bundles
* Fixed: :py:meth:`prov.model.NamespaceManager.valid_qualified_name` did not support :py:class:`~prov.model.XSDQName`
* Added: Convenience :py:func:`prov.read` method with a lazy format detection
* Added: Convenience :py:meth:`~prov.model.ProvBundle.plot` method on the :py:class:`~prov.model.ProvBundle` class (requiring matplotlib).
* Changed: The previous :py:meth:`!add_record` method renamed to :py:meth:`~prov.model.ProvBundle.new_record`
* Added: :py:meth:`~prov.model.ProvBundle.add_record` function which takes one argument, a :py:class:`~prov.model.ProvRecord`, has been added
* Fixed: Document flattening (see :py:meth:`~prov.model.ProvDocument.flattened`)
* Added: :py:meth:`~prov.model.ProvRecord.__hash__` function added to :py:class:`~prov.model.ProvRecord` (**at risk**: to be removed as :py:class:`~prov.model.ProvRecord` is expected to be mutable)
* Added: :py:attr:`~prov.model.ProvRecord.extra_attributes` added to mirror existing :py:attr:`~prov.model.ProvRecord.formal_attributes`

1.0.0 (2014-07-15)
^^^^^^^^^^^^^^^^^^

* The underlying data model has been rewritten and is **incompatible** with pre-1.0 versions.
* References to PROV elements (i.e. entities, activities, agents) in relation records are now QualifiedName instances.
* A document or bundle can have multiple records with the same identifier.
* PROV-JSON serializer and deserializer are now separated from the data model. 
* Many tests added, including round-trip PROV-JSON encoding/decoding.
* For changes pre-1.0, see CHANGES.txt.

.. :changelog:

History
-------

dev (2014-07-30)
^^^^^^^^^^^^^^^^^^
* add_record method renamed to new_record.
* New add_record function which takes one argument, a ProvRecord, has been added.
* Document flattening fixed.
* Hash function added to ProvRecord.
* Helper method extra_attributes added to mirror existing formal_attributes.

1.0.0 (2014-07-15)
^^^^^^^^^^^^^^^^^^

* The underlying data model has been rewritten and is **incompatible** with pre-1.0 versions.
* References to PROV elements (i.e. entities, activities, agents) in relation records are now QualifiedName instances.
* A document or bundle can have multiple records with the same identifier.
* PROV-JSON serializer and deserializer are now separated from the data model. 
* Many tests added, including round-trip PROV-JSON encoding/decoding.
* For changes pre-1.0, see CHANGES.txt.

.. :changelog:

History
-------

1.0.0 (2014-07-15)
^^^^^^^^^^^^^^^^^^

* The underlying data model has been rewritten and is **incompatible** with pre-1.0 versions.
* References to PROV elements (i.e. entities, activities, agents) in relation records are now QualifiedName instances.
* A document or bundle can have multiple records with the same identifier.
* PROV-JSON serializer and deserializer are now separated from the data model. 
* Many tests added, including round-trip PROV-JSON encoding/decoding.
* For changes pre-1.0, see CHANGES.txt.
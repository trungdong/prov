PROV-XML test documents, read by test_xml.py and the shared round-trip tests.

* example_01.xml to example_41.xml (numbers 04 and 05 are absent): the official
  PROV-XML examples from the specification. Examples 4 and 5 are tested
  separately in test_xml.py. Some files were adjusted to be valid according to
  the specification.
* prov_primer_complete_example.xml: the complete example from the PROV Primer
  documentation, adjusted to be valid according to the specification.
* pc1.xml: a Provenance Challenge 1 style document from the ProvToolbox test
  resources (https://github.com/lucmoreau/ProvToolbox), with a few ordering and
  formatting changes so that it round-trips.
* namespace_redefined.xml, namespace_redefined_but_does_not_change.xml and
  nested_default_namespace.xml: documents for the namespace-handling tests in
  test_xml.py.

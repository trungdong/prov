from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.model import ProvDocument, Namespace, XSDQName


def document_with_n_bundles_having_default_namespace(n):
    prov_doc = ProvDocument()
    prov_doc.add_namespace('ex', 'http://www.example.org/')
    for i in range(n):
        x = str(i + 1)
        bundle = prov_doc.bundle('ex:bundle/' + x)
        bundle.set_default_namespace('http://www.example.org/default/' + x)
        bundle.entity('e')
    return prov_doc


class TestQualifiedNamesBase(object):
    """This is the base class for testing support for qualified names and
    namespaces. It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    def test_xsd_qnames(self):
        prov_doc = ProvDocument()
        ex = Namespace('ex', 'http://www.example.org/')
        prov_doc.add_namespace(ex)
        # ex1 is not added to the document
        ex1 = Namespace('ex1', 'http://www.example1.org/')

        an_xsd_qname = XSDQName(ex['a_value'])
        another_xsd_qname = XSDQName(ex1['another_value'])

        e1 = prov_doc.entity(
            'ex:e1',
            {'prov:value': an_xsd_qname, 'prov:type': another_xsd_qname}
        )
        for _, attr_value in e1.attributes:
            self.assertIsInstance(attr_value, XSDQName)

        self.assertRoundTripEquivalence(prov_doc)

    def test_namespace_inheritance(self):
        prov_doc = ProvDocument()
        prov_doc.add_namespace('ex', 'http://www.example.org/')
        bundle = prov_doc.bundle('ex:bundle')
        e1 = bundle.entity('ex:e1')
        self.assertIsNotNone(e1.identifier, "e1's identifier is None!")
        self.assertRoundTripEquivalence(prov_doc)

    def test_default_namespace_inheritance(self):
        prov_doc = ProvDocument()
        prov_doc.set_default_namespace('http://www.example.org/')
        bundle = prov_doc.bundle('bundle')
        e1 = bundle.entity('e1')
        self.assertIsNotNone(e1.identifier, "e1's identifier is None!")
        self.assertRoundTripEquivalence(prov_doc)

    def test_flattening_1_bundle_with_default_namespace(self):
        prov_doc = document_with_n_bundles_having_default_namespace(1)
        flattened = prov_doc.flattened()
        self.assertRoundTripEquivalence(flattened)

    def test_flattening_2_bundles_with_default_namespace(self):
        prov_doc = document_with_n_bundles_having_default_namespace(2)
        flattened = prov_doc.flattened()
        self.assertRoundTripEquivalence(flattened)

    def test_flattening_3_bundles_with_default_namespace(self):
        prov_doc = document_with_n_bundles_having_default_namespace(3)
        flattened = prov_doc.flattened()
        self.assertRoundTripEquivalence(flattened)

    def test_flattening_1_bundle_with_default_namespaces(self):
        prov_doc = document_with_n_bundles_having_default_namespace(1)
        prov_doc.set_default_namespace('http://www.example.org/default/0')
        flattened = prov_doc.flattened()
        self.assertRoundTripEquivalence(flattened)

    def test_flattening_2_bundle_with_default_namespaces(self):
        prov_doc = document_with_n_bundles_having_default_namespace(2)
        prov_doc.set_default_namespace('http://www.example.org/default/0')
        flattened = prov_doc.flattened()
        self.assertRoundTripEquivalence(flattened)

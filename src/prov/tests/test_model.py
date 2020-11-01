"""
Created on Jan 25, 2012

@author: Trung Dong Huynh
"""
import unittest
import logging
import os

from prov.model import ProvDocument, ProvBundle, ProvException, first, Literal
from prov.tests import examples
from prov.tests.attributes import TestAttributesBase
from prov.tests.qnames import TestQualifiedNamesBase
from prov.tests.statements import TestStatementsBase
from prov.tests.utility import RoundTripTestCase

logger = logging.getLogger(__name__)


EX_URI = "http://www.example.org/"
EX2_URI = "http://www.example2.org/"


class TestExamplesBase(object):
    """This is the base class for testing support for all the examples provided
    in prov.tests.examples.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    def test_all_examples(self):
        counter = 0
        for name, graph in examples.tests:
            counter += 1
            logger.info("%d. Testing the %s example", counter, name)
            g = graph()
            self.do_tests(g)


class TestLoadingProvToolboxJSON(unittest.TestCase):
    def setUp(self):
        self.json_path = os.path.dirname(os.path.abspath(__file__)) + "/json/"
        filenames = os.listdir(self.json_path)
        self.fails = []
        for filename in filenames:
            if filename.endswith(".json"):
                with open(self.json_path + filename) as json_file:
                    try:
                        g1 = ProvDocument.deserialize(json_file)
                        json_str = g1.serialize(indent=4)
                        g2 = ProvDocument.deserialize(content=json_str)
                        self.assertEqual(
                            g1,
                            g2,
                            "Round-trip JSON encoding/decoding failed:  %s." % filename,
                        )
                    except:
                        self.fails.append(filename)

    def test_loading_all_json(self):
        # self.assertFalse(fails, 'Failed to load/round-trip %d JSON files (%s)' % (len(fails), ', '.join(fails)))

        # Code for debugging the failed tests
        for filename in self.fails:
            # Reload the failed files
            filepath = self.json_path + filename
            #             os.rename(json_path + filename, json_path + filename + '-fail')
            with open(filepath) as json_file:
                logger.info("Loading %s...", filepath)
                g1 = ProvDocument.deserialize(json_file)
                json_str = g1.serialize(indent=4)
                g2 = ProvDocument.deserialize(content=json_str)
                self.assertEqual(
                    g1, g2, "Round-trip JSON encoding/decoding failed:  %s." % filename
                )


class TestFlattening(unittest.TestCase):
    def test_flattening(self):
        for name, graph in examples.tests:
            logger.info("Testing flattening of the %s example", name)
            document = graph()
            flattened = document.flattened()
            flattened_records = set(flattened.get_records())
            # counting all the records:
            n_records = 0
            for record in document.get_records():
                n_records += 1
                self.assertIn(record, flattened_records)
            for bundle in document.bundles:
                for record in bundle.get_records():
                    n_records += 1
                    self.assertIn(record, flattened_records)
            self.assertEqual(n_records, len(flattened.get_records()))


class TestUnification(unittest.TestCase):
    def test_unifying(self):
        # This is a very trivial test just to exercise the unified() function
        # TODO: Create a proper unification test
        json_path = os.path.dirname(os.path.abspath(__file__)) + "/unification/"
        filenames = os.listdir(json_path)
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            filepath = json_path + filename
            with open(filepath) as json_file:
                logger.info("Testing unifying: %s", filename)
                logger.debug("Loading %s...", filepath)
                document = ProvDocument.deserialize(json_file)
                flattened = document.flattened()
                unified = flattened.unified()
                self.assertLess(
                    len(unified.get_records()), len(flattened.get_records())
                )


class TestBundleUpdate(unittest.TestCase):
    def test_bundle_update_simple(self):
        doc = ProvDocument()
        doc.set_default_namespace(EX_URI)

        b1 = doc.bundle("b1")
        b1.entity("e")

        b2 = doc.bundle("b2")
        b2.entity("e")

        self.assertRaises(ProvException, lambda: b1.update(1))
        self.assertRaises(ProvException, lambda: b1.update(doc))

        b1.update(b2)
        self.assertEqual(len(b1.get_records()), 2)

    def test_document_update_simple(self):
        d1 = ProvDocument()
        d1.set_default_namespace(EX_URI)
        d1.entity("e")

        b1 = d1.bundle("b1")
        b1.entity("e")

        d2 = ProvDocument()
        d2.set_default_namespace(EX_URI)
        d2.entity("e")

        b1 = d2.bundle("b1")
        b1.entity("e")
        b2 = d2.bundle("b2")
        b2.entity("e")

        self.assertRaises(ProvException, lambda: d1.update(1))

        d1.update(d2)
        self.assertEqual(len(d1.get_records()), 2)
        self.assertEqual(len(d1.bundles), 2)


class TestAddBundle(unittest.TestCase):
    def document_1(self):
        d1 = ProvDocument()
        ns_ex = d1.add_namespace("ex", EX_URI)
        d1.entity(ns_ex["e1"])
        return d1

    def document_2(self):
        d2 = ProvDocument()
        ns_ex = d2.add_namespace("ex", EX2_URI)
        d2.activity(ns_ex["a1"])
        return d2

    def bundle_0(self):
        b = ProvBundle(namespaces={"ex": EX2_URI})
        return b

    def test_add_bundle_simple(self):
        d1 = self.document_1()
        b0 = self.bundle_0()

        def sub_test_1():
            d1.add_bundle(b0)

        self.assertRaises(ProvException, sub_test_1)
        self.assertFalse(d1.has_bundles())

        d1.add_bundle(b0, "ex:b0")
        self.assertTrue(d1.has_bundles())
        self.assertIn(b0, d1.bundles)

        def sub_test_2():
            ex2_b0 = b0.identifier
            d1.add_bundle(ProvBundle(identifier=ex2_b0))

        self.assertRaises(ProvException, sub_test_2)

        d1.add_bundle(ProvBundle(), "ex:b0")
        self.assertEqual(len(d1.bundles), 2)

    def test_add_bundle_document(self):
        d1 = self.document_1()
        d2 = self.document_2()

        def sub_test_1():
            d1.add_bundle(d2)

        self.assertRaises(ProvException, sub_test_1)

        ex2_b2 = d2.valid_qualified_name("ex:b2")
        d1.add_bundle(d2, "ex:b2")
        self.assertEqual(ex2_b2, first(d1.bundles).identifier)
        self.assertNotIn(d2, d1.bundles)
        b2 = ProvBundle()
        b2.update(d2)
        self.assertIn(b2, d1.bundles)


class TestLiteralRepresentation(unittest.TestCase):
    def test_literal_provn_with_single_quotes(self):
        l = Literal('{"foo": "bar"}')
        string_rep = l.provn_representation()
        self.assertTrue('{\\"f' in string_rep)

    def test_literal_provn_with_triple_quotes(self):
        l = Literal('"""foo\\nbar"""')
        string_rep = l.provn_representation()
        self.assertTrue('\\"\\"\\"f' in string_rep)


class AllTestsBase(
    TestExamplesBase, TestStatementsBase, TestAttributesBase, TestQualifiedNamesBase
):
    """This is a test to include all available tests."""

    pass


class RoundTripModelTest(RoundTripTestCase, AllTestsBase):
    def assertRoundTripEquivalence(self, prov_doc, msg=None):
        """Exercises prov.model without the actual serialization and PROV-N
        generation.
        """
        provn_content = prov_doc.get_provn()
        # Checking for self-equality
        self.assertEqual(
            prov_doc, prov_doc, "The document is not self-equal:\n" + provn_content
        )


if __name__ == "__main__":
    unittest.main()

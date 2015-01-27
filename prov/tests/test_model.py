"""
Created on Jan 25, 2012

@author: Trung Dong Huynh
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest
import logging
import os

from prov.model import ProvDocument, ProvException
from prov.tests import examples
from prov.tests.attributes import TestAttributesBase
from prov.tests.qnames import TestQualifiedNamesBase
from prov.tests.statements import TestStatementsBase
from prov.tests.utility import BaseTestCase, RoundTripTestCase

logger = logging.getLogger(__name__)


EX_URI = 'http://www.example.org'


class TestExamplesBase(object):
    """This is the base class for testing support for all the examples provided in prov.tests.examples.
    It is not runnable and needs to be included in a subclass of RoundTripTestCase.
    """
    def test_all_examples(self):
        counter = 0
        for name, graph in examples.tests:
            counter += 1
            logger.info('%d. Testing the %s example', counter, name)
            g = graph()
            self.assertRoundTripEquivalence(g)


class TestLoadingProvToolboxJSON(BaseTestCase):
    def setUp(self):
        self.json_path = os.path.dirname(os.path.abspath(__file__)) + '/json/'
        filenames = os.listdir(self.json_path)
        self.fails = []
        for filename in filenames:
            if filename.endswith('.json'):
                with open(self.json_path + filename) as json_file:
                    try:
                        g1 = ProvDocument.deserialize(json_file)
                        json_str = g1.serialize(indent=4)
                        g2 = ProvDocument.deserialize(content=json_str)
                        self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % filename)
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
                self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % filename)


class TestFlattening(BaseTestCase):
    def test_flattening(self):
        for name, graph in examples.tests:
            logger.info('Testing flattening of the %s example', name)
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


class TestUnification(BaseTestCase):
    def test_unifying(self):
        # This is a very trivial test just to exercise the unified() function
        # TODO: Create a proper unification test
        json_path = os.path.dirname(os.path.abspath(__file__)) + '/unification/'
        filenames = os.listdir(json_path)
        for filename in filenames:
            if not filename.endswith('.json'):
                continue
            filepath = json_path + filename
            with open(filepath) as json_file:
                logger.info('Testing unifying: %s', filename)
                logger.debug("Loading %s...", filepath)
                document = ProvDocument.deserialize(json_file)
                flattened = document.flattened()
                unified = flattened.unified()
                self.assertLess(len(unified.get_records()), len(flattened.get_records()))


class TestBundleUpdate(BaseTestCase):
    def test_bundle_update_simple(self):
        doc = ProvDocument()
        doc.set_default_namespace(EX_URI)

        b1 = doc.bundle('b1')
        b1.entity('e')

        b2 = doc.bundle('b2')
        b2.entity('e')

        self.assertRaises(ProvException, lambda: b1.update(1))
        self.assertRaises(ProvException, lambda: b1.update(doc))

        b1.update(b2)
        self.assertEqual(len(b1.get_records()), 2)

    def test_document_update_simple(self):
        d1 = ProvDocument()
        d1.set_default_namespace(EX_URI)
        d1.entity('e')

        b1 = d1.bundle('b1')
        b1.entity('e')

        d2 = ProvDocument()
        d2.set_default_namespace(EX_URI)
        d2.entity('e')

        b1 = d2.bundle('b1')
        b1.entity('e')
        b2 = d2.bundle('b2')
        b2.entity('e')

        self.assertRaises(ProvException, lambda: d1.update(1))

        d1.update(d2)
        self.assertEqual(len(d1.get_records()), 2)
        self.assertEqual(len(d1.bundles), 2)


class AllTestsBase(TestExamplesBase, TestStatementsBase, TestAttributesBase, TestQualifiedNamesBase):
    """This is a test to include all available tests.
    """
    pass


class RoundTripModelTest(RoundTripTestCase, AllTestsBase):
    def assertRoundTripEquivalence(self, prov_doc, msg=None):
        """Exercises prov.model without the actual serialization and PROV-N generation.
        """
        provn_content = prov_doc.get_provn()
        # Checking for self-equality
        self.assertEqual(prov_doc, prov_doc, 'The document is not self-equal:\n' + provn_content)


if __name__ == "__main__":
    unittest.main()

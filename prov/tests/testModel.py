"""
Created on Jan 25, 2012

@author: Trung Dong Huynh
"""
import unittest
import logging
import os

from prov.model import ProvDocument, XSDQName, Namespace
from prov.tests import examples


logger = logging.getLogger(__name__)


class JSONRoundTripTestCase(unittest.TestCase):
    def assertPROVJSONRoundTripEquivalence(self, prov_doc, msg=None):
        json_str = prov_doc.serialize(indent=4)
        prov_doc_new = ProvDocument.deserialize(content=json_str)
        self.assertEqual(prov_doc, prov_doc_new, msg)


class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testAllExamples(self):
        num_graphs = len(examples.tests)
        logger.info('PROV-JSON round-trip testing %d example provenance graphs', num_graphs)
        counter = 0
        for name, graph in examples.tests:
            counter += 1
            logger.info('%d. Testing the %s example', counter, name)
            g1 = graph()
            logger.debug('Original graph in PROV-N\n%s', g1.get_provn())
            # json_str = g1.get_provjson(indent=4)
            json_str = g1.serialize(indent=4)
            logger.debug('Original graph in PROV-JSON\n%s', json_str)
            g2 = ProvDocument.deserialize(content=json_str)
            logger.debug('Graph decoded from PROV-JSON\n%s', g2.get_provn())
            self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % name)


class TestLoadingProvToolboxJSON(unittest.TestCase):
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

    def testLoadAllJSON(self):
        # self.assertFalse(fails, 'Failed to load/round-trip %d JSON files (%s)' % (len(fails), ', '.join(fails)))
        logging.basicConfig(level=logging.DEBUG)

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


class TestFlattening(unittest.TestCase):
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


class TestUnification(unittest.TestCase):
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


class TestXSDQNames(JSONRoundTripTestCase):
    def test_xsd_qnames(self):
        prov_doc = ProvDocument()
        ex = Namespace('ex', 'http://www.example.org')
        prov_doc.add_namespace(ex)

        an_xsd_qname = XSDQName(ex['a_value'])
        prov_doc.entity('ex:e1', {'prov:value': an_xsd_qname})

        self.assertPROVJSONRoundTripEquivalence(prov_doc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()

"""
Created on Jan 25, 2012

@author: Trung Dong Huynh
"""
import unittest
import logging
import json
import os
from prov.model import ProvBundle, ProvRecord, ProvExceptionCannotUnifyAttribute, ProvDocument
from prov.model.test import examples

logger = logging.getLogger(__name__)


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


class ProvToolboxJSONTestSuite(unittest.TestSuite):
    class TestProvJSONRoundtrip(unittest.TestCase):
        def __init__(self, filepath, filename):
            self.filepath = filepath
            self.filename = filename
            super(ProvToolboxJSONTestSuite.TestProvJSONRoundtrip, self).__init__()

        def runTest(self):
            """Round-trip testing for PROV-JSON serializing and de-serializing from a PROV-JSON file.
            This test loads the specified file as PROV-JSON into a ProvBundle, serializes the ProvBundle into PROV-JSON,
            reloads the new PROV-JSON into another ProvBundle, and compares the two ProvBundle.
            """
            full_file_path = os.path.join(self.filepath, self.filename)
            with open(full_file_path) as json_file:
                g1 = json.load(json_file, cls=ProvBundle.JSONDecoder)
                json_str = g1.get_provjson(indent=4)
                g2 = ProvBundle.from_provjson(json_str)
                self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % self.filename)

    def __init__(self, tests=()):
        unittest.TestSuite.__init__(self, tests)
        json_path = os.path.dirname(os.path.abspath(__file__)) + '/json/'
        filenames = os.listdir(json_path)
        for filename in filenames:
            if filename.endswith('.json'):
                test = ProvToolboxJSONTestSuite.TestProvJSONRoundtrip(json_path, filename)
                self.addTest(test)


# class TestLoadingProvToolboxJSON(unittest.TestCase):
#     def setUp(self):
#         self.json_path = os.path.dirname(os.path.abspath(__file__)) + '/json/'
#         filenames = os.listdir(self.json_path)
#         self.fails = []
#         for filename in filenames:
#             if filename.endswith('.json'):
#                 with open(self.json_path + filename) as json_file:
#                     try:
#                         g1 = json.load(json_file, cls=ProvBundle.JSONDecoder)
#                         json_str = g1.get_provjson(indent=4)
#                         g2 = ProvBundle.from_provjson(json_str)
#                         self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % filename)
#                     except:
#                         self.fails.append(filename)
#
#     def testLoadAllJSON(self):
#         # self.assertFalse(fails, 'Failed to load/round-trip %d JSON files (%s)' % (len(fails), ', '.join(fails)))
#         logging.basicConfig(level=logging.DEBUG)
#
#         # Code for debugging the failed tests
#         for filename in self.fails:
#             # Reload the failed files
#             filepath = self.json_path + filename
# #             os.rename(json_path + filename, json_path + filename + '-fail')
#             with open(filepath) as json_file:
#                 logger.info("Loading %s...", filepath)
#                 g1 = json.load(json_file, cls=ProvBundle.JSONDecoder)
#                 json_str = g1.get_provjson(indent=4)
#                 g2 = ProvBundle.from_provjson(json_str)
#                 self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % filename)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()

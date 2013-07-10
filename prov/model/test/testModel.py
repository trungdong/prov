'''
Created on Jan 25, 2012

@author: Trung Dong Huynh
'''
import unittest
from prov.model import ProvBundle
import logging
import json
import examples
import os
logger = logging.getLogger(__name__)


class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testAllExamples(self):
        num_graphs = len(examples.tests)
        logger.info('Testing %d provenance graphs' % num_graphs)
        counter = 0
        for name, graph in examples.tests:
            counter += 1
            logger.info('%d. Testing the %s example' % (counter, name))
            g1 = graph()
            logger.debug('Original graph in PROV-N\n%s' % g1.get_provn())
            json_str = json.dumps(g1, cls=ProvBundle.JSONEncoder, indent=4)
            logger.debug('Original graph in PROV-JSON\n%s' % json_str)
            g2 = json.loads(json_str, cls=ProvBundle.JSONDecoder)
            logger.debug('Graph decoded from PROV-JSON\n%s' % g2.get_provn())
            self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % name)


class TestLoadingProvToolboxJSON(unittest.TestCase):

    def testLoadAllJSON(self):
        json_path = os.path.dirname(os.path.abspath(__file__)) + '/json/'
        filenames = os.listdir(json_path)
        fails = []
        for filename in filenames:
            if filename.endswith('.json'):
                with open(json_path + filename) as json_file:
                    try:
                        json.load(json_file, cls=ProvBundle.JSONDecoder)
                    except:
                        fails.append(filename)
        self.assertFalse(fails, 'Failed to load %d JSON files (%s)' % (len(fails), ', '.join(fails)))

        # Code for debugging the failed tests
#         for filename in fails:
#             os.rename(json_path + filename, json_path + filename + '-fail')
#             with open(json_path + filename) as json_file:
#                 json.load(json_file, cls=ProvBundle.JSONDecoder)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()

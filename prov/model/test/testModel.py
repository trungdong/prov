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
            json_str = g1.get_provjson(indent=4)
            logger.debug('Original graph in PROV-JSON\n%s' % json_str)
            g2 = ProvBundle.from_provjson(json_str)
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
                        g1 = json.load(json_file, cls=ProvBundle.JSONDecoder)
                        json_str = g1.get_provjson(indent=4)
                        g2 = ProvBundle.from_provjson(json_str)
                        self.assertEqual(g1, g2, 'Round-trip JSON encoding/decoding failed:  %s.' % filename)
                    except:
                        fails.append(filename)
        self.assertFalse(fails, 'Failed to load %d JSON files (%s)' % (len(fails), ', '.join(fails)))

        # Code for debugging the failed tests
#         for filename in fails:
#             os.rename(json_path + filename, json_path + filename + '-fail')
#             with open(json_path + filename) as json_file:
#                 json.load(json_file, cls=ProvBundle.JSONDecoder)


class TestFlattening(unittest.TestCase):
    def test1(self):
        target = ProvBundle()
        target.activity('ex:correct', '2012-03-31T09:21:00', '2012-04-01T15:21:00')

        result = ProvBundle()
        result.activity('ex:correct', '2012-03-31T09:21:00')
        result_inner = ProvBundle(identifier="ex:bundle1")
        result_inner.activity('ex:correct', None, '2012-04-01T15:21:00')
        result.add_bundle(result_inner)
        self.assertEqual(result.get_flattened(), target)

    def test2(self):
        target = ProvBundle()
        target.activity('ex:compose', other_attributes=(('prov:role', "ex:dataToCompose1"), ('prov:role', "ex:dataToCompose2")))

        result = ProvBundle()
        result.activity('ex:compose', other_attributes={'prov:role': "ex:dataToCompose1"})
        result_inner = ProvBundle(identifier="ex:bundle1")
        result_inner.activity('ex:compose', other_attributes={'prov:role': "ex:dataToCompose2"})
        result.add_bundle(result_inner)
        self.assertEqual(result.get_flattened(), target)

    def test3(self):
        target = ProvBundle()
        target.activity('ex:compose', other_attributes=(('prov:role', "ex:dataToCompose1"), ('prov:role', "ex:dataToCompose2")))

        result = ProvBundle()
        result.activity('ex:compose', other_attributes={'prov:role': "ex:dataToCompose1"})
        result_inner = ProvBundle(identifier="ex:bundle1")
        result_inner.activity('ex:compose', other_attributes=(('prov:role', "ex:dataToCompose1"), ('prov:role', "ex:dataToCompose2")))
        result.add_bundle(result_inner)
        self.assertEqual(result.get_flattened(), target)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()

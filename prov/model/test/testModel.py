'''
Created on Jan 25, 2012

@author: Trung Dong Huynh
'''
import unittest
from prov.model import ProvBundle, ProvRecord, ProvExceptionCannotUnifyAttribute
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

    def test_references_in_flattened_documents(self):
        bundle = examples.bundles1()
        flattened = bundle.get_flattened()

        records = set(flattened._records)
        for record in records:
            for attr_value in (record._attributes or {}).values():
                if attr_value and isinstance(attr_value, ProvRecord):
                    self.assertIn(attr_value, records, 'Document does not contain the record %s with id %i (related to %s)' % (attr_value, id(attr_value), record))

    def test_inferred_retyping_in_flattened_documents(self):
        g = ProvBundle()
        g.add_namespace("ex", "http://www.example.com/")
        g.wasGeneratedBy('ex:Bob', time='2012-05-25T11:15:00')
        b1 = g.bundle('ex:bundle')
        b1.agent('ex:Bob')

        h = ProvBundle()
        h.add_namespace("ex", "http://www.example.com/")
        h.agent('ex:Bob')
        h.wasGeneratedBy('ex:Bob', time='2012-05-25T11:15:00')

        self.assertEqual(g.get_flattened(), h)

    def test_non_unifiable_document(self):
        g = ProvBundle()
        g.add_namespace("ex", "http://www.example.com/")
        g.activity('ex:compose', other_attributes={'prov:role': "ex:dataToCompose1"})
        g.used('ex:compose', 'ex:testEntity')
        with self.assertRaises(ProvExceptionCannotUnifyAttribute):
            g.activity('ex:testEntity')

        h = g.bundle('ex:bundle')
        h.add_namespace("ex", "http://www.example.com/")
        h.entity('ex:compose', other_attributes={'prov:label': "impossible!!!"})

        with self.assertRaises(ProvExceptionCannotUnifyAttribute):
            g.get_flattened()

    def test_merging_records_json(self):
        test_json = """
        {
            "entity": {
                "e1": [
                    {"prov:label": "First instance of e1"},
                    {"prov:label": "Second instance of e1"}
                ]
            },
            "activity": {
                "a1": [
                    {"prov:label": "An activity with no time (yet)"},
                    {"prov:startTime": "2011-11-16T16:05:00"},
                    {"prov:endTime": "2011-11-16T16:06:00"}
                ]
            }
        }"""
        g = ProvBundle.from_provjson(test_json)
        e1 = g.get_record("e1")
        self.assertEqual(len(e1.get_attribute('prov:label')), 2, "e1 was not merged correctly, expecting two prov:label attributes")
        a1 = g.get_record("a1")
        self.assertIsNotNone(a1.get_startTime(), "a1 was not merged correctly, expecting startTime set.")
        self.assertIsNotNone(a1.get_endTime(), "a1 was not merged correctly, expecting startTime set.")
        self.assertEqual(len(a1.get_attribute('prov:label')), 1, "a1 was not merged correctly, expecting one prov:label attribute")

    def test_datetime_with_tz(self):
        """ test that timezone is taken in to account while parsing json"""
        test_json = """
        {
            "activity": {
                "a1": [
                    {"prov:label": "An activity with timezone"},
                    {"prov:startTime": "2011-11-16T16:05:00.123456+03:00"},
                    {"prov:endTime": "2011-11-16T16:06:00.654321"}
                ]
            }
        }"""
        g = ProvBundle.from_provjson(test_json)
        a1 = g.get_record("a1")
        self.assertEqual(a1.get_startTime().isoformat(),
                         "2011-11-16T16:05:00.123456+03:00",
                         "timezone is not set correctly")
        self.assertEqual(a1.get_endTime().isoformat(),
                         "2011-11-16T16:06:00.654321",
                         "timezone is not set correctly")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()

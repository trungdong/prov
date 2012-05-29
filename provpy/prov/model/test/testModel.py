'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
from prov.model import ProvContainer
import logging
import json
import examples
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def runTestOnGraph(self, graph):
        logger.debug('Original graph in PROV-N\n%s' % graph.get_asn())
        json_str = json.dumps(graph, cls=ProvContainer.JSONEncoder, indent=4)
        logger.debug('Original graph in PROV-JSON\n%s' % json_str)
        g2 = json.loads(json_str, cls=ProvContainer.JSONDecoder)
        logger.debug('Graph decoded from PROV-JSON\n%s' % g2.get_asn())
        assert(graph == g2)
        
    def testAllExamples(self):
        num_graphs = len(examples.tests)
        logger.info('Testing %d provenance graphs' % num_graphs)
        counter = 0
        for test, graph in examples.tests:
            counter += 1
            logger.info('%d. Testing the %s example' % (counter, test))
            g1 = graph()
            self.runTestOnGraph(g1)
                    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

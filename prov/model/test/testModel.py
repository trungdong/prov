'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
from prov.model import ProvBundle
import logging
import json
import examples
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# turns on the ability to use pdb
import functools
import pdb
import sys
def debug_on(*exceptions):
    if not exceptions:
        exceptions = (AssertionError, )
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions:
                pdb.post_mortem(sys.exc_info()[2])
        return wrapper
    return decorator


class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def runTestOnGraph(self, graph):
        logger.debug('Original graph in PROV-N\n%s' % graph.get_provn())
        json_str = json.dumps(graph, cls=ProvBundle.JSONEncoder, indent=4)
        logger.debug('Original graph in PROV-JSON\n%s' % json_str)
        g2 = json.loads(json_str, cls=ProvBundle.JSONDecoder)
        logger.debug('Graph decoded from PROV-JSON\n%s' % g2.get_provn())
        assert(graph == g2)

    @debug_on()
    def testAllExamples(self):
        num_graphs = len(examples.tests)
        logger.info('Testing %d provenance graphs' % num_graphs)
        counter = 0
        for test, graph in examples.tests:
            counter += 1
            logger.info('%d. Testing the %s example' % (counter, test))
            g1 = graph()
            self.runTestOnGraph(g1)

    def testCollections1(self):
        g = examples.collections()
        provn =  g.get_provn()
        assert('entity' in provn)

    def testCollections2(self):
        g = examples.collections()
        provn =  g.get_provn()
        assert('prov:Collection' in provn)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

'''
Created on Dec 7, 2012

@author: tdh
'''
import unittest
import logging
import examples
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Test(unittest.TestCase):
        
    def setUp(self):
        pass


    def tearDown(self):
        pass

    def runTestOnGraph(self, graph):
        logger.debug('Original graph in PROV-N\n%s' % graph.get_provn())
        rdf_graph = graph.rdf()
        representation = "n3"  if len(list(rdf_graph.contexts())) == 1 else "trig"
        rdf_content = rdf_graph.serialize(format=representation) 
        logger.debug('Original graph in RDF\n%s' % rdf_content)
        
    def testAllExamplesRDF(self):
        num_graphs = len(examples.tests)
        logger.info('Testing %d provenance graphs' % num_graphs)
        counter = 0
        for test, graph in examples.tests:
            counter += 1
            logger.info('%d. Testing the %s example' % (counter, test))
            prov_graph = graph()
            self.runTestOnGraph(prov_graph)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
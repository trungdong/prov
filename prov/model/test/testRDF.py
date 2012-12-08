'''
Created on Dec 7, 2012

@author: tdh
'''
import unittest
from rdflib.graph import ConjunctiveGraph
from prov.model.test.examples import bundles1


class Test(unittest.TestCase):
        
    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        prov_graph = bundles1()
        rdf_graph = prov_graph.rdf() 
        print rdf_graph.serialize(format="trig")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
import datetime
from provdjango.provmodel import Namespace, ProvContainer, PROV, Literal, XSD


class Test(unittest.TestCase):

    @staticmethod
    def build_prov_graph():
        FOAF = Namespace("foaf","http://xmlns.com/foaf/0.1/")
        EX = Namespace("ex","http://www.example.com/")
        DCTERMS = Namespace("dcterms","http://purl.org/dc/terms/")
        
        # create a provenance _container
        g = ProvContainer()
        
        # Set the default _namespace name
        g.set_default_namespace(EX.get_uri())
        g.add_namespace(DCTERMS)
        
        # add entities, first define the _attributes in a dictionary
        e0_attrs = {PROV["type"]: "File",
                    EX["path"]: "/shared/crime.txt",
                    EX["creator"]: "Alice"}
        # then create the entity
        # If you give the id as a string, it will be treated as a localname
        # under the default _namespace
        e0 = g.entity(EX["e0"], e0_attrs)
        
        # define the _attributes for the next entity
        lit0 = Literal("2011-11-16T16:06:00", XSD["dateTime"])
        attrdict ={PROV["type"]: EX["File"],
                   EX["path"]: "/shared/crime.txt",
                   DCTERMS["creator"]: FOAF['Alice'],
                   EX["content"]: "",
                   DCTERMS["create"]: lit0}
        # create the entity, note this time we give the id as a PROVQname
        e1 = g.entity(FOAF['Foo'], attrdict)
        
        # add activities
        # You can give the _attributes during the creation if there are not many
        a0 = g.activity(EX['a0'], datetime.datetime(2008, 7, 6, 5, 4, 3), None, {PROV["type"]: EX["create-file"]})
        
        g0 = g.wasGeneratedBy("g0", e0, a0, None, {EX["fct"]: "create"})
        
        attrdict={EX["fct"]: "load",
                  EX["typeexample"] : Literal("MyValue", EX["MyType"])}
        u0 = g.used("u0", a0, e1, None, attrdict)
        
        # The id for a relation is an optional argument, The system will generate one
        # if you do not specify it 
        g.wasDerivedFrom(None, e0, e1, a0, g0, u0)
    
        return g
    
    def setUp(self):
        self.prov_graph = Test.build_prov_graph()

    def tearDown(self):
        pass

    def testName(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
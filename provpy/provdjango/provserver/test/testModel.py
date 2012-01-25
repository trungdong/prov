'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
from provdm.provdm.model import PROVNamespace, PROVContainer, Entity, Activity,\
    PROVLiteral
import datetime


class Test(unittest.TestCase):

    @staticmethod
    def build_prov_graph():
        # Define your namespaces (see provpyexample_PROVQname_PROVNamespace.py)
        FOAF = PROVNamespace("foaf","http://xmlns.com/foaf/0.1/")
        ex = PROVNamespace("ex","http://www.example.com/")
        dcterms = PROVNamespace("dcterms","http://purl.org/dc/terms/")
        xsd = PROVNamespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
        prov = PROVNamespace("prov","http://www.w3.org/ns/prov-dm/")
        
        # create a provenance container
        graph = PROVContainer()
        
        # Set the default namespace name
        graph.set_default_namespace("http://www.example.com/")
        
        # add the other namespaces with their prefixes into the container
        # You can do this any time before you output the JSON serialization
        # of the container
        # Note for each namespace name, if a prefix given here is different to the
        # one carried in the PROVNamespace instance defined previously, the prefix
        # HERE will be used in the JSON serialization.
        graph.add_namespace("dcterms","http://purl.org/dc/terms/")
        graph.add_namespace("foaf","http://xmlns.com/foaf/0.1/")
        
        # add entities, first define the attributes in a dictionary
        attrdict = {"type": "File",
                    ex["path"]: "/shared/crime.txt",
                    ex["creator"]: "Alice"}
        # then create the entity
        # If you give the id as a string, it will be treated as a localname
        # under the default namespace
        e0 = Entity(id=ex["e0"],attributes=attrdict)
        # you can then add the entity into the provenance container
        graph.add(e0)
        
        # define the attributes for the next entity
        lit0 = PROVLiteral("2011-11-16T16:06:00",xsd["dateTime"])
        attrdict ={prov["type"]: ex["File"],
                   ex["path"]: "/shared/crime.txt",
                   dcterms["creator"]: FOAF['Alice'],
                   ex["content"]: "",
                   dcterms["create"]: lit0}
        # create the entity, note this time we give the id as a PROVQname
        e1 = Entity(FOAF['Foo'],attributes=attrdict)
        graph.add(e1)
        
        # add activities
        # You can give the attributes during the creation if there are not many
        a0 = Activity(id=ex['a0'],starttime=datetime.datetime(2008, 7, 6, 5, 4, 3),attributes={prov["plan"]: ex["create-file"]})
        graph.add(a0)
        
        return graph
    
    def setUp(self):
        self.prov_graph = Test.build_prov_graph()

    def tearDown(self):
        pass

    def testName(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
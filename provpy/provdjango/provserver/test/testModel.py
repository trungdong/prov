'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
import datetime
from provdjango.provmodel import Namespace, ProvContainer, PROV, Literal, XSD,\
    Identifier
import logging
import json


class Test(unittest.TestCase):

    @staticmethod
    def test_graph():
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
        
        g0 = g.wasGeneratedBy(e0, a0, None, "g0", {EX["fct"]: "create"})
        
        attrdict={EX["fct"]: "load",
                  EX["typeexample"] : Literal("MyValue", EX["MyType"])}
        u0 = g.used(a0, e1, None, "u0", attrdict)
        
        # The id for a relation is an optional argument, The system will generate one
        # if you do not specify it 
        g.wasDerivedFrom(e0, e1, a0, g0, u0)
    
        return g
    
    @staticmethod
    def w3c_publication_1():
        # prefix ex  <http://example.org/>
        ex = Namespace('ex', 'http://example.org/')
        # prefix w3  <http://www.w3.org/>
        w3 = Namespace('w3', 'http://www.w3.org/')
        # prefix tr  <http://www.w3.org/TR/2011/>
        tr = Namespace('tr', 'http://www.w3.org/TR/2011/')
        #prefix pr  <http://www.w3.org/2005/10/Process-20051014/tr.html#>
        pr = Namespace('pr', 'http://www.w3.org/2005/10/Process-20051014/tr.html#')
        
        #prefix ar1 <https://lists.w3.org/Archives/Member/chairs/2011OctDec/>
        ar1 = Namespace('ar1', 'https://lists.w3.org/Archives/Member/chairs/2011OctDec/')
        #prefix ar2 <https://lists.w3.org/Archives/Member/w3c-archive/2011Oct/>
        ar2 = Namespace('ar3', 'https://lists.w3.org/Archives/Member/w3c-archive/2011Oct/')
        #prefix ar3 <https://lists.w3.org/Archives/Member/w3c-archive/2011Dec/>
        ar3 = Namespace('ar2', 'https://lists.w3.org/Archives/Member/w3c-archive/2011Dec/')
        
        
        g = ProvContainer()
        
        g.entity(tr['WD-prov-dm-20111018'], {PROV['type']: pr['RecsWD']})
        g.entity(tr['WD-prov-dm-20111215'], {PROV['type']: pr['RecsWD']})
        g.entity(pr['rec-advance'], {PROV['type']: PROV['Plan']})
        
        
        g.entity(ar1['0004'], {PROV['type']: Identifier("http://www.w3.org/2005/08/01-transitions.html#transreq")})
        g.entity(ar2['0141'], {PROV['type']: Identifier("http://www.w3.org/2005/08/01-transitions.html#pubreq")})
        g.entity(ar3['0111'], {PROV['type']: Identifier("http://www.w3.org/2005/08/01-transitions.html#pubreq")})
        
        
        g.wasDerivedFrom(tr['WD-prov-dm-20111215'], tr['WD-prov-dm-20111018'])
        
        
        g.activity(ex['pub1'], other_attributes={PROV['type']: "publish"})
        g.activity(ex['pub2'], other_attributes={PROV['type']: "publish"})
        
        
        g.wasGeneratedBy(tr['WD-prov-dm-20111018'], ex['pub1'])
        g.wasGeneratedBy(tr['WD-prov-dm-20111215'], ex['pub2'])
        
        g.used(ex['pub1'], ar1['0004'])
        g.used(ex['pub1'], ar2['0141'])
        g.used(ex['pub2'], ar3['0111'])
        
        g.agent(w3['Consortium'], {PROV['type']: PROV['Organization']})
        
        g.wasAssociatedWith(ex['pub1'], w3['Consortium'], pr['rec-advance'])
        g.wasAssociatedWith(ex['pub2'], w3['Consortium'], pr['rec-advance'])
    
        return g
    
    def setUp(self):
        self.prov_graph = Test.build_prov_graph()

    def tearDown(self):
        pass

    def testJSONSerialization(self):
        logging.basicConfig(level=logging.DEBUG)
        g1 = Test.w3c_publication_1()
#        g1 = Test.build_prov_graph()
        print '-------------------------------------- Original graph in ASN'
        g1.print_records()
        json_str = json.dumps(g1, cls=ProvContainer.JSONEncoder, indent=4)
#        print '-------------------------------------- Original graph in JSON'
#        print json_str
        g2 = json.loads(json_str, cls=ProvContainer.JSONDecoder)
        print '-------------------------------------- Graph decoded from JSON' 
        g2.print_records()
        assert(g1 == g2)
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
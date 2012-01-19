import json
from provpy import *


FOAF = PROVNamespace("foaf","http://xmlns.com/foaf/0.1/")
ex = PROVNamespace("ex","http://www.example.com/")
dcterms = PROVNamespace("dcterms","http://purl.org/dc/terms/")
xsd = PROVNamespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')

testns = PROVNamespace("test",'http://www.test.org/')
exns = PROVNamespace("test",'http://www.example.org/')

examplegraph = PROVContainer()
examplegraph.set_default_namespace("http://www.example.com/")

#add namespaces
#examplegraph.add_namespace("ex","http://www.example.com/")
examplegraph.add_namespace("dcterms","http://purl.org/dc/terms/")
examplegraph.add_namespace("foaf","http://xmlns.com/foaf/0.1/")
#examplegraph.add_namespace("ex","http://www.example111.com/")

# We use an entity as example
# For PROVQname amd the following 5 Python types (string, float, integer,
# boolean and datetime), you do not need to specify the data type,
# provpy will map them with the corresponding JSON or xsd type.
attrdict = {ex["PROVQname"] : ex["localname"],
            ex["string"] : "String Literal",
            ex["float"] : 3.2,
            ex["integer"] : 14,
            ex["boolean"] : True,
            ex["datetime"] : datetime.datetime(2008, 7, 6, 5, 4, 3)}
# For all other data types including application specific data types,
# You must specify the type in a PROVLiteral instance
attrdict.update({ex['language'] : PROVLiteral("EN",xsd["language"]),
                 ex['appSpecific'] : PROVLiteral("myValue",ex["myType"])})
# To give multiple values to one attribute, put the values in a
# Python list. Even the value are of the same data type, you MUST
# put them in separate PROVLiteral instances. 
attrdict.update({
                 ex['multi_values'] : [1,"value2",PROVLiteral("value3",ex["myType"])],
                 ex['languages'] : [PROVLiteral("EN",xsd["language"]),PROVLiteral("FR",xsd["language"])]
                 })
e0 = Entity(id=None,attributes=attrdict)
examplegraph.add(e0)





print json.dumps(examplegraph.to_provJSON(),indent=4)
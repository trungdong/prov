import json
from provpy import *


examplegraph = PROVContainer("http://www.defaultnamespace.com/")

#add namespaces
examplegraph.add_namespace("ex","http://www.example.com/")
examplegraph.add_namespace("dcterms","http://purl.org/dc/terms/")

# add entities
attrdict = {"type": "File",
            "ex:path": "/shared/crime.txt",
            "ex:creator": "Alice"}
e0 = Entity("e0",attrdict)
examplegraph.add(e0)
lit0 = PROVLiteral("2011-11-16T16:06:00","xsd:dateTime")
attrdict ={"type": "File",
           "ex:path": "/shared/crime.txt",
           "ex:creator": "Alice",
           "ex:content": "",
           "dcterms:create": lit0}
e1 = Entity("e1",attributes=attrdict)
examplegraph.add(e1)

# add activities
attrdict = {"recipeLink": "create-file"}
#starttime = datetime.datetime.utcnow().isoformat()
starttime = datetime.datetime(2008, 7, 6, 5, 4, 3)
a0 = Activity("a0",starttime=starttime,attributes=attrdict)
examplegraph.add(a0)

# add relation 
attrdict={"ex:fct": "create"}
g0=wasGeneratedBy(e0,a0,id="g0",time=None,attributes=attrdict)
examplegraph.add(g0)

attrdict={"ex:fct": "load",
          "ex:typeexample" : PROVLiteral("MyValue","ex:MyType")}
u0 = Used(a0,e1,id="u0",time=None,attributes=attrdict)
examplegraph.add(u0)

d0=wasDerivedFrom(e0,e1,activity=a0,generation=g0,usage=u0,attributes=None)
examplegraph.add(d0)

#add accounts
acc0 = Account("acc0","http://www.example.org/asserter",attributes={"attr01":"value01","attr02":PROVLiteral("Value02","ex:valueType02")})
#acc0.add_namespace('ex','www.example.com')
examplegraph.add(acc0)

acc0.add_entity("em")

en = examplegraph.add_entity('en',account=acc0)

print json.dumps(examplegraph.to_provJSON(),indent=4)


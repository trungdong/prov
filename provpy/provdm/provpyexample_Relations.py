import json
from provpy import *

# Define your namespaces (see provpyexample_PROVQname_PROVNamespace.py)
FOAF = PROVNamespace("foaf","http://xmlns.com/foaf/0.1/")
ex = PROVNamespace("ex","http://www.example.com/")
dcterms = PROVNamespace("dcterms","http://purl.org/dc/terms/")
xsd = PROVNamespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
prov = PROVNamespace("prov","http://www.w3.org/ns/prov-dm/")

# create a provenance container
examplegraph = PROVContainer()

# Set the default namespace name
examplegraph.set_default_namespace("http://www.example.com/")

# add the other namespaces with their prefixes into the container
# You can do this any time before you output the JSON serialization
# of the container.
# Note for each namespace name, if a prefix given here is different to the
# one carried in the PROVNamespace instance defined previously, the prefix
# HERE will be used in the JSON serialization.
examplegraph.add_namespace("dcterms","http://purl.org/dc/terms/")
examplegraph.add_namespace("foaf","http://xmlns.com/foaf/0.1/")

# add some entities that will be used by the relations
e0 = Entity()
examplegraph.add(e0)

e1 = Entity(ex['Foo'],attributes={dcterms['creator']:FOAF['Alice']})
examplegraph.add(e1)

# an activity as well
a0 = Activity(id=None,starttime=datetime.datetime(2008, 7, 6, 5, 4, 3),attributes={prov["recipeLink"]: ex["create-file"]})
examplegraph.add(a0)



# Then add some relations, using the element instances directly in the call
attrdict = {ex["fct"]: "create"}
g0 = wasGeneratedBy(e0,a0,id="g0",time=None,attributes=attrdict)
examplegraph.add(g0)

attrdict={ex["fct"]: "load",
          ex["typeexample"] : PROVLiteral("MyValue",ex["MyType"])}
u0 = Used(a0,e1,id="u0",time=None,attributes=attrdict)
examplegraph.add(u0)

# The id for a relation is an optional argument, The system will generate one
# if you do not specify it 
d0=wasDerivedFrom(e0,e1,activity=a0,generation=g0,usage=u0,attributes=None)
examplegraph.add(d0)



# You can then have the JSON of the container with the to_provJSON() function
print json.dumps(examplegraph.to_provJSON(),indent=4)

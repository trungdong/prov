import json
from provdm.model import *

# The namespace names should be defined as instances of PROVNamespace
FOAF = PROVNamespace("foaf","http://xmlns.com/foaf/0.1/")
ex = PROVNamespace("ex","http://www.example.com/")
dcterms = PROVNamespace("dcterms","http://purl.org/dc/terms/")
xsd = PROVNamespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
prov = PROVNamespace("prov","http://www.w3.org/ns/prov-dm/")

# The URIRef can then be defined using the namespace created
exuri = ex["mylocalname"]

# The URIRef will have a type of PROVQname:
print "the type of exuri is: %s" % type(exuri)

# You are able to access the full uri, its namespace name and local name
print "the full uri of exuri is: %s" % exuri.name
print "the namespace name of exuri is: %s" % exuri.namespacename
print "the local name of exuri is: %s" % exuri.localname

# You will use PROVQname for any URIRef when you use provpy lib
# to create your provenance records:

# for example, create an entity
lit0 = PROVLiteral("2011-11-16T16:06:00",xsd["dateTime"])
attrdict ={prov["type"]: ex["File"],
           ex["path"]: "/shared/crime.txt",
           dcterms["creator"]: FOAF['Alice'],
           ex["content"]: "",
           dcterms["create"]: lit0}
e1 = Entity(ex['Foo'],attributes=attrdict)

# create a container and add the entity
examplegraph = PROVContainer()
examplegraph.set_default_namespace("http://www.example.com/")
examplegraph.add_namespace("dcterms","http://purl.org/dc/terms/")
examplegraph.add_namespace("foaf","http://xmlns.com/foaf/0.1/")
examplegraph.add_namespace("ex","http://www.example111.com/")

examplegraph.add(e1)

print "An example serialization:"
print json.dumps(examplegraph.to_provJSON(),indent=4)
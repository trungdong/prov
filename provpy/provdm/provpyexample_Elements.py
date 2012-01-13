import json
from provpy import *

# Define your namespaces (see provpyexample_PROVURIRef_PROVNamespace.py)
FOAF = PROVNamespace("http://xmlns.com/foaf/0.1/")
ex = PROVNamespace("http://www.example.com/")
dcterms = PROVNamespace("http://purl.org/dc/terms/")
xsd = PROVNamespace('http://www.w3.org/2001/XMLSchema-datatypes#')
prov = PROVNamespace("http://www.w3.org/ns/prov-dm/")

# create a provenance container
examplegraph = PROVContainer()

# Set the default namespace name
examplegraph.set_default_namespace("http://www.example.com/")

# add the other namespaces with their prefixes into the container
# You can do this any time before you output the JSON serialization
# of the container
examplegraph.add_namespace("dcterms","http://purl.org/dc/terms/")
examplegraph.add_namespace("foaf","http://xmlns.com/foaf/0.1/")

# add entities, first define the attributes in a dictionary
attrdict = {"type": "File",
            ex["path"]: "/shared/crime.txt",
            ex["creator"]: "Alice"}
# then create the entity
# If you give the id as a string, it will be treated as a localname
# under the default namespace
e0 = Entity(id="e0",attributes=attrdict)
# you can then add the entity into the provenance container
examplegraph.add(e0)

# define the attributes for the next entity
lit0 = PROVLiteral("2011-11-16T16:06:00",xsd["dateTime"])
attrdict ={prov["type"]: ex["File"],
           ex["path"]: "/shared/crime.txt",
           dcterms["creator"]: FOAF['Alice'],
           ex["content"]: "",
           dcterms["create"]: lit0}
# create the entity, note this time we give the id as a PROVURIRef
e1 = Entity(FOAF['Foo'],attributes=attrdict)
examplegraph.add(e1)

# add activities
# You can give the attributes during the creation if there are not many
a0 = Activity(id=None,starttime=datetime.datetime(2008, 7, 6, 5, 4, 3),attributes={prov["recipeLink"]: ex["create-file"]})
examplegraph.add(a0)


# You can have the JSON of the container with the to_provJSON() function
# as container is also a provenance record
print json.dumps(examplegraph.to_provJSON(),indent=4)
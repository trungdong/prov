import json
from provdm.model import *


FOAF = PROVNamespace("foaf","http://xmlns.com/foaf/0.1/")
ex = PROVNamespace("ex","http://www.example.com/")
dcterms = PROVNamespace("dcterms","http://purl.org/dc/terms/")
xsd = PROVNamespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')

testns = PROVNamespace("test",'http://www.test.org/')
exns = PROVNamespace("test",'http://www.example.org/')

# create the top level container
examplegraph = PROVContainer()
examplegraph.set_default_namespace("http://www.example.com/")

#add namespaces
examplegraph.add_namespace("dcterms","http://purl.org/dc/terms/")
examplegraph.add_namespace("foaf","http://xmlns.com/foaf/0.1/")

# to add record in an account, first create the account
# identifier and asserter are required arguments for Account
# You can give optional attributes in a dictionary with keyword argument 'attributes'
acc0 = Account("acc0",ex["asserter_name"],attributes={ex['accountattr']:ex['accattrvalue']})
# You are allowed to add namespace into Account, the namespaces
# from all accounts will be merged with top level container's namespace
# definitions before exporting JSON. If two prefix clashes, on of them
# will be replaced by provpy with an automatically generated prefix only 
# in the JSON serialization.
acc0.add_namespace("ex","http://www.exampleexample.com/")

# You can now create and add records directly into the Account, as account 
# is a type of container/bundle in prov-dm
e0 = Entity(ex['Foo'],attributes={"type": "File"})
acc0.add(e0)

# You can all add record to an account by calling its add_(recordname) function
# directly:
a0 = acc0.add_activity("a0",starttime=datetime.datetime(2008, 7, 6, 5, 4, 3),attributes={"recipeLink": "create-file"})

# Don't forget to add the account to the top level container
examplegraph.add(acc0)

# Another way of adding reocrd into account is to add the record into the
# top level container with the account specified in the record's argument.
# The account MUST have been added into the container before you can do it
# this way:
g0=wasGeneratedBy(e0,a0,id="g0",time=None,attributes={ex["fct"]: "create"},account=acc0)
examplegraph.add(g0)
# or this way:
e1 = examplegraph.add_entity('e1',account=acc0)

# A nested account can be added in this way:
acc1 = Account("acc1",ex["asserter_name"])
acc0.add(acc1)

# You can then add any records to the account
acc1.add_entity('e2')

print json.dumps(examplegraph.to_provJSON(),indent=4)

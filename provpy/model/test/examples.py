from model import ProvContainer, Namespace, Literal, PROV, XSD, Identifier
import datetime

def example_graph():
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

def primer_graph():
    #prefix ex <http://example/>
    ex = Namespace('ex', 'http://example/')
    
    g = ProvContainer()
    g.add_namespace(Namespace("dcterms","http://purl.org/dc/terms/"))
    
    #entity(ex:article, [dcterms:title="Crime rises in cities"])
    g.entity(ex['article'], {'dcterms:title': "Crime rises in cities"})
    #entity(ex:dataSet1)
    g.entity(ex['dataSet1'])
    #entity(ex:dataSet2)
    g.entity(ex['dataSet2'])
    #entity(ex:regionList)
    g.entity(ex['regionList'])
    #entity(ex:composition)
    g.entity(ex['composition'])
    #entity(ex:chart1)
    g.entity(ex['chart1'])
    #entity(ex:chart2)
    g.entity(ex['chart2'])

    #activity(ex:compile)
    g.activity(ex['compile'])
    #activity(ex:compose)
    g.activity(ex['compose'])
    #activity(ex:illustrate)
    g.activity(ex['illustrate'])

    #used(ex:compose, ex:dataSet1, -)
    g.used(ex['compose'], ex['dataSet1'])
    #used(ex:compose, ex:regionList, -)
    g.used(ex['compose'], ex['regionList'])
    #wasGeneratedBy(ex:composition, ex:compose, -)
    g.wasGeneratedBy('ex:composition', 'ex:compose')
    
    #used(ex:illustrate, ex:composition, -)
    g.used('ex:illustrate', 'ex:composition')
    #wasGeneratedBy(ex:chart1, ex:illustrate, -)
    g.wasGeneratedBy('ex:chart1', 'ex:illustrate')
    #
    #
    #agent(ex:derek, [ prov:type="prov:Person", foaf:givenName = "Derek", 
    #       foaf:mbox= "<mailto:derek@example.org>"])
    g.agent('ex:derek', {'prov:type': "prov:Person", 'foaf:givenName': "Derek", 'foaf:mbox': "<mailto:derek@example.org>"})
    #wasAssociatedWith(ex:compose, ex:derek, -)
    g.wasAssociatedWith('ex:compose', 'ex:derek')
    #wasAssociatedWith(ex:illustrate, ex:derek, -)
    g.wasAssociatedWith('ex:illustrate', 'ex:derek')
    
    # agent(ex:chartgen, [ prov:type="prov:Organization", foaf:name = "Chart Generators Inc"])
    g.agent('ex:chartgen', {'prov:type': "prov:Organization", 'foaf:name' : "Chart Generators Inc"})
    # actedOnBehalfOf(ex:derek, ex:chartgen, ex:compose)
    g.actedOnBehalfOf('ex:derek', 'ex:chartgen', 'ex:compose')
    # wasAttributedTo(ex:chart1, ex:derek)
    g.wasAttributedTo('ex:chart1', 'ex:derek')

    # used(ex:compose, ex:dataSet1, -,   [ prov:role = "ex:dataToCompose"])
    g.used('ex:compose', 'ex:dataSet1', other_attributes={'prov:role' : "ex:dataToCompose"})
    # used(ex:compose, ex:regionList, -, [ prov:role = "ex:regionsToAggregteBy"])
    g.used('ex:compose', 'ex:regionList', other_attributes={'prov:role' : "ex:regionsToAggregteBy"})

    # wasRevisionOf(ex:dataSet2, ex:dataSet1, -)
    g.wasRevisionOf('ex:dataSet2', 'ex:dataSet1')
    # wasDerivedFrom(ex:chart2, ex:dataSet2)
    g.wasDerivedFrom('ex:chart2', 'ex:dataSet2')
    
    return g
    
def w3c_publication_1():
    # prefix ex  <http://example.org/>
    ex = Namespace('ex', 'http://example.org/')
    # prefix w3  <http://www.w3.org/>
    w3 = Namespace('w3', 'http://www.w3.org/')
    # prefix tr  <http://www.w3.org/TR/2011/>
    tr = Namespace('tr', 'http://www.w3.org/TR/2011/')
    # prefix process <http://www.w3.org/2005/10/Process-20051014/tr.html#>
    process = Namespace('process', 'http://www.w3.org/2005/10/Process-20051014/tr.html#')
    # prefix email   <https://lists.w3.org/Archives/Member/w3c-archive/>
    email = Namespace('email', 'https://lists.w3.org/Archives/Member/w3c-archive/')
    # prefix chairs  <https://lists.w3.org/Archives/Member/chairs/>
    chairs = Namespace('chairs', 'https://lists.w3.org/Archives/Member/chairs/')
    # prefix trans   <http://www.w3.org/2005/08/01-transitions.html#>
    trans = Namespace('trans', 'http://www.w3.org/2005/08/01-transitions.html#')
    
    g = ProvContainer()
    g.add_namespace(ex)
    g.add_namespace(w3)
    g.add_namespace(tr)
    g.add_namespace(process)
    g.add_namespace(email)
    g.add_namespace(chairs)
    g.add_namespace(trans)

    # entity(tr:WD-prov-dm-20111018, [ prov:type='process:RecsWD' ])
    g.entity('tr:WD-prov-dm-20111018', {'prov:type': 'process:RecsWD'})
    # entity(tr:WD-prov-dm-20111215, [ prov:type='process:RecsWD' ])
    g.entity('tr:WD-prov-dm-20111215', {'prov:type': 'process:RecsWD'})
    # entity(process:rec-advance,    [ prov:type='prov:Plan' ])
    g.entity('process:rec-advance',    {'prov:type': 'prov:Plan'})

    # entity(chairs:2011OctDec/0004, [ prov:type='trans:transreq' ])
    g.entity('chairs:2011OctDec/0004', {'prov:type': 'trans:transreq'})
    # entity(email:2011Oct/0141,     [ prov:type='trans:pubreq' ])
    g.entity('email:2011Oct/0141', {'prov:type': 'trans:pubreq'})
    # entity(email:2011Dec/0111,     [ prov:type='trans:pubreq' ])
    g.entity('email:2011Dec/0111', {'prov:type': 'trans:pubreq'})

    # wasDerivedFrom(tr:WD-prov-dm-20111215,tr:WD-prov-dm-20111018)
    g.wasDerivedFrom('tr:WD-prov-dm-20111215', 'tr:WD-prov-dm-20111018')

    # activity(ex:act1,-,-,[prov:type="publish"])
    g.activity('ex:act1', other_attributes={'prov:type': "publish"})
    # activity(ex:act2,-,-,[prov:type="publish"])
    g.activity('ex:act2', other_attributes={'prov:type': "publish"})

    # wasGeneratedBy(tr:WD-prov-dm-20111018, ex:act1, -)
    g.wasGeneratedBy('tr:WD-prov-dm-20111018', 'ex:act1')
    # wasGeneratedBy(tr:WD-prov-dm-20111215, ex:act2, -)
    g.wasGeneratedBy('tr:WD-prov-dm-20111215', 'ex:act2')

    # used(ex:act1,chairs:2011OctDec/0004,-)
    g.used('ex:act1', 'chairs:2011OctDec/0004')
    # used(ex:act1,email:2011Oct/0141,-)
    g.used('ex:act1', 'email:2011Oct/0141')
    # used(ex:act2,email:2011Dec/0111,-)
    g.used('ex:act2', 'email:2011Dec/0111')

    # agent(w3:Consortium, [ prov:type="Organization" ])
    g.agent('w3:Consortium', other_attributes= {'prov:type': "Organization"})

    # wasAssociatedWith(ex:act1, w3:Consortium, process:rec-advance)
    g.wasAssociatedWith('ex:act1', 'w3:Consortium', 'process:rec-advance')
    # wasAssociatedWith(ex:act2, w3:Consortium, process:rec-advance)
    g.wasAssociatedWith('ex:act2', 'w3:Consortium', 'process:rec-advance')
    

    return g

def w3c_publication_2():
    #prefix ex <http://example.org/>
    ex = Namespace('ex', 'http://example.org/')
    #prefix rec <http://example.org/record>
    rec = Namespace('rec', 'http://example.org/record')
    #prefix w3 <http://www.w3.org/TR/2011/>
    w3 = Namespace('w3', 'http://www.w3.org/TR/2011/')
    #prefix hg <http://dvcs.w3.org/hg/prov/raw-file/9628aaff6e20/model/releases/WD-prov-dm-20111215/>
    hg = Namespace('hg', 'http://dvcs.w3.org/hg/prov/raw-file/9628aaff6e20/model/releases/WD-prov-dm-20111215/')
    
    
    g = ProvContainer()
    
    # entity(hg:Overview.html, [ prov:type="file in hg" ])
    g.entity(hg['Overview.html'], {'prov:type': "file in hg"})
    # entity(w3:WD-prov-dm-20111215, [ prov:type="html4" ])
    g.entity(w3['WD-prov-dm-20111215'], {'prov:type': "html4"})

    # activity(ex:rcp,-,-,[prov:type="copy directory"])
    g.activity(ex['rcp'], None, None, {'prov:type': "copy directory"})

    # wasGeneratedBy(rec:g,w3:WD-prov-dm-20111215, ex:rcp, -)
    g.wasGeneratedBy('w3:WD-prov-dm-20111215', 'ex:rcp', identifier=rec['g'])

    # entity(ex:req3, [ prov:type="http://www.w3.org/2005/08/01-transitions.html#pubreq" %% xsd:anyURI ])
    g.entity('ex:req3', {'prov:type': Identifier("http://www.w3.org/2005/08/01-transitions.html#pubreq")})
    
    # used(rec:u, ex:rcp,hg:Overview.html,-)
    g.used('ex:rcp', 'hg:Overview.html', identifier='rec:u')
    # used(ex:rcp,ex:req3,-)
    g.used('ex:rcp', 'ex:req3')
    #
    # wasDerivedFrom(w3:WD-prov-dm-20111215,hg:Overview.html, ex:rcp, rec:g, rec:u)
    g.wasDerivedFrom('w3:WD-prov-dm-20111215', 'hg:Overview.html', 'ex:rcp', 'rec:g', 'rec:u')

    # agent(ex:webmaster, [ prov:type="Person" ])
    g.agent('ex:webmaster', {'prov:type': "Person"})

    # wasAssociatedWith(ex:rcp, ex:webmaster, -)
    g.wasAssociatedWith('ex:rcp', 'ex:webmaster')
        
    return g

tests = [
    ('Primer', primer_graph),
    ('W3C Publication 1', w3c_publication_1),
    ('W3C Publication 2', w3c_publication_2)
]
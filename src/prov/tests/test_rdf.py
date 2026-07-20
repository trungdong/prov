"""RDF serializer-specific tests.

The shared statement/attribute/qname/example round-trips run through the
pytest-native ``fmt`` matrix (see ``conftest.py`` and the ``test_statements``/
``test_attributes``/``test_qnames``/``test_examples`` modules); this file keeps
only the genuinely RDF-specific cases.
"""

import logging
import os
import struct
from glob import glob
from io import BytesIO, StringIO

import pytest
import rdflib as rl
from rdflib import RDF, URIRef
from rdflib.compare import graph_diff
from rdflib.graph import Dataset, Graph

import prov.model as pm
from prov.model import ProvDocument
from prov.serializers.provrdf import (
    ProvRDFException,
    ProvRDFSerializer,
    literal_rdf_representation,
)
from prov.tests.conftest import roundtrip_document

logger = logging.getLogger(__name__)


def _as_triple_graph(g):
    # rdflib.compare.graph_diff() (via _TripleCanonicalizer) iterates its
    # inputs expecting triples; Dataset.__iter__ always yields quads (its
    # predecessor's __iter__ yielded the default_union's triples instead),
    # so flatten to a plain Graph holding the union of all of g's triples
    # across every graph/context first.
    flat = Graph()
    flat += g.triples((None, None, None))
    return flat


def find_diff(g_rdf, g0_rdf):
    graphs_equal = True
    in_both, in_first, in_second = graph_diff(
        _as_triple_graph(g_rdf), _as_triple_graph(g0_rdf)
    )
    g1 = sorted(in_first.serialize(format="nt", encoding="utf-8").splitlines())[1:]
    g2 = sorted(in_second.serialize(format="nt", encoding="utf-8").splitlines())[1:]
    # Compare literals
    if len(g1) != len(g2):
        graphs_equal = False
    matching_indices = [[], []]
    for idx, g1_line in enumerate(g1):
        g1_stmt = next(
            iter(rl.Dataset(default_union=True).parse(BytesIO(g1_line), format="nt"))
        )
        match_found = False
        for idx2, g2_line in enumerate(g2):
            if idx2 in matching_indices[1]:
                continue
            g2_stmt = next(
                iter(
                    rl.Dataset(default_union=True).parse(BytesIO(g2_line), format="nt")
                )
            )
            try:
                all_match = all(g1_stmt[i].eq(g2_stmt[i]) for i in range(3))
            except TypeError:
                all_match = False
            if all_match:
                matching_indices[0].append(idx)
                matching_indices[1].append(idx2)
                match_found = True
                break
        if not match_found:
            graphs_equal = False
    in_first2 = rl.Dataset(default_union=True)
    for idx, g1_line in enumerate(g1):
        if idx in matching_indices[0]:
            in_both.parse(BytesIO(g1_line), format="nt")
        else:
            in_first2.parse(BytesIO(g1_line), format="nt")
    in_second2 = rl.Dataset(default_union=True)
    for idx, g2_line in enumerate(g2):
        if idx not in matching_indices[1]:
            in_second2.parse(BytesIO(g2_line), format="nt")
    return graphs_equal, in_both, in_first2, in_second2


def test_decoding_unicode_value():
    unicode_char = "\u2019"
    rdf_content = f"""
@prefix ex: <http://www.example.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    ex:unicode_char a prov:Entity ;
        rdfs:label "{unicode_char}"^^xsd:string .
"""
    prov_doc = ProvDocument.deserialize(
        content=rdf_content, format="rdf", rdf_format="turtle"
    )
    e1 = prov_doc.get_record("ex:unicode_char")[0]
    assert unicode_char in e1.get_attribute("prov:label")


def test_serialize_without_a_document_raises():
    serializer = ProvRDFSerializer(document=None)
    with pytest.raises(ProvRDFException) as ctx:
        serializer.serialize(BytesIO())
    assert "No document to serialize" in str(ctx.value)


def test_literal_rdf_representation_langtag():
    literal = pm.Literal("bonjour", langtag="fr")
    rdf_literal = literal_rdf_representation(literal)
    assert str(rdf_literal) == "bonjour"
    assert rdf_literal.language == "fr"


def test_literal_rdf_representation_base64binary():
    literal = pm.Literal("aGVsbG8=", datatype=pm.XSD["base64Binary"])
    rdf_literal = literal_rdf_representation(literal)
    assert str(rdf_literal) == "aGVsbG8="


def test_base64binary_survives_rdf_roundtrip():
    # #288: a document with a base64Binary-typed attribute round-trips through
    # RDF equal.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity(
        "ex:e1",
        {"ex:blob": pm.Literal("aGVsbG8=", datatype=pm.XSD["base64Binary"])},
    )
    assert roundtrip_document(document, "rdf") == document


def test_base64binary_decodes_to_lexical_text():
    # #288 repro: third-party-authored RDF, decode only. rdflib coerces
    # xsd:base64Binary literals to bytes in .value, and decode_rdf_representation
    # must return the base64 text, not a bytes repr.
    turtle = """
@prefix ex: <http://example.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:e1 a prov:Entity ; ex:blob "aGVsbG8="^^xsd:base64Binary .
"""
    document = ProvDocument.deserialize(
        content=turtle, format="rdf", rdf_format="turtle"
    )
    record = next(iter(document.get_records()))
    (value,) = [v for a, v in record.attributes if a.localpart == "blob"]
    assert value == pm.Literal("aGVsbG8=", datatype=pm.XSD["base64Binary"])


def test_literal_rdf_representation_double_full_precision():
    # #225: an explicitly xsd:double-typed Literal is always collapsed to a
    # plain float before it reaches a record's stored attributes (see
    # _auto_literal_conversion), so encode_rdf_representation's plain-float
    # path (exercised by test_float_precision_survives_rdf_roundtrip) is the
    # only route a document attribute takes. literal_rdf_representation's own
    # xsd:double branch is reachable only via a direct call -- e.g. a
    # Literal built by hand rather than assigned to a record -- so it is
    # exercised directly here.
    value = struct.unpack("f", struct.pack("f", 0.1))[0]
    literal = pm.Literal(repr(value), datatype=pm.XSD_DOUBLE)
    rdf_literal = literal_rdf_representation(literal)
    assert str(rdf_literal) == repr(value)
    assert rdf_literal.datatype == URIRef(pm.XSD_DOUBLE.uri)
    assert float(str(rdf_literal)) == value


def test_literal_rdf_representation_without_datatype_raises():
    with pytest.raises(ValueError):
        literal_rdf_representation(pm.Literal("no datatype, no langtag"))


def test_out_of_int32_plain_int_emits_xsd_long_ntriples():
    # #256: a plain out-of-int32 int must not be ill-typed as xsd:int.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", {"ex:big": 123456789000})
    nt = doc.serialize(format="rdf", rdf_format="nt")
    assert '"123456789000"^^<http://www.w3.org/2001/XMLSchema#long>' in nt
    assert "http://www.w3.org/2001/XMLSchema#int>" not in nt


def test_decode_xsd_qname_gyear_gyearmonth_round_trip():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity(
        "ex:e1",
        other_attributes={
            "ex:year": pm.Literal(2020, datatype=pm.XSD["gYear"]),
            "ex:yearmonth": pm.Literal("2020-05", datatype=pm.XSD["gYearMonth"]),
            "ex:qname": pm.Literal("ex:e1", datatype=pm.XSD["QName"]),
        },
    )

    ttl = doc.serialize(format="rdf", rdf_format="turtle")
    reloaded = ProvDocument.deserialize(content=ttl, format="rdf", rdf_format="turtle")
    e1 = reloaded.get_record("ex:e1")[0]

    assert {lit.value for lit in e1.get_attribute("ex:year")} == {"2020"}
    assert {lit.value for lit in e1.get_attribute("ex:yearmonth")} == {"2020-05"}
    assert {lit.value for lit in e1.get_attribute("ex:qname")} == {"ex:e1"}


def test_long_prefix_survives_turtle_serialization():
    # #96 repro (distilled): a namespace prefix with a long, unusual local
    # name must keep its own `@prefix` declaration in turtle output rather
    # than falling back to an rdflib-minted `ns1:` -- this already works as
    # of rdflib 7 plus the pre-existing bind loop in encode_container(); kept
    # here as a regression guard.
    doc = ProvDocument()
    doc.add_namespace("nidm_groupName", "http://purl.org/nidash/nidm#NIDM_0000170")
    doc.entity("nidm_groupName:group1")

    turtle = doc.serialize(format="rdf", rdf_format="turtle")

    assert "@prefix nidm_groupName:" in turtle
    assert "ns1:" not in turtle


def test_bundle_local_namespace_prefix_survives_trig_serialization():
    # #96: a namespace registered only on a bundle (not the document) must
    # still be bound into the Dataset's namespace manager, so TriG output
    # uses its declared prefix instead of an rdflib-minted `ns1:`.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    bundle = doc.bundle("ex:bundle1")
    bundle.add_namespace("bl", "http://bundlelocal.example/")
    bundle.entity("bl:e1")

    trig = doc.serialize(format="rdf", rdf_format="trig")

    assert "@prefix bl:" in trig
    assert "ns1:" not in trig


def test_bundle_local_prefix_collision_keeps_document_level_binding():
    # #96: when a bundle-local prefix collides with a document-level one
    # (same prefix string, different namespace URI), the document-level
    # binding must keep the prefix -- copying bundle namespaces into the
    # Dataset uses `override=False` and relies on rdflib's own collision
    # handling (which renames the *incoming* namespace, e.g. to `coll1:`,
    # regardless of `override`) to avoid clobbering it.
    doc = ProvDocument()
    doc.add_namespace("coll", "http://document.example/")
    bundle = doc.bundle("coll:bundle1")
    bundle.add_namespace("coll", "http://bundlelocal.example/")
    bundle.entity("coll:e1")

    trig = doc.serialize(format="rdf", rdf_format="trig")

    assert "@prefix coll: <http://document.example/> ." in trig
    assert "@prefix coll: <http://bundlelocal.example/> ." not in trig
    # rdflib's own collision handling renames the incoming (bundle-local)
    # namespace to an alternate prefix rather than dropping its binding.
    assert "@prefix coll1: <http://bundlelocal.example/> ." in trig


def test_default_namespace_survives_turtle_serialization():
    # #96: a document's default namespace (set via set_default_namespace())
    # must be bound as the empty prefix, so its terms render as `:local`
    # rather than a full IRI in turtle output.
    doc = ProvDocument()
    doc.set_default_namespace("http://default.example/")
    doc.entity("e1")

    turtle = doc.serialize(format="rdf", rdf_format="turtle")

    assert "@prefix : <http://default.example/> ." in turtle
    assert ":e1" in turtle


def test_encode_container_reuses_a_provided_container():
    # encode_container()'s `container` parameter defaults to None
    # everywhere it is called internally; passing one explicitly (as an
    # external caller might) must reuse it rather than creating a new
    # Graph.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    serializer = ProvRDFSerializer(document=doc)
    # A Dataset works here (it's a Graph subclass), but this exercises the
    # accepted-tradeoff path, not the recommended one: its .add() calls
    # surface rdflib's own internal deprecation noise (Dataset.default_context,
    # rdflib >=7.3) -- see encode_container()'s docstring. encode_document()
    # avoids this by always passing a plain Graph.
    container = Dataset(default_union=True)
    result = serializer.encode_container(doc, container=container)

    assert result is container
    assert len(list(container.triples((None, None, None)))) > 0


def test_decode_document_without_contexts_uses_plain_graph_path():
    # decode_document()'s `hasattr(content, "graphs")` branch is False
    # for a plain rdflib Graph (as opposed to a Dataset), which
    # every other test in this module parses into.
    graph = Graph()
    graph.add(
        (
            URIRef("http://example.org/e1"),
            RDF.type,
            URIRef("http://www.w3.org/ns/prov#Entity"),
        )
    )

    document = ProvDocument()
    serializer = ProvRDFSerializer()
    serializer.document = document
    serializer.decode_document(graph, document)

    assert len(document.get_records()) == 1


def test_decode_document_bundle_iri_without_registered_namespace():
    # rdflib >= 7 no longer carries bundle-graph prefix bindings into
    # TriG output, so a re-parsed document may name a bundle context by
    # an IRI matching no registered namespace; decode_document() must
    # fall back to compute_qname instead of raising ProvException.
    content = Dataset(default_union=True)
    bundle_graph = content.get_context(URIRef("http://example.org/bundle1"))
    bundle_graph.add(
        (
            URIRef("http://example.org/e1"),
            RDF.type,
            URIRef("http://www.w3.org/ns/prov#Entity"),
        )
    )

    document = ProvDocument()
    serializer = ProvRDFSerializer()
    serializer.document = document
    serializer.decode_document(content, document)

    bundles = list(document.bundles)
    assert len(bundles) == 1
    assert bundles[0].identifier.uri == "http://example.org/bundle1"
    assert len(bundles[0].get_records()) == 1


def test_decode_multi_valued_qualified_relation_produces_cartesian_product():
    # A hand-authored (non-2.x-encoder-produced) PROV-O document may
    # legally repeat a formal-attribute predicate on the same qualified-
    # relation bnode; decode_container()'s walk() helper must expand
    # that into one new_record() call per combination rather than
    # silently overwriting (docs/test-gap-checklist.md, T13 item under
    # provrdf.py: "multi-valued unique-set walking").
    turtle = """
    @prefix prov: <http://www.w3.org/ns/prov#> .
    @prefix ex: <http://example.org/> .

    ex:e1 a prov:Entity .
    ex:e2 a prov:Entity .
    ex:a1 a prov:Activity .

    _:u1 a prov:Usage ;
         prov:entity ex:e1 ;
         prov:entity ex:e2 ;
         prov:activity ex:a1 .

    ex:a1 prov:qualifiedUsage _:u1 .
    """
    doc = ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")

    usages = [r for r in doc.get_records() if r.get_type().localpart == "Usage"]
    assert len(usages) == 2
    used_entities = {
        value
        for usage in usages
        for name, value in usage.formal_attributes
        if name.localpart == "entity"
    }
    assert {str(qn) for qn in used_entities} == {"ex:e1", "ex:e2"}


def test_alternate_triple_follows_dm_argument_order():
    # #258: PROV-O maps alternateOf(alt1, alt2) to alt1 prov:alternateOf
    # alt2 (subject = first argument), matching the PROV-DM argument order.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.alternate("ex:alt1", "ex:alt2")
    buf = BytesIO()
    document.serialize(buf, format="rdf", rdf_format="nt11")
    triples = buf.getvalue().decode()
    assert "alt1> <http://www.w3.org/ns/prov#alternateOf> <" in triples
    assert triples.index("alt1>") < triples.index("alt2>")


def test_alternate_triple_round_trips():
    # #258: encode and decode must agree, so a document with alternate()
    # survives an RDF round trip. (This test is symmetric, so it cannot
    # detect a transposition that affects both encode and decode equally.)
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.alternate("ex:alt1", "ex:alt2")
    assert roundtrip_document(document, "rdf") == document


def test_decode_alternate_triple_follows_dm_argument_order():
    # #258: RDF authored by other tools with `a1 prov:alternateOf a2` must
    # decode as alternate(a1, a2), not alternate(a2, a1).
    turtle = """
    @prefix prov: <http://www.w3.org/ns/prov#> .
    @prefix ex: <http://example.org/> .

    ex:e1 a prov:Entity .
    ex:e2 a prov:Entity .
    ex:e1 prov:alternateOf ex:e2 .
    """
    doc = ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")

    alternates = [r for r in doc.get_records() if r.get_type().localpart == "Alternate"]
    assert len(alternates) == 1
    assert [str(value) for _, value in alternates[0].formal_attributes] == [
        "ex:e1",
        "ex:e2",
    ]


def test_json_to_ttl_match():
    json_files = sorted(glob(os.path.join(os.path.dirname(__file__), "json", "*.json")))

    # invalid round trip files
    skip = list(range(352, 380))

    # invalid literal set representation e.g., set((1, True))
    skip_match = [
        5,
        6,
        7,
        8,
        15,
        27,
        28,
        29,
        75,
        76,
        77,
        78,
        79,
        80,
        260,
        261,
        262,
        263,
        264,
        306,
        313,
        315,
        317,
        322,
        323,
        324,
        325,
        330,
        332,
        344,
        346,
        382,
        389,
        395,
        397,
    ]
    errors = []
    for idx, fname in enumerate(json_files):
        _, ttl_file = os.path.split(fname)
        ttl_file = os.path.join(
            os.path.dirname(__file__), "rdf", ttl_file.replace("json", "ttl")
        )
        try:
            g = pm.ProvDocument.deserialize(fname)
            format = "turtle" if len(g.bundles) == 0 else "trig"
            if format == "trig":
                ttl_file = ttl_file.replace("ttl", "trig")

            with open(ttl_file, "rb") as fp:
                g_rdf = rl.Dataset(default_union=True).parse(fp, format=format)
            g0_rdf = rl.Dataset(default_union=True).parse(
                StringIO(g.serialize(format="rdf", rdf_format=format)),
                format=format,
            )
            if idx not in skip_match:
                match, _, _in_first, _in_second = find_diff(g_rdf, g0_rdf)
                assert match
            else:
                logger.info(f"Skipping match: {fname}")
            if idx in skip:
                logger.info(f"Skipping deserialization: {fname}")
                continue
            pm.ProvDocument.deserialize(
                content=g.serialize(format="rdf", rdf_format=format),
                format="rdf",
                rdf_format=format,
            )
        except Exception as e:
            raise e
            # errors.append((e, idx, fname, in_first, in_second))
    assert not errors


def test_float_precision_survives_rdf_roundtrip():
    # 0.1 narrowed to float32 -> 0.10000000149011612; RDF now emits this at
    # full repr() precision, so it reloads as the exact same value (#225).
    value = struct.unpack("f", struct.pack("f", 0.1))[0]
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e0", {"ex:k0": value})
    assert roundtrip_document(document, "rdf") == document


def test_qualified_delegation_pair_survives_rdf_roundtrip():
    # #226: two qualified delegations sharing the same delegate and
    # qualifying activity but differing in responsible used to collapse
    # through RDF -- one lost its responsible, because the qualifiedDelegation
    # blank nodes were keyed on (delegate, activity) alone. Fixed by #250:
    # each qualifiedDelegation node now carries its own prov:agent triple, so
    # decoding can match the correct node by its actual influencer instead of
    # an ambiguous "last node seen" guess.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.agent("ex:g0")
    document.agent("ex:g1")
    document.activity("ex:a")
    document.delegation("ex:g0", "ex:g1", "ex:a")
    document.delegation("ex:g0", "ex:g0", "ex:a")
    assert roundtrip_document(document, "rdf") == document


@pytest.mark.parametrize(
    ("build", "influencer_uri"),
    [
        (
            lambda d: d.communication("ex:a2", "ex:a1", other_attributes={"ex:k": "v"}),
            "http://www.w3.org/ns/prov#activity",
        ),
        (
            lambda d: d.attribution("ex:e1", "ex:ag1", other_attributes={"ex:k": "v"}),
            "http://www.w3.org/ns/prov#agent",
        ),
        (
            lambda d: d.delegation(
                "ex:ag2", "ex:ag1", "ex:a", other_attributes={"ex:k": "v"}
            ),
            "http://www.w3.org/ns/prov#agent",
        ),
        (
            lambda d: d.influence("ex:e2", "ex:e1", other_attributes={"ex:k": "v"}),
            "http://www.w3.org/ns/prov#influencer",
        ),
    ],
    ids=["communication", "attribution", "delegation", "influence"],
)
def test_anonymous_qualified_node_carries_influencer(build, influencer_uri):
    # #250: an anonymous qualified Communication/Attribution/Delegation/
    # Influence node must carry its influencer property directly (PROV-O
    # section 3.1's qualification tables), not just imply it via the
    # shorthand binary triple, so the node is interpretable in isolation.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    build(document)
    buf = BytesIO()
    document.serialize(destination=buf, format="rdf", rdf_format="nt11")
    output = buf.getvalue()
    assert influencer_uri.encode() in output


def test_anonymous_attributions_to_different_agents_each_carry_their_own_agent():
    # #250's ambiguity repro: two anonymous, qualified (extra-attributed)
    # attributions of the same entity to *different* agents must yield two
    # distinct prov:Attribution blank nodes, each carrying its own
    # prov:agent -- not a single node whose agent is ambiguous or lost.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.attribution("ex:e1", "ex:ag1", other_attributes={"ex:k": "v1"})
    document.attribution("ex:e1", "ex:ag2", other_attributes={"ex:k": "v2"})
    buf = BytesIO()
    document.serialize(destination=buf, format="rdf", rdf_format="trig")
    buf.seek(0)
    graph = Dataset(default_union=True)
    graph.parse(buf, format="trig")

    agent_pred = URIRef("http://www.w3.org/ns/prov#agent")
    ag1 = URIRef("http://example.org/ag1")
    ag2 = URIRef("http://example.org/ag2")
    attribution_nodes = {
        stmt[0]
        for stmt in graph.triples(
            (None, RDF.type, URIRef("http://www.w3.org/ns/prov#Attribution"))
        )
    }
    assert len(attribution_nodes) == 2
    nodes_with_ag1 = {
        node for node in attribution_nodes if (node, agent_pred, ag1) in graph
    }
    nodes_with_ag2 = {
        node for node in attribution_nodes if (node, agent_pred, ag2) in graph
    }
    assert len(nodes_with_ag1) == 1
    assert len(nodes_with_ag2) == 1
    assert nodes_with_ag1 != nodes_with_ag2


def test_legacy_qualified_delegation_without_influencer_still_parses():
    # Documents produced by prov <=2.x (pre-#250) never asserted an
    # influencer property directly on an anonymous qualification node --
    # only the binary triple and (for delegation) prov:hadActivity. Such
    # legacy input must still deserialize without error. Where two legacy
    # nodes are genuinely ambiguous (same subject, no distinguishing
    # prov:agent on either), decoding falls back to the old "last node seen"
    # behaviour and -- as before #250 -- may collapse the pair; that is the
    # documented pre-existing #226 limitation for legacy input, not a crash.
    legacy_trig = """
    @prefix ex: <http://example.org/> .
    @prefix prov: <http://www.w3.org/ns/prov#> .
    {
        ex:ag2 prov:actedOnBehalfOf ex:ag1 ;
               prov:actedOnBehalfOf ex:ag2 ;
               prov:qualifiedDelegation _:b1 , _:b2 .
        _:b1 a prov:Delegation ;
             prov:hadActivity ex:a .
        _:b2 a prov:Delegation ;
             prov:hadActivity ex:a .
    }
    """
    document = ProvDocument.deserialize(
        content=legacy_trig, format="rdf", rdf_format="trig"
    )
    delegations = [
        record
        for record in document.get_records()
        if record.get_type().localpart == "Delegation"
    ]
    assert len(delegations) == 2
    # Neither bnode carries a distinguishing prov:agent, so the two
    # prov:actedOnBehalfOf triples both land on whichever qualification node
    # was last seen (the pre-#250 "last node seen" collapse): one delegation
    # ends up with a real `responsible`, the other with None. Which agent
    # (ex:ag1 or ex:ag2) survives depends on rdflib's triple iteration order
    # (hash-seed dependent), so only the shape of the collapse is asserted.
    responsible_values = [
        value for _, value in (d.formal_attributes[1] for d in delegations)
    ]
    assert responsible_values.count(None) == 1
    (survivor,) = [value for value in responsible_values if value is not None]
    assert str(survivor) in {"ex:ag1", "ex:ag2"}
    assert {
        str(value) for _, value in (d.formal_attributes[0] for d in delegations)
    } == {"ex:ag2"}
    assert {
        str(value) for _, value in (d.formal_attributes[2] for d in delegations)
    } == {"ex:a"}

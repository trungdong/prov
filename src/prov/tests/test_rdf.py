"""RDF serializer-specific tests.

The shared statement/attribute/qname/example round-trips run through the
pytest-native ``fmt`` matrix (see ``conftest.py`` and the ``test_statements``/
``test_attributes``/``test_qnames``/``test_examples`` modules); this file keeps
only the genuinely RDF-specific cases.
"""

import datetime
import logging
import os
import struct
from glob import glob
from io import BytesIO, StringIO

import pytest
import rdflib as rl
from rdflib import RDF, URIRef
from rdflib.compare import graph_diff
from rdflib.graph import ConjunctiveGraph, Dataset, Graph

import prov.model as pm
from prov.model import ProvDocument, ProvException
from prov.serializers.provrdf import (
    ProvRDFException,
    ProvRDFSerializer,
    literal_rdf_representation,
)
from prov.tests.conftest import roundtrip_document

logger = logging.getLogger(__name__)


def find_diff(g_rdf, g0_rdf):
    graphs_equal = True
    in_both, in_first, in_second = graph_diff(g_rdf, g0_rdf)
    g1 = sorted(
        line
        for line in in_first.serialize(format="nt", encoding="utf-8").splitlines()
        if line.strip()
    )
    g2 = sorted(
        line
        for line in in_second.serialize(format="nt", encoding="utf-8").splitlines()
        if line.strip()
    )
    # Compare literals
    if len(g1) != len(g2):
        graphs_equal = False
    matching_indices = [[], []]
    for idx in range(len(g1)):
        g1_stmt = next(iter(rl.ConjunctiveGraph().parse(BytesIO(g1[idx]), format="nt")))
        match_found = False
        for idx2 in range(len(g2)):
            if idx2 in matching_indices[1]:
                continue
            g2_stmt = next(
                iter(rl.ConjunctiveGraph().parse(BytesIO(g2[idx2]), format="nt"))
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
    in_first2 = rl.ConjunctiveGraph()
    for idx in range(len(g1)):
        if idx in matching_indices[0]:
            in_both.parse(BytesIO(g1[idx]), format="nt")
        else:
            in_first2.parse(BytesIO(g1[idx]), format="nt")
    in_second2 = rl.ConjunctiveGraph()
    for idx in range(len(g2)):
        if idx not in matching_indices[1]:
            in_second2.parse(BytesIO(g2[idx]), format="nt")
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


def test_literal_rdf_representation_without_datatype_raises():
    with pytest.raises(ValueError):
        literal_rdf_representation(pm.Literal("no datatype, no langtag"))


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


def test_encode_container_reuses_a_provided_container():
    # encode_container()'s `container` parameter defaults to None
    # everywhere it is called internally; passing one explicitly (as an
    # external caller might) must reuse it rather than creating a new
    # ConjunctiveGraph.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    serializer = ProvRDFSerializer(document=doc)
    container = ConjunctiveGraph()
    result = serializer.encode_container(doc, container=container)

    assert result is container
    assert len(list(container.triples((None, None, None)))) > 0


def test_decode_document_without_contexts_uses_plain_graph_path():
    # decode_document()'s `hasattr(content, "contexts")` branch is False
    # for a plain rdflib Graph (as opposed to a ConjunctiveGraph), which
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
    content = ConjunctiveGraph()
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
                g_rdf = rl.ConjunctiveGraph().parse(fp, format=format)
            g0_rdf = rl.ConjunctiveGraph().parse(
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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="#225: PROV types a Python float as xsd:float (single precision) and "
    "RDF canonicalises it to a short decimal, so a precision-carrying float32 "
    "value comes back changed (JSON/XML keep the full repr). Regression guard "
    "from the Hypothesis property tests; remove when #225 is fixed in 3.0.",
)
def test_float_precision_survives_rdf_roundtrip():
    # 0.1 narrowed to float32 -> 0.10000000149011612; RDF writes "1e-01",
    # which reloads as 0.1, so the value is lost.
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


def test_find_diff_detects_single_triple_difference():
    # #304: find_diff must report a mismatch for graphs differing by a single
    # triple. The [1:] slices that removed a leading blank line from nt
    # serialization were too aggressive: after sorted(), when the difference
    # was a single triple, the slice discarded the only real line, leaving both
    # g1 and g2 empty, and the function returned the initial graphs_equal=True.
    # Regression test for the fix: replace [1:] slices with explicit
    # blank-line filtering.

    # Case 1: Single-triple graphs with transposed subject/object
    # (genuinely differ, not just formatting)
    a = Graph().parse(
        data="@prefix ex: <http://e/> . ex:a ex:p ex:b .", format="turtle"
    )
    b = Graph().parse(
        data="@prefix ex: <http://e/> . ex:b ex:p ex:a .", format="turtle"
    )
    match, _, _, _ = find_diff(a, b)
    assert not match, (
        "Single-triple graphs with transposed subject/object should differ"
    )

    # Case 2: Two-triple graphs differing in exactly one triple
    c = Graph().parse(
        data="@prefix ex: <http://e/> . ex:a ex:p ex:b . ex:c ex:p ex:d .",
        format="turtle",
    )
    d = Graph().parse(
        data="@prefix ex: <http://e/> . ex:b ex:p ex:a . ex:c ex:p ex:d .",
        format="turtle",
    )
    match, _, _, _ = find_diff(c, d)
    assert not match, "Two-triple graphs differing in exactly one triple should differ"

    # Case 3: Identical graphs should still match (ensure fix doesn't over-correct)
    e = Graph().parse(
        data="@prefix ex: <http://e/> . ex:a ex:p ex:b .", format="turtle"
    )
    f = Graph().parse(
        data="@prefix ex: <http://e/> . ex:a ex:p ex:b .", format="turtle"
    )
    match, _, _, _ = find_diff(e, f)
    assert match, "Identical graphs should match"


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


def test_decode_qualified_start_started_at_time_lands_in_formal_time():
    # #299: some PROV-O producers put the time on a qualified prov:Start
    # node using the binary prov:startedAtTime predicate (which prov's own
    # encoder never emits for a qualified node -- it always uses
    # prov:atTime there) rather than the generic prov:atTime spelling.
    # Document equality would pass even with the bug (that is exactly why
    # it stayed invisible), so this asserts formal_attributes/extra_attributes
    # directly instead.
    turtle = """
    @prefix ex: <http://example.org/> .
    @prefix prov: <http://www.w3.org/ns/prov#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    ex:a1 a prov:Activity ;
        prov:qualifiedStart ex:n1 .

    ex:n1 a prov:Start ;
        prov:startedAtTime "2020-01-01T00:00:00"^^xsd:dateTime ;
        prov:entity ex:trig .
    """
    doc = ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")

    (start,) = [r for r in doc.get_records() if type(r).__name__ == "ProvStart"]
    formal = dict(start.formal_attributes)
    time_values = {value for name, value in formal.items() if name.localpart == "time"}
    assert time_values == {datetime.datetime(2020, 1, 1, 0, 0, 0)}
    extra_names = {str(name) for name, _value in start.extra_attributes}
    assert "prov:startTime" not in extra_names


def test_decode_qualified_end_ended_at_time_lands_in_formal_time():
    # #299, End's half of the fix above.
    turtle = """
    @prefix ex: <http://example.org/> .
    @prefix prov: <http://www.w3.org/ns/prov#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    ex:a1 a prov:Activity ;
        prov:qualifiedEnd ex:n1 .

    ex:n1 a prov:End ;
        prov:endedAtTime "2020-01-01T00:00:00"^^xsd:dateTime ;
        prov:entity ex:trig .
    """
    doc = ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")

    (end,) = [r for r in doc.get_records() if type(r).__name__ == "ProvEnd"]
    formal = dict(end.formal_attributes)
    time_values = {value for name, value in formal.items() if name.localpart == "time"}
    assert time_values == {datetime.datetime(2020, 1, 1, 0, 0, 0)}
    extra_names = {str(name) for name, _value in end.extra_attributes}
    assert "prov:endTime" not in extra_names


def test_decode_duplicated_started_at_time_on_qualified_start_raises_documented_limitation():
    # #217 guard: the #299 rewrite must not resurrect the rejected
    # permutation-decode option. Two prov:startedAtTime values on the same
    # identified qualified prov:Start node are just as irreconcilable as two
    # prov:atTime values, and must fail rather than silently fabricating two
    # same-identifier records.
    #
    # On `master`, this failure is relabelled with a friendly
    # "documented PROV-O representational limitation" message pointing at
    # conformance.md (see `_repeated_formal_attribute`/`_emit_decoded_records`
    # in `provrdf.py`). That relabelling was introduced by a separate,
    # 3.0-only commit ("Document #217 as a permanent PROV-O representational
    # limitation") that Stage 2 does not back-port, so on 2.x the same
    # duplicate-value case still raises the raw
    # `ProvRecord.add_attributes()` message. This test is adapted to assert
    # that raw message instead, while still guarding the behaviour that
    # matters here: a ProvException, not a second fabricated record.
    turtle = """
    @prefix ex: <http://example.org/> .
    @prefix prov: <http://www.w3.org/ns/prov#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    ex:a1 a prov:Activity ;
        prov:qualifiedStart ex:n1 .

    ex:n1 a prov:Start ;
        prov:entity ex:trig ;
        prov:startedAtTime "2020-01-01T00:00:00"^^xsd:dateTime,
            "2021-01-01T00:00:00"^^xsd:dateTime .
    """
    with pytest.raises(ProvException) as ctx:
        ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")

    message = str(ctx.value)
    assert "Cannot have more than one value for attribute" in message
    assert "prov:time" in message


def test_decode_qualified_start_at_time_still_lands_in_formal_time():
    # Regression: prov's own qualified-node spelling (prov:atTime, built via
    # the model API's start(..., time=...)) must keep decoding onto the
    # formal prov:time slot exactly as before the #299 rewrite.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1")
    document.activity("ex:a1")
    document.start(
        "ex:a1", "ex:e1", identifier="ex:s1", time=datetime.datetime(2020, 1, 1)
    )

    rdf = document.serialize(format="rdf")

    # Encode must be unaffected by this decode-only fix: the qualified node
    # still uses prov:atTime, never the binary prov:startedAtTime spelling.
    assert "prov:atTime" in rdf
    assert "startedAtTime" not in rdf

    decoded = ProvDocument.deserialize(content=rdf, format="rdf")
    (start,) = [r for r in decoded.get_records() if type(r).__name__ == "ProvStart"]
    formal = dict(start.formal_attributes)
    time_values = {value for name, value in formal.items() if name.localpart == "time"}
    assert time_values == {datetime.datetime(2020, 1, 1, 0, 0, 0)}


@pytest.mark.parametrize(
    "build",
    [
        lambda d: d.communication("ex:a2", "ex:a1", other_attributes={"ex:k": "v"}),
        lambda d: d.attribution("ex:e1", "ex:ag1", other_attributes={"ex:k": "v"}),
        lambda d: d.influence("ex:e2", "ex:e1", other_attributes={"ex:k": "v"}),
        lambda d: d.delegation(
            "ex:ag2", "ex:ag1", "ex:a", other_attributes={"ex:k": "v"}
        ),
    ],
    ids=["communication", "attribution", "influence", "delegation"],
)
def test_anonymous_qualified_relation_with_extra_attributes_round_trips(build):
    # #303: an anonymous (unidentified) Communication/Attribution/Influence
    # relation carrying extra attributes used to decode into TWO records --
    # one from the shorthand binary triple, one reconstructed from the
    # prov:qualified* node -- because only Delegation/Association reconciled
    # the two back into a single record. Generalised via
    # _QUALIFIED_RELATION_INFLUENCER (provrdf.py) so all four qualifiable
    # families collapse back to one record, matching what was actually
    # asserted.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    build(document)
    assert len(list(document.get_records())) == 1
    roundtripped = roundtrip_document(document, "rdf")
    assert len(list(roundtripped.get_records())) == 1
    assert roundtripped == document


@pytest.mark.parametrize(
    "build",
    [
        lambda d: d.communication(
            "ex:a2", "ex:a1", identifier="ex:c1", other_attributes={"ex:k": "v"}
        ),
        lambda d: d.attribution(
            "ex:e1", "ex:ag1", identifier="ex:att1", other_attributes={"ex:k": "v"}
        ),
        lambda d: d.influence(
            "ex:e2", "ex:e1", identifier="ex:inf1", other_attributes={"ex:k": "v"}
        ),
        lambda d: d.delegation(
            "ex:ag2",
            "ex:ag1",
            "ex:a",
            identifier="ex:del1",
            other_attributes={"ex:k": "v"},
        ),
    ],
    ids=["communication", "attribution", "influence", "delegation"],
)
def test_identified_qualified_relation_with_extra_attributes_round_trips(build):
    # Regression guard: identified relations were never affected by #303 --
    # the identifier alone is enough to reconcile the binary triple and the
    # qualified node onto one record -- and must keep round-tripping cleanly.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    build(document)
    assert len(list(document.get_records())) == 1
    roundtripped = roundtrip_document(document, "rdf")
    assert len(list(roundtripped.get_records())) == 1
    assert roundtripped == document


@pytest.mark.parametrize(
    "build",
    [
        lambda d: d.communication("ex:a2", "ex:a1"),
        lambda d: d.attribution("ex:e1", "ex:ag1"),
        lambda d: d.influence("ex:e2", "ex:e1"),
        lambda d: d.delegation("ex:ag2", "ex:ag1", "ex:a"),
    ],
    ids=["communication", "attribution", "influence", "delegation"],
)
def test_anonymous_qualified_relation_without_extra_attributes_round_trips(build):
    # Regression guard: without extra attributes, an anonymous relation of
    # these families is only ever emitted as the plain binary triple (no
    # prov:qualified* node at all), so #303 never applied to this shape --
    # confirm it still round-trips to exactly one record.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    build(document)
    assert len(list(document.get_records())) == 1
    roundtripped = roundtrip_document(document, "rdf")
    assert len(list(roundtripped.get_records())) == 1
    assert roundtripped == document


def _rdf_roundtrip(doc: ProvDocument) -> ProvDocument:
    """Serialize ``doc`` to PROV-O and deserialize it back."""
    with BytesIO() as stream:
        doc.serialize(destination=stream, format="rdf", indent=4)
        stream.seek(0)
        return ProvDocument.deserialize(source=stream, format="rdf")


# The PROV-N metacharacters (#223); a local part ending in any of these left
# rdflib's compute_qname unable to split the full IRI on decode, raising
# ``ValueError: Can't split ...`` (#294). All must now survive the round trip.
_TRAILING_METACHARS = ["=", "'", ",", ":", ";", "[", "]"]


@pytest.mark.parametrize("ch", _TRAILING_METACHARS)
def test_trailing_metacharacter_qname_round_trips(ch):
    # #294: a qualified name whose local part ends in a PROV-N metacharacter
    # serializes fine but used to raise on decode. It must round-trip, even as
    # a single record whose namespace rdflib omits from the output prefixes.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    original = doc.entity(f"ex:a{ch}").identifier

    reloaded = _rdf_roundtrip(doc)

    ids = {r.identifier for r in reloaded.get_records()}
    assert original in ids
    # Equality is URI-based: the decoded identifier carries the exact full IRI.
    decoded = next(r.identifier for r in reloaded.get_records())
    assert decoded.uri == "http://example.org/a" + ch


@pytest.mark.parametrize("ch", _TRAILING_METACHARS)
def test_inner_and_leading_metacharacter_qname_round_trips(ch):
    # Regression guard: metacharacters in inner and leading positions already
    # round-tripped and must keep doing so once trailing is fixed.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    inner = doc.entity(f"ex:a{ch}b").identifier
    leading = doc.entity(f"ex:{ch}ab").identifier

    reloaded = _rdf_roundtrip(doc)

    uris = {r.identifier.uri for r in reloaded.get_records()}
    assert inner.uri in uris
    assert leading.uri in uris


def test_unregistered_namespace_iri_decodes_via_compute_qname():
    # An ordinary IRI under no registered namespace must still decode via the
    # compute_qname minting fallback (reading RDF authored by other tools).
    turtle = """
    @prefix prov: <http://www.w3.org/ns/prov#> .
    <http://other.example/thing> a prov:Entity .
    """
    doc = ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")

    ids = {r.identifier.uri for r in doc.get_records()}
    assert "http://other.example/thing" in ids


def test_unsplittable_iri_raises_clear_error():
    # An IRI with no '#' or '/' separator genuinely cannot be split into a
    # namespace and local part; the decoder must raise a clear error naming
    # the IRI rather than letting an obscure rdflib error escape.
    serializer = ProvRDFSerializer(document=ProvDocument())
    graph = Graph()
    with pytest.raises(ValueError) as ctx:
        serializer.decode_rdf_representation(URIRef("urn:no-separator;"), graph)
    assert "urn:no-separator;" in str(ctx.value)


def test_trailing_metacharacter_encode_output_unchanged():
    # #294 is a decode-side-only fix: the encoded graph must be byte-identical
    # in content to what master produced. Compare by graph isomorphism (rdflib
    # mints random bnodes, so raw-text diff is meaningless).
    from rdflib.compare import isomorphic

    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    for ch in _TRAILING_METACHARS:
        doc.entity(f"ex:a{ch}")

    turtle = doc.serialize(format="rdf", rdf_format="turtle")
    reparsed = Graph().parse(data=turtle, format="turtle")

    expected = Graph()
    ns = "http://example.org/"
    prov = "http://www.w3.org/ns/prov#"
    for ch in _TRAILING_METACHARS:
        expected.add((URIRef(ns + "a" + ch), RDF.type, URIRef(prov + "Entity")))
    assert isomorphic(reparsed, expected)

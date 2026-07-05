import logging
import os
import unittest
from glob import glob
from io import BytesIO, StringIO

import rdflib as rl
from rdflib.compare import graph_diff

import prov.model as pm
from prov.model import ProvDocument
from prov.tests import examples
from prov.tests.test_model import (
    TestAttributesBase,
    TestQualifiedNamesBase,
    TestStatementsBase,
)
from prov.tests.utility import RoundTripTestCase

logger = logging.getLogger(__name__)


def find_diff(g_rdf, g0_rdf):
    graphs_equal = True
    in_both, in_first, in_second = graph_diff(g_rdf, g0_rdf)
    g1 = sorted(in_first.serialize(format="nt", encoding="utf-8").splitlines())[1:]
    g2 = sorted(in_second.serialize(format="nt", encoding="utf-8").splitlines())[1:]
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


class TestExamplesBase:
    """This is the base class for testing support for all the examples provided
    in prov.tests.examples.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    def test_all_examples(self):
        counter = 0
        for name, graph in examples.tests:
            if name in ["datatypes"]:
                logger.info("%d. Skipping the %s example", counter, name)
                continue
            counter += 1
            logger.info("%d. Testing the %s example", counter, name)
            g = graph()
            self.do_tests(g)


class TestJSONExamplesBase:
    """This is the base class for testing support for all the examples provided
    in prov.tests.examples.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    def test_all_examples(self):
        counter = 0
        for name, graph in examples.tests:
            if name in ["datatypes"]:
                logger.info("%d. Skipping the %s example", counter, name)
                continue
            counter += 1
            logger.info("%d. Testing the %s example", counter, name)
            g = graph()
            self.do_tests(g)


class TestStatementsBase2(TestStatementsBase):
    @unittest.expectedFailure
    def test_scruffy_end_1(self):
        TestStatementsBase.test_scruffy_end_1(self)

    @unittest.expectedFailure
    def test_scruffy_end_2(self):
        TestStatementsBase.test_scruffy_end_2(self)

    @unittest.expectedFailure
    def test_scruffy_end_3(self):
        TestStatementsBase.test_scruffy_end_3(self)

    @unittest.expectedFailure
    def test_scruffy_end_4(self):
        TestStatementsBase.test_scruffy_end_4(self)

    @unittest.expectedFailure
    def test_scruffy_generation_1(self):
        TestStatementsBase.test_scruffy_generation_1(self)

    @unittest.expectedFailure
    def test_scruffy_generation_2(self):
        TestStatementsBase.test_scruffy_generation_2(self)

    @unittest.expectedFailure
    def test_scruffy_invalidation_1(self):
        TestStatementsBase.test_scruffy_invalidation_1(self)

    @unittest.expectedFailure
    def test_scruffy_invalidation_2(self):
        TestStatementsBase.test_scruffy_invalidation_2(self)

    @unittest.expectedFailure
    def test_scruffy_start_1(self):
        TestStatementsBase.test_scruffy_start_1(self)

    @unittest.expectedFailure
    def test_scruffy_start_2(self):
        TestStatementsBase.test_scruffy_start_2(self)

    @unittest.expectedFailure
    def test_scruffy_start_3(self):
        TestStatementsBase.test_scruffy_start_3(self)

    @unittest.expectedFailure
    def test_scruffy_start_4(self):
        TestStatementsBase.test_scruffy_start_4(self)

    @unittest.expectedFailure
    def test_scruffy_usage_1(self):
        TestStatementsBase.test_scruffy_usage_1(self)

    @unittest.expectedFailure
    def test_scruffy_usage_2(self):
        TestStatementsBase.test_scruffy_usage_2(self)


class TestAttributesBase2(TestAttributesBase):
    @unittest.expectedFailure
    def test_entity_with_multiple_attribute(self):
        TestAttributesBase.test_entity_with_multiple_attribute(self)

    @unittest.expectedFailure
    def test_entity_with_multiple_value_attribute(self):
        TestAttributesBase.test_entity_with_multiple_value_attribute(self)

    @unittest.expectedFailure
    def test_entity_with_one_type_attribute_8(self):
        TestAttributesBase.test_entity_with_one_type_attribute_8(self)


class AllTestsBase(
    TestExamplesBase, TestStatementsBase2, TestQualifiedNamesBase, TestAttributesBase2
):
    """This is a test to include all available tests."""

    pass


class TestRDFSerializer(unittest.TestCase):
    def test_decoding_unicode_value(self):
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
        self.assertIn(unicode_char, e1.get_attribute("prov:label"))

    def test_serialize_without_a_document_raises(self):
        from prov.serializers.provrdf import ProvRDFException, ProvRDFSerializer

        serializer = ProvRDFSerializer(document=None)
        with self.assertRaises(ProvRDFException) as ctx:
            serializer.serialize(BytesIO())
        self.assertIn("No document to serialize", str(ctx.exception))

    def test_literal_rdf_representation_langtag(self):
        from prov.serializers.provrdf import literal_rdf_representation

        literal = pm.Literal("bonjour", langtag="fr")
        rdf_literal = literal_rdf_representation(literal)
        self.assertEqual(str(rdf_literal), "bonjour")
        self.assertEqual(rdf_literal.language, "fr")

    def test_literal_rdf_representation_base64binary(self):
        from prov.serializers.provrdf import literal_rdf_representation

        literal = pm.Literal("aGVsbG8=", datatype=pm.XSD["base64Binary"])
        rdf_literal = literal_rdf_representation(literal)
        self.assertEqual(str(rdf_literal), "aGVsbG8=")

    def test_literal_rdf_representation_without_datatype_raises(self):
        from prov.serializers.provrdf import literal_rdf_representation

        with self.assertRaises(ValueError):
            literal_rdf_representation(pm.Literal("no datatype, no langtag"))

    def test_decode_xsd_qname_gyear_gyearmonth_round_trip(self):
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
        reloaded = ProvDocument.deserialize(
            content=ttl, format="rdf", rdf_format="turtle"
        )
        e1 = reloaded.get_record("ex:e1")[0]

        self.assertEqual({lit.value for lit in e1.get_attribute("ex:year")}, {"2020"})
        self.assertEqual(
            {lit.value for lit in e1.get_attribute("ex:yearmonth")}, {"2020-05"}
        )
        self.assertEqual({lit.value for lit in e1.get_attribute("ex:qname")}, {"ex:e1"})

    def test_encode_container_reuses_a_provided_container(self):
        # encode_container()'s `container` parameter defaults to None
        # everywhere it is called internally; passing one explicitly (as an
        # external caller might) must reuse it rather than creating a new
        # ConjunctiveGraph.
        from rdflib.graph import ConjunctiveGraph

        from prov.serializers.provrdf import ProvRDFSerializer

        doc = ProvDocument()
        doc.add_namespace("ex", "http://example.org/")
        doc.entity("ex:e1")

        serializer = ProvRDFSerializer(document=doc)
        container = ConjunctiveGraph()
        result = serializer.encode_container(doc, container=container)

        self.assertIs(result, container)
        self.assertGreater(len(list(container.triples((None, None, None)))), 0)

    def test_decode_document_without_contexts_uses_plain_graph_path(self):
        # decode_document()'s `hasattr(content, "contexts")` branch is False
        # for a plain rdflib Graph (as opposed to a ConjunctiveGraph), which
        # every other test in this module parses into.
        from rdflib import RDF, URIRef
        from rdflib.graph import Graph

        from prov.serializers.provrdf import ProvRDFSerializer

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

        self.assertEqual(len(document.get_records()), 1)

    def test_decode_document_bundle_iri_without_registered_namespace(self):
        # rdflib >= 7 no longer carries bundle-graph prefix bindings into
        # TriG output, so a re-parsed document may name a bundle context by
        # an IRI matching no registered namespace; decode_document() must
        # fall back to compute_qname instead of raising ProvException.
        from rdflib import RDF, URIRef
        from rdflib.graph import ConjunctiveGraph

        from prov.serializers.provrdf import ProvRDFSerializer

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
        self.assertEqual(len(bundles), 1)
        self.assertEqual(bundles[0].identifier.uri, "http://example.org/bundle1")
        self.assertEqual(len(bundles[0].get_records()), 1)

    def test_decode_multi_valued_qualified_relation_produces_cartesian_product(self):
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
        doc = ProvDocument.deserialize(
            content=turtle, format="rdf", rdf_format="turtle"
        )

        usages = [r for r in doc.get_records() if r.get_type().localpart == "Usage"]
        self.assertEqual(len(usages), 2)
        used_entities = {
            value
            for usage in usages
            for name, value in usage.formal_attributes
            if name.localpart == "entity"
        }
        self.assertEqual({str(qn) for qn in used_entities}, {"ex:e1", "ex:e2"})

    def test_json_to_ttl_match(self):
        json_files = sorted(
            glob(os.path.join(os.path.dirname(__file__), "json", "*.json"))
        )

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
                    self.assertTrue(match)
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
        self.assertFalse(errors)


class RoundTripRDFTests(RoundTripTestCase, AllTestsBase):
    FORMAT = "rdf"


if __name__ == "__main__":
    suite = unittest.TestSuite()
    for method in dir(TestRDFSerializer):
        if method.startswith("test"):
            suite.addTest(TestRDFSerializer(method))
    unittest.TextTestRunner().run(suite)

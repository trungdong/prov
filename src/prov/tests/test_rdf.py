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

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest
from prov.model import ProvDocument
from prov.tests.utility import RoundTripTestCase
from prov.tests.test_model import (TestStatementsBase,
                                   TestAttributesBase, TestQualifiedNamesBase)
import logging
logger = logging.getLogger(__name__)

from prov.tests import examples

class TestExamplesBase(object):
    """This is the base class for testing support for all the examples provided
    in prov.tests.examples.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """
    def test_all_examples(self):
        counter = 0
        for name, graph in examples.tests:
            if name in ['datatypes']:
                logger.info('%d. Skipping the %s example', counter, name)
                continue
            counter += 1
            logger.info('%d. Testing the %s example', counter, name)
            g = graph()
            self.do_tests(g)

class TestStatementsBase2(TestStatementsBase):
    @unittest.expectedFailure
    def test_scruffy_end_1(self):
        TestStatementsBase.test_scruffy_end_1()
    @unittest.expectedFailure
    def test_scruffy_end_2(self):
        TestStatementsBase.test_scruffy_end_2()
    @unittest.expectedFailure
    def test_scruffy_end_3(self):
        TestStatementsBase.test_scruffy_end_3()
    @unittest.expectedFailure
    def test_scruffy_end_4(self):
        TestStatementsBase.test_scruffy_end_4()
    @unittest.expectedFailure
    def test_scruffy_generation_1(self):
        TestStatementsBase.test_scruffy_generation_1()
    @unittest.expectedFailure
    def test_scruffy_generation_2(self):
        TestStatementsBase.test_scruffy_generation_2()
    @unittest.expectedFailure
    def test_scruffy_invalidation_1(self):
        TestStatementsBase.test_scruffy_invalidation_1()
    @unittest.expectedFailure
    def test_scruffy_invalidation_2(self):
        TestStatementsBase.test_scruffy_invalidation_2()
    @unittest.expectedFailure
    def test_scruffy_start_1(self):
        TestStatementsBase.test_scruffy_start_1()
    @unittest.expectedFailure
    def test_scruffy_start_2(self):
        TestStatementsBase.test_scruffy_start_2()
    @unittest.expectedFailure
    def test_scruffy_start_3(self):
        TestStatementsBase.test_scruffy_start_3()
    @unittest.expectedFailure
    def test_scruffy_start_4(self):
        TestStatementsBase.test_scruffy_start_4()
    @unittest.expectedFailure
    def test_scruffy_usage_1(self):
        TestStatementsBase.test_scruffy_usage_1()
    @unittest.expectedFailure
    def test_scruffy_usage_2(self):
        TestStatementsBase.test_scruffy_usage_2()


class TestAttributesBase2(TestAttributesBase):
    @unittest.expectedFailure
    def test_entity_with_multiple_attribute(self):
        TestAttributesBase.test_entity_with_multiple_attribute()
    @unittest.expectedFailure
    def test_entity_with_multiple_value_attribute(self):
        TestAttributesBase.test_entity_with_multiple_value_attribute()
    @unittest.expectedFailure
    def test_entity_with_one_type_attribute_8(self):
        TestAttributesBase.test_entity_with_one_type_attribute_8()


class AllTestsBase(TestExamplesBase,
                   TestStatementsBase2,
                   TestQualifiedNamesBase,
                   TestAttributesBase2
                   ):
    """This is a test to include all available tests.
    """
    pass


class TestRDFSerializer(unittest.TestCase):
    def test_decoding_unicode_value(self):
        unicode_char = u'\u2019'
        rdf_content = u'''
@prefix ex: <http://www.example.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    ex:unicode_char a prov:Entity ;
        rdfs:label "%s"^^xsd:string .
''' % unicode_char
        prov_doc = ProvDocument.deserialize(content=rdf_content,
                                            format='rdf', rdf_format='turtle')
        e1 = prov_doc.get_record('ex:unicode_char')[0]
        self.assertIn(unicode_char, e1.get_attribute('prov:label'))


class RoundTripRDFTests(RoundTripTestCase, AllTestsBase):
    FORMAT = 'rdf'

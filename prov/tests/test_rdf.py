from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest
from prov.model import ProvDocument
from prov.tests.utility import RoundTripTestCase
from prov.tests.test_model import AllTestsBase

import logging
logger = logging.getLogger(__name__)


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

import unittest
from prov.model import ProvDocument
from prov.tests.utility import RoundTripTestCase
from prov.tests.test_model import AllTestsBase

import logging

logger = logging.getLogger(__name__)


class TestJSONSerializer(unittest.TestCase):
    def test_decoding_unicode_value(self):
        unicode_char = "\u2019"
        json_content = (
            """{
    "prefix": {
        "ex": "http://www.example.org"
    },
    "entity": {
        "ex:unicode_char": {
            "prov:label": "%s"
        }
    }
}"""
            % unicode_char
        )

        prov_doc = ProvDocument.deserialize(content=json_content, format="json")
        e1 = prov_doc.get_record("ex:unicode_char")[0]
        self.assertIn(unicode_char, e1.get_attribute("prov:label"))


class RoundTripJSONTests(RoundTripTestCase, AllTestsBase):
    FORMAT = "json"

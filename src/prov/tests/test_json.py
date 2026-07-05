import logging
import unittest

from prov.model import ProvDocument
from prov.serializers.provjson import ProvJSONEncoder, ProvJSONException
from prov.tests.test_model import AllTestsBase
from prov.tests.utility import RoundTripTestCase

logger = logging.getLogger(__name__)


class TestJSONSerializer(unittest.TestCase):
    def test_decoding_unicode_value(self):
        unicode_char = "\u2019"
        json_content = f"""{{
    "prefix": {{
        "ex": "http://www.example.org"
    }},
    "entity": {{
        "ex:unicode_char": {{
            "prov:label": "{unicode_char}"
        }}
    }}
}}"""

        prov_doc = ProvDocument.deserialize(content=json_content, format="json")
        e1 = prov_doc.get_record("ex:unicode_char")[0]
        self.assertIn(unicode_char, e1.get_attribute("prov:label"))

    def test_multi_valued_prov_attribute_raises(self):
        # PROV attributes (e.g. usage's prov:entity) must be single-valued;
        # a JSON list of more than one value is rejected (docs/test-gap-
        # checklist.md, T13 item under serializers/provjson.py).
        json_content = """{
    "prefix": {"ex": "http://example.org/"},
    "used": {
        "ex:u1": {
            "prov:activity": "ex:a1",
            "prov:entity": ["ex:e1", "ex:e2"]
        }
    }
}"""
        self.assertRaises(
            ProvJSONException,
            ProvDocument.deserialize,
            content=json_content,
            format="json",
        )

    def test_encoder_default_fallback_for_non_document(self):
        # ProvJSONEncoder.default() is only ever invoked by json.dump() for
        # objects it does not natively know how to encode; for anything
        # other than a ProvDocument it falls back to the base encoder.
        encoder = ProvJSONEncoder()
        self.assertEqual(encoder.default("plain string"), '"plain string"')

    def test_attribute_touched_but_never_set_is_omitted_from_json(self):
        # Accessing .label/.value auto-vivifies an empty set entry in the
        # record's attribute dict (a plain defaultdict); the encoder must
        # skip empty attribute value sets rather than emitting them.
        doc = ProvDocument()
        doc.add_namespace("ex", "http://example.org/")
        e1 = doc.entity("ex:e1")
        _ = e1.label  # touches (and auto-vivifies) the "prov:label" entry

        json_str = doc.serialize(format="json")

        self.assertNotIn("prov:label", json_str)

    def test_third_record_with_same_identifier_appends_to_existing_list(self):
        # The first duplicate-identifier record turns the container entry
        # into a singleton list; a third (or later) record with the same
        # identifier must append directly to that list without re-wrapping
        # it (docs/test-gap-checklist.md, T13 item under provjson.py).
        doc = ProvDocument()
        doc.add_namespace("ex", "http://example.org/")
        doc.activity("ex:a1", other_attributes={"ex:tag": "one"})
        doc.activity("ex:a1", other_attributes={"ex:tag": "two"})
        doc.activity("ex:a1", other_attributes={"ex:tag": "three"})

        json_str = doc.serialize(format="json")
        reloaded = ProvDocument.deserialize(content=json_str, format="json")

        self.assertEqual(len(reloaded.get_record("ex:a1")), 3)


class RoundTripJSONTests(RoundTripTestCase, AllTestsBase):
    FORMAT = "json"

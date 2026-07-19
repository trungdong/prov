"""JSON serializer-specific tests.

The shared statement/attribute/qname/example round-trips run through the
pytest-native ``fmt`` matrix (see ``conftest.py`` and the ``test_statements``/
``test_attributes``/``test_qnames``/``test_examples`` modules); this file keeps
only the genuinely JSON-specific cases.
"""

import json

import pytest

from prov.model import PROV_QUALIFIEDNAME, Literal, ProvDocument
from prov.serializers.provjson import ProvJSONEncoder, ProvJSONException


def test_decoding_unicode_value():
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
    assert unicode_char in e1.get_attribute("prov:label")


def test_multi_valued_prov_attribute_raises():
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
    with pytest.raises(ProvJSONException):
        ProvDocument.deserialize(content=json_content, format="json")


def test_encoder_default_fallback_for_non_document():
    # Pins the isolated method's contract: for anything other than a
    # ProvDocument, default() falls back to the base encoder. In the
    # real serialize() path json.dump() only ever hands default() the
    # top-level ProvDocument (everything nested is already plain
    # dicts/strings), so this branch is not reachable end-to-end today.
    encoder = ProvJSONEncoder()
    assert encoder.default("plain string") == '"plain string"'


def test_attribute_touched_but_never_set_is_omitted_from_json():
    # Accessing .label/.value auto-vivifies an empty set entry in the
    # record's attribute dict (a plain defaultdict); the encoder must
    # skip empty attribute value sets rather than emitting them.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    e1 = doc.entity("ex:e1")
    _ = e1.label  # touches (and auto-vivifies) the "prov:label" entry

    json_str = doc.serialize(format="json")

    assert "prov:label" not in json_str


def test_third_record_with_same_identifier_appends_to_existing_list():
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

    assert len(reloaded.get_record("ex:a1")) == 3


def test_qualified_name_encodes_as_xsd_qname():
    # #168: the submission's examples type QualifiedName values as xsd:QName.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {"ex:a": document.valid_qualified_name("ex:v")})
    container = json.loads(document.serialize(format="json"))
    assert container["entity"]["ex:e1"]["ex:a"] == {"$": "ex:v", "type": "xsd:QName"}


def test_legacy_prov_qualified_name_type_still_decodes():
    # 2.x emitted prov:QUALIFIED_NAME; documents in the wild must keep parsing.
    content = (
        '{"prefix": {"ex": "http://example.org/"},'
        ' "entity": {"ex:e1": {"ex:a": {"$": "ex:v", "type": "prov:QUALIFIED_NAME"}}}}'
    )
    document = ProvDocument.deserialize(content=content, format="json")
    expected = ProvDocument()
    expected.add_namespace("ex", "http://example.org/")
    expected.entity("ex:e1", {"ex:a": expected.valid_qualified_name("ex:v")})
    assert document == expected


def test_unresolvable_qualified_name_literal_stays_opaque():
    # A prov:QUALIFIED_NAME literal whose prefix has no in-scope namespace
    # cannot be resolved to a QualifiedName; it must stay an opaque Literal
    # rather than crash or silently guess a namespace (#238, #257 lock).
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {"ex:a": Literal("unknown:v", PROV_QUALIFIEDNAME)})
    content = document.serialize(format="json")
    reloaded = ProvDocument.deserialize(content=content, format="json")
    assert reloaded == document

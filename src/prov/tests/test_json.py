"""JSON serializer-specific tests.

The shared statement/attribute/qname/example round-trips run through the
pytest-native ``fmt`` matrix (see ``conftest.py`` and the ``test_statements``/
``test_attributes``/``test_qnames``/``test_examples`` modules); this file keeps
only the genuinely JSON-specific cases.
"""

import datetime
import decimal
import io
import json
import re
from collections.abc import Callable, Iterator
from typing import Any

import pytest

import prov
from prov.model import (
    Literal,
    ProvBundle,
    ProvDocument,
    ProvMembership,
)
from prov.serializers._json_common import _JSONPrefixMap
from prov.serializers.provjson import (
    ProvJSONDecoder,
    ProvJSONEncoder,
    ProvJSONException,
    decode_json_representation,
    encode_json_container,
)
from prov.serializers.provjsonld import _JSONLD_DEFAULT_KEYS
from prov.tests import examples


def test_decoding_unicode_value() -> None:
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


def test_multi_valued_prov_attribute_raises() -> None:
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


def test_encoder_default_fallback_for_non_document() -> None:
    # Pins the isolated method's contract: for anything other than a
    # ProvDocument, default() falls back to the base encoder. In the
    # real serialize() path json.dump() only ever hands default() the
    # top-level ProvDocument (everything nested is already plain
    # dicts/strings), so this branch is not reachable end-to-end today.
    encoder = ProvJSONEncoder()
    assert encoder.default("plain string") == '"plain string"'


def test_attribute_touched_but_never_set_is_omitted_from_json() -> None:
    # Accessing .label/.value auto-vivifies an empty set entry in the
    # record's attribute dict (a plain defaultdict); the encoder must
    # skip empty attribute value sets rather than emitting them.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    e1 = doc.entity("ex:e1")
    _ = e1.label  # touches (and auto-vivifies) the "prov:label" entry

    json_str = doc.serialize(format="json")

    assert "prov:label" not in json_str


def test_third_record_with_same_identifier_appends_to_existing_list() -> None:
    # The first duplicate-identifier record turns the container entry
    # into a singleton list; a third (or later) record with the same
    # identifier must append directly to that list without re-wrapping
    # it (planning/test-gap-checklist.md, T13 item under provjson.py).
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.activity("ex:a1", other_attributes={"ex:tag": "one"})
    doc.activity("ex:a1", other_attributes={"ex:tag": "two"})
    doc.activity("ex:a1", other_attributes={"ex:tag": "three"})

    json_str = doc.serialize(format="json")
    reloaded = ProvDocument.deserialize(content=json_str, format="json")

    assert len(reloaded.get_record("ex:a1")) == 3


def test_qualified_name_encodes_as_xsd_qname() -> None:
    # #168: the submission's examples type QualifiedName values as xsd:QName.
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {"ex:a": document.valid_qualified_name("ex:v")})
    container = json.loads(document.serialize(format="json"))
    assert container["entity"]["ex:e1"]["ex:a"] == {"$": "ex:v", "type": "xsd:QName"}


def test_legacy_prov_qualified_name_type_still_decodes() -> None:
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


def test_had_member_multi_entity_hack_survives_attribute_order() -> None:
    # #275 regression: the multi-entity `hadMember` hack (a JSON list of
    # more than one `prov:entity` value on a single membership record)
    # must produce one membership relation per entity regardless of
    # whether "prov:entity" or "prov:collection" comes first in the
    # record's JSON object -- key order carries no semantics in PROV-JSON
    # and json.load() preserves source order. This library's own encoder
    # always emits "prov:collection" before "prov:entity" (matching
    # ProvMembership.FORMAL_ATTRIBUTES), so a corpus built only from
    # round-tripping this library's own output can never exercise the
    # reverse order.
    json_content = """{
    "prefix": {"ex": "http://example.org/"},
    "hadMember": {
        "_:id1": {
            "prov:entity": ["ex:e1", "ex:e2"],
            "prov:collection": "ex:coll"
        }
    }
}"""
    document = ProvDocument.deserialize(content=json_content, format="json")
    memberships = list(document.get_records(ProvMembership))
    entities = {rel.get_attribute("prov:entity").pop() for rel in memberships}
    assert len(memberships) == 2
    assert {str(e) for e in entities} == {"ex:e1", "ex:e2"}


def test_equal_anonymous_relations_share_a_key_and_both_read_back() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.wasGeneratedBy("ex:e", "ex:a")
    document.wasGeneratedBy("ex:e", "ex:a")
    content = json.loads(document.serialize(format="json"))
    assert list(content["wasGeneratedBy"]) == ["_:id1"]
    reloaded = ProvDocument.deserialize(content=json.dumps(content), format="json")
    assert len(reloaded.get_records()) == 2


def _qualified_names(bundle: ProvBundle) -> Iterator[object]:
    """Every value a JSON writer passes through the prefix map for ``bundle``."""
    if bundle.identifier is not None:
        yield bundle.identifier
    for record in bundle.get_records():
        yield record.identifier
        for attr, value in record.attributes:
            yield attr
            yield value
            if isinstance(value, Literal):
                yield value.datatype


@pytest.mark.parametrize(
    "default_keys", [("default",), _JSONLD_DEFAULT_KEYS], ids=["json", "jsonld"]
)
@pytest.mark.parametrize(
    "make_doc",
    [make_doc for _, make_doc in examples.tests],
    ids=[name for name, _ in examples.tests],
)
def test_prefix_map_leaves_other_documents_unchanged(
    make_doc: Callable[[], ProvDocument], default_keys: tuple[str, ...]
) -> None:
    # The JSON writers' output differs from 3.2.2's only through the prefix
    # map: if it declares the namespaces as 3.2.2 did and writes every name as
    # str(name), the output is byte for byte the same.
    prov_doc = make_doc()
    document_map = _JSONPrefixMap(prov_doc, default_keys)
    maps = [(prov_doc, document_map)] + [
        (bundle, _JSONPrefixMap(bundle, default_keys, document_map))
        for bundle in prov_doc.bundles
    ]
    for bundle, prefix_map in maps:
        names = list(_qualified_names(bundle))
        assert [prefix_map.qname_text(name) for name in names] == [
            str(name) for name in names
        ]
        before = {ns.prefix: ns.uri for ns in bundle.get_registered_namespaces()}
        default = bundle.get_default_namespace()
        if default is not None:
            before.update(dict.fromkeys(default_keys, default.uri))
        assert list(prefix_map.prefixes.items()) == list(before.items())


def test_encode_json_container_builds_its_own_prefix_map() -> None:
    document = ProvDocument()
    document.set_default_namespace("http://d.example/")
    default = document.get_default_namespace()
    assert default is not None
    document.entity(default["a:b"])
    container = encode_json_container(document)
    assert container["prefix"] == {
        "default": "http://d.example/",
        "dn": "http://d.example/",
    }
    assert "dn:a:b" in container["entity"]


_TIME = "2012-01-01T00:00:00"
_DATETIME_OBJECT = {"$": _TIME, "type": "xsd:dateTime"}


def _json(sections: dict[str, Any]) -> str:
    """A PROV-JSON document declaring ``ex`` and holding ``sections``."""
    return json.dumps({"prefix": {"ex": "http://example.org/"}, **sections})


def _read(text: str) -> ProvDocument:
    return ProvDocument.deserialize(content=text, format="json")


_PREFIX = '"prefix": {"ex": "http://example.org/"}'


def test_caller_object_hook_still_sees_every_object() -> None:
    seen: list[dict[str, Any]] = []

    def object_hook(obj: dict[str, Any]) -> dict[str, Any]:
        seen.append(obj)
        return obj

    text = _json({"entity": {"ex:e": {"ex:k": "a"}}})
    document = prov.read(text, format="json", object_hook=object_hook)
    assert {"ex:k": "a"} in seen
    assert document == _read(text)


def test_caller_object_pairs_hook_still_sees_every_pair() -> None:
    seen: list[list[tuple[str, Any]]] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen.append(pairs)
        return dict(pairs)

    text = _json({"entity": {"ex:e": {"ex:k": "a"}}})
    _ = prov.read(text, format="json", object_pairs_hook=object_pairs_hook)
    assert [("ex:k", "a")] in seen

    seen.clear()
    repeated = f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b"}}}}}}'
    with pytest.raises(
        ProvJSONException, match=r"^the key 'ex:k' is repeated in a JSON object$"
    ):
        _ = prov.read(repeated, format="json", object_pairs_hook=object_pairs_hook)
    assert [("ex:k", "a"), ("ex:k", "b")] not in seen


def test_json_decoder_decodes_a_document() -> None:
    text = _json({"entity": {"ex:e": {"ex:k": "a"}}})
    assert json.loads(text, cls=ProvJSONDecoder) == _read(text)


_TIMES = [
    pytest.param(
        "wasGeneratedBy", {"prov:entity": "ex:e"}, "prov:time", id="generation"
    ),
    pytest.param("used", {"prov:activity": "ex:a"}, "prov:time", id="usage"),
    pytest.param(
        "wasInvalidatedBy", {"prov:entity": "ex:e"}, "prov:time", id="invalidation"
    ),
    pytest.param("wasStartedBy", {"prov:activity": "ex:a"}, "prov:time", id="start"),
    pytest.param("wasEndedBy", {"prov:activity": "ex:a"}, "prov:time", id="end"),
    pytest.param("activity", {}, "prov:startTime", id="startTime"),
    pytest.param("activity", {}, "prov:endTime", id="endTime"),
]


@pytest.mark.parametrize(("section", "attributes", "time_attr"), _TIMES)
def test_time_reads_from_a_datetime_value_object(
    section: str, attributes: dict[str, str], time_attr: str
) -> None:
    def text(time: object) -> str:
        return _json({section: {"ex:r": {**attributes, time_attr: time}}})

    document = _read(text(_DATETIME_OBJECT))
    assert document == _read(text(_TIME))
    (record,) = document.get_records()
    assert datetime.datetime(2012, 1, 1) in {value for _, value in record.attributes}


@pytest.mark.parametrize("time", ["not-a-time", "2011-11-16"])
@pytest.mark.parametrize(("section", "attributes", "time_attr"), _TIMES)
def test_bare_time_that_is_not_an_xsd_datetime_raises(
    section: str, attributes: dict[str, str], time_attr: str, time: str
) -> None:
    text = _json({section: {"ex:r": {**attributes, time_attr: time}}})
    expected = f"record 'ex:r', attribute {time_attr!r}: expected an xsd:dateTime, found {time!r}"
    with pytest.raises(ProvJSONException, match=re.escape(expected)):
        _ = ProvDocument.deserialize(content=text, format="json")


def test_had_member_entity_written_as_an_array_reads() -> None:
    def text(entity: object) -> str:
        return _json(
            {"hadMember": {"ex:r": {"prov:collection": "ex:c", "prov:entity": entity}}}
        )

    assert _read(text(["ex:e"])) == _read(text("ex:e"))


def test_had_member_array_gives_every_member_the_identifier_and_attributes() -> None:
    # #530: each record of the fan-out carries the membership's identifier and
    # attributes, as if every member were written as a membership of its own.
    def membership(entity: object) -> dict[str, object]:
        return {"prov:collection": "ex:c", "prov:entity": entity, "ex:k": "v"}

    fanned_out = _read(_json({"hadMember": {"ex:m": membership(["ex:e1", "ex:e2"])}}))
    one_each = _read(
        _json({"hadMember": {"ex:m": [membership("ex:e1"), membership("ex:e2")]}})
    )
    assert fanned_out == one_each
    assert [str(r.identifier) for r in fanned_out.get_records()] == ["ex:m", "ex:m"]


def test_had_member_array_without_a_collection_reads() -> None:
    # The fan-out took the collection from the first record and raised
    # KeyError when the membership had none.
    document = _read(
        _json({"hadMember": {"ex:m": {"prov:entity": ["ex:e1", "ex:e2"]}}})
    )
    members = [r.get_attribute("prov:entity") for r in document.get_records()]
    assert [{str(e) for e in m} for m in members] == [{"ex:e1"}, {"ex:e2"}]


def test_had_member_members_resolve_alike() -> None:
    # Every member resolves as the first one does.
    def members(entities: list[str]) -> list[set[Any]]:
        document = _read(_membership(entities))
        return [r.get_attribute("prov:entity") for r in document.get_records()]

    assert members(["ex:e1", "ex:e2"]) == members(["ex:e2", "ex:e1"])[::-1]


def test_bundle_round_trip_copies_no_document_declaration() -> None:
    # #449: the bundle's names are the document's; the writer declares
    # nothing inside the bundle and the reader registers nothing on it.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.bundle("ex:b").entity("ex:e")
    back = ProvDocument.deserialize(content=doc.serialize(format="json"), format="json")
    (bundle,) = back.bundles
    assert list(bundle.get_registered_namespaces()) == []
    assert "prefix" not in json.loads(back.serialize(format="json"))["bundle"]["ex:b"]
    assert back == doc


def test_bundle_own_prefix_stays_on_the_bundle() -> None:
    content = json.dumps(
        {
            "prefix": {"ex": "http://example.org/"},
            "bundle": {
                "ex:b1": {
                    "prefix": {"bob": "http://bob.org/"},
                    "entity": {"bob:e1": {}},
                }
            },
        }
    )
    back = ProvDocument.deserialize(content=content, format="json")
    (bundle,) = back.bundles
    assert [n.prefix for n in back.get_registered_namespaces()] == ["ex"]
    assert [n.prefix for n in bundle.get_registered_namespaces()] == ["bob"]


# A qualified name the reader rejects because it does not resolve by its
# prefix in scope (#516, #551, #599): the sections under the ex prefix and the
# message of the ProvJSONException. The reader never compacts an IRI, so a
# full IRI is the undeclared prefix 'http'. A qualified-name value object is
# one row here and every reason in test_unresolved_names.py. The other rows are
# the inputs 3.2.3 warned about (#528, #529, #531, #532, #552, #555, #597), one
# per message the reader gives.
_E = "record 'ex:e', attribute 'ex:k': "
_R = "record 'ex:r', attribute "
_M = "record 'ex:m', attribute 'prov:entity': "
_T = "record 'ex:a', attribute 'prov:startTime': "
_GENERATION = {"prov:entity": "ex:e"}
_MEMBERSHIP = {"prov:collection": "ex:c"}
_UNDECLARED = "its prefix 'zz' is not declared"
_FULL_IRI = "its prefix 'http' is not declared"
_NO_PREFIX = "it has no prefix and no default namespace is declared"


def _unresolved(position: str, text: str, reason: str) -> str:
    return f"{position}: the qualified name {text!r} does not resolve, because {reason}"


def _generation(**attributes: object) -> str:
    return _json({"wasGeneratedBy": {"ex:r": {**_GENERATION, **attributes}}})


def _membership(entity: object) -> str:
    return _json({"hadMember": {"ex:m": {**_MEMBERSHIP, "prov:entity": entity}}})


def _value(value: object) -> str:
    return _json({"entity": {"ex:e": {"ex:k": value}}})


def _time(time: object) -> str:
    return _json({"activity": {"ex:a": {"prov:startTime": time}}})


REJECTED_DOCUMENTS = [
    pytest.param(
        _json({"entity": {"http://example.org/e1": {}}}),
        _unresolved(
            "record 'http://example.org/e1'", "http://example.org/e1", _FULL_IRI
        ),
        id="record key full IRI",
    ),
    pytest.param(
        _json({"entity": {"zz:e1": {}}}),
        _unresolved("record 'zz:e1'", "zz:e1", _UNDECLARED),
        id="record key undeclared",
    ),
    pytest.param(
        _json({"wasGeneratedBy": {"g1": {"prov:entity": "ex:e"}}}),
        _unresolved("record 'g1'", "g1", _NO_PREFIX),
        id="relation key with no prefix and no default",
    ),
    pytest.param(
        _json({"bundle": {"http://example.org/b": {"entity": {"ex:e": {}}}}}),
        _unresolved("bundle 'http://example.org/b'", "http://example.org/b", _FULL_IRI),
        id="bundle key full IRI",
    ),
    pytest.param(
        _json(
            {
                "wasGeneratedBy": {
                    "ex:r": {
                        "prov:entity": "ex:e",
                        "prov:activity": "http://example.org/a",
                    }
                }
            }
        ),
        _unresolved(
            "record 'ex:r', attribute 'prov:activity'",
            "http://example.org/a",
            _FULL_IRI,
        ),
        id="formal attribute full IRI",
    ),
    pytest.param(
        _json(
            {
                "wasGeneratedBy": {
                    "ex:r": {
                        "prov:entity": "ex:e",
                        "prov:activity": "http://example.org/a b",
                    }
                }
            }
        ),
        _unresolved(
            "record 'ex:r', attribute 'prov:activity'",
            "http://example.org/a b",
            _FULL_IRI,
        ),
        id="formal attribute full IRI with a space",
    ),
    pytest.param(
        _json(
            {
                "wasGeneratedBy": {
                    "ex:r": {"prov:entity": "ex:e", "prov:activity": "zz:a"}
                }
            }
        ),
        _unresolved("record 'ex:r', attribute 'prov:activity'", "zz:a", _UNDECLARED),
        id="formal attribute undeclared",
    ),
    pytest.param(
        _json(
            {
                "hadMember": {
                    "ex:m": {
                        "prov:collection": "ex:c",
                        "prov:entity": ["ex:e1", "http://example.org/e3"],
                    }
                }
            }
        ),
        _unresolved(
            "record 'ex:m', attribute 'prov:entity'", "http://example.org/e3", _FULL_IRI
        ),
        id="member full IRI",
    ),
    pytest.param(
        _json(
            {"hadMember": {"ex:m": {"prov:collection": "ex:c", "prov:entity": "zz:a"}}}
        ),
        _unresolved("record 'ex:m', attribute 'prov:entity'", "zz:a", _UNDECLARED),
        id="member undeclared",
    ),
    pytest.param(
        _json({"entity": {"ex:e": {"http://example.org/k": "v"}}}),
        _unresolved(
            "record 'ex:e', attribute 'http://example.org/k'",
            "http://example.org/k",
            _FULL_IRI,
        ),
        id="attribute name full IRI",
    ),
    pytest.param(
        _json({"entity": {"ex:e": {"zz:k": "v"}}}),
        _unresolved("record 'ex:e', attribute 'zz:k'", "zz:k", _UNDECLARED),
        id="attribute name undeclared",
    ),
    pytest.param(
        _json(
            {
                "entity": {
                    "ex:e": {
                        "ex:k": {
                            "$": "http://example.org/x",
                            "type": "prov:QUALIFIED_NAME",
                        }
                    }
                }
            }
        ),
        _unresolved(
            "record 'ex:e', attribute 'ex:k'", "http://example.org/x", _FULL_IRI
        ),
        id="value full IRI",
    ),
    pytest.param(
        _json(
            {
                "entity": {
                    "ex:e": {
                        "ex:k": [
                            {"$": "ex:x", "type": "xsd:QName"},
                            {"$": "zz:x", "type": "xsd:QName"},
                        ]
                    }
                }
            }
        ),
        _unresolved("record 'ex:e', attribute 'ex:k'", "zz:x", _UNDECLARED),
        id="value undeclared after a declared one",
    ),
    # #532: a repeated key, with no position (Python's JSON parser reports none)
    pytest.param(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b"}}}}}}',
        "the key 'ex:k' is repeated in a JSON object",
        id="repeated attribute",
    ),
    pytest.param(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a"}}, "ex:e": {{}}}}}}',
        "the key 'ex:e' is repeated in a JSON object",
        id="repeated record",
    ),
    pytest.param(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{}}}}, "entity": {{"ex:f": {{}}}}}}',
        "the key 'entity' is repeated in a JSON object",
        id="repeated section",
    ),
    pytest.param(
        '{"prefix": {"ex": "http://other.org/", "ex": "http://example.org/"},'
        ' "entity": {"ex:e": {}}}',
        "the key 'ex' is repeated in a JSON object",
        id="repeated prefix",
    ),
    pytest.param(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": {{"$": "a", "$": "b"}}}}}}}}',
        "the key '$' is repeated in a JSON object",
        id="repeated value-object key",
    ),
    pytest.param(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b", "ex:j": 1, "ex:j": 2}}}}}}',
        "the key 'ex:k' is repeated in a JSON object",
        id="the first repeated key of an object",
    ),
    # #528: null
    pytest.param(_value(None), _E + "the value is null", id="null attribute value"),
    pytest.param(
        _value([None, "x"]), _E + "the value is null", id="null in an attribute array"
    ),
    pytest.param(
        _generation(**{"prov:activity": None}),
        _R + "'prov:activity': the value is null",
        id="null formal attribute",
    ),
    pytest.param(_membership(None), _M + "the value is null", id="null member"),
    pytest.param(
        _membership([None, "ex:e"]), _M + "the value is null", id="null in the members"
    ),
    # #597: a formal attribute or member that is not a string
    pytest.param(
        _generation(**{"prov:activity": 5}),
        _R + "'prov:activity': the value is 5, not a qualified name",
        id="formal number",
    ),
    pytest.param(
        _generation(**{"prov:activity": 1.5}),
        _R + "'prov:activity': the value is 1.5, not a qualified name",
        id="formal float",
    ),
    pytest.param(
        _generation(**{"prov:activity": True}),
        _R + "'prov:activity': the value is true, not a qualified name",
        id="formal boolean",
    ),
    pytest.param(
        _generation(**{"prov:activity": {"$": "ex:a", "type": "prov:QUALIFIED_NAME"}}),
        _R + "'prov:activity': the value is "
        '{"$": "ex:a", "type": "prov:QUALIFIED_NAME"}, not a qualified name',
        id="formal value object",
    ),
    pytest.param(
        _membership([5]),
        _M + "the value is 5, not a qualified name",
        id="member number",
    ),
    # #531: a formal attribute written as an array, of any length
    pytest.param(
        _generation(**{"prov:entity": ["ex:e"]}),
        _R + "'prov:entity': the value is written as an array",
        id="array qualified name",
    ),
    pytest.param(
        _time([_TIME]), _T + "the value is written as an array", id="array time"
    ),
    pytest.param(
        _time([_DATETIME_OBJECT]),
        _T + "the value is written as an array",
        id="array time value object",
    ),
    pytest.param(
        _json(
            {
                "hadMember": {
                    "ex:r": {"prov:collection": ["ex:c"], "prov:entity": "ex:e"}
                }
            }
        ),
        _R + "'prov:collection': the value is written as an array",
        id="array collection",
    ),
    pytest.param(
        _generation(**{"prov:activity": ["ex:a", "ex:b"]}),
        _R + "'prov:activity': the value is written as an array",
        id="array of several values",
    ),
    pytest.param(
        _generation(**{"prov:entity": []}),
        _R + "'prov:entity': the value is written as an array",
        id="empty array",
    ),
    pytest.param(
        _generation(**{"prov:activity": [[1]]}),
        _R + "'prov:activity': the value is written as an array",
        id="nested array",
    ),
    pytest.param(
        _json({"hadMember": {"ex:r": {**_MEMBERSHIP, "prov:entity": []}}}),
        _R + "'prov:entity': the value is an empty array",
        id="empty members",
    ),
    # #529 and #552: a value object
    pytest.param(
        _value({"$": "1", "datatype": "xsd:int"}),
        _E + "the value object has the unknown key 'datatype'",
        id="unknown key",
    ),
    pytest.param(
        _value({"$": "1", "b": "x", "a": "x"}),
        _E + "the value object has the unknown key 'a'",
        id="the first unknown key",
    ),
    pytest.param(
        _value({"$": 1}), _E + 'the value object\'s "$" is 1, not a string', id="number"
    ),
    pytest.param(
        _value({"$": 1, "type": "xsd:double"}),
        _E + 'the value object\'s "$" is 1, not a string',
        id="integer typed double",
    ),
    pytest.param(
        _value({"$": 1.5, "type": "xsd:int"}),
        _E + 'the value object\'s "$" is 1.5, not a string',
        id="float typed int",
    ),
    pytest.param(
        _value({"$": True, "type": "xsd:int"}),
        _E + 'the value object\'s "$" is true, not a string',
        id="boolean typed int",
    ),
    pytest.param(
        _value({"$": 1, "type": "xsd:int", "lang": "en"}),
        _E + 'the value object\'s "$" is 1, not a string',
        id="typed number with lang",
    ),
    pytest.param(
        _value({"$": True}),
        _E + 'the value object\'s "$" is true, not a string',
        id="boolean",
    ),
    pytest.param(
        _value({"$": None}),
        _E + 'the value object\'s "$" is null, not a string',
        id="null $",
    ),
    pytest.param(
        _value({"$": 1, "type": "xsd:QName"}),
        _E + 'the value object\'s "$" is 1, not a string',
        id="number typed QName",
    ),
    pytest.param(
        _value({"$": "1", "type": "foo:int"}),
        _E
        + "the qualified name 'foo:int' does not resolve, because its prefix 'foo' is not declared",
        id="undeclared datatype",
    ),
    pytest.param(
        _value({"$": "1", "type": "foo:int", "lang": "en"}),
        _E
        + "the qualified name 'foo:int' does not resolve, because its prefix 'foo' is not declared",
        id="undeclared datatype with lang",
    ),
    pytest.param(
        _value({"$": "1", "type": "http://www.w3.org/2001/XMLSchema#int"}),
        _E
        + "the qualified name 'http://www.w3.org/2001/XMLSchema#int' does not resolve, "
        "because its prefix 'http' is not declared",
        id="full IRI datatype",
    ),
    pytest.param(
        _value({"$": "1", "type": 5}),
        _E + 'the value object\'s "type" is 5, not a string',
        id="datatype not a string",
    ),
    pytest.param(
        _value({"$": 1, "type": "foo:int", "x": 1}),
        _E + "the value object has the unknown key 'x'",
        id="unknown key before the datatype",
    ),
    pytest.param(
        _value({"$": 1, "type": "foo:int"}),
        _E
        + "the qualified name 'foo:int' does not resolve, because its prefix 'foo' is not declared",
        id="datatype before $",
    ),
    # #555 and the value-object rules at a time position
    pytest.param(
        _time({"$": "not-a-time", "type": "xsd:dateTime"}),
        _T
        + "expected an xsd:dateTime, found "
        + repr({"$": "not-a-time", "type": "xsd:dateTime"}),
        id="time ill-formed",
    ),
    pytest.param(
        _time({"$": _TIME, "type": "xsd:string"}),
        _T
        + "expected an xsd:dateTime, found "
        + repr({"$": _TIME, "type": "xsd:string"}),
        id="time other datatype",
    ),
    pytest.param(
        _time({"$": _TIME, "type": "foo:dateTime"}),
        _T
        + "the qualified name 'foo:dateTime' does not resolve, because its prefix 'foo' is not declared",
        id="time undeclared datatype",
    ),
    pytest.param(
        _time({"$": _TIME}),
        _T + "expected an xsd:dateTime, found " + repr({"$": _TIME}),
        id="time no datatype",
    ),
    pytest.param(
        _time({"$": _TIME, "type": "xsd:dateTime", "lang": "en"}),
        _T
        + "expected an xsd:dateTime, found "
        + repr({"$": _TIME, "type": "xsd:dateTime", "lang": "en"}),
        id="time with lang",
    ),
    pytest.param(
        _time({"$": 2012, "type": "xsd:dateTime"}),
        _T + 'the value object\'s "$" is 2012, not a string',
        id="time number $",
    ),
    pytest.param(
        _time({"$": _TIME, "type": 5}),
        _T + 'the value object\'s "type" is 5, not a string',
        id="time datatype not a string",
    ),
    pytest.param(_time(None), _T + "the value is null", id="time null"),
    pytest.param(
        _time(5), _T + "expected an xsd:dateTime, found 5", id="time bare number"
    ),
]


@pytest.mark.parametrize(("text", "message"), REJECTED_DOCUMENTS)
def test_reader_rejects(text: str, message: str) -> None:
    with pytest.raises(ProvJSONException) as ctx:
        _ = ProvDocument.deserialize(content=text, format="json")
    assert str(ctx.value) == message


@pytest.mark.parametrize(
    ("value", "same_as"),
    [
        pytest.param(
            {"$": 1, "type": "xsd:int"}, {"$": "1", "type": "xsd:int"}, id="int"
        ),
        pytest.param(
            {"$": 1.5, "type": "xsd:double"},
            {"$": "1.5", "type": "xsd:double"},
            id="double",
        ),
        pytest.param(
            {"$": 1, "type": "xsd:long"}, {"$": "1", "type": "xsd:long"}, id="long"
        ),
        pytest.param(
            {"$": 3000000000, "type": "xsd:int"},
            {"$": "3000000000", "type": "xsd:int"},
            id="int-beyond-the-xsd-int-range",
        ),
        pytest.param(
            {"$": 1e20, "type": "xsd:double"},
            {"$": "1e+20", "type": "xsd:double"},
            id="double-with-exponent",
        ),
    ],
)
def test_value_object_number_as_prov_2_wrote_it_reads(
    value: dict[str, object], same_as: dict[str, str]
) -> None:
    # prov 2.x and earlier wrote an int as xsd:int and a float as xsd:double,
    # and prov 1.x on Python 2 wrote a long as xsd:long.
    text = _json({"entity": {"ex:e": {"ex:k": value}}})
    expected = _json({"entity": {"ex:e": {"ex:k": same_as}}})
    assert _read(text) == _read(expected)


def test_value_object_number_parsed_as_a_decimal_is_rejected() -> None:
    expected = (
        "record 'ex:e', attribute 'ex:k': the value object's \"$\" is 1.5, not a string"
    )
    with pytest.raises(ProvJSONException, match=re.escape(expected)):
        _ = prov.read(
            io.StringIO(_value({"$": 1.5})), format="json", parse_float=decimal.Decimal
        )


def test_value_object_keys_a_caller_hook_makes_non_strings_are_rejected() -> None:
    def hook(pairs: list[tuple[str, Any]]) -> dict[Any, Any]:
        return {int(k) if k.isdigit() else k: v for k, v in pairs}

    text = _value({"$": "1", "2": "x", "a": "y"})
    expected = "record 'ex:e', attribute 'ex:k': the value object has the unknown key 2"
    with pytest.raises(ProvJSONException, match=re.escape(expected)):
        _ = prov.read(io.StringIO(text), format="json", object_pairs_hook=hook)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("1", id="string"),
        pytest.param({"$": "1"}, id="untyped"),
        pytest.param({"$": "1", "type": "xsd:int"}, id="typed"),
        pytest.param({"$": "1", "lang": "en"}, id="tagged"),
        pytest.param({"$": "ex:v", "type": "xsd:QName"}, id="qualified-name"),
        pytest.param({"$": "http://example.org/", "type": "xsd:anyURI"}, id="uri"),
        pytest.param(["1", {"$": "2", "type": "xsd:int"}], id="array"),
    ],
)
def test_well_formed_attribute_value_reads(value: object) -> None:
    _read(_json({"entity": {"ex:e": {"ex:k": value}}}))


def test_value_object_error_without_a_position() -> None:
    with pytest.raises(
        ProvJSONException, match=r"^the value object has the unknown key 'x'$"
    ):
        _ = decode_json_representation({"$": "1", "x": "y"}, ProvDocument())

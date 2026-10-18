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
import warnings
from collections.abc import Iterator
from typing import Any

import pytest

import prov
from prov.model import (
    PROV_QUALIFIEDNAME,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvFutureRejectionWarning,
    ProvMembership,
)
from prov.serializers.provjson import (
    ProvJSONDecoder,
    ProvJSONEncoder,
    ProvJSONException,
    _JSONPrefixMap,
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


def test_unresolvable_qualified_name_literal_stays_opaque() -> None:
    # A prov:QUALIFIED_NAME literal whose prefix has no in-scope namespace
    # cannot be resolved to a QualifiedName; it must stay an opaque Literal
    # rather than crash or silently guess a namespace (#238, #257 lock).
    # Asserting it and reading it back each warn, as 3.3.0 rejects it (#516).
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    with pytest.warns(ProvFutureRejectionWarning, match="'unknown:v' of ex:a"):
        document.entity("ex:e1", {"ex:a": Literal("unknown:v", PROV_QUALIFIEDNAME)})
    content = document.serialize(format="json")
    with pytest.warns(ProvFutureRejectionWarning, match="'unknown:v'"):
        reloaded = ProvDocument.deserialize(content=content, format="json")
    assert reloaded == document


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
def test_prefix_map_leaves_other_documents_unchanged(make_doc, default_keys) -> None:
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
    document.entity(document.get_default_namespace()["a:b"])
    container = encode_json_container(document)
    assert container["prefix"] == {
        "default": "http://d.example/",
        "dn": "http://d.example/",
    }
    assert "dn:a:b" in container["entity"]


# The 3.2.3 reader warnings. Each one names an input 3.3.0 rejects, and the
# document still reads as it did before 3.2.3.

_TIME = "2012-01-01T00:00:00"
_DATETIME_OBJECT = {"$": _TIME, "type": "xsd:dateTime"}


def _json(sections: dict[str, Any]) -> str:
    """A PROV-JSON document declaring ``ex`` and holding ``sections``."""
    return json.dumps({"prefix": {"ex": "http://example.org/"}, **sections})


def _read_quietly(text: str) -> ProvDocument:
    """Read ``text``, failing on any ProvFutureRejectionWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        return ProvDocument.deserialize(content=text, format="json")


def _read_warning(text: str) -> tuple[ProvDocument, list[str]]:
    """Read ``text``; return the document and its ProvFutureRejectionWarning
    messages, each of which must name this file as the caller."""
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        document = ProvDocument.deserialize(content=text, format="json")
    future = [w for w in caught if w.category is ProvFutureRejectionWarning]
    assert [w.filename for w in future] == [__file__] * len(future)
    return document, [str(w.message) for w in future]


def _rejected(detail: str, issue: int) -> str:
    return f"{detail}. prov 3.3.0 will reject this (#{issue})"


_PREFIX = '"prefix": {"ex": "http://example.org/"}'


@pytest.mark.parametrize(
    ("repeated", "single", "key"),
    [
        pytest.param(
            f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b"}}}}}}',
            f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "b"}}}}}}',
            "ex:k",
            id="attribute",
        ),
        pytest.param(
            f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a"}}, "ex:e": {{}}}}}}',
            f'{{{_PREFIX}, "entity": {{"ex:e": {{}}}}}}',
            "ex:e",
            id="record",
        ),
        pytest.param(
            f'{{{_PREFIX}, "entity": {{"ex:e": {{}}}}, "entity": {{"ex:f": {{}}}}}}',
            f'{{{_PREFIX}, "entity": {{"ex:f": {{}}}}}}',
            "entity",
            id="section",
        ),
        pytest.param(
            '{"prefix": {"ex": "http://other.org/", "ex": "http://example.org/"},'
            ' "entity": {"ex:e": {}}}',
            f'{{{_PREFIX}, "entity": {{"ex:e": {{}}}}}}',
            "ex",
            id="prefix",
        ),
        pytest.param(
            f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": {{"$": "a", "$": "b"}}}}}}}}',
            f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": {{"$": "b"}}}}}}}}',
            "$",
            id="value-object",
        ),
    ],
)
def test_repeated_key_warns(repeated: str, single: str, key: str) -> None:
    document, messages = _read_warning(repeated)
    assert messages == [
        _rejected(
            f"the key {key!r} is repeated in a JSON object; the last value is used",
            532,
        )
    ]
    assert document == _read_quietly(single)


def test_repeated_key_warns_once_per_object() -> None:
    _, messages = _read_warning(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b", "ex:k": "c"}},'
        ' "ex:f": {"ex:k": "a", "ex:k": "b"}}}'
    )
    message = _rejected(
        "the key 'ex:k' is repeated in a JSON object; the last value is used", 532
    )
    assert messages == [message, message]


def test_caller_object_hook_still_sees_every_object() -> None:
    seen: list[dict[str, Any]] = []

    def object_hook(obj: dict[str, Any]) -> dict[str, Any]:
        seen.append(obj)
        return obj

    text = f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b"}}}}}}'
    with pytest.warns(ProvFutureRejectionWarning, match="'ex:k' is repeated"):
        document = prov.read(text, format="json", object_hook=object_hook)
    assert {"ex:k": "b"} in seen
    assert document == _read_quietly(
        f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "b"}}}}}}'
    )


def test_caller_object_pairs_hook_still_sees_every_pair() -> None:
    seen: list[list[tuple[str, Any]]] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen.append(pairs)
        return dict(pairs)

    text = f'{{{_PREFIX}, "entity": {{"ex:e": {{"ex:k": "a", "ex:k": "b"}}}}}}'
    with pytest.warns(ProvFutureRejectionWarning, match="'ex:k' is repeated"):
        prov.read(text, format="json", object_pairs_hook=object_pairs_hook)
    assert [("ex:k", "a"), ("ex:k", "b")] in seen


def test_json_decoder_decodes_a_document() -> None:
    text = _json({"entity": {"ex:e": {"ex:k": "a"}}})
    assert json.loads(text, cls=ProvJSONDecoder) == _read_quietly(text)


def test_model_warning_from_a_json_read_names_the_caller() -> None:
    _, messages = _read_warning(
        _json({"activity": {"ex:a": {"prov:startTime": "2012-01-01T00:00:00+15:00"}}})
    )
    assert messages == [
        _rejected(
            "prov:startTime 2012-01-01T00:00:00+15:00 has a timezone offset"
            " beyond ±14:00",
            513,
        )
    ]


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

    document = _read_quietly(text(_DATETIME_OBJECT))
    assert document == _read_quietly(text(_TIME))
    (record,) = document.get_records()
    assert datetime.datetime(2012, 1, 1) in {value for _, value in record.attributes}


@pytest.mark.parametrize(
    "time",
    [
        pytest.param({"$": "not-a-time", "type": "xsd:dateTime"}, id="ill-formed"),
        pytest.param({"$": _TIME, "type": "xsd:string"}, id="other-datatype"),
        pytest.param({"$": _TIME, "type": "foo:dateTime"}, id="unresolved-datatype"),
        pytest.param({"$": _TIME}, id="no-datatype"),
        pytest.param({"$": _TIME, "type": "xsd:dateTime", "lang": "en"}, id="lang"),
        pytest.param({"$": 2012, "type": "xsd:dateTime"}, id="number"),
        pytest.param({"$": _TIME, "type": 5}, id="number-datatype"),
        pytest.param(None, id="null"),
        pytest.param(5, id="bare-number"),
    ],
)
def test_time_that_is_not_an_xsd_datetime_raises(time: object) -> None:
    text = _json({"activity": {"ex:a": {"prov:startTime": time}}})
    expected = (
        "record 'ex:a', attribute 'prov:startTime': expected an xsd:dateTime,"
        f" found {time!r}"
    )
    with pytest.raises(ProvJSONException, match=re.escape(expected)):
        ProvDocument.deserialize(content=text, format="json")


@pytest.mark.parametrize("time", ["not-a-time", "2011-11-16"])
@pytest.mark.parametrize(("section", "attributes", "time_attr"), _TIMES)
def test_bare_time_that_is_not_an_xsd_datetime_warns(
    section: str, attributes: dict[str, str], time_attr: str, time: str
) -> None:
    document, messages = _read_warning(
        _json({section: {"ex:r": {**attributes, time_attr: time}}})
    )
    assert messages == [
        _rejected(
            f"record 'ex:r', attribute {time_attr!r}: {time!r} is not an"
            " xsd:dateTime and is dropped",
            555,
        )
    ]
    assert document == _read_quietly(_json({section: {"ex:r": attributes}}))


@pytest.mark.parametrize(
    ("section", "attributes", "attr", "value"),
    [
        pytest.param("wasGeneratedBy", {}, "prov:entity", "ex:e", id="qualified-name"),
        pytest.param("activity", {}, "prov:startTime", _TIME, id="time"),
        pytest.param(
            "activity", {}, "prov:startTime", _DATETIME_OBJECT, id="time-value-object"
        ),
        pytest.param(
            "hadMember",
            {"prov:entity": "ex:e"},
            "prov:collection",
            "ex:c",
            id="collection",
        ),
    ],
)
def test_formal_attribute_written_as_an_array_warns(
    section: str, attributes: dict[str, str], attr: str, value: object
) -> None:
    document, messages = _read_warning(
        _json({section: {"ex:r": {**attributes, attr: [value]}}})
    )
    assert messages == [
        _rejected(
            f"record 'ex:r', attribute {attr!r}: the value is written as an array",
            531,
        )
    ]
    assert document == _read_quietly(
        _json({section: {"ex:r": {**attributes, attr: value}}})
    )


def test_had_member_entity_written_as_an_array_does_not_warn() -> None:
    def text(entity: object) -> str:
        return _json(
            {"hadMember": {"ex:r": {"prov:collection": "ex:c", "prov:entity": entity}}}
        )

    assert _read_quietly(text(["ex:e"])) == _read_quietly(text("ex:e"))


def test_had_member_array_gives_every_member_the_identifier_and_attributes() -> None:
    # #530: each record of the fan-out carries the membership's identifier and
    # attributes, as if every member were written as a membership of its own.
    def membership(entity: object) -> dict[str, object]:
        return {"prov:collection": "ex:c", "prov:entity": entity, "ex:k": "v"}

    fanned_out = _read_quietly(
        _json({"hadMember": {"ex:m": membership(["ex:e1", "ex:e2"])}})
    )
    one_each = _read_quietly(
        _json({"hadMember": {"ex:m": [membership("ex:e1"), membership("ex:e2")]}})
    )
    assert fanned_out == one_each
    assert [str(r.identifier) for r in fanned_out.get_records()] == ["ex:m", "ex:m"]


def test_had_member_array_without_a_collection_reads() -> None:
    # The fan-out took the collection from the first record and raised
    # KeyError when the membership had none.
    document = _read_quietly(
        _json({"hadMember": {"ex:m": {"prov:entity": ["ex:e1", "ex:e2"]}}})
    )
    members = [r.get_attribute("prov:entity") for r in document.get_records()]
    assert [{str(e) for e in m} for m in members] == [{"ex:e1"}, {"ex:e2"}]


def test_had_member_members_resolve_alike() -> None:
    # Every member resolves as the first one does. A later member with an
    # undeclared prefix, or a null, raised ProvExceptionInvalidQualifiedName.
    # The undeclared prefix warns, as 3.3.0 rejects it (#516).
    def members(entities: list[str | None]) -> list[set[Any]]:
        text = _json(
            {
                "hadMember": {
                    "ex:m": {"prov:collection": "ex:c", "prov:entity": entities}
                }
            }
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ProvFutureRejectionWarning)
            document = ProvDocument.deserialize(content=text, format="json")
        return [r.get_attribute("prov:entity") for r in document.get_records()]

    assert members(["foo:e1", "ex:e2"]) == members(["ex:e2", "foo:e1"])[::-1]
    assert members([None, "ex:e2"]) == members(["ex:e2", None])[::-1]


@pytest.mark.parametrize(
    ("section", "attributes"),
    [
        pytest.param("wasGeneratedBy", {}, id="generation"),
        pytest.param("hadMember", {"prov:collection": "ex:c"}, id="membership"),
    ],
)
def test_formal_attribute_written_as_an_empty_array_raises(
    section: str, attributes: dict[str, str]
) -> None:
    text = _json({section: {"ex:r": {**attributes, "prov:entity": []}}})
    expected = "record 'ex:r', attribute 'prov:entity': the value is an empty array"
    with pytest.raises(ProvJSONException, match=re.escape(expected)):
        ProvDocument.deserialize(content=text, format="json")


@pytest.mark.parametrize(
    ("value", "same_as"),
    [
        pytest.param(None, {}, id="alone"),
        pytest.param([None, "x"], {"ex:k": "x"}, id="in-an-array"),
    ],
)
def test_null_attribute_value_warns(value: object, same_as: dict[str, str]) -> None:
    document, messages = _read_warning(_json({"entity": {"ex:e": {"ex:k": value}}}))
    assert messages == [
        _rejected(
            "record 'ex:e', attribute 'ex:k': the value is null and is dropped", 528
        )
    ]
    assert document == _read_quietly(_json({"entity": {"ex:e": same_as}}))


_FULL_IRI_REASON = "its prefix 'http' is not declared"


def _full_iri(text: str, position: str) -> str:
    return _rejected(
        f"{position}: the qualified name {text!r} does not resolve, because"
        f" {_FULL_IRI_REASON}; it reads as ex:{text.rpartition('/')[2]}",
        551,
    )


@pytest.mark.parametrize(
    ("section", "attributes", "attr_name", "clean"),
    [
        pytest.param(
            "wasGeneratedBy",
            {"prov:entity": "ex:e", "prov:activity": "http://example.org/a"},
            "prov:activity",
            {"prov:entity": "ex:e", "prov:activity": "ex:a"},
            id="formal",
        ),
        pytest.param(
            "hadMember",
            {"prov:collection": "ex:c", "prov:entity": "http://example.org/e"},
            "prov:entity",
            {"prov:collection": "ex:c", "prov:entity": "ex:e"},
            id="member",
        ),
        pytest.param(
            "hadMember",
            {"prov:collection": "ex:c", "prov:entity": ["http://example.org/e"]},
            "prov:entity",
            {"prov:collection": "ex:c", "prov:entity": ["ex:e"]},
            id="member-in-an-array",
        ),
    ],
)
def test_formal_attribute_that_is_a_full_iri_warns(
    section: str, attributes: dict[str, Any], attr_name: str, clean: dict[str, Any]
) -> None:
    document, messages = _read_warning(_json({section: {"ex:r": attributes}}))
    value = attributes[attr_name]
    text = value[0] if isinstance(value, list) else value
    assert messages == [_full_iri(text, f"record 'ex:r', attribute '{attr_name}'")]
    assert document == _read_quietly(_json({section: {"ex:r": clean}}))


def test_had_member_full_iri_members_each_warn() -> None:
    entity = ["http://example.org/e1", "ex:e2", "http://example.org/e3"]
    document, messages = _read_warning(
        _json(
            {"hadMember": {"ex:m": {"prov:collection": "ex:c", "prov:entity": entity}}}
        )
    )
    assert messages == [
        _full_iri("http://example.org/e1", "record 'ex:m', attribute 'prov:entity'"),
        _full_iri("http://example.org/e3", "record 'ex:m', attribute 'prov:entity'"),
    ]
    clean = ["ex:e1", "ex:e2", "ex:e3"]
    assert document == _read_quietly(
        _json(
            {"hadMember": {"ex:m": {"prov:collection": "ex:c", "prov:entity": clean}}}
        )
    )


def test_bundle_key_that_is_a_full_iri_warns() -> None:
    def text(key: str) -> str:
        return _json({"bundle": {key: {"entity": {"ex:e": {}}}}})

    document, messages = _read_warning(text("http://example.org/b"))
    assert messages == [
        _full_iri("http://example.org/b", "bundle 'http://example.org/b'")
    ]
    assert document == _read_quietly(text("ex:b"))


def test_null_formal_attribute_warns() -> None:
    attributes = {"prov:entity": "ex:e", "prov:activity": None}
    document, messages = _read_warning(_json({"wasGeneratedBy": {"ex:r": attributes}}))
    assert messages == [
        _rejected(
            "record 'ex:r', attribute 'prov:activity': the value is null and is"
            " dropped",
            528,
        )
    ]
    assert document == _read_quietly(
        _json({"wasGeneratedBy": {"ex:r": {"prov:entity": "ex:e"}}})
    )


@pytest.mark.parametrize(
    ("entity", "members"),
    [
        pytest.param(None, [set()], id="alone"),
        pytest.param([None, "ex:e"], [set(), {"ex:e"}], id="in-an-array"),
    ],
)
def test_null_had_member_member_warns(entity: object, members: list[set[str]]) -> None:
    document, messages = _read_warning(
        _json(
            {"hadMember": {"ex:m": {"prov:collection": "ex:c", "prov:entity": entity}}}
        )
    )
    assert messages == [
        _rejected(
            "record 'ex:m', attribute 'prov:entity': the value is null and is dropped",
            528,
        )
    ]
    read = [r.get_attribute("prov:entity") for r in document.get_records()]
    assert [{str(e) for e in m} for m in read] == members


@pytest.mark.parametrize(
    ("value", "text"),
    [
        pytest.param(5, "5", id="number"),
        pytest.param(1.5, "1.5", id="float"),
        pytest.param(True, "true", id="boolean"),
        pytest.param({"$": "ex:a", "type": "prov:QUALIFIED_NAME"}, None, id="object"),
        pytest.param([[1]], "[1]", id="nested-array"),
    ],
)
def test_formal_attribute_that_is_not_a_string_warns(
    value: object, text: str | None
) -> None:
    attributes = {"prov:entity": "ex:e", "prov:activity": value}
    document, messages = _read_warning(_json({"wasGeneratedBy": {"ex:r": attributes}}))
    shown = text if text is not None else json.dumps(value)
    expected = [
        _rejected(
            f"record 'ex:r', attribute 'prov:activity': the value is {shown}, not a"
            " qualified name, and is dropped",
            597,
        )
    ]
    if isinstance(value, list):
        expected.insert(
            0,
            _rejected(
                "record 'ex:r', attribute 'prov:activity': the value is written as"
                " an array",
                531,
            ),
        )
    assert messages == expected
    assert document == _read_quietly(
        _json({"wasGeneratedBy": {"ex:r": {"prov:entity": "ex:e"}}})
    )


def test_had_member_member_that_is_not_a_string_warns() -> None:
    document, messages = _read_warning(
        _json({"hadMember": {"ex:m": {"prov:collection": "ex:c", "prov:entity": [5]}}})
    )
    assert messages == [
        _rejected(
            "record 'ex:m', attribute 'prov:entity': the value is 5, not a qualified"
            " name, and is dropped",
            597,
        )
    ]
    assert [r.get_attribute("prov:entity") for r in document.get_records()] == [set()]


@pytest.mark.parametrize(
    ("value", "details", "same_as"),
    [
        pytest.param(
            {"$": "1", "datatype": "xsd:int"},
            [("the value object has the unknown key 'datatype'", 529)],
            "1",
            id="unknown-key",
        ),
        pytest.param(
            {"$": "1", "b": "x", "a": "x"},
            [
                ("the value object has the unknown key 'a'", 529),
                ("the value object has the unknown key 'b'", 529),
            ],
            "1",
            id="unknown-keys",
        ),
        pytest.param(
            {"$": 1},
            [('the value object\'s "$" is 1, not a string', 529)],
            "1",
            id="number",
        ),
        pytest.param(
            {"$": 1, "type": "xsd:double"},
            [('the value object\'s "$" is 1, not a string', 529)],
            {"$": "1", "type": "xsd:double"},
            id="integer-typed-double",
        ),
        pytest.param(
            {"$": 1.5, "type": "xsd:int"},
            [('the value object\'s "$" is 1.5, not a string', 529)],
            {"$": "1.5", "type": "xsd:int"},
            id="float-typed-int",
        ),
        pytest.param(
            {"$": True, "type": "xsd:int"},
            [('the value object\'s "$" is true, not a string', 529)],
            {"$": "True", "type": "xsd:int"},
            id="boolean-typed-int",
        ),
        pytest.param(
            {"$": 1, "type": "xsd:int", "lang": "en"},
            [('the value object\'s "$" is 1, not a string', 529)],
            {"$": "1", "type": "xsd:int", "lang": "en"},
            id="typed-number-with-lang",
        ),
        pytest.param(
            {"$": True},
            [('the value object\'s "$" is true, not a string', 529)],
            "True",
            id="boolean",
        ),
        pytest.param(
            {"$": None},
            [('the value object\'s "$" is null, not a string', 529)],
            "None",
            id="null",
        ),
        pytest.param(
            {"$": "1", "type": "foo:int"},
            [("the datatype 'foo:int' does not resolve and is dropped", 552)],
            "1",
            id="undeclared-datatype",
        ),
        pytest.param(
            {"$": "1", "type": "foo:int", "lang": "en"},
            [("the datatype 'foo:int' does not resolve and is dropped", 552)],
            {"$": "1", "lang": "en"},
            id="undeclared-datatype-with-lang",
        ),
    ],
)
def test_value_object_that_3_3_0_rejects_warns(
    value: dict[str, object], details: list[tuple[str, int]], same_as: object
) -> None:
    document, messages = _read_warning(_json({"entity": {"ex:e": {"ex:k": value}}}))
    assert messages == [
        _rejected(f"record 'ex:e', attribute 'ex:k': {detail}", issue)
        for detail, issue in details
    ]
    assert document == _read_quietly(_json({"entity": {"ex:e": {"ex:k": same_as}}}))


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
def test_value_object_number_as_prov_2_wrote_it_reads_quietly(
    value: dict[str, object], same_as: dict[str, str]
) -> None:
    # prov 2.x and earlier wrote an int as xsd:int and a float as xsd:double,
    # and prov 1.x on Python 2 wrote a long as xsd:long.
    text = _json({"entity": {"ex:e": {"ex:k": value}}})
    expected = _json({"entity": {"ex:e": {"ex:k": same_as}}})
    assert _read_quietly(text) == _read_quietly(expected)


def test_formal_attribute_written_as_an_array_of_several_values_raises() -> None:
    text = _json(
        {
            "wasGeneratedBy": {
                "ex:g": {"prov:entity": "ex:e", "prov:activity": ["ex:a", "ex:b"]}
            }
        }
    )
    expected = (
        "record 'ex:g', attribute 'prov:activity': the value is an array of 2 values, "
        "but the attribute takes one"
    )
    with pytest.raises(ProvJSONException, match=re.escape(expected)):
        ProvDocument.deserialize(content=text, format="json")


def test_value_object_number_parsed_as_a_decimal_warns() -> None:
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        document = prov.read(
            io.StringIO(_json({"entity": {"ex:e": {"ex:k": {"$": 1.5}}}})),
            format="json",
            parse_float=decimal.Decimal,
        )
    future = [w for w in caught if w.category is ProvFutureRejectionWarning]
    assert [str(w.message) for w in future] == [
        _rejected(
            "record 'ex:e', attribute 'ex:k': the value object's \"$\" is 1.5, not a string",
            529,
        )
    ]
    assert [w.filename for w in future] == [__file__]
    assert document == _read_quietly(
        _json({"entity": {"ex:e": {"ex:k": {"$": "1.5"}}}})
    )


def test_value_object_keys_a_caller_hook_makes_non_strings_warn() -> None:
    def hook(pairs: list[tuple[str, Any]]) -> dict[Any, Any]:
        return {int(k) if k.isdigit() else k: v for k, v in pairs}

    text = _json({"entity": {"ex:e": {"ex:k": {"$": "1", "2": "x", "a": "y"}}}})
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        document = prov.read(io.StringIO(text), format="json", object_pairs_hook=hook)
    future = [w for w in caught if w.category is ProvFutureRejectionWarning]
    assert [str(w.message) for w in future] == [
        _rejected(
            "record 'ex:e', attribute 'ex:k': the value object has the unknown key 2",
            529,
        ),
        _rejected(
            "record 'ex:e', attribute 'ex:k': the value object has the unknown key 'a'",
            529,
        ),
    ]
    assert document == _read_quietly(_json({"entity": {"ex:e": {"ex:k": "1"}}}))


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
def test_well_formed_attribute_value_does_not_warn(value: object) -> None:
    _read_quietly(_json({"entity": {"ex:e": {"ex:k": value}}}))


def test_value_object_warning_without_a_position() -> None:
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        decode_json_representation({"$": "1", "x": "y"}, ProvDocument())
    assert [str(w.message) for w in caught] == [
        _rejected("the value object has the unknown key 'x'", 529)
    ]

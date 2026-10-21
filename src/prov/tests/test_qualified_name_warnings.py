"""3.3.0 warnings about qualified names that do not resolve (#516, #551, #553)."""

from __future__ import annotations

import json
import warnings
from typing import Any

import pytest

from prov.model import (
    PROV_QUALIFIEDNAME,
    XSD_QNAME,
    Literal,
    Namespace,
    ProvDocument,
    ProvFutureRejectionWarning,
    QualifiedName,
)
from prov.serializers.provjsonld import JSONLD_CONTEXT_URL
from prov.tests.conftest import ROUNDTRIP_FORMATS

from .conftest import ex_document, future_messages, no_future_rejection

EX = "http://example.org/"
UNDECLARED = "its prefix 'zz' is not declared"
FULL_IRI = "its prefix 'http' is not declared"
NO_PREFIX = "it has no prefix and no default namespace is declared"
KEPT = "it is kept as a Literal"


def _message(
    where: str, text: str, reason: str, today: str, issue: int, attr: str = ""
) -> str:
    return (
        f"{where}the qualified name {text!r}{attr} does not resolve, because"
        f" {reason}; {today}. prov 3.3.0 will reject this (#{issue})"
    )


#  Values asserted in code
def _declared_in_the_document(literal: Literal) -> None:
    document = ex_document()
    document.bundle("ex:b").entity("ex:e", {"ex:k": literal})


def _bare_name_with_a_default(literal: Literal) -> None:
    document = ProvDocument()
    document.set_default_namespace(EX)
    document.entity("e", {"k": literal})


@pytest.mark.parametrize(
    ("literal", "assert_in"),
    [
        pytest.param(
            Literal("ex:x", PROV_QUALIFIEDNAME),
            lambda literal: ex_document().entity("ex:e", {"ex:k": literal}),
            id="declared",
        ),
        pytest.param(
            Literal("ex:x", XSD_QNAME),
            lambda literal: ex_document().entity("ex:e", {"ex:k": literal}),
            id="xsd:QName declared",
        ),
        pytest.param(
            Literal("ex:x", PROV_QUALIFIEDNAME),
            _declared_in_the_document,
            id="declared in the document",
        ),
        pytest.param(
            Literal("x", PROV_QUALIFIEDNAME),
            _bare_name_with_a_default,
            id="bare name with a default",
        ),
        pytest.param(
            Literal("zz:x"),
            lambda literal: ex_document().entity("ex:e", {"ex:k": literal}),
            id="untyped",
        ),
    ],
)
def test_resolvable_qualified_name_value_does_not_warn(
    literal: Literal, assert_in: Any
) -> None:
    with no_future_rejection():
        assert_in(literal)


#  PROV-N
def _provn(attributes: str, declarations: str = f"prefix ex <{EX}>\n") -> str:
    return f"document\n{declarations}entity(ex:e, [ex:k={attributes}])\nendDocument\n"


@pytest.mark.parametrize(
    ("value", "text", "reason", "today", "stored", "issue"),
    [
        pytest.param("'zz:x'", "zz:x", UNDECLARED, KEPT, None, 516, id="undeclared"),
        pytest.param(
            f"'{EX}x'",
            f"{EX}x",
            FULL_IRI,
            "it reads as ex:x",
            "ex:x",
            553,
            id="full IRI",
        ),
    ],
)
def test_provn_unresolvable_qualified_name_value_warns_once(
    value: str, text: str, reason: str, today: str, stored: str | None, issue: int
) -> None:
    source = _provn(value)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ProvFutureRejectionWarning)
        expected = ProvDocument.deserialize(content=source, format="provn")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        document = ProvDocument.deserialize(content=source, format="provn")
    assert future_messages(caught, __file__) == [
        _message("line 3, column 20: ", text, reason, today, issue)
    ]
    assert document == expected
    if stored is not None:
        ((_, read),) = next(iter(document.get_records())).extra_attributes
        assert str(read) == stored


@pytest.mark.parametrize(
    ("value", "declarations"),
    [
        pytest.param("'ex:x'", f"prefix ex <{EX}>\n", id="declared"),
        pytest.param(
            '"ex:x" %% prov:QUALIFIED_NAME', f"prefix ex <{EX}>\n", id="typed"
        ),
        pytest.param('"ex:x" %% xsd:QName', f"prefix ex <{EX}>\n", id="xsd:QName"),
        pytest.param("'x'", f"prefix ex <{EX}>\ndefault <{EX}>\n", id="default"),
        pytest.param(
            '"xsi:x" %% xsd:QName',
            f"prefix ex <{EX}>\nprefix xsi <http://www.w3.org/2001/XMLSchema-instance>\n",
            id="xsd:QName declared xsi",
        ),
        pytest.param(
            "'http://example.org/x'",
            f"prefix ex <{EX}>\nprefix http <http://h/>\n",
            id="prefix named http",
        ),
    ],
)
def test_provn_resolvable_qualified_name_value_does_not_warn(
    value: str, declarations: str
) -> None:
    with no_future_rejection():
        ProvDocument.deserialize(content=_provn(value, declarations), format="provn")


def test_provn_value_in_a_bundle_resolves_against_the_document() -> None:
    source = (
        f"document\nprefix ex <{EX}>\nbundle ex:b\nprefix b <http://b/>\n"
        "entity(ex:e, [ex:k='ex:x', ex:j='b:y'])\nendBundle\nendDocument\n"
    )
    with no_future_rejection():
        ProvDocument.deserialize(content=source, format="provn")


#  PROV-JSON
def _json(records: dict[str, Any], prefixes: dict[str, str] | None = None) -> str:
    return json.dumps({"prefix": prefixes or {"ex": EX}, **records})


def _read_json(text: str) -> tuple[ProvDocument, list[str], ProvDocument]:
    """Read ``text``; return the document, its warnings and the document read
    with the warnings ignored."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ProvFutureRejectionWarning)
        expected = ProvDocument.deserialize(content=text, format="json")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        document = ProvDocument.deserialize(content=text, format="json")
    return document, future_messages(caught, __file__), expected


def test_json_record_key_that_is_a_full_iri_warns() -> None:
    document, messages, expected = _read_json(_json({"entity": {f"{EX}e1": {}}}))
    assert messages == [
        _message(f"record '{EX}e1': ", f"{EX}e1", FULL_IRI, "it reads as ex:e1", 551)
    ]
    assert document == expected
    assert str(next(iter(document.get_records())).identifier) == "ex:e1"


def test_json_record_key_with_several_instances_warns_once() -> None:
    document, messages, expected = _read_json(
        _json({"entity": {f"{EX}e1": [{}, {"ex:k": "v"}]}})
    )
    assert messages == [
        _message(f"record '{EX}e1': ", f"{EX}e1", FULL_IRI, "it reads as ex:e1", 551)
    ]
    assert document == expected


@pytest.mark.parametrize(
    ("section", "attributes", "attr_name"),
    [
        pytest.param(
            "wasGeneratedBy",
            {"prov:entity": "ex:e", "prov:activity": "zz:a"},
            "prov:activity",
            id="formal",
        ),
        pytest.param(
            "hadMember",
            {"prov:collection": "ex:c", "prov:entity": ["ex:e", "zz:a"]},
            "prov:entity",
            id="member",
        ),
    ],
)
def test_json_unresolvable_name_that_is_dropped_warns(
    section: str, attributes: dict[str, Any], attr_name: str
) -> None:
    document, messages, expected = _read_json(_json({section: {"ex:r": attributes}}))
    where = f"record 'ex:r', attribute '{attr_name}': "
    assert messages == [_message(where, "zz:a", UNDECLARED, "it is dropped", 516)]
    assert document == expected


@pytest.mark.parametrize(
    ("records", "prefixes"),
    [
        pytest.param({"entity": {"ex:e": {}}}, None, id="declared key"),
        pytest.param(
            {"wasGeneratedBy": {"_:id1": {"prov:entity": "ex:e"}}},
            None,
            id="blank node key",
        ),
        pytest.param(
            {"wasGeneratedBy": {"g1": {"prov:entity": "ex:e"}}},
            None,
            id="bare key with no default",
        ),
        pytest.param(
            {"entity": {"http://example.org/e": {}}},
            {"ex": EX, "http": "http://h/"},
            id="prefix named http",
        ),
        pytest.param(
            {"entity": {"ex:e": {"ex:k": {"$": "ex:x", "type": "xsd:QName"}}}},
            None,
            id="declared value",
        ),
        pytest.param(
            {
                "entity": {
                    "ex:e": {"ex:k": {"$": "zz:x", "type": "xsd:QName", "lang": "en"}}
                }
            },
            None,
            id="value with a language tag",
        ),
        pytest.param(
            {"bundle": {"ex:b": {"entity": {"ex:e": {}}}}},
            None,
            id="declared bundle key",
        ),
        pytest.param(
            {"bundle": {"http://example.org/b": {"entity": {"ex:e": {}}}}},
            {"ex": EX, "http": "http://h/"},
            id="bundle key with a prefix named http",
        ),
        pytest.param(
            {
                "wasGeneratedBy": {
                    "ex:r": {"prov:entity": "ex:e", "prov:activity": "ex:a"}
                }
            },
            None,
            id="declared formal attribute",
        ),
        pytest.param(
            {
                "wasGeneratedBy": {
                    "ex:r": {"prov:entity": "ex:e", "prov:activity": "http://h/a"}
                }
            },
            {"ex": EX, "http": "http://h/"},
            id="formal attribute with a prefix named http",
        ),
        pytest.param(
            {
                "hadMember": {
                    "ex:m": {"prov:collection": "ex:c", "prov:entity": ["ex:e"]}
                }
            },
            None,
            id="declared member",
        ),
    ],
)
def test_json_resolvable_name_does_not_warn(
    records: dict[str, Any], prefixes: dict[str, str] | None
) -> None:
    with no_future_rejection():
        ProvDocument.deserialize(content=_json(records, prefixes), format="json")


#  Every reader and assertion, one message per reason (#587)
_REASONS = [
    pytest.param("zz:x", UNDECLARED, id="undeclared"),
    pytest.param(f"{EX}x", FULL_IRI, id="full IRI"),
    pytest.param("not a name", NO_PREFIX, id="no prefix"),
    pytest.param("", "it is empty", id="empty"),
]


def _asserted(text: str, datatype: QualifiedName) -> ProvDocument:
    document = ex_document()
    document.entity("ex:e", {"ex:k": Literal(text, datatype)})
    return document


def _read_provn(text: str, datatype: QualifiedName) -> ProvDocument:
    source = _provn(f'"{text}" %% {datatype}')
    return ProvDocument.deserialize(content=source, format="provn")


def _read_json_value(text: str, datatype: QualifiedName) -> ProvDocument:
    source = _json({"entity": {"ex:e": {"ex:k": {"$": text, "type": str(datatype)}}}})
    return ProvDocument.deserialize(content=source, format="json")


def _read_jsonld(text: str, datatype: QualifiedName) -> ProvDocument:
    source = json.dumps(
        {
            "@context": [{"ex": EX}, JSONLD_CONTEXT_URL],
            "@graph": [
                {
                    "@type": "Entity",
                    "@id": "ex:e",
                    "ex:k": [{"@value": text, "@type": str(datatype)}],
                }
            ],
        }
    )
    return ProvDocument.deserialize(content=source, format="jsonld")


# Each reader: its builder, the position that starts its message, the
# attribute named after the text, and the issue it cites when the value reads
# by compacting an IRI.
_READERS = {
    "asserted": (_asserted, "", " of ex:k", 553),
    "provn": (_read_provn, "line 3, column 20: ", "", 553),
    "json": (_read_json_value, "record 'ex:e', attribute 'ex:k': ", "", 551),
    "jsonld": (_read_jsonld, "", " of ex:k", 553),
}


@pytest.mark.parametrize("datatype", [PROV_QUALIFIEDNAME, XSD_QNAME], ids=str)
@pytest.mark.parametrize(("text", "reason"), _REASONS)
@pytest.mark.parametrize("reader", list(_READERS))
def test_every_reader_and_assertion_warn_once_with_one_message(
    reader: str, text: str, reason: str, datatype: QualifiedName
) -> None:
    build, where, attr, compaction_issue = _READERS[reader]
    # A full IRI compacts at assertion and in every reader, whichever of the
    # two datatypes it carries. 3.3.0 rejects it (#553).
    compacts = text == f"{EX}x"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        document = build(text, datatype)
    today, issue = ("it reads as ex:x", compaction_issue) if compacts else (KEPT, 516)
    assert future_messages(caught, __file__) == [
        _message(where, text, reason, today, issue, attr)
    ]
    ((_, value),) = next(iter(document.get_records())).extra_attributes
    assert value == (Namespace("ex", EX)["x"] if compacts else Literal(text, datatype))


#  Every reader, once per value; the XML reader already rejects such a value
@pytest.mark.parametrize("fmt", [fmt for fmt in ROUNDTRIP_FORMATS if fmt != "xml"])
def test_written_unresolvable_value_warns_once_on_reading(fmt: str) -> None:
    document = ex_document()
    with pytest.warns(ProvFutureRejectionWarning):
        document.entity("ex:e", {"ex:k": Literal("zz:x", XSD_QNAME)})
    text = document.serialize(format=fmt)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ProvDocument.deserialize(content=text, format=fmt)
    (message,) = future_messages(caught, __file__)
    assert "the qualified name 'zz:x'" in message

"""A qualified-name value that does not resolve by its prefix is rejected,
by every reader and at assertion (#516, #551, #553, #599)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from prov.constants import XSI
from prov.model import (
    PROV_QUALIFIEDNAME,
    XSD_QNAME,
    Literal,
    Namespace,
    ProvBundle,
    ProvDocument,
    ProvExceptionInvalidQualifiedName,
    ProvRecord,
    QualifiedName,
)
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provjsonld import JSONLD_CONTEXT_URL
from prov.serializers.provn_lexer import ProvNSyntaxError

from .conftest import ex_document

EX = "http://example.org/"
EX_X = Namespace("ex", EX)["x"]
UNDECLARED = "its prefix 'zz' is not declared"
FULL_IRI = "its prefix 'http' is not declared"
NO_PREFIX = "it has no prefix and no default namespace is declared"


def _detail(text: str, reason: str, attr: str = "") -> str:
    return f"the qualified name {text!r}{attr} does not resolve, because {reason}"


def _stored(document: ProvBundle) -> Any:
    ((_, value),) = next(iter(document.get_records())).extra_attributes
    return value


#  Values asserted in code
def _in_the_document(literal: Literal) -> ProvRecord:
    return ex_document().entity("ex:e", {"ex:k": literal})


def _declared_in_the_document(literal: Literal) -> ProvRecord:
    return ex_document().bundle("ex:b").entity("ex:e", {"ex:k": literal})


def _bare_name_with_a_default(literal: Literal) -> ProvRecord:
    document = ProvDocument()
    document.set_default_namespace(EX)
    return document.entity("e", {"k": literal})


@pytest.mark.parametrize(
    ("literal", "assert_in", "stored"),
    [
        pytest.param(
            Literal("ex:x", PROV_QUALIFIEDNAME), _in_the_document, EX_X, id="declared"
        ),
        pytest.param(
            Literal("ex:x", XSD_QNAME), _in_the_document, EX_X, id="xsd:QName declared"
        ),
        pytest.param(
            Literal("ex:x", PROV_QUALIFIEDNAME),
            _declared_in_the_document,
            EX_X,
            id="declared in the document",
        ),
        pytest.param(
            Literal("x", PROV_QUALIFIEDNAME),
            _bare_name_with_a_default,
            Namespace("", EX)["x"],
            id="bare name with a default",
        ),
        pytest.param(Literal("zz:x"), _in_the_document, "zz:x", id="untyped"),
    ],
)
def test_resolvable_qualified_name_value_is_stored(
    literal: Literal, assert_in: Callable[[Literal], ProvRecord], stored: Any
) -> None:
    ((_, value),) = assert_in(literal).extra_attributes
    assert value == stored


#  PROV-N
def _provn(attributes: str, declarations: str = f"prefix ex <{EX}>\n") -> str:
    return f"document\n{declarations}entity(ex:e, [ex:k={attributes}])\nendDocument\n"


@pytest.mark.parametrize(
    ("value", "declarations", "stored"),
    [
        pytest.param("'ex:x'", f"prefix ex <{EX}>\n", EX_X, id="declared"),
        pytest.param(
            '"ex:x" %% prov:QUALIFIED_NAME', f"prefix ex <{EX}>\n", EX_X, id="typed"
        ),
        pytest.param(
            '"ex:x" %% xsd:QName', f"prefix ex <{EX}>\n", EX_X, id="xsd:QName"
        ),
        pytest.param(
            "'x'",
            f"prefix ex <{EX}>\ndefault <{EX}>\n",
            Namespace("", EX)["x"],
            id="default",
        ),
        pytest.param(
            '"xsi:x" %% xsd:QName',
            f"prefix ex <{EX}>\nprefix xsi <{XSI.uri}>\n",
            XSI["x"],
            id="xsd:QName declared xsi",
        ),
        pytest.param(
            f"'{EX}x'",
            f"prefix ex <{EX}>\nprefix http <http://h/>\n",
            Namespace("http", "http://h/")["//example.org/x"],
            id="prefix named http",
        ),
    ],
)
def test_provn_resolvable_qualified_name_value_is_stored(
    value: str, declarations: str, stored: QualifiedName
) -> None:
    document = ProvDocument.deserialize(
        content=_provn(value, declarations), format="provn"
    )
    assert _stored(document) == stored


def test_provn_value_in_a_bundle_resolves_against_the_document() -> None:
    source = (
        f"document\nprefix ex <{EX}>\nbundle ex:b\nprefix b <http://b/>\n"
        "entity(ex:e, [ex:k='ex:x', ex:j='b:y'])\nendBundle\nendDocument\n"
    )
    document = ProvDocument.deserialize(content=source, format="provn")
    (bundle,) = document.bundles
    (record,) = bundle.get_records()
    assert [value for _, value in record.extra_attributes] == [
        EX_X,
        Namespace("b", "http://b/")["y"],
    ]


#  PROV-JSON
def _json(records: dict[str, Any], prefixes: dict[str, str] | None = None) -> str:
    return json.dumps({"prefix": prefixes or {"ex": EX}, **records})


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
def test_json_resolvable_name_reads(
    records: dict[str, Any], prefixes: dict[str, str] | None
) -> None:
    document = ProvDocument.deserialize(content=_json(records, prefixes), format="json")
    assert list(document.get_records()) or document.has_bundles()


#  Every reader and assertion, one message per reason (#587)
_REASONS = [
    pytest.param("zz:x", UNDECLARED, id="undeclared"),
    pytest.param(f"{EX}x", FULL_IRI, id="full IRI"),
    pytest.param("not a name", NO_PREFIX, id="no prefix"),
    pytest.param("", "it is empty", id="empty"),
]


def _assert(text: str, datatype: QualifiedName) -> None:
    ex_document().entity("ex:e", {"ex:k": Literal(text, datatype)})


def _read_provn(text: str, datatype: QualifiedName) -> None:
    source = _provn(f'"{text}" %% {datatype}')
    ProvDocument.deserialize(content=source, format="provn")


def _read_json_value(text: str, datatype: QualifiedName) -> None:
    source = _json({"entity": {"ex:e": {"ex:k": {"$": text, "type": str(datatype)}}}})
    ProvDocument.deserialize(content=source, format="json")


def _read_jsonld(text: str, datatype: QualifiedName) -> None:
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
    ProvDocument.deserialize(content=source, format="jsonld")


def _read_rdf(text: str, datatype: QualifiedName) -> None:
    source = (
        f"@prefix ex: <{EX}> .\n@prefix prov: <http://www.w3.org/ns/prov#> .\n"
        f"ex:e a prov:Entity ; ex:k {json.dumps(text)}^^<{datatype.uri}> .\n"
    )
    ProvDocument.deserialize(content=source, format="rdf", rdf_format="turtle")


# Each channel: its reader, the error it raises, what starts the message
# ("{text}" is the rejected text) and whether the attribute is named after it.
_CHANNELS: dict[
    str, tuple[Callable[[str, QualifiedName], None], type[Exception], str, str]
] = {
    "asserted": (
        _assert,
        ProvExceptionInvalidQualifiedName,
        "Invalid Qualified Name: {text}, ",
        " of ex:k",
    ),
    "provn": (_read_provn, ProvNSyntaxError, "line 3, column 20: ", ""),
    "json": (
        _read_json_value,
        ProvJSONException,
        "record 'ex:e', attribute 'ex:k': ",
        "",
    ),
    "jsonld": (
        _read_jsonld,
        ProvExceptionInvalidQualifiedName,
        "Invalid Qualified Name: {text}, ",
        " of ex:k",
    ),
    "rdf": (
        _read_rdf,
        ProvExceptionInvalidQualifiedName,
        "Invalid Qualified Name: {text}, ",
        " of ex:k",
    ),
}


@pytest.mark.parametrize("datatype", [PROV_QUALIFIEDNAME, XSD_QNAME], ids=str)
@pytest.mark.parametrize(("text", "reason"), _REASONS)
@pytest.mark.parametrize("channel", list(_CHANNELS))
def test_every_reader_and_assertion_reject_with_one_message(
    channel: str, text: str, reason: str, datatype: QualifiedName
) -> None:
    read, error, where, attr = _CHANNELS[channel]
    with pytest.raises(error) as ctx:
        read(text, datatype)
    assert str(ctx.value) == where.format(text=text) + _detail(text, reason, attr)


#  A prefix the document declares wins over compaction in a bundle (#599)
HTTP_A = Namespace("http", "http://h/")["//example.org/a"]


def test_prefix_declared_in_the_document_resolves_from_a_bundle() -> None:
    # The bundle declares ex and the document declares http, so the text
    # http://example.org/a is the name http:'//example.org/a', not ex:a,
    # whether the value is asserted, read, or given as a plain identifier.
    document = ProvDocument()
    document.add_namespace("d", "http://d/")
    document.add_namespace("http", "http://h/")
    bundle = document.bundle("d:b")
    bundle.add_namespace("ex", EX)
    record = bundle.entity("ex:e", {"ex:k": Literal(f"{EX}a", XSD_QNAME)})
    assert _stored(bundle) == HTTP_A
    assert (
        bundle.entity(f"{EX}e2").identifier
        == Namespace("http", "http://h/")["//example.org/e2"]
    )
    assert record is not None

    source = json.dumps(
        {
            "prefix": {"d": "http://d/", "http": "http://h/"},
            "bundle": {
                "d:b": {
                    "prefix": {"ex": EX},
                    "wasGeneratedBy": {
                        "ex:g": {"prov:entity": "ex:e", "prov:activity": f"{EX}a"}
                    },
                }
            },
        }
    )
    read = ProvDocument.deserialize(content=source, format="json")
    (read_bundle,) = read.bundles
    (generation,) = read_bundle.get_records()
    assert generation.get_attribute("prov:activity") == {HTTP_A}


def test_plain_identifier_in_code_still_compacts() -> None:
    # D3: with no prefix named http in scope, a plain-string identifier in
    # code compacts against the declared namespaces, as the how-to promises.
    document = ex_document()
    assert document.entity(f"{EX}e1").identifier == Namespace("ex", EX)["e1"]

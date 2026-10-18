"""3.3.0 warnings about qualified names that do not resolve (#516, #551, #553)."""

from __future__ import annotations

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
)
from prov.tests.conftest import ROUNDTRIP_FORMATS

EX = "http://example.org/"
UNDECLARED = "its prefix 'zz' is not declared"
FULL_IRI = "its prefix 'http' is not declared"
NO_PREFIX = "it has no prefix and no default namespace is declared"
KEPT = "it is kept as a Literal"


def _document() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", EX)
    return document


def _message(where: str, text: str, reason: str, today: str) -> str:
    return (
        f"{where}the qualified name {text!r} does not resolve, because {reason};"
        f" {today}. prov 3.3.0 will reject this"
    )


def _future_warnings(caught: list[warnings.WarningMessage]) -> list[str]:
    """The ProvFutureRejectionWarning messages in ``caught``, each of which
    must name this file as the caller."""
    future = [w for w in caught if w.category is ProvFutureRejectionWarning]
    assert [w.filename for w in future] == [__file__] * len(future)
    return [str(w.message) for w in future]


#  Values asserted in code
@pytest.mark.parametrize(
    ("literal", "reason", "today", "stored"),
    [
        pytest.param(
            Literal("zz:x", PROV_QUALIFIEDNAME),
            UNDECLARED,
            KEPT,
            Literal("zz:x", PROV_QUALIFIEDNAME),
            id="undeclared",
        ),
        pytest.param(
            Literal(f"{EX}x", PROV_QUALIFIEDNAME),
            FULL_IRI,
            "it reads as ex:x",
            Namespace("ex", EX)["x"],
            id="full IRI",
        ),
        pytest.param(
            Literal("not a name", PROV_QUALIFIEDNAME),
            NO_PREFIX,
            KEPT,
            Literal("not a name", PROV_QUALIFIEDNAME),
            id="no prefix",
        ),
        pytest.param(
            Literal("", PROV_QUALIFIEDNAME),
            "it is empty",
            KEPT,
            Literal("", PROV_QUALIFIEDNAME),
            id="empty",
        ),
        pytest.param(
            Literal("zz:x", XSD_QNAME),
            UNDECLARED,
            KEPT,
            Literal("zz:x", XSD_QNAME),
            id="xsd:QName undeclared",
        ),
        pytest.param(
            Literal(f"{EX}x", XSD_QNAME),
            FULL_IRI,
            KEPT,
            Literal(f"{EX}x", XSD_QNAME),
            id="xsd:QName full IRI",
        ),
    ],
)
def test_unresolvable_qualified_name_value_warns(
    literal: Literal, reason: str, today: str, stored: object
) -> None:
    document = _document()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        entity = document.entity("ex:e", {"ex:k": literal})
    assert _future_warnings(caught) == [
        _message("", literal.value, reason, today).replace(
            " does not resolve", " of ex:k does not resolve"
        )
    ]
    assert entity.get_attribute("ex:k") == {stored}


def _declared_in_the_document(literal: Literal) -> None:
    document = _document()
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
            lambda literal: _document().entity("ex:e", {"ex:k": literal}),
            id="declared",
        ),
        pytest.param(
            Literal("ex:x", XSD_QNAME),
            lambda literal: _document().entity("ex:e", {"ex:k": literal}),
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
            lambda literal: _document().entity("ex:e", {"ex:k": literal}),
            id="untyped",
        ),
    ],
)
def test_resolvable_qualified_name_value_does_not_warn(
    literal: Literal, assert_in: Any
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        assert_in(literal)


#  PROV-N
def _provn(attributes: str, declarations: str = f"prefix ex <{EX}>\n") -> str:
    return f"document\n{declarations}entity(ex:e, [ex:k={attributes}])\nendDocument\n"


@pytest.mark.parametrize(
    ("value", "text", "reason", "today", "stored"),
    [
        pytest.param("'zz:x'", "zz:x", UNDECLARED, KEPT, None, id="undeclared"),
        pytest.param(
            f"'{EX}x'", f"{EX}x", FULL_IRI, "it reads as ex:x", "ex:x", id="full IRI"
        ),
        pytest.param(
            '"zz:x" %% prov:QUALIFIED_NAME',
            "zz:x",
            UNDECLARED,
            KEPT,
            None,
            id="typed undeclared",
        ),
        pytest.param(
            f'"{EX}x" %% prov:QUALIFIED_NAME',
            f"{EX}x",
            FULL_IRI,
            "it reads as ex:x",
            "ex:x",
            id="typed full IRI",
        ),
        pytest.param(
            '"not a name" %% prov:QUALIFIED_NAME',
            "not a name",
            NO_PREFIX,
            KEPT,
            None,
            id="typed no prefix",
        ),
        pytest.param(
            '"zz:x" %% xsd:QName', "zz:x", UNDECLARED, KEPT, None, id="xsd:QName"
        ),
        pytest.param(
            f'"{EX}x" %% xsd:QName',
            f"{EX}x",
            FULL_IRI,
            KEPT,
            None,
            id="xsd:QName full IRI",
        ),
        pytest.param(
            '"xsi:x" %% xsd:QName',
            "xsi:x",
            "its prefix 'xsi' is not declared",
            KEPT,
            None,
            id="xsd:QName undeclared xsi",
        ),
    ],
)
def test_provn_unresolvable_qualified_name_value_warns_once(
    value: str, text: str, reason: str, today: str, stored: str | None
) -> None:
    source = _provn(value)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ProvFutureRejectionWarning)
        expected = ProvDocument.deserialize(content=source, format="provn")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        document = ProvDocument.deserialize(content=source, format="provn")
    assert _future_warnings(caught) == [
        _message("line 3, column 20: ", text, reason, today)
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
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        ProvDocument.deserialize(content=_provn(value, declarations), format="provn")


def test_provn_value_in_a_bundle_resolves_against_the_document() -> None:
    source = (
        f"document\nprefix ex <{EX}>\nbundle ex:b\nprefix b <http://b/>\n"
        "entity(ex:e, [ex:k='ex:x', ex:j='b:y'])\nendBundle\nendDocument\n"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        ProvDocument.deserialize(content=source, format="provn")


#  Every reader, once per value; the XML reader already rejects such a value
@pytest.mark.parametrize("fmt", [fmt for fmt in ROUNDTRIP_FORMATS if fmt != "xml"])
def test_written_unresolvable_value_warns_once_on_reading(fmt: str) -> None:
    document = _document()
    with pytest.warns(ProvFutureRejectionWarning):
        document.entity("ex:e", {"ex:k": Literal("zz:x", XSD_QNAME)})
    text = document.serialize(format=fmt)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ProvDocument.deserialize(content=text, format=fmt)
    (message,) = _future_warnings(caught)
    assert "the qualified name 'zz:x'" in message

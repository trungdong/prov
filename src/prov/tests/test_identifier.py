"""Exercises prov.identifier.Namespace edges not otherwise covered by the
serializer round-trip tests (planning/test-gap-checklist.md, T13), and
the local parts 3.3.0 rejects (#524)."""

import re
from typing import Any, cast

import pytest

from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import ProvDocument, ProvExceptionInvalidQualifiedName
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provjsonld import ProvJSONLDException
from prov.serializers.provxml import ProvXMLException


def test_namespace_rejects_empty_uri() -> None:
    with pytest.raises(ValueError):
        Namespace("ex", "")


def test_namespace_rejects_whitespace_only_uri() -> None:
    with pytest.raises(ValueError):
        Namespace("ex", "   ")


def test_contains_with_matching_str() -> None:
    ns = Namespace("ex", "http://example.org/")
    assert ns.contains("http://example.org/thing")


def test_contains_with_matching_identifier() -> None:
    ns = Namespace("ex", "http://example.org/")
    assert ns.contains(Identifier("http://example.org/thing"))


def test_contains_with_non_matching_uri() -> None:
    ns = Namespace("ex", "http://example.org/")
    assert not ns.contains("http://other.org/thing")


def test_contains_with_non_str_non_identifier_returns_false() -> None:
    ns = Namespace("ex", "http://example.org/")
    assert not ns.contains(cast(Any, 12345))


def test_qname_for_contained_str() -> None:
    ns = Namespace("ex", "http://example.org/")
    qname = ns.qname("http://example.org/thing")
    assert str(qname) == "ex:thing"


def test_qname_for_contained_identifier() -> None:
    ns = Namespace("ex", "http://example.org/")
    qname = ns.qname(Identifier("http://example.org/thing"))
    assert str(qname) == "ex:thing"


def test_qname_for_non_contained_uri_returns_none() -> None:
    ns = Namespace("ex", "http://example.org/")
    assert ns.qname("http://other.org/thing") is None


def test_qname_for_non_str_non_identifier_returns_none() -> None:
    ns = Namespace("ex", "http://example.org/")
    assert ns.qname(cast(Any, 12345)) is None


EX = "http://example.org/"

UNWRITABLE = [
    pytest.param("a b", id="space"),
    pytest.param("a\tb", id="control"),
    pytest.param('a"b', id="quote"),
    pytest.param("a|b", id="bar"),
    pytest.param("50%", id="bare-percent"),
    pytest.param("a%zz", id="percent-not-hex"),
    pytest.param("·a", id="leading-middle-dot"),
    pytest.param("e\udc80", id="lone-surrogate"),
]


def _message(localpart: str) -> str:
    return re.escape(
        f"Invalid Qualified Name: ex:{localpart}, the local part {localpart!r} of "
        f"<{EX}{localpart}> contains a character PROV-N cannot write"
    )


@pytest.mark.parametrize("localpart", UNWRITABLE)
def test_local_part_provn_cannot_write_raises(localpart: str) -> None:
    # #524: a local part that PROV-N can write only by percent-encoding it
    # would read back as a different IRI, so no QualifiedName holds one.
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_message(localpart)):
        _ = Namespace("ex", EX)[localpart]


def test_qualified_name_built_directly_raises() -> None:
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_message("a b")):
        QualifiedName(Namespace("ex", EX), "a b")


def test_unpickled_name_is_checked_too() -> None:
    # A pickle from an earlier release may hold such a name; loading it runs
    # the same check, so no document holds a name the writer cannot spell.
    name = QualifiedName.__new__(QualifiedName)
    state = {
        "_uri": EX + "a b",
        "_namespace": Namespace("ex", EX),
        "_localpart": "a b",
        "_str": "ex:a b",
    }
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_message("a b")):
        name.__setstate__(state)


@pytest.mark.parametrize(
    "localpart", ["e1", "run_1", "a-b.c", "a%20b", "na=me", "-a", "a.", "é", "1a", ""]
)
def test_local_part_provn_can_write_is_accepted(localpart: str) -> None:
    assert Namespace("ex", EX)[localpart].localpart == localpart


# What starts a reader's message for the record whose name is rejected.
_READ_WHERE = {
    "json": "record 'ex:a b': ",
    "xml": "line 3, <prov:entity> 'ex:a b': ",
    "jsonld": "Entity 'ex:a b': ",
}
_READ_ERRORS = {
    "json": ProvJSONException,
    "xml": ProvXMLException,
    "jsonld": ProvJSONLDException,
}


@pytest.mark.parametrize("fmt", list(_READ_ERRORS))
def test_local_part_raises_when_read(fmt: str) -> None:
    # The readers build the name, so each raises its own error for the record,
    # with the model's error as the cause.
    # PROV-N cannot carry the name and PROV-O refuses to write it, so the
    # text is written with an accepted name and edited.
    document = ProvDocument()
    document.add_namespace("ex", EX)
    document.entity("ex:a_b")
    text = document.serialize(format=fmt)
    assert text is not None
    assert text.count("a_b") == 1
    with pytest.raises(
        _READ_ERRORS[fmt], match=f"^{re.escape(_READ_WHERE[fmt])}{_message('a b')}$"
    ) as ctx:
        ProvDocument.deserialize(content=text.replace("a_b", "a b"), format=fmt)
    assert isinstance(ctx.value.__cause__, ProvExceptionInvalidQualifiedName)

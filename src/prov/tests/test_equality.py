"""Equality and hashing of records, bundles and documents: one rule, symmetric
and consistent with ``hash()`` (#525, #527). Each pair compares the same from
both sides and, where equal, two records hash alike."""

from collections.abc import Callable

import pytest

from prov.constants import XSD
from prov.model import (
    AttributeValue,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvEntity,
    ProvRecord,
)


def _ex() -> ProvDocument:
    document = ProvDocument()
    document.set_default_namespace("http://example.org/")
    return document


def _with_value(value: AttributeValue) -> ProvEntity:
    return _ex().entity("e1", {"v": value})


def _relation(identifier: str | None = None) -> ProvRecord:
    return _ex().wasGeneratedBy("e1", "a1", identifier=identifier)


def _document_with_bundles(*names: str) -> ProvDocument:
    document = _ex()
    document.entity("e1")
    for name in names:
        document.bundle(name)
    return document


def _bundle_with_e1() -> ProvBundle:
    bundle = _ex().bundle("b")
    bundle.entity("e1")
    return bundle


EQUALITY_PAIRS = [
    pytest.param(
        _relation, lambda: _relation("g1"), False, id="anonymous-vs-identified"
    ),
    pytest.param(
        lambda: _relation("g1"), lambda: _relation("g1"), True, id="identified"
    ),
    pytest.param(_relation, _relation, True, id="anonymous"),
    pytest.param(
        _document_with_bundles,
        lambda: _document_with_bundles("b1"),
        False,
        id="extra-bundle",
    ),
    pytest.param(
        lambda: _document_with_bundles("b1"),
        lambda: _document_with_bundles("b2"),
        False,
        id="different-bundle-identifiers",
    ),
    pytest.param(
        lambda: _document_with_bundles("b1", "b2"),
        lambda: _document_with_bundles("b2", "b1"),
        True,
        id="same-bundles",
    ),
    pytest.param(
        _bundle_with_e1, _document_with_bundles, False, id="bundle-vs-document"
    ),
    pytest.param(
        lambda: _with_value(5),
        lambda: _with_value(Literal("05", XSD["int"])),
        True,
        id="int",
    ),
    pytest.param(
        lambda: _with_value(Literal("1e0", XSD["double"])),
        lambda: _with_value(1.0),
        True,
        id="double",
    ),
    pytest.param(
        lambda: _with_value(True),
        lambda: _with_value(Literal("1", XSD["boolean"])),
        True,
        id="boolean",
    ),
    pytest.param(
        lambda: _with_value(Literal("1.0", XSD["decimal"])),
        lambda: _with_value(Literal("1.00", XSD["decimal"])),
        True,
        id="decimal",
    ),
    pytest.param(
        lambda: _with_value(float("nan")),
        lambda: _with_value(float("nan")),
        True,
        id="nan",
    ),
    pytest.param(lambda: _with_value(0.0), lambda: _with_value(-0.0), True, id="zero"),
    pytest.param(
        lambda: _with_value(5),
        lambda: _with_value(Literal("5", XSD["long"])),
        False,
        id="int-vs-long",
    ),
    pytest.param(
        lambda: _with_value(2), lambda: _with_value(2.0), False, id="int-vs-float"
    ),
]


@pytest.mark.parametrize(("left", "right", "equal"), EQUALITY_PAIRS)
def test_equality_is_symmetric_and_agrees_with_hashing(
    left: Callable[[], object], right: Callable[[], object], equal: bool
) -> None:
    a, b = left(), right()
    assert (a == b) is equal
    assert (b == a) is equal
    if equal and isinstance(a, ProvRecord):
        assert hash(a) == hash(b)


def test_bundle_equality_refuses_a_document() -> None:
    # Under == ProvDocument.__eq__ answers first; a ProvBundle subclass
    # compared with a document reaches ProvBundle.__eq__, which refuses it.
    assert ProvBundle.__eq__(_bundle_with_e1(), _document_with_bundles()) is False

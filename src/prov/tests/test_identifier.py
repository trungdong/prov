"""Exercises prov.identifier.Namespace edges not otherwise covered by the
serializer round-trip tests (planning/test-gap-checklist.md, T13), and the
3.2.3 warning for a local part 3.3.0 rejects (#524)."""

import copy
import pickle
import re
import warnings
from collections.abc import Callable
from typing import Any, cast

import pytest

from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import ProvDocument, ProvFutureRejectionWarning


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
    pytest.param("\u00b7a", id="leading-middle-dot"),
]


def _message(localpart: str) -> str:
    return re.escape(
        f"the local part {localpart!r} of <{EX}{localpart}> contains a character "
        "PROV-N cannot write. prov 3.3.0 will reject this (#524)"
    )


@pytest.mark.parametrize("localpart", UNWRITABLE)
def test_local_part_provn_cannot_write_warns(localpart: str) -> None:
    # #524: 3.3.0 rejects a local part that PROV-N cannot write without
    # changing the IRI; 3.2.3 warns and keeps the name as given.
    with pytest.warns(ProvFutureRejectionWarning, match=_message(localpart)) as record:
        qname = Namespace("ex", EX)[localpart]
    assert qname.localpart == localpart
    assert qname.uri == EX + localpart
    assert record[0].filename == __file__


def test_qualified_name_built_directly_warns() -> None:
    with pytest.warns(ProvFutureRejectionWarning, match=_message("a b")):
        QualifiedName(Namespace("ex", EX), "a b")


def test_cached_name_warns_once() -> None:
    namespace = Namespace("ex", EX)
    with pytest.warns(ProvFutureRejectionWarning) as record:
        first = namespace["a b"]
        second = namespace["a b"]
    assert first is second
    assert len(record) == 1


@pytest.mark.parametrize(
    "localpart", ["e1", "run_1", "a-b.c", "a%20b", "na=me", "-a", "a.", "é", "1a", ""]
)
def test_local_part_provn_can_write_does_not_warn(localpart: str) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        assert Namespace("ex", EX)[localpart].localpart == localpart


def _document_with_unwritable_name() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", EX)
    with pytest.warns(ProvFutureRejectionWarning, match=_message("a b")) as record:
        document.entity("ex:a b")
    assert [w.filename for w in record] == [__file__]
    return document


def _updated(document: ProvDocument) -> ProvDocument:
    other = ProvDocument()
    other.update(document)
    return other


COPIES: dict[str, Callable[[ProvDocument], ProvDocument]] = {
    "pickle": lambda document: pickle.loads(pickle.dumps(document)),  # nosec B301 - nosemgrep
    "deepcopy": copy.deepcopy,
    "unified": lambda document: document.unified(),
    "flattened": lambda document: document.flattened(),
    "update": _updated,
}


@pytest.mark.parametrize("copy_document", COPIES.values(), ids=COPIES.keys())
def test_copies_of_a_name_do_not_warn_again(
    copy_document: Callable[[ProvDocument], ProvDocument],
) -> None:
    document = _document_with_unwritable_name()
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        copied = copy_document(document)
    assert copied == document


@pytest.mark.parametrize(
    "target_default", [EX, "http://other.org/"], ids=["same-default", "other-default"]
)
def test_default_namespace_name_does_not_warn_again_on_update(
    target_default: str,
) -> None:
    # The two default-namespace branches of the bundle's reconciliation: the
    # same default namespace, and another one, which renames this one to dn.
    document = ProvDocument()
    document.set_default_namespace(EX)
    with pytest.warns(ProvFutureRejectionWarning, match=_message("a b")):
        document.entity("a b")
    other = ProvDocument()
    other.set_default_namespace(target_default)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        other.update(document)
    (record,) = other.get_records()
    assert record.identifier is not None
    assert record.identifier.uri == EX + "a b"


@pytest.mark.parametrize("fmt", ["json", "xml", "jsonld"])
def test_local_part_warns_when_read(fmt: str) -> None:
    # The readers build the name, so the model's warning reaches their caller.
    # PROV-N writes the name percent-encoded and PROV-O refuses to write it.
    document = _document_with_unwritable_name()
    content = document.serialize(format=fmt)
    with pytest.warns(ProvFutureRejectionWarning, match=_message("a b")) as record:
        read = ProvDocument.deserialize(content=content, format=fmt)
    assert read == document
    assert [w.filename for w in record] == [__file__]

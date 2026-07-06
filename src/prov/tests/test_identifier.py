"""Exercises prov.identifier.Namespace edges not otherwise covered by the
serializer round-trip tests (docs/test-gap-checklist.md, T13)."""

import pytest

from prov.identifier import Identifier, Namespace


def test_namespace_rejects_empty_uri():
    with pytest.raises(ValueError):
        Namespace("ex", "")


def test_namespace_rejects_whitespace_only_uri():
    with pytest.raises(ValueError):
        Namespace("ex", "   ")


def test_contains_with_matching_str():
    ns = Namespace("ex", "http://example.org/")
    assert ns.contains("http://example.org/thing")


def test_contains_with_matching_identifier():
    ns = Namespace("ex", "http://example.org/")
    assert ns.contains(Identifier("http://example.org/thing"))


def test_contains_with_non_matching_uri():
    ns = Namespace("ex", "http://example.org/")
    assert not ns.contains("http://other.org/thing")


def test_contains_with_non_str_non_identifier_returns_false():
    ns = Namespace("ex", "http://example.org/")
    assert not ns.contains(12345)


def test_qname_for_contained_str():
    ns = Namespace("ex", "http://example.org/")
    qname = ns.qname("http://example.org/thing")
    assert str(qname) == "ex:thing"


def test_qname_for_contained_identifier():
    ns = Namespace("ex", "http://example.org/")
    qname = ns.qname(Identifier("http://example.org/thing"))
    assert str(qname) == "ex:thing"


def test_qname_for_non_contained_uri_returns_none():
    ns = Namespace("ex", "http://example.org/")
    assert ns.qname("http://other.org/thing") is None


def test_qname_for_non_str_non_identifier_returns_none():
    ns = Namespace("ex", "http://example.org/")
    assert ns.qname(12345) is None

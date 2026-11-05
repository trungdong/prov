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


def test_namespace_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(Namespace, "_CACHE_LIMIT", 3)
    ns = Namespace("ex", "http://example.org/")

    first = ns["a"]
    assert list(ns._cache) == ["a"]
    assert ns["b"].localpart == "b"
    assert list(ns._cache) == ["a", "b"]
    assert ns["c"].localpart == "c"
    assert list(ns._cache) == ["a", "b", "c"]

    # A miss at the limit empties the cache, so the new name sits alone.
    assert ns["d"].localpart == "d"
    assert list(ns._cache) == ["d"]

    # A name taken before the flush equals, and hashes as, the one after it.
    again = ns["a"]
    assert again == first
    assert hash(again) == hash(first)
    assert list(ns._cache) == ["d", "a"]

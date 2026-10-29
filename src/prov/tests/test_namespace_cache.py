"""The resolve-once cache in NamespaceManager and its invalidation."""

from collections.abc import ValuesView

import pytest

from prov.identifier import Identifier, Namespace
from prov.model import NamespaceManager, ProvDocument, ProvExceptionInvalidQualifiedName

from .conftest import default_namespace


def test_repeat_lookup_is_served_from_the_cache() -> None:
    manager = NamespaceManager({"ex": "http://example.org/"})
    first = manager.valid_qualified_name("ex:e1")
    assert "ex:e1" in manager._resolve_cache
    assert manager.valid_qualified_name("ex:e1") is first


def test_unresolvable_names_are_not_cached() -> None:
    manager = NamespaceManager()
    assert manager.valid_qualified_name("zz:e1") is None
    assert "zz:e1" not in manager._resolve_cache


@pytest.mark.parametrize("count", [50, 200])
def test_a_read_with_many_namespaces_scans_none(
    monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    scans = 0

    def counting_values(self: NamespaceManager) -> ValuesView[Namespace]:
        nonlocal scans
        scans += 1
        return dict.values(self)

    monkeypatch.setattr(NamespaceManager, "values", counting_values)
    manager = NamespaceManager()
    for i in range(count):
        iri = f"http://ex.org/run/{i}/out"
        assert manager.valid_qualified_name(iri) is None
        manager.add_namespace(Namespace(f"ns{i}", f"http://ex.org/run/{i}/"))
        assert str(manager.valid_qualified_name(iri)) == f"ns{i}:out"
    assert scans == 0


def test_adding_a_namespace_clears_the_cache() -> None:
    manager = NamespaceManager({"ex": "http://example.org/"})
    manager.valid_qualified_name("ex:e1")
    manager.add_namespace(Namespace("other", "http://other.org/"))
    assert manager._resolve_cache == {}


def test_changing_the_default_clears_the_cache_and_re_resolves() -> None:
    manager = NamespaceManager(default="http://one.org/")
    first = manager.valid_qualified_name("e1")
    manager.set_default_namespace("http://two.org/")
    second = manager.valid_qualified_name("e1")
    assert first.uri == "http://one.org/e1"
    assert second.uri == "http://two.org/e1"


def test_a_prefixless_name_is_rejected_when_no_default_is_declared() -> None:
    # Only set_default_namespace() sets a default, and the model mints no prefix.
    manager = NamespaceManager()
    qname = default_namespace("http://implicit.org/")["e1"]
    with pytest.raises(ProvExceptionInvalidQualifiedName, match="declare a prefix"):
        manager.valid_qualified_name(qname)
    assert manager.get_default_namespace() is None
    assert "" not in manager
    assert list(manager.get_registered_namespaces()) == []


def test_a_prefixless_name_takes_the_prefix_bound_to_its_iri() -> None:
    # A bundle reads a prefix-less name through the prefix its document binds
    # to the IRI, and registers nothing of its own.
    document = ProvDocument()
    document.add_namespace("ex", "http://ex/")
    bundle = document.bundle("ex:b")
    resolved = bundle.valid_qualified_name(default_namespace("http://ex/")["e"])

    assert str(resolved) == "ex:e"
    assert list(bundle.get_registered_namespaces()) == []
    assert str(bundle.valid_qualified_name("http://ex/other")) == "ex:other"
    assert bundle.valid_qualified_name(":foo") is None


def test_a_prefixless_name_is_rejected_when_the_bound_prefix_is_shadowed() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://ex/")
    named = document.add_namespace("nm", "http://named.org/")
    bundle = document.bundle(named["b"])
    bundle.add_namespace("ex", "http://other/")
    with pytest.raises(ProvExceptionInvalidQualifiedName, match="declare a prefix"):
        bundle.valid_qualified_name(default_namespace("http://ex/")["e"])


def test_child_lookup_answered_by_parent_is_not_cached_in_the_child() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    named = document.add_namespace("nm", "http://named.org/")
    bundle = document.bundle(named["b"])
    resolved = bundle.valid_qualified_name("ex:e1")
    assert resolved.uri == "http://example.org/e1"
    assert bundle._namespaces._resolve_cache == {}
    bundle.add_namespace("ex", "http://shadow.org/")
    shadowed = bundle.valid_qualified_name("ex:e1")
    assert shadowed.uri == "http://shadow.org/e1"


def test_identifier_input_bypasses_the_cache() -> None:
    # A colon-less Identifier never falls back to the default namespace, so
    # it must not be able to read (or plant) a cache entry keyed the same as
    # the plain string that does.
    manager = NamespaceManager(default="http://example.org/")
    resolved = manager.valid_qualified_name("e1")
    assert resolved.uri == "http://example.org/e1"
    assert manager.valid_qualified_name(Identifier("e1")) is None


def test_parent_answered_resolution_is_not_cached_in_the_child() -> None:
    document = ProvDocument()
    document.set_default_namespace("http://one.org/")
    named = document.add_namespace("nm", "http://named.org/")
    bundle = document.bundle(named["b"])
    resolved = bundle.valid_qualified_name("e1")
    assert resolved.uri == "http://one.org/e1"
    assert bundle._namespaces._resolve_cache == {}
    document.set_default_namespace("http://two.org/")
    assert bundle.valid_qualified_name("e1").uri == "http://two.org/e1"


def test_add_namespace_with_known_uri_clears_the_resolve_cache() -> None:
    ordered = ProvDocument()
    for prefix, uri in (("x", "a:"), ("y", "a:b"), ("a", "a:b")):
        ordered.add_namespace(prefix, uri)
    expected = ordered.valid_qualified_name("a:bc")

    doc = ProvDocument()
    doc.add_namespace("x", "a:")
    doc.add_namespace("y", "a:b")
    first = doc.valid_qualified_name("a:bc")
    # "a" is not yet registered here, so x's namespace is the only one whose
    # URI prefixes "a:bc"; x:bc is the correct resolution at this point.
    assert first.uri == "a:bc"
    # Same URI as y: registers a rename, must drop the cache.
    doc.add_namespace("a", "a:b")
    second = doc.valid_qualified_name("a:bc")
    assert second == expected
    assert second.uri == "a:bbc"


def test_a_name_whose_namespace_is_registered_here_is_returned_as_is() -> None:
    manager = NamespaceManager({"ex": "http://example.org/"}, default="http://d.org/")
    prefixed = manager.valid_qualified_name("ex:e1")
    plain = manager.valid_qualified_name("e1")
    assert prefixed is not None and plain is not None
    assert manager.valid_qualified_name(prefixed) is prefixed
    assert manager.valid_qualified_name(plain) is plain

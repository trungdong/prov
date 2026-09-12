"""The resolve-once cache in NamespaceManager and its invalidation."""

from prov.identifier import Identifier, Namespace
from prov.model import NamespaceManager, ProvDocument


def test_repeat_lookup_is_served_from_the_cache():
    manager = NamespaceManager({"ex": "http://example.org/"})
    first = manager.valid_qualified_name("ex:e1")
    assert "ex:e1" in manager._resolve_cache
    assert manager.valid_qualified_name("ex:e1") is first


def test_unresolvable_names_are_not_cached():
    manager = NamespaceManager()
    assert manager.valid_qualified_name("zz:e1") is None
    assert "zz:e1" not in manager._resolve_cache


def test_adding_a_namespace_clears_the_cache():
    manager = NamespaceManager({"ex": "http://example.org/"})
    manager.valid_qualified_name("ex:e1")
    manager.add_namespace(Namespace("other", "http://other.org/"))
    assert manager._resolve_cache == {}


def test_changing_the_default_clears_the_cache_and_re_resolves():
    manager = NamespaceManager(default="http://one.org/")
    first = manager.valid_qualified_name("e1")
    manager.set_default_namespace("http://two.org/")
    second = manager.valid_qualified_name("e1")
    assert first.uri == "http://one.org/e1"
    assert second.uri == "http://two.org/e1"


def test_implicit_default_from_a_prefixless_qualified_name_uses_the_setter():
    manager = NamespaceManager()
    qname = Namespace("", "http://implicit.org/")["e1"]
    manager.valid_qualified_name(qname)
    assert manager.get_default_namespace().uri == "http://implicit.org/"
    # The implicit default is not registered under the "" prefix, so it
    # does not take part in URI compaction or ":local" resolution.
    assert "" not in manager


def test_implicit_default_does_not_shadow_an_existing_prefix():
    # Reviewer scenario: a document registers "ex", then a bundle adopts an
    # unprefixed default namespace with the same URI. Before the fix,
    # adopting the default also registered it under "", so URI compaction
    # picked the bare local name instead of the "ex:" prefix, and ":local"
    # resolved against the adopted default even though no default namespace
    # was ever explicitly set on the bundle.
    document = ProvDocument()
    document.add_namespace("ex", "http://ex/")
    bundle = document.bundle("ex:b")
    bundle.valid_qualified_name(Namespace("", "http://ex/")["e"])

    assert str(bundle.valid_qualified_name("http://ex/other")) == "ex:other"
    assert bundle.valid_qualified_name(":foo") is None


def test_child_lookup_answered_by_parent_is_not_cached_in_the_child():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    bundle = document.bundle("ex:b")
    resolved = bundle.valid_qualified_name("ex:e1")
    assert resolved.uri == "http://example.org/e1"
    assert bundle._namespaces._resolve_cache == {}
    bundle.add_namespace("ex", "http://shadow.org/")
    shadowed = bundle.valid_qualified_name("ex:e1")
    assert shadowed.uri == "http://shadow.org/e1"


def test_identifier_input_bypasses_the_cache():
    # A colon-less Identifier never falls back to the default namespace, so
    # it must not be able to read (or plant) a cache entry keyed the same as
    # the plain string that does.
    manager = NamespaceManager(default="http://example.org/")
    resolved = manager.valid_qualified_name("e1")
    assert resolved.uri == "http://example.org/e1"
    assert manager.valid_qualified_name(Identifier("e1")) is None


def test_parent_answered_resolution_is_not_cached_in_the_child():
    document = ProvDocument()
    document.set_default_namespace("http://one.org/")
    bundle = document.bundle("http://one.org/b")
    resolved = bundle.valid_qualified_name("e1")
    assert resolved.uri == "http://one.org/e1"
    assert bundle._namespaces._resolve_cache == {}
    document.set_default_namespace("http://two.org/")
    assert bundle.valid_qualified_name("e1").uri == "http://two.org/e1"


def test_add_namespace_with_known_uri_clears_the_resolve_cache():
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

"""Scope, declaration and lookup tests for namespaces, bundles and documents."""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from prov.constants import PROV
from prov.identifier import Namespace, QualifiedName
from prov.model import (
    Literal,
    NamespaceManager,
    ProvBundle,
    ProvDocument,
    ProvException,
    ProvExceptionInvalidQualifiedName,
)

from . import examples
from .attribute_values import document as attribute_values_document
from .conftest import Roundtrip, default_namespace
from .test_provn_corpus import (
    CORPUS,
    EXCLUDED_PROVTOOLBOX_DOCUMENTS,
    EXCLUDED_SPEC_EXAMPLES,
)

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

_UNDECLARED_DEFAULT = (
    r"the name '\w+' is in the default namespace http://[\w.]+/, "
    "which is not the default namespace in scope; declare a prefix for it"
)


def test_a_bundle_registers_only_what_it_binds() -> None:
    # #449: a name an enclosing scope binds is that scope's name; the
    # bundle copies a declaration only when it rebinds the prefix itself.
    doc = ProvDocument()
    doc.set_default_namespace("http://d.org/")
    ex = doc.add_namespace("ex", "http://example.org/")
    bundle = doc.bundle("ex:b")
    assert bundle.entity(ex["e"]).identifier is ex["e"]
    assert bundle.entity(_name(doc, "f")).identifier is _name(doc, "f")
    assert bundle.add_record(doc.entity("ex:g")).identifier is ex["g"]
    assert list(bundle.get_registered_namespaces()) == []
    assert bundle.get_default_namespace() is None

    nm = doc.add_namespace("nm", "http://named.org/")
    rebinding = doc.bundle(nm["c"])
    rebinding.add_namespace("ex", "http://other.org/")
    renamed = rebinding.entity(ex["e"]).identifier
    assert renamed.namespace.prefix == "ex_1"
    assert renamed.uri == ex["e"].uri

    own_default = doc.bundle("ex:d")
    own_default.set_default_namespace("http://other.org/")
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_UNDECLARED_DEFAULT):
        own_default.entity(_name(doc, "f"))


def test_unified_bundle_registers_only_what_it_binds() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    bundle = doc.bundle("ex:b")
    bundle.entity("ex:e")
    bundle.entity("ex:e")
    (unified,) = doc.unified().bundles
    assert len(unified.get_records()) == 1
    assert list(unified.get_registered_namespaces()) == []


def _name(scope: ProvBundle, text: str) -> QualifiedName:
    name = scope.valid_qualified_name(text)
    assert name is not None
    return name


def _read_back(document: ProvDocument, format: str) -> ProvDocument:
    text = document.serialize(format=format)
    return ProvDocument.deserialize(content=text, format=format)


def test_a_prefix_less_name_is_rejected_and_sets_no_default() -> None:
    manager = NamespaceManager()
    with pytest.raises(ProvExceptionInvalidQualifiedName, match="declare a prefix"):
        manager.valid_qualified_name(default_namespace("http://u.org/")["e1"])
    assert manager.get_default_namespace() is None
    assert "" not in manager
    assert list(manager.get_registered_namespaces()) == []

    with_default = ProvDocument()
    with_default.set_default_namespace("http://u.org/")
    assert with_default._namespaces[""] is with_default.get_default_namespace()


def test_a_default_namespace_is_set_only_through_the_api() -> None:
    with pytest.raises(ValueError, match="set_default_namespace"):
        Namespace("", "http://x/")

    declaring = ProvDocument()
    declaring.set_default_namespace("http://x/")
    default = declaring.get_default_namespace()
    assert default is not None
    other = ProvDocument()
    with pytest.raises(ProvException, match="set_default_namespace"):
        other.add_namespace(default)
    manager = NamespaceManager()
    with pytest.raises(ProvException, match="set_default_namespace"):
        manager.add_namespace(default)
    with pytest.raises(ValueError, match="set_default_namespace"):
        manager.add_namespaces({"": "http://x/"})
    assert other.get_default_namespace() is None
    assert manager.get_default_namespace() is None


@pytest.mark.parametrize("format", ["json", "provn"])
def test_a_namespace_a_bundle_registers_never_shadows_a_declared_prefix(
    format: str,
) -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://one.org/")
    bundle = doc.bundle("ex:b")
    bundle.entity("ex:a")
    other = Namespace("ex", "http://two.org/")
    second = bundle.entity(other["b"]).identifier

    assert second is not None
    assert second.namespace.prefix == "ex_1"
    assert [ns.prefix for ns in bundle.get_registered_namespaces()] == ["ex_1"]

    (read_bundle,) = _read_back(doc, format).bundles
    uris = {str(r.identifier.uri) for r in read_bundle.get_records() if r.identifier}
    assert uris == {"http://one.org/a", "http://two.org/b"}

    with pytest.raises(ProvException, match=r"cannot declare prefix ex <http://three"):
        bundle.add_namespace("ex", "http://three.org/")


def _document_with_default_and_a_bundle() -> ProvDocument:
    doc = ProvDocument()
    doc.set_default_namespace("http://d.org/")
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("a")
    doc.entity("ex:b")
    bundle = doc.bundle("ex:bn")
    bundle.entity("c")
    return doc


def _spellings(bundle: ProvBundle) -> list[tuple[str, str]]:
    return [
        (str(r.identifier), r.identifier.uri)
        for r in bundle.get_records()
        if r.identifier is not None
    ]


def test_flattened_and_unified_keep_the_spelling_of_every_identifier() -> None:
    doc = _document_with_default_and_a_bundle()
    flat = doc.flattened()
    assert [s for s, _ in _spellings(flat)] == ["a", "ex:b", "c"]
    assert flat.get_default_namespace() == doc.get_default_namespace()

    unified = doc.unified()
    assert _spellings(unified) == _spellings(doc)
    assert unified.get_default_namespace() == doc.get_default_namespace()
    (unified_bundle,) = unified.bundles
    assert _spellings(unified_bundle) == [("c", "http://d.org/c")]

    standalone = ProvBundle()
    standalone.set_default_namespace("http://s.org/")
    standalone.entity("x")
    assert _spellings(standalone.unified()) == [("x", "http://s.org/x")]
    assert standalone.unified().get_default_namespace() == default_namespace(
        "http://s.org/"
    )


def test_add_bundle_keeps_the_spellings_of_a_document_argument() -> None:
    source = _document_with_default_and_a_bundle()
    target = ProvDocument()
    target.add_namespace("tg", "http://b.org/")
    as_document = source.flattened()
    target.add_bundle(as_document, target.valid_qualified_name("tg:bn"))
    (copied,) = target.bundles
    assert [s for s, _ in _spellings(copied)] == ["a", "ex:b", "c"]
    assert copied.get_default_namespace() == source.get_default_namespace()


def test_add_bundle_refuses_a_bundle_of_another_document() -> None:
    source = _document_with_default_and_a_bundle()
    (bundle,) = source.bundles
    target = ProvDocument()
    with pytest.raises(ProvException, match="belongs to another document"):
        target.add_bundle(bundle)
    assert not target.has_bundles()
    assert bundle.document is source
    assert _spellings(bundle) == [("c", "http://d.org/c")]
    assert list(source.bundles) == [bundle]


def test_update_into_a_document_without_a_default_is_rejected() -> None:
    source = ProvDocument()
    source.set_default_namespace("http://u.org/")
    source.entity("e")
    target = ProvDocument()
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_UNDECLARED_DEFAULT):
        target.update(source)
    assert target.get_default_namespace() is None


def test_a_name_in_another_default_is_rejected_where_that_default_is_not_in_scope() -> (
    None
):
    doc = ProvDocument()
    doc.set_default_namespace("http://a/")
    doc.add_namespace("ex", "http://example.org/")
    name = _name(doc, "e")

    own_default = doc.bundle("ex:b")
    own_default.set_default_namespace("http://b/")
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_UNDECLARED_DEFAULT):
        own_default.entity(name)
    with pytest.raises(ProvExceptionInvalidQualifiedName, match=_UNDECLARED_DEFAULT):
        own_default.entity("ex:x", {"ex:attr": Literal("v", datatype=name)})

    no_default = doc.bundle("ex:c")
    assert no_default.entity(name).identifier == name


def test_a_default_that_would_change_a_held_name_is_refused() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://a/")
    doc.add_namespace("ex", "http://example.org/")

    named = doc.bundle("e001")
    with pytest.raises(ProvException, match=r"holds e001.*read as http://b/e001"):
        named.set_default_namespace("http://b/")
    assert named.get_default_namespace() is None

    holding = doc.bundle("ex:h")
    holding.entity(_name(doc, "f"))
    with pytest.raises(ProvException, match=r"holds f.*read as http://b/f"):
        holding.set_default_namespace("http://b/")

    clean = doc.bundle("ex:k")
    clean.set_default_namespace("http://b/")
    assert clean.get_default_namespace() == default_namespace("http://b/")

    doc.entity("a")
    with pytest.raises(ProvException, match=r"holds a.*read as http://b/a"):
        doc.set_default_namespace("http://b/")


def test_a_document_declaration_is_refused_when_a_bundle_reads_through_it() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://a/")
    ns = doc.add_namespace("ex", "http://example.org/")
    bundle = doc.bundle(ns["b"])
    bundle.entity("e")
    with pytest.raises(ProvException, match=r"this bundle holds e.*read as http://b/e"):
        doc.set_default_namespace("http://b/")
    assert doc.get_default_namespace() == default_namespace("http://a/")


def test_a_prefix_that_would_change_a_held_name_is_refused() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://one.org/")
    bundle = doc.bundle("ex:b")
    bundle.entity("ex:a")
    with pytest.raises(ProvException, match=r"holds ex:b.*read as http://two.org/b"):
        bundle.add_namespace("ex", "http://two.org/")
    assert list(bundle.get_registered_namespaces()) == []

    other = doc.bundle(doc.add_namespace("nm", "http://named.org/")["c"])
    other.add_namespace("ex", "http://two.org/")
    assert [ns.prefix for ns in other.get_registered_namespaces()] == ["ex"]

    # a prefix this scope itself binds is renamed, which changes no held name
    doc.entity("ex:z")
    assert doc.add_namespace("ex", "http://two.org/").prefix == "ex_1"


def _held_names(bundle: ProvBundle) -> Iterator[QualifiedName]:
    if bundle.identifier is not None:
        yield bundle.identifier
    for record in bundle.get_records():
        if record.identifier is not None:
            yield record.identifier
        for name, value in record.attributes:
            yield name
            if isinstance(value, QualifiedName):
                yield value
            elif isinstance(value, Literal) and value.datatype is not None:
                yield value.datatype


def _provn_corpus_files() -> list[Path]:
    excluded = {*EXCLUDED_SPEC_EXAMPLES, *EXCLUDED_PROVTOOLBOX_DOCUMENTS}
    return sorted(path for path in CORPUS.rglob("*.provn") if path.name not in excluded)


def _corpus_sources() -> "Iterator[ParameterSet]":
    for name, build in examples.tests:
        yield pytest.param(build, id=name)
    yield pytest.param(attribute_values_document, id="attribute_values")
    for path in _provn_corpus_files():
        yield pytest.param(path, id=path.name)


@pytest.mark.parametrize("source", list(_corpus_sources()))
def test_lookup_agrees_with_valid_qualified_name(
    source: Path | Callable[[], ProvDocument],
) -> None:
    document = (
        ProvDocument.deserialize(str(source), format="provn")
        if isinstance(source, Path)
        else source()
    )
    # Spec 3, 3.4: the reader's one-walk resolution and the model's resolver
    # give the same object for every name a document holds.
    scopes: list[ProvBundle] = [document, *document.bundles]
    for bundle in scopes:
        for name in _held_names(bundle):
            assert bundle._lookup(name.namespace.prefix, name.localpart) is name
            if not name.namespace.prefix and ":" in name.localpart:
                # A bare local part with a colon has no string form the
                # resolver splits correctly; the lookup half covers it.
                continue
            resolved = bundle.valid_qualified_name(str(name))
            assert resolved == name
            assert resolved is not None and resolved.namespace is name.namespace


def test_lookup_corners() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://d.org/")
    doc.add_namespace("ex", "http://example.org/")
    bundle = doc.bundle("ex:b")
    assert doc._lookup("", "") is None
    assert doc._lookup("_", "x") is None
    doc.add_namespace("_", "http://blank.org/")
    assert doc._lookup("_", "x") is None
    assert doc._lookup("zz", "x") is None
    default = doc.get_default_namespace()
    assert default is not None
    assert doc._lookup("", "a:b") == default["a:b"]
    assert bundle._lookup("ex", "z") is doc.valid_qualified_name("ex:z")
    assert list(bundle.get_registered_namespaces()) == []


def test_a_foreign_namespace_that_takes_a_new_prefix_leaves_no_alias() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://w.org/")
    foreign = Namespace("ex", "http://x.org/")
    assert doc.add_namespace(foreign).prefix == "ex_1"

    named = doc.valid_qualified_name(foreign["a"])

    assert named is not None
    assert named.namespace.prefix == "ex_1"
    assert doc.valid_qualified_name("ex_2:z") is None
    assert doc._namespaces.lookup("ex_2", "z") is None


def test_a_bundle_default_bound_to_a_prefix_leaves_no_dn_alias() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://ex.org/")
    bundle = doc.bundle("ex:b")
    bundle.set_default_namespace("http://ex.org/")
    bundle.entity("e")

    flat = doc.flattened()

    assert [str(r.identifier) for r in flat.get_records()] == ["ex:e"]
    assert flat.valid_qualified_name("dn:x") is None
    assert flat._namespaces.lookup("dn", "x") is None
    assert flat._namespaces._unused_prefix_in_scope("dn") == "dn"


def test_update_gives_a_new_bundle_the_declarations_of_its_source(
    roundtrip: Roundtrip,
) -> None:
    source = ProvDocument()
    source.add_namespace("ex", "http://ex.example/")
    bundle = source.bundle("ex:b")
    bundle.set_default_namespace("http://b.example/")
    bundle.add_namespace("bb", "http://bb.example/")
    bundle.entity("e")
    bundle.entity("bb:f")

    target = ProvDocument()
    target.update(source)

    (copied,) = target.bundles
    default = copied.get_default_namespace()
    assert default is not None
    assert default.uri == "http://b.example/"
    assert [ns.prefix for ns in copied.get_registered_namespaces()] == ["bb"]
    assert target == source
    roundtrip(target)


def test_a_foreign_prefix_for_a_registered_iri_keeps_its_alias() -> None:
    doc = ProvDocument()
    bound = doc.add_namespace("ex", "http://a.example/")
    doc.entity(Namespace("foo", "http://a.example/")["x"])

    assert doc.valid_qualified_name("foo:y") == bound["y"]
    assert doc._namespaces.lookup("foo", "y") == bound["y"]


def test_a_bundle_default_in_the_built_in_prov_iri_flattens_as_prov() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://ex.example/")
    bundle = doc.bundle("ex:b")
    bundle.set_default_namespace(PROV.uri)
    bundle.entity("e")

    flat = doc.flattened()

    assert [str(r.identifier) for r in flat.get_records()] == ["prov:e"]


def test_a_bundle_default_flattens_under_the_prefix_the_bundle_binds_to_it() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://ex.example/")
    bundle = doc.bundle("ex:b")
    bundle.set_default_namespace("http://b.example/")
    bundle.add_namespace("bb", "http://b.example/")
    bundle.entity("bb:x")
    bundle.entity("y")

    flat = doc.flattened()

    assert [str(r.identifier) for r in flat.get_records()] == ["bb:x", "bb:y"]
    assert [ns.prefix for ns in flat.get_registered_namespaces()] == ["ex", "bb"]

"""Compacting a full IRI against a NamespaceManager's namespaces."""

import copy
import pickle
from functools import partial

import pytest

from prov.constants import PROV
from prov.identifier import Namespace
from prov.model import NamespaceManager, ProvDocument


@pytest.mark.parametrize("count", [50, 200])
def test_a_read_with_many_namespaces_scans_none(monkeypatch, count):
    manager = NamespaceManager()
    scans = 0

    def counting_values(self):
        nonlocal scans
        scans += 1
        return dict.values(self)

    monkeypatch.setattr(NamespaceManager, "values", counting_values)
    for i in range(count):
        iri = f"http://ex.org/run/{i}/out"
        assert manager.valid_qualified_name(iri) is None
        manager.add_namespace(Namespace(f"ns{i}", f"http://ex.org/run/{i}/"))
        assert str(manager.valid_qualified_name(iri)) == f"ns{i}:out"
    assert scans == 0


def _redefaulted():
    manager = NamespaceManager({"ex": "http://ex/"}, default="http://d1/")
    manager.set_default_namespace("http://d2/")
    return manager


def _bundle_under_a_document_prefix():
    document = ProvDocument()
    document.add_namespace("http", "urn:h:")
    bundle = document.bundle("http:b")
    bundle.add_namespace("a", "http://a/")
    return bundle._namespaces


_COMPACTING_ROWS = {
    "single": (
        partial(NamespaceManager, {"ex": "http://ex.org/"}),
        "http://ex.org/a",
        ("ex", "http://ex.org/a"),
    ),
    "nested-outer-first": (
        partial(NamespaceManager, {"o": "http://ex.org/", "i": "http://ex.org/a/"}),
        "http://ex.org/a/b",
        ("o", "http://ex.org/a/b"),
    ),
    "nested-inner-first": (
        partial(NamespaceManager, {"i": "http://ex.org/a/", "o": "http://ex.org/"}),
        "http://ex.org/a/b",
        ("i", "http://ex.org/a/b"),
    ),
    "default-local": (
        partial(NamespaceManager, default="http://d.org/"),
        "http://d.org/x",
        ("", "http://d.org/x"),
    ),
    # 2.x names an empty local part in the default namespace.
    "default-empty-local": (
        partial(NamespaceManager, default="http://d.org/"),
        "http://d.org/",
        ("", "http://d.org/"),
    ),
    "default-and-prefix-same-uri": (
        partial(NamespaceManager, {"ex": "http://ex/"}, default="http://ex/"),
        "http://ex/",
        ("", "http://ex/"),
    ),
    "prov-uri-under-second-prefix": (
        partial(NamespaceManager, {"p": PROV.uri}),
        PROV.uri + "Entity",
        ("prov", PROV.uri + "Entity"),
    ),
    "replaced-default": (_redefaulted, "http://d1/x", None),
    "no-match": (
        partial(NamespaceManager, {"ex": "http://ex.org/"}),
        "http://other.org/a",
        None,
    ),
    # The local part comes from replacing every occurrence of the URI.
    "uri-twice-in-the-iri": (
        partial(NamespaceManager, {"a": "http://a/"}),
        "http://a/http://a/x",
        ("a", "http://a/x"),
    ),
    # The enclosing scope's prefix does not read the text as its own name.
    "parent-scope": (
        _bundle_under_a_document_prefix,
        "http://a/x",
        ("a", "http://a/x"),
    ),
}


@pytest.mark.parametrize(
    ("setup", "text", "expected"), _COMPACTING_ROWS.values(), ids=_COMPACTING_ROWS
)
def test_compacting_a_full_iri_gives_the_scans_answer(setup, text, expected):
    name = setup().valid_qualified_name(text)
    assert (None if name is None else (name.namespace.prefix, name.uri)) == expected


def _without_index(document):
    # A pickle from a release without the index holds none.
    document._namespaces.__dict__.pop("_uris_by_length", None)
    return document


def _pickled(document):
    return pickle.loads(pickle.dumps(document, protocol=5))  # nosec B301


_COPIERS = {
    "pickle-5-old": lambda d: _pickled(_without_index(d)),
    "pickle-5-current": _pickled,
    "deepcopy": copy.deepcopy,
}


@pytest.mark.parametrize("copier", _COPIERS.values(), ids=_COPIERS)
def test_a_copied_or_old_manager_compacts(copier):
    document = ProvDocument()
    document.set_default_namespace("http://d.org/")
    document.add_namespace("ex", "http://ex.org/")
    copied = copier(document)
    assert str(copied.valid_qualified_name("http://ex.org/y")) == "ex:y"
    assert str(copied.valid_qualified_name("http://d.org/z")) == "z"

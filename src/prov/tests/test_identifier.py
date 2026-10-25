"""Exercises prov.identifier.Namespace edges not otherwise covered by the
serializer round-trip tests (planning/test-gap-checklist.md, T13), and
the local parts 3.3.0 rejects (#524)."""

import re
from typing import Any, cast

import pytest

from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import (
    ProvBundle,
    ProvDocument,
    ProvExceptionInvalidQualifiedName,
    ProvValueError,
)
from prov.tests.format_errors import READER_ERRORS


def test_namespace_rejects_empty_uri() -> None:
    with pytest.raises(ProvValueError):
        Namespace("ex", "")


def test_namespace_rejects_whitespace_only_uri() -> None:
    with pytest.raises(ProvValueError):
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


# The pattern that starts a reader's message for the record whose name is rejected.
_READ_WHERE = {
    "json": r"record 'ex:a b': ",
    "xml": r"line \d+, <prov:entity> 'ex:a b': ",
    "jsonld": r"prov:Entity 'ex:a b': ",
}


@pytest.mark.parametrize("fmt", list(_READ_WHERE))
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
        READER_ERRORS[fmt], match=f"^{_READ_WHERE[fmt]}{_message('a b')}$"
    ) as ctx:
        ProvDocument.deserialize(content=text.replace("a_b", "a b"), format=fmt)
    assert isinstance(ctx.value.__cause__, ProvExceptionInvalidQualifiedName)


_PREFIX_MESSAGE = "the prefix {!r} is not a PN_PREFIX, so no format can write it"


@pytest.mark.parametrize("prefix", ["ex", "a.b", "a-b", "a_b", "é", "a·b"])
def test_prefix_that_is_a_pn_prefix_is_accepted(prefix: str) -> None:
    assert Namespace(prefix, EX).prefix == prefix


@pytest.mark.parametrize(
    "prefix", ["1a", "_a", "_", "a.", ".a", "·a", "a b", "a\nb", "a:b", 'a"b']
)
def test_prefix_that_is_not_a_pn_prefix_is_rejected(prefix: str) -> None:
    # Every way to build a Namespace goes through the same check.
    message = f"^{re.escape(_PREFIX_MESSAGE.format(prefix))}$"
    with pytest.raises(ProvValueError, match=message) as ctx:
        Namespace(prefix, EX)
    assert isinstance(ctx.value, ValueError)
    with pytest.raises(ProvValueError, match=message):
        ProvDocument().add_namespace(prefix, EX)
    with pytest.raises(ProvValueError, match=message):
        ProvDocument(namespaces={prefix: EX})
    with pytest.raises(ProvValueError, match=message):
        ProvBundle(namespaces={prefix: EX})


_IRI_MESSAGE = "the namespace IRI {!r} cannot start with '@'"


def test_namespace_iri_starting_with_at_is_rejected() -> None:
    # Every entry point refuses it and names the IRI.
    message = f"^{re.escape(_IRI_MESSAGE.format('@foo/'))}$"
    with pytest.raises(ProvValueError, match=message):
        Namespace("ex", "@foo/")
    with pytest.raises(ProvValueError, match=message):
        ProvDocument().add_namespace("ex", "@foo/")
    with pytest.raises(ProvValueError, match=message):
        ProvDocument().set_default_namespace("@foo/")
    with pytest.raises(
        ProvValueError, match=f"^{re.escape(_IRI_MESSAGE.format('@type'))}$"
    ):
        Namespace("_type", "@type")


_RDF_PREFIXES = (
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
    'xmlns:prov="http://www.w3.org/ns/prov#" xmlns:_a="http://example.org/a/">'
)
# Case name -> format, the reader's extra arguments, document, whole message.
_PREFIX_DOCUMENTS = {
    "json document": (
        "json",
        {},
        '{"prefix": {"1a": "http://example.org/"}}',
        "prefix '1a', IRI 'http://example.org/': " + _PREFIX_MESSAGE.format("1a"),
    ),
    "json bundle": (
        "json",
        {},
        '{"prefix": {"ex": "http://example.org/"}, "bundle": {"ex:b": '
        '{"prefix": {"1a": "http://example.org/"}}}}',
        "prefix '1a', IRI 'http://example.org/': " + _PREFIX_MESSAGE.format("1a"),
    ),
    "json at sign": (
        "json",
        {},
        '{"prefix": {"ex": "@foo/"}}',
        "prefix 'ex', IRI '@foo/': " + _IRI_MESSAGE.format("@foo/"),
    ),
    "json null IRI": (
        "json",
        {},
        '{"prefix": {"ex": null}}',
        "prefix 'ex', IRI None: Not a valid URI to create a namespace.",
    ),
    "json default": (
        "json",
        {},
        '{"prefix": {"default": ""}}',
        "prefix 'default', IRI '': Not a valid URI to create a namespace.",
    ),
    "xml bundleContent, unused": (
        "xml",
        {},
        '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
        'xmlns:ex="http://example.org/">\n'
        '<prov:bundleContent prov:id="ex:b" xmlns:_a="http://example.org/a/"/>'
        "</prov:document>",
        "line 2, <prov:bundleContent> 'ex:b': " + _PREFIX_MESSAGE.format("_a"),
    ),
    "xml document element, at sign": (
        "xml",
        {},
        '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
        'xmlns:ex="@foo/">\n<prov:entity prov:id="ex:e"/></prov:document>',
        "line 2, <prov:entity> 'ex:e': " + _IRI_MESSAGE.format("@foo/"),
    ),
    "xml document element default, at sign": (
        "xml",
        {},
        '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
        'xmlns="@foo/">\n<prov:entity prov:id="e"/></prov:document>',
        "line 1, <prov:document>: " + _IRI_MESSAGE.format("@foo/"),
    ),
    "xml bundleContent default, at sign": (
        "xml",
        {},
        '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
        'xmlns:ex="http://example.org/">\n'
        '<prov:bundleContent prov:id="ex:b" xmlns="@foo/"/></prov:document>',
        "line 2, <prov:bundleContent> 'ex:b': " + _IRI_MESSAGE.format("@foo/"),
    ),
    "xml document element, underscore": (
        "xml",
        {},
        '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
        'xmlns:_a="http://example.org/a/">\n<prov:entity prov:id="_a:e"/>'
        "</prov:document>",
        "line 2, <prov:entity> '_a:e': " + _PREFIX_MESSAGE.format("_a"),
    ),
    "xml document element, trailing dot": (
        "xml",
        {},
        '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
        'xmlns:a.="http://example.org/a/">\n<prov:entity prov:id="a.:e"/>'
        "</prov:document>",
        "line 2, <prov:entity> 'a.:e': " + _PREFIX_MESSAGE.format("a."),
    ),
    "jsonld document": (
        "jsonld",
        {},
        '{"@context": {"1a": "http://example.org/"}, "@graph": []}',
        "prefix '1a', IRI 'http://example.org/': " + _PREFIX_MESSAGE.format("1a"),
    ),
    "jsonld bundle": (
        "jsonld",
        {},
        '{"@context": {"ex": "http://example.org/"}, "@graph": [{"@type": "Bundle", '
        '"@id": "ex:b", "@context": {"1a": "http://example.org/"}, "@graph": []}]}',
        "prefix '1a', IRI 'http://example.org/': " + _PREFIX_MESSAGE.format("1a"),
    ),
    "jsonld term definition": (
        "jsonld",
        {},
        '{"@context": {"ex": "http://example.org/", '
        '"ex:term": "http://example.org/term"}, "@graph": []}',
        "prefix 'ex:term', IRI 'http://example.org/term': "
        + _PREFIX_MESSAGE.format("ex:term"),
    ),
    "jsonld alias": (
        "jsonld",
        {},
        '{"@context": {"id": "@id"}, "@graph": []}',
        "prefix 'id', IRI '@id': " + _IRI_MESSAGE.format("@id"),
    ),
    "jsonld underscore alias": (
        "jsonld",
        {},
        '{"@context": {"_type": "@type"}, "@graph": []}',
        "prefix '_type', IRI '@type': " + _IRI_MESSAGE.format("@type"),
    ),
    "jsonld vocab alias": (
        "jsonld",
        {},
        '{"@context": {"@vocab": "@id"}, "@graph": []}',
        "prefix '@vocab', IRI '@id': " + _IRI_MESSAGE.format("@id"),
    ),
    "jsonld empty key alias": (
        "jsonld",
        {},
        '{"@context": {"": "@id"}, "@graph": []}',
        "prefix '', IRI '@id': " + _IRI_MESSAGE.format("@id"),
    ),
    "jsonld space": (
        "jsonld",
        {},
        '{"@context": {"a b": "http://example.org/"}, "@graph": []}',
        "prefix 'a b', IRI 'http://example.org/': " + _PREFIX_MESSAGE.format("a b"),
    ),
    "rdf xml": (
        "rdf",
        {"rdf_format": "xml"},
        _RDF_PREFIXES + '<rdf:Description rdf:about="http://example.org/a/e">'
        '<rdf:type rdf:resource="http://www.w3.org/ns/prov#Entity"/>'
        "</rdf:Description></rdf:RDF>",
        "prefix '_a', IRI 'http://example.org/a/': " + _PREFIX_MESSAGE.format("_a"),
    ),
    "rdf trig": (
        "rdf",
        {"rdf_format": "trig"},
        "@prefix prov: <http://www.w3.org/ns/prov#> .\n"
        "@prefix _a: <http://example.org/a/> .\n_a:e a prov:Entity .\n",
        "prefix '_a', IRI 'http://example.org/a/': " + _PREFIX_MESSAGE.format("_a"),
    ),
}


@pytest.mark.parametrize("name", list(_PREFIX_DOCUMENTS))
def test_prefix_raises_when_read(name: str) -> None:
    # The readers build the Namespace, so each raises its own error naming the
    # declaration, with the model's error as the cause.
    fmt, kwargs, text, message = _PREFIX_DOCUMENTS[name]
    with pytest.raises(READER_ERRORS[fmt], match=f"^{re.escape(message)}$") as ctx:
        ProvDocument.deserialize(content=text, format=fmt, **kwargs)
    assert isinstance(ctx.value.__cause__, ProvValueError)


@pytest.mark.parametrize(
    ("declaration", "iri"),
    [('"ex": 5', "5"), ('"ex": ["x"]', "['x']"), ('"default": 5', "5")],
)
def test_json_namespace_iri_that_is_not_a_string_is_rejected(
    declaration: str, iri: str
) -> None:
    # The reader refuses it with its own error, so there is no cause.
    prefix = declaration.split('"')[1]
    message = (
        f"^prefix {prefix!r}, IRI {re.escape(iri)}: a namespace IRI must be a string$"
    )
    with pytest.raises(READER_ERRORS["json"], match=message) as ctx:
        ProvDocument.deserialize(
            content="{" + f'"prefix": {{{declaration}}}' + "}", format="json"
        )
    assert ctx.value.__cause__ is None


def test_jsonld_context_keywords_are_not_namespaces() -> None:
    # A keyword other than @vocab, even one holding an '@' string, is skipped.
    text = (
        '{"@context": [{"ex": "http://example.org/", "@base": "@x", '
        '"@version": 1.1, "@language": "en"}], "@graph": []}'
    )
    document = ProvDocument.deserialize(content=text, format="jsonld")
    assert {namespace.prefix for namespace in document.namespaces} == {"ex"}
    assert document.default_ns_uri is None

"""PROV-N parser tests: document structure, every expression form, literal
forms, error paths and equality with documents the writer produced.
Profile behaviour (default, lenient) is in test_provn_profiles.py."""

import datetime
import io
import re
import warnings
from typing import Any

import pytest

from prov.constants import PROV, PROV_ALTERNATE, XSD, XSI
from prov.model import (
    PROV_REC_CLS,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvException,
    ProvMention,
    ProvWarning,
)
from prov.serializers.provn_lexer import ProvNSyntaxError
from prov.serializers.provn_parser import (
    _ELEMENTS,
    _MENTION,
    _RELATIONS,
    PROFILES,
    ProvNParser,
)
from prov.tests import examples
from prov.tests.conftest import no_future_rejection

PREFIXES = "prefix ex <http://example.org/>\nprefix dc <http://purl.org/dc/terms/>\n"


def parse(body, profile="strict", prefixes=PREFIXES):
    return ProvNParser(f"document\n{prefixes}{body}\nendDocument", profile).parse()


def only_record(doc: ProvBundle) -> Any:
    records = list(doc.get_records())
    assert len(records) == 1
    return records[0]


def test_empty_document() -> None:
    doc = ProvNParser("document endDocument", "strict").parse()
    assert list(doc.get_records()) == []


def test_prefix_and_default_declarations() -> None:
    doc = parse(
        "entity(e1)\nentity(ex:e2)", prefixes="default <http://d.org/>\n" + PREFIXES
    )
    ids = sorted(str(r.identifier) for r in doc.get_records())
    assert ids == ["e1", "ex:e2"]
    assert doc.get_default_namespace().uri == "http://d.org/"


@pytest.mark.parametrize(
    ("text", "keyword", "n_formal"),
    [
        ("entity(ex:e1)", "entity", 0),
        ("activity(ex:a1)", "activity", 0),
        ("activity(ex:a1, 2011-11-16T16:05:00, 2011-11-16T16:06:00)", "activity", 2),
        ("activity(ex:a1, -, -)", "activity", 0),
        ("agent(ex:ag)", "agent", 0),
        ("wasGeneratedBy(ex:e1)", "wasGeneratedBy", 1),
        ("wasGeneratedBy(ex:e1, ex:a1, 2011-11-16T16:05:00)", "wasGeneratedBy", 3),
        ("wasGeneratedBy(ex:g1; ex:e1, -, -)", "wasGeneratedBy", 1),
        ("used(ex:a1)", "used", 1),
        ("used(ex:u1; ex:a1, ex:e1, -)", "used", 2),
        ("wasInformedBy(ex:a2, ex:a1)", "wasInformedBy", 2),
        ("wasStartedBy(ex:a1)", "wasStartedBy", 1),
        ("wasStartedBy(ex:a1, ex:e1, ex:a0, 2011-11-16T16:05:00)", "wasStartedBy", 4),
        ("wasEndedBy(ex:a1, -, ex:a0, -)", "wasEndedBy", 2),
        ("wasInvalidatedBy(ex:e1, ex:a1, -)", "wasInvalidatedBy", 2),
        ("wasDerivedFrom(ex:e2, ex:e1)", "wasDerivedFrom", 2),
        ("wasDerivedFrom(ex:e2, ex:e1, ex:a, ex:g2, ex:u1)", "wasDerivedFrom", 5),
        ("wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)", "wasDerivedFrom", 2),
        ("wasAttributedTo(ex:e1, ex:ag)", "wasAttributedTo", 2),
        ("wasAssociatedWith(ex:a1)", "wasAssociatedWith", 1),
        ("wasAssociatedWith(ex:a1, ex:ag, ex:plan)", "wasAssociatedWith", 3),
        ("actedOnBehalfOf(ex:ag2, ex:ag1)", "actedOnBehalfOf", 2),
        ("actedOnBehalfOf(ex:ag2, ex:ag1, ex:a1)", "actedOnBehalfOf", 3),
        ("wasInfluencedBy(ex:e2, ex:e1)", "wasInfluencedBy", 2),
        ("alternateOf(ex:e1, ex:e2)", "alternateOf", 2),
        ("specializationOf(ex:e1, ex:e2)", "specializationOf", 2),
        ("hadMember(ex:c, ex:e)", "hadMember", 2),
        ("prov:mentionOf(ex:e1, ex:e0, ex:b)", "prov:mentionOf", 3),
    ],
)
def test_every_expression_form(text, keyword, n_formal) -> None:
    record = only_record(parse(text))
    assert len([v for _, v in record.formal_attributes if v is not None]) == n_formal
    assert text.split("(")[0] == keyword
    if keyword == "prov:mentionOf":
        expected_type = _MENTION[0]
    else:
        expected_type = _ELEMENTS.get(keyword, _RELATIONS.get(keyword))[0]
    assert record.get_type() == expected_type


def test_relation_identifier_is_kept() -> None:
    record = only_record(parse("wasGeneratedBy(ex:g1; ex:e1, ex:a1, -)"))
    assert str(record.identifier) == "ex:g1"


def test_formal_time_is_a_datetime() -> None:
    record = only_record(parse("used(ex:a1, ex:e1, 2011-11-16T16:05:00Z)"))
    (time,) = [v for k, v in record.formal_attributes if str(k) == "prov:time"]
    assert time == datetime.datetime(2011, 11, 16, 16, 5, tzinfo=datetime.UTC)


def test_mention_maps_to_prov_mention() -> None:
    record = only_record(parse("prov:mentionOf(ex:e1, ex:e0, ex:b)"))
    assert isinstance(record, ProvMention)


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ('"plain"', "plain"),
        ('"""two\nlines"""', "two\nlines"),
        ("42", 42),
        ('"1" %% xsd:int', 1),
        ('"2.5" %% xsd:double', 2.5),
        ('"1" %% xsd:boolean', True),
        ('"5000000000" %% xsd:long', 5000000000),
        ("'ex:abc'", "QNAME"),
        ('"a place"@en', Literal("a place", langtag="en")),
        (
            '"2019-03-27T12:52:02" %% xsd:dateTime',
            datetime.datetime(2019, 3, 27, 12, 52, 2),
        ),
    ],
)
def test_literal_forms(literal, expected) -> None:
    record = only_record(parse(f"entity(ex:e1, [ex:v={literal}])"))
    (value,) = record.get_attribute("ex:v")
    if expected == "QNAME":
        assert str(value) == "ex:abc"
    else:
        assert value == expected


def test_writer_spells_booleans_as_words() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", {"ex:yes": True, "ex:no": False})
    provn = doc.get_provn()
    assert 'ex:yes="true" %% xsd:boolean' in provn
    assert 'ex:no="false" %% xsd:boolean' in provn
    assert (
        ProvDocument.deserialize(content=provn, format="provn", profile="strict") == doc
    )


def test_literal_equivalence_with_json() -> None:
    body = (
        'entity(ex:e1, [ex:s="x", ex:i=1, ex:f="1.5" %% xsd:double, ex:q=\'ex:q1\','
        ' ex:l="un lieu"@fr, ex:t="2019-03-27T12:52:02" %% xsd:dateTime])'
    )
    doc = parse(body)
    reloaded = ProvDocument.deserialize(
        content=doc.serialize(format="json"), format="json"
    )
    assert doc == reloaded


def test_bare_identifier_with_escaped_colon_resolves_via_default() -> None:
    # A bare (unprefixed) identifier whose local part contains an escaped
    # ':' can't be turned back into 'prefix:local' text without looking
    # like a (wrong) prefixed name, so it must stay resolved rather than
    # round-tripping through a reconstructed string.
    doc = parse(r"entity(a\:b)", prefixes="default <http://d.org/>\n" + PREFIXES)
    record = only_record(doc)
    assert str(record.identifier) == "a:b"
    assert record.identifier.uri == "http://d.org/a:b"


def test_bare_escaped_colon_name_in_bundle_adopts_the_enclosing_default() -> None:
    # Accepted, documented limitation: a bare local part with an escaped
    # ':' can't go through the string-based resolution path (it would be
    # mis-split at the colon), so it resolves eagerly against the document's
    # default and, unlike a plain bare name, the bundle then adopts that
    # default as its own on this path -- see the comment in
    # ProvNParser._identifier_text().
    doc = parse(
        "bundle ex:b\n  entity(a\\:b)\nendBundle",
        prefixes="default <http://d.org/>\nprefix ex <http://example.org/>\n",
    )
    (bundle,) = doc.bundles
    record = only_record(bundle)
    assert record.identifier.uri == "http://d.org/a:b"
    assert bundle.get_default_namespace().uri == "http://d.org/"
    reloaded = ProvDocument.deserialize(content=doc.get_provn(), format="provn")
    assert reloaded == doc


def test_qname_literal_with_escaped_colon_resolves_via_default() -> None:
    # Same shape as test_bare_identifier_with_escaped_colon_resolves_via_default,
    # but for a QNAME_LITERAL attribute *value* ('a\:b') rather than an
    # identifier position: the bare local part "a:b" must not be re-split
    # on its escaped ':' by valid_qualified_name()'s string-based lookup.
    doc = ProvDocument()
    doc.set_default_namespace("http://def/")
    doc.add_namespace("ex", "http://ex/")
    doc.entity("ex:e", {"ex:v": doc.get_default_namespace()["a:b"]})

    reloaded = ProvDocument.deserialize(content=doc.get_provn(), format="provn")
    assert reloaded == doc


def test_qname_literal_with_escaped_colon_ignores_a_colliding_prefix() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://def/")
    doc.add_namespace("ex", "http://ex/")
    doc.add_namespace("a", "http://other/")
    doc.entity("ex:e", {"ex:v": doc.get_default_namespace()["a:b"]})

    reloaded = ProvDocument.deserialize(content=doc.get_provn(), format="provn")
    assert reloaded == doc


def test_multiple_attributes_and_repeated_keys() -> None:
    record = only_record(parse('entity(ex:e1, [prov:type="a", prov:type="b", ex:k=1])'))
    assert record.get_attribute("prov:type") == {"a", "b"}


def test_bundle_with_own_prefixes() -> None:
    body = "bundle ex:b1\n  prefix bob <http://bob.org/>\n  entity(bob:e1)\nendBundle"
    doc = parse(body)
    (bundle,) = doc.bundles
    assert str(bundle.identifier) == "ex:b1"
    assert str(only_record(bundle).identifier) == "bob:e1"
    assert "bob" not in {ns.prefix for ns in doc.get_registered_namespaces()}
    # "ex" is a document-level prefix, not one of the bundle's own -- using
    # it to spell the bundle's own identifier must not redundantly copy it
    # onto the bundle too.
    assert "ex" not in {ns.prefix for ns in bundle.get_registered_namespaces()}


def test_bundle_bare_name_uses_document_default() -> None:
    doc = parse(
        "bundle ex:b1\n  entity(e1)\nendBundle",
        prefixes="default <http://d.org/>\n" + PREFIXES,
    )
    (bundle,) = doc.bundles
    assert only_record(bundle).identifier.uri == "http://d.org/e1"


def test_bundle_identifier_resolves_against_its_own_prefix() -> None:
    # PROV-N 3.1.3: the bundle identifier is interpreted with the bundle's
    # own declarations, not just the document's -- bx is only declared
    # inside the bundle.
    body = "bundle bx:b1\n  prefix bx <http://bundle.org/>\n  entity(bx:e1)\nendBundle"
    doc = parse(body)
    (bundle,) = doc.bundles
    assert str(bundle.identifier) == "bx:b1"
    assert str(only_record(bundle).identifier) == "bx:e1"
    assert "bx" not in {ns.prefix for ns in doc.get_registered_namespaces()}


def test_bundle_local_prefix_json_round_trip() -> None:
    import json

    source = ProvDocument.deserialize(
        content=json.dumps(
            {
                "prefix": {"ex": "http://example.org/"},
                "bundle": {
                    "bx:b1": {
                        "prefix": {"bx": "http://bundle.org/"},
                        "entity": {"bx:e1": {}},
                    }
                },
            }
        ),
        format="json",
    )
    reloaded = ProvNParser(source.get_provn(), "default").parse()
    assert reloaded == source
    assert "bx" not in {ns.prefix for ns in reloaded.get_registered_namespaces()}


def test_bundle_without_own_default_gains_none_on_reparse() -> None:
    # A bare name inside a bundle resolves against the document's default
    # namespace (via NamespaceManager's parent delegation) without that
    # delegation being cached as the bundle's own default.
    doc = parse(
        "bundle ex:b\n  entity(e1)\nendBundle",
        prefixes="default <http://d.org/>\n" + PREFIXES,
    )
    (bundle,) = doc.bundles
    assert bundle.get_default_namespace() is None
    inside_bundle = doc.get_provn().split("bundle ex:b")[1].split("endBundle")[0]
    assert "default " not in inside_bundle


def test_bundle_bare_name_with_no_default_anywhere_still_raises() -> None:
    with pytest.raises(ProvNSyntaxError, match="no default namespace declared"):
        parse("bundle ex:b1\n  entity(e1)\nendBundle")


def test_comments_anywhere() -> None:
    doc = parse("entity(ex:e1) // trailing\n/* block */ entity(ex:e2)")
    assert len(list(doc.get_records())) == 2


@pytest.mark.parametrize(
    ("body", "message", "line"),
    [
        ("entity(ex:e1)", "expected 'endDocument'", None),  # closing removed below
        ("foo(ex:e1)", "unknown statement keyword 'foo'", 4),
        ("ex:custom(ex:e1)", "extensibility expression", 4),
        ("wasGeneratedBy(ex:e1, ex:a1)", "takes 1 or 3 arguments, got 2", 4),
        ("used(ex:a1, 2011-11-16T16:05:00, -)", "expected an identifier", 4),
        ("entity(zz:e1)", "prefix 'zz' is not declared", 4),
        ("entity(e1)", "no default namespace", 4),
        ("entity(ex:e1, [ex:k=1)", "expected ']'", 4),
        (
            "bundle ex:b\n bundle ex:c\n endBundle\nendBundle",
            "cannot contain a bundle",
            5,
        ),
        ("entity(ex:e1,, [])", "expected an identifier, a time or '-'", 4),
        ("entity(ex:e1) endDocument entity(ex:e2)", "after 'endDocument'", 4),
    ],
)
def test_errors_name_the_problem_and_position(body, message, line) -> None:
    if line is None:
        text = f"document\n{PREFIXES}{body}"  # no endDocument
        with pytest.raises(ProvNSyntaxError, match=message):
            ProvNParser(text, "strict").parse()
        return
    with pytest.raises(ProvNSyntaxError) as ctx:
        parse(body)
    assert message in str(ctx.value)
    assert ctx.value.line == line


EX_PREFIX = "prefix ex <http://example.org/>\n"
STATEMENT_PREFIX = f"document\n{EX_PREFIX}"
EVERY = PROFILES
STRICT = ("strict",)
# Rejected inside a statement, so the lenient profile skips the statement.
STATEMENT = ("strict", "default")


# The declarations and whitespace the reader rejects (#508, #509, #510, #511,
# #519 a and d): the document, the profiles that reject it, the message and
# the line and column of the ProvNSyntaxError.
REJECTED_DOCUMENTS = [
    pytest.param(
        "document\ndefault <http://a/>\ndefault <http://b/>\nentity(e)\nendDocument",
        EVERY,
        "'default' is declared twice in this scope",
        (3, 1),
        508,
        id="repeated default",
    ),
    *[
        pytest.param(
            f"document\nprefix {name} <http://x/>\n{EX_PREFIX}entity(ex:e)\nendDocument",
            EVERY,
            f"'{name}' is not a PROV-N prefix name",
            (2, 8),
            511,
            id=f"prefix {name}",
        )
        for name in ("_", "a/b", "1a")
    ],
    pytest.param(
        f"document\n{EX_PREFIX}default <http://d/>\nentity(ex:e)\nendDocument",
        STRICT,
        "'default' follows a 'prefix' declaration",
        (3, 1),
        519,
        id="default after prefix",
    ),
    *[
        pytest.param(
            f"document\nprefix {ns.prefix} <{ns.uri}>\n{EX_PREFIX}entity(ex:e)\nendDocument",
            STRICT,
            f"prefix '{ns.prefix}' is predeclared",
            (2, 8),
            519,
            id=f"declares {ns.prefix}",
        )
        for ns in (PROV, XSD)
    ],
    pytest.param(
        f"document\n{EX_PREFIX}entity(ex:e)\xa0\nendDocument\n",
        EVERY,
        "U+00A0 is not PROV-N whitespace",
        (3, 13),
        509,
        id="no-break space",
    ),
    pytest.param(
        "document\ndefault <http://a/>\ndefault <http://b/>\nentity(e)\xa0\nendDocument\n",
        EVERY,
        "U+00A0 is not PROV-N whitespace",
        (4, 10),
        509,
        id="whitespace before a repeated default",
    ),
    pytest.param(
        f'document\n{EX_PREFIX}entity(ex:e, [xsi:type="ex:T"])\nendDocument',
        STATEMENT,
        "cannot resolve 'xsi:type': prefix 'xsi' is not declared",
        (3, 15),
        510,
        id="undeclared xsi",
    ),
    # Statement rules (#523, #519 b and c). An attribute named after one of
    # the statement's own arguments is rejected at the attribute; under
    # strict, a statement after a bundle at the statement, and an identifier
    # or an attribute block on a bare relation at that identifier or '['.
    *[
        pytest.param(
            f"{STATEMENT_PREFIX}{statement}\nendDocument",
            STATEMENT,
            f"'prov:{formal}' names the '{formal}' argument of '{keyword}',"
            " which PROV-N gives only by position",
            (3, statement.index("[prov:") + 2),
            523,
            id=label,
        )
        for statement, keyword, formal, label in (
            (
                "wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])",
                "wasGeneratedBy",
                "activity",
                "argument given as an attribute",
            ),
            (
                "wasGeneratedBy(ex:e, ex:a, -, [prov:activity='ex:a'])",
                "wasGeneratedBy",
                "activity",
                "argument repeated as an attribute",
            ),
            (
                "wasGeneratedBy(ex:e, ex:a, -, [prov:activity='ex:b'])",
                "wasGeneratedBy",
                "activity",
                "argument contradicted by an attribute",
            ),
            (
                'activity(ex:a, -, -, [prov:startTime="2011-11-16T16:05:00"])',
                "activity",
                "startTime",
                "time argument given as an attribute",
            ),
        )
    ],
    pytest.param(
        "document\nprefix ex <http://example.org/>\n"
        "prefix p <http://www.w3.org/ns/prov#>\n"
        "wasGeneratedBy(ex:e, -, -, [p:activity='ex:a'])\nendDocument",
        STATEMENT,
        "'p:activity' names the 'activity' argument of 'wasGeneratedBy'",
        (4, 29),
        523,
        id="argument matched by name, not spelling",
    ),
    pytest.param(
        f"{STATEMENT_PREFIX}bundle ex:b\nentity(ex:e)\nendBundle\n"
        "entity(ex:f)\nendDocument",
        STRICT,
        "a statement follows a bundle, which the strict profile does not allow",
        (6, 1),
        519,
        id="statement after a bundle",
    ),
    *[
        pytest.param(
            f"{STATEMENT_PREFIX}{statement}\nendDocument",
            STRICT,
            f"'{keyword}' has {what}, which the strict profile does not allow",
            (3, statement.index(marker) + 1),
            519,
            id=label,
        )
        for keyword, statement, what, marker, label in (
            (
                "hadMember",
                "hadMember(ex:m; ex:c, ex:e)",
                "an identifier",
                "ex:m",
                "hadMember with an identifier",
            ),
            (
                "hadMember",
                "hadMember(-; ex:c, ex:e)",
                "an identifier",
                "-",
                "hadMember with a marker",
            ),
            (
                "alternateOf",
                "alternateOf(ex:a; ex:e2, ex:e1)",
                "an identifier",
                "ex:a",
                "alternateOf with an identifier",
            ),
            (
                "specializationOf",
                'specializationOf(ex:e2, ex:e1, [ex:k="x"])',
                "an attribute block",
                "[",
                "specializationOf with attributes",
            ),
            (
                "alternateOf",
                "alternateOf(ex:e2, ex:e1, [])",
                "an attribute block",
                "[",
                "alternateOf with an empty attribute block",
            ),
            (
                "hadMember",
                'hadMember(ex:m; ex:c, ex:e, [ex:k="x"])',
                "an identifier",
                "ex:m",
                "hadMember with both, rejected at the identifier",
            ),
        )
    ],
]


@pytest.mark.parametrize(
    ("text", "profiles", "message", "position", "issue"), REJECTED_DOCUMENTS
)
def test_reader_rejects(text, profiles, message, position, issue) -> None:
    for profile in profiles:
        with pytest.raises(ProvNSyntaxError) as ctx:
            ProvDocument.deserialize(content=text, format="provn", profile=profile)
        assert message in str(ctx.value), profile
        assert (ctx.value.line, ctx.value.column) == position, profile
    if profiles == STATEMENT:
        # The lenient profile skips the statement with the same text at the
        # same position, warns about nothing else and reads nothing from it.
        line, column = position
        with pytest.warns(
            ProvWarning,
            match=f"skipped: line {line}, column {column}: {re.escape(message)}",
        ) as caught:
            document = ProvDocument.deserialize(
                content=text, format="provn", profile="lenient"
            )
        assert len(caught) == 1
        assert not list(document.get_records())


# Declarations each profile reads without a message (#508, #511, #519 a and d,
# #510): the declaration block and the profiles that accept it.
ACCEPTED_DECLARATIONS = [
    pytest.param("default <http://a/>\n", EVERY, id="one default"),
    *[
        pytest.param(f"prefix {name} <http://x/>\n", EVERY, id=f"prefix {name}")
        for name in ("a.b", "a_b", "a-1")
    ],
    pytest.param(
        f"{EX_PREFIX}default <http://d/>\n",
        ("default", "lenient"),
        id="default after prefix",
    ),
    pytest.param(
        f"default <http://d/>\n{EX_PREFIX}", EVERY, id="default before prefix"
    ),
    *[
        pytest.param(
            f"prefix {ns.prefix} <{ns.uri}>\n",
            ("default", "lenient"),
            id=f"declares {ns.prefix}",
        )
        for ns in (PROV, XSD)
    ],
    pytest.param(f"prefix xsi <{XSI.uri}>\n", EVERY, id="declares xsi at its XML IRI"),
    pytest.param(
        "prefix xsi <http://other/>\n", EVERY, id="declares xsi at another IRI"
    ),
]


@pytest.mark.parametrize(("declarations", "profiles"), ACCEPTED_DECLARATIONS)
def test_reader_accepts_declarations(declarations, profiles) -> None:
    for profile in profiles:
        with no_future_rejection():
            ProvDocument.deserialize(
                content=f"document\n{declarations}endDocument",
                format="provn",
                profile=profile,
            )


# Statements each profile reads with no warning of any kind (#523, #519 b
# and c): the statement block and the profiles that accept it.
ACCEPTED_STATEMENTS = [
    pytest.param(
        "wasGeneratedBy(ex:e, ex:a, -, [prov:role='ex:r'])",
        EVERY,
        id="reserved attribute that is not an argument",
    ),
    pytest.param(
        "entity(ex:f)\nbundle ex:b\nentity(ex:e)\nendBundle",
        EVERY,
        id="statement before a bundle",
    ),
    pytest.param(
        "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)",
        ("default", "lenient"),
        id="statement after a bundle",
    ),
    *[
        pytest.param(statement, ("default", "lenient"), id=label)
        for statement, label in (
            ("hadMember(ex:m; ex:c, ex:e)", "hadMember with an identifier"),
            ("hadMember(-; ex:c, ex:e)", "hadMember with a marker"),
            ("alternateOf(ex:a; ex:e2, ex:e1)", "alternateOf with an identifier"),
            (
                'specializationOf(ex:e2, ex:e1, [ex:k="x"])',
                "specializationOf with attributes",
            ),
            ("alternateOf(ex:e2, ex:e1, [])", "alternateOf with an empty block"),
        )
    ],
    pytest.param(
        'wasDerivedFrom(ex:d; ex:e2, ex:e1, [ex:k="x"])',
        EVERY,
        id="identifier and attributes on a derivation",
    ),
    pytest.param(
        "prov:mentionOf(ex:m; ex:e2, ex:e1, ex:b)",
        EVERY,
        id="identifier on a mention",
    ),
]


@pytest.mark.parametrize(("body", "profiles"), ACCEPTED_STATEMENTS)
def test_reader_accepts_statements(body, profiles) -> None:
    for profile in profiles:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ProvWarning)
            ProvDocument.deserialize(
                content=f"{STATEMENT_PREFIX}{body}\nendDocument",
                format="provn",
                profile=profile,
            )


def test_strict_rejects_bare_mention_with_a_hint() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        parse("mentionOf(ex:e1, ex:e0, ex:b)")
    assert "unknown statement keyword 'mentionOf'" in ctx.value.message
    assert "prov:mentionOf" in ctx.value.message
    assert "profile='default'" in ctx.value.message


def test_model_errors_carry_the_statement_position() -> None:
    # A membership whose collection identifier resolves but the record
    # constructor rejects (an element with no identifier cannot happen via
    # the grammar; a relation to a bundle-typed value can), so exercise the
    # generic wrapping with a time literal the model cannot parse.
    with pytest.raises(ProvNSyntaxError) as ctx:
        parse("used(ex:a1, ex:e1, 2011-13-40T99:00:00)")
    assert ctx.value.line == 4


def test_unknown_profile_rejected() -> None:
    with pytest.raises(ValueError, match="profile"):
        ProvNParser("document endDocument", "loose")


def test_arity_table_matches_formal_attributes() -> None:
    for rec_type, arities in [*_ELEMENTS.values(), *_RELATIONS.values(), _MENTION]:
        assert max(arities) == len(PROV_REC_CLS[rec_type].FORMAL_ATTRIBUTES)


def test_document_missing_keyword_reports_expected_document() -> None:
    with pytest.raises(ProvNSyntaxError, match="expected 'document'"):
        ProvNParser("entity(ex:e1)", "strict").parse()


def test_prefix_declaration_rejects_a_qualified_name() -> None:
    with pytest.raises(ProvNSyntaxError, match="expected a prefix"):
        ProvNParser(
            "document\nprefix ex:x <http://example.org/>\nendDocument", "strict"
        ).parse()


def test_prefix_declaration_rejects_redeclaring_a_reserved_prefix() -> None:
    with pytest.raises(ProvNSyntaxError, match="reserved") as ctx:
        ProvNParser(
            "document\nprefix xsd <http://example.org/other#>\nendDocument", "strict"
        ).parse()
    assert ctx.value.line == 2


OTHER_XSI = "document\nprefix ex <http://example.org/>\nprefix xsi <http://other/>\n"


XSI_ROUND_TRIP_RECORD = "entity(xsi:e, [ex:t=\"1\" %% xsi:t, xsi:k='xsi:v'])"


def _datatype_uri(doc):
    (record,) = [r for r in doc.get_records() if r.identifier is not None]
    attributes = {name.uri: value for name, value in record.extra_attributes}
    return attributes["http://example.org/t"].datatype.uri


@pytest.mark.parametrize("target", ["provn", "json"])
def test_declared_xsi_round_trips_through_the_writers(target) -> None:
    doc = ProvNParser(
        OTHER_XSI + XSI_ROUND_TRIP_RECORD + "\nendDocument", "strict"
    ).parse()
    assert _datatype_uri(doc) == "http://other/t"
    (record,) = [r for r in doc.get_records() if r.identifier is not None]
    assert record.identifier.uri == "http://other/e"
    content = doc.serialize(format=target)
    # xsi is an ordinary prefix: a document that binds it to another IRI is
    # written back under its own name, not renamed away from a built-in.
    assert "xsi_1" not in content
    if target == "provn":
        assert "prefix xsi <http://other/>" in content
    reloaded = ProvDocument.deserialize(content=content, format=target)
    assert reloaded == doc
    assert _datatype_uri(reloaded) == "http://other/t"


@pytest.mark.parametrize("target", ["provn", "json"])
def test_declared_xsi_round_trips_through_the_writers_at_bundle_scope(target) -> None:
    doc = ProvNParser(
        "document\nprefix ex <http://example.org/>\nbundle ex:b\n"
        "prefix xsi <http://other/>\n"
        + XSI_ROUND_TRIP_RECORD
        + "\nendBundle\nendDocument",
        "strict",
    ).parse()
    (bundle,) = doc.bundles
    assert _datatype_uri(bundle) == "http://other/t"
    content = doc.serialize(format=target)
    reloaded = ProvDocument.deserialize(content=content, format=target)
    assert reloaded == doc
    (reloaded_bundle,) = reloaded.bundles
    assert _datatype_uri(reloaded_bundle) == "http://other/t"


def test_prefix_declaration_accepts_redeclaring_prov_to_its_own_iri() -> None:
    record = only_record(
        ProvNParser(
            f"document\nprefix prov <{PROV.uri}>\nentity(prov:e1)\nendDocument",
            "default",
        ).parse()
    )
    assert str(record.identifier) == "prov:e1"


def test_bare_all_digit_local_name_is_an_identifier() -> None:
    # [53] PN_LOCAL allows a leading digit, so an unprefixed, all-digit
    # local name is a valid identifier, not an integer literal.
    doc = parse("entity(4567)", prefixes="default <http://example.org/>\n")
    record = only_record(doc)
    assert str(record.identifier) == "4567"


def test_bare_all_digit_local_name_as_a_relation_argument() -> None:
    doc = parse("wasDerivedFrom(4567, e1)", prefixes="default <http://example.org/>\n")
    record = only_record(doc)
    subject, target = (value for _, value in record.formal_attributes[:2])
    assert str(subject) == "4567"
    assert str(target) == "e1"


@pytest.mark.parametrize("profile", ["strict", "default"])
def test_signed_digit_run_is_not_an_identifier(profile) -> None:
    # PN_LOCAL allows a leading digit but not an unescaped '-', so a signed
    # INT token ('-4567') must still be rejected as an identifier, not
    # re-kinded to a bare local name the way an unsigned one is.
    with pytest.raises(ProvNSyntaxError, match="expected an identifier"):
        parse(
            "entity(-4567)", profile=profile, prefixes="default <http://example.org/>\n"
        )


def test_signed_int_is_still_an_integer_in_an_attribute_value() -> None:
    doc = parse(
        "entity(e1, [prov:value=-42])", prefixes="default <http://example.org/>\n"
    )
    record = only_record(doc)
    (value,) = (v for k, v in record.attributes if str(k) == "prov:value")
    assert value == -42


def test_strict_requires_an_identifier_at_the_named_position() -> None:
    with pytest.raises(ProvNSyntaxError, match="'hadMember' requires an identifier"):
        parse("hadMember(-, -)")
    # default keeps the model's own scruffy-statement policy (#257): both
    # markers are accepted, producing a membership with no formal values set.
    record = only_record(parse("hadMember(-, -)", profile="default"))
    assert all(value is None for _, value in record.formal_attributes)


def test_strict_still_accepts_wasderivedfrom_with_trailing_markers() -> None:
    record = only_record(parse("wasDerivedFrom(ex:e2, ex:e1, -, -, -)"))
    assert record.get_type() == _RELATIONS["wasDerivedFrom"][0]


def test_unterminated_bundle_reports_end_of_input() -> None:
    with pytest.raises(ProvNSyntaxError, match="expected 'endBundle'"):
        ProvNParser(
            f"document\n{PREFIXES}bundle ex:b\n  entity(ex:e1)", "strict"
        ).parse()


def test_semicolon_marker_leaves_identifier_unset() -> None:
    # Grammar [10]/[11]: identifierOrMarker ';' -- the Recommendation's own
    # example is used(-; ex:a1, ex:e1, -).
    record = only_record(parse("used(-; ex:a1, ex:e1, -)"))
    assert record.identifier is None


def test_semicolon_identifier_must_be_a_name_or_marker() -> None:
    with pytest.raises(ProvNSyntaxError, match="expected an identifier before ';'"):
        parse("used(2011-11-16T16:05:00; ex:a1, ex:e1, -)")


def test_time_attribute_rejects_a_non_datetime_argument() -> None:
    with pytest.raises(ProvNSyntaxError, match="expected a time"):
        parse("wasGeneratedBy(ex:e1, ex:a1, ex:notatime)")


@pytest.mark.parametrize(
    "statement",
    [
        'entity(ex:e1, [prov:time="2012-01-01T00:00:00" %% xsd:dateTime])',
        "wasGeneratedBy(ex:e1, ex:a1, -,"
        ' [prov:time="2012-01-01T00:00:00" %% xsd:dateTime])',
    ],
)
def test_time_attribute_accepts_a_typed_datetime_literal(statement) -> None:
    record = only_record(parse(statement))
    assert record.get_attribute("prov:time") == {datetime.datetime(2012, 1, 1)}


def test_empty_attribute_list() -> None:
    record = only_record(parse("entity(ex:e1, [])"))
    assert record.attributes == []


def test_resync_stops_at_a_prefixed_mention() -> None:
    doc = parse("foo(ex:e1)\nprov:mentionOf(ex:e2, ex:e0, ex:b)", profile="lenient")
    (record,) = list(doc.get_records())
    assert isinstance(record, ProvMention)


def test_lenient_skip_is_recorded_for_the_caller_to_warn_with() -> None:
    # ProvNParser itself only records skipped statements (on .skipped); it
    # is ProvNSerializer.deserialize() that turns them into ProvWarning, so
    # that the warning points at the caller of deserialize() rather than a
    # frame inside the parser. See test_provn_profiles.py for that warning.
    parser = ProvNParser(
        f"document\n{PREFIXES}foo(ex:e1)\nentity(ex:e2)\nendDocument", "lenient"
    )
    doc = parser.parse()
    assert [str(r.identifier) for r in doc.get_records()] == ["ex:e2"]
    assert len(parser.skipped) == 1
    assert "unknown statement keyword 'foo'" in parser.skipped[0]


@pytest.mark.parametrize(
    "build",
    [
        examples.primer_example,
        examples.w3c_publication_1,
        examples.bundles1,
        examples.collections,
        examples.datatypes,
        examples.long_literals,
        examples.default_namespace_attributes,
    ],
)
def test_writer_output_parses_to_an_equal_document(build) -> None:
    doc = build()
    reloaded = ProvNParser(doc.get_provn(), "default").parse()
    assert reloaded == doc


def test_strict_writer_drops_what_bare_relations_cannot_carry() -> None:
    # Productions 24 to 26 give alternateOf, specializationOf and hadMember
    # neither an identifier nor an attribute block, and the strict reader
    # rejects both, so strict=True drops each with a warning (#569).
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.membership("ex:c", "ex:x").add_attributes({"ex:k": 1})
    document.new_record(
        PROV_ALTERNATE,
        "ex:alt",
        {"prov:alternate1": "ex:e1", "prov:alternate2": "ex:e2"},
        {"ex:k": "v"},
    )
    with pytest.warns(ProvWarning) as caught:
        text = document.get_provn(strict=True)
    assert [str(w.message) for w in caught] == [
        "strict=True drops the attribute block [ex:k=1] of hadMember(ex:c, ex:x),"
        " because PROV-N gives hadMember no attribute block",
        "strict=True drops the identifier ex:alt of alternateOf(ex:e1, ex:e2),"
        " because PROV-N gives alternateOf no identifier",
        'strict=True drops the attribute block [ex:k="v"] of'
        " alternateOf(ex:e1, ex:e2), because PROV-N gives alternateOf no"
        " attribute block",
    ]
    expected = ProvDocument()
    expected.add_namespace("ex", "http://example.org/")
    expected.membership("ex:c", "ex:x")
    expected.alternateOf("ex:e1", "ex:e2")
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        reread = ProvDocument.deserialize(
            content=text, format="provn", profile="strict"
        )
        assert reread == expected
        # The default writer keeps both and warns about nothing.
        assert 'alternateOf(ex:alt; ex:e1, ex:e2, [ex:k="v"])' in document.get_provn()


def test_duplicate_prefix_in_one_scope_is_an_error() -> None:
    with pytest.raises(ProvNSyntaxError, match="prefix 'ex' is declared twice") as ctx:
        parse(
            "entity(ex:e1)",
            prefixes="prefix ex <http://a.org/>\nprefix ex <http://b.org/>\n",
        )
    assert (ctx.value.line, ctx.value.column) == (3, 8)


def test_escaped_colon_literal_needs_a_default_namespace() -> None:
    with pytest.raises(ProvNSyntaxError, match="no default namespace declared"):
        parse(r"entity(ex:e1, [ex:k='a\:b'])")


def test_duplicate_bundle_identifier_is_a_positioned_syntax_error() -> None:
    with pytest.raises(ProvNSyntaxError, match="already exists") as ctx:
        parse("bundle ex:b\nendBundle\nbundle ex:b\nendBundle")
    assert ctx.value.line == 6


def test_all_digit_local_name_as_an_attribute_name() -> None:
    doc = parse('entity(ex:e1, [123="x"])', prefixes="default <http://d/>\n" + PREFIXES)
    (record,) = doc.get_records()
    ((attr, _),) = record.attributes
    assert attr.uri == "http://d/123"


def test_all_digit_local_name_as_a_datatype() -> None:
    doc = parse(
        'entity(ex:e1, [ex:a="x" %% 123])', prefixes="default <http://d/>\n" + PREFIXES
    )
    (record,) = doc.get_records()
    ((_, value),) = record.attributes
    assert value.datatype.uri == "http://d/123"


def test_leading_byte_order_mark_is_skipped() -> None:
    doc = ProvDocument.deserialize(
        content="﻿document\n prefix ex <http://example.org/>\n entity(ex:e1)\nendDocument",
        format="provn",
    )
    assert [str(r.identifier) for r in doc.get_records()] == ["ex:e1"]


def test_bytearray_stream_is_decoded() -> None:
    text = "document\n prefix ex <http://example.org/>\n entity(ex:e1)\nendDocument"
    doc = ProvDocument.deserialize(io.BytesIO(bytearray(text, "utf-8")), format="provn")
    assert [str(r.identifier) for r in doc.get_records()] == ["ex:e1"]


def test_bundle_in_document_default_with_its_own_default_round_trips() -> None:
    d = ProvDocument()
    d.set_default_namespace("http://doc.org/")
    b = d.bundle("b1")
    b.set_default_namespace("http://bundle.org/")
    b.entity("e1")
    text = d.get_provn()
    assert "bundle dn:b1" in text and "prefix dn <http://doc.org/>" in text
    again = ProvDocument.deserialize(content=text, format="provn")
    assert again == d
    (bundle,) = again.bundles
    assert bundle.identifier.uri == "http://doc.org/b1"


def test_bundle_header_prefix_avoids_a_taken_dn_prefix() -> None:
    # When the bundle already declares its own "dn" prefix for something
    # else, the header's minted prefix falls back to "dn_1" instead of
    # colliding with it.
    d = ProvDocument()
    d.set_default_namespace("http://doc.org/")
    b = d.bundle("b1")
    b.set_default_namespace("http://bundle.org/")
    b.add_namespace("dn", "http://other.org/")
    b.entity("e1")
    text = d.get_provn()
    assert "bundle dn_1:b1" in text
    assert "prefix dn_1 <http://doc.org/>" in text
    assert ProvDocument.deserialize(content=text, format="provn") == d


def test_namespace_uri_that_is_not_an_iri_cannot_be_written() -> None:
    d = ProvDocument()
    d.add_namespace("bad", "http://example.org/a b/")
    with pytest.raises(ProvException, match="bad"):
        d.get_provn()


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
@pytest.mark.parametrize("declaration", ["prefix z <>", "default <>"])
def test_empty_namespace_iri_is_a_syntax_error(profile, declaration) -> None:
    with pytest.raises(
        ProvNSyntaxError, match="a namespace IRI cannot be empty"
    ) as ctx:
        ProvNParser(f"document\n{declaration}\nendDocument", profile).parse()
    assert (ctx.value.line, ctx.value.column) == (2, declaration.index("<") + 1)


@pytest.mark.parametrize("declaration", ["prefix z <>", "default <>"])
def test_empty_namespace_iri_in_a_bundle_is_a_syntax_error(declaration) -> None:
    with pytest.raises(
        ProvNSyntaxError, match="a namespace IRI cannot be empty"
    ) as ctx:
        ProvNParser(
            "document\nprefix ex <http://example.org/>\nbundle ex:b\n"
            f"{declaration}\nendBundle\nendDocument",
            "lenient",
        ).parse()
    assert ctx.value.line == 4


def test_code_point_escapes_read_in_strings_and_iris() -> None:
    text = (
        "document\nprefix ex <http://example.org/caf\\u00E9/>\n"
        'entity(ex:e, [ex:k="caf\\u00E9"])\nendDocument\n'
    )
    document = ProvDocument.deserialize(content=text, format="provn")
    (record,) = document.get_records()
    assert record.identifier.uri == "http://example.org/café/e"
    assert record.get_attribute("ex:k") == {"café"}

"""PROV-N parser tests: document structure, every expression form, literal
forms, error paths and equality with documents the writer produced.
Profile behaviour (default, lenient) is in test_provn_profiles.py."""

import datetime
import io
import warnings

import pytest

from prov.constants import PROV, XSD, XSI
from prov.model import (
    PROV_REC_CLS,
    Literal,
    ProvDocument,
    ProvException,
    ProvFutureRejectionWarning,
    ProvMention,
    ProvWarning,
)
from prov.serializers.provn_lexer import ProvNSyntaxError
from prov.serializers.provn_parser import (
    _ELEMENTS,
    _MENTION,
    _RELATIONS,
    ProvNParser,
)
from prov.tests import examples

PREFIXES = "prefix ex <http://example.org/>\nprefix dc <http://purl.org/dc/terms/>\n"


def parse(body, profile="strict", prefixes=PREFIXES):
    return ProvNParser(f"document\n{prefixes}{body}\nendDocument", profile).parse()


def only_record(doc):
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
    assert time == datetime.datetime(2011, 11, 16, 16, 5, tzinfo=datetime.timezone.utc)


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
        prefixes="prefix ex <http://example.org/>\ndefault <http://d.org/>\n",
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


def parse_with_warnings(text, profile="default"):
    parser = ProvNParser(text, profile)
    return parser.parse(), parser.warnings


OTHER_XSI = "document\nprefix ex <http://example.org/>\nprefix xsi <http://other/>\n"


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
def test_xsi_is_an_ordinary_prefix(profile) -> None:
    doc, messages = parse_with_warnings(
        OTHER_XSI + "entity(xsi:e, [xsi:k='xsi:v', ex:t=\"1\" %% xsi:t])\nendDocument",
        profile,
    )
    record = only_record(doc)
    assert record.identifier.uri == "http://other/e"
    attributes = {name.uri: value for name, value in record.extra_attributes}
    assert attributes["http://other/k"].uri == "http://other/v"
    assert attributes["http://example.org/t"].datatype.uri == "http://other/t"
    assert messages == []


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
    content = doc.serialize(format=target)
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


def test_xsi_is_an_ordinary_prefix_at_bundle_scope() -> None:
    doc, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\nbundle ex:b\n"
        "prefix xsi <http://other/>\nentity(xsi:e)\nendBundle\nendDocument"
    )
    (bundle,) = doc.bundles
    assert only_record(bundle).identifier.uri == "http://other/e"
    assert messages == []


def test_undeclared_xsi_resolves_to_the_builtin_namespace_and_warns() -> None:
    doc, messages = parse_with_warnings(
        'document\nprefix ex <http://example.org/>\nentity(ex:e, [xsi:type="ex:T"])\n'
        "endDocument"
    )
    ((name, _),) = only_record(doc).extra_attributes
    assert name.uri == XSI.uri + "type"
    assert len(messages) == 1
    assert messages[0].startswith("line 3, column ")
    assert messages[0].endswith(
        f"prefix 'xsi' is not declared; it resolves to <{XSI.uri}>."
        " prov 3.3.0 will reject this (#510)"
    )


def test_undeclared_xsi_value_warns() -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\nentity(ex:e, [ex:p='xsi:v'])\n"
        "endDocument"
    )
    assert len(messages) == 1
    assert "prefix 'xsi' is not declared" in messages[0]


def test_undeclared_xsi_warning_reaches_the_caller() -> None:
    with pytest.warns(ProvFutureRejectionWarning, match="prefix 'xsi' is not declared"):
        ProvDocument.deserialize(
            content="document\nprefix ex <http://example.org/>\n"
            'entity(ex:e, [xsi:type="ex:T"])\nendDocument',
            format="provn",
        )


def test_xsi_qualified_name_literal_resolves_against_the_declared_scope() -> None:
    doc, messages = parse_with_warnings(
        OTHER_XSI + 'entity(ex:e, [ex:p="xsi:v" %% prov:QUALIFIED_NAME])\nendDocument'
    )
    ((_, value),) = only_record(doc).extra_attributes
    assert value.uri == "http://other/v"
    assert messages == []


def test_undeclared_xsi_qualified_name_literal_warns_and_keeps_the_builtin() -> None:
    doc, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\n"
        'entity(ex:e, [ex:p="xsi:v" %% prov:QUALIFIED_NAME])\nendDocument'
    )
    ((_, value),) = only_record(doc).extra_attributes
    assert value.uri == XSI.uri + "v"
    assert len(messages) == 1
    assert messages[0].endswith(
        f"prefix 'xsi' is not declared; it resolves to <{XSI.uri}>."
        " prov 3.3.0 will reject this (#510)"
    )


def test_xsi_bundle_identifier_resolves_against_the_declared_scope() -> None:
    doc, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\nprefix xsi <http://other/>\n"
        "bundle xsi:b\nentity(ex:e)\nendBundle\nendDocument"
    )
    (bundle,) = doc.bundles
    assert bundle.identifier.uri == "http://other/b"
    assert messages == []


def test_xsi_declared_at_its_standard_iri_does_not_warn() -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix ex <http://example.org/>\nprefix xsi <{XSI.uri}>\n"
        'entity(ex:e, [xsi:type="ex:T"])\nendDocument'
    )
    assert messages == []


def test_prefix_declaration_accepts_redeclaring_prov_to_its_own_iri() -> None:
    from prov.constants import PROV

    record = only_record(
        ProvNParser(
            f"document\nprefix prov <{PROV.uri}>\nentity(prov:e1)\nendDocument",
            "strict",
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
    doc = parse('entity(ex:e1, [123="x"])', prefixes=PREFIXES + "default <http://d/>\n")
    (record,) = doc.get_records()
    ((attr, _),) = record.attributes
    assert attr.uri == "http://d/123"


def test_all_digit_local_name_as_a_datatype() -> None:
    doc = parse(
        'entity(ex:e1, [ex:a="x" %% 123])', prefixes=PREFIXES + "default <http://d/>\n"
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


def test_bundle_header_prefix_percent_encoding_warns_once() -> None:
    # The synthesised "dn:" prefix and the percent-encoding of an
    # unrepresentable character in the bundle's own identifier are two
    # separate writer decisions on the same identifier; only one warning
    # should reach the caller, via the same code path
    # provn_bare_representation() uses.
    d = ProvDocument()
    d.set_default_namespace("http://doc.org/")
    with pytest.warns(ProvFutureRejectionWarning):
        b = d.bundle("b 1")
    b.set_default_namespace("http://bundle.org/")
    b.entity("e1")
    with pytest.warns(ProvWarning) as record:
        text = d.get_provn()
    assert "bundle dn:b%201" in text
    assert len(record) == 1


def test_namespace_uri_that_is_not_an_iri_cannot_be_written() -> None:
    d = ProvDocument()
    d.add_namespace("bad", "http://example.org/a b/")
    with pytest.raises(ProvException, match="bad"):
        d.get_provn()


XSI_LINE = f"prefix xsi <{XSI.uri}>"


def _xsi_document():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    return doc


def _reads_back_without_future_warnings(text):
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        return ProvDocument.deserialize(content=text, format="provn")


def test_writer_declares_xsi_when_a_record_uses_it() -> None:
    doc = _xsi_document()
    doc.entity("ex:e", {XSI["type"]: "ex:T"})
    text = doc.get_provn()
    assert XSI_LINE in text
    assert _reads_back_without_future_warnings(text) == doc


def test_writer_declares_xsi_for_an_xsi_identifier() -> None:
    doc = _xsi_document()
    doc.entity(XSI["e"])
    text = doc.get_provn()
    assert XSI_LINE in text
    assert _reads_back_without_future_warnings(text) == doc


def test_writer_declares_xsi_for_an_xsi_datatype() -> None:
    doc = _xsi_document()
    doc.entity("ex:e", {"ex:p": Literal("v", XSI["t"])})
    assert XSI_LINE in doc.get_provn()


def test_writer_declares_xsi_when_another_prefix_holds_its_iri() -> None:
    doc = _xsi_document()
    doc.add_namespace("foo", XSI.uri)
    doc.entity("ex:e", {XSI["type"]: "ex:T"})
    text = doc.get_provn()
    assert XSI_LINE in text
    assert _reads_back_without_future_warnings(text) == doc


def test_writer_omits_xsi_when_no_record_uses_it() -> None:
    doc = _xsi_document()
    doc.entity("ex:e")
    assert "prefix xsi" not in doc.get_provn()


def test_writer_omits_xsi_for_a_string_value_that_only_looks_like_an_xsi_name() -> None:
    doc = _xsi_document()
    doc.entity("ex:e", {"ex:p": "xsi:not-a-name"})
    text = doc.get_provn()
    assert "xsi:not-a-name" in text
    assert "prefix xsi" not in text


def test_writer_declares_xsi_in_the_bundle_that_uses_it() -> None:
    doc = _xsi_document()
    doc.entity("ex:e")
    bundle = doc.bundle("ex:b")
    bundle.entity("ex:f", {XSI["type"]: "ex:T"})
    text = doc.get_provn()
    assert text.count(XSI_LINE) == 1
    assert text.index(XSI_LINE) > text.index("bundle ex:b")
    assert _reads_back_without_future_warnings(text) == doc


STRICT_ISSUE = 519
STRICT_CLAUSE = (
    f". prov 3.3.0 will reject this under the strict profile (#{STRICT_ISSUE})"
)


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


def test_repeated_default_warns_and_the_last_one_wins() -> None:
    doc, messages = parse_with_warnings(
        "document\ndefault <http://a/>\ndefault <http://b/>\nentity(e)\nendDocument"
    )
    assert only_record(doc).identifier.uri == "http://b/e"
    assert messages == [
        "line 3, column 1: 'default' is declared twice in this scope; the last one"
        " is used. prov 3.3.0 will reject this (#508)"
    ]


def test_single_default_does_not_warn() -> None:
    _, messages = parse_with_warnings(
        "document\ndefault <http://a/>\nentity(e)\nendDocument"
    )
    assert messages == []


@pytest.mark.parametrize("name", ["_", "a/b", "1a"])
def test_prefix_name_that_is_not_a_pn_prefix_warns(name) -> None:
    doc, messages = parse_with_warnings(
        f"document\nprefix {name} <http://x/>\nprefix ex <http://example.org/>\n"
        "entity(ex:e)\nendDocument"
    )
    assert only_record(doc).identifier.uri == "http://example.org/e"
    assert messages == [
        f"line 2, column 8: '{name}' is not a PROV-N prefix name, so no qualified"
        " name can use it. prov 3.3.0 will reject this (#511)"
    ]


@pytest.mark.parametrize("name", ["ex", "a.b", "a_b", "a-1"])
def test_pn_prefix_names_do_not_warn(name) -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix {name} <http://x/>\nendDocument"
    )
    assert messages == []


def test_strict_default_after_prefix_warns() -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\ndefault <http://d/>\nendDocument",
        "strict",
    )
    assert messages == [
        "line 3, column 1: 'default' follows a 'prefix' declaration, which the"
        " strict profile does not allow" + STRICT_CLAUSE
    ]


@pytest.mark.parametrize("profile", ["default", "lenient"])
def test_default_after_prefix_warns_only_under_strict(profile) -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\ndefault <http://d/>\nendDocument",
        profile,
    )
    assert messages == []


def test_strict_default_before_prefix_does_not_warn() -> None:
    _, messages = parse_with_warnings(
        "document\ndefault <http://d/>\nprefix ex <http://example.org/>\nendDocument",
        "strict",
    )
    assert messages == []


@pytest.mark.parametrize("prefix, namespace", [("prov", PROV), ("xsd", XSD)])
def test_strict_declaring_a_predeclared_prefix_warns(prefix, namespace) -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix {prefix} <{namespace.uri}>\nendDocument", "strict"
    )
    assert messages == [
        f"line 2, column 8: prefix '{prefix}' is predeclared, and the strict"
        " profile does not allow declaring it" + STRICT_CLAUSE
    ]


@pytest.mark.parametrize("profile", ["default", "lenient"])
@pytest.mark.parametrize("prefix, namespace", [("prov", PROV), ("xsd", XSD)])
def test_declaring_a_predeclared_prefix_warns_only_under_strict(
    profile, prefix, namespace
) -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix {prefix} <{namespace.uri}>\nendDocument", profile
    )
    assert messages == []


def _read_warning(text, match, profile="default"):
    with pytest.warns(ProvFutureRejectionWarning, match=match) as caught:
        doc = ProvDocument.deserialize(content=text, format="provn", profile=profile)
    assert len(caught) == 1
    return doc


def test_repeated_default_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        "document\ndefault <http://a/>\ndefault <http://b/>\nentity(e)\nendDocument",
        "'default' is declared twice in this scope",
    )
    assert only_record(doc).identifier.uri == "http://b/e"


def test_non_pn_prefix_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        "document\nprefix 1a <http://x/>\nprefix ex <http://example.org/>\n"
        "entity(ex:e)\nendDocument",
        "'1a' is not a PROV-N prefix name",
    )
    assert only_record(doc).identifier.uri == "http://example.org/e"


def test_strict_default_after_prefix_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        "document\nprefix ex <http://example.org/>\ndefault <http://d/>\n"
        "entity(e)\nendDocument",
        "'default' follows a 'prefix' declaration",
        "strict",
    )
    assert only_record(doc).identifier.uri == "http://d/e"


def test_strict_predeclared_prefix_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        f"document\nprefix prov <{PROV.uri}>\nprefix ex <http://example.org/>\n"
        "entity(ex:e)\nendDocument",
        "prefix 'prov' is predeclared",
        "strict",
    )
    assert only_record(doc).identifier.uri == "http://example.org/e"


def test_code_point_escapes_read_in_strings_and_iris() -> None:
    text = (
        "document\nprefix ex <http://example.org/caf\\u00E9/>\n"
        'entity(ex:e, [ex:k="caf\\u00E9"])\nendDocument\n'
    )
    document = ProvDocument.deserialize(content=text, format="provn")
    (record,) = document.get_records()
    assert record.identifier.uri == "http://example.org/café/e"
    assert record.get_attribute("ex:k") == {"café"}


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
def test_non_ws_space_warns_and_reads_as_before(profile) -> None:
    text = "document\nprefix ex <http://example.org/>\nentity(ex:e)\xa0\nendDocument\n"
    document = _read_warning(
        text,
        (
            r"^line 3, column 13: U\+00A0 is not PROV-N whitespace\."
            r" prov 3\.3\.0 will reject this \(#509\)$"
        ),
        profile,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        assert document == ProvDocument.deserialize(
            content=text.replace("\xa0", " "), format="provn", profile=profile
        )


def test_lexer_warnings_come_before_parser_warnings() -> None:
    text = (
        "document\ndefault <http://a/>\ndefault <http://b/>\n"
        "entity(e)\xa0\nendDocument\n"
    )
    parser = ProvNParser(text)
    parser.parse()
    assert len(parser.warnings) == 2
    assert "U+00A0 is not PROV-N whitespace" in parser.warnings[0]
    assert "'default' is declared twice" in parser.warnings[1]


STATEMENT_PREFIX = "document\nprefix ex <http://example.org/>\n"


def read_statement(statement, profile="default"):
    return parse_with_warnings(f"{STATEMENT_PREFIX}{statement}\nendDocument", profile)


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
@pytest.mark.parametrize(
    ("statement", "positional", "formal", "keyword"),
    [
        (
            "wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])",
            "wasGeneratedBy(ex:e, ex:a, -)",
            "activity",
            "wasGeneratedBy",
        ),
        (
            "wasGeneratedBy(ex:e, ex:a, -, [prov:activity='ex:a'])",
            "wasGeneratedBy(ex:e, ex:a, -)",
            "activity",
            "wasGeneratedBy",
        ),
        (
            'activity(ex:a, -, -, [prov:startTime="2011-11-16T16:05:00"])',
            "activity(ex:a, 2011-11-16T16:05:00, -)",
            "startTime",
            "activity",
        ),
    ],
)
def test_attribute_named_after_a_formal_warns_and_reads_as_that_formal(
    profile, statement, positional, formal, keyword
) -> None:
    doc, messages = read_statement(statement, profile)
    column = statement.index("[prov:") + 2
    assert messages == [
        f"line 3, column {column}: 'prov:{formal}' names the '{formal}' argument"
        f" of '{keyword}', which PROV-N gives only by position."
        " prov 3.3.0 will reject this (#523)"
    ]
    positional_doc, positional_messages = read_statement(positional, profile)
    assert positional_messages == []
    assert doc == positional_doc


def test_conflicting_formal_attribute_is_skipped_without_a_warning() -> None:
    parser = ProvNParser(
        f"{STATEMENT_PREFIX}wasGeneratedBy(ex:e, ex:a, -, [prov:activity='ex:b'])\n"
        "entity(ex:z)\nendDocument",
        "lenient",
    )
    parser.parse()
    assert parser.warnings == []
    assert len(parser.skipped) == 1


def test_reserved_attribute_that_is_not_a_formal_does_not_warn() -> None:
    _, messages = read_statement("wasGeneratedBy(ex:e, ex:a, -, [prov:role='ex:r'])")
    assert messages == []


def test_formal_attribute_is_matched_by_name_not_spelling() -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\n"
        "prefix p <http://www.w3.org/ns/prov#>\n"
        "wasGeneratedBy(ex:e, -, -, [p:activity='ex:a'])\nendDocument"
    )
    assert messages == [
        "line 4, column 29: 'p:activity' names the 'activity' argument of"
        " 'wasGeneratedBy', which PROV-N gives only by position."
        " prov 3.3.0 will reject this (#523)"
    ]


def test_formal_attribute_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        f"{STATEMENT_PREFIX}wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])\n"
        "endDocument",
        "'prov:activity' names the 'activity' argument of 'wasGeneratedBy'",
    )
    assert doc == read_statement("wasGeneratedBy(ex:e, ex:a, -)")[0]


AFTER_BUNDLE = "a statement follows a bundle, which the strict profile does not allow"


def test_strict_statement_after_a_bundle_warns_once_per_run() -> None:
    _, messages = read_statement(
        "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)\nentity(ex:g)\n"
        "bundle ex:c\nentity(ex:e)\nendBundle\nentity(ex:h)",
        "strict",
    )
    assert messages == [
        f"line 6, column 1: {AFTER_BUNDLE}" + STRICT_CLAUSE,
        f"line 11, column 1: {AFTER_BUNDLE}" + STRICT_CLAUSE,
    ]


def test_strict_statement_before_a_bundle_does_not_warn() -> None:
    _, messages = read_statement(
        "entity(ex:f)\nbundle ex:b\nentity(ex:e)\nendBundle", "strict"
    )
    assert messages == []


@pytest.mark.parametrize("profile", ["default", "lenient"])
def test_statement_after_a_bundle_warns_only_under_strict(profile) -> None:
    _, messages = read_statement(
        "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)", profile
    )
    assert messages == []


BARE_RELATION_CASES = [
    ("hadMember(ex:m; ex:c, ex:e)", "an identifier", "ex:m"),
    ("hadMember(-; ex:c, ex:e)", "an identifier", "-"),
    ("alternateOf(ex:a; ex:e2, ex:e1)", "an identifier", "ex:a"),
    ('specializationOf(ex:e2, ex:e1, [ex:k="x"])', "an attribute block", "["),
    ("alternateOf(ex:e2, ex:e1, [])", "an attribute block", "["),
]


@pytest.mark.parametrize(("statement", "what", "marker"), BARE_RELATION_CASES)
def test_strict_identifier_or_attributes_on_a_bare_relation_warns(
    statement, what, marker
) -> None:
    keyword = statement.split("(")[0]
    column = statement.index(marker) + 1
    _, messages = read_statement(statement, "strict")
    assert messages == [
        f"line 3, column {column}: '{keyword}' has {what}, which the strict"
        " profile does not allow" + STRICT_CLAUSE
    ]


def test_strict_identifier_and_attributes_on_a_bare_relation_warn_twice() -> None:
    _, messages = read_statement('hadMember(ex:m; ex:c, ex:e, [ex:k="x"])', "strict")
    assert messages == [
        "line 3, column 11: 'hadMember' has an identifier, which the strict"
        " profile does not allow" + STRICT_CLAUSE,
        "line 3, column 29: 'hadMember' has an attribute block, which the strict"
        " profile does not allow" + STRICT_CLAUSE,
    ]


@pytest.mark.parametrize("profile", ["default", "lenient"])
@pytest.mark.parametrize("statement", [case[0] for case in BARE_RELATION_CASES])
def test_bare_relation_warns_only_under_strict(profile, statement) -> None:
    _, messages = read_statement(statement, profile)
    assert messages == []


@pytest.mark.parametrize(
    "statement",
    [
        'wasDerivedFrom(ex:d; ex:e2, ex:e1, [ex:k="x"])',
        "prov:mentionOf(ex:m; ex:e2, ex:e1, ex:b)",
    ],
)
def test_strict_identifier_and_attributes_on_other_relations_do_not_warn(
    statement,
) -> None:
    _, messages = read_statement(statement, "strict")
    assert messages == []


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (
            "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)",
            "a statement follows a bundle",
        ),
        ("hadMember(ex:m; ex:c, ex:e)", "'hadMember' has an identifier"),
        (
            'specializationOf(ex:e2, ex:e1, [ex:k="x"])',
            "'specializationOf' has an attribute block",
        ),
    ],
)
def test_strict_statement_warning_reaches_the_caller(body, match) -> None:
    text = f"{STATEMENT_PREFIX}{body}\nendDocument"
    doc = _read_warning(text, match, "strict")
    assert doc == ProvDocument.deserialize(content=text, format="provn")

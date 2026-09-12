"""PROV-N parser tests: document structure, every expression form, literal
forms, error paths and equality with documents the writer produced.
Profile behaviour (default, lenient) is in test_provn_profiles.py."""

import datetime

import pytest

from prov.model import PROV_REC_CLS, Literal, ProvDocument, ProvMention
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


def test_empty_document():
    doc = ProvNParser("document endDocument", "strict").parse()
    assert list(doc.get_records()) == []


def test_prefix_and_default_declarations():
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
def test_every_expression_form(text, keyword, n_formal):
    record = only_record(parse(text))
    assert len([v for _, v in record.formal_attributes if v is not None]) == n_formal
    assert text.split("(")[0] == keyword
    if keyword == "prov:mentionOf":
        expected_type = _MENTION[0]
    else:
        expected_type = _ELEMENTS.get(keyword, _RELATIONS.get(keyword))[0]
    assert record.get_type() == expected_type


def test_relation_identifier_is_kept():
    record = only_record(parse("wasGeneratedBy(ex:g1; ex:e1, ex:a1, -)"))
    assert str(record.identifier) == "ex:g1"


def test_formal_time_is_a_datetime():
    record = only_record(parse("used(ex:a1, ex:e1, 2011-11-16T16:05:00Z)"))
    (time,) = [v for k, v in record.formal_attributes if str(k) == "prov:time"]
    assert time == datetime.datetime(2011, 11, 16, 16, 5, tzinfo=datetime.timezone.utc)


def test_mention_maps_to_prov_mention():
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
def test_literal_forms(literal, expected):
    record = only_record(parse(f"entity(ex:e1, [ex:v={literal}])"))
    (value,) = record.get_attribute("ex:v")
    if expected == "QNAME":
        assert str(value) == "ex:abc"
    else:
        assert value == expected


def test_literal_equivalence_with_json():
    body = (
        'entity(ex:e1, [ex:s="x", ex:i=1, ex:f="1.5" %% xsd:double, ex:q=\'ex:q1\','
        ' ex:l="un lieu"@fr, ex:t="2019-03-27T12:52:02" %% xsd:dateTime])'
    )
    doc = parse(body)
    reloaded = ProvDocument.deserialize(
        content=doc.serialize(format="json"), format="json"
    )
    assert doc == reloaded


def test_bare_identifier_with_escaped_colon_resolves_via_default():
    # A bare (unprefixed) identifier whose local part contains an escaped
    # ':' can't be turned back into 'prefix:local' text without looking
    # like a (wrong) prefixed name, so it must stay resolved rather than
    # round-tripping through a reconstructed string.
    doc = parse(r"entity(a\:b)", prefixes="default <http://d.org/>\n" + PREFIXES)
    record = only_record(doc)
    assert str(record.identifier) == "a:b"
    assert record.identifier.uri == "http://d.org/a:b"


def test_bare_escaped_colon_name_in_bundle_adopts_the_enclosing_default():
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


def test_multiple_attributes_and_repeated_keys():
    record = only_record(parse('entity(ex:e1, [prov:type="a", prov:type="b", ex:k=1])'))
    assert record.get_attribute("prov:type") == {"a", "b"}


def test_bundle_with_own_prefixes():
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


def test_bundle_bare_name_uses_document_default():
    doc = parse(
        "bundle ex:b1\n  entity(e1)\nendBundle",
        prefixes="default <http://d.org/>\n" + PREFIXES,
    )
    (bundle,) = doc.bundles
    assert only_record(bundle).identifier.uri == "http://d.org/e1"


def test_bundle_identifier_resolves_against_its_own_prefix():
    # PROV-N 3.1.3: the bundle identifier is interpreted with the bundle's
    # own declarations, not just the document's -- bx is only declared
    # inside the bundle.
    body = "bundle bx:b1\n  prefix bx <http://bundle.org/>\n  entity(bx:e1)\nendBundle"
    doc = parse(body)
    (bundle,) = doc.bundles
    assert str(bundle.identifier) == "bx:b1"
    assert str(only_record(bundle).identifier) == "bx:e1"
    assert "bx" not in {ns.prefix for ns in doc.get_registered_namespaces()}


def test_bundle_local_prefix_json_round_trip():
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


def test_bundle_without_own_default_gains_none_on_reparse():
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


def test_bundle_bare_name_with_no_default_anywhere_still_raises():
    with pytest.raises(ProvNSyntaxError, match="no default namespace declared"):
        parse("bundle ex:b1\n  entity(e1)\nendBundle")


def test_comments_anywhere():
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
def test_errors_name_the_problem_and_position(body, message, line):
    if line is None:
        text = f"document\n{PREFIXES}{body}"  # no endDocument
        with pytest.raises(ProvNSyntaxError, match=message):
            ProvNParser(text, "strict").parse()
        return
    with pytest.raises(ProvNSyntaxError) as ctx:
        parse(body)
    assert message in str(ctx.value)
    assert ctx.value.line == line


def test_strict_rejects_bare_mention_and_shorthand():
    with pytest.raises(ProvNSyntaxError, match="unknown statement keyword 'mentionOf'"):
        parse("mentionOf(ex:e1, ex:e0, ex:b)")
    with pytest.raises(ProvNSyntaxError, match="unknown statement keyword 'person'"):
        parse("person(ex:p)")


def test_model_errors_carry_the_statement_position():
    # A membership whose collection identifier resolves but the record
    # constructor rejects (an element with no identifier cannot happen via
    # the grammar; a relation to a bundle-typed value can), so exercise the
    # generic wrapping with a time literal the model cannot parse.
    with pytest.raises(ProvNSyntaxError) as ctx:
        parse("used(ex:a1, ex:e1, 2011-13-40T99:00:00)")
    assert ctx.value.line == 4


def test_unknown_profile_rejected():
    with pytest.raises(ValueError, match="profile"):
        ProvNParser("document endDocument", "loose")


def test_arity_table_matches_formal_attributes():
    for rec_type, arities in [*_ELEMENTS.values(), *_RELATIONS.values(), _MENTION]:
        assert max(arities) == len(PROV_REC_CLS[rec_type].FORMAL_ATTRIBUTES)


def test_document_missing_keyword_reports_expected_document():
    with pytest.raises(ProvNSyntaxError, match="expected 'document'"):
        ProvNParser("entity(ex:e1)", "strict").parse()


def test_prefix_declaration_rejects_a_qualified_name():
    with pytest.raises(ProvNSyntaxError, match="expected a prefix"):
        ProvNParser(
            "document\nprefix ex:x <http://example.org/>\nendDocument", "strict"
        ).parse()


def test_prefix_declaration_rejects_redeclaring_a_reserved_prefix():
    with pytest.raises(ProvNSyntaxError, match="reserved") as ctx:
        ProvNParser(
            "document\nprefix xsi <http://example.org/other#>\nendDocument", "strict"
        ).parse()
    assert ctx.value.line == 2


def test_prefix_declaration_accepts_redeclaring_prov_to_its_own_iri():
    from prov.constants import PROV

    record = only_record(
        ProvNParser(
            f"document\nprefix prov <{PROV.uri}>\nentity(prov:e1)\nendDocument",
            "strict",
        ).parse()
    )
    assert str(record.identifier) == "prov:e1"


def test_bare_all_digit_local_name_is_an_identifier():
    # [53] PN_LOCAL allows a leading digit, so an unprefixed, all-digit
    # local name is a valid identifier, not an integer literal.
    doc = parse("entity(4567)", prefixes="default <http://example.org/>\n")
    record = only_record(doc)
    assert str(record.identifier) == "4567"


def test_bare_all_digit_local_name_as_a_relation_argument():
    doc = parse("wasDerivedFrom(4567, e1)", prefixes="default <http://example.org/>\n")
    record = only_record(doc)
    subject, target = (value for _, value in record.formal_attributes[:2])
    assert str(subject) == "4567"
    assert str(target) == "e1"


def test_strict_requires_an_identifier_at_the_named_position():
    with pytest.raises(ProvNSyntaxError, match="'hadMember' requires an identifier"):
        parse("hadMember(-, -)")
    # default keeps the model's own scruffy-statement policy (#257): both
    # markers are accepted, producing a membership with no formal values set.
    record = only_record(parse("hadMember(-, -)", profile="default"))
    assert all(value is None for _, value in record.formal_attributes)


def test_strict_still_accepts_wasderivedfrom_with_trailing_markers():
    record = only_record(parse("wasDerivedFrom(ex:e2, ex:e1, -, -, -)"))
    assert record.get_type() == _RELATIONS["wasDerivedFrom"][0]


def test_unterminated_bundle_reports_end_of_input():
    with pytest.raises(ProvNSyntaxError, match="expected 'endBundle'"):
        ProvNParser(
            f"document\n{PREFIXES}bundle ex:b\n  entity(ex:e1)", "strict"
        ).parse()


def test_semicolon_marker_leaves_identifier_unset():
    # Grammar [10]/[11]: identifierOrMarker ';' -- the Recommendation's own
    # example is used(-; ex:a1, ex:e1, -).
    record = only_record(parse("used(-; ex:a1, ex:e1, -)"))
    assert record.identifier is None


def test_semicolon_identifier_must_be_a_name_or_marker():
    with pytest.raises(ProvNSyntaxError, match="expected an identifier before ';'"):
        parse("used(2011-11-16T16:05:00; ex:a1, ex:e1, -)")


def test_time_attribute_rejects_a_non_datetime_argument():
    with pytest.raises(ProvNSyntaxError, match="expected a time"):
        parse("wasGeneratedBy(ex:e1, ex:a1, ex:notatime)")


def test_empty_attribute_list():
    record = only_record(parse("entity(ex:e1, [])"))
    assert record.attributes == []


def test_resync_stops_at_a_prefixed_mention():
    doc = parse("foo(ex:e1)\nprov:mentionOf(ex:e2, ex:e0, ex:b)", profile="lenient")
    (record,) = list(doc.get_records())
    assert isinstance(record, ProvMention)


def test_lenient_skip_is_recorded_for_the_caller_to_warn_with():
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
def test_writer_output_parses_to_an_equal_document(build):
    doc = build()
    reloaded = ProvNParser(doc.get_provn(), "default").parse()
    assert reloaded == doc

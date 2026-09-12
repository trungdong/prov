"""PROV-N parser tests: document structure, every expression form, literal
forms, error paths and equality with documents the writer produced.
Profile behaviour (default, lenient) is in test_provn_profiles.py."""

import datetime
import warnings

import pytest

from prov.model import PROV_REC_CLS, Literal, ProvDocument, ProvMention, ProvWarning
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


def test_bundle_bare_name_uses_document_default():
    doc = parse(
        "bundle ex:b1\n  entity(e1)\nendBundle",
        prefixes="default <http://d.org/>\n" + PREFIXES,
    )
    (bundle,) = doc.bundles
    assert only_record(bundle).identifier.uri == "http://d.org/e1"


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


def test_lenient_skip_warns_with_prov_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        doc = parse("foo(ex:e1)\nentity(ex:e2)", profile="lenient")
    assert [str(r.identifier) for r in doc.get_records()] == ["ex:e2"]
    assert any(w.category is ProvWarning for w in caught)


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

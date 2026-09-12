"""Parsing profiles: strict (Recommendation only), default (de-facto
extensions), lenient (skip unparseable statements with a warning)."""

import warnings

import pytest

from prov.constants import PROV
from prov.model import (
    ProvBundle,
    ProvDocument,
    ProvException,
    ProvMention,
    ProvWarning,
)
from prov.serializers.provn import PROFILES, ProvNSyntaxError

PREFIXES = "prefix ex <http://example.org/>\n"


def parse(body, profile="default"):
    text = f"document\n{PREFIXES}{body}\nendDocument"
    return ProvDocument.deserialize(content=text, format="provn", profile=profile)


def records(doc):
    return list(doc.get_records())


def test_profiles_constant():
    assert PROFILES == ("strict", "default", "lenient")


def test_default_is_the_default_profile():
    doc = ProvDocument.deserialize(
        content=f"document\n{PREFIXES}mentionOf(ex:e1, ex:e0, ex:b)\nendDocument",
        format="provn",
    )
    assert isinstance(records(doc)[0], ProvMention)


def test_unknown_profile_raises():
    with pytest.raises(ValueError, match="profile"):
        parse("entity(ex:e1)", profile="loose")


@pytest.mark.parametrize(
    ("keyword", "base", "asserted"),
    [
        ("person", "agent", PROV["Person"]),
        ("organization", "agent", PROV["Organization"]),
        ("softwareAgent", "agent", PROV["SoftwareAgent"]),
        ("collection", "entity", PROV["Collection"]),
        ("emptyCollection", "entity", PROV["EmptyCollection"]),
        ("plan", "entity", PROV["Plan"]),
    ],
)
def test_default_shorthand_elements(keyword, base, asserted):
    (record,) = records(parse(f"{keyword}(ex:x)"))
    assert record.get_type() == PROV[base.capitalize()]
    assert asserted in record.get_asserted_types()
    with pytest.raises(
        ProvNSyntaxError, match=f"unknown statement keyword '{keyword}'"
    ):
        parse(f"{keyword}(ex:x)", profile="strict")


@pytest.mark.parametrize(
    ("keyword", "asserted"),
    [
        ("wasRevisionOf", PROV["Revision"]),
        ("wasQuotedFrom", PROV["Quotation"]),
        ("hadPrimarySource", PROV["PrimarySource"]),
    ],
)
def test_default_shorthand_derivations(keyword, asserted):
    (record,) = records(parse(f"{keyword}(ex:e2, ex:e1)"))
    assert record.get_type() == PROV["Derivation"]
    assert asserted in record.get_asserted_types()
    with pytest.raises(ProvNSyntaxError):
        parse(f"{keyword}(ex:e2, ex:e1)", profile="strict")


def test_shorthand_equals_xml_decoding():
    doc = parse('person(ex:p, [prov:label="P"])')
    reloaded = ProvDocument.deserialize(
        content=doc.serialize(format="xml"), format="xml"
    )
    assert doc == reloaded


def test_strict_rejects_bare_mention_but_accepts_prefixed():
    with pytest.raises(ProvNSyntaxError):
        parse("mentionOf(ex:e1, ex:e0, ex:b)", profile="strict")
    (record,) = records(parse("prov:mentionOf(ex:e1, ex:e0, ex:b)", profile="strict"))
    assert isinstance(record, ProvMention)


def test_extensibility_rejected_in_default():
    with pytest.raises(ProvNSyntaxError, match="extensibility expression"):
        parse("ex:custom(ex:e1)")


def test_lenient_skips_bad_statement_and_warns_with_position():
    # document=1, prefix ex=2, entity(ex:e1)=3, so foo(ex:e2) is line 4 --
    # same convention test_provn.py's test_errors_name_the_problem_and_position
    # and test_model_errors_carry_the_statement_position pin with their own
    # two-line PREFIXES.
    body = "entity(ex:e1)\nfoo(ex:e2)\nentity(ex:e3)"
    with pytest.warns(
        ProvWarning, match=r"line 4, column 1: unknown statement keyword 'foo'"
    ):
        doc = parse(body, profile="lenient")
    assert sorted(str(r.identifier) for r in records(doc)) == ["ex:e1", "ex:e3"]


def test_lenient_resumes_after_multiline_attribute_list():
    body = (
        "entity(ex:e1, [\n"
        "  ex:a=1,\n"
        "  ex:b=\n"  # missing value
        "])\n"
        "entity(ex:e2, [\n"
        "  ex:c=3\n"
        "])"
    )
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 1
    assert [str(r.identifier) for r in records(doc)] == ["ex:e2"]


def test_lenient_warns_once_per_bad_statement():
    body = "foo(ex:e1)\nentity(ex:e2)\nbar(ex:e3)\nentity(ex:e4, [ex:k=])"
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 3
    assert [str(r.identifier) for r in records(doc)] == ["ex:e2"]


def test_lenient_skips_extensibility_expression():
    with pytest.warns(ProvWarning, match="extensibility"):
        doc = parse("ex:custom(ex:e1)\nentity(ex:e2)", profile="lenient")
    assert [str(r.identifier) for r in records(doc)] == ["ex:e2"]


def test_lenient_still_raises_on_tokenisation_error():
    with pytest.raises(ProvNSyntaxError, match="unterminated string"):
        parse('entity(ex:e1, [ex:k="open])', profile="lenient")


def test_lenient_returns_bundle_statements_after_a_skip():
    body = "bundle ex:b\n  foo(ex:x)\n  entity(ex:e1)\nendBundle"
    with pytest.warns(ProvWarning):
        doc = parse(body, profile="lenient")
    (bundle,) = doc.bundles
    assert [str(r.identifier) for r in records(bundle)] == ["ex:e1"]


def test_lenient_resync_recovers_from_a_missing_close_paren():
    # entity(ex:e1 is missing its ')'; _advance() raises self._depth on '('
    # and never lowers it again, so resync must not gate on depth staying
    # at or below where the failed statement started.
    body = "entity(ex:e1\nentity(ex:e2)\nentity(ex:e3)"
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 1
    assert sorted(str(r.identifier) for r in records(doc)) == ["ex:e2", "ex:e3"]


def test_lenient_resync_recovers_from_a_missing_close_bracket():
    body = 'entity(ex:e1, [ex:a="x"\nentity(ex:e2)\nentity(ex:e3)'
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 1
    assert sorted(str(r.identifier) for r in records(doc)) == ["ex:e2", "ex:e3"]


def test_lenient_resync_recovers_from_a_missing_close_paren_in_a_bundle():
    body = "bundle ex:b\n  entity(ex:e1\n  entity(ex:e2)\n  entity(ex:e3)\nendBundle"
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 1
    (bundle,) = doc.bundles
    assert sorted(str(r.identifier) for r in records(bundle)) == ["ex:e2", "ex:e3"]


def test_lenient_resync_does_not_stop_on_a_structural_keyword_shaped_value():
    # A structural keyword (here 'bundle') used as a bare attribute value
    # inside the failed statement's still-open '[...]' is not a resync
    # boundary just because it matches by name -- unlike an element/relation
    # keyword, it is never followed by '(', so it can only be told apart
    # from a real boundary by depth.
    body = "entity(ex:e1, [ex:k=bundle]\nentity(ex:e2)\nentity(ex:e3)"
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 1
    assert sorted(str(r.identifier) for r in records(doc)) == ["ex:e2", "ex:e3"]


def test_strict_and_default_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        parse("entity(ex:e1)", profile="strict")
        parse("entity(ex:e1)")


def test_model_rejection_is_wrapped_and_skippable(monkeypatch):
    """A statement the grammar accepts but ``new_record()`` rejects is a
    ``ProvException``, not a ``ProvNSyntaxError``; the parser must wrap it
    with the statement's position before applying the lenient skip-and-warn
    behaviour, exactly as for a grammar error."""
    original_new_record = ProvBundle.new_record

    def flaky_new_record(
        self, record_type, identifier, attributes=None, other_attributes=None
    ):
        if identifier is not None and str(identifier) == "ex:bad":
            raise ProvException("rejected by the model")
        return original_new_record(
            self, record_type, identifier, attributes, other_attributes
        )

    monkeypatch.setattr(ProvBundle, "new_record", flaky_new_record)

    body = "entity(ex:bad)\nentity(ex:good)"

    with pytest.raises(ProvNSyntaxError, match=r"line 3.*rejected by the model"):
        parse(body, profile="default")

    with pytest.warns(ProvWarning, match="rejected by the model"):
        doc = parse(body, profile="lenient")
    assert [str(r.identifier) for r in records(doc)] == ["ex:good"]


def test_typed_literal_value_error_is_wrapped_and_skippable():
    """``parse_xsd_types()`` raises a bare ``ValueError``/``OverflowError``
    for a malformed typed literal (e.g. ``int("abc")``); the parser must
    wrap it into a ``ProvNSyntaxError`` with the statement's position, just
    like a ``ProvException`` from ``new_record()``."""
    body = 'entity(ex:e1, [ex:v="abc" %% xsd:int])\nentity(ex:e2)'

    with pytest.raises(ProvNSyntaxError) as ctx:
        parse(body, profile="default")
    assert ctx.value.line == 3

    with pytest.warns(ProvWarning):
        doc = parse(body, profile="lenient")
    assert [str(r.identifier) for r in records(doc)] == ["ex:e2"]


def test_lenient_resync_does_not_stop_on_a_keyword_shaped_literal():
    # The bad literal 'entity' inside [ex:k=entity] is itself spelt like a
    # statement keyword; resync must not treat it as a fresh statement
    # boundary just because it matches by name.
    body = "entity(ex:e1, [ex:k=entity]) entity(ex:e2)"
    with pytest.warns(ProvWarning) as caught:
        doc = parse(body, profile="lenient")
    assert len(caught) == 1
    assert [str(r.identifier) for r in records(doc)] == ["ex:e2"]


def test_lenient_resync_does_not_stop_on_a_keyword_shaped_attribute_value():
    # Same bug, dressed as the shape examples.default_namespace_attributes's
    # writer output takes: a keyword-shaped bare name used as an attribute
    # key/value in the statement that should be recovered into, not treated
    # as a second, spurious statement boundary.
    text = (
        "document\n"
        "  default <http://example.org/>\n"
        "  entity(e1, [mine=entity])\n"
        '  used(a1, e1, -, [entity="collides"])\n'
        "endDocument"
    )
    with pytest.warns(ProvWarning) as caught:
        doc = ProvDocument.deserialize(content=text, format="provn", profile="lenient")
    assert len(caught) == 1
    (record,) = records(doc)
    assert record.get_type() == PROV["Usage"]


def test_lenient_warning_reports_the_deserialize_call_site():
    """The warning's reported filename/line is this test module's call to
    ``ProvDocument.deserialize()``, not a frame inside the parser -- whether
    the skipped statement is at document level or inside a bundle."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parse("foo(ex:e1)\nentity(ex:e2)", profile="lenient")
    assert len(caught) == 1
    assert caught[0].filename == __file__

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parse("bundle ex:b\n  foo(ex:x)\n  entity(ex:e1)\nendBundle", profile="lenient")
    assert len(caught) == 1
    assert caught[0].filename == __file__


def test_lenient_warning_reports_the_read_call_site(tmp_path):
    """The same guarantee holds through prov.read()'s extra frame, for both
    an explicit format= and auto-detection."""
    import prov

    path = tmp_path / "doc.provn"
    path.write_text(f"document\n{PREFIXES}foo(ex:e1)\nentity(ex:e2)\nendDocument")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        prov.read(str(path), format="provn", profile="lenient")
    prov_warnings = [w for w in caught if w.category is ProvWarning]
    assert len(prov_warnings) == 1
    assert prov_warnings[0].filename == __file__

    # Auto-detection: other candidates (rdflib in particular) may emit their
    # own unrelated warnings while failing to match, so filter to ProvWarning.
    text = f"document\n{PREFIXES}foo(ex:e1)\nentity(ex:e2)\nendDocument"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        prov.read(text, profile="lenient")
    prov_warnings = [w for w in caught if w.category is ProvWarning]
    assert len(prov_warnings) == 1
    assert prov_warnings[0].filename == __file__

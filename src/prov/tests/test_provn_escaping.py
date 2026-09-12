"""PROV-N output correctness: local-part metacharacter escaping (#223, PROV-N
[53]/[55]) and Mention keyword rendering (#248)."""

import pytest

from prov.identifier import Namespace
from prov.model import Literal, ProvDocument, ProvWarning

METACHARS = "='(),:;[]"

NS = Namespace("ex", "http://example.org/")


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def _roundtrips(document):
    provn = document.get_provn()
    reloaded = ProvDocument.deserialize(content=provn, format="provn")
    assert reloaded == document
    return provn


@pytest.mark.parametrize("ch", list(METACHARS))
def test_metachar_local_parts_are_escaped(ch):
    document = _doc()
    document.entity(f"ex:na{ch}me")
    provn = document.get_provn()
    assert f"ex:na\\{ch}me" in provn


def test_issue_repro_escaped_end_to_end():
    document = _doc()
    document.entity("ex:weird'name)x,y")
    assert "entity(ex:weird\\'name\\)x\\,y)" in document.get_provn()


def test_plain_local_parts_unchanged():
    document = _doc()
    document.entity("ex:plain-name_1.x")
    assert "entity(ex:plain-name_1.x)" in document.get_provn()


def test_string_literal_backslash_escaped_before_quotes():
    document = _doc()
    document.entity("ex:e1", {"ex:note": 'back\\slash and "quote"'})
    provn = document.get_provn()
    # backslash must be escaped first, giving an unambiguous \\ followed by \"
    assert '\\\\slash and \\"quote\\"' in provn


def test_bundle_identifier_metachar_is_escaped():
    document = _doc()
    bundle = document.bundle("ex:weird'bundle")
    bundle.entity("ex:e1")
    assert "bundle ex:weird\\'bundle" in document.get_provn()


def test_bundle_identifier_plain_unchanged():
    document = _doc()
    bundle = document.bundle("ex:plain-bundle")
    bundle.entity("ex:e1")
    assert "bundle ex:plain-bundle" in document.get_provn()


def test_attribute_name_metachar_is_escaped():
    document = _doc()
    document.entity("ex:e1", {"ex:weird'key": "value"})
    assert '[ex:weird\\\'key="value"]' in document.get_provn()


def test_attribute_name_plain_unchanged():
    document = _doc()
    document.entity("ex:e1", {"ex:plain_key": "value"})
    assert '[ex:plain_key="value"]' in document.get_provn()


@pytest.mark.parametrize(
    ("local", "written"),
    [
        ("-abc", "\\-abc"),  # leading dash is escaped
        (".abc", "\\.abc"),  # leading dot is escaped
        ("abc.", "abc\\."),  # trailing dot is escaped
        ("-", "\\-"),  # the Recommendation's own PN_LOCAL example
        ("ab-cd.ef", "ab-cd.ef"),  # inner dash and dot stay bare
    ],
)
def test_dash_and_dot_local_parts(local, written):
    document = _doc()
    document.entity(f"ex:{local}")
    provn = _roundtrips(document)
    assert f"entity(ex:{written})" in provn


@pytest.mark.parametrize(
    ("local", "escaped"),
    [
        ("a\tb", "a%09b"),  # tab: not a PN_CHAR, previously written raw
        ("a\u00d7b", "a%C3%97b"),  # multiplication sign, 2-byte UTF-8
        ("a\u2192b", "a%E2%86%92b"),  # rightwards arrow, 3-byte UTF-8
        ("a b", "a%20b"),  # space, already covered but kept for symmetry
    ],
)
def test_unrepresentable_chars_are_percent_encoded(local, escaped):
    document = _doc()
    document.entity(f"ex:{local}")
    provn = document.get_provn()
    assert f"entity(ex:{escaped})" in provn
    # Documented non-round-trip: the reloaded local part is the
    # percent-encoded text, not the original character.
    reloaded = ProvDocument.deserialize(content=provn, format="provn")
    (reloaded_entity,) = reloaded.get_records()
    assert reloaded_entity.identifier.localpart == escaped


def test_percent_encoding_warns_that_the_iri_changes():
    with pytest.warns(ProvWarning, match="percent"):
        assert NS["a b"].provn_bare_representation() == "ex:a%20b"


def test_lone_surrogate_is_percent_encoded():
    with pytest.warns(ProvWarning):
        assert NS["e\udc80"].provn_bare_representation() == "ex:e%ED%B2%80"


@pytest.mark.parametrize("first", ["·", "́", "‿"])
def test_leading_name_char_that_cannot_start_a_local_part_is_encoded(first):
    with pytest.warns(ProvWarning):
        written = NS[first + "a"].provn_bare_representation()
    assert written.startswith("ex:%")
    doc = ProvDocument.deserialize(
        content=f"document\n prefix ex <{NS.uri}>\n entity({written})\nendDocument",
        format="provn",
    )
    assert len(list(doc.get_records())) == 1


def test_empty_langtag_literal_written_as_plain_string():
    """An empty langtag has no PROV-N spelling, so the writer treats it as none.

    The model itself is unaffected. The ``Literal``'s own ``langtag`` stays
    ``""`` (not ``None``), so this is a writer-only choice, not a round trip;
    the JSON/XML/RDF/JSON-LD codecs still keep the empty tag, e.g. PROV-XML's
    ``xml:lang=""``, which this task leaves untouched.
    """
    literal = Literal("hi", langtag="")
    assert literal.langtag == ""
    document = _doc()
    document.entity("ex:e1", {"ex:note": literal})
    provn = document.get_provn()
    assert '[ex:note="hi"]' in provn
    assert "None" not in provn


def test_langtag_underscore_written_as_hyphen():
    """An underscore-separated langtag is not valid PROV-N LANGTAG ([63]).

    BCP 47 tags use hyphens, so writing one changes the tag's lexical form
    from "en_US" to "en-US". That is a different value under the model's
    case-insensitive langtag comparison, so this is not a round trip like the
    other fixes here.
    """
    document = _doc()
    document.entity("ex:e1", {"ex:note": Literal("hi", langtag="en_US")})
    provn = document.get_provn()
    assert '[ex:note="hi"@en-US]' in provn
    reloaded = ProvDocument.deserialize(content=provn, format="provn")
    (reloaded_entity,) = reloaded.get_records()
    (reloaded_literal,) = reloaded_entity.get_attribute("ex:note")
    assert reloaded_literal.langtag == "en-US"


def test_short_string_carriage_return_is_escaped():
    document = _doc()
    document.entity("ex:e1", {"ex:note": "a\rb"})
    provn = _roundtrips(document)
    assert '[ex:note="a\\rb"]' in provn


def test_crlf_string_stays_triple_quoted():
    """A CRLF value still takes the triple-quoted path, CR unaffected by the escape fix."""
    document = _doc()
    document.entity("ex:e1", {"ex:note": "a\r\nb"})
    provn = _roundtrips(document)
    assert '[ex:note="""a\r\nb"""]' in provn


def test_mention_bare_keyword_no_prefix():
    """PROV-N Mention emits bare mentionOf(...) without prov: prefix (decision 2026-07-20).

    The PROV-Links specification grammar requires prov:mentionOf, but the bare keyword has
    been the de-facto output of reference implementations for the last decade and matches
    ProvToolbox's ANTLR grammar (PROV_N.g:338), so provconvert keeps parsing prov's output.
    This test locks in the current syntax to prevent silent regressions.
    """
    document = _doc()
    bundle = document.bundle("ex:bundle1")
    bundle.entity("ex:report1bis")
    bundle.mentionOf("ex:report1bis", "ex:report1", "ex:bundle2")
    provn = document.get_provn()

    assert "mentionOf(ex:report1bis, ex:report1, ex:bundle2)" in provn

    # This negative assertion is the one that actually guards the decision, and
    # it is not the redundant twin of the line above: ``mentionOf(`` is a
    # substring of ``prov:mentionOf(``, so a regression to the spec-exact form
    # would still satisfy the positive assertion. Do not remove this as dead
    # weight.
    assert "prov:mentionOf" not in provn


def _mention_doc():
    document = _doc()
    bundle = document.bundle("ex:b")
    bundle.entity("ex:e0")
    document.entity("ex:e1")
    document.mention("ex:e1", "ex:e0", "ex:b")
    return document


def test_default_output_keeps_bare_mention_keyword():
    assert "\n  mentionOf(ex:e1, ex:e0, ex:b)" in _mention_doc().get_provn()


def test_strict_output_writes_prefixed_mention_keyword():
    provn = _mention_doc().get_provn(strict=True)
    assert "prov:mentionOf(ex:e1, ex:e0, ex:b)" in provn
    assert "\n  mentionOf(" not in provn


def test_strict_output_parses_under_strict_profile():
    document = _mention_doc()
    reloaded = ProvDocument.deserialize(
        content=document.get_provn(strict=True), format="provn", profile="strict"
    )
    assert reloaded == document


def test_serialize_strict_matches_get_provn_strict():
    document = _mention_doc()
    assert document.serialize(format="provn", strict=True) == document.get_provn(
        strict=True
    )


def test_strict_flag_changes_nothing_without_a_mention():
    document = _doc()
    document.entity("ex:e1", {"ex:k": "v"})
    assert document.get_provn(strict=True) == document.get_provn()

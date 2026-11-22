"""PROV-N output correctness: local-part metacharacter escaping (#223, PROV-N
[53]/[55]), Mention keyword rendering (#248) and string quoting."""

import warnings

import pytest

from prov.identifier import Identifier, Namespace
from prov.model import (
    Literal,
    ProvDocument,
    ProvWarning,
    encoding_provn_value,
)
from prov.tests.conftest import ex_document

METACHARS = "='(),:;[]"

NS = Namespace("ex", "http://example.org/")


def _roundtrips(document):
    provn = document.get_provn()
    reloaded = ProvDocument.deserialize(content=provn, format="provn")
    assert reloaded == document
    return provn


@pytest.mark.parametrize("ch", list(METACHARS))
def test_metachar_local_parts_are_escaped(ch) -> None:
    document = ex_document()
    document.entity(f"ex:na{ch}me")
    provn = document.get_provn()
    assert f"ex:na\\{ch}me" in provn


def test_issue_repro_escaped_end_to_end() -> None:
    document = ex_document()
    document.entity("ex:weird'name)x,y")
    assert "entity(ex:weird\\'name\\)x\\,y)" in document.get_provn()


def test_string_literal_backslash_escaped_before_quotes() -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:note": 'back\\slash and "quote"'})
    provn = document.get_provn()
    # backslash must be escaped first, giving an unambiguous \\ followed by \"
    assert '\\\\slash and \\"quote\\"' in provn


@pytest.mark.parametrize(
    ("identifier", "written"),
    [
        pytest.param(
            "ex:weird'bundle", "bundle ex:weird\\'bundle", id="metacharacter escaped"
        ),
        pytest.param("ex:plain-bundle", "bundle ex:plain-bundle", id="plain unchanged"),
    ],
)
def test_bundle_identifier_escaping(identifier, written) -> None:
    document = ex_document()
    bundle = document.bundle(identifier)
    bundle.entity("ex:e1")
    assert written in document.get_provn()


@pytest.mark.parametrize(
    ("key", "written"),
    [
        pytest.param(
            "ex:weird'key", '[ex:weird\\\'key="value"]', id="metacharacter escaped"
        ),
        pytest.param("ex:plain_key", '[ex:plain_key="value"]', id="plain unchanged"),
    ],
)
def test_attribute_name_escaping(key, written) -> None:
    document = ex_document()
    document.entity("ex:e1", {key: "value"})
    assert written in document.get_provn()


@pytest.mark.parametrize(
    ("local", "written"),
    [
        ("-abc", "\\-abc"),  # leading dash is escaped
        (".abc", "\\.abc"),  # leading dot is escaped
        ("abc.", "abc\\."),  # trailing dot is escaped
        ("-", "\\-"),  # the Recommendation's own PN_LOCAL example
        ("ab-cd.ef", "ab-cd.ef"),  # inner dash and dot stay bare
        ("plain-name_1.x", "plain-name_1.x"),  # nothing to escape
    ],
)
def test_dash_and_dot_local_parts(local, written) -> None:
    document = ex_document()
    document.entity(f"ex:{local}")
    provn = _roundtrips(document)
    assert f"entity(ex:{written})" in provn


def test_percent_escape_is_written_unchanged() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        assert NS["a%20b"].provn_bare_representation() == "ex:a%20b"


def test_fast_path_skips_only_local_parts_written_unchanged() -> None:
    from prov.identifier import _PROVN_LOCAL_NEEDS_ESCAPE, _provn_escape_local

    # Every BMP character, lone surrogates included, and one astral character,
    # in the three positions the escaping rules tell apart.
    chars = [chr(cp) for cp in (*range(0x10000), 0x1F600)]
    local_parts = [lp for ch in chars for lp in (ch + "a", "a" + ch + "a", "a" + ch)]
    skipped = [lp for lp in local_parts if not _PROVN_LOCAL_NEEDS_ESCAPE.search(lp)]

    assert 0 < len(skipped) < len(local_parts)
    assert [lp for lp in skipped if _provn_escape_local(lp) != lp] == []


def test_every_local_part_that_can_be_built_is_written_reversibly() -> None:
    from prov.identifier import _PROVN_LOCAL_PERCENT_ENCODED, _provn_escape_local

    # The same characters and positions as the test above, against the rule
    # QualifiedName enforces (#524): what it lets through, the writer spells
    # with backslash escapes only, which a PROV-N reader reverses.
    chars = [chr(cp) for cp in (*range(0x10000), 0x1F600)]
    local_parts = [lp for ch in chars for lp in (ch + "a", "a" + ch + "a", "a" + ch)]
    accepted = [lp for lp in local_parts if not _PROVN_LOCAL_PERCENT_ENCODED.search(lp)]

    assert 0 < len(accepted) < len(local_parts)
    assert [
        lp for lp in accepted if _provn_escape_local(lp).replace("\\", "") != lp
    ] == []


@pytest.mark.parametrize(
    ("value", "written"),
    [
        pytest.param("a\rb", '[ex:note="a\\rb"]', id="lone CR escaped"),
        # A CRLF value takes the triple-quoted form, and its CR stays raw.
        pytest.param("a\r\nb", '[ex:note="""a\r\nb"""]', id="CRLF stays triple quoted"),
    ],
)
def test_carriage_return_in_a_string(value, written) -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:note": value})
    provn = _roundtrips(document)
    assert written in provn


def test_mention_bare_keyword_no_prefix() -> None:
    """PROV-N Mention emits bare mentionOf(...) without prov: prefix (decision 2026-07-20).

    The PROV-Links specification grammar requires prov:mentionOf, but the bare keyword has
    been the de-facto output of reference implementations for the last decade and matches
    ProvToolbox's ANTLR grammar (PROV_N.g:338), so provconvert keeps parsing prov's output.
    This test locks in the current syntax to prevent silent regressions.
    """
    document = ex_document()
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
    document = ex_document()
    bundle = document.bundle("ex:b")
    bundle.entity("ex:e0")
    document.entity("ex:e1")
    document.mention("ex:e1", "ex:e0", "ex:b")
    return document


def test_default_output_keeps_bare_mention_keyword() -> None:
    assert "\n  mentionOf(ex:e1, ex:e0, ex:b)" in _mention_doc().get_provn()


def test_strict_output_writes_prefixed_mention_keyword() -> None:
    provn = _mention_doc().get_provn(strict=True)
    assert "prov:mentionOf(ex:e1, ex:e0, ex:b)" in provn
    assert "\n  mentionOf(" not in provn


def test_strict_output_parses_under_strict_profile() -> None:
    document = _mention_doc()
    reloaded = ProvDocument.deserialize(
        content=document.get_provn(strict=True), format="provn", profile="strict"
    )
    assert reloaded == document


def test_serialize_strict_matches_get_provn_strict() -> None:
    document = _mention_doc()
    assert document.serialize(format="provn", strict=True) == document.get_provn(
        strict=True
    )


def test_strict_flag_changes_nothing_without_a_mention() -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:k": "v"})
    assert document.get_provn(strict=True) == document.get_provn()


def test_code_point_escapes_round_trip() -> None:
    text = (
        "document\nprefix ex <http://example.org/>\n"
        'entity(ex:e, [ex:k="caf\\u00E9 \\U0001F600"])\nendDocument\n'
    )
    document = ProvDocument.deserialize(content=text, format="provn")
    assert '"café \U0001f600"' in _roundtrips(document)


def test_any_uri_value_with_quote_and_backslash_round_trips() -> None:
    document = ex_document()
    document.entity("ex:e", {"ex:v": Identifier('http://example.org/a"b\\c')})
    assert '"http://example.org/a\\"b\\\\c" %% xsd:anyURI' in _roundtrips(document)


@pytest.mark.parametrize("uri", ["http://example.org/a\nb", "http://example.org/a\rb"])
def test_any_uri_value_with_a_line_break_round_trips(uri) -> None:
    document = ex_document()
    document.entity("ex:e", {"ex:v": Identifier(uri)})
    _roundtrips(document)


class _Shouted(str):
    def __str__(self) -> str:
        return self.upper()


def test_string_subclass_is_written_through_its_str() -> None:
    assert encoding_provn_value(_Shouted('a"b')) == '"A\\"B"'


@pytest.mark.parametrize(
    ("value", "written"),
    [
        pytest.param(NS["a"], "'ex:a'", id="qualified name"),
        pytest.param(
            Identifier("http://example.org/b"),
            '"http://example.org/b" %% xsd:anyURI',
            id="identifier",
        ),
    ],
)
def test_encoding_provn_value_writes_a_name_as_a_provn_literal(value, written) -> None:
    assert encoding_provn_value(value) == written


class _RaisingLiteral(Literal):
    def provn_representation(self) -> str:
        raise AttributeError("boom")

    # Without this override the pre-fix `except` branch reached
    # Literal.__str__ and raised anyway, so the test would pass on the old code.
    def __str__(self) -> str:
        return '"fallback"'


def test_provn_writer_lets_an_error_in_a_literal_subclass_propagate() -> None:
    document = ex_document()
    record = document.entity("ex:e", {"ex:v": _RaisingLiteral("x", NS["custom"])})
    assert any(type(v) is _RaisingLiteral for v in record.get_attribute("ex:v"))
    with pytest.raises(AttributeError, match="boom"):
        document.get_provn()

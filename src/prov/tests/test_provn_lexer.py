"""Tokeniser tests for PROV-N (W3C PROV-N Recommendation, section 3.8
lexical productions). Table-driven: one case per token class and one per
boundary that a hand-written lexer gets wrong."""

import pytest

from prov.serializers.provn_lexer import ProvNSyntaxError, TokenKind, tokenize


def kinds(text):
    return [t.kind for t in tokenize(text) if t.kind is not TokenKind.EOF]


def values(text):
    return [t.value for t in tokenize(text) if t.kind is not TokenKind.EOF]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("entity", [TokenKind.NAME]),
        ("ex:e1", [TokenKind.NAME]),
        ("<http://example.org/>", [TokenKind.IRI]),
        ('"hello"', [TokenKind.STRING]),
        ('"""multi\nline"""', [TokenKind.STRING]),
        ("42", [TokenKind.INT]),
        ("-42", [TokenKind.INT]),
        ("2011-11-16T16:00:00", [TokenKind.DATETIME]),
        ("2011-11-16T16:00:00.123Z", [TokenKind.DATETIME]),
        ("2011-11-16T16:00:00+01:00", [TokenKind.DATETIME]),
        ("%%", [TokenKind.TYPED]),
        ("-", [TokenKind.MARKER]),
        ("'ex:abc'", [TokenKind.QNAME_LITERAL]),
        (
            "( ) [ ] , ; =",
            [
                TokenKind.LPAREN,
                TokenKind.RPAREN,
                TokenKind.LBRACKET,
                TokenKind.RBRACKET,
                TokenKind.COMMA,
                TokenKind.SEMICOLON,
                TokenKind.EQUALS,
            ],
        ),
    ],
)
def test_token_kinds(text, expected):
    assert kinds(text) == expected


def test_comments_are_skipped():
    text = "entity // trailing\n/* block\ncomment */ agent"
    assert values(text) == [("", "entity"), ("", "agent")]


@pytest.mark.parametrize("ch", list("='(),:;[]"))
def test_escaped_metachar_in_local_part(ch):
    tokens = list(tokenize(f"ex:na\\{ch}me"))
    assert tokens[0].kind is TokenKind.NAME
    assert tokens[0].value == ("ex", f"na{ch}me")


def test_percent_encoding_is_kept_verbatim():
    assert values("ex:a%20b") == [("ex", "a%20b")]


def test_stray_dot_raises_with_position():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("ex:abc."))
    assert (ctx.value.line, ctx.value.column) == (1, 7)


def test_escaped_dot_is_kept():
    assert values(r"ex:abc\.") == [("ex", "abc.")]


def test_inner_dot_is_part_of_the_name():
    assert values("ex:a.b") == [("ex", "a.b")]


def test_langtag_only_after_a_string():
    assert kinds('"a place"@en') == [TokenKind.STRING, TokenKind.LANGTAG]
    assert values('"a place"@en')[1] == "en"
    assert kinds("ex:a@b") == [TokenKind.NAME]
    assert values("ex:a@b") == [("ex", "a@b")]


def test_typed_literal_marker_vs_percent_in_name():
    assert kinds('"1" %% xsd:int') == [
        TokenKind.STRING,
        TokenKind.TYPED,
        TokenKind.NAME,
    ]
    assert kinds("ex:%41b") == [TokenKind.NAME]


def test_marker_vs_negative_int():
    assert kinds("-, -5, - 5") == [
        TokenKind.MARKER,
        TokenKind.COMMA,
        TokenKind.INT,
        TokenKind.COMMA,
        TokenKind.MARKER,
        TokenKind.INT,
    ]
    assert values("-5")[0] == -5


def test_string_escapes_are_decoded():
    assert values(r'"back\\slash and \"quote\""')[0] == 'back\\slash and "quote"'
    assert values('"""a "quoted" word\nline two"""')[0] == 'a "quoted" word\nline two'
    assert values(r'"tab\there"')[0] == "tab\there"


def test_qname_literal_with_escape():
    assert values(r"'ex:we\'ird'")[0] == ("ex", "we'ird")


def test_bare_local_name_has_empty_prefix():
    assert values("e1") == [("", "e1")]


def test_line_and_column_tracking():
    tokens = list(tokenize("entity(\n  ex:e1)"))
    assert (tokens[0].line, tokens[0].column) == (1, 1)
    assert (tokens[2].line, tokens[2].column) == (2, 3)
    assert tokens[-1].kind is TokenKind.EOF


@pytest.mark.parametrize(
    ("text", "line", "column"),
    [
        ('"unterminated', 1, 1),
        ('"""never closed', 1, 1),
        ("<http://no-close", 1, 1),
        ("'ex:open", 1, 1),
        ("entity(\n  ex:e1, ^)", 2, 10),
        ("ex:a:b", 1, 5),
        ('"x" %', 1, 5),
        ("ex:a\\zb", 1, 5),
    ],
)
def test_malformed_input_reports_position(text, line, column):
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize(text))
    assert (ctx.value.line, ctx.value.column) == (line, column)
    assert f"line {line}, column {column}" in str(ctx.value)


def test_unicode_names_and_strings():
    assert values("ex:café") == [("ex", "café")]
    assert values('"日本語"') == ["日本語"]


def test_escaped_colon_at_end_of_local_part():
    assert values(r"ex:a\:") == [("ex", "a:")]


def test_unknown_string_escape_raises():
    with pytest.raises(ProvNSyntaxError, match="unknown string escape"):
        list(tokenize(r'"\q"'))


def test_invalid_qname_literal_raises():
    with pytest.raises(ProvNSyntaxError, match="invalid qualified name"):
        list(tokenize("'not a qname'"))


def test_invalid_language_tag_raises():
    with pytest.raises(ProvNSyntaxError, match="invalid language tag"):
        list(tokenize('"a"@'))

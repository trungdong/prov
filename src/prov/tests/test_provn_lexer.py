"""Tokeniser tests for PROV-N (W3C PROV-N Recommendation, section 3.8
lexical productions). Table-driven: one case per token class and one per
boundary that a hand-written lexer gets wrong."""

import copy
import pickle
import time

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
    with pytest.raises(ProvNSyntaxError, match="unknown string escape") as ctx:
        list(tokenize(r'"\q"'))
    assert (ctx.value.line, ctx.value.column) == (1, 2)


def test_invalid_qname_literal_raises():
    with pytest.raises(ProvNSyntaxError, match="invalid qualified name") as ctx:
        list(tokenize("'not a qname'"))
    assert (ctx.value.line, ctx.value.column) == (1, 5)


def test_invalid_language_tag_raises():
    with pytest.raises(ProvNSyntaxError, match="invalid language tag"):
        list(tokenize('"a"@'))


def test_prefix_only_name_has_empty_local():
    # [52] permits "PN_PREFIX ':'" alone; the Recommendation's own example
    # (section 3.6) is entity(bbc:).
    tokens = list(tokenize("entity(bbc:)"))
    assert [t.value for t in tokens[:4]] == [
        ("", "entity"),
        "(",
        ("bbc", ""),
        ")",
    ]


def test_escaped_hyphen_in_local_part():
    # The Recommendation's own example (section 3.8) is entity(ex:\-).
    assert values(r"ex:\-") == [("ex", "-")]


def test_unterminated_block_comment_raises_with_position():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("entity(ex:e1) /* open"))
    assert (ctx.value.line, ctx.value.column) == (1, 15)
    assert "unterminated comment" in str(ctx.value)


def test_string_escape_error_position_is_inside_the_literal():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize('"abc \\q def"'))
    assert (ctx.value.line, ctx.value.column) == (1, 6)


def test_string_escape_error_position_spans_lines_in_a_long_string():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize('"""ab\ncd \\q"""'))
    assert (ctx.value.line, ctx.value.column) == (2, 4)


def test_qname_literal_error_position_is_the_first_invalid_character():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("'ex:bad name'"))
    assert (ctx.value.line, ctx.value.column) == (1, 8)


def test_huge_integer_raises_instead_of_crashing():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("1" * 5000))
    assert (ctx.value.line, ctx.value.column) == (1, 1)
    assert "digits" in str(ctx.value)


def test_provn_syntax_error_supports_pickle_and_deepcopy():
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize('"unterminated'))
    original = ctx.value

    # Round-trips a value created immediately above, not external input.
    restored = pickle.loads(pickle.dumps(original))  # nosec B301 - nosemgrep
    assert (restored.line, restored.column, restored.message) == (
        original.line,
        original.column,
        original.message,
    )
    assert str(restored) == str(original)

    cloned = copy.deepcopy(original)
    assert (cloned.line, cloned.column, cloned.message) == (
        original.line,
        original.column,
        original.message,
    )
    assert str(cloned) == str(original)


def test_line_comment_ends_at_cr_not_just_lf():
    text = "entity(ex:a) // note\rentity(ex:b)"
    assert values(text) == [
        ("", "entity"),
        "(",
        ("ex", "a"),
        ")",
        ("", "entity"),
        "(",
        ("ex", "b"),
        ")",
    ]


def test_crlf_and_lone_cr_each_count_as_one_line_break():
    crlf_tokens = list(tokenize("a\r\nb"))
    assert (crlf_tokens[1].line, crlf_tokens[1].column) == (2, 1)
    cr_tokens = list(tokenize("a\rb"))
    assert (cr_tokens[1].line, cr_tokens[1].column) == (2, 1)


def test_long_run_of_trailing_dots_is_fast():
    # 200_000 dots isn't large enough to expose the old O(n^2) back-off
    # loop within a 1s bound on typical hardware (~0.5s pre-fix); 1_000_000
    # matches the scale the regression was originally measured at (~7-9s
    # pre-fix) and stays well under 1s with the linear regex-based fix.
    text = "a" + "." * 1_000_000
    start = time.perf_counter()
    with pytest.raises(ProvNSyntaxError):
        list(tokenize(text))
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize("text", ["ex.:abc", "a.b.:c", "ex.:"])
def test_prefix_cannot_end_in_a_dot(text):
    dot_column = text.index(".") + 1
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize(text))
    assert ctx.value.column >= dot_column


def test_prefix_with_inner_dot_is_still_accepted():
    assert values("a.b:c") == [("a.b", "c")]


def test_qname_literal_trailing_dot_raises():
    # Unlike the bare form, this used to succeed silently before _PN_LOCAL
    # excluded a bare trailing '.'; now _QNAME_FULL simply doesn't match
    # "ex:abc." and _split_qname reports the dot itself, consistent with
    # test_qname_literal_error_position_is_the_first_invalid_character.
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("'ex:abc.'"))
    assert (ctx.value.line, ctx.value.column) == (1, 8)


@pytest.mark.parametrize(
    "text",
    [
        chr(0x664) + chr(0x662),  # Arabic-Indic digits four, two
        chr(0xFF14) + chr(0xFF12),  # fullwidth digits four, two
    ],
)
def test_non_ascii_digits_are_names_not_integers(text):
    # These are Unicode Nd but not [0-9]; the grammar's DIGIT is ASCII-only,
    # so they are ordinary name characters, not an integer literal.
    assert kinds(text) == [TokenKind.NAME]
    assert values(text) == [("", text)]


def test_iri_allows_non_breaking_space_but_rejects_control_characters():
    nbsp = chr(0xA0)
    assert values(f"<http://a/b{nbsp}c>") == [f"http://a/b{nbsp}c"]
    with pytest.raises(ProvNSyntaxError, match="unterminated IRI"):
        list(tokenize("<a\x01b>"))

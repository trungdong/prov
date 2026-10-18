"""Tokeniser tests for PROV-N (W3C PROV-N Recommendation, section 3.8
lexical productions). Table-driven: one case per token class and one per
boundary that a hand-written lexer gets wrong."""

import copy
import pickle
import re
import time

import pytest

from prov.serializers import provn_lexer
from prov.serializers.provn_lexer import ProvNSyntaxError, Token, TokenKind, tokenize


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
def test_token_kinds(text, expected) -> None:
    assert kinds(text) == expected


def test_token_uses_slots() -> None:
    # Every Token instance is thrown away almost immediately by the parser,
    # so __dict__ per instance is pure overhead.
    assert not hasattr(Token(TokenKind.EOF, "", None, 1, 1), "__dict__")


def test_comments_are_skipped() -> None:
    text = "entity // trailing\n/* block\ncomment */ agent"
    assert values(text) == [("", "entity"), ("", "agent")]


@pytest.mark.parametrize("ch", list("='(),:;[]"))
def test_escaped_metachar_in_local_part(ch) -> None:
    tokens = list(tokenize(f"ex:na\\{ch}me"))
    assert tokens[0].kind is TokenKind.NAME
    assert tokens[0].value == ("ex", f"na{ch}me")


def test_percent_encoding_is_kept_verbatim() -> None:
    assert values("ex:a%20b") == [("ex", "a%20b")]


def test_stray_dot_raises_with_position() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("ex:abc."))
    assert (ctx.value.line, ctx.value.column) == (1, 7)


def test_escaped_dot_is_kept() -> None:
    assert values(r"ex:abc\.") == [("ex", "abc.")]


def test_inner_dot_is_part_of_the_name() -> None:
    assert values("ex:a.b") == [("ex", "a.b")]


def test_langtag_only_after_a_string() -> None:
    assert kinds('"a place"@en') == [TokenKind.STRING, TokenKind.LANGTAG]
    assert values('"a place"@en')[1] == "en"
    assert kinds("ex:a@b") == [TokenKind.NAME]
    assert values("ex:a@b") == [("ex", "a@b")]


def test_typed_literal_marker_vs_percent_in_name() -> None:
    assert kinds('"1" %% xsd:int') == [
        TokenKind.STRING,
        TokenKind.TYPED,
        TokenKind.NAME,
    ]
    assert kinds("ex:%41b") == [TokenKind.NAME]


def test_marker_vs_negative_int() -> None:
    assert kinds("-, -5, - 5") == [
        TokenKind.MARKER,
        TokenKind.COMMA,
        TokenKind.INT,
        TokenKind.COMMA,
        TokenKind.MARKER,
        TokenKind.INT,
    ]
    assert values("-5")[0] == -5


def test_string_escapes_are_decoded() -> None:
    assert values(r'"back\\slash and \"quote\""')[0] == 'back\\slash and "quote"'
    assert values('"""a "quoted" word\nline two"""')[0] == 'a "quoted" word\nline two'
    assert values(r'"tab\there"')[0] == "tab\there"


def test_qname_literal_with_escape() -> None:
    assert values(r"'ex:we\'ird'")[0] == ("ex", "we'ird")


def test_bare_local_name_has_empty_prefix() -> None:
    assert values("e1") == [("", "e1")]


def test_line_and_column_tracking() -> None:
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
def test_malformed_input_reports_position(text, line, column) -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize(text))
    assert (ctx.value.line, ctx.value.column) == (line, column)
    assert f"line {line}, column {column}" in str(ctx.value)


def test_unicode_names_and_strings() -> None:
    assert values("ex:café") == [("ex", "café")]
    assert values('"日本語"') == ["日本語"]


def test_escaped_colon_at_end_of_local_part() -> None:
    assert values(r"ex:a\:") == [("ex", "a:")]


def test_unknown_string_escape_raises() -> None:
    with pytest.raises(ProvNSyntaxError, match="unknown string escape") as ctx:
        list(tokenize(r'"\q"'))
    assert (ctx.value.line, ctx.value.column) == (1, 2)


def test_invalid_qname_literal_raises() -> None:
    with pytest.raises(ProvNSyntaxError, match="invalid qualified name") as ctx:
        list(tokenize("'not a qname'"))
    assert (ctx.value.line, ctx.value.column) == (1, 5)


def test_invalid_language_tag_raises() -> None:
    with pytest.raises(ProvNSyntaxError, match="invalid language tag"):
        list(tokenize('"a"@'))


def test_prefix_only_name_has_empty_local() -> None:
    # [52] permits "PN_PREFIX ':'" alone; the Recommendation's own example
    # (section 3.6) is entity(bbc:).
    tokens = list(tokenize("entity(bbc:)"))
    assert [t.value for t in tokens[:4]] == [
        ("", "entity"),
        "(",
        ("bbc", ""),
        ")",
    ]


def test_escaped_hyphen_in_local_part() -> None:
    # The Recommendation's own example (section 3.8) is entity(ex:\-).
    assert values(r"ex:\-") == [("ex", "-")]


def test_unterminated_block_comment_raises_with_position() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("entity(ex:e1) /* open"))
    assert (ctx.value.line, ctx.value.column) == (1, 15)
    assert "unterminated comment" in str(ctx.value)


def test_string_escape_error_position_is_inside_the_literal() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize('"abc \\q def"'))
    assert (ctx.value.line, ctx.value.column) == (1, 6)


def test_string_escape_error_position_spans_lines_in_a_long_string() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize('"""ab\ncd \\q"""'))
    assert (ctx.value.line, ctx.value.column) == (2, 4)


def test_qname_literal_error_position_is_the_first_invalid_character() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("'ex:bad name'"))
    assert (ctx.value.line, ctx.value.column) == (1, 8)


def test_huge_integer_raises_instead_of_crashing() -> None:
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize("1" * 5000))
    assert (ctx.value.line, ctx.value.column) == (1, 1)
    assert "digits" in str(ctx.value)


def test_provn_syntax_error_supports_pickle_and_deepcopy() -> None:
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


def test_line_comment_ends_at_cr_not_just_lf() -> None:
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


def test_crlf_and_lone_cr_each_count_as_one_line_break() -> None:
    crlf_tokens = list(tokenize("a\r\nb"))
    assert (crlf_tokens[1].line, crlf_tokens[1].column) == (2, 1)
    cr_tokens = list(tokenize("a\rb"))
    assert (cr_tokens[1].line, cr_tokens[1].column) == (2, 1)


def test_long_run_of_trailing_dots_is_fast() -> None:
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
def test_prefix_cannot_end_in_a_dot(text) -> None:
    dot_column = text.index(".") + 1
    with pytest.raises(ProvNSyntaxError) as ctx:
        list(tokenize(text))
    assert ctx.value.column >= dot_column


def test_prefix_with_inner_dot_is_still_accepted() -> None:
    assert values("a.b:c") == [("a.b", "c")]


def test_qname_literal_trailing_dot_raises() -> None:
    # _QNAME_FULL rejects a bare trailing '.'; the reported position is the dot.
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
def test_non_ascii_digits_are_names_not_integers(text) -> None:
    # These are Unicode Nd but not [0-9]; the grammar's DIGIT is ASCII-only,
    # so they are ordinary name characters, not an integer literal.
    assert kinds(text) == [TokenKind.NAME]
    assert values(text) == [("", text)]


def test_iri_allows_non_breaking_space_but_rejects_control_characters() -> None:
    nbsp = chr(0xA0)
    assert values(f"<http://a/b{nbsp}c>") == [f"http://a/b{nbsp}c"]
    with pytest.raises(ProvNSyntaxError, match="unterminated IRI"):
        list(tokenize("<a\x01b>"))


def test_pn_chars_classes_match_the_recommendation_s_own_literal_ranges() -> None:
    """provn_lexer's PN_CHARS_BASE/PN_CHARS_U/PN_CHARS are now derived from
    prov.identifier's shared NCName tables rather than spelled out here; this
    pins that derivation against the Recommendation's own literal ranges
    ([53]-[55]) they replaced, over the full non-surrogate codepoint space."""
    old_pn_chars_base = (
        r"A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
        r"\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF"
        r"\uFDF0-\uFFFD\U00010000-\U000EFFFF"
    )
    old_pn_chars_u = old_pn_chars_base + "_"
    old_pn_chars = old_pn_chars_u + r"\-0-9\u00B7\u0300-\u036F\u203F-\u2040"

    checks = [
        (old_pn_chars_base, provn_lexer._PN_CHARS_BASE),
        (old_pn_chars_u, provn_lexer._PN_CHARS_U),
        (old_pn_chars, provn_lexer._PN_CHARS),
    ]
    compiled = [(re.compile(f"[{old}]"), re.compile(f"[{new}]")) for old, new in checks]

    for codepoint in range(0x110000):
        if 0xD800 <= codepoint <= 0xDFFF:  # surrogates: not real characters
            continue
        char = chr(codepoint)
        for old_re, new_re in compiled:
            assert bool(old_re.match(char)) == bool(new_re.match(char)), hex(codepoint)


@pytest.mark.parametrize("text", ['"a\rb"', "'a\rb'"])
def test_carriage_return_ends_a_short_literal(text) -> None:
    with pytest.raises(ProvNSyntaxError, match="unterminated"):
        list(tokenize(text))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r'"caf\u00E9"', "café"),
        (r'"caf\u00e9"', "café"),
        (r'"\U0001F600"', "\U0001f600"),
        (r'"""caf\u00E9\nline"""', "café\nline"),
        (r'"a\u0022b"', 'a"b'),
        (r'"\\u00E9"', "\\u00E9"),
        (r"<http://example.org/caf\u00E9>", "http://example.org/café"),
        (r"<http://example.org/\U0001F600>", "http://example.org/\U0001f600"),
    ],
)
def test_code_point_escapes_are_decoded(text, expected) -> None:
    assert values(text) == [expected]


@pytest.mark.parametrize(
    ("text", "message", "column"),
    [
        (r'"ab\u00G9"', r"escape '\u' needs four hex digits", 4),
        (r'"ab\U0001F60"', r"escape '\U' needs eight hex digits", 4),
        (r'"ab\uD800"', r"escape '\uD800' is not a Unicode scalar value", 4),
        (r'"ab\U00110000"', r"escape '\U00110000' is not a Unicode scalar value", 4),
        (r"<http://a/\u00G9>", r"escape '\u' needs four hex digits", 11),
        (r"<http://a/\q>", r"unknown IRI escape '\q'", 11),
        (r"<http://a/\n>", r"unknown IRI escape '\n'", 11),
        (r"<http://a/\\>", r"unknown IRI escape '\\'", 11),
        (r"<http://a/\|>", r"unknown IRI escape '\|'", 11),
        (
            r"<http://a/\u0020>",
            r"escape '\u0020' encodes a character an IRI cannot contain",
            11,
        ),
        (
            r"<http://a/\u003E>",
            r"escape '\u003E' encodes a character an IRI cannot contain",
            11,
        ),
    ],
)
def test_bad_code_point_escape_raises_at_the_escape(text, message, column) -> None:
    with pytest.raises(ProvNSyntaxError, match=re.escape(message)) as ctx:
        list(tokenize(text))
    assert (ctx.value.line, ctx.value.column) == (1, column)


def test_bad_code_point_escape_position_on_a_later_line_of_a_long_string() -> None:
    with pytest.raises(
        ProvNSyntaxError, match=re.escape(r"escape '\u' needs four hex digits")
    ) as ctx:
        list(tokenize('"""ab\ncd \\u12"""'))
    assert (ctx.value.line, ctx.value.column) == (2, 4)


def lexer_warnings(text):
    collected: list[str] = []
    list(tokenize(text, collected))
    return collected


# Unicode whitespace that WS (SPARQL [93]) excludes, U+1680 apart: it is also
# a name character, so it has its own test.
NON_WS_SPACES = [
    "\x0b",
    "\x0c",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x1f",
    "\x85",
    "\xa0",
    *[chr(code) for code in range(0x2000, 0x200B)],
    "\u2028",
    "\u2029",
    "\u202f",
    "\u205f",
    "\u3000",
]


def test_non_ws_spaces_are_every_unicode_space_but_the_four_ws_characters() -> None:
    spaces = {chr(code) for code in range(0x110000) if chr(code).isspace()}
    assert spaces - set(" \t\r\n") == {*NON_WS_SPACES, "\u1680"}


@pytest.mark.parametrize("ch", NON_WS_SPACES)
def test_non_ws_space_between_tokens_is_skipped_and_warned(ch) -> None:
    text = f"entity(ex:e){ch}endDocument"
    assert values(text) == values("entity(ex:e) endDocument")
    assert lexer_warnings(text) == [
        f"line 1, column 13: U+{ord(ch):04X} is not PROV-N whitespace."
        " prov 3.3.0 will reject this (#509)"
    ]


def test_ogham_space_mark_warns_that_it_becomes_a_name_character() -> None:
    text = "entity(\u1680ex:e)"
    assert values(text) == values("entity(ex:e)")
    assert lexer_warnings(text) == [
        "line 1, column 8: U+1680 is not PROV-N whitespace."
        " prov 3.3.0 will read it as a name character (#509)"
    ]


def test_a_run_of_one_character_warns_once() -> None:
    assert lexer_warnings("entity(ex:e)\xa0\xa0\xa0\u2028endDocument") == [
        "line 1, column 13: U+00A0 is not PROV-N whitespace. prov 3.3.0 will reject this (#509)",
        "line 1, column 16: U+2028 is not PROV-N whitespace. prov 3.3.0 will reject this (#509)",
    ]


def test_non_ws_space_between_ws_and_comments_is_skipped() -> None:
    text = "entity(ex:e) \xa0// note\n\xa0endDocument"
    assert values(text) == values("entity(ex:e) endDocument")
    assert lexer_warnings(text) == [
        "line 1, column 14: U+00A0 is not PROV-N whitespace. prov 3.3.0 will reject this (#509)",
        "line 2, column 1: U+00A0 is not PROV-N whitespace. prov 3.3.0 will reject this (#509)",
    ]


def test_ws_and_spaces_inside_comments_strings_and_iris_do_not_warn() -> None:
    text = 'entity(ex:e,\t[ex:a="\xa0"])\r\n// \xa0\n/* \u3000 */ <http://a/\xa0>'
    assert lexer_warnings(text) == []

"""Tests for the PROV-N Pygments lexer (prov.pygments).

The reader is the oracle for well-formed input: a text it accepts lexes with no Error
token. Every round trip builds the lexer with ``stripnl=False, ensurenl=False``, because
Pygments otherwise strips leading and trailing newlines and appends one, and the joined
token values must equal the raw text.
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import warnings
from collections.abc import Callable
from pathlib import Path

import pytest
from pygments.lexer import Lexer
from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    get_lexer_for_mimetype,
)
from pygments.token import (
    Comment,
    Error,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Whitespace,
    _TokenType,
)

import prov
from prov import identifier, pygments as lexer_module
from prov.model import ProvDocument, _values
from prov.pygments import ProvNLexer
from prov.serializers import provn_lexer as tokenizer_module
from prov.serializers.provn_lexer import ProvNSyntaxError
from prov.serializers.provn_parser import _KEYWORDS, _STRUCTURAL
from prov.tests import examples

Tok = tuple[_TokenType, str]

TESTS = Path(__file__).parent
CORPUS = sorted(TESTS.rglob("*.provn"))
P = Punctuation


def lex(text: str) -> list[Tok]:
    return list(ProvNLexer(stripnl=False, ensurenl=False).get_tokens(text))


def rejoins(tokens: list[Tok], text: str) -> bool:
    return "".join(value for _, value in tokens) == text


def has_error(tokens: list[Tok]) -> bool:
    return any(ttype is Error for ttype, _ in tokens)


def reader_accepts(source: Path | io.StringIO) -> bool:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            prov.read(source, format="provn")
        except ProvNSyntaxError:
            return False
    return True


# -- round trips ------------------------------------------------------------------


def test_corpus_round_trips_and_accepted_files_have_no_error() -> None:
    assert CORPUS
    failures = []
    accepted = 0
    for path in CORPUS:
        text = path.read_text(encoding="utf-8")
        tokens = lex(text)
        name = path.relative_to(TESTS).as_posix()
        if not rejoins(tokens, text):
            failures.append(f"{name}: token values do not rejoin the text")
        else:
            ok = reader_accepts(path)
            accepted += ok
            if ok and has_error(tokens):
                failures.append(f"{name}: Error token on a file the reader accepts")
    assert failures == []
    assert accepted


@pytest.mark.parametrize(
    "build", [pytest.param(build, id=name) for name, build in examples.tests]
)
def test_examples_lex_without_error(build: Callable[[], ProvDocument]) -> None:
    text = build().get_provn()
    tokens = lex(text)
    assert rejoins(tokens, text)
    assert not has_error(tokens)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param('document\nentity(ex:a, [ex:k="never ends])\n', id="string"),
        pytest.param("document\nprefix ex <http://example.org/\n", id="iri"),
        pytest.param("document\n/* never ends\nentity(ex:a)", id="comment"),
        pytest.param("document\nentity(ex:a,\n", id="mid-statement"),
        pytest.param('document\nentity(ex:a, [ex:k="""never\nends])', id="long-string"),
        pytest.param("document\n)]} ; = \x00 \u00a0 \n", id="stray-characters"),
    ],
)
def test_rejected_text_terminates_and_rejoins(text: str) -> None:
    assert rejoins(lex(text), text)


@pytest.mark.parametrize(
    ("text", "first"),
    [
        pytest.param(
            "/* x\nentity(ex:a)",
            (Comment.Multiline, "/* x\nentity(ex:a)"),
            id="comment",
        ),
        pytest.param(
            '"""x\nentity(ex:a)',
            (String.Double, '"""x\nentity(ex:a)'),
            id="long-string",
        ),
        pytest.param('"x\nentity(ex:a)', (String.Double, '"x'), id="string"),
        pytest.param("'x\nentity(ex:a)", (String.Single, "'x"), id="quoted-name"),
        pytest.param("<http://x\nentity(ex:a)", (String.Other, "<http://x"), id="iri"),
        pytest.param(
            "<http://x entity(ex:a)", (String.Other, "<http://x"), id="iri-space"
        ),
    ],
)
def test_unterminated_construct_is_one_token(text: str, first: Tok) -> None:
    """A comment or long string runs to the end of the text.

    A string or quoted name runs to the end of its line. An IRI runs to the first
    character in \\x00-\\x20, a space included.
    """
    assert lex(text)[0] == first


# -- the rich fixture --------------------------------------------------------------

# Rows of spec 3.3 that attribute-values.provn holds. Each value must carry this token
# type wherever it occurs in the stream, and must occur.
RICH_FIXTURE = TESTS / "fixtures" / "written-by-3.2.3" / "attribute-values.provn"
RICH_FIXTURE_TOKENS: list[Tok] = [
    (Keyword, "document"),
    (Keyword, "endDocument"),
    (Keyword.Declaration, "prefix"),
    (Name.Namespace, "ex"),
    (Name.Namespace, "ex_1"),
    (Name.Namespace, "xsd"),
    (String.Other, "<http://example.org/>"),
    (String.Other, "<http://example4.org/>"),
    (Keyword, "entity"),
    (P, ":"),
    (P, "("),
    (P, ")"),
    (P, "["),
    (P, "]"),
    (P, ","),
    (P, "="),
    (Name, "e0"),
    (Name, "e37"),
    (Name.Attribute, "v"),
    (String.Double, '"un lieu"'),
    (String.Double, r'"http://example.org/a\"b\\c"'),
    (String.Double, '"-INF"'),
    (Name.Decorator, "@fr"),
    (Name.Decorator, "@en"),
    (Operator, "%%"),
    (Keyword.Type, "long"),
    (Keyword.Type, "dateTime"),
    (Number.Integer, "1"),
    (String.Single, "'ex:abc'"),
    (String.Single, "'ex_1:zabcd'"),
    (Whitespace, "\n  "),
    (Whitespace, " "),
]


def test_rich_fixture_tokens() -> None:
    tokens = lex(RICH_FIXTURE.read_text(encoding="utf-8"))
    for ttype, value in RICH_FIXTURE_TOKENS:
        assert {t for t, v in tokens if v == value} == {ttype}, value


# -- the hand-written snippet ------------------------------------------------------


def seq(*parts: list[Tok]) -> list[Tok]:
    return [token for part in parts for token in part]


def lit(ttype: _TokenType, value: str) -> list[Tok]:
    return [(ttype, value)]


def punct(characters: str) -> list[Tok]:
    return [(P, character) for character in characters]


def qname(prefix: str, local: str, kind: _TokenType = Name) -> list[Tok]:
    """The three tokens of a qualified name (spec 3.3)."""
    return [(Name.Namespace, prefix), (P, ":"), (kind, local)]


def commas(*items: list[Tok]) -> list[Tok]:
    tokens: list[Tok] = []
    for position, item in enumerate(items):
        tokens += punct(",") if position else []
        tokens += item
    return tokens


def call(name: list[Tok], *arguments: list[Tok]) -> list[Tok]:
    return seq(name, punct("("), commas(*arguments), punct(")"))


def entity(*arguments: list[Tok]) -> list[Tok]:
    return call(lit(Keyword, "entity"), *arguments)


def attrs(*pairs: list[Tok]) -> list[Tok]:
    return seq(punct("["), commas(*pairs), punct("]"))


def key(name: list[Tok], value: list[Tok]) -> list[Tok]:
    return seq(name, punct("="), value)


def qkey(prefix: str, local: str, value: list[Tok]) -> list[Tok]:
    return key(qname(prefix, local, Name.Attribute), value)


def string(value: str) -> list[Tok]:
    return lit(String.Double, value)


def language(value: str, tag: str) -> list[Tok]:
    return seq(string(value), lit(Name.Decorator, tag))


MARKER = lit(Keyword.Constant, "-")

# Each item is a run of source lines and the tokens it lexes to, whitespace dropped.
SNIPPET: list[tuple[str, list[Tok]]] = [
    ("document", lit(Keyword, "document")),
    (
        "  default <http://example.org/>",
        seq(
            lit(Keyword.Declaration, "default"),
            lit(String.Other, "<http://example.org/>"),
        ),
    ),
    (
        "  prefix ex <http://example.org/ex#>",
        seq(
            lit(Keyword.Declaration, "prefix"),
            lit(Name.Namespace, "ex"),
            lit(String.Other, "<http://example.org/ex#>"),
        ),
    ),
    (
        "  // a comment, with 'quotes' and \"more\"",
        lit(Comment.Single, "// a comment, with 'quotes' and \"more\""),
    ),
    (
        "  /* a block\n     comment */",
        lit(Comment.Multiline, "/* a block\n     comment */"),
    ),
    (
        "  prefix document <http://example.org/doc#>",
        seq(
            lit(Keyword.Declaration, "prefix"),
            lit(Name.Namespace, "document"),
            lit(String.Other, "<http://example.org/doc#>"),
        ),
    ),
    # Structural words and declarations are names inside brackets.
    ("  entity(bundle)", entity(lit(Name, "bundle"))),
    ("  entity(@x)", entity(lit(Name, "@x"))),
    ("  entity(1a)", entity(lit(Name, "1a"))),
    ("  entity (ex:e)", entity(qname("ex", "e"))),
    # An expression name as an argument is a name; a comment may precede the parenthesis.
    ("  entity(entity)", entity(lit(Name, "entity"))),
    (
        "  ex:foo /* c */ (ex:a)",
        seq(
            qname("ex", "foo", Name.Function),
            lit(Comment.Multiline, "/* c */"),
            punct("("),
            qname("ex", "a"),
            punct(")"),
        ),
    ),
    # An empty local part: two tokens, not three.
    ("  entity(ex:)", entity(seq(lit(Name.Namespace, "ex"), punct(":")))),
    (r"  entity(ex:a\:b)", entity(qname("ex", r"a\:b"))),
    ("  entity(ex:c%20d)", entity(qname("ex", "c%20d"))),
    ("  entity(ex:\u00e9l\u00e8ve)", entity(qname("ex", "\u00e9l\u00e8ve"))),
    (
        "  ex:entity(ex:a, ex:b)",
        call(qname("ex", "entity", Name.Function), qname("ex", "a"), qname("ex", "b")),
    ),
    ("  entity(ex:document)", entity(qname("ex", "document"))),
    # A structural word followed by a colon is a prefix.
    (
        "  document:foo(ex:a)",
        call(qname("document", "foo", Name.Function), qname("ex", "a")),
    ),
    # Values: marker, negative integer, quoted name, comment marker in a string, language
    # tags with and without trivia before them, datatype.
    (
        '  entity(ex:t, [prefix="x", ex:n=-4, ex:q=\'ex:q\', ex:s="a // b",\n'
        '                ex:l="x"@en, ex:u="y" @en, ex:d="1" %% xsd:string])',
        entity(
            qname("ex", "t"),
            attrs(
                key(lit(Name.Attribute, "prefix"), string('"x"')),
                qkey("ex", "n", lit(Number.Integer, "-4")),
                qkey("ex", "q", lit(String.Single, "'ex:q'")),
                qkey("ex", "s", string('"a // b"')),
                qkey("ex", "l", language('"x"', "@en")),
                qkey("ex", "u", language('"y"', "@en")),
                qkey(
                    "ex",
                    "d",
                    seq(
                        string('"1"'),
                        lit(Operator, "%%"),
                        qname("xsd", "string", Keyword.Type),
                    ),
                ),
            ),
        ),
    ),
    (
        '  entity(ex:m, [ex:m="""line one\nline two"""@en])',
        entity(
            qname("ex", "m"),
            attrs(qkey("ex", "m", language('"""line one\nline two"""', "@en"))),
        ),
    ),
    # The marker and the semicolon, the datetime, the two mention spellings.
    (
        "  wasGeneratedBy(-; ex:e, ex:a, -)",
        seq(
            lit(Keyword, "wasGeneratedBy"),
            punct("("),
            MARKER,
            punct(";"),
            commas(qname("ex", "e"), qname("ex", "a"), MARKER),
            punct(")"),
        ),
    ),
    (
        "  wasGeneratedBy(ex:g; ex:e, ex:a, 2012-03-31T09:21:00)",
        seq(
            lit(Keyword, "wasGeneratedBy"),
            punct("("),
            qname("ex", "g"),
            punct(";"),
            commas(
                qname("ex", "e"),
                qname("ex", "a"),
                lit(Literal.Date, "2012-03-31T09:21:00"),
            ),
            punct(")"),
        ),
    ),
    (
        "  prov:mentionOf(ex:s, ex:g, ex:p)",
        call(
            qname("prov", "mentionOf", Keyword),
            qname("ex", "s"),
            qname("ex", "g"),
            qname("ex", "p"),
        ),
    ),
    (
        "  mentionOf(ex:s, ex:g, ex:p)",
        call(
            lit(Keyword, "mentionOf"),
            qname("ex", "s"),
            qname("ex", "g"),
            qname("ex", "p"),
        ),
    ),
    # An extensibility call with a tuple, a nested call and an attribute block.
    (
        '  ex:foo(ex:i; { ex:b, (ex:c, ex:d) }, ex:bar(ex:z, 1, "s"), [ex:k="v"])',
        seq(
            qname("ex", "foo", Name.Function),
            punct("("),
            qname("ex", "i"),
            punct(";"),
            punct("{"),
            qname("ex", "b"),
            punct(","),
            punct("("),
            commas(qname("ex", "c"), qname("ex", "d")),
            punct(")"),
            punct("}"),
            punct(","),
            call(
                qname("ex", "bar", Name.Function),
                qname("ex", "z"),
                lit(Number.Integer, "1"),
                string('"s"'),
            ),
            punct(","),
            attrs(qkey("ex", "k", string('"v"'))),
            punct(")"),
        ),
    ),
    # Back outside every bracket.
    ("  entity(ex:after)", entity(qname("ex", "after"))),
    # An attribute block broken over lines, structural words as keys after the break.
    (
        '  entity(ex:b, [ex:a="1",\n                prefix="x",\n'
        '                document="y"])',
        entity(
            qname("ex", "b"),
            attrs(
                qkey("ex", "a", string('"1"')),
                key(lit(Name.Attribute, "prefix"), string('"x"')),
                key(lit(Name.Attribute, "document"), string('"y"')),
            ),
        ),
    ),
    # The name after "bundle" is a name, whatever it spells.
    ("  bundle bundle", seq(lit(Keyword, "bundle"), lit(Name, "bundle"))),
    ("    entity(ex:inb)", entity(qname("ex", "inb"))),
    ("  endBundle", lit(Keyword, "endBundle")),
    ("  bundle ex:document", seq(lit(Keyword, "bundle"), qname("ex", "document"))),
    ("    entity(ex:inb2)", entity(qname("ex", "inb2"))),
    ("  endBundle", lit(Keyword, "endBundle")),
    ("endDocument", lit(Keyword, "endDocument")),
]
SNIPPET_TEXT = "\n".join(source for source, _ in SNIPPET) + "\n"
SNIPPET_TOKENS = [token for _, tokens in SNIPPET for token in tokens]


def test_snippet_is_accepted_by_the_reader() -> None:
    assert reader_accepts(io.StringIO(SNIPPET_TEXT))


def test_snippet_tokens() -> None:
    tokens = lex(SNIPPET_TEXT)
    assert rejoins(tokens, SNIPPET_TEXT)
    assert [t for t in tokens if t[0] is not Whitespace] == SNIPPET_TOKENS


# -- the copies and the registration -----------------------------------------------


def test_expression_and_structural_words_match_the_parser() -> None:
    bare = {name for prefix, name in _KEYWORDS if prefix == ""}
    assert set(lexer_module._EXPRESSIONS) == bare | {"mentionOf"}
    assert ("prov", "mentionOf") in _KEYWORDS
    assert set(lexer_module._STRUCTURAL) == _STRUCTURAL


@pytest.mark.parametrize(
    ("source", "name"),
    [
        (identifier, name)
        for name in (
            "_NCNAME_START_CHARS",
            "_PN_CHARS",
            "_PN_CHARS_ESC",
            "_PN_CHARS_OTHER",
            "_PN_PREFIX",
        )
    ]
    + [(_values, name) for name in ("XSD_DATETIME_PATTERN", "LANGTAG_PATTERN")]
    + [
        (tokenizer_module, name)
        for name in (
            "_PN_OTHERS",
            "_PERCENT",
            "_ESC",
            "_LOCAL_START",
            "_LOCAL_CONT",
            "_LOCAL_LAST",
            "_PN_LOCAL",
        )
    ],
)
def test_copied_strings_equal_their_sources(source: object, name: str) -> None:
    assert getattr(lexer_module, name) == getattr(source, name)


@pytest.mark.parametrize(
    ("lookup", "argument"),
    [
        pytest.param(get_lexer_by_name, "provn", id="name"),
        pytest.param(get_lexer_by_name, "prov-n", id="alias"),
        pytest.param(get_lexer_for_filename, "a.provn", id="filename"),
        pytest.param(get_lexer_for_mimetype, "text/provenance-notation", id="mimetype"),
    ],
)
def test_lookup_finds_the_lexer(lookup: Callable[[str], Lexer], argument: str) -> None:
    assert isinstance(lookup(argument), ProvNLexer)


def run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("statement", "absent"),
    [
        pytest.param("import prov", ["pygments"], id="prov"),
        pytest.param(
            "import prov.pygments",
            ["prov.identifier", "prov.model", "prov.serializers"],
            id="prov.pygments",
        ),
    ],
)
def test_imports_stay_apart(statement: str, absent: list[str]) -> None:
    result = run_isolated(
        f"import sys; {statement}; print([m for m in {absent!r} if m in sys.modules])"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "[]\n"


def test_import_without_pygments_names_the_extra() -> None:
    result = run_isolated(
        "import sys\n"
        "sys.modules['pygments'] = None\n"
        "try:\n"
        "    import prov.pygments\n"
        "except ModuleNotFoundError as e:\n"
        "    print(e)\n"
    )
    assert result.returncode == 0, result.stderr
    assert re.search(r"prov\[pygments\]", result.stdout)

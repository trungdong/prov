"""Tokeniser for PROV-N (https://www.w3.org/TR/prov-n/, section 3.8).

Produces a flat token stream with line and column positions. Keywords are
not distinguished here: every bare or prefixed name is a ``NAME`` token, and
the parser decides whether a name at statement start is a keyword. The one
context-sensitive rule is the language tag, which only follows a string.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from prov.identifier import _NCNAME_CHARS, _NCNAME_START_CHARS
from prov.model import ProvException

__all__ = ["ProvNSyntaxError", "Token", "TokenKind", "tokenize"]


class ProvNSyntaxError(ProvException):
    """A PROV-N document could not be tokenised or parsed.

    Attributes:
        message: What was expected and what was found.
        line: 1-based line of the offending token.
        column: 1-based column of the offending token.
    """

    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"line {line}, column {column}: {message}")
        self.message = message
        self.line = line
        self.column = column

    def __reduce__(self) -> tuple[type[ProvNSyntaxError], tuple[str, int, int]]:
        return type(self), (self.message, self.line, self.column)


class TokenKind(Enum):
    """Token classes; the names follow the Recommendation's productions."""

    NAME = "name"  # QUALIFIED_NAME [51], value (prefix, local)
    QNAME_LITERAL = "qualified name literal"  # 'prefix:local', value (prefix, local)
    IRI = "IRI"  # IRI_REF [56], value the IRI text
    STRING = "string"  # STRING_LITERAL [60], value the unescaped text
    INT = "integer"  # INT_LITERAL [61], value an int
    DATETIME = "dateTime"  # DATETIME [62], value the lexical form
    LANGTAG = "language tag"  # LANGTAG [63], value the tag
    TYPED = "%%"
    MARKER = "-"
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    SEMICOLON = ";"
    EQUALS = "="
    EOF = "end of input"


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    text: str
    value: Any
    line: int
    column: int


# Character classes from the Recommendation ([53] to [55]); '.' is handled
# in the local-part patterns because its placement rules differ, so PN_CHARS
# is PROV-N's share of prov.identifier's NCName tables minus '.'. PN_CHARS_U
# (NCName's NameStartChar, '_' included) is that table unchanged; PN_CHARS_BASE
# (SPARQL's PN_CHARS_BASE, no leading '_') strips '_' back out. Both classes'
# equivalence to the NCName tables over the full codepoint space is pinned
# by test_provn_lexer.py.
_PN_CHARS_U = _NCNAME_START_CHARS
_PN_CHARS_BASE = _PN_CHARS_U.replace("_", "")
_PN_CHARS = _NCNAME_CHARS.replace(".", "")
_PN_OTHERS = r"/@~&+*?#$!"
_PERCENT = r"%[0-9A-Fa-f]{2}"
_ESC = r"\\[=',\-:;\[\]().]"
_LOCAL_START = rf"[{_PN_CHARS_U}0-9{_PN_OTHERS}]|{_PERCENT}|{_ESC}"
_LOCAL_CONT = rf"[{_PN_CHARS}.{_PN_OTHERS}]|{_PERCENT}|{_ESC}"
# The last character of a local part can't be a bare '.' ([54]); an escaped
# '\.' or a percent-escape are still fine, so this is _LOCAL_CONT without
# the bare-dot alternative. Folding the end rule into the grammar keeps
# matching linear even for a long run of trailing dots.
_LOCAL_LAST = rf"[{_PN_CHARS}{_PN_OTHERS}]|{_PERCENT}|{_ESC}"
_PN_LOCAL = rf"(?:{_LOCAL_START})(?:(?:{_LOCAL_CONT})*(?:{_LOCAL_LAST}))?"
# SPARQL's PN_PREFIX ([52]'s reference production) is PN_CHARS_BASE
# ((PN_CHARS | '.')* PN_CHARS)? -- a prefix can't end in '.' either.
_PN_PREFIX = rf"[{_PN_CHARS_BASE}](?:[{_PN_CHARS}.]*[{_PN_CHARS}])?"

# [52] allows "PN_PREFIX ':'" alone (empty local, e.g. the Recommendation's
# own `bbc:`), so the prefixed branch's local part is optional; group 3 is
# the bare, unprefixed local part.
_QNAME = re.compile(rf"(?:({_PN_PREFIX}):({_PN_LOCAL})?|({_PN_LOCAL}))")
# Anchored variant of _QNAME, built from the same pattern so the two can't
# drift apart.
_QNAME_FULL = re.compile(_QNAME.pattern + r"\Z")
# DIGIT is [0-9] ([55]); \d would also match other Unicode decimal digits,
# which the grammar treats as ordinary name characters, not digits.
_DATETIME = re.compile(
    r"-?[0-9]{4,}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?"
)
_INT = re.compile(r"-?[0-9]+")
# [56]'s UCHAR exclusion is [#x00-#x20], not full Unicode whitespace: \s
# would reject non-breaking space (a legal IRI character) and admit other
# control characters that aren't spaces.
_IRI = re.compile(r"<([^<>\"{}|^`\\\x00-\x20]*)>")
_LANGTAG = re.compile(r"@([A-Za-z]+(?:-[A-Za-z0-9]+)*)")
_SHORT_STRING = re.compile(r'"((?:\\.|[^"\\\n])*)"')
_LONG_STRING = re.compile(r'"""((?:\\.|"(?!"")|[^"\\])*)"""', re.S)
_QNAME_LITERAL = re.compile(r"'((?:\\.|[^'\\\n])*)'")
# A '//' comment ends at CR or LF (the Recommendation's note on comments),
# not just LF.
_SKIP = re.compile(r"(?:\s+|//[^\n\r]*|/\*.*?\*/)+", re.S)
_LINEBREAK = re.compile(r"\r\n|\r|\n")
_ESCAPE_CHAR = re.compile(r"\\(.)", re.S)
_STRING_ESCAPES = {
    "t": "\t",
    "b": "\b",
    "n": "\n",
    "r": "\r",
    "f": "\f",
    '"': '"',
    "'": "'",
    "\\": "\\",
}

_PUNCTUATION = {
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    ",": TokenKind.COMMA,
    ";": TokenKind.SEMICOLON,
    "=": TokenKind.EQUALS,
}


# A locator maps an absolute offset in the source text to its (line, column).
_Locate = Callable[[int], tuple[int, int]]


def _unescape_string(raw: str, locate: _Locate, start: int) -> str:
    if "\\" not in raw:
        return raw

    def replace(match: re.Match[str]) -> str:
        char = match.group(1)
        if char not in _STRING_ESCAPES:
            line, column = locate(start + match.start())
            raise ProvNSyntaxError(f"unknown string escape '\\{char}'", line, column)
        return _STRING_ESCAPES[char]

    return _ESCAPE_CHAR.sub(replace, raw)


def _qname_value(match: re.Match[str]) -> tuple[str, str]:
    """Unescape a _QNAME/_QNAME_FULL match into its (prefix, local) value."""
    prefix, local, bare = match.groups()
    if prefix is not None:
        return prefix, _ESCAPE_CHAR.sub(r"\1", local or "")
    return "", _ESCAPE_CHAR.sub(r"\1", bare or "")


def _split_qname(raw: str, locate: _Locate, start: int) -> tuple[str, str]:
    match = _QNAME_FULL.match(raw)
    if match is None:
        partial = _QNAME.match(raw)
        line, column = locate(start + (partial.end() if partial else 0))
        raise ProvNSyntaxError(f"invalid qualified name '{raw}'", line, column)
    return _qname_value(match)


class _Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.line_start = 0
        self.previous: TokenKind | None = None

    @property
    def column(self) -> int:
        return self.pos - self.line_start + 1

    def _line_after(self, chunk: str) -> tuple[int, int]:
        """(line, line_start) reached by moving past ``chunk``, which starts
        at ``self.pos``; a CRLF pair counts as a single line break. Shared by
        ``advance`` (moving the lexer itself) and ``locate`` (a read-only
        look-ahead), so the newline arithmetic lives in one place."""
        count = 0
        last_end = 0
        for match in _LINEBREAK.finditer(chunk):
            count += 1
            last_end = match.end()
        if count:
            return self.line + count, self.pos + last_end
        return self.line, self.line_start

    def advance(self, length: int) -> None:
        chunk = self.text[self.pos : self.pos + length]
        self.line, self.line_start = self._line_after(chunk)
        self.pos += length

    def error(self, message: str) -> ProvNSyntaxError:
        return ProvNSyntaxError(message, self.line, self.column)

    def locate(self, offset: int) -> tuple[int, int]:
        """Line and column of the absolute ``offset``, which must be at or
        after ``self.pos``; used to report errors inside a literal's body
        rather than at the literal's opening delimiter."""
        line, line_start = self._line_after(self.text[self.pos : offset])
        return line, offset - line_start + 1

    def emit(self, kind: TokenKind, text: str, value: Any) -> Token:
        token = Token(kind, text, value, self.line, self.column)
        self.advance(len(text))
        self.previous = kind
        return token

    def tokens(self) -> Iterator[Token]:
        text = self.text
        while True:
            skip = _SKIP.match(text, self.pos)
            if skip:
                self.advance(skip.end() - self.pos)
            if text.startswith("/*", self.pos):
                raise self.error("unterminated comment")
            if self.pos >= len(text):
                yield Token(TokenKind.EOF, "", None, self.line, self.column)
                return
            yield self.next_token()

    def next_token(self) -> Token:
        text, pos = self.text, self.pos
        char = text[pos]
        if char in _PUNCTUATION:
            return self.emit(_PUNCTUATION[char], char, char)
        if char == "<":
            return self.iri_token()
        if char == '"':
            return self.string_token()
        if char == "'":
            return self.qname_literal_token()
        if char == "@" and self.previous is TokenKind.STRING:
            return self.langtag_token()
        if text.startswith("%%", pos):
            return self.emit(TokenKind.TYPED, "%%", "%%")
        token = self.literal_or_name_token()
        if token is not None:
            return token
        if char == "-":
            return self.emit(TokenKind.MARKER, "-", "-")
        raise self.error(f"unexpected character {char!r}")

    def iri_token(self) -> Token:
        match = _IRI.match(self.text, self.pos)
        if match is None:
            raise self.error("unterminated IRI")
        return self.emit(TokenKind.IRI, match.group(0), match.group(1))

    def qname_literal_token(self) -> Token:
        match = _QNAME_LITERAL.match(self.text, self.pos)
        if match is None:
            raise self.error("unterminated qualified name literal")
        value = _split_qname(match.group(1), self.locate, match.start(1))
        return self.emit(TokenKind.QNAME_LITERAL, match.group(0), value)

    def langtag_token(self) -> Token:
        match = _LANGTAG.match(self.text, self.pos)
        if match is None:
            raise self.error("invalid language tag")
        return self.emit(TokenKind.LANGTAG, match.group(0), match.group(1))

    def literal_or_name_token(self) -> Token | None:
        text, pos = self.text, self.pos
        datetime_match = _DATETIME.match(text, pos)
        if datetime_match:
            raw = datetime_match.group(0)
            return self.emit(TokenKind.DATETIME, raw, raw)
        int_match = _INT.match(text, pos)
        name_match = _QNAME.match(text, pos)
        # Longer match wins; on a tie, the integer reading wins.
        if int_match and (name_match is None or name_match.end() <= int_match.end()):
            raw = int_match.group(0)
            return self.emit(TokenKind.INT, raw, self._int_value(raw))
        if name_match:
            return self.name_token(name_match)
        return None

    def _int_value(self, raw: str) -> int:
        try:
            return int(raw)
        except ValueError as exc:
            limit = sys.get_int_max_str_digits()
            raise self.error(f"integer literal has more than {limit} digits") from exc

    def name_token(self, match: re.Match[str]) -> Token:
        # _PN_LOCAL already excludes a bare trailing '.' ([54]), so the
        # match never needs trimming here.
        raw = match.group(0)
        token = self.emit(TokenKind.NAME, raw, _qname_value(match))
        if self.pos < len(self.text) and self.text[self.pos] == ":":
            raise self.error("unexpected ':' inside a qualified name")
        return token

    def string_token(self) -> Token:
        text, pos = self.text, self.pos
        if text.startswith('"""', pos):
            match = _LONG_STRING.match(text, pos)
            if match is None:
                raise self.error("unterminated long string")
        else:
            match = _SHORT_STRING.match(text, pos)
            if match is None:
                raise self.error("unterminated string")
        value = _unescape_string(match.group(1), self.locate, match.start(1))
        return self.emit(TokenKind.STRING, match.group(0), value)


def tokenize(text: str) -> Iterator[Token]:
    """Yield the tokens of ``text``, ending with an ``EOF`` token.

    Raises:
        ProvNSyntaxError: On the first character that starts no valid token,
            with the line and column of that character.
    """
    return _Lexer(text).tokens()

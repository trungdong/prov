"""Pygments lexer for PROV-N (https://www.w3.org/TR/prov-n/).

``ProvNLexer`` is registered under the ``pygments.lexers`` entry point as ``provn``, so
Pygments finds it by name (``get_lexer_by_name("provn")``) once ``prov`` is installed. It
follows ``prov.serializers.provn_lexer``, so it emits no ``Error`` token on text the
PROV-N reader accepts, and it lexes any other text without failing.

The module imports Pygments and nothing from ``prov``, so it can be submitted to Pygments
with the import guard removed. It carries its own copies of the name character classes
and the keyword list, and ``test_pygments.py`` pins each copy to its source.
"""

import re
from typing import Any

try:
    from pygments.lexer import RegexLexer, bygroups, default, include, words
    from pygments.token import (
        Comment,
        Keyword,
        Literal,
        Name,
        Number,
        Operator,
        Punctuation,
        String,
        Whitespace,
    )
except ImportError as e:  # pragma: no cover -- Pygments (pygments extra) absent; the no-Pygments subprocess test covers it
    raise ModuleNotFoundError(
        'prov.pygments requires the optional "pygments" extra; '
        'install "prov[pygments]" to use the PROV-N lexer'
    ) from e

__all__ = ["ProvNLexer"]

# Copies of prov.identifier's name tables, written out in full.
_NCNAME_START_CHARS = (
    "\x41-\x5a"  # NameStartChar: [A-Z]
    "\x5f"  # NameStartChar: "_"
    "\x61-\x7a"  # NameStartChar: [a-z]
    "\xc0-\xd6"  # NameStartChar: [#xC0-#xD6]
    "\xd8-\xf6"  # NameStartChar: [#xD8-#xF6]
    "\xf8-\u02ff"  # NameStartChar: [#xF8-#x2FF]
    "\u0370-\u037d"  # NameStartChar: [#x370-#x37D]
    "\u037f-\u1fff"  # NameStartChar: [#x37F-#x1FFF]
    "\u200c-\u200d"  # NameStartChar: [#x200C-#x200D]
    "\u2070-\u218f"  # NameStartChar: [#x2070-#x218F]
    "\u2c00-\u2fef"  # NameStartChar: [#x2C00-#x2FEF]
    "\u3001-\ud7ff"  # NameStartChar: [#x3001-#xD7FF]
    "\uf900-\ufdcf"  # NameStartChar: [#xF900-#xFDCF]
    "\ufdf0-\ufffd"  # NameStartChar: [#xFDF0-#xFFFD]
    "\U00010000-\U000effff"  # NameStartChar: [#x10000-#xEFFFF]
)
_PN_CHARS = (
    "\x41-\x5a"  # NameStartChar: [A-Z]
    "\x5f"  # NameStartChar: "_"
    "\x61-\x7a"  # NameStartChar: [a-z]
    "\xc0-\xd6"  # NameStartChar: [#xC0-#xD6]
    "\xd8-\xf6"  # NameStartChar: [#xD8-#xF6]
    "\xf8-\u02ff"  # NameStartChar: [#xF8-#x2FF]
    "\u0370-\u037d"  # NameStartChar: [#x370-#x37D]
    "\u037f-\u1fff"  # NameStartChar: [#x37F-#x1FFF]
    "\u200c-\u200d"  # NameStartChar: [#x200C-#x200D]
    "\u2070-\u218f"  # NameStartChar: [#x2070-#x218F]
    "\u2c00-\u2fef"  # NameStartChar: [#x2C00-#x2FEF]
    "\u3001-\ud7ff"  # NameStartChar: [#x3001-#xD7FF]
    "\uf900-\ufdcf"  # NameStartChar: [#xF900-#xFDCF]
    "\ufdf0-\ufffd"  # NameStartChar: [#xFDF0-#xFFFD]
    "\U00010000-\U000effff"  # NameStartChar: [#x10000-#xEFFFF]
    "\\-"  # NameChar: "-" (escaped: literal, not a range operator)
    "\x30-\x39"  # NameChar: [0-9]
    "\xb7"  # NameChar: #xB7
    "\u0300-\u036f"  # NameChar: [#x0300-#x036F]
    "\u203f-\u2040"  # NameChar: [#x203F-#x2040]
)
_PN_CHARS_ESC = "='(),:;[]" + "-."
_PN_CHARS_OTHER = "/@~&+*?#$!"
# A bracketed regex fragment; the four strings above are class bodies.
_PN_PREFIX = (
    rf"[{_NCNAME_START_CHARS.replace('_', '')}](?:[{_PN_CHARS}.]*[{_PN_CHARS}])?"
)

# Copies of the two patterns prov.model._values shares with the tokenizer.
LANGTAG_PATTERN = r"[A-Za-z]+(?:-[A-Za-z0-9]+)*"
XSD_DATETIME_PATTERN = (
    r"-?[0-9]{4,}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?"
)

# The 17 statement names and the bare mentionOf, keywords before "(".
_EXPRESSIONS = (
    "entity",
    "activity",
    "agent",
    "wasGeneratedBy",
    "used",
    "wasInvalidatedBy",
    "wasStartedBy",
    "wasEndedBy",
    "wasInformedBy",
    "wasAttributedTo",
    "wasAssociatedWith",
    "actedOnBehalfOf",
    "wasDerivedFrom",
    "wasInfluencedBy",
    "alternateOf",
    "specializationOf",
    "hadMember",
    "mentionOf",
)
_STRUCTURAL = ("document", "endDocument", "bundle", "endBundle")

_OTHERS = re.escape(_PN_CHARS_OTHER)
_PERCENT = r"%[0-9A-Fa-f]{2}"
_ESC = rf"\\[{re.escape(_PN_CHARS_ESC)}]"
_LOCAL_START = rf"[{_NCNAME_START_CHARS}0-9{_OTHERS}]|{_PERCENT}|{_ESC}"
_LOCAL_CONT = rf"[{_PN_CHARS}.{_OTHERS}]|{_PERCENT}|{_ESC}"
_LOCAL_LAST = rf"[{_PN_CHARS}{_OTHERS}]|{_PERCENT}|{_ESC}"
_LOCAL = rf"(?:{_LOCAL_START})(?:(?:{_LOCAL_CONT})*(?:{_LOCAL_LAST}))?"

_LINE_COMMENT = r"//[^\n\r]*"
_BLOCK_COMMENT = r"/\*(?:[^*]|\*(?!/))*\*/"

# Lookaheads. A name ends where no further local-part character can follow, and a bare
# word is not a prefix when a colon follows. Trivia is whitespace and comments; each
# alternative has one way to match, so a failed lookahead backtracks in linear time.
_NAME_END = rf"(?!{_LOCAL_LAST}|\.+(?:{_LOCAL_LAST}))"
_WORD_END = _NAME_END + "(?!:)"
_TRIVIA = rf"(?:[ \t\r\n]|{_LINE_COMMENT}(?![^\n\r])|{_BLOCK_COMMENT})*"
_BEFORE_PAREN = rf"(?={_TRIVIA}\()"
_BEFORE_EQUALS = rf"(?={_TRIVIA}=)"

_PREFIXED = rf"({_PN_PREFIX})(:)({_LOCAL})?"
_BARE = rf"({_LOCAL})"
_IRI_OPEN = r'<(?:[^<>"{}|^`\\\x00-\x20]|\\[^\x00-\x20])*'
_IRI = _IRI_OPEN + ">"


def _groups(*args: Any) -> Any:
    return bygroups(*args)  # type: ignore[no-untyped-call]


class ProvNLexer(RegexLexer):
    """Lexer for PROV-N."""

    name = "PROV-N"
    aliases = ["provn", "prov-n"]
    filenames = ["*.provn"]
    mimetypes = ["text/provenance-notation"]
    url = "https://www.w3.org/TR/prov-n/"

    tokens = {
        # Outside brackets: the six structural words and the declarations.
        "root": [
            (rf"bundle{_WORD_END}", Keyword, "bundle_name"),
            # "bundle" is caught above; it stays in the list so the list is _STRUCTURAL.
            (words(_STRUCTURAL, suffix=_WORD_END), Keyword),
            (rf"prefix{_WORD_END}", Keyword.Declaration, "prefix_name"),
            (rf"default{_WORD_END}", Keyword.Declaration),
            include("common"),
        ],
        # Inside ( ), { } and [ ]; every opener pushes it and every closer pops it.
        "bracket": [include("common")],
        "trivia": [
            (r"[ \t\r\n]+", Whitespace),
            (_LINE_COMMENT, Comment.Single),
            (_BLOCK_COMMENT, Comment.Multiline),
            # An unterminated comment runs to the end of the text.
            (r"/\*[\s\S]*", Comment.Multiline),
        ],
        "common": [
            include("trivia"),
            (XSD_DATETIME_PATTERN, Literal.Date),
            (r'"""(?:\\(?s:.)|"(?!"")|[^"\\])*"""', String.Double, "string_tail"),
            # An unterminated string, quoted name or IRI runs to the end of its line
            # (a long string, to the end of the text), so a bad file lexes in linear time.
            (r'"""[\s\S]*', String.Double),
            (r'"(?:\\.|[^"\\\n\r])*"', String.Double, "string_tail"),
            (r'"(?:\\.|[^"\\\n\r])*', String.Double),
            (r"'(?:\\.|[^'\\\n\r])*'", String.Single),
            (r"'(?:\\.|[^'\\\n\r])*", String.Single),
            (_IRI, String.Other),
            (_IRI_OPEN, String.Other),
            (r"%%", Operator, "datatype"),
            (
                words(_EXPRESSIONS, suffix=_NAME_END + _BEFORE_PAREN),
                Keyword,
            ),
            (
                rf"(prov)(:)(mentionOf){_NAME_END}{_BEFORE_PAREN}",
                _groups(Name.Namespace, Punctuation, Keyword),
            ),
            (
                _PREFIXED + _NAME_END + _BEFORE_PAREN,
                _groups(Name.Namespace, Punctuation, Name.Function),
            ),
            (_BARE + _NAME_END + _BEFORE_PAREN, Name.Function),
            (
                _PREFIXED + _NAME_END + _BEFORE_EQUALS,
                _groups(Name.Namespace, Punctuation, Name.Attribute),
            ),
            (_BARE + _NAME_END + _BEFORE_EQUALS, Name.Attribute),
            (r"-[0-9]+", Number.Integer),
            (rf"[0-9]+{_NAME_END}", Number.Integer),
            (_PREFIXED, _groups(Name.Namespace, Punctuation, Name)),
            (_BARE, Name),
            (r"-", Keyword.Constant),
            (r"[(\[{]", Punctuation, "bracket"),
            (r"[)\]}]", Punctuation, "#pop"),
            (r"[,;=]", Punctuation),
        ],
        # The name after "bundle" is a name, whatever it spells.
        "bundle_name": [
            include("trivia"),
            (_PREFIXED, _groups(Name.Namespace, Punctuation, Name), "#pop"),
            (_BARE, Name, "#pop"),
            default("#pop"),
        ],
        "prefix_name": [
            include("trivia"),
            (_PN_PREFIX, Name.Namespace, "#pop"),
            default("#pop"),
        ],
        # A language tag follows a string, with trivia allowed between them.
        "string_tail": [
            include("trivia"),
            (rf"@{LANGTAG_PATTERN}", Name.Decorator, "#pop"),
            default("#pop"),
        ],
        "datatype": [
            include("trivia"),
            (
                _PREFIXED,
                _groups(Name.Namespace, Punctuation, Keyword.Type),
                "#pop",
            ),
            (_BARE, Keyword.Type, "#pop"),
            default("#pop"),
        ],
    }

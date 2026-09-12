from __future__ import annotations  # defer eval: Namespace used before it's defined

import re
from typing import Any, Final

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

# Character classes for the XML 1.0 5th-edition Name productions, minus ':'
# (NCName). Shared by prov.serializers.provxml (PROV-XML element-tag
# legality, #289) and prov.serializers.provn_lexer, whose PN_CHARS_BASE/
# PN_CHARS_U/PN_CHARS ([53]-[55]) are these same ranges, bar '.', which
# PROV-N's grammar handles positionally rather than as an ordinary name char.
#
# Every range boundary is spelled as a \xHH/\uHHHH/\UHHHHHHHH escape (never
# a literal glyph) and annotated with the spec clause it implements, so a
# mangled/look-alike codepoint is visible on inspection rather than hiding
# in the source as an indistinguishable glyph.
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
_NCNAME_CHARS = _NCNAME_START_CHARS + (
    "\\-"  # NameChar: "-" (escaped: literal, not a range operator)
    "\x2e"  # NameChar: "."
    "\x30-\x39"  # NameChar: [0-9]
    "\xb7"  # NameChar: #xB7
    "\u0300-\u036f"  # NameChar: [#x0300-#x036F]
    "\u203f-\u2040"  # NameChar: [#x203F-#x2040]
)

# PROV-N metacharacters that must be backslash-escaped anywhere in the local
# part of a qualified name (grammar production [55] PN_CHARS_ESC, #223).
_PROVN_LOCAL_METACHARS = "='(),:;[]"
# PN_CHARS_ESC also lists '-' and '.' as escapable, but PN_LOCAL ([53]) only
# forbids a *bare* '-' or '.' as the first character, and a bare '.' as the
# last character; elsewhere both are ordinary PN_CHARS and stay unescaped.
_PROVN_LOCAL_LEADING_ESCAPE = "-."
# PN_LOCAL's own character class ([53]), the shared NCName table minus '.'
# (see the comment on _NCNAME_CHARS above).
_PN_CHARS = _NCNAME_CHARS.replace(".", "")
# The remaining characters PN_LOCAL allows unescaped ([54]'s PLX minus '%').
_PN_CHARS_OTHER = "/@~&+*?#$!"
_PROVN_HEX_PAIR = re.compile(r"[0-9A-Fa-f]{2}")
# Everything PN_LOCAL can spell as-is or via a backslash escape: PN_CHARS,
# PN_CHARS_OTHER, the backslash-escaped metacharacters, and '-'/'.' (whose
# escaping is positional, decided in the loop below). Any character outside
# this set cannot be written at all, even escaped, so it is percent-encoded
# ([54]'s PERCENT) as its UTF-8 bytes instead -- valid PROV-N, but read back
# as the literal text "%XX" rather than the original character, a
# documented, deliberate exclusion (see strategies.py's local_part comment).
_PROVN_LOCAL_ALLOWED_UNESCAPED = _PN_CHARS + re.escape(
    _PN_CHARS_OTHER + _PROVN_LOCAL_METACHARS + _PROVN_LOCAL_LEADING_ESCAPE
)
_PROVN_LOCAL_NEEDS_PERCENT_ENCODING = re.compile(f"[^{_PROVN_LOCAL_ALLOWED_UNESCAPED}]")
# Matches any character the escaping loop below treats specially, anywhere
# in the local part; a local part matching none of these needs no escaping
# at all, including the leading/trailing '-'/'.' rule and percent-encoding.
_PROVN_LOCAL_NEEDS_ESCAPE = re.compile(
    "["
    + re.escape(_PROVN_LOCAL_METACHARS + _PROVN_LOCAL_LEADING_ESCAPE + "%")
    + "]"
    + f"|{_PROVN_LOCAL_NEEDS_PERCENT_ENCODING.pattern}"
)


def _provn_escape_local(localpart: str) -> str:
    """Return ``localpart`` escaped for use in a PROV-N ``PN_LOCAL`` position."""
    if not _PROVN_LOCAL_NEEDS_ESCAPE.search(localpart):
        return localpart
    last_index = len(localpart) - 1
    parts = []
    for i, char in enumerate(localpart):
        if char == "%":
            # An existing valid escape (e.g. "%20") is kept verbatim; a bare
            # '%' not followed by two hex digits is not, so it is escaped
            # itself to keep the sequence unambiguous.
            parts.append(char if _PROVN_HEX_PAIR.match(localpart, i + 1) else "%25")
        elif (
            (i == 0 and char in _PROVN_LOCAL_LEADING_ESCAPE)
            or (i == last_index and char == ".")
            or char in _PROVN_LOCAL_METACHARS
        ):
            parts.append(f"\\{char}")
        elif _PROVN_LOCAL_NEEDS_PERCENT_ENCODING.match(char):
            parts.extend(f"%{byte:02X}" for byte in char.encode("utf-8"))
        else:
            parts.append(char)
    return "".join(parts)


class Identifier:
    """Base class for all identifiers and also represents xsd:anyURI."""

    # TODO: make Identifier an "abstract" base class and move xsd:anyURI
    # into a subclass

    __slots__ = ("__weakref__", "_hash", "_uri")

    # This field is assign-once. The hash is computed from it at construction,
    # and a later reassignment would leave the cached hash stale. #444 tracks
    # the runtime guard.
    _uri: Final[str]

    def __init__(self, uri: str):
        """Create an identifier for the given URI.

        Args:
            uri: URI string for the identifier. Converted to ``str`` if not
                already one.
        """
        self._uri = str(uri)  # Ensure this is a unicode string
        self._hash = self._compute_hash()

    def _compute_hash(self) -> int:
        """Hash by URI alone, so equal identifiers hash equal whatever their
        concrete class: ``__eq__`` compares URIs across Identifier subclasses."""
        return hash(self._uri)

    def __getstate__(self) -> dict[str, Any]:
        """Pickle state: every slot except the process-specific ``_hash``,
        which :meth:`__setstate__` recomputes in the loading process."""
        return {"_uri": self._uri}

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Also accepts the __dict__ state of pickles written before 3.2.0.
        object.__setattr__(self, "_uri", state["_uri"])
        object.__setattr__(self, "_hash", self._compute_hash())

    @property
    def uri(self) -> str:
        """The URI associated with the current identifier."""
        return self._uri

    def __str__(self) -> str:
        return self._uri

    def __eq__(self, other: Any) -> bool:
        return self.uri == other.uri if isinstance(other, Identifier) else False

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._uri}>"

    def provn_representation(self) -> str:
        """Return the PROV-N representation of this identifier as an xsd:anyURI literal."""
        return f'"{self._uri}" %% xsd:anyURI'


class QualifiedName(Identifier):
    """
    Represents a `qualified name <https://www.w3.org/TR/prov-dm/#concept-qualifiedName>`_,
    which combines a namespace and a local part for use in identifying entities in a
    namespace-aware context.

    This class facilitates handling and manipulation of qualified names, which
    combine a namespace and a local identifier. It supports string representation,
    hashing, and retrieval of individual components (namespace or local part).
    """

    __slots__ = ("_localpart", "_namespace", "_str")

    # These fields are assign-once. The hash is computed from them at
    # construction, and a later reassignment would leave the cached hash
    # stale. #444 tracks the runtime guard.
    _namespace: Final[Namespace]
    _localpart: Final[str]
    _str: Final[str]

    def __init__(self, namespace: Namespace, localpart: str):
        """
        Initializes a new qualified name with the provided namespace and localpart
        values. It combines the namespace URI and localpart to form an identifier and
        constructs a string representation including optional namespace prefix.

        Args:
            namespace (Namespace): The namespace object containing a URI and optional
                prefix associated with this qualified name.
            localpart (str): The local part of the qualified name.
        """
        Identifier.__init__(self, "".join([namespace.uri, localpart]))
        self._namespace = namespace
        self._localpart = localpart
        self._str = (
            ":".join([namespace.prefix, localpart]) if namespace.prefix else localpart
        )

    def _compute_hash(self) -> int:
        """Hash by URI alone, as the base class does; kept explicit because
        the string form is cached separately."""
        return hash(self._uri)

    def __getstate__(self) -> dict[str, Any]:
        return {
            "_uri": self._uri,
            "_namespace": self._namespace,
            "_localpart": self._localpart,
            "_str": self._str,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        object.__setattr__(self, "_namespace", state["_namespace"])
        object.__setattr__(self, "_localpart", state["_localpart"])
        object.__setattr__(self, "_str", state["_str"])
        Identifier.__setstate__(self, state)

    @property
    def namespace(self) -> Namespace:
        """Namespace of qualified name."""
        return self._namespace

    @property
    def localpart(self) -> str:
        """Local part of qualified name."""
        return self._localpart

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._str}>"

    def provn_bare_representation(self) -> str:
        """Return the ``prefix:local`` PROV-N form used at IDENTIFIER positions.

        The local part's PROV-N metacharacters (``= ' ( ) , : ; [ ]``) are
        backslash-escaped per grammar production [55] ``PN_CHARS_ESC`` (#223),
        as are a leading ``-``/``.`` and a trailing ``.`` (forbidden bare by
        [53]/[54]); characters PN_LOCAL cannot express at all are
        percent-encoded. The prefix is never escaped, as it cannot contain
        these characters.
        """
        escaped_localpart = _provn_escape_local(self._localpart)
        return (
            ":".join([self._namespace.prefix, escaped_localpart])
            if self._namespace.prefix
            else escaped_localpart
        )

    def provn_representation(self) -> str:
        """Return the PROV-N representation of this qualified name as a quoted string."""
        return f"'{self.provn_bare_representation()}'"


class Namespace:
    """PROV Namespace."""

    __slots__ = ("__weakref__", "_cache", "_prefix", "_uri")

    # These fields are assign-once. They take part in equality and hashing,
    # so reassigning one after the object has been used as a set member or
    # dict key corrupts that container. #444 tracks the runtime guard.
    _prefix: Final[str]
    _uri: Final[str]

    def __init__(self, prefix: str, uri: str):
        """Create a namespace with the given prefix and URI.

        Args:
            prefix: Short-hand prefix for the namespace.
            uri: URI string for the namespace (cannot be blank).

        Raises:
            ValueError: If ``uri`` is empty or contains only whitespace.
        """
        if not uri or uri.isspace():
            raise ValueError("Not a valid URI to create a namespace.")
        self._prefix = prefix
        self._uri = uri
        self._cache: dict[str, QualifiedName] = {}

    @property
    def uri(self) -> str:
        """Namespace URI."""
        return self._uri

    @property
    def prefix(self) -> str:
        """Namespace prefix."""
        return self._prefix

    def contains(self, identifier: Identifier) -> bool:
        """Check whether the given identifier's URI is contained in this namespace.

        Args:
            identifier: Identifier (or URI string) to check.

        Returns:
            ``True`` if the identifier's URI starts with this namespace's URI,
            ``False`` otherwise (including when the URI cannot be determined).
        """
        uri = (
            identifier
            if isinstance(identifier, str)
            else (identifier.uri if isinstance(identifier, Identifier) else None)
        )
        return uri.startswith(self._uri) if uri else False

    def qname(self, identifier: str | Identifier) -> QualifiedName | None:
        """Resolve an identifier to a :class:`QualifiedName` in this namespace.

        Args:
            identifier: Identifier (or URI string) to resolve.

        Returns:
            A new :class:`QualifiedName` in this namespace if ``identifier``'s
            URI starts with this namespace's URI, otherwise ``None``.
        """
        uri = (
            identifier
            if isinstance(identifier, str)
            else (identifier.uri if isinstance(identifier, Identifier) else None)
        )
        if uri and uri.startswith(self._uri):
            return QualifiedName(self, uri[len(self._uri) :])
        else:
            return None

    def __eq__(self, other: Any) -> bool:
        return (
            (self._uri == other.uri and self._prefix == other.prefix)
            if isinstance(other, Namespace)
            else False
        )

    def __ne__(self, other: Any) -> bool:
        return (
            not isinstance(other, Namespace)
            or self._uri != other.uri
            or self._prefix != other.prefix
        )

    def __hash__(self) -> int:
        return hash((self._uri, self._prefix))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._prefix} {{{self._uri}}}>"

    def __getstate__(self) -> dict[str, Any]:
        """Pickle state without the interning cache, which is rebuilt lazily."""
        return {"_prefix": self._prefix, "_uri": self._uri}

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Also accepts the __dict__ state of pickles written before 3.2.0,
        # which carries the cache; it is discarded.
        object.__setattr__(self, "_prefix", state["_prefix"])
        object.__setattr__(self, "_uri", state["_uri"])
        object.__setattr__(self, "_cache", {})

    def __getitem__(self, localpart: str) -> QualifiedName:
        if localpart in self._cache:
            return self._cache[localpart]
        else:
            qname = QualifiedName(self, localpart)
            self._cache[localpart] = qname
            return qname

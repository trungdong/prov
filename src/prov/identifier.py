from __future__ import annotations  # defer eval: Namespace used before it's defined

import re
from typing import Any, Final

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

# PROV-N metacharacters that must be backslash-escaped anywhere in the local
# part of a qualified name (grammar production [55] PN_CHARS_ESC, #223).
_PROVN_LOCAL_METACHARS = "='(),:;[]"
# PN_CHARS_ESC also lists '-' and '.' as escapable, but PN_LOCAL ([53]) only
# forbids a *bare* '-' or '.' as the first character, and a bare '.' as the
# last character; elsewhere both are ordinary PN_CHARS and stay unescaped.
_PROVN_LOCAL_LEADING_ESCAPE = "-."
# Characters PN_LOCAL cannot express at all, even escaped, are percent-encoded
# ([54]'s PERCENT), which is valid PROV-N. The lexer keeps percent-encoding
# verbatim, so this reads back as the literal text "%XX" rather than the
# original character, a documented, deliberate exclusion (see
# strategies.py's local_part comment).
_PROVN_LOCAL_PERCENT_ENCODE = ' <>"{}|^`\\'
_PROVN_HEX_PAIR = re.compile(r"[0-9A-Fa-f]{2}")
# Matches any character the escaping loop below treats specially, anywhere
# in the local part. A bare '%' is included too, since it may need
# %25-encoding, which the loop's hex-pair check decides. A local part
# matching none of these needs no escaping at all, including the
# leading/trailing '-'/'.' rule, since both characters are in this class.
_PROVN_LOCAL_NEEDS_ESCAPE = re.compile(
    "["
    + re.escape(
        _PROVN_LOCAL_METACHARS
        + _PROVN_LOCAL_LEADING_ESCAPE
        + _PROVN_LOCAL_PERCENT_ENCODE
        + "%"
    )
    + "]"
)


def _provn_escape_local(localpart: str) -> str:
    """Return ``localpart`` escaped for use in a PROV-N ``PN_LOCAL`` position."""
    if not _PROVN_LOCAL_NEEDS_ESCAPE.search(localpart):
        return localpart
    last_index = len(localpart) - 1
    parts = []
    for i, char in enumerate(localpart):
        if char in _PROVN_LOCAL_PERCENT_ENCODE:
            parts.append(f"%{ord(char):02X}")
        elif char == "%" and not _PROVN_HEX_PAIR.match(localpart, i + 1):
            parts.append("%25")
        elif (
            (i == 0 and char in _PROVN_LOCAL_LEADING_ESCAPE)
            or (i == last_index and char == ".")
            or char in _PROVN_LOCAL_METACHARS
        ):
            parts.append(f"\\{char}")
        else:
            parts.append(char)
    return "".join(parts)


class Identifier:
    """Base class for all identifiers and also represents xsd:anyURI."""

    # TODO: make Identifier an "abstract" base class and move xsd:anyURI
    # into a subclass

    __slots__ = ("_hash", "_uri")

    # Assign-once: the hash is derived from this field at construction, so a
    # later reassignment would desynchronise it. #444 tracks a runtime guard.
    _uri: Final[str]

    def __init__(self, uri: str):
        """Create an identifier for the given URI.

        Args:
            uri: URI string for the identifier. Converted to ``str`` if not
                already one.
        """
        self._uri = str(uri)  # Ensure this is a unicode string
        self._hash = hash((self._uri, self.__class__))

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

    # Assign-once: the hash is derived from these fields at construction, so a
    # later reassignment would desynchronise it. #444 tracks a runtime guard.
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
        self._hash = hash(self._uri)

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

    def __hash__(self) -> int:
        return self._hash

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

    __slots__ = ("_cache", "_prefix", "_uri")

    # Assign-once: the hash is derived from these fields at construction, so a
    # later reassignment would desynchronise it. #444 tracks a runtime guard.
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

    def __getitem__(self, localpart: str) -> QualifiedName:
        if localpart in self._cache:
            return self._cache[localpart]
        else:
            qname = QualifiedName(self, localpart)
            self._cache[localpart] = qname
            return qname

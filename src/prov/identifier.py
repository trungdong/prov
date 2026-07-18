from __future__ import annotations  # defer eval: Namespace used before it's defined

from typing import Any

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


class Identifier:
    """Base class for all identifiers and also represents xsd:anyURI."""

    # TODO: make Identifier an "abstract" base class and move xsd:anyURI
    # into a subclass

    def __init__(self, uri: str):
        """Create an identifier for the given URI.

        Args:
            uri: URI string for the identifier. Converted to ``str`` if not
                already one.
        """
        self._uri: str = str(uri)  # Ensure this is a unicode string

    @property
    def uri(self) -> str:
        """The URI associated with the current identifier."""
        return self._uri

    def __str__(self) -> str:
        return self._uri

    def __eq__(self, other: Any) -> bool:
        return self.uri == other.uri if isinstance(other, Identifier) else False

    def __hash__(self) -> int:
        return hash((self.uri, self.__class__))

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
        return hash(self.uri)

    def provn_representation(self) -> str:
        """Return the PROV-N representation of this qualified name as a quoted string."""
        return f"'{self._str}'"


class Namespace:
    """PROV Namespace."""

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

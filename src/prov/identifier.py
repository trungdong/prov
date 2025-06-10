from __future__ import annotations  # needed for | type annotations in Python < 3.10
from typing import Any

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


class Identifier(object):
    """Base class for all identifiers and also represents xsd:anyURI."""

    # TODO: make Identifier an "abstract" base class and move xsd:anyURI
    # into a subclass

    def __init__(self, uri: str):
        """
        Constructor.

        :param uri: URI string for the long namespace identifier.
        """
        self._uri: str = str(uri)  # Ensure this is a unicode string

    @property
    def uri(self) -> str:
        """
        Returns the URI associated with the current identifier.

        Returns:
            str: The URI representing the resource identifier.
        """
        return self._uri

    def __str__(self) -> str:
        return self._uri

    def __eq__(self, other: Any) -> bool:
        return self.uri == other.uri if isinstance(other, Identifier) else False

    def __hash__(self) -> int:
        return hash((self.uri, self.__class__))

    def __repr__(self) -> str:
        return "<%s: %s>" % (self.__class__.__name__, self._uri)

    def provn_representation(self) -> str:
        """
        Returns the PROV-N representation of the URI.

        Returns:
            str: The PROV-N representation of the URI.
        """
        return '"%s" %%%% xsd:anyURI' % self._uri


class QualifiedName(Identifier):
    """
    Represents a `qualified name <https://www.w3.org/TR/prov-dm/#concept-qualifiedName>`_,
    which combines a namespace and a local part for use in identifying entities in a
    namespace-aware context.

    This class facilitates handling and manipulation of qualified names, which
    combine a namespace and a local identifier. It supports string representation,
    hashing, and retrieval of individual components (namespace or local part).
    """

    def __init__(self, namespace: "Namespace", localpart: str):
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
    def namespace(self) -> "Namespace":
        """Namespace of qualified name."""
        return self._namespace

    @property
    def localpart(self) -> str:
        """Local part of qualified name."""
        return self._localpart

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return "<%s: %s>" % (self.__class__.__name__, self._str)

    def __hash__(self) -> int:
        return hash(self.uri)

    def provn_representation(self) -> str:
        """PROV-N representation of qualified name in a string."""
        return "'%s'" % self._str


class Namespace(object):
    """PROV Namespace."""

    def __init__(self, prefix: str, uri: str):
        """
        Constructor.

        :param prefix: String short hand prefix for the namespace.
        :param uri: URI string for the long namespace identifier (cannot be blank).
        """
        if not uri or uri.isspace():
            raise ValueError("Not a valid URI to create a namespace.")
        self._prefix = prefix
        self._uri = uri
        self._cache: dict[str, QualifiedName] = dict()

    @property
    def uri(self) -> str:
        """Namespace URI."""
        return self._uri

    @property
    def prefix(self) -> str:
        """Namespace prefix."""
        return self._prefix

    def contains(self, identifier: Identifier) -> bool:
        """
        Indicates whether the identifier provided is contained in this namespace.

        :param identifier: Identifier to check.
        :return: bool
        """
        uri = (
            identifier
            if isinstance(identifier, str)
            else (identifier.uri if isinstance(identifier, Identifier) else None)
        )
        return uri.startswith(self._uri) if uri else False

    def qname(self, identifier: str | Identifier) -> QualifiedName | None:
        """
        Returns the qualified name of the identifier given using the namespace
        prefix.

        :param identifier: Identifier to resolve to a qualified name.
        :return: :py:class:`QualifiedName`
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
        return "<%s: %s {%s}>" % (self.__class__.__name__, self._prefix, self._uri)

    def __getitem__(self, localpart: str) -> QualifiedName:
        if localpart in self._cache:
            return self._cache[localpart]
        else:
            qname = QualifiedName(self, localpart)
            self._cache[localpart] = qname
            return qname

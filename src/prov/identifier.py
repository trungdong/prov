__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


class Identifier(object):
    """Base class for all identifiers and also represents xsd:anyURI."""

    # TODO: make Identifier an "abstract" base class and move xsd:anyURI
    # into a subclass

    def __init__(self, uri):
        """
        Constructor.

        :param uri: URI string for the long namespace identifier.
        """
        self._uri = str(uri)  # Ensure this is a unicode string

    @property
    def uri(self):
        """Identifier's URI."""
        return self._uri

    def __str__(self):
        return self._uri

    def __eq__(self, other):
        return self.uri == other.uri if isinstance(other, Identifier) else False

    def __hash__(self):
        return hash((self.uri, self.__class__))

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self._uri)

    def provn_representation(self):
        """PROV-N representation of qualified name in a string."""
        return '"%s" %%%% xsd:anyURI' % self._uri


class QualifiedName(Identifier):
    """Qualified name of an identifier in a particular namespace."""

    def __init__(self, namespace, localpart):
        """
        Constructor.

        :param namespace: Namespace to use for qualified name resolution.
        :param localpart: Portion of identifier not part of the namespace prefix.
        """
        Identifier.__init__(self, "".join([namespace.uri, localpart]))
        self._namespace = namespace
        self._localpart = localpart
        self._str = (
            ":".join([namespace.prefix, localpart]) if namespace.prefix else localpart
        )

    @property
    def namespace(self):
        """Namespace of qualified name."""
        return self._namespace

    @property
    def localpart(self):
        """Local part of qualified name."""
        return self._localpart

    def __str__(self):
        return self._str

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self._str)

    def __hash__(self):
        return hash(self.uri)

    def provn_representation(self):
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
        self._cache = dict()

    @property
    def uri(self):
        """Namespace URI."""
        return self._uri

    @property
    def prefix(self):
        """Namespace prefix."""
        return self._prefix

    def contains(self, identifier):
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

    def qname(self, identifier):
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

    def __eq__(self, other):
        return (
            (self._uri == other.uri and self._prefix == other.prefix)
            if isinstance(other, Namespace)
            else False
        )

    def __ne__(self, other):
        return (
            not isinstance(other, Namespace)
            or self._uri != other.uri
            or self._prefix != other.prefix
        )

    def __hash__(self):
        return hash((self._uri, self._prefix))

    def __repr__(self):
        return "<%s: %s {%s}>" % (self.__class__.__name__, self._prefix, self._uri)

    def __getitem__(self, localpart):
        if localpart in self._cache:
            return self._cache[localpart]
        else:
            qname = QualifiedName(self, localpart)
            self._cache[localpart] = qname
            return qname

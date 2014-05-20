class Identifier(object):
    def __init__(self, uri):
        self._uri = unicode(uri)  # Ensure this is a unicode string

    @property
    def uri(self):
        return self._uri

    def __unicode__(self):
        return self._uri

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __eq__(self, other):
        return self.uri == other.uri if isinstance(other, Identifier) else False

    def __hash__(self):
        return hash(self.uri)

    def provn_representation(self):
        return u'"%s" %%%% xsd:anyURI' % self._uri


class QualifiedName(Identifier):
    def __init__(self, namespace, localpart):
        Identifier.__init__(self, u''.join([namespace.uri, localpart]))
        self._namespace = namespace
        self._localpart = localpart
        self._str = u':'.join([namespace.prefix, localpart]) if namespace.prefix else localpart

    @property
    def namespace(self):
        return self._namespace

    @property
    def localpart(self):
        return self._localpart

    def __unicode__(self):
        return self._str

    def __str__(self):
        return unicode(self).encode('utf-8')

    def provn_representation(self):
        return u"'%s'" % self._str


class XSDQName(QualifiedName):
    """
    A subclass to wrap around a QualifiedName for xsd:QName literals
    """
    def __init__(self, qualified_name):
        QualifiedName.__init__(self, qualified_name.namespace, qualified_name.localpart)

    def provn_representation(self):
        return u'"%s" %%%% xsd:QName' % self._str


class Namespace(object):
    def __init__(self, prefix, uri):
        self._prefix = prefix
        self._uri = uri
        self._cache = dict()

    @property
    def uri(self):
        return self._uri

    @property
    def prefix(self):
        return self._prefix

    def contains(self, identifier):
        uri = identifier if isinstance(identifier, (str, unicode)) else (
            identifier.uri if isinstance(identifier, Identifier) else None
        )
        return uri.startswith(self._uri) if uri else False

    def qname(self, identifier):
        uri = identifier if isinstance(identifier, (str, unicode)) else (
            identifier.uri if isinstance(identifier, Identifier) else None
        )
        if uri and uri.startswith(self._uri):
            return QualifiedName(self, uri[len(self._uri):])
        else:
            return None

    def __eq__(self, other):
        return (self._uri == other.uri and self._prefix == other.prefix) if isinstance(other, Namespace) else False

    def __hash__(self):
        return hash((self._uri, self._prefix))

    def __getitem__(self, localpart):
        if localpart in self._cache:
            return self._cache[localpart]
        else:
            qname = QualifiedName(self, localpart)
            self._cache[localpart] = qname
            return qname

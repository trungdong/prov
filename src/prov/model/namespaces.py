"""Namespace management for PROV documents and bundles."""

from __future__ import annotations  # defer eval: refs itself before class is defined

from collections.abc import Iterable

from prov.constants import PROV, XSD, XSI
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model.records import NSCollection, QualifiedNameCandidate

DEFAULT_NAMESPACES = {"prov": PROV, "xsd": XSD, "xsi": XSI}


class NamespaceManager(dict[str, Namespace]):
    """Manages namespaces for PROV documents and bundles."""

    parent = None  # type: NamespaceManager | None
    """Parent :class:`NamespaceManager` this manager is a child of, if any."""

    def __init__(
        self,
        namespaces: NSCollection | None = None,
        default: str | None = None,
        parent: NamespaceManager | None = None,
    ):
        """Initialise the namespace manager.

        Args:
            namespaces: Optional namespaces to add, as a ``{prefix: uri}`` dict
                or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
            default: Optional default namespace URI (default: ``None``).
            parent: Optional parent :class:`NamespaceManager` to make this one a
                child of (default: ``None``).
        """
        dict.__init__(self)
        self._default_namespaces = DEFAULT_NAMESPACES
        self.update(self._default_namespaces)
        self._namespaces = {}  # type: dict[str, Namespace]

        if default is not None:
            self.set_default_namespace(default)
        else:
            self._default = None  # type: Namespace | None
        self.parent = parent
        #  TODO check if default is in the default namespaces
        self._anon_id_count = 0
        self._uri_map = {}  # type: dict[str, Namespace]
        self._rename_map = {}  # type: dict[Namespace, Namespace]
        self._prefix_renamed_map = {}  # type: dict[str, Namespace]
        if namespaces is not None:
            self.add_namespaces(namespaces)

    def get_namespace(self, uri: str) -> Namespace | None:
        """Return the known namespace with the given URI.

        Args:
            uri: The namespace URI to look up.

        Returns:
            The matching :class:`~prov.identifier.Namespace`, or ``None`` if no
            known namespace has that URI.
        """
        for namespace in self.values():
            if uri == namespace._uri:
                return namespace
        return None

    def get_registered_namespaces(self) -> Iterable[Namespace]:
        """Return all explicitly registered namespaces.

        Returns:
            An iterable of :class:`~prov.identifier.Namespace`. This excludes
            the default namespaces (``prov``, ``xsd``, ``xsi``).
        """
        return self._namespaces.values()

    def set_default_namespace(self, uri: str) -> None:
        """Set the default namespace to one with the given URI.

        Args:
            uri: The URI of the default namespace.
        """
        self._default = Namespace("", uri)
        self[""] = self._default

    def get_default_namespace(self) -> Namespace | None:
        """Return the default namespace, or ``None`` if none is set."""
        return self._default

    def add_namespace(self, namespace: Namespace) -> Namespace:
        """Add a namespace, unless an equivalent one is already registered.

        If a namespace with the same URI already exists, that existing
        namespace is returned. If the prefix conflicts with a different
        namespace, the added namespace is renamed to an unused prefix.

        Args:
            namespace: The :class:`~prov.identifier.Namespace` to add.

        Returns:
            The registered namespace, which may be the existing or renamed one
            rather than the argument.
        """
        if namespace in self.values():
            #  no need to do anything
            return namespace
        if namespace in self._rename_map:
            #  already renamed and added
            return self._rename_map[namespace]

        # Checking if the URI has been defined and use the existing namespace
        # instead
        uri = namespace.uri
        prefix = namespace.prefix

        if uri in self._uri_map:
            existing_ns = self._uri_map[uri]
            self._rename_map[namespace] = existing_ns
            self._prefix_renamed_map[prefix] = existing_ns
            return existing_ns

        if prefix in self:
            #  Conflicting prefix
            new_prefix = self._get_unused_prefix(prefix)
            new_namespace = Namespace(new_prefix, namespace.uri)
            self._rename_map[namespace] = new_namespace
            # TODO: What if the prefix is already in the map and point to a
            # different Namespace? Raise an exception?
            self._prefix_renamed_map[prefix] = new_namespace
            prefix = new_prefix
            namespace = new_namespace

        # Only now add the namespace to the registry
        self._namespaces[prefix] = namespace
        self[prefix] = namespace
        self._uri_map[uri] = namespace

        return namespace

    def add_namespaces(self, namespaces: NSCollection) -> None:
        """Add multiple namespaces into this manager.

        Args:
            namespaces: The namespaces to add, as a ``{prefix: uri}`` dict or an
                iterable of :class:`~prov.identifier.Namespace`.
        """
        if isinstance(namespaces, dict):
            # expecting a dictionary of {prefix: uri},
            # convert it to a list of Namespace
            namespaces = [Namespace(prefix, uri) for prefix, uri in namespaces.items()]
        if namespaces:
            for ns in namespaces:
                self.add_namespace(ns)

    def valid_qualified_name(
        self, qname: QualifiedNameCandidate
    ) -> QualifiedName | None:
        """Resolve an identifier to a valid qualified name.

        Registers the namespace of the resolved name if it was not registered
        already. Where the identifier is a string or :class:`Identifier`, an
        attempt is made to expand a known prefix or compact a known namespace
        URI, delegating to the parent manager if all local attempts fail.

        Args:
            qname: The candidate to resolve, as a
                :class:`~prov.identifier.QualifiedName`,
                :class:`~prov.identifier.Identifier`, or string.

        Returns:
            The resolved :class:`~prov.identifier.QualifiedName`, or ``None`` if
            it could not be resolved.
        """
        if not qname:
            return None

        if isinstance(qname, QualifiedName):
            #  Register the namespace if it has not been registered before
            namespace = qname.namespace
            prefix = namespace.prefix
            local_part = qname.localpart
            if not prefix:
                # the namespace is a default namespace
                if self._default == namespace:
                    # the same default namespace is defined
                    new_qname = self._default[local_part]
                elif self._default is None:
                    # no default namespace is defined, reused the one given
                    self._default = namespace
                    return qname  # no change, return the original
                else:
                    # different default namespace,
                    # use the 'dn' prefix for the new namespace
                    dn_namespace = Namespace("dn", namespace.uri)
                    dn_namespace = self.add_namespace(dn_namespace)
                    new_qname = dn_namespace[local_part]
            elif prefix in self and self[prefix] == namespace:
                # No need to add the namespace
                existing_ns = self[prefix]
                if existing_ns is namespace:
                    return qname
                else:
                    # reuse the existing namespace
                    new_qname = existing_ns[local_part]
            else:
                # Do not reuse the namespace object, making an identical copy
                ns = self.add_namespace(Namespace(namespace.prefix, namespace.uri))
                # minting the same Qualified Name from the namespace's copy
                new_qname = ns[qname.localpart]
            # returning the new qname
            return new_qname

        # Trying to generate a valid qualified name from here
        if not isinstance(qname, (str, Identifier)):
            # Only proceed with a string or URI value
            return None
        # Extract the URI string value if it is an identifier
        str_value = qname.uri if isinstance(qname, Identifier) else qname
        if str_value.startswith("_:"):
            # this is a blank node ID
            return None
        elif ":" in str_value:
            #  check if the identifier contains a registered prefix
            prefix, local_part = str_value.split(":", 1)
            if prefix in self:
                #  return a new QualifiedName
                return self[prefix][local_part]
            if prefix in self._prefix_renamed_map:
                #  return a new QualifiedName
                return self._prefix_renamed_map[prefix][local_part]
            else:
                #  assuming it is a URI (with the first part as its scheme)
                #  check if the URI can be compacted by any of the registered namespaces
                for namespace in self.values():
                    if str_value.startswith(namespace.uri):
                        #  create a QName with the namespace
                        return namespace[str_value.replace(namespace.uri, "")]
        elif self._default and isinstance(qname, str):
            # no colon in the identifier and a default namespace is defined,
            # create and return a qualified name in the default namespace
            return self._default[qname]

        if self.parent:
            # all attempts have failed so far
            # now delegate this to the parent NamespaceManager
            return self.parent.valid_qualified_name(qname)

        # Default to FAIL
        return None

    def get_anonymous_identifier(self, local_prefix: str = "id") -> Identifier:
        """Return a fresh anonymous (blank-node) identifier.

        Each call increments an internal counter, so successive calls return
        distinct identifiers.

        Args:
            local_prefix: Prefix for the local part of the identifier
                (default: ``"id"``).

        Returns:
            A new :class:`~prov.identifier.Identifier` of the form
            ``_:<local_prefix><n>``.
        """
        self._anon_id_count += 1
        return Identifier(f"_:{local_prefix}{self._anon_id_count}")

    def _get_unused_prefix(self, original_prefix: str) -> str:
        if original_prefix not in self:
            return original_prefix
        count = 1
        while True:
            new_prefix = "_".join((original_prefix, str(count)))
            if new_prefix in self:
                count += 1
            else:
                return new_prefix

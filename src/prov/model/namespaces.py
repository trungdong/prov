"""Namespace management for PROV documents and bundles."""

from __future__ import annotations  # defer eval: NamespaceManager self-refs in __init__

from collections.abc import Iterable, Mapping

from prov.constants import PROV, XSD
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model.records import NSCollection, QualifiedNameCandidate

DEFAULT_NAMESPACES = {"prov": PROV, "xsd": XSD}
_DEFAULT_NAMESPACES_BY_URI = {ns.uri: ns for ns in DEFAULT_NAMESPACES.values()}


class NamespaceManager(dict[str, Namespace]):
    """Manages namespaces for PROV documents and bundles."""

    parent: NamespaceManager | None = None
    """Parent :class:`NamespaceManager` this manager is a child of, if any."""

    def __init__(
        self,
        namespaces: NSCollection | None = None,
        default: str | None = None,
        parent: NamespaceManager | None = None,
    ):
        """Initialise the namespace manager.

        Args:
            namespaces: Optional namespaces to add, as a ``{prefix: uri}`` mapping
                or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
            default: Optional default namespace URI (default: ``None``).
            parent: Optional parent :class:`NamespaceManager` to make this one a
                child of (default: ``None``).
        """
        dict.__init__(self)
        self._default_namespaces = DEFAULT_NAMESPACES
        self.update(self._default_namespaces)
        self._namespaces: dict[str, Namespace] = {}

        # Plain str -> QualifiedName this manager resolved. A compaction can
        # cache a name minted in an outer scope's namespace. Cleared by every
        # mutation that can change how a string resolves: add_namespace()
        # clears it before the entry is written, and _set_default().
        self._resolve_cache: dict[str, QualifiedName] = {}

        if default is not None:
            self.set_default_namespace(default)
        else:
            self._default: Namespace | None = None
        self.parent = parent
        #  TODO check if default is in the default namespaces
        self._anon_id_count = 0
        self._uri_map: dict[str, Namespace] = {}
        self._rename_map: dict[Namespace, Namespace] = {}
        self._prefix_renamed_map: dict[str, Namespace] = {}
        if namespaces is not None:
            self.add_namespaces(namespaces)

    def get_namespace(self, uri: str) -> Namespace | None:
        """Return the known namespace with the given URI.

        Lookup is by index, not by scan. When more than one known namespace
        has the URI, the built-in ``prov`` and ``xsd`` namespaces win,
        then the explicitly registered namespace, then the default namespace.

        Args:
            uri: The namespace URI to look up.

        Returns:
            The matching :class:`~prov.identifier.Namespace`, or ``None`` if no
            known namespace has that URI.
        """
        namespace = _DEFAULT_NAMESPACES_BY_URI.get(uri)
        if namespace is None:
            namespace = self._uri_map.get(uri)
        if namespace is not None:
            return namespace
        if self._default is not None and self._default.uri == uri:
            return self._default
        return None

    def get_registered_namespaces(self) -> Iterable[Namespace]:
        """Return all explicitly registered namespaces.

        Returns:
            An iterable of :class:`~prov.identifier.Namespace`. This excludes
            the default namespaces (``prov`` and ``xsd``).
        """
        return self._namespaces.values()

    def set_default_namespace(self, uri: str) -> None:
        """Set the default namespace to one with the given URI.

        Args:
            uri: The URI of the default namespace.
        """
        self._set_default(Namespace("", uri))

    def _set_default(self, namespace: Namespace, register: bool = True) -> None:
        self._default = namespace
        if register:
            self[""] = namespace
        self._resolve_cache.clear()

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
            # _prefix_renamed_map feeds _resolve_prefixed_string, so cached
            # resolutions are stale from here.
            self._resolve_cache.clear()
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
        self._resolve_cache.clear()
        self._namespaces[prefix] = namespace
        self[prefix] = namespace
        self._uri_map[uri] = namespace

        return namespace

    def add_namespaces(self, namespaces: NSCollection) -> None:
        """Add multiple namespaces into this manager.

        Args:
            namespaces: The namespaces to add, as a ``{prefix: uri}`` mapping
                or an iterable of :class:`~prov.identifier.Namespace`.
        """
        if isinstance(namespaces, Mapping):
            namespaces = [Namespace(prefix, uri) for prefix, uri in namespaces.items()]
        for ns in namespaces:
            self.add_namespace(ns)

    def valid_qualified_name(
        self, qname: QualifiedNameCandidate
    ) -> QualifiedName | None:
        """Resolve an identifier to a valid qualified name.

        Registers the namespace of the resolved name if it was not registered
        already. Where the identifier is a string or :class:`~prov.identifier.Identifier`, an
        attempt is made to expand a prefix declared here, or, when no enclosing
        scope declares the prefix, to compact a known namespace URI, delegating
        to the parent manager if all local attempts fail.

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
            return self._reconcile_qualified_name(qname)

        # Trying to generate a valid qualified name from here
        if not isinstance(qname, (str, Identifier)):
            # Only proceed with a string or URI value
            return None

        if not isinstance(qname, str):
            # An Identifier resolves the same way a plain string does, except
            # a colon-less value never falls back to the default namespace
            # (see _resolve_string). It bypasses the cache entirely, both
            # read and write, because the cache is keyed by string value only
            # and would otherwise conflate the two.
            resolved = self._resolve_string(qname.uri, is_plain_str=False)
        else:
            # Plain string input: served from, and written to, this
            # manager's own cache.
            resolved = self._resolve_cache.get(qname)
            if resolved is None:
                resolved = self._resolve_string(qname, is_plain_str=True)
                if resolved is not None:
                    self._resolve_cache[qname] = resolved

        if resolved is not None or not self.parent:
            return resolved
        # all attempts have failed so far; delegate to the parent, but do
        # not cache a result this manager did not itself resolve
        return self.parent.valid_qualified_name(qname)

    def _resolve_string(
        self, str_value: str, is_plain_str: bool
    ) -> QualifiedName | None:
        if str_value.startswith("_:"):
            # this is a blank node ID
            return None
        if ":" in str_value:
            return self._resolve_prefixed_string(str_value)
        if self._default and is_plain_str:
            # no colon in the identifier and a default namespace is defined,
            # create and return a qualified name in the default namespace
            return self._default[str_value]
        return None

    def _reconcile_qualified_name(self, qname: QualifiedName) -> QualifiedName:
        # The name as this scope holds it: unchanged when a scope in reach
        # binds its namespace (#449), else registered here, renamed when this
        # scope binds the prefix to another IRI.
        namespace = qname.namespace
        prefix = namespace.prefix
        if not prefix and not qname.localpart:
            # The IRI itself has no spelling in a default namespace (#473).
            return self._prefixed_namespace(namespace.uri)[""]
        bound = self._binding_in_scope(prefix)
        if bound is namespace:
            return qname
        if bound == namespace:
            return bound[qname.localpart]
        if prefix:
            return self.add_namespace(Namespace(prefix, namespace.uri))[qname.localpart]
        if self._default is None:
            # No default anywhere in reach: adopt the one given, unregistered,
            # so it takes no part in compaction or ":local" resolution.
            self._set_default(namespace, register=False)
            return qname
        return self.add_namespace(Namespace("dn", namespace.uri))[qname.localpart]

    def _resolve_prefixed_string(self, str_value: str) -> QualifiedName | None:
        #  check if the identifier contains a registered prefix
        prefix, local_part = str_value.split(":", 1)
        if prefix in self:
            #  return a new QualifiedName
            return self[prefix][local_part]
        if prefix in self._prefix_renamed_map:
            #  return a new QualifiedName
            return self._prefix_renamed_map[prefix][local_part]
        if (
            self.parent is not None
            and self.parent._binding_in_scope(prefix) is not None
        ):
            # An enclosing scope declares the prefix and resolves the name;
            # compacting it here would read it as another name (#599).
            return None
        #  assuming it is a URI (with the first part as its scheme)
        #  check if the URI can be compacted by any of the registered namespaces
        for namespace in self.values():
            if str_value.startswith(namespace.uri):
                local = str_value[len(namespace.uri) :]
                if not local and not namespace.prefix:
                    # the IRI itself; the name takes a prefix (#473)
                    return self._reconcile_qualified_name(namespace[local])
                return namespace[local]
        return None

    def _prefixed_namespace(self, uri: str) -> Namespace:
        """The nearest namespace bound to ``uri`` whose prefix this scope
        reads the same way, ``dn`` (or the next free suffix) registered here
        when there is none (#473)."""
        manager: NamespaceManager | None = self
        while manager is not None:
            namespace = manager._uri_map.get(uri)
            if (
                namespace is not None
                and self._binding_in_scope(namespace.prefix) is namespace
            ):
                return namespace
            manager = manager.parent
        return self.add_namespace(Namespace("dn", uri))

    def _binding(self, prefix: str) -> Namespace | None:
        """The namespace this scope alone binds ``prefix`` to, the default
        for ``""``, or ``None``. A registered prefix wins over a renamed one."""
        if not prefix:
            return self._default
        return self.get(prefix) or self._prefix_renamed_map.get(prefix)

    def _binding_in_scope(self, prefix: str) -> Namespace | None:
        """The namespace the nearest scope binds ``prefix`` to, or ``None``."""
        manager: NamespaceManager | None = self
        while manager is not None:
            namespace = manager._binding(prefix)
            if namespace is not None:
                return namespace
            manager = manager.parent
        return None

    def lookup(self, prefix: str, local: str) -> QualifiedName | None:
        """Resolve a name a reader has already split at its first ``:``.

        The name is minted from the namespace the nearest scope binds
        ``prefix`` to, the nearest default namespace for an empty prefix.
        Nothing is compacted, registered or cached. ``("", "")`` and the
        blank-node prefix ``_`` resolve to nothing whatever is declared.

        Args:
            prefix: The prefix before the first ``:``, ``""`` for none.
            local: The local part after it.

        Returns:
            The :class:`~prov.identifier.QualifiedName`, or ``None`` when no
            scope binds ``prefix``.
        """
        if prefix == "_" or (prefix, local) == ("", ""):
            return None
        namespace = self._binding_in_scope(prefix)
        return None if namespace is None else namespace[local]

    def _unresolved_reason(self, text: str) -> str:
        """Why ``text`` resolves to no qualified name by its prefix, as the
        clause after "because"; meaningful after :meth:`lookup` returned
        ``None`` for the text's prefix and local part."""
        if text in ("", ":"):
            return "it is empty"
        if text.startswith("_:"):
            return "its prefix '_' is reserved for blank nodes"
        if ":" in text:
            return f"its prefix {text.partition(':')[0]!r} is not declared"
        return "it has no prefix and no default namespace is declared"

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

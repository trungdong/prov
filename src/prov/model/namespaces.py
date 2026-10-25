"""Namespace management for PROV documents and bundles."""

from __future__ import annotations  # defer eval: NamespaceManager self-refs in __init__

from collections.abc import Callable, Iterable, Iterator, Mapping

from prov.constants import PROV, XSD
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model.records import (
    NSCollection,
    ProvException,
    ProvExceptionInvalidQualifiedName,
    QualifiedNameCandidate,
)

DEFAULT_NAMESPACES = {"prov": PROV, "xsd": XSD}
_DEFAULT_NAMESPACES_BY_URI = {ns.uri: ns for ns in DEFAULT_NAMESPACES.values()}


def _default_iri_detail(uri: str) -> str:
    return (
        f"the IRI {uri} is the default namespace and has no qualified-name form; "
        "declare a prefix for it"
    )


def _undeclared_default_detail(qname: QualifiedName) -> str:
    return (
        f"the name '{qname.localpart}' is in the default namespace "
        f"{qname.namespace.uri}, which is not the default namespace in scope; "
        "declare a prefix for it"
    )


def _first_free(prefix: str, taken: Callable[[str], bool]) -> str:
    """``prefix`` when ``taken`` rejects it, else the first ``prefix_N``
    it rejects."""
    candidate, count = prefix, 1
    while taken(candidate):
        candidate = f"{prefix}_{count}"
        count += 1
    return candidate


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

        # Maps a plain string to the name this manager resolved, possibly one
        # minted in an outer scope's namespace. add_namespace() and
        # _set_default() clear it whenever a string could resolve differently.
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
        self._set_default(Namespace._default(uri))

    def _set_default(self, namespace: Namespace) -> None:
        self._default = namespace
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

        Raises:
            ProvException: If ``namespace`` is a default namespace, which only
                :meth:`set_default_namespace` declares.
        """
        if not namespace.prefix:
            raise ProvException(
                "a default namespace is set with set_default_namespace(), "
                "not add_namespace()"
            )
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

        Raises:
            ValueError: If a mapping has an empty prefix.
            ProvException: If an iterable holds a default namespace.
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
        # binds its namespace (#449); a name in a default namespace no scope
        # in reach declares takes a prefix in reach that is bound to its IRI
        # and rejected without one, as is the default IRI itself (#473);
        # a prefixed foreign namespace is registered here under a prefix no
        # scope in reach binds.
        namespace = qname.namespace
        prefix = namespace.prefix
        if not prefix and not qname.localpart:
            raise ProvExceptionInvalidQualifiedName(
                qname, _default_iri_detail(namespace.uri)
            )
        if self.get(prefix) is namespace:
            # hot-path shortcut for a name this scope already holds
            return qname
        bound = self._binding_in_scope(prefix)
        if bound is namespace:
            return qname
        if bound == namespace:
            return bound[qname.localpart]
        if not prefix:
            return self._spelled_by_prefix(qname)
        existing = self._uri_map.get(namespace.uri)
        if existing is not None:
            if prefix not in self:
                # the prefix the caller gave reads as the registered namespace
                self._prefix_renamed_map.setdefault(prefix, existing)
                self._resolve_cache.clear()
            return existing[qname.localpart]
        chosen = prefix if bound is None else self._unused_prefix_in_scope(prefix)
        return self.add_namespace(Namespace(chosen, namespace.uri))[qname.localpart]

    def _spelled_by_prefix(self, qname: QualifiedName) -> QualifiedName:
        """``qname`` under the nearest prefix in reach bound to its IRI that
        this scope reads the same way; nothing is minted."""
        uri = qname.namespace.uri
        for manager in self._scopes():
            namespace = manager.get_namespace(uri)
            if (
                namespace is not None
                and self._binding_in_scope(namespace.prefix) is namespace
            ):
                return namespace[qname.localpart]
        raise ProvExceptionInvalidQualifiedName(
            qname, _undeclared_default_detail(qname)
        )

    def _resolve_prefixed_string(self, str_value: str) -> QualifiedName | None:
        #  check if the identifier contains a registered prefix
        prefix, local_part = str_value.split(":", 1)
        namespace = self._binding(prefix)
        if namespace is not None:
            return namespace[local_part]
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
            local = str_value[len(namespace.uri) :]
            if str_value.startswith(namespace.uri) and (namespace.prefix or local):
                return namespace[local]
        return None

    def reject_default_iri(self, text: str) -> None:
        """Raise when ``text`` is the IRI of a default namespace in reach.

        Called by the assertion paths after ``text`` resolved to nothing. The
        IRI has no qualified-name form, so the model rejects it and mints no
        prefix for it (#473).

        Args:
            text: The identifier text being asserted.

        Raises:
            ProvExceptionInvalidQualifiedName: If ``text`` equals the IRI of
                this manager's default or an enclosing one.
        """
        iri = self._default_iri_in_reach(text)
        if iri is not None:
            raise ProvExceptionInvalidQualifiedName(text, _default_iri_detail(iri))

    def _default_iri_in_reach(self, text: str) -> str | None:
        """The IRI of the default namespace in reach that equals ``text``, or
        ``None``."""
        for manager in self._scopes():
            default = manager._default
            if default is not None and default.uri == text:
                return default.uri
        return None

    def _scopes(self) -> Iterator[NamespaceManager]:
        """This manager, then each of its ancestors."""
        manager: NamespaceManager | None = self
        while manager is not None:
            yield manager
            manager = manager.parent

    def _binding(self, prefix: str) -> Namespace | None:
        """The namespace this scope alone binds ``prefix`` to, the default
        for ``""``, or ``None``. A registered prefix wins over a renamed one."""
        return self.get(prefix) or self._prefix_renamed_map.get(prefix)

    def _binding_in_scope(self, prefix: str) -> Namespace | None:
        """The namespace the nearest scope binds ``prefix`` to, or ``None``."""
        if self.parent is None:
            return self._binding(prefix)
        manager: NamespaceManager | None = self
        while manager is not None:
            namespace = manager.get(prefix) or manager._prefix_renamed_map.get(prefix)
            if namespace is not None:
                return namespace
            manager = manager.parent
        return None

    def _unused_prefix_in_scope(self, prefix: str) -> str:
        """``prefix`` when no scope in reach binds it, else the first
        ``prefix_N`` none binds, so a namespace the model registers itself
        never shadows a declared one."""
        return _first_free(prefix, lambda p: self._binding_in_scope(p) is not None)

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

    def _unresolved_reason(
        self, prefix: str, local: str, colon: bool, text: str
    ) -> str:
        """Why the name split into ``prefix`` and ``local`` resolves to no
        qualified name, as the clause after "because"; meaningful after
        :meth:`lookup` returned ``None`` for the pair. ``colon`` says the
        name was written with a ``:``, so an empty ``prefix`` is a declared
        empty prefix and not the lack of one. ``text`` is the name as
        written; when it is the IRI of a default namespace in reach, that
        is the reason (#675)."""
        if (iri := self._default_iri_in_reach(text)) is not None:
            return _default_iri_detail(iri)
        if (prefix, local) == ("", ""):
            return "it is empty"
        if prefix == "_":
            return "its prefix '_' is reserved for blank nodes"
        if prefix or colon:
            return f"its prefix {prefix!r} is not declared"
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
        return _first_free(original_prefix, self.__contains__)

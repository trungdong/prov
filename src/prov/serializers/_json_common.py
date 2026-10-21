"""The JSON machinery PROV-JSON and PROV-JSONLD share.

:mod:`prov.serializers.provjson` and :mod:`prov.serializers.provjsonld` both
write qualified names against a container's prefix map and fan a membership
out into one ``hadMember`` record per member. Those pieces live here so that
neither module imports the other's private names. The position and rejection
helpers that PROV-JSON's messages use live here too (#589).
"""

import json
import typing
from collections.abc import Sequence
from typing import Any

from prov._warnings import ProvFutureRejectionWarning, future_rejection_message, warn
from prov.constants import PROV_ATTR_ENTITY, PROV_MEMBERSHIP
from prov.identifier import Namespace, QualifiedName
from prov.model import AttributePair, OptionalID, ProvBundle, QualifiedNameCandidate

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

_Kind = typing.Literal["record", "bundle"]


def _position(rec_id: str | None, attr_name: str | None, kind: _Kind = "record") -> str:
    """Return the ``"record 'r', attribute 'a': "`` that starts a message,
    naming as much of the value's position as is known; ``kind`` is ``"bundle"``
    for a bundle's key."""
    parts = []
    if rec_id is not None:
        parts.append(f"{kind} {rec_id!r}")
    if attr_name is not None:
        parts.append(f"attribute {attr_name!r}")
    return ", ".join(parts) + ": " if parts else ""


def _json_text(value: Any) -> str:
    """Return ``value`` as JSON text, or ``str(value)`` if JSON cannot encode it."""
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return str(value)


def _warn_rejection(
    detail: str,
    rec_id: str | None = None,
    attr_name: str | None = None,
    *,
    issue: int,
    kind: _Kind = "record",
) -> None:
    """Warn that 3.3.0 rejects the value ``detail`` describes."""
    warn(
        future_rejection_message(
            _position(rec_id, attr_name, kind) + detail, issue=issue
        ),
        ProvFutureRejectionWarning,
    )


class _JSONPrefixMap:
    """The prefix map of one PROV-JSON or PROV-JSONLD container, and the text
    of each qualified name written against it.

    A reader splits a name at its first ``:``, so two kinds of name are
    written with a prefix other than their own.

    * a name in the default namespace whose local part contains ``:`` (#517)
      takes a prefix in scope bound to the namespace IRI, and one is declared
      in :attr:`prefixes` if none exists;
    * a name whose prefix is one of ``default_keys``, the keys that hold the
      default namespace (#518), takes a generated prefix.

    The prefix declared for the default namespace is ``dn``, the name
    :class:`~prov.model.NamespaceManager` gives a second default namespace. A
    generated prefix that is already in scope, including in ``parent``, takes
    the next free suffix (``default_1``, ``dn_1``, ...), as in
    :class:`~prov.model.NamespaceManager`'s renaming. Every other name is
    written as ``str(name)``.
    """

    def __init__(
        self,
        bundle: ProvBundle,
        default_keys: tuple[str, ...] = ("default",),
        parent: "_JSONPrefixMap | None" = None,
    ) -> None:
        """Build the prefix map for ``bundle``'s container.

        Args:
            bundle: Bundle (or document) whose namespaces are written.
            default_keys: The keys that hold the default namespace, ``default``
                in PROV-JSON and ``@vocab`` and ``@base`` in PROV-JSONLD. A
                registered prefix with one of these names is renamed.
            parent: The enclosing document's map, whose prefixes are in scope
                in a bundle.
        """
        self.prefixes: dict[str, str] = {}
        """Prefix (or default key) -> namespace IRI, in writing order."""
        self._namespaces = bundle._namespaces
        self._default_keys = default_keys
        self._parent = parent
        self._chosen: dict[Namespace, str] = {}
        for namespace in self._namespaces.get_registered_namespaces():
            prefix = namespace.prefix
            if prefix in default_keys:
                prefix = self._chosen[namespace] = self._unused_prefix(prefix)
            self.prefixes[prefix] = namespace.uri
        default = self._namespaces.get_default_namespace()
        if default is not None:
            for key in default_keys:
                self.prefixes[key] = default.uri

    def qname_text(self, name: object) -> str:
        """Return the text that writes ``name``; ``str(name)`` for anything
        but a :class:`~prov.identifier.QualifiedName` that needs a prefix."""
        if isinstance(name, QualifiedName):
            # read the slots directly, as this runs for every name written
            prefix = name._namespace._prefix
            if prefix in self._default_keys or (not prefix and ":" in name._localpart):
                return f"{self._prefix_for(name.namespace)}:{name.localpart}"
            return name._str
        return str(name)

    def _prefix_for(self, namespace: Namespace) -> str:
        prefix = self._find(namespace)
        if prefix is None:
            prefix = self._chosen[namespace] = self._unused_prefix(
                namespace.prefix or "dn"
            )
            self.prefixes[prefix] = namespace.uri
        return prefix

    def _find(self, namespace: Namespace) -> str | None:
        """Return a prefix in scope here that is bound to ``namespace``'s IRI."""
        if namespace in self._chosen:
            return self._chosen[namespace]
        for prefix, uri in self.prefixes.items():
            if uri == namespace.uri and prefix not in self._default_keys:
                self._chosen[namespace] = prefix
                return prefix
        if self._parent is not None:
            inherited = self._parent._find(namespace)
            # a prefix declared here shadows the parent's
            if inherited is not None and inherited not in self.prefixes:
                self._chosen[namespace] = inherited
                return inherited
        return None

    def _taken(self, prefix: str) -> bool:
        return (
            prefix in self.prefixes
            or prefix in self._namespaces
            or (self._parent is not None and self._parent._taken(prefix))
        )

    def _unused_prefix(self, base: str) -> str:
        if not self._taken(base) and base not in self._default_keys:
            return base
        count = 1
        while self._taken(f"{base}_{count}"):
            count += 1
        return f"{base}_{count}"


def _add_memberships(
    bundle: ProvBundle,
    identifier: OptionalID,
    attributes: dict[QualifiedNameCandidate, Any],
    other_attributes: list[AttributePair],
    members: Sequence[QualifiedName | None],
) -> None:
    """Add one ``hadMember`` record per member to ``bundle``.

    PROV-DM's ``hadMember`` is binary, so a membership listing several members
    becomes one record per member. Each record carries the identifier and the
    attributes of the membership. The PROV-JSON and PROV-JSONLD readers share
    this fan-out.

    Args:
        bundle: Bundle to add the records to.
        identifier: The membership's identifier, or ``None``.
        attributes: The membership's formal attributes other than
            ``prov:entity``.
        other_attributes: The membership's other attributes.
        members: The resolved members, one record each.
    """
    for member in members:
        bundle.new_record(
            PROV_MEMBERSHIP,
            identifier,
            {**attributes, PROV_ATTR_ENTITY: member},
            other_attributes,
        )

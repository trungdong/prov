"""PROV-JSON serializer for ProvDocument."""

import datetime
import io
import json
import typing
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from typing import Any

from prov import Error
from prov._warnings import ProvFutureRejectionWarning, future_rejection_message, warn
from prov.constants import *
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import (
    AttributePair,
    Literal,
    OptionalID,
    ProvBundle,
    ProvDocument,
    ProvRecord,
    QualifiedNameCandidate,
    canonical_xsd_datatype,
    first,
    parse_xsd_datetime,
)
from prov.model.records import (
    _reader_checking_names,
    _xsd_datetime_text,
    _xsd_double_text,
)
from prov.serializers import Serializer, _is_text_stream

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

_Kind = typing.Literal["record", "bundle"]


ProvJSONDict = dict[str, dict[str, Any]]


class ProvJSONException(Error):
    """Raised when a PROV-JSON document contains a construct this package cannot decode."""


class AnonymousIDGenerator:
    """Assigns and caches stable blank-node identifiers for unidentified records."""

    def __init__(self) -> None:
        self._cache: dict[ProvRecord, Identifier] = {}
        self._count: int = 0

    def get_anon_id(self, obj: ProvRecord, local_prefix: str = "id") -> Identifier:
        """Return a blank-node :class:`~prov.identifier.Identifier` for a record.

        The same object always gets the same identifier back; a new one
        (``_:<local_prefix><n>``) is minted and cached the first time a given
        record is seen.

        Args:
            obj: Record needing an anonymous identifier.
            local_prefix: Prefix used when minting a new identifier.

        Returns:
            The cached or newly minted blank-node identifier for ``obj``.
        """
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = Identifier(f"_:{local_prefix}{self._count}")
        return self._cache[obj]


class ProvJSONSerializer(Serializer):
    """PROV-JSON serializer for :class:`~prov.model.ProvDocument`."""

    deserialize_options = frozenset(
        {
            "object_hook",
            "object_pairs_hook",
            "parse_float",
            "parse_int",
            "parse_constant",
        }
    )
    """The :func:`json.load` options :meth:`deserialize` forwards.

    ``object_hook`` and ``object_pairs_hook`` receive each object after the
    check for repeated keys."""

    def serialize(self, stream: io.IOBase, **args: Any) -> None:
        """Serialize ``self.document`` to `PROV-JSON <https://openprovenance.org/prov-json/>`_.

        Args:
            stream: Stream to write the output to. Text streams receive the
                JSON text directly; other (binary) streams receive it
                UTF-8-encoded.
            **args: Extra keyword arguments passed through to
                :func:`json.dump`.
        """
        buf = io.StringIO()
        try:
            json.dump(self.document, buf, cls=ProvJSONEncoder, **args)
            buf.seek(0, 0)
            # Right now this is a bytestream. If the object to stream to is
            # a text object, it must be decoded. We assume utf-8 here, which
            # should be fine for almost every case.
            if _is_text_stream(stream):
                stream.write(buf.read())
            else:
                stream.write(buf.read().encode("utf-8"))
        finally:
            buf.close()

    def deserialize(self, stream: io.IOBase, **args: Any) -> ProvDocument:
        """Deserialize a `PROV-JSON <https://openprovenance.org/prov-json/>`_
        stream into a :class:`~prov.model.ProvDocument`.

        A key repeated in a JSON object warns with
        :class:`~prov.model.ProvFutureRejectionWarning`; the last value is used.

        Args:
            stream: Input data; binary streams are decoded as UTF-8 first.
            **args: Extra keyword arguments passed through to
                :func:`json.load`.

        Returns:
            The deserialized :class:`~prov.model.ProvDocument`.
        """
        if not _is_text_stream(stream):
            buf = io.StringIO(stream.read().decode("utf-8"))
            stream = buf
        repeated: list[str] = []
        hook = _repeated_key_hook(
            repeated, args.pop("object_hook", None), args.pop("object_pairs_hook", None)
        )
        container = json.load(stream, object_pairs_hook=hook, **args)
        for key in repeated:
            _warn_rejection(
                f"the key {key!r} is repeated in a JSON object; the last value is used",
                issue=532,
            )
        # Decoded here, not in json.load(), so that a warning names the caller's line.
        document = ProvDocument()
        decode_json_document(container, document)
        return document


def _repeated_key_hook(
    repeated: list[str],
    object_hook: Callable[[dict[str, Any]], Any] | None,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None,
) -> Callable[[list[tuple[str, Any]]], Any]:
    """Return a ``json`` ``object_pairs_hook`` that records each repeated key
    in ``repeated`` and then hands the object to the caller's own hook."""

    def hook(pairs: list[tuple[str, Any]]) -> Any:
        obj = dict(pairs)
        if len(obj) < len(pairs):
            counts = Counter(key for key, _ in pairs)
            repeated.extend(key for key, count in counts.items() if count > 1)
        if object_pairs_hook is not None:
            return object_pairs_hook(pairs)
        return object_hook(obj) if object_hook is not None else obj

    return hook


class ProvJSONEncoder(json.JSONEncoder):
    """``json.JSONEncoder`` that knows how to encode a :class:`~prov.model.ProvDocument`."""

    def default(self, o: Any) -> Any:
        """Return the PROV-JSON container dict for a :class:`~prov.model.ProvDocument`.

        Args:
            o: Object being encoded.

        Returns:
            The result of :func:`encode_json_document` if ``o`` is a
            :class:`~prov.model.ProvDocument`, otherwise the superclass's
            default handling.
        """
        if isinstance(o, ProvDocument):
            return encode_json_document(o)
        else:
            return super().encode(o)


class ProvJSONDecoder(json.JSONDecoder):
    """``json.JSONDecoder`` that decodes PROV-JSON into a :class:`~prov.model.ProvDocument`.

    Used directly with :func:`json.loads`, it does not warn about repeated keys;
    :meth:`ProvJSONSerializer.deserialize` does.
    """

    def decode(self, s: str, *args: Any, **kwargs: Any) -> Any:
        """Parse a PROV-JSON string into a new :class:`~prov.model.ProvDocument`.

        Args:
            s: PROV-JSON text to parse.
            *args: Extra positional arguments passed to the superclass's
                ``decode()``.
            **kwargs: Extra keyword arguments passed to the superclass's
                ``decode()``.

        Returns:
            A new :class:`~prov.model.ProvDocument` populated via
            :func:`decode_json_document`.
        """
        container = super().decode(s, *args, **kwargs)
        document = ProvDocument()
        decode_json_document(container, document)
        return document


# Encoding/decoding functions
def valid_qualified_name(
    bundle: ProvBundle, value: QualifiedNameCandidate | None
) -> QualifiedName | None:
    """Resolve a candidate value to a :class:`~prov.identifier.QualifiedName` in a bundle.

    Args:
        bundle: Bundle whose namespaces are used to resolve ``value``.
        value: Candidate qualified name (string, :class:`QualifiedName`, or
            other supported representation), or ``None``.

    Returns:
        The resolved :class:`~prov.identifier.QualifiedName`, or ``None`` if
        ``value`` is ``None`` or cannot be resolved.
    """
    if value is None:
        return None
    qualified_name = bundle.valid_qualified_name(value)
    return qualified_name


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


def encode_json_document(document: ProvDocument) -> ProvJSONDict:
    """Encode a whole :class:`~prov.model.ProvDocument`, including its named bundles.

    Args:
        document: Document to encode.

    Returns:
        The PROV-JSON container dict for ``document``, with each named
        bundle's own encoded container nested under ``container["bundle"]``
        keyed by the bundle's identifier string.
    """
    prefix_map = _JSONPrefixMap(document)
    container = encode_json_container(document, prefix_map)
    for bundle in document.bundles:
        #  encoding the sub-bundle
        bundle_map = _JSONPrefixMap(bundle, parent=prefix_map)
        # a reader resolves the bundle identifier in the bundle's own scope
        bundle_id = bundle_map.qname_text(bundle.identifier)
        container["bundle"][bundle_id] = encode_json_container(bundle, bundle_map)
    return container


def encode_json_container(
    bundle: ProvBundle, prefix_map: _JSONPrefixMap | None = None
) -> ProvJSONDict:
    """Encode a single bundle's namespaces and records to a PROV-JSON container dict.

    Does not recurse into ``bundle``'s own named bundles; see
    :func:`encode_json_document` for encoding a whole document.

    Args:
        bundle: Bundle (or document, treated as its top-level bundle) to
            encode.
        prefix_map: The container's prefix map; built from ``bundle`` if not
            given.

    Returns:
        A dict with an optional ``"prefix"`` entry for registered namespaces
        and one entry per PROV-N record-type keyword, each mapping record
        identifiers (real or anonymous) to their encoded attributes.
    """
    if prefix_map is None:
        prefix_map = _JSONPrefixMap(bundle)
    qname_text = prefix_map.qname_text
    container: dict[str, dict[str, Any]] = defaultdict(dict)
    # filled as names are written; removed below if still empty
    container["prefix"] = prefix_map.prefixes

    id_generator = AnonymousIDGenerator()

    def real_or_anon_id(r: ProvRecord) -> Identifier:
        return r._identifier if r._identifier else id_generator.get_anon_id(r)

    for record in bundle._records:
        rec_type = record.get_type()
        rec_label = PROV_N_MAP[rec_type]
        identifier = qname_text(real_or_anon_id(record))

        record_json: dict[str, Any] = {}
        if record._attributes:
            for attr, values in record._attributes.items():
                if not values:
                    continue
                attr_name = qname_text(attr)
                if attr in PROV_ATTRIBUTE_QNAMES:
                    # TODO: QName export
                    record_json[attr_name] = qname_text(first(values))
                elif attr in PROV_ATTRIBUTE_LITERALS:
                    record_json[attr_name] = _xsd_datetime_text(
                        first(values)  # type: ignore[arg-type]
                    )
                else:
                    if len(values) == 1:
                        # single value
                        record_json[attr_name] = encode_json_representation(
                            first(values), qname_text
                        )
                    else:
                        # multiple values
                        record_json[attr_name] = [
                            encode_json_representation(value, qname_text)
                            for value in values
                        ]
        # Check if the container already has the id of the record
        if identifier not in container[rec_label]:
            # this is the first instance, just put in the new record
            container[rec_label][identifier] = record_json
        else:
            # the container already has some record(s) of the same identifier
            # check if this is the second instance
            current_content = container[rec_label][identifier]
            if hasattr(current_content, "items"):
                # this is a dict, make it a singleton list
                container[rec_label][identifier] = [current_content]
            # now append the new record to the list
            container[rec_label][identifier].append(record_json)

    if not prefix_map.prefixes:
        del container["prefix"]
    return container


def _expect_json_object(value: Any, description: str) -> dict[str, Any]:
    """Check that a decoded JSON value is an object (a Python ``dict``).

    Args:
        value: Value to check.
        description: Human-readable name of what ``value`` represents (e.g.
            ``'The "prefix" value'``), used to build the exception message.

    Returns:
        ``value`` unchanged, for convenient chaining.

    Raises:
        ProvJSONException: If ``value`` is not a ``dict``.
    """
    if not isinstance(value, dict):
        raise ProvJSONException(
            f"{description} must be a JSON object; found "
            f"{type(value).__name__}: {value!r}"
        )
    return value


def _json_record_elements(
    content: Any, rec_type_str: str, rec_id: str
) -> list[dict[str, Any]]:
    """Normalise one record's raw PROV-JSON content to a list of attribute dicts.

    A record's content is either a single JSON object (one instance of
    ``rec_id``) or a JSON array of objects (multiple instances sharing the
    same identifier).

    Args:
        content: The raw value keyed by ``rec_id``.
        rec_type_str: The enclosing record-type keyword (e.g. ``"entity"``),
            used in the exception message.
        rec_id: The record identifier string, used in the exception message.

    Returns:
        A list of attribute dicts, one per instance.

    Raises:
        ProvJSONException: If ``content`` is neither a JSON object nor a
            JSON array of JSON objects.
    """
    if isinstance(content, dict):
        return [content]
    if isinstance(content, list) and all(isinstance(el, dict) for el in content):
        return content
    raise ProvJSONException(
        f"The {rec_type_str!r} record {rec_id!r} must be a JSON object "
        f"(single instance) or a list of JSON objects (multiple "
        f"instances); found {content!r}"
    )


def decode_json_document(content: ProvJSONDict, document: ProvDocument) -> None:
    """Decode a whole PROV-JSON container, including named bundles, into a document.

    Mutates ``content`` in place, removing the top-level ``"bundle"`` key (if
    present) before decoding the rest as the document's own records; mutates
    ``document`` in place by adding the decoded records and named bundles to
    it.

    Args:
        content: PROV-JSON container dict, as produced by
            :func:`encode_json_document` (or parsed JSON in that shape).
        document: Document to populate.

    Raises:
        ProvJSONException: If ``content``, or its ``"bundle"`` value (when
            present), is not a JSON object.
    """
    _expect_json_object(content, "A PROV-JSON document")
    bundles = {}
    if "bundle" in content:
        bundles = _expect_json_object(content["bundle"], 'The "bundle" value')
        del content["bundle"]

    decode_json_container(content, document)

    for bundle_id, bundle_content in bundles.items():
        bundle = ProvBundle(document=document)
        decode_json_container(bundle_content, bundle)
        _check_record_key(bundle, bundle_id, "bundle")
        document.add_bundle(bundle, bundle.valid_qualified_name(bundle_id))


def decode_json_container(jc: ProvJSONDict, bundle: ProvBundle) -> None:
    """Decode one PROV-JSON container's namespaces and records into a bundle.

    Mutates ``jc`` in place, removing the ``"prefix"`` key (if present) once
    its namespaces have been registered on ``bundle``; mutates ``bundle`` in
    place by adding the decoded records to it. Does not handle a nested
    ``"bundle"`` key; see :func:`decode_json_document` for a whole document.

    Args:
        jc: PROV-JSON container dict for a single bundle (no ``"bundle"``
            key), as produced by :func:`encode_json_container`.
        bundle: Bundle to populate.

    Raises:
        ProvJSONException: If ``jc`` is not a JSON object; if its
            ``"prefix"`` value (when present) is not a JSON object; if a key
            other than ``"prefix"`` is not a recognised PROV-N record-type
            keyword; if a record-type's value is not a JSON object mapping
            record identifiers to content; if a record's content is not a
            JSON object or a list of JSON objects; if a non-formal
            attribute's typed-literal representation is missing its required
            ``"$"`` key (see :func:`decode_json_representation`); if a
            formal (QualifiedName- or literal-valued) attribute has more
            than one value, other than the members of ``hadMember``; if a
            formal attribute is written as an empty JSON array; or if a time
            attribute's value is neither a string nor an ``xsd:dateTime``
            value object with a well-formed ``"$"``.
    """
    _expect_json_object(jc, "A PROV-JSON container")
    if "prefix" in jc:
        _decode_namespaces(jc, bundle)

    # The reader warns about its own qualified-name values, with their
    # position, so the model does not warn about them again.
    with _reader_checking_names():
        for rec_type_str in jc:
            _decode_record_group(jc, rec_type_str, bundle)


def _decode_namespaces(jc: ProvJSONDict, bundle: ProvBundle) -> None:
    """Register a container's namespaces on ``bundle`` and consume its ``"prefix"`` key.

    Mutates ``jc`` in place, removing the ``"prefix"`` key once its
    namespaces have been registered.

    Args:
        jc: PROV-JSON container dict; must contain a ``"prefix"`` key.
        bundle: Bundle to register the namespaces on.

    Raises:
        ProvJSONException: If the ``"prefix"`` value is not a JSON object.
    """
    prefixes = _expect_json_object(jc["prefix"], 'The "prefix" value')
    for prefix, uri in prefixes.items():
        if prefix != "default":
            bundle.add_namespace(Namespace(prefix, uri))
        else:
            bundle.set_default_namespace(uri)
    del jc["prefix"]


def _decode_record_group(
    jc: ProvJSONDict, rec_type_str: str, bundle: ProvBundle
) -> None:
    """Decode every record instance filed under one PROV-N record-type keyword.

    Args:
        jc: PROV-JSON container dict (its ``"prefix"`` key, if any, already
            consumed).
        rec_type_str: The record-type keyword (e.g. ``"entity"``) naming the
            ``jc`` entry to decode.
        bundle: Bundle to add the decoded records to.

    Raises:
        ProvJSONException: If ``rec_type_str`` is not a recognised PROV-N
            record-type keyword; if its value is not a JSON object mapping
            record identifiers to content; if a record's content is not a
            JSON object or a list of JSON objects; if a non-formal
            attribute's typed-literal representation is missing its required
            ``"$"`` key; if a formal attribute has more than one value,
            other than the members of ``hadMember``; if a formal attribute is
            written as an empty JSON array; or if a time attribute's value is
            neither a string nor an ``xsd:dateTime`` value object with a
            well-formed ``"$"``
            (all raised further down the call chain, by
            :func:`_decode_record_instance` / :func:`_decode_formal_attribute`).
    """
    try:
        rec_type = PROV_RECORD_IDS_MAP[rec_type_str]
    except KeyError as exc:
        raise ProvJSONException(
            f"{rec_type_str!r} is not a recognised PROV-N record-type"
            f" keyword (e.g. 'entity', 'activity', 'wasGeneratedBy')"
        ) from exc
    records_by_id = _expect_json_object(jc[rec_type_str], f"The {rec_type_str!r} value")
    for rec_id, content in records_by_id.items():
        elements = _json_record_elements(content, rec_type_str, rec_id)
        _check_record_key(bundle, rec_id)
        for element in elements:
            _decode_record_instance(rec_type, rec_id, element, bundle)


def _decode_record_instance(
    rec_type: QualifiedName,
    rec_id: str,
    element: dict[str, Any],
    bundle: ProvBundle,
) -> None:
    """Decode one record instance's attributes and add it to ``bundle``.

    Args:
        rec_type: The record's PROV-N record type.
        rec_id: The record's identifier string.
        element: The instance's raw attribute dict, as produced by
            :func:`_json_record_elements`.
        bundle: Bundle to add the decoded record, or one ``hadMember``
            record per member, to.

    Raises:
        ProvJSONException: If a non-formal attribute's typed-literal
            representation is missing its required ``"$"`` key; if a
            formal attribute has more than one value, other than the
            members of ``hadMember``; if a formal attribute is written as an
            empty JSON array; or if a time attribute's value is neither a
            string nor an ``xsd:dateTime`` value object with a well-formed
            ``"$"``.
    """
    attributes: dict[QualifiedNameCandidate, Any] = {}
    other_attributes: list[AttributePair] = []
    members: list[QualifiedName | None] | None = None
    is_membership = rec_type == PROV_MEMBERSHIP
    for attr_name, values in element.items():
        attr: QualifiedName = (
            PROV_ATTRIBUTES_ID_MAP[attr_name]
            if attr_name in PROV_ATTRIBUTES_ID_MAP
            else bundle.mandatory_valid_qname(attr_name)
        )
        if attr in PROV_ATTRIBUTES:
            if is_membership and attr == PROV_ATTR_ENTITY:
                members = _decode_members(rec_id, attr_name, values, bundle)
            else:
                attributes[attr] = _decode_formal_attribute(
                    rec_id, attr_name, attr, values, bundle
                )
        else:
            for value in values if isinstance(values, list) else [values]:
                if value is None:
                    # The model drops a None value.
                    _warn_rejection(
                        "the value is null and is dropped",
                        rec_id,
                        attr_name,
                        issue=528,
                    )
                other_attributes.append(
                    (attr, decode_json_representation(value, bundle, attr_name, rec_id))
                )
    if members is None:
        bundle.new_record(rec_type, rec_id, attributes, other_attributes)
    else:
        _add_memberships(bundle, rec_id, attributes, other_attributes, members)


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


def _decode_members(
    rec_id: str, attr_name: str, values: Any, bundle: ProvBundle
) -> list[QualifiedName | None]:
    """Decode the ``prov:entity`` of a ``hadMember``, a single value or an array.

    Args:
        rec_id: The enclosing record's identifier string, for messages.
        attr_name: The attribute's PROV-JSON key, for messages.
        values: The raw value or JSON array of values.
        bundle: Bundle used to resolve the members' qualified names.

    Returns:
        The resolved members, in the order written. A member that does not
        resolve is ``None``, with a warning.

    Raises:
        ProvJSONException: If ``values`` is an empty JSON array.
    """
    if not isinstance(values, list):
        return [_decode_name(bundle, values, rec_id, attr_name)]
    if not values:
        raise ProvJSONException(
            f"{_position(rec_id, attr_name)}the value is an empty array"
        )
    return [_decode_name(bundle, value, rec_id, attr_name) for value in values]


def _decode_formal_attribute(
    rec_id: str,
    attr_name: str,
    attr: QualifiedName,
    values: Any,
    bundle: ProvBundle,
) -> Any:
    """Decode the value of a formal (:data:`~prov.constants.PROV_ATTRIBUTES`) attribute.

    The members of ``hadMember`` go to :func:`_decode_members` instead.

    Args:
        rec_id: The enclosing record's identifier string, for messages.
        attr_name: The attribute's PROV-JSON key, for messages.
        attr: The formal attribute being decoded.
        values: The raw value read from the PROV-JSON element, either a
            single value or a JSON array.
        bundle: Bundle used to resolve any QualifiedName value.

    Returns:
        The decoded attribute value.

    Raises:
        ProvJSONException: If ``values`` is an empty JSON array or a JSON
            array with more than one value; or if a time attribute's value is
            neither a string nor an ``xsd:dateTime`` value object with a
            well-formed ``"$"``.
    """
    if isinstance(values, list):
        if not values:
            raise ProvJSONException(
                f"{_position(rec_id, attr_name)}the value is an empty array"
            )
        # only one value is allowed
        if len(values) > 1:
            raise ProvJSONException(
                f"{_position(rec_id, attr_name)}the value is an array of "
                f"{len(values)} values, but the attribute takes one"
            )
        _warn_rejection(
            "the value is written as an array", rec_id, attr_name, issue=531
        )
        value = values[0]
    else:
        value = values
    if attr in PROV_ATTRIBUTE_QNAMES:
        return _decode_name(bundle, value, rec_id, attr_name)
    return _decode_time(rec_id, attr_name, value, bundle)


def _decode_name(
    bundle: ProvBundle, value: Any, rec_id: str, attr_name: str
) -> QualifiedName | None:
    """Resolve the qualified name a formal attribute or a member refers to.

    A value that is not a string, and a string that does not resolve, are
    dropped with a warning. A string that resolves only by compacting an IRI
    warns too.
    """
    resolved = valid_qualified_name(bundle, value)
    if value is None:
        _warn_rejection(
            "the value is null and is dropped", rec_id, attr_name, issue=528
        )
    elif not isinstance(value, str):
        _warn_rejection(
            f"the value is {_json_text(value)}, not a qualified name, and is dropped",
            rec_id,
            attr_name,
            issue=597,
        )
    elif (
        # A resolved name with a declared prefix needs no check.
        (resolved is None or value.partition(":")[0] not in bundle._namespaces)
        and (reason := bundle._unresolved_reason(value)) is not None
    ):
        if resolved is None:
            _warn_unresolved_name(
                value, reason, "it is dropped", rec_id, attr_name, issue=516
            )
        else:
            _warn_unresolved_name(
                value, reason, f"it reads as {resolved}", rec_id, attr_name, issue=551
            )
    return resolved


def _check_record_key(bundle: ProvBundle, key: str, kind: _Kind = "record") -> None:
    """Warn when the record or bundle key ``key`` resolves only by compacting an
    IRI (#551); ``kind`` is ``"record"`` or ``"bundle"``."""
    if (
        isinstance(key, str)
        # Check the common cases first, a prefix this bundle declares and a
        # relation's blank node identifier, which has no namespace.
        and (prefix := key.partition(":")[0]) not in bundle._namespaces
        and prefix != "_"
        and (reason := bundle._unresolved_reason(key)) is not None
        and (resolved := bundle.valid_qualified_name(key)) is not None
    ):
        _warn_unresolved_name(
            key, reason, f"it reads as {resolved}", key, issue=551, kind=kind
        )


def _check_name_value(
    bundle: ProvBundle,
    value: Any,
    resolved: QualifiedName | None,
    rec_id: str | None,
    attr_name: str | None,
) -> None:
    """Warn when the qualified-name value ``value`` does not resolve by its
    prefix (#516, #551); ``resolved`` is what it resolves to today."""
    if (
        isinstance(value, str)
        and (reason := bundle._unresolved_reason(value)) is not None
    ):
        today = (
            f"it reads as {resolved}"
            if resolved is not None
            else "it is kept as a Literal"
        )
        issue = 551 if resolved is not None else 516
        _warn_unresolved_name(value, reason, today, rec_id, attr_name, issue=issue)


def _warn_unresolved_name(
    text: str,
    reason: str,
    today: str,
    rec_id: str | None,
    attr_name: str | None = None,
    *,
    issue: int,
    kind: _Kind = "record",
) -> None:
    """Warn that the qualified name ``text`` does not resolve, for ``reason``;
    ``today`` says how ``prov`` reads it instead."""
    _warn_rejection(
        f"the qualified name {text!r} does not resolve, because {reason}; {today}",
        rec_id,
        attr_name,
        issue=issue,
        kind=kind,
    )


def _decode_time(
    rec_id: str, attr_name: str, value: Any, bundle: ProvBundle
) -> datetime.datetime | None:
    """Decode the value of ``prov:time``, ``prov:startTime`` or ``prov:endTime``.

    Args:
        rec_id: The enclosing record's identifier string, for messages.
        attr_name: The attribute's PROV-JSON key, for messages.
        value: A string, or a value object typed ``xsd:dateTime``.
        bundle: Bundle used to resolve the value object's ``"type"``.

    Returns:
        The parsed :class:`~datetime.datetime`, or ``None`` for a string
        that is not an ``xsd:dateTime``, which is dropped with a warning.

    Raises:
        ProvJSONException: If ``value`` is neither a string nor a value
            object typed ``xsd:dateTime`` whose ``"$"`` is one.
    """
    if isinstance(value, str):
        parsed = parse_xsd_datetime(value)
        if parsed is None:
            _warn_rejection(
                f"{value!r} is not an xsd:dateTime and is dropped",
                rec_id,
                attr_name,
                issue=555,
            )
        return parsed
    if (
        isinstance(value, dict)
        and value.keys() == {"$", "type"}
        and isinstance(value["$"], str)
        and isinstance(value["type"], str)
        and valid_qualified_name(bundle, value["type"]) == XSD_DATETIME
        and (parsed := parse_xsd_datetime(value["$"])) is not None
    ):
        return parsed
    raise ProvJSONException(
        f"{_position(rec_id, attr_name)}expected an xsd:dateTime, found {value!r}"
    )


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


# The JSON numbers prov 2.x and earlier wrote in "$", which 3.3.0 still reads;
# prov 1.x on Python 2 wrote a long as xsd:long.
_LEGACY_NUMBER_TYPES = {int: (XSD_INT, XSD_LONG), float: (XSD_DOUBLE,)}

# The keys a PROV-JSON value object may have.
_VALUE_OBJECT_KEYS = frozenset({"$", "type", "lang"})


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


def encode_json_representation(
    value: Any, qname_text: Callable[[object], str] = str
) -> Any:
    """Encode a single non-formal attribute value to its PROV-JSON representation.

    Args:
        value: Attribute value to encode: a :class:`~prov.model.Literal`,
            a :class:`datetime.datetime`, a
            :class:`~prov.identifier.QualifiedName`, another
            :class:`~prov.identifier.Identifier`, a plain ``int``/``float``
            (typed by :func:`~prov.model.canonical_xsd_datatype`), or a
            plain JSON-native value.
        qname_text: Writes a qualified name (the value or a literal's
            datatype); the container's ``_JSONPrefixMap.qname_text`` in
            :func:`encode_json_container`.

    Returns:
        A ``{"$": ..., "type": ...}`` (optionally ``"lang"``) dict for typed
        values, or ``value`` unchanged if it is already natively
        JSON-representable (e.g. plain ``str``/``bool``).
    """
    if isinstance(value, Literal):
        return literal_json_representation(value, qname_text)
    elif isinstance(value, datetime.datetime):
        return {"$": _xsd_datetime_text(value), "type": "xsd:dateTime"}
    elif isinstance(value, QualifiedName):
        # #168: the PROV-JSON submission (§3.1.2) types QualifiedName values
        # as xsd:QName; prov:QUALIFIED_NAME (this library's pre-3.0 choice)
        # remains accepted on input for backward compatibility.
        return {"$": qname_text(value), "type": str(XSD_QNAME)}
    elif isinstance(value, Identifier):
        return {"$": value.uri, "type": "xsd:anyURI"}
    elif (datatype := canonical_xsd_datatype(value)) is not None:
        # int/float: the submission's typedLiteral schema requires a string
        # "$" (#246); the datatype is magnitude-aware for ints (#244/#256).
        return {
            "$": _xsd_double_text(value) if isinstance(value, float) else str(value),
            "type": str(datatype),
        }
    else:
        return value


def decode_json_representation(
    literal: Any,
    bundle: ProvBundle,
    attr_name: str | None = None,
    rec_id: str | None = None,
) -> Any:
    """Decode a single non-formal attribute value from its PROV-JSON representation.

    A value object with a key other than ``"$"``, ``"type"`` and ``"lang"``,
    a ``"$"`` that is not a string, a ``"type"`` that does not resolve, or a
    qualified-name value that does not resolve by its prefix warns with
    :class:`~prov.model.ProvFutureRejectionWarning` and is read as before. A
    number typed as ``prov`` 2.x and earlier wrote it, an integer as
    ``xsd:int`` or ``xsd:long`` or a float as ``xsd:double``, with no
    ``"lang"``, does not warn.

    Args:
        literal: Either a ``{"$": ..., "type": ..., "lang": ...}`` dict (the
            complex/typed representation) or a plain JSON-native value.
        bundle: Bundle used to resolve any ``"type"``/value that is a
            qualified name.
        attr_name: The PROV-JSON attribute key ``literal`` was read from, if
            known. Used only to name the attribute in messages; omit for a
            generic message.
        rec_id: The identifier of the record ``literal`` was read from, if
            known. Used only to name the record in warning messages.

    Returns:
        An :class:`~prov.identifier.Identifier` for ``xsd:anyURI`` values, a
        resolved :class:`~prov.identifier.QualifiedName` for ``xsd:QName`` or
        (legacy) ``prov:QUALIFIED_NAME`` values whose prefix is in scope, an
        opaque :class:`~prov.model.Literal` if it is not, a
        :class:`~prov.model.Literal` for other typed values, or ``literal``
        unchanged if it was not a dict (conversion of plain Python types
        happens later, when the value is added to a record).

    Raises:
        ProvJSONException: If ``literal`` is a dict (the complex/typed
            representation) missing its required ``"$"`` (value) key.
    """
    if isinstance(literal, dict):
        # complex type
        try:
            value = literal["$"]
        except KeyError as exc:
            where = f"attribute {attr_name!r}" if attr_name is not None else "a value"
            raise ProvJSONException(
                f"The typed-literal representation for {where} is missing "
                f'its required "$" (value) key; found {literal!r}'
            ) from exc
        if not literal.keys() <= _VALUE_OBJECT_KEYS:
            for key in sorted(literal.keys() - _VALUE_OBJECT_KEYS, key=str):
                _warn_rejection(
                    f"the value object has the unknown key {key!r}",
                    rec_id,
                    attr_name,
                    issue=529,
                )
        datatype_str: str | None = literal.get("type", None)
        datatype = valid_qualified_name(bundle, datatype_str)
        legacy_types = _LEGACY_NUMBER_TYPES.get(type(value), ())
        if not isinstance(value, str) and (
            datatype not in legacy_types or "lang" in literal
        ):
            _warn_rejection(
                f'the value object\'s "$" is {_json_text(value)}, not a string',
                rec_id,
                attr_name,
                issue=529,
            )
        if datatype_str is not None and datatype is None:
            _warn_rejection(
                f"the datatype {datatype_str!r} does not resolve and is dropped",
                rec_id,
                attr_name,
                issue=552,
            )
        langtag = literal.get("lang", None)
        if datatype == XSD_ANYURI:
            return Identifier(value)
        elif datatype in (PROV_QUALIFIEDNAME, XSD_QNAME):
            # #168: xsd:QName is the submission's type for QualifiedName
            # values; prov:QUALIFIED_NAME is accepted for documents produced
            # by 2.x. If the value's prefix has no in-scope namespace, keep
            # it as an opaque Literal rather than dropping it (#238).
            resolved = valid_qualified_name(bundle, value)
            # A value with a "lang" is no qualified name, and the model logs
            # that it overrides its datatype.
            if langtag is None:
                _check_name_value(bundle, value, resolved, rec_id, attr_name)
            return (
                resolved if resolved is not None else Literal(value, datatype, langtag)
            )
        else:
            # The literal of standard Python types is not converted here
            # It will be automatically converted when added to a record by
            # _auto_literal_conversion()
            return Literal(value, datatype, langtag)
    else:
        # simple type, just return it
        return literal


def literal_json_representation(
    literal: Literal, qname_text: Callable[[object], str] = str
) -> dict[str, str]:
    """Encode a :class:`~prov.model.Literal` to its PROV-JSON dict representation.

    Args:
        literal: Literal to encode.
        qname_text: Writes the datatype; see :func:`encode_json_representation`.

    Returns:
        ``{"$": value, "lang": langtag}`` if the literal has a language tag,
        otherwise ``{"$": value, "type": str(datatype)}``.
    """
    # TODO: QName export
    value, datatype, langtag = literal.value, literal.datatype, literal.langtag
    if langtag:
        return {"$": value, "lang": langtag}
    else:
        return {"$": value, "type": qname_text(datatype)}

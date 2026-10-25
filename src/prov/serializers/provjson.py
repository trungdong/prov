"""PROV-JSON serializer for ProvDocument."""

import datetime
import io
import json
from collections import defaultdict
from collections.abc import Callable
from typing import Any, cast

from prov.constants import *
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import (
    AttributePair,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvException,
    ProvRecord,
    QualifiedNameCandidate,
    first,
    parse_xsd_datetime,
)
from prov.model._values import (
    _xsd_datetime_text,
    python_value_form,
    resolve_name,
)
from prov.serializers import ProvSerializationError, Serializer, _is_text_stream
from prov.serializers._json_common import (
    _add_memberships,
    _json_text,
    _JSONPrefixMap,
    _Kind,
    _position,
    _repeated_key_hook,
)

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


ProvJSONDict = dict[str, dict[str, Any]]


class ProvJSONException(ProvSerializationError):
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
        anon_id = self._cache.get(obj)
        if anon_id is None:
            self._count += 1
            anon_id = self._cache[obj] = Identifier(f"_:{local_prefix}{self._count}")
        return anon_id


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

        Raises:
            ProvSerializationError: If ``self.document`` is ``None``.
        """
        if self.document is None:
            raise ProvSerializationError("No document to serialize.")

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

        Args:
            stream: Input data; binary streams are decoded as UTF-8 first.
            **args: Extra keyword arguments passed through to
                :func:`json.load`.

        Returns:
            The deserialized :class:`~prov.model.ProvDocument`.

        Raises:
            ProvJSONException: If a key is repeated in a JSON object (#532), or
                if the document holds a construct the reader rejects; see
                :func:`decode_json_container`.
        """
        if not _is_text_stream(stream):
            stream = io.StringIO(stream.read().decode("utf-8"))
        hook = _repeated_key_hook(
            ProvJSONException,
            args.pop("object_hook", None),
            args.pop("object_pairs_hook", None),
        )
        container = json.load(stream, object_pairs_hook=hook, **args)
        document = ProvDocument()
        decode_json_document(container, document)
        return document


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

    Used directly with :func:`json.loads`, it does not check for repeated keys;
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
            present), is not a JSON object; or, naming the bundle, if a
            bundle's identifier is not a qualified name or repeats an
            earlier bundle's (the model's error is the ``__cause__``).
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
        try:
            document.add_bundle(
                bundle, _resolve_name(bundle, bundle_id, bundle_id, kind="bundle")
            )
        except ProvException as exc:
            raise ProvJSONException(
                f"{_position(bundle_id, None, kind='bundle')}{exc}"
            ) from exc


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
            keyword; if a record's content is not a JSON object or a list of
            JSON objects; or for any record key, attribute name or value the
            reader rejects. The how-to (``docs/howto/prepare-for-3-3.md``)
            lists the errors 3.3.0 adds, with their messages.
    """
    _expect_json_object(jc, "A PROV-JSON container")
    if "prefix" in jc:
        _decode_namespaces(jc, bundle)

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
        ProvJSONException: If the ``"prefix"`` value is not a JSON object, or
            declares its default namespace under both ``""`` and ``"default"``
            with different IRIs, or holds an IRI that is neither a string nor
            ``null``, or declares a prefix or default namespace the model
            refuses (``__cause__`` holds the :class:`ProvException`).
    """
    prefixes = _expect_json_object(jc["prefix"], 'The "prefix" value')
    if "" in prefixes and "default" in prefixes and prefixes[""] != prefixes["default"]:
        raise ProvJSONException(
            'The "prefix" object declares two different default namespaces, '
            f'under "" ({prefixes[""]!r}) and "default" ({prefixes["default"]!r})'
        )
    try:
        for prefix, uri in prefixes.items():
            if uri is not None and not isinstance(uri, str):
                raise ProvJSONException(
                    f"prefix {prefix!r}, IRI {uri!r}: a namespace IRI must be a string"
                )
            # a null IRI reaches the model, which refuses it as blank
            iri = cast("str", uri)
            if prefix in ("", "default"):
                bundle.set_default_namespace(iri)
            else:
                bundle.add_namespace(Namespace(prefix, iri))
    except ProvException as exc:
        raise ProvJSONException(f"prefix {prefix!r}, IRI {uri!r}: {exc}") from exc
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
            :func:`_decode_record_instance` / :func:`_decode_formal_attribute`);
            or, naming the record, if the model rejects the record's
            identifier, a value or the record itself (the model's error is
            the ``__cause__``).
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
        if not isinstance(rec_id, str):
            raise ProvJSONException(
                f"{_position(str(rec_id), None)}the record key is {_json_text(rec_id)}, "
                "not a string"
            )
        elements = _json_record_elements(content, rec_type_str, rec_id)
        try:
            identifier = (
                None
                if rec_id.startswith("_:")
                else _resolve_name(bundle, rec_id, rec_id)
            )
            for element in elements:
                _decode_record_instance(rec_type, rec_id, identifier, element, bundle)
        except ProvException as exc:
            raise ProvJSONException(f"{_position(rec_id, None)}{exc}") from exc


def _decode_record_instance(
    rec_type: QualifiedName,
    rec_id: str,
    identifier: QualifiedName | None,
    element: dict[str, Any],
    bundle: ProvBundle,
) -> None:
    """Decode one record instance's attributes and add it to ``bundle``.

    Args:
        rec_type: The record's PROV-N record type.
        rec_id: The record's identifier string, for messages.
        identifier: The record's identifier, resolved, or ``None`` for a
            blank-node identifier.
        element: The instance's raw attribute dict, as produced by
            :func:`_json_record_elements`.
        bundle: Bundle to add the decoded record, or one ``hadMember``
            record per member, to.

    Raises:
        ProvJSONException: For an attribute name, a formal attribute value, a
            member or an attribute value the reader rejects; the how-to
            (``docs/howto/prepare-for-3-3.md``) lists the errors 3.3.0 adds,
            with their messages.
    """
    attributes: dict[QualifiedNameCandidate, Any] = {}
    other_attributes: list[AttributePair] = []
    members: list[QualifiedName] | None = None
    is_membership = rec_type == PROV_MEMBERSHIP
    for attr_name, values in element.items():
        if attr_name in PROV_ATTRIBUTES_ID_MAP:
            attr: QualifiedName = PROV_ATTRIBUTES_ID_MAP[attr_name]
        else:
            attr = _resolve_name(bundle, attr_name, rec_id, attr_name)
        if attr in PROV_ATTRIBUTES:
            if is_membership and attr == PROV_ATTR_ENTITY:
                members = _decode_members(rec_id, attr_name, values, bundle)
            else:
                attributes[attr] = _decode_formal_attribute(
                    rec_id, attr_name, attr, values, bundle
                )
        else:
            other_attributes.extend(
                (attr, decode_json_representation(value, bundle, attr_name, rec_id))
                for value in (values if isinstance(values, list) else [values])
            )
    if members is None:
        bundle.new_record(rec_type, identifier, attributes, other_attributes)
    else:
        _add_memberships(bundle, identifier, attributes, other_attributes, members)


def _decode_members(
    rec_id: str, attr_name: str, values: Any, bundle: ProvBundle
) -> list[QualifiedName]:
    """Decode the ``prov:entity`` of a ``hadMember``, a single value or an array.

    Args:
        rec_id: The enclosing record's identifier string, for messages.
        attr_name: The attribute's PROV-JSON key, for messages.
        values: The raw value or JSON array of values.
        bundle: Bundle used to resolve the members' qualified names.

    Returns:
        The resolved members, in the order written.

    Raises:
        ProvJSONException: If ``values`` is an empty JSON array, or if a
            member is null, is not a string, or does not resolve by its prefix
            in scope.
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
    value: Any,
    bundle: ProvBundle,
) -> QualifiedName | datetime.datetime:
    """Decode the value of a formal (:data:`~prov.constants.PROV_ATTRIBUTES`) attribute.

    The members of ``hadMember`` go to :func:`_decode_members` instead.

    Args:
        rec_id: The enclosing record's identifier string, for messages.
        attr_name: The attribute's PROV-JSON key, for messages.
        attr: The formal attribute being decoded.
        value: The raw value read from the PROV-JSON element.
        bundle: Bundle used to resolve a qualified-name value.

    Returns:
        The decoded attribute value.

    Raises:
        ProvJSONException: If ``value`` is a JSON array (#531); if a
            qualified-name attribute's value is null, is not a string, or
            does not resolve by its prefix in scope; or if a time attribute's
            value is not an ``xsd:dateTime`` (see :func:`_decode_time`).
    """
    if isinstance(value, list):
        raise ProvJSONException(
            f"{_position(rec_id, attr_name)}the value is written as an array"
        )
    if attr in PROV_ATTRIBUTE_QNAMES:
        return _decode_name(bundle, value, rec_id, attr_name)
    return _decode_time(rec_id, attr_name, value, bundle)


def _decode_name(
    bundle: ProvBundle, value: Any, rec_id: str, attr_name: str
) -> QualifiedName:
    """Resolve the qualified name a formal attribute or a member refers to.

    Raises:
        ProvJSONException: If ``value`` is null (#528), is not a string
            (#597), or does not resolve by its prefix in scope.
    """
    if value is None:
        raise ProvJSONException(f"{_position(rec_id, attr_name)}the value is null")
    if not isinstance(value, str):
        raise ProvJSONException(
            f"{_position(rec_id, attr_name)}the value is {_json_text(value)}, "
            "not a qualified name"
        )
    return _resolve_name(bundle, value, rec_id, attr_name)


def _resolve_name(
    bundle: ProvBundle,
    text: str,
    rec_id: str | None,
    attr_name: str | None = None,
    *,
    kind: _Kind = "record",
) -> QualifiedName:
    """The qualified name ``text`` resolves to by its prefix in scope, or a
    positioned ``ProvJSONException`` (#516, #551, #599); ``kind`` is
    ``"record"`` or ``"bundle"``."""
    name = resolve_name(bundle, text)
    if isinstance(name, str):
        raise ProvJSONException(_position(rec_id, attr_name, kind) + name)
    return name


def _decode_time(
    rec_id: str, attr_name: str, value: Any, bundle: ProvBundle
) -> datetime.datetime:
    """Decode the value of ``prov:time``, ``prov:startTime`` or ``prov:endTime``.

    Args:
        rec_id: The enclosing record's identifier string, for messages.
        attr_name: The attribute's PROV-JSON key, for messages.
        value: An ``xsd:dateTime`` string, or a value object typed
            ``xsd:dateTime`` whose ``"$"`` is one.
        bundle: Bundle used to resolve the value object's ``"type"``.

    Returns:
        The parsed :class:`~datetime.datetime`.

    Raises:
        ProvJSONException: If ``value`` is null (#528); if it is a value
            object the reader rejects (see :func:`_check_value_object`); or if
            it is neither an ``xsd:dateTime`` string nor a value object typed
            ``xsd:dateTime`` with no ``"lang"`` whose ``"$"`` is one (#555).
    """
    if value is None:
        raise ProvJSONException(f"{_position(rec_id, attr_name)}the value is null")
    text = value
    if isinstance(value, dict):
        text, datatype = _check_value_object(value, bundle, attr_name, rec_id)
        if datatype != XSD_DATETIME or "lang" in value:
            text = None
    if isinstance(text, str) and (parsed := parse_xsd_datetime(text)) is not None:
        return parsed
    raise ProvJSONException(
        f"{_position(rec_id, attr_name)}expected an xsd:dateTime, found {value!r}"
    )


# The JSON numbers prov 2.x and earlier wrote in "$", which 3.3.0 still reads;
# prov 1.x on Python 2 wrote a long as xsd:long.
_LEGACY_NUMBER_TYPES = {int: (XSD_INT, XSD_LONG), float: (XSD_DOUBLE,)}

# The keys a PROV-JSON value object may have.
_VALUE_OBJECT_KEYS = frozenset({"$", "type", "lang"})


def encode_json_representation(
    value: Any, qname_text: Callable[[object], str] = str
) -> Any:
    """Encode a single non-formal attribute value to its PROV-JSON representation.

    Args:
        value: Attribute value to encode: a :class:`~prov.model.Literal`, a
            :class:`~prov.identifier.QualifiedName`, a ``str`` or ``bool``
            (JSON-native), or any other value with an XSD form
            (``python_value_form``, e.g. an ``int``, ``float``, ``Decimal``,
            ``date`` or :class:`datetime.datetime`), which is written as a
            typed value object. A value with no form is passed through.
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
    if isinstance(value, QualifiedName):
        # #168: the PROV-JSON submission (section 3.1.2) types QualifiedName
        # values as xsd:QName; prov:QUALIFIED_NAME (this library's pre-3.0
        # choice) remains accepted on input for backward compatibility.
        return {"$": qname_text(value), "type": str(XSD_QNAME)}
    if isinstance(value, (str, bool)):
        # JSON-native
        return value
    form = python_value_form(value)
    if form is None or form[0] is None:
        # no PROV form, or no lexical form: passed through as it is
        return value
    text, datatype = form
    # int/float/datetime: the submission's typedLiteral schema requires a string "$"
    # (#246); the datatype is magnitude-aware for ints (#244/#256)
    return {"$": text, "type": str(datatype)}


def _check_value_object(
    literal: dict[str, Any],
    bundle: ProvBundle,
    attr_name: str | None,
    rec_id: str | None,
) -> tuple[Any, QualifiedName | None]:
    """Check a PROV-JSON value object and return its ``"$"`` and datatype.

    The checks run in this order: a key other than ``"$"``, ``"type"`` and
    ``"lang"`` (#529); a ``"type"`` that is not a string or does not resolve
    by its prefix in scope (#552); a ``"$"`` that is not a string (#529). A
    number typed as ``prov`` 2.x and earlier wrote it, an integer as
    ``xsd:int`` or ``xsd:long`` or a float as ``xsd:double``, with no
    ``"lang"``, is accepted.

    Args:
        literal: The value object.
        bundle: Bundle used to resolve the ``"type"``.
        attr_name: The attribute key ``literal`` was read from, for
            messages, or ``None``.
        rec_id: The identifier of the record, for messages, or ``None``.

    Returns:
        The ``"$"`` value and the resolved datatype, ``None`` when there is
        no ``"type"``.

    Raises:
        ProvJSONException: As above, or if ``literal`` has no ``"$"`` key.
    """
    try:
        value = literal["$"]
    except KeyError as exc:
        where = f"attribute {attr_name!r}" if attr_name is not None else "a value"
        raise ProvJSONException(
            f"The typed-literal representation for {where} is missing "
            f'its required "$" (value) key; found {literal!r}'
        ) from exc
    position = _position(rec_id, attr_name)
    unknown = sorted(literal.keys() - _VALUE_OBJECT_KEYS, key=str)
    if unknown:
        raise ProvJSONException(
            f"{position}the value object has the unknown key {unknown[0]!r}"
        )
    datatype = None
    if "type" in literal:
        datatype_str = literal["type"]
        if not isinstance(datatype_str, str):
            raise ProvJSONException(
                f'{position}the value object\'s "type" is '
                f"{_json_text(datatype_str)}, not a string"
            )
        datatype = _resolve_name(bundle, datatype_str, rec_id, attr_name)
    legacy_types = _LEGACY_NUMBER_TYPES.get(type(value), ())
    if not isinstance(value, str) and (
        datatype not in legacy_types or "lang" in literal
    ):
        raise ProvJSONException(
            f'{position}the value object\'s "$" is {_json_text(value)}, not a string'
        )
    return value, datatype


def decode_json_representation(
    literal: Any,
    bundle: ProvBundle,
    attr_name: str | None = None,
    rec_id: str | None = None,
) -> Any:
    """Decode a single non-formal attribute value from its PROV-JSON representation.

    Args:
        literal: Either a ``{"$": ..., "type": ..., "lang": ...}`` dict (the
            complex/typed representation) or a plain JSON-native value.
        bundle: Bundle used to resolve a ``"type"`` or a value that is a
            qualified name.
        attr_name: The PROV-JSON attribute key ``literal`` was read from, if
            known. Used only to name the attribute in messages; omit for a
            generic message.
        rec_id: The identifier of the record ``literal`` was read from, if
            known. Used only to name the record in messages.

    Returns:
        A :class:`~prov.model.Literal` for a value object, the resolved
        :class:`~prov.identifier.QualifiedName` for one typed ``xsd:QName``
        or ``prov:QUALIFIED_NAME``, or ``literal`` unchanged if it was not a dict
        (conversion of plain Python types happens later, when the value is
        added to a record).

    Raises:
        ProvJSONException: If ``literal`` is null (#528); if it is a value
            object the reader rejects (see :func:`_check_value_object`); or
            if it is a qualified-name value that does not resolve by its
            prefix in scope.
    """
    if literal is None:
        raise ProvJSONException(f"{_position(rec_id, attr_name)}the value is null")
    if not isinstance(literal, dict):
        # simple type, just return it
        return literal
    value, datatype = _check_value_object(literal, bundle, attr_name, rec_id)
    langtag = literal.get("lang")
    if datatype in (PROV_QUALIFIEDNAME, XSD_QNAME) and langtag is None:
        # #168: xsd:QName is the submission's type for QualifiedName
        # values; prov:QUALIFIED_NAME is accepted for documents produced
        # by 2.x. The value is the QualifiedName itself; one that does not
        # resolve is rejected here, with its position. The "$" is a string,
        # checked above.
        return _resolve_name(bundle, value, rec_id, attr_name)
    # The literal of standard Python types is not converted here. It is
    # converted when added to a record by _auto_literal_conversion().
    return Literal(value, datatype, langtag)


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

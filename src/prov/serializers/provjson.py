"""PROV-JSON serializer for ProvDocument."""

import datetime
import io
import json
import logging
from collections import defaultdict
from typing import Any, cast

from prov import Error
from prov.constants import *
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import (
    Literal,
    ProvBundle,
    ProvDocument,
    ProvRecord,
    QualifiedNameCandidate,
    canonical_xsd_datatype,
    first,
    parse_xsd_datetime,
)
from prov.serializers import Serializer, _is_text_stream

logger = logging.getLogger(__name__)

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


ProvJSONDict = dict[str, dict[str, Any]]


class ProvJSONException(Error):
    """Raised when a PROV-JSON document contains a construct this package cannot decode."""


class AnonymousIDGenerator:
    """Assigns and caches stable blank-node identifiers for unidentified records."""

    def __init__(self) -> None:
        self._cache = {}  # type: dict[ProvRecord, Identifier]
        self._count = 0  # type: int

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
        return cast(ProvDocument, json.load(stream, cls=ProvJSONDecoder, **args))


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
    """``json.JSONDecoder`` that decodes PROV-JSON into a :class:`~prov.model.ProvDocument`."""

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


def encode_json_document(document: ProvDocument) -> ProvJSONDict:
    """Encode a whole :class:`~prov.model.ProvDocument`, including its named bundles.

    Args:
        document: Document to encode.

    Returns:
        The PROV-JSON container dict for ``document``, with each named
        bundle's own encoded container nested under ``container["bundle"]``
        keyed by the bundle's identifier string.
    """
    container = encode_json_container(document)
    for bundle in document.bundles:
        #  encoding the sub-bundle
        bundle_json = encode_json_container(bundle)
        container["bundle"][str(bundle.identifier)] = bundle_json
    return container


def encode_json_container(bundle: ProvBundle) -> ProvJSONDict:
    """Encode a single bundle's namespaces and records to a PROV-JSON container dict.

    Does not recurse into ``bundle``'s own named bundles; see
    :func:`encode_json_document` for encoding a whole document.

    Args:
        bundle: Bundle (or document, treated as its top-level bundle) to
            encode.

    Returns:
        A dict with an optional ``"prefix"`` entry for registered namespaces
        and one entry per PROV-N record-type keyword, each mapping record
        identifiers (real or anonymous) to their encoded attributes.
    """
    container = defaultdict(dict)  # type: dict[str, dict[str, Any]]
    prefixes = {}  # type: dict[str, str]
    for namespace in bundle._namespaces.get_registered_namespaces():
        prefixes[namespace.prefix] = namespace.uri
    if bundle._namespaces._default:
        prefixes["default"] = bundle._namespaces._default.uri
    if prefixes:
        container["prefix"] = prefixes

    id_generator = AnonymousIDGenerator()

    def real_or_anon_id(r: ProvRecord) -> Identifier:
        return r._identifier if r._identifier else id_generator.get_anon_id(r)

    for record in bundle._records:
        rec_type = record.get_type()
        rec_label = PROV_N_MAP[rec_type]
        identifier = str(real_or_anon_id(record))

        record_json = {}  # type: dict[str, Any]
        if record._attributes:
            for attr, values in record._attributes.items():
                if not values:
                    continue
                attr_name = str(attr)
                if attr in PROV_ATTRIBUTE_QNAMES:
                    # TODO: QName export
                    record_json[attr_name] = str(first(values))
                elif attr in PROV_ATTRIBUTE_LITERALS:
                    record_json[attr_name] = first(values).isoformat()  # type: ignore[union-attr]
                else:
                    if len(values) == 1:
                        # single value
                        record_json[attr_name] = encode_json_representation(
                            first(values)
                        )
                    else:
                        # multiple values
                        record_json[attr_name] = [
                            encode_json_representation(value) for value in values
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

    return container


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
    """
    bundles = {}
    if "bundle" in content:
        bundles = content["bundle"]
        del content["bundle"]

    decode_json_container(content, document)

    for bundle_id, bundle_content in bundles.items():
        bundle = ProvBundle(document=document)
        decode_json_container(bundle_content, bundle)
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
        ProvJSONException: If a formal (QualifiedName- or literal-valued)
            attribute has more than one value, other than the documented
            multi-entity ``hadMember`` (membership) hack.
    """
    if "prefix" in jc:
        prefixes = jc["prefix"]
        for prefix, uri in prefixes.items():
            if prefix != "default":
                bundle.add_namespace(Namespace(prefix, uri))
            else:
                bundle.set_default_namespace(uri)
        del jc["prefix"]

    for rec_type_str in jc:
        rec_type = PROV_RECORD_IDS_MAP[rec_type_str]
        for rec_id, content in jc[rec_type_str].items():
            #  If it is a dict, there is only one element: make a singleton list.
            #  Otherwise, it is expected to already be a list of dictionaries.
            elements = [content] if hasattr(content, "items") else content

            for element in elements:
                attributes = {}  # type: dict[QualifiedNameCandidate, Any]
                other_attributes = []  # type: list[tuple[QualifiedNameCandidate, Any]]
                # this is for the multiple-entity membership hack to come
                membership_extra_members = None
                for attr_name, values in element.items():
                    attr = (
                        PROV_ATTRIBUTES_ID_MAP[attr_name]
                        if attr_name in PROV_ATTRIBUTES_ID_MAP
                        else bundle.mandatory_valid_qname(attr_name)
                    )  # type: QualifiedName
                    if attr in PROV_ATTRIBUTES:
                        if isinstance(values, list):
                            # only one value is allowed
                            if len(values) > 1:
                                # unless it is the membership hack
                                if (
                                    rec_type == PROV_MEMBERSHIP
                                    and attr == PROV_ATTR_ENTITY
                                ):
                                    # This is a membership relation with
                                    # multiple entities
                                    # HACK: create multiple membership
                                    # relations, one for each entity

                                    # Store all the extra entities
                                    membership_extra_members = values[1:]
                                    # Create the first membership relation as
                                    # normal for the first entity
                                    value = values[0]
                                else:
                                    error_msg = (
                                        "The prov package does not support PROV"
                                        " attributes having multiple values."
                                    )
                                    logger.error(error_msg)
                                    raise ProvJSONException(error_msg)
                            else:
                                value = values[0]
                        else:
                            value = values
                        value = (
                            valid_qualified_name(bundle, value)
                            if attr in PROV_ATTRIBUTE_QNAMES
                            else parse_xsd_datetime(value)
                        )
                        attributes[attr] = value
                    else:
                        if isinstance(values, list):
                            other_attributes.extend(
                                (attr, decode_json_representation(value, bundle))
                                for value in values
                            )
                        else:
                            # single value
                            other_attributes.append(
                                (attr, decode_json_representation(values, bundle))
                            )
                bundle.new_record(rec_type, rec_id, attributes, other_attributes)
                # HACK: creating extra (unidentified) membership relations
                if membership_extra_members:
                    collection = attributes[PROV_ATTR_COLLECTION]
                    for member in membership_extra_members:
                        bundle.membership(
                            collection, bundle.mandatory_valid_qname(member)
                        )


def encode_json_representation(value: Any) -> Any:
    """Encode a single non-formal attribute value to its PROV-JSON representation.

    Args:
        value: Attribute value to encode: a :class:`~prov.model.Literal`,
            a :class:`datetime.datetime`, a
            :class:`~prov.identifier.QualifiedName`, another
            :class:`~prov.identifier.Identifier`, a plain ``int``/``float``
            (typed by :func:`~prov.model.canonical_xsd_datatype`), or a
            plain JSON-native value.

    Returns:
        A ``{"$": ..., "type": ...}`` (optionally ``"lang"``) dict for typed
        values, or ``value`` unchanged if it is already natively
        JSON-representable (e.g. plain ``str``/``bool``).
    """
    if isinstance(value, Literal):
        return literal_json_representation(value)
    elif isinstance(value, datetime.datetime):
        return {"$": value.isoformat(), "type": "xsd:dateTime"}
    elif isinstance(value, QualifiedName):
        # TODO Manage prefix in the whole structure consistently
        # TODO QName export
        return {"$": str(value), "type": PROV_QUALIFIEDNAME._str}
    elif isinstance(value, Identifier):
        return {"$": value.uri, "type": "xsd:anyURI"}
    elif (datatype := canonical_xsd_datatype(value)) is not None:
        # int/float: the submission's typedLiteral schema requires a string
        # "$" (#246); the datatype is magnitude-aware for ints (#244/#256).
        return {
            "$": repr(value) if isinstance(value, float) else str(value),
            "type": str(datatype),
        }
    else:
        return value


def decode_json_representation(literal: Any, bundle: ProvBundle) -> Any:
    """Decode a single non-formal attribute value from its PROV-JSON representation.

    Args:
        literal: Either a ``{"$": ..., "type": ..., "lang": ...}`` dict (the
            complex/typed representation) or a plain JSON-native value.
        bundle: Bundle used to resolve any ``"type"``/value that is a
            qualified name.

    Returns:
        An :class:`~prov.identifier.Identifier` for ``xsd:anyURI`` values, a
        resolved :class:`~prov.identifier.QualifiedName` for
        ``prov:QUALIFIED_NAME`` values, a :class:`~prov.model.Literal` for
        other typed values, or ``literal`` unchanged if it was not a dict
        (conversion of plain Python types happens later, when the value is
        added to a record).
    """
    if isinstance(literal, dict):
        # complex type
        value = literal["$"]
        datatype_str = literal.get("type", None)  # type: str | None
        datatype = valid_qualified_name(bundle, datatype_str)
        langtag = literal.get("lang", None)
        if datatype == XSD_ANYURI:
            return Identifier(value)
        elif datatype == PROV_QUALIFIEDNAME:
            return valid_qualified_name(bundle, value)
        else:
            # The literal of standard Python types is not converted here
            # It will be automatically converted when added to a record by
            # _auto_literal_conversion()
            return Literal(value, datatype, langtag)
    else:
        # simple type, just return it
        return literal


def literal_json_representation(literal: Literal) -> dict[str, str]:
    """Encode a :class:`~prov.model.Literal` to its PROV-JSON dict representation.

    Args:
        literal: Literal to encode.

    Returns:
        ``{"$": value, "lang": langtag}`` if the literal has a language tag,
        otherwise ``{"$": value, "type": str(datatype)}``.
    """
    # TODO: QName export
    value, datatype, langtag = literal.value, literal.datatype, literal.langtag
    if langtag:
        return {"$": value, "lang": langtag}
    else:
        return {"$": value, "type": str(datatype)}

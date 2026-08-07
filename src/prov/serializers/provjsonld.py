"""PROV-JSONLD serializer for ProvDocument.

Implements the W3C member submission "A JSON-LD Representation for the PROV
Data Model" (https://www.w3.org/submissions/prov-jsonld/): the canonical
compacted shape only, one JSON object per PROV-DM statement in ``@graph``.
"""

import datetime
import io
import json
from importlib.resources import files
from typing import Any

from prov import Error
from prov.constants import (
    PROV_ATTRIBUTE_LITERALS,
    PROV_BUNDLE,
    PROV_ENTITY,
    PROV_LABEL,
    PROV_LOCATION,
    PROV_MENTION,
    PROV_N_MAP,
    PROV_QUALIFIEDNAME,
    PROV_ROLE,
    PROV_TYPE,
    PROV_VALUE,
    XSD_ANYURI,
    XSD_QNAME,
)
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import (
    PROV_REC_CLS,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvElement,
    ProvRecord,
    canonical_xsd_datatype,
    first,
    parse_xsd_datetime,
)
from prov.serializers import Serializer, _is_text_stream

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

#: The context URL the submission's own examples reference; emitted by default.
JSONLD_CONTEXT_URL = "https://openprovenance.org/prov-jsonld/context.jsonld"

#: JSON-LD ``@type`` term (the record type's local part) -> record type.
#: ``Mention`` is deliberately absent -- the submission defines no such term --
#: and ``Bundle`` is handled structurally (nested ``@graph``), not via this map.
JSONLD_TYPE_TERMS: dict[str, QualifiedName] = {
    rec_type.localpart: rec_type
    for rec_type in PROV_N_MAP
    if rec_type not in (PROV_MENTION, PROV_BUNDLE)
}

#: PROV special attributes -> their unprefixed context terms (and back).
SPECIAL_ATTR_TERMS: dict[QualifiedName, str] = {
    PROV_TYPE: "type",
    PROV_LABEL: "label",
    PROV_ROLE: "role",
    PROV_LOCATION: "location",
    PROV_VALUE: "value",
}
SPECIAL_TERM_ATTRS: dict[str, QualifiedName] = {
    term: attr for attr, term in SPECIAL_ATTR_TERMS.items()
}
#: Special terms typed ``@id`` in the context: their values are bare
#: qualified-name strings, not value objects.
ID_TYPED_TERMS = frozenset({"type", "role", "location"})


class ProvJSONLDException(Error):
    """Raised when a document cannot be written as, or read from, PROV-JSONLD."""


def _load_vendored_context() -> dict[str, Any]:
    """Return the vendored submission context (the ``@context`` object).

    Returns:
        The ``@context`` object read from the vendored
        ``prov-jsonld-context.jsonld`` resource shipped alongside this module.
    """
    text = files("prov.serializers").joinpath("prov-jsonld-context.jsonld").read_text()
    result: dict[str, Any] = json.loads(text)["@context"]
    return result


def _encode_namespaces(bundle: ProvBundle) -> dict[str, str]:
    """Encode a bundle's registered namespaces as a JSON-LD context object.

    Args:
        bundle: Bundle (or document) whose namespaces are encoded.

    Returns:
        A dict mapping each registered prefix to its namespace URI, plus an
        ``"@vocab"`` entry if ``bundle`` has a default namespace. Empty if
        ``bundle`` has neither registered nor a default namespace.
    """
    ns_map = {ns.prefix: ns.uri for ns in bundle.get_registered_namespaces()}
    default_ns = bundle.get_default_namespace()
    if default_ns is not None:
        ns_map["@vocab"] = default_ns.uri
    return ns_map


def encode_jsonld_value(value: Any, term: str) -> Any:
    """Encode one non-formal attribute value as a JSON-LD array member.

    Args:
        value: Attribute value to encode: a
            :class:`~prov.identifier.QualifiedName`, a
            :class:`~prov.model.Literal`, a :class:`datetime.datetime`,
            another :class:`~prov.identifier.Identifier`, a plain ``bool``,
            ``str``, ``int``/``float`` (typed by
            :func:`~prov.model.canonical_xsd_datatype`), or another plain
            JSON-native value.
        term: The unprefixed JSON-LD term ``value`` is being encoded under
            (e.g. ``"type"``, ``"ex:price"``), used to decide whether a
            :class:`~prov.identifier.QualifiedName` value is emitted as a
            bare string (``@id``-typed terms, see :data:`ID_TYPED_TERMS`) or
            as a typed value object.

    Returns:
        A bare qualified-name string for ``@id``-typed terms, or a
        ``{"@value": ..., "@type"/"@language": ...}`` value object.
    """
    if isinstance(value, QualifiedName):
        if term in ID_TYPED_TERMS:
            return str(value)  # @id-typed term: bare qualified-name string
        return {"@value": str(value), "@type": str(XSD_QNAME)}
    if isinstance(value, Literal):
        if value.langtag:
            return {"@value": value.value, "@language": value.langtag}
        return {"@value": value.value, "@type": str(value.datatype)}
    if isinstance(value, datetime.datetime):
        return {"@value": value.isoformat(), "@type": "xsd:dateTime"}
    if isinstance(value, Identifier):
        return {"@value": value.uri, "@type": "xsd:anyURI"}
    if isinstance(value, bool):
        return {"@value": "true" if value else "false", "@type": "xsd:boolean"}
    if isinstance(value, str):
        return {"@value": value}
    datatype = canonical_xsd_datatype(value)
    if datatype is not None:  # int / float, magnitude-aware (#244/#256)
        return {
            "@value": repr(value) if isinstance(value, float) else str(value),
            "@type": str(datatype),
        }
    return {"@value": str(value)}


def encode_jsonld_statement(record: ProvRecord) -> dict[str, Any]:
    """Encode one PROV record as its submission §4 statement object.

    Args:
        record: Record to encode.

    Returns:
        The statement object: ``"@type"`` (the record type's local part),
        an optional ``"@id"`` (if the record is identified), one entry per
        formal attribute (a single string/ISO-8601 value), and one entry
        per non-formal attribute (an array of encoded values).

    Raises:
        ProvJSONLDException: If ``record`` is a :class:`~prov.model.ProvMention`
            -- the submission defines no term for ``mentionOf``.
    """
    rec_type = record.get_type()
    if rec_type == PROV_MENTION:
        raise ProvJSONLDException(
            f"PROV-JSONLD cannot represent mentionOf ({record.identifier}): "
            "the submission defines no Mention term; see "
            "docs/reference/conformance.md"
        )
    obj: dict[str, Any] = {"@type": rec_type.localpart}
    if record.identifier is not None:
        obj["@id"] = str(record.identifier)
    for attr in record.FORMAL_ATTRIBUTES:
        values = record._attributes.get(attr)
        if values:
            value = first(values)
            obj[attr.localpart] = (
                value.isoformat()  # type: ignore[union-attr]
                if attr in PROV_ATTRIBUTE_LITERALS
                else str(value)
            )
    for attr, values in record._attributes.items():
        if attr in record.FORMAL_ATTRIBUTES or not values:
            continue
        term = SPECIAL_ATTR_TERMS.get(attr, str(attr))
        if attr == PROV_VALUE and rec_type != PROV_ENTITY:
            term = str(attr)  # the schema scopes bare "value" to Entity
        obj[term] = [encode_jsonld_value(v, term) for v in values]
    return obj


def encode_jsonld_container(bundle: ProvBundle) -> list[dict[str, Any]]:
    """Encode a bundle's (or document's own) records as a ``@graph`` array.

    Args:
        bundle: Bundle (or document, treated as its top-level bundle) whose
            own records (not its named bundles) are encoded.

    Returns:
        A list with one statement object (see :func:`encode_jsonld_statement`)
        per record.
    """
    return [encode_jsonld_statement(record) for record in bundle._records]


def encode_jsonld_document(document: ProvDocument, context: str) -> dict[str, Any]:
    """Encode a whole document, including its named bundles, as the §4 document object.

    Args:
        document: Document to encode.
        context: ``"url"`` to reference the canonical context by URL, or
            ``"embed"`` to inline the vendored context object.

    Returns:
        The document object: ``"@context"`` (the document's namespaces, if
        any, followed by the context URL/object) and ``"@graph"`` (the
        document's own records plus one nested ``{"@type": "Bundle", ...}``
        object per named bundle).
    """
    context_tail: Any = (
        JSONLD_CONTEXT_URL if context == "url" else _load_vendored_context()
    )
    ns_map = _encode_namespaces(document)
    graph = encode_jsonld_container(document)
    for bundle in document.bundles:
        bundle_ns = _encode_namespaces(bundle)
        graph.append(
            {
                "@type": "Bundle",
                "@id": str(bundle.identifier),
                "@context": [bundle_ns] if bundle_ns else [],
                "@graph": encode_jsonld_container(bundle),
            }
        )
    context_list: list[Any] = [ns_map] if ns_map else []
    context_list.append(context_tail)
    return {"@context": context_list, "@graph": graph}


def _expect_object(value: Any, description: str) -> dict[str, Any]:
    """Check that a decoded JSON value is an object (a Python ``dict``).

    Args:
        value: Value to check.
        description: Human-readable name of what ``value`` represents (e.g.
            ``"A @graph statement"``), used to build the exception message.

    Returns:
        ``value`` unchanged, for convenient chaining.

    Raises:
        ProvJSONLDException: If ``value`` is not a ``dict``.
    """
    if not isinstance(value, dict):
        raise ProvJSONLDException(
            f"{description} must be a JSON object; found "
            f"{type(value).__name__}: {value!r}"
        )
    return value


def _decode_context(context: Any, bundle: ProvBundle) -> None:
    """Register namespaces from a submission §4 ``@context`` on ``bundle``.

    Args:
        context: The ``@context`` value: a single entry or a JSON array of
            entries, as produced by :func:`encode_jsonld_document` /
            :func:`encode_jsonld_container`.
        bundle: Bundle (or document) to register the decoded namespaces on.

    String items (the context URL) and dict items containing dict values (an
    embedded copy of the submission context, whose terms are already known
    to this library via the built-in ``prov``/``xsd`` namespaces) are
    skipped; namespace maps -- dicts whose values are all strings -- are
    registered, with ``@vocab`` as the default namespace and ``@version``
    ignored.

    Raises:
        ProvJSONLDException: If a ``@context`` entry is neither a string nor
            a JSON object.
    """
    if not isinstance(context, list):
        context = [context]
    for item in context:
        if isinstance(item, str):
            continue
        item = _expect_object(item, "A @context entry")
        if any(isinstance(v, dict) for v in item.values()):
            continue  # embedded submission context, not a namespace map
        for prefix, uri in item.items():
            if prefix == "@version":
                continue
            if prefix == "@vocab":
                bundle.set_default_namespace(uri)
            else:
                bundle.add_namespace(Namespace(prefix, uri))


def _strip_prov_prefix(term: str) -> str:
    """Return ``term`` with a leading ``"prov:"`` (ProvToolbox spelling) removed.

    Args:
        term: The JSON-LD term to strip.

    Returns:
        ``term`` without its ``"prov:"`` prefix, or unchanged if it has none.
    """
    return term[5:] if term.startswith("prov:") else term


def decode_jsonld_value(value: Any, bundle: ProvBundle, term: str) -> Any:
    """Decode one member of a non-formal attribute's value array.

    Mirrors :func:`~prov.serializers.provjson.decode_json_representation`'s
    #168/#238 behaviour: an ``xsd:QName``/``prov:QUALIFIED_NAME``-typed value
    (or an ``@id``-typed term's bare string) whose prefix has no in-scope
    namespace is kept as an opaque :class:`~prov.model.Literal` rather than
    dropped.

    Args:
        value: The raw JSON-LD value: a bare string (for
            :data:`ID_TYPED_TERMS`) or a ``{"@value": ..., ...}`` value
            object.
        bundle: Bundle used to resolve any qualified-name value.
        term: The unprefixed JSON-LD term ``value`` was read from (e.g.
            ``"type"``, ``"ex:price"``), used to decide how a bare string is
            interpreted.

    Returns:
        The resolved :class:`~prov.identifier.QualifiedName` for an
        ``@id``-typed term or an ``xsd:QName``/``prov:QUALIFIED_NAME``-typed
        value object, an :class:`~prov.identifier.Identifier` for an
        ``xsd:anyURI``-typed value object, a language-tagged or datatyped
        :class:`~prov.model.Literal`, or the plain decoded text.

    Raises:
        ProvJSONLDException: If ``value`` is neither a string nor a JSON
            object, or if a value object is missing its required
            ``"@value"`` key.
    """
    if isinstance(value, str):
        if term in ID_TYPED_TERMS:
            resolved = bundle.valid_qualified_name(value)
            return resolved if resolved is not None else Literal(value, XSD_QNAME)
        return value
    value = _expect_object(value, f"A value of {term!r}")
    try:
        text = value["@value"]
    except KeyError as exc:
        raise ProvJSONLDException(
            f'A value object for {term!r} is missing its required "@value" '
            f"key; found {value!r}"
        ) from exc
    if "@language" in value:
        return Literal(text, langtag=value["@language"])
    datatype_str = value.get("@type")
    if datatype_str is None:
        return text
    datatype = bundle.valid_qualified_name(datatype_str)
    if datatype == XSD_ANYURI:
        return Identifier(text)
    if datatype in (XSD_QNAME, PROV_QUALIFIEDNAME):
        resolved = bundle.valid_qualified_name(text)
        return resolved if resolved is not None else Literal(text, datatype)
    return Literal(text, datatype)


def _decode_formal_qname(
    bundle: ProvBundle, value: Any, type_term: str, key: str
) -> QualifiedName:
    """Resolve a formal QName-valued attribute's raw value, requiring success.

    Args:
        bundle: Bundle used to resolve ``value``.
        value: The raw (string) value read from the statement object.
        type_term: The enclosing statement's ``@type``, used in the
            exception message.
        key: The attribute's JSON-LD key, used in the exception message.

    Returns:
        The resolved :class:`~prov.identifier.QualifiedName`.

    Raises:
        ProvJSONLDException: If ``value`` cannot be resolved to a qualified
            name (e.g. its prefix has no in-scope namespace).
    """
    resolved = bundle.valid_qualified_name(value)
    if resolved is None:
        raise ProvJSONLDException(
            f"The {key!r} attribute of {type_term} is not a valid qualified "
            f"name: {value!r}"
        )
    return resolved


def decode_jsonld_statement(item: dict[str, Any], bundle: ProvBundle) -> None:
    """Decode one submission §4 statement object and add it to ``bundle``.

    Args:
        item: The statement object (one ``@graph`` entry), as produced by
            :func:`encode_jsonld_statement`.
        bundle: Bundle to add the decoded record to.

    Raises:
        ProvJSONLDException: If ``item``'s ``"@type"`` is missing, is not a
            recognised PROV-JSONLD statement type (including ``"Mention"``,
            which the submission defines no term for), or names an element
            type without an ``"@id"``; if a formal attribute's value is an
            array (formal attributes take a single value) or cannot be
            resolved to a qualified name; or if a non-formal attribute's
            value is not a JSON array.
    """
    type_term = item.get("@type")
    if not isinstance(type_term, str):
        raise ProvJSONLDException(
            f'Every @graph statement needs a string "@type"; found {item!r}'
        )
    rec_type = JSONLD_TYPE_TERMS.get(_strip_prov_prefix(type_term))
    if rec_type is None:
        raise ProvJSONLDException(
            f"{type_term!r} is not a PROV-JSONLD statement type"
            + (
                " (the submission defines no Mention term)"
                if _strip_prov_prefix(type_term) == "Mention"
                else ""
            )
        )
    cls = PROV_REC_CLS[rec_type]
    formal_by_term = {attr.localpart: attr for attr in cls.FORMAL_ATTRIBUTES}
    rec_id = item.get("@id")
    if rec_id is None and issubclass(cls, ProvElement):
        raise ProvJSONLDException(
            f'A {type_term} statement requires an "@id"; found {item!r}'
        )
    attributes: dict[Any, Any] = {}
    other_attributes: list[Any] = []
    for key, value in item.items():
        if key in ("@type", "@id"):
            continue
        attr = formal_by_term.get(_strip_prov_prefix(key))
        if attr is not None and not isinstance(value, list):
            if attr in PROV_ATTRIBUTE_LITERALS:
                attributes[attr] = parse_xsd_datetime(value)
            else:
                attributes[attr] = _decode_formal_qname(bundle, value, type_term, key)
            continue
        if attr is not None:
            raise ProvJSONLDException(
                f"The formal attribute {key!r} of {type_term} takes a single "
                f"value, not an array; found {value!r}"
            )
        stripped = _strip_prov_prefix(key)
        term = stripped if stripped in SPECIAL_TERM_ATTRS else key
        qname = SPECIAL_TERM_ATTRS.get(term) or bundle.mandatory_valid_qname(key)
        if not isinstance(value, list):
            raise ProvJSONLDException(
                f"The attribute {key!r} must be an array of values; found {value!r}"
            )
        other_attributes.extend(
            (qname, decode_jsonld_value(v, bundle, term)) for v in value
        )
    bundle.new_record(rec_type, rec_id, attributes, other_attributes)


def decode_jsonld_document(container: Any, document: ProvDocument) -> None:
    """Decode a whole PROV-JSONLD document object, including named bundles.

    Args:
        container: The document object, as produced by
            :func:`encode_jsonld_document` (or parsed JSON in that shape).
        document: Document to populate.

    Raises:
        ProvJSONLDException: If ``container`` is not a JSON object; if it is
            missing ``"@context"`` or ``"@graph"``; if ``"@graph"`` is not a
            JSON array; if a ``@graph`` entry is not a JSON object; if a
            nested bundle object is missing its required ``"@id"``; or (from
            further down the call chain) if a statement is malformed (see
            :func:`decode_jsonld_statement`).
    """
    container = _expect_object(container, "A PROV-JSONLD document")
    if "@graph" not in container or "@context" not in container:
        raise ProvJSONLDException(
            'A PROV-JSONLD document requires both "@context" and "@graph"; '
            f"found keys {sorted(container)!r}"
        )
    _decode_context(container["@context"], document)
    graph = container["@graph"]
    if not isinstance(graph, list):
        raise ProvJSONLDException(
            f'"@graph" must be a JSON array; found {type(graph).__name__}'
        )
    bundles: list[dict[str, Any]] = []
    for item in graph:
        item = _expect_object(item, "A @graph statement")
        type_term = item.get("@type")
        is_bundle = (
            isinstance(type_term, str) and _strip_prov_prefix(type_term) == "Bundle"
        ) or "@graph" in item
        if is_bundle:
            bundles.append(item)
        else:
            decode_jsonld_statement(item, document)
    for item in bundles:
        if "@id" not in item:
            raise ProvJSONLDException(f'A Bundle requires an "@id"; found {item!r}')
        bundle = ProvBundle(document=document)
        _decode_context(item.get("@context", []), bundle)
        for stmt in item.get("@graph", []):
            decode_jsonld_statement(_expect_object(stmt, "A bundle statement"), bundle)
        document.add_bundle(bundle, bundle.valid_qualified_name(item["@id"]))


class ProvJSONLDSerializer(Serializer):
    """PROV-JSONLD serializer for :class:`~prov.model.ProvDocument`."""

    def serialize(self, stream: io.IOBase, **args: Any) -> None:
        """Serialize ``self.document`` to `PROV-JSONLD <https://www.w3.org/submissions/prov-jsonld/>`_.

        Args:
            stream: Stream to write the output to. Text streams receive the
                JSON text directly; other (binary) streams receive it
                UTF-8-encoded.
            **args: ``context`` (``"url"`` (default) or ``"embed"``) selects
                whether ``@context`` references the canonical context by URL
                or inlines the vendored context object; any other value
                raises :class:`ValueError`. Remaining keyword arguments are
                passed through to :func:`json.dump`.

        Raises:
            ValueError: If ``context`` is neither ``"url"`` nor ``"embed"``.
            ProvJSONLDException: If the document contains a
                :class:`~prov.model.ProvMention` record.
        """
        context = args.pop("context", "url")
        if context not in ("url", "embed"):
            raise ValueError(f'context must be "url" or "embed"; got {context!r}')
        assert self.document is not None
        container = encode_jsonld_document(self.document, context)
        buf = io.StringIO()
        try:
            json.dump(container, buf, **args)
            buf.seek(0, 0)
            if _is_text_stream(stream):
                stream.write(buf.read())
            else:
                stream.write(buf.read().encode("utf-8"))
        finally:
            buf.close()

    def deserialize(self, stream: io.IOBase, **args: Any) -> ProvDocument:
        """Deserialize a `PROV-JSONLD <https://www.w3.org/submissions/prov-jsonld/>`_
        stream into a :class:`~prov.model.ProvDocument`.

        Only the submission's canonical compacted shape (one JSON object per
        PROV-DM statement in ``@graph``) is accepted; see the module
        docstring.

        Args:
            stream: Input data; binary streams are decoded as UTF-8 first.
            **args: Extra keyword arguments passed through to
                :func:`json.load`.

        Returns:
            The deserialized :class:`~prov.model.ProvDocument`.

        Raises:
            ProvJSONLDException: If ``stream`` does not hold a well-formed
                PROV-JSONLD document (see :func:`decode_jsonld_document`).
        """
        if not _is_text_stream(stream):
            stream = io.StringIO(stream.read().decode("utf-8"))
        container = json.load(stream, **args)
        document = ProvDocument()
        decode_jsonld_document(container, document)
        return document

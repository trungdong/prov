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
    PROV_ROLE,
    PROV_TYPE,
    PROV_VALUE,
    XSD_QNAME,
)
from prov.identifier import Identifier, QualifiedName
from prov.model import (
    Literal,
    ProvBundle,
    ProvDocument,
    ProvRecord,
    canonical_xsd_datatype,
    first,
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
        """Not yet implemented.

        Args:
            stream: Input data (unused).
            **args: Format-specific deserialization options (unused).

        Raises:
            NotImplementedError: Always; PROV-JSONLD decoding is a later step.
        """
        raise NotImplementedError

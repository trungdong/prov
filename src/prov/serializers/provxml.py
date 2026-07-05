"""PROV-XML serializer for ProvDocument."""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

import datetime
import io
import logging
import warnings
from typing import Any

from lxml import etree

import prov
import prov.identifier
from prov.constants import *
from prov.model import DEFAULT_NAMESPACES, sorted_attributes
from prov.serializers import Serializer

__author__ = "Lion Krischer"
__email__ = "krischer@geophysik.uni-muenchen.de"

logger = logging.getLogger(__name__)

# Create a dictionary containing all top-level PROV XML elements for an easy
# mapping.
FULL_NAMES_MAP = dict(PROV_N_MAP)
FULL_NAMES_MAP.update(ADDITIONAL_N_MAP)
"""Maps every PROV record/subtype QualifiedName (including PROV-XML's
top-level subtypes from :data:`~prov.constants.ADDITIONAL_N_MAP`) to its
PROV-XML element name."""
# Inverse mapping.
FULL_PROV_RECORD_IDS_MAP = {
    FULL_NAMES_MAP[rec_type_id]: rec_type_id for rec_type_id in FULL_NAMES_MAP
}
"""Inverse of :data:`FULL_NAMES_MAP`: maps each PROV-XML element name back to
its record/subtype QualifiedName."""

XML_XSD_URI = "http://www.w3.org/2001/XMLSchema"


class ProvXMLException(prov.Error):
    """Raised when a PROV-XML document cannot be serialized or parsed by this package."""

    pass


class ProvXMLSerializer(Serializer):
    """PROV-XML serializer for :class:`~prov.model.ProvDocument`"""

    def serialize(
        self, stream: io.IOBase, force_types: bool = False, **kwargs: Any
    ) -> None:
        """Serialize ``self.document`` to `PROV-XML <http://www.w3.org/TR/prov-xml/>`_.

        Args:
            stream: Stream to write the output to. Text streams receive the
                XML text directly; other (binary) streams are written to via
                ``lxml``'s own UTF-8 encoding.
            force_types: If ``True``, force ``xsi:type`` to be written for
                most attributes, including non-PROV-namespaced ones. Off by
                default, meaning ``xsi:type`` attributes are only set for
                ``prov:type``, ``prov:location``, and ``prov:value`` as done
                in the official PROV-XML specification. Regardless of this
                flag, the type is always set if the Python type of the value
                requires it (e.g. ``bool``, ``float``, ``datetime``). A good
                default; it should rarely require changing.
            **kwargs: Unused; accepted for interface compatibility with
                :meth:`~prov.serializers.Serializer.serialize`.

        Raises:
            ProvXMLException: If ``self.document`` is ``None``.
        """
        if self.document is None:
            raise ProvXMLException("No document to serialize.")

        xml_root = self.serialize_bundle(bundle=self.document, force_types=force_types)
        for bundle in self.document.bundles:
            self.serialize_bundle(
                bundle=bundle, element=xml_root, force_types=force_types
            )
        # No encoding must be specified when writing to String object which
        # does not have the concept of an encoding as it should already
        # represent unicode code points.
        et = etree.ElementTree(xml_root)
        if isinstance(stream, io.TextIOBase):
            stream.write(
                etree.tostring(et, xml_declaration=True, pretty_print=True).decode(
                    "utf-8"
                )
            )
        else:
            et.write(stream, pretty_print=True, xml_declaration=True, encoding="UTF-8")  # type: ignore[arg-type]

    def serialize_bundle(
        self,
        bundle: prov.model.ProvBundle,
        element: etree._Element | None = None,
        force_types: bool = False,
    ) -> etree._Element:
        """Serialize a bundle or document to a PROV-XML etree element.

        Namespaces are collected from ``self.document`` (the top-level
        document being serialized) plus ``bundle``'s own namespaces and the
        package's default namespaces.

        Args:
            bundle: The bundle or document to serialize.
            element: Parent XML element to attach a ``<prov:bundleContent>``
                child to. If ``None``, a new top-level ``<prov:document>``
                element is created and returned instead.
            force_types: See :meth:`serialize`.

        Returns:
            The XML element created for ``bundle``: a new
            ``<prov:document>`` element if ``element`` was ``None``, or the
            ``<prov:bundleContent>`` child added to ``element`` otherwise.
        """
        # Build the namespace map for lxml and attach it to the root XML
        # element.
        nsmap = {
            ns.prefix: ns.uri
            for ns in self.document._namespaces.get_registered_namespaces()  # type: ignore[union-attr]
        }  # type: dict[str, str]
        if self.document._namespaces._default:  # type: ignore[union-attr]
            # TODO: Check if the below works as expected.
            nsmap[None] = self.document._namespaces._default.uri  # type: ignore[union-attr, index]
        for namespace in bundle.namespaces:
            if namespace not in nsmap:
                nsmap[namespace.prefix] = namespace.uri

        for _key, value in DEFAULT_NAMESPACES.items():
            uri = value.uri
            if value.prefix == "xsd":
                # The XSD namespace for some reason has no hash at the end
                # for PROV XML, but for all other serializations it does.
                uri = uri.rstrip("#")
            nsmap[value.prefix] = uri

        if element is not None:
            xml_bundle_root = etree.SubElement(
                element, _ns_prov("bundleContent"), nsmap=nsmap
            )
        else:
            xml_bundle_root = etree.Element(_ns_prov("document"), nsmap=nsmap)

        if bundle.identifier:
            xml_bundle_root.attrib[_ns_prov("id")] = str(bundle.identifier)

        for record in bundle._records:
            rec_type = record.get_type()
            identifier = str(record._identifier) if record._identifier else None

            attrs = {_ns_prov("id"): identifier} if identifier else None

            # Derive the record label from its attributes which is sometimes
            # needed.
            attributes = record.attributes
            rec_label = self._derive_record_label(rec_type, attributes)

            elem = etree.SubElement(xml_bundle_root, _ns_prov(rec_label), attrs)

            for attr, value in sorted_attributes(rec_type, attributes):
                subelem = etree.SubElement(
                    elem, _ns(attr.namespace.uri, attr.localpart)
                )
                if isinstance(value, prov.model.Literal):
                    if (
                        value.datatype is not None
                        and value.datatype != PROV_INTERNATIONALIZEDSTRING
                    ):
                        subelem.attrib[_ns_xsi("type")] = (
                            f"{value.datatype.namespace.prefix}:{value.datatype.localpart}"
                        )
                    if value.langtag is not None:
                        subelem.attrib[_ns_xml("lang")] = value.langtag
                    v = value.value
                elif isinstance(value, prov.identifier.QualifiedName):
                    if attr not in PROV_ATTRIBUTE_QNAMES:
                        subelem.attrib[_ns_xsi("type")] = "xsd:QName"
                    v = str(value)
                elif isinstance(value, datetime.datetime):
                    v = value.isoformat()
                else:
                    v = str(value)

                # xsd type inference.
                #
                # This is a bit messy and there are all kinds of special
                # rules but it appears to get the job done.
                #
                # If it is a type element and does not yet have an
                # associated xsi type, try to infer it from the value.
                # The not startswith("prov:") check is a little bit hacky to
                # avoid type interference when the type is a standard prov
                # type.
                #
                # To enable a mapping of Python types to XML and back,
                # the XSD type must be written for these types.
                ALWAYS_CHECK = {
                    bool,
                    datetime.datetime,
                    float,
                    int,
                    prov.identifier.Identifier,
                }
                if (
                    (
                        force_types
                        or type(value) in ALWAYS_CHECK
                        or attr in [PROV_TYPE, PROV_LOCATION, PROV_VALUE]
                    )
                    and _ns_xsi("type") not in subelem.attrib
                    and not str(value).startswith("prov:")
                    and not (attr in PROV_ATTRIBUTE_QNAMES and v)
                    and attr not in [PROV_ATTR_TIME, PROV_LABEL]
                ):
                    xsd_type = None
                    if isinstance(value, bool):
                        xsd_type = XSD_BOOLEAN
                        v = v.lower()
                    elif isinstance(value, str):
                        xsd_type = XSD_STRING
                    elif isinstance(value, float):
                        xsd_type = XSD_DOUBLE
                    elif isinstance(value, int):
                        xsd_type = XSD_INT
                    elif isinstance(value, datetime.datetime):
                        # Exception of the exception, while technically
                        # still correct, do not write XSD dateTime type for
                        # attributes in the PROV namespaces as the type is
                        # already declared in the XSD and PROV XML also does
                        # not specify it in the docs.
                        if (
                            attr.namespace.prefix != "prov"
                            or "time" not in attr.localpart.lower()
                        ):
                            xsd_type = XSD_DATETIME
                    elif isinstance(value, prov.identifier.Identifier):
                        xsd_type = XSD_ANYURI

                    if xsd_type is not None:
                        subelem.attrib[_ns_xsi("type")] = str(xsd_type)

                if attr in PROV_ATTRIBUTE_QNAMES and v:
                    subelem.attrib[_ns_prov("ref")] = v
                else:
                    subelem.text = v
        return xml_bundle_root

    def deserialize(self, stream: io.IOBase, **kwargs: Any) -> prov.model.ProvDocument:
        """Deserialize a `PROV-XML <http://www.w3.org/TR/prov-xml/>`_
        stream into a :class:`~prov.model.ProvDocument`.

        XML comments in the input are discarded before parsing.

        Args:
            stream: Input data; text streams are UTF-8-encoded before
                parsing.
            **kwargs: Unused; accepted for interface compatibility with
                :meth:`~prov.serializers.Serializer.deserialize`.

        Returns:
            The deserialized :class:`~prov.model.ProvDocument`.
        """
        if isinstance(stream, io.TextIOBase):
            with io.BytesIO() as buf:
                buf.write(stream.read().encode("utf-8"))
                buf.seek(0, 0)
                xml_doc = etree.parse(buf).getroot()  # type: etree._Element
        else:
            xml_doc = etree.parse(stream).getroot()  # type: ignore[arg-type]

        # Remove all comments.
        for c in xml_doc.xpath("//comment()"):  # type: ignore[union-attr]
            p = c.getparent()  # type: ignore[union-attr]
            p.remove(c)  # type: ignore[union-attr, arg-type]

        document = prov.model.ProvDocument()
        self.deserialize_subtree(xml_doc, document)
        return document

    def deserialize_subtree(
        self,
        xml_doc: etree._Element,
        bundle: prov.model.ProvDocument | prov.model.ProvBundle,
    ) -> prov.model.ProvDocument | prov.model.ProvBundle:
        """Deserialize an etree element containing a PROV document or bundle.

        Mutates ``bundle`` in place, adding one record per child element of
        ``xml_doc``; ``<prov:bundleContent>`` children are recursively
        deserialized into new named bundles added to ``bundle`` (which must
        then be a :class:`~prov.model.ProvDocument`). A ``<prov:other>``
        child (non-PROV information) is skipped with a warning.

        Args:
            xml_doc: The etree element (document or bundle content) to read.
            bundle: The document or bundle object to populate.

        Returns:
            ``bundle``, mutated in place.

        Raises:
            ProvXMLException: If a child element is not in the PROV
                namespace.

        Warns:
            UserWarning: For each ``<prov:other>`` child, which is otherwise
                ignored.
        """

        for element in xml_doc:
            qname = etree.QName(element)
            if qname.namespace != DEFAULT_NAMESPACES["prov"].uri:
                raise ProvXMLException(
                    "Non PROV element discovered in document or bundle."
                )
            # Ignore the <prov:other> element storing non-PROV information.
            if qname.localname == "other":
                warnings.warn(
                    "Document contains non-PROV information in "
                    "<prov:other>. It will be ignored in this package.",
                    UserWarning,
                    stacklevel=2,
                )
                continue

            id_tag = _ns_prov("id")
            rec_id = element.attrib.get(id_tag, None)
            # Try to make a qualified name out of it!
            prov_rec_id = (
                xml_qname_to_QualifiedName(element, rec_id)
                if rec_id is not None
                else None
            )

            # Recursively read bundles.
            if qname.localname == "bundleContent":
                assert isinstance(bundle, prov.model.ProvDocument)
                assert prov_rec_id is not None
                b = bundle.bundle(identifier=prov_rec_id)
                self.deserialize_subtree(element, b)
                continue

            attributes = _extract_attributes(element)

            # Map the record type to its base type.
            q_prov_name = FULL_PROV_RECORD_IDS_MAP[qname.localname]
            rec_type = PROV_BASE_CLS[q_prov_name]

            if _ns_xsi("type") in element.attrib:
                value = xml_qname_to_QualifiedName(
                    element,
                    element.attrib[_ns_xsi("type")],  # type: ignore[arg-type]
                )
                attributes.append((PROV["type"], value))

            rec = bundle.new_record(rec_type, prov_rec_id, attributes)

            # Add the actual type in case a base type has been used.
            if rec_type != q_prov_name:
                rec.add_asserted_type(q_prov_name)
        return bundle

    def _derive_record_label(
        self,
        rec_type: prov.identifier.QualifiedName,
        attributes: list[tuple[prov.identifier.QualifiedName, Any]],
    ) -> str:
        """Derive the PROV-XML element name for a record, honouring subtypes.

        If a ``prov:type`` attribute's value names a subtype of ``rec_type``
        (per :data:`~prov.constants.PROV_BASE_CLS`), that subtype's element
        name is used instead of ``rec_type``'s, and the matching
        ``(PROV_TYPE, value)`` entry is removed from ``attributes`` in place
        (it is then encoded as the element name rather than duplicated as a
        ``prov:type`` attribute).

        Args:
            rec_type: The record's (base) type.
            attributes: The record's attributes; mutated in place if a
                subtype is found.

        Returns:
            The PROV-XML element name to use for the record.
        """
        rec_label = FULL_NAMES_MAP[rec_type]

        for key, value in list(attributes):
            if key != PROV_TYPE:
                continue
            if isinstance(value, prov.model.Literal):
                value = value.value
            if value in PROV_BASE_CLS and PROV_BASE_CLS[value] != value:
                attributes.remove((key, value))
                rec_label = FULL_NAMES_MAP[value]
                break
        return rec_label


def _extract_attributes(
    element: etree._Element,
) -> list[tuple[prov.identifier.QualifiedName, Any]]:
    """Extract a record's attributes from its PROV-XML etree element.

    Each child of ``element`` becomes one ``(QualifiedName, value)`` pair:
    a ``prov:ref`` attribute yields a :class:`~prov.identifier.QualifiedName`
    value, an ``xsi:type`` attribute yields a typed
    :class:`~prov.model.Literal` (or, for ``xsd:QName``, a
    :class:`~prov.identifier.QualifiedName`), an ``xml:lang`` attribute
    yields a language-tagged :class:`~prov.model.Literal`, and a child with
    no attributes yields its plain text content.

    Args:
        element: The PROV-XML record element whose children are its
            attributes.

    Returns:
        The extracted ``(QualifiedName, value)`` pairs, in document order.

    Warns:
        UserWarning: For any child attribute that is none of ``prov:ref``,
            ``xsi:type``, or ``xml:lang``; such attributes are ignored.
    """
    attributes = []  # type: list[tuple[prov.identifier.QualifiedName, Any]]
    for subel in element:
        sqname = etree.QName(subel)
        qname_str = (
            f"{subel.prefix}:{sqname.localname}" if subel.prefix else sqname.localname
        )
        _t = xml_qname_to_QualifiedName(subel, qname_str)

        for key, value in subel.attrib.items():
            value_str = value.decode("utf-8") if isinstance(value, bytes) else value
            if key == _ns_prov("ref"):
                _v = xml_qname_to_QualifiedName(subel, value_str)  # type: Any
            elif key == _ns_xsi("type"):
                datatype = xml_qname_to_QualifiedName(subel, value_str)
                if datatype == XSD_QNAME:
                    _v = xml_qname_to_QualifiedName(subel, subel.text)  # type: ignore[arg-type]
                else:
                    _v = prov.model.Literal(subel.text, datatype)
            elif key == _ns_xml("lang"):
                _v = prov.model.Literal(subel.text, langtag=value_str)
            else:
                warnings.warn(
                    f"The element '{_t}' contains an attribute {key!s}='{value!s}' "
                    "which is not representable in the prov module's "
                    "internal data model and will thus be ignored.",
                    UserWarning,
                    stacklevel=2,
                )

        if not subel.attrib:
            _v = subel.text

        attributes.append((_t, _v))

    return attributes


def xml_qname_to_QualifiedName(
    element: etree._Element, qname_str: str
) -> prov.identifier.QualifiedName:
    """Resolve an XML QName-like string to a :class:`~prov.identifier.QualifiedName`.

    Args:
        element: The etree element ``qname_str`` was read from; its
            ``nsmap`` (in scope at that point in the document) is used to
            resolve the prefix.
        qname_str: A ``"prefix:localpart"`` string, or a bare local name to
            be resolved against the default namespace.

    Returns:
        The resolved qualified name. The XSD and PROV namespaces are mapped
        to this package's canonical :data:`~prov.constants.XSD`/
        :data:`~prov.constants.PROV` namespace objects; any other namespace
        URI becomes a new :class:`~prov.identifier.Namespace`.

    Raises:
        ProvXMLException: If ``qname_str`` has no recognized prefix and
            ``element`` has no default namespace in scope.
    """
    if ":" in qname_str:
        prefix, localpart = qname_str.split(":", 1)
        if prefix in element.nsmap:
            ns_uri = element.nsmap[prefix]
            if ns_uri == XML_XSD_URI:
                ns = XSD  # use the standard xsd namespace (i.e. with #)
            elif ns_uri == PROV.uri:
                ns = PROV
            else:
                ns = prov.identifier.Namespace(prefix, ns_uri)
            return ns[localpart]
    # case 1: no colon
    # case 2: unknown prefix
    if None in element.nsmap:
        ns_uri = element.nsmap[None]
        if ns_uri == XML_XSD_URI:  # noqa: SIM108
            ns = XSD  # use the standard xsd namespace (i.e. with #)
        else:
            # Deliberately not mapping PROV.uri to the canonical PROV namespace
            # here (unlike the prefixed branch above): doing so would change the
            # serialized output for previously-accepted documents, breaking the
            # 2.x output-compatibility promise. Kept as an if/else (not a
            # ternary) so this explanation stays attached to the branch it
            # documents.
            ns = prov.identifier.Namespace("", ns_uri)
        return ns[qname_str]
    # no default namespace
    raise ProvXMLException(f'Could not create a valid QualifiedName for "{qname_str}"')


def _ns(ns: str, tag: str) -> str:
    # Clark notation ("{uri}tag") as used by lxml/ElementTree
    return f"{{{ns}}}{tag}"


def _ns_prov(tag: str) -> str:
    return _ns(DEFAULT_NAMESPACES["prov"].uri, tag)


def _ns_xsi(tag: str) -> str:
    return _ns(DEFAULT_NAMESPACES["xsi"].uri, tag)


def _ns_xml(tag: str) -> str:
    NS_XML = "http://www.w3.org/XML/1998/namespace"
    return _ns(NS_XML, tag)

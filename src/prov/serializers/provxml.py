"""PROV-XML serializer for ProvDocument."""

import datetime
import io
import logging
import re
from collections.abc import Iterable, Iterator
from typing import Any

from lxml import etree

import prov.identifier
import prov.model
from prov._warnings import warn
from prov.constants import *
from prov.identifier import _NCNAME_CHARS, _NCNAME_START_CHARS
from prov.model import (
    DEFAULT_NAMESPACES,
    NameValuePair,
    ProvException,
    ProvExceptionInvalidQualifiedName,
    sorted_attributes,
)
from prov.model._values import (
    _xsd_datetime_text,
    _xsd_double_text,
    python_value_form,
    resolve_name,
    resolve_pair,
)
from prov.model.namespaces import _first_free
from prov.serializers import ProvSerializationError, Serializer, _is_text_stream
from prov.serializers._json_common import _add_memberships

__author__ = "Lion Krischer"
__email__ = "krischer@geophysik.uni-muenchen.de"

logger = logging.getLogger(__name__)

# Create a dictionary containing all top-level PROV XML elements for an easy
# mapping.
FULL_NAMES_MAP = dict(PROV_N_MAP)
FULL_NAMES_MAP.update(ADDITIONAL_N_MAP)
# Maps every PROV record/subtype QualifiedName (including PROV-XML's
# top-level subtypes from ADDITIONAL_N_MAP in prov.constants) to its
# PROV-XML element name.
# Inverse mapping.
FULL_PROV_RECORD_IDS_MAP = {
    FULL_NAMES_MAP[rec_type_id]: rec_type_id for rec_type_id in FULL_NAMES_MAP
}
# Inverse of FULL_NAMES_MAP: maps each PROV-XML element name back to its
# record/subtype QualifiedName.

XML_XSD_URI = "http://www.w3.org/2001/XMLSchema"

# Hardened against XXE / entity expansion (#273): PROV-XML documents have no
# legitimate use for DTD entity resolution or network access, so both are
# switched off explicitly rather than left to whatever lxml's own default
# parser happens to do. This matters for three distinct reasons, not just
# one: lxml's own default for `resolve_entities` only became safe ('internal')
# in lxml 5.0 -- this package's floor (`lxml>=3.3.5`) still admits older
# releases that default to `True` (full external entity resolution); even on
# a safe lxml release, any other library sharing the process can repoint the
# *global* default parser via `etree.set_default_parser(...)`, which is what
# a bare `etree.parse(...)` call (no `parser=`) silently inherits; and prov
# is embedded in other applications that may load such libraries. Passing this parser explicitly at both parse sites closes all
# three regardless of the installed lxml version or what else is loaded in
# the process. `huge_tree` is left at its lxml default of `False`: raising it
# disables libxml2's own hard limits on tree depth/text length/entity
# amplification, which is the opposite of what a hardened parser wants here.
#
# Shared module-level instance, not one constructed per parse: lxml's own
# documentation for `XMLParser` states that sharing a parser across threads
# "is not harmful", only less efficient than per-thread instances under
# heavy concurrent load (access is internally serialized). PROV-XML
# deserialization is not expected to be a high-frequency, highly concurrent
# hot path even in a web service, so the simplicity of a single shared
# parser wins over per-parse allocation; if profiling ever
# shows lock contention here, switch to constructing a parser per call.
_XML_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


class ProvXMLException(ProvSerializationError):
    """Raised when a PROV-XML document cannot be serialized or parsed by this package."""


def _line(element: etree._Element) -> str:
    """``"line N, "`` for an element that has a line, else nothing."""
    return "" if element.sourceline is None else f"line {element.sourceline}, "


def _element_position(element: etree._Element, rec_id: str | None) -> str:
    """Where an error about ``element`` starts: its line, if it has one, its
    tag and its ``prov:id``."""
    named = repr(rec_id) if rec_id is not None else "with no prov:id"
    return f"{_line(element)}<prov:{etree.QName(element).localname}> {named}: "


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
        if _is_text_stream(stream):
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
        nsmap = self._build_nsmap(bundle)
        _declare_a_prefix_for_colon_names(nsmap, bundle)

        if element is not None:
            xml_bundle_root = etree.SubElement(
                element, _ns_prov("bundleContent"), nsmap=nsmap
            )
        else:
            xml_bundle_root = etree.Element(_ns_prov("document"), nsmap=nsmap)

        if bundle.identifier:
            xml_bundle_root.attrib[_ns_prov("id")] = _name_text(
                xml_bundle_root, bundle.identifier
            )

        for record in bundle._records:
            self._encode_record(xml_bundle_root, record, force_types)
        return xml_bundle_root

    def _build_nsmap(self, bundle: prov.model.ProvBundle) -> dict[str, str]:
        """Build the lxml namespace map for ``bundle``'s root XML element.

        Insertion order is significant: lxml emits namespace declarations in
        the order of the mapping, so the registered namespaces of
        ``self.document`` come first, then its default namespace (under the
        ``None`` key), replaced by ``bundle``'s own default where it has one,
        then ``bundle``'s own namespaces, then
        :data:`~prov.model.DEFAULT_NAMESPACES` and ``xsi``.

        Args:
            bundle: The bundle or document being serialized.

        Returns:
            A prefix-to-URI mapping suitable for lxml's ``nsmap`` argument.
        """
        nsmap: dict[str, str] = {
            ns.prefix: ns.uri
            for ns in self.document._namespaces.get_registered_namespaces()  # type: ignore[union-attr]
        }
        if self.document._namespaces._default:  # type: ignore[union-attr]
            # TODO: Check if the below works as expected.
            nsmap[None] = self.document._namespaces._default.uri  # type: ignore[union-attr, index]
        own_default = bundle.get_default_namespace()
        if own_default is not None:
            # a bundle's own default replaces the document's on its element
            nsmap[None] = own_default.uri  # type: ignore[index]
        for namespace in bundle.get_registered_namespaces():
            if namespace not in nsmap:
                nsmap[namespace.prefix] = namespace.uri

        for _key, value in DEFAULT_NAMESPACES.items():
            uri = value.uri
            if value.prefix == "xsd":
                # The XSD namespace for some reason has no hash at the end
                # for PROV XML, but for all other serializations it does.
                uri = uri.rstrip("#")
            nsmap[value.prefix] = uri
        # xsi:type carries every typed value's datatype (PROV-XML section 2.1).
        bound = nsmap.pop(XSI.prefix, XSI.uri)
        if bound != XSI.uri:
            raise ProvXMLException(
                f"PROV-XML binds the prefix '{XSI.prefix}' to <{XSI.uri}>, "
                f"but the document binds it to <{bound}>"
            )
        nsmap[XSI.prefix] = XSI.uri
        return nsmap

    def _encode_record(
        self,
        xml_bundle_root: etree._Element,
        record: prov.model.ProvRecord,
        force_types: bool,
    ) -> None:
        """Add one record, with all of its attributes, to a bundle element.

        Args:
            xml_bundle_root: The ``<prov:document>`` or
                ``<prov:bundleContent>`` element to append the record
                element to.
            record: The record to encode.
            force_types: See :meth:`serialize`.
        """
        rec_type = record.get_type()
        identifier = (
            _name_text(xml_bundle_root, record._identifier)
            if record._identifier
            else None
        )

        attrs = {_ns_prov("id"): identifier} if identifier else None

        # Derive the record label from its attributes which is sometimes
        # needed.
        attributes = record.attributes
        rec_label = self._derive_record_label(rec_type, attributes)

        elem = etree.SubElement(xml_bundle_root, _ns_prov(rec_label), attrs)

        for attr, value in sorted_attributes(rec_type, attributes):
            _encode_attribute(elem, attr, value, force_types)

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
        if _is_text_stream(stream):
            with io.BytesIO() as buf:
                buf.write(stream.read().encode("utf-8"))
                buf.seek(0, 0)
                xml_doc: etree._Element = etree.parse(buf, parser=_XML_PARSER).getroot()
        else:
            xml_doc = etree.parse(stream, parser=_XML_PARSER).getroot()  # type: ignore[arg-type]

        # Remove all comments.
        for c in xml_doc.xpath("//comment()"):  # type: ignore[union-attr]
            p = c.getparent()  # type: ignore[union-attr]
            p.remove(c)  # type: ignore[union-attr, arg-type]

        document = prov.model.ProvDocument()
        namespaces: dict[tuple[str, str], prov.identifier.Namespace] = {}
        self.deserialize_subtree(xml_doc, document, namespaces=namespaces)
        return document

    def deserialize_subtree(
        self,
        xml_doc: etree._Element,
        bundle: prov.model.ProvDocument | prov.model.ProvBundle,
        *,
        namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None = None,
    ) -> prov.model.ProvDocument | prov.model.ProvBundle:
        """Deserialize an etree element containing a PROV document or bundle.

        Mutates ``bundle`` in place, adding one record per child element of
        ``xml_doc``; ``<prov:bundleContent>`` children are recursively
        deserialized into new named bundles added to ``bundle`` (which must
        then be a :class:`~prov.model.ProvDocument`). An ``xmlns`` on
        ``xml_doc`` that differs from the enclosing default becomes
        ``bundle``'s default namespace. A ``<prov:other>`` child
        (non-PROV information) is skipped with a warning.

        Args:
            xml_doc: The etree element (document or bundle content) to read.
            bundle: The document or bundle object to populate.
            namespaces: The read's ``(prefix, uri)`` map of
                :class:`~prov.identifier.Namespace` objects, shared with
                nested bundles; ``None`` creates a namespace per call.

        Returns:
            ``bundle``, mutated in place.

        Raises:
            ProvXMLException: If a child element is not in the PROV
                namespace; if a ``<prov:bundleContent>`` has no
                ``prov:id`` or is nested in a bundle; or, naming the
                element and, when it has one, its line, if the element is
                not a PROV element or the model rejects a record, a bundle
                or the default namespace ``xml_doc`` declares, such as one
                that starts with ``@`` (the model's error is the
                ``__cause__``).

        Warns:
            UserWarning: For each ``<prov:other>`` child, which is otherwise
                ignored.
        """

        # For a bundleContent, _read_bundle_content has already adopted the
        # element's default inside the record wrap, so this wrap fires for the
        # document element only.
        try:
            _adopt_own_default(xml_doc, bundle)
        except ProvException as exc:
            raise ProvXMLException(
                f"{_line(xml_doc)}<prov:{etree.QName(xml_doc).localname}>: {exc}"
            ) from exc

        for element in xml_doc:
            qname = etree.QName(element)
            if qname.namespace != DEFAULT_NAMESPACES["prov"].uri:
                raise ProvXMLException(
                    "Non PROV element discovered in document or bundle."
                )
            # Ignore the <prov:other> element storing non-PROV information.
            if qname.localname == "other":
                warn(
                    "Document contains non-PROV information in "
                    "<prov:other>. It will be ignored in this package.",
                    UserWarning,
                )
                continue

            id_tag = _ns_prov("id")
            rec_id = element.attrib.get(id_tag, None)

            try:
                # Recursively read bundles.
                if qname.localname == "bundleContent":
                    self._read_bundle_content(element, bundle, rec_id, namespaces)
                    continue

                self._read_record(element, qname.localname, rec_id, bundle, namespaces)
            except ProvException as exc:
                raise ProvXMLException(
                    f"{_element_position(element, rec_id)}{exc}"
                ) from exc
        return bundle

    def _read_record(
        self,
        element: etree._Element,
        localname: str,
        rec_id: str | None,
        bundle: prov.model.ProvDocument | prov.model.ProvBundle,
        namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None,
    ) -> None:
        """Add the record that ``element`` encodes to ``bundle``."""
        # Try to make a qualified name out of it!
        prov_rec_id = (
            xml_qname_to_QualifiedName(
                element, rec_id, namespaces=namespaces, scope=bundle
            )
            if rec_id is not None
            else None
        )

        attributes = _extract_attributes(element, namespaces, bundle)

        # Map the record type to its base type.
        q_prov_name = FULL_PROV_RECORD_IDS_MAP.get(localname)
        if q_prov_name is None:
            raise ProvXMLException(
                _element_position(element, rec_id) + "it is not a PROV element"
            )
        rec_type = PROV_BASE_CLS[q_prov_name]

        if _ns_xsi("type") in element.attrib:
            value = xml_qname_to_QualifiedName(
                element,
                element.attrib[_ns_xsi("type")],  # type: ignore[arg-type]
                namespaces=namespaces,
                scope=bundle,
            )
            attributes.append((PROV["type"], value))

        if rec_type == PROV_MEMBERSHIP and _add_split_memberships(
            bundle, prov_rec_id, attributes
        ):
            return

        rec = bundle.new_record(rec_type, prov_rec_id, attributes)

        # Add the actual type in case a base type has been used.
        if rec_type != q_prov_name:
            rec.add_asserted_type(q_prov_name)

    def _read_bundle_content(
        self,
        element: etree._Element,
        document: prov.model.ProvDocument | prov.model.ProvBundle,
        rec_id: str | None,
        namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None,
    ) -> None:
        """Read a ``<prov:bundleContent>`` into a new bundle of ``document``.

        The bundle takes its own ``xmlns`` as its default, and the prefixes
        declared on the element as its own namespaces, before its ``prov:id``
        is resolved, so the identifier and the records read in its scope.

        Raises:
            ProvXMLException: If ``document`` is not a document, or ``rec_id``
                is ``None``.
        """
        if not isinstance(document, prov.model.ProvDocument):
            # Only a document may directly contain named bundles;
            # nested bundleContent would mean a bundle-within-a-bundle.
            raise ProvXMLException("bundleContent found outside a ProvDocument")
        if rec_id is None:
            raise ProvXMLException("bundleContent element has no id")
        bundle = prov.model.ProvBundle(document=document)
        _adopt_own_default(element, bundle)
        own_prefixes = _own_prefixes(element)
        for prefix, uri in own_prefixes:
            bundle.add_namespace(_namespace(namespaces, prefix, uri))
        identifier = xml_qname_to_QualifiedName(
            element, rec_id, namespaces=namespaces, scope=bundle
        )
        if identifier.namespace.prefix and identifier.namespace.prefix not in (
            prefix for prefix, _ in own_prefixes
        ):
            # a prefix read from the document or an ancestor is the document's
            identifier = document.mandatory_valid_qname(identifier)
        document.add_bundle(bundle, identifier)
        self.deserialize_subtree(element, bundle, namespaces=namespaces)

    def _derive_record_label(
        self,
        rec_type: prov.identifier.QualifiedName,
        attributes: list[NameValuePair],
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
            if not isinstance(value, prov.identifier.QualifiedName):
                continue
            if value in PROV_BASE_CLS and PROV_BASE_CLS[value] != value:
                attributes.remove((key, value))
                rec_label = FULL_NAMES_MAP[value]
                break
        return rec_label


def _prefix_bound_to(
    bindings: Iterable[tuple[str | None, str]], uri: str
) -> str | None:
    """A prefix among ``bindings`` bound to ``uri``, or ``None``."""
    return next((p for p, u in bindings if p is not None and u == uri), None)


def _names_written_by(
    bundle: prov.model.ProvBundle,
) -> Iterator[prov.identifier.QualifiedName]:
    """The names ``bundle`` writes as text: its identifier, its records'
    identifiers, and their name values and literal datatypes."""
    if bundle.identifier is not None:
        yield bundle.identifier
    for record in bundle._records:
        if record._identifier is not None:
            yield record._identifier
        for values in record._attributes.values():
            for value in values:
                if isinstance(value, prov.model.Literal):
                    if value.datatype is not None:
                        yield value.datatype
                elif isinstance(value, prov.identifier.QualifiedName):
                    yield value


def _holds_a_colon_name_in(bundle: prov.model.ProvBundle, uri: str) -> bool:
    """Whether ``bundle`` writes a name in the namespace ``uri`` whose local
    part contains ``:``, which has no QName."""
    return any(
        ":" in name.localpart and name.namespace.uri == uri
        for name in _names_written_by(bundle)
    )


def _declare_a_prefix_for_colon_names(
    nsmap: dict[str, str], bundle: prov.model.ProvBundle
) -> None:
    """Bind ``dn`` (``dn_1``, ... when taken) in ``nsmap`` to the default
    namespace in scope when ``bundle`` writes a name in it whose local part
    contains ``:``, and no prefix is bound to it yet; the name is then written
    under that prefix, as the PROV-JSON writer does (#570, #677). lxml fixes
    an element's declarations at creation, so this runs before the element is
    built."""
    default = next((uri for prefix, uri in nsmap.items() if prefix is None), None)
    if default is None or _prefix_bound_to(nsmap.items(), default) is not None:
        return
    if _holds_a_colon_name_in(bundle, default):
        nsmap[_first_free("dn", nsmap.__contains__)] = default


def _name_text(elem: etree._Element, name: prov.identifier.QualifiedName) -> str:
    """The QName text that names ``name`` under ``elem``: ``prefix:local``; a
    bare local part under the element's ``xmlns`` when the namespace has no
    prefix; and, when that local part contains ``:`` and so has no QName, the
    local part under the prefix bound to the IRI on the bundle element, which
    the pre-scan declares for the default namespace, the only prefix-less one
    a bundle can hold."""
    namespace = name.namespace
    if namespace.prefix:
        return str(name)
    local = name.localpart
    if ":" in local:
        prefix = _prefix_bound_to(elem.nsmap.items(), namespace.uri)
        if prefix:
            return f"{prefix}:{local}"
    return local


def _encode_attribute(
    elem: etree._Element,
    attr: prov.identifier.QualifiedName,
    value: Any,
    force_types: bool,
) -> None:
    """Add one attribute of a record as a child element of its record element.

    Args:
        elem: The record element to append the attribute element to.
        attr: The attribute's name.
        value: The attribute's value.
        force_types: See :meth:`ProvXMLSerializer.serialize`.
    """
    subelem = etree.SubElement(
        elem,
        _ns(
            attr.namespace.uri,
            _escape_ncname_localpart(attr.localpart),
        ),
    )
    v = _encode_attribute_value(subelem, attr, value)

    has_xsi_type = _ns_xsi("type") in subelem.attrib
    if _needs_xsd_type_inference(has_xsi_type, attr, value, v, force_types):
        xsd_type, v = _infer_xsd_type(attr, value, v)
        if xsd_type is not None:
            subelem.attrib[_ns_xsi("type")] = str(xsd_type)

    if attr in PROV_ATTRIBUTE_QNAMES and v:
        subelem.attrib[_ns_prov("ref")] = v
    else:
        subelem.text = v


def _encode_attribute_value(
    subelem: etree._Element,
    attr: prov.identifier.QualifiedName,
    value: Any,
) -> str:
    """Write an attribute value's explicit type/language hints and render it.

    Sets ``xsi:type`` and ``xml:lang`` on ``subelem`` where the value's own
    Python type already determines them (a typed or language-tagged
    :class:`~prov.model.Literal`, or a
    :class:`~prov.identifier.QualifiedName` outside a PROV formal attribute).

    Args:
        subelem: The attribute's XML element.
        attr: The attribute's name.
        value: The attribute's value.

    Returns:
        The value's string rendering, for use as element text or as a
        ``prov:ref`` attribute.
    """
    if isinstance(value, prov.model.Literal):
        if (
            value.datatype is not None
            and value.datatype != PROV_INTERNATIONALIZEDSTRING
        ):
            subelem.attrib[_ns_xsi("type")] = _name_text(subelem, value.datatype)
        if value.langtag is not None:
            subelem.attrib[_ns_xml("lang")] = value.langtag
        return value.value
    elif isinstance(value, prov.identifier.QualifiedName):
        if attr not in PROV_ATTRIBUTE_QNAMES:
            subelem.attrib[_ns_xsi("type")] = "xsd:QName"
        return _name_text(subelem, value)
    elif isinstance(value, datetime.datetime):
        return _xsd_datetime_text(value)
    elif isinstance(value, float):
        return _xsd_double_text(value)
    elif isinstance(value, int) and not isinstance(value, bool):
        return int.__repr__(value)
    else:
        return str(value)


_ANY_VALUE_ATTRIBUTES = frozenset({PROV_TYPE, PROV_LOCATION, PROV_VALUE})
_UNTYPED_ATTRIBUTES = frozenset({PROV_ATTR_TIME, PROV_LABEL})


def _needs_xsd_type_inference(
    has_xsi_type: bool,
    attr: prov.identifier.QualifiedName,
    value: Any,
    v: str,
    force_types: bool,
) -> bool:
    """Decide whether an ``xsi:type`` should be inferred for an attribute.

    A ``bool``, ``int``, ``float`` or ``datetime`` value, a subclass included
    (#657), is typed so that it reads back as the same Python type; the three
    ``prov:`` attributes that take any value are typed for the same reason.
    The not startswith("prov:") check avoids typing a standard PROV type.

    Args:
        has_xsi_type: Whether the attribute's XML element, as written so
            far, already carries an ``xsi:type`` attribute.
        attr: The attribute's name.
        value: The attribute's value.
        v: The value's string rendering.
        force_types: See :meth:`ProvXMLSerializer.serialize`.

    Returns:
        ``True`` if :func:`_infer_xsd_type` should be consulted for this
        attribute.
    """
    return (
        (
            force_types
            or isinstance(value, (int, float, datetime.datetime))
            or attr in _ANY_VALUE_ATTRIBUTES
        )
        and not has_xsi_type
        and not str(value).startswith("prov:")
        and not (attr in PROV_ATTRIBUTE_QNAMES and v)
        and attr not in _UNTYPED_ATTRIBUTES
    )


def _infer_xsd_type(
    attr: prov.identifier.QualifiedName,
    value: Any,
    v: str,
) -> tuple[prov.identifier.QualifiedName | None, str]:
    """Infer an attribute's ``xsd`` datatype from its Python value.

    Args:
        attr: The attribute's name.
        value: The attribute's value.
        v: The value's string rendering.

    Returns:
        A ``(xsd_type, v)`` pair: the inferred datatype (``None`` if none
        applies) and the value's text in that datatype's lexical form, which
        lower-cases a ``bool``.
    """
    if isinstance(value, datetime.datetime) and (
        attr.namespace.prefix == "prov" and "time" in attr.localpart.lower()
    ):
        # Exception of the exception, while technically still correct, do
        # not write XSD dateTime type for attributes in the PROV namespaces
        # as the type is already declared in the XSD and PROV XML also does
        # not specify it in the docs.
        return None, v
    form = python_value_form(value)
    if form is None or (text := form[0]) is None:
        return None, v
    return form[1], text


def _add_split_memberships(
    bundle: prov.model.ProvDocument | prov.model.ProvBundle,
    identifier: prov.model.OptionalID,
    attributes: list[NameValuePair],
) -> bool:
    """Add one ``hadMember`` record per ``prov:entity`` of a membership element.

    PROV-DM's ``hadMember`` is binary, so an element that lists several members
    becomes one record per member, as in the PROV-JSON and PROV-JSONLD readers.

    Args:
        bundle: Bundle to add the records to.
        identifier: The element's ``prov:id``, or ``None``.
        attributes: The element's ``(name, value)`` pairs.

    Returns:
        ``True`` when the element lists two or more members and the records are
        added; ``False`` when it lists fewer and nothing is added.
    """
    members = [value for name, value in attributes if name == PROV_ATTR_ENTITY]
    if len(members) < 2:
        return False
    collection: dict[prov.model.QualifiedNameCandidate, Any] = {}
    others: list[prov.model.AttributePair] = []
    for name, value in attributes:
        if name == PROV_ATTR_COLLECTION and name not in collection:
            collection[name] = value
        elif name != PROV_ATTR_ENTITY:
            others.append((name, value))
    _add_memberships(bundle, identifier, collection, others, members)
    return True


def _extract_attributes(
    element: etree._Element,
    namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None,
    scope: prov.model.ProvBundle,
) -> list[NameValuePair]:
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
        namespaces: The read's ``(prefix, uri)`` map of namespaces; ``None``
            creates a namespace per call.
        scope: The document or bundle the record is read into; a bare name
            resolves against its default namespace.

    Returns:
        The extracted ``(QualifiedName, value)`` pairs, in document order.

    Warns:
        UserWarning: For any child attribute that is none of ``prov:ref``,
            ``xsi:type``, or ``xml:lang``; such attributes are ignored.
        ProvWarning: When a reference-valued attribute's prov:ref sits on a
            nested child element (see ``_nested_reference``).

    Raises:
        ProvXMLException: If a child element carries XML attributes but
            none of them is ``prov:ref``, ``xsi:type``, or ``xml:lang``, so
            no attribute value can be determined, or if a reference-valued
            attribute element carries neither a prov:ref nor text.
    """
    attributes: list[NameValuePair] = []
    _unassigned = object()
    for subel in element:
        _t = _attribute_name(subel, namespaces, scope)

        _v: Any = _unassigned
        for key, value in subel.attrib.items():
            value_str = value.decode("utf-8") if isinstance(value, bytes) else value
            if key == _ns_prov("ref"):
                _v = xml_qname_to_QualifiedName(
                    subel, value_str, namespaces=namespaces, scope=scope
                )
            elif key == _ns_xsi("type"):
                datatype = xml_qname_to_QualifiedName(
                    subel, value_str, namespaces=namespaces, scope=scope
                )
                if datatype == XSD_QNAME:
                    _v = xml_qname_to_QualifiedName(
                        subel, _stripped_text(subel), namespaces=namespaces, scope=scope
                    )
                else:
                    # An empty XSD-typed text value (e.g. prov:value="")
                    # round-trips through lxml as .text is None rather than
                    # "" (#224); coalesce back to the empty string.
                    _v = prov.model.Literal(
                        subel.text if subel.text is not None else "", datatype
                    )
            elif key == _ns_xml("lang"):
                # Same None/"" coalescing as above, for language-tagged
                # literals (#224).
                _v = prov.model.Literal(
                    subel.text if subel.text is not None else "", langtag=value_str
                )
            else:
                warn(
                    f"The element '{_t}' contains an attribute {key!s}='{value!s}' "
                    "which is not representable in the prov module's "
                    "internal data model and will thus be ignored.",
                    UserWarning,
                )

        if not subel.attrib:
            if _t in PROV_ATTRIBUTE_QNAMES:
                _v = _nested_reference(subel, _t, namespaces, scope)
            else:
                # A plain-text attribute value (no xsi:type/xml:lang/prov:ref):
                # lxml reports an empty element's .text as None rather than ""
                # (e.g. <ex:k0></ex:k0>), which would otherwise make the
                # attribute vanish entirely once None reaches record
                # construction. Coalesce back to the empty string (#224). This
                # does not affect optional formal attributes that are absent
                # from the XML altogether: those never enter this loop.
                _v = subel.text if subel.text is not None else ""

        if _v is _unassigned:
            raise ProvXMLException(
                f"The element '{_t}' has no representable value: it carries "
                "XML attributes, but none of them is prov:ref, xsi:type, or "
                "xml:lang."
            )
        attributes.append((_t, _v))

    return attributes


def _attribute_name(
    subel: etree._Element,
    namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None,
    scope: prov.model.ProvBundle,
) -> prov.identifier.QualifiedName:
    """The name an attribute element spells. Its local part may hold ``:``
    (escaped on write), so it is resolved in the namespace the tag carries
    and never split."""
    qname = etree.QName(subel)
    local = _unescape_ncname_localpart(qname.localname)
    if qname.namespace is None:
        return _resolved(resolve_pair(scope, "", local), local)
    if subel.prefix is None:
        return _bare_name(qname.namespace, local, scope)
    return _namespace(namespaces, subel.prefix, qname.namespace)[local]


def _stripped_text(element: etree._Element) -> str:
    """The text of ``element`` read as a name, as ``xsd:QName``'s whitespace
    facet reads it: stripped, and empty when the element has none."""
    return (element.text or "").strip()


def _nested_reference(
    subel: etree._Element,
    attr: prov.identifier.QualifiedName,
    namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None,
    scope: prov.model.ProvBundle,
) -> prov.identifier.QualifiedName:
    """Value of a reference-valued formal attribute element with no ``prov:ref``.

    PROV-XML puts the reference on the element itself
    (``<prov:entity prov:ref="ex:e1"/>``). ProvToolbox 2.0.4 writes a
    ``hadMember`` member inside a wrapper,
    ``<entity><entity prov:ref="ex:e1"/></entity>``; the single child's
    reference is taken, with a warning. Non-blank text is the reference,
    resolved through the element's ``nsmap`` as a ``prov:ref`` is. A blank
    element with no reference anywhere has no value.

    Returns:
        The referenced qualified name.

    Raises:
        ProvXMLException: If ``subel`` has neither a ``prov:ref`` child nor
            text.
        ProvExceptionInvalidQualifiedName: If the reference does not
            resolve (see :func:`xml_qname_to_QualifiedName`).

    Warns:
        ProvWarning: When the reference is taken from a nested child.
    """
    ref = _ns_prov("ref")
    children = list(subel)
    if len(children) == 1 and ref in children[0].attrib:
        warn(
            f"The element '{attr}' carries its prov:ref on a nested "
            f"<{etree.QName(children[0]).localname}> child rather than on "
            "itself; the nested reference is used. The shape is not "
            "PROV-XML schema-valid (ProvToolbox writes it for hadMember)."
        )
        return xml_qname_to_QualifiedName(
            children[0],
            str(children[0].attrib[ref]),
            namespaces=namespaces,
            scope=scope,
        )
    text = _stripped_text(subel)
    if text:
        return xml_qname_to_QualifiedName(
            subel, text, namespaces=namespaces, scope=scope
        )
    raise ProvXMLException(
        f"The reference element '{attr}' has no prov:ref attribute and no "
        "reference text."
    )


def _adopt_own_default(
    element: etree._Element,
    bundle: prov.model.ProvDocument | prov.model.ProvBundle,
) -> None:
    """Make the ``xmlns`` of ``element`` the default of ``bundle`` when it
    differs from the default in scope at ``bundle``."""
    default = element.nsmap.get(None)
    enclosing = bundle.document
    inherited = None if enclosing is None else enclosing.default_ns_uri
    if default is not None and default not in (inherited, bundle.default_ns_uri):
        bundle.set_default_namespace(default)


# PROV-XML spells the xsd namespace without its trailing "#" (see _build_nsmap).
_BUILT_IN_URIS = frozenset({PROV.uri, XSD.uri, XML_XSD_URI, XSI.uri})


def _own_prefixes(element: etree._Element) -> list[tuple[str, str]]:
    """The ``(prefix, uri)`` declarations made on ``element`` itself, leaving
    out those inherited from its parent and the built-in ``xsd``, ``prov`` and
    ``xsi`` namespaces."""
    parent = element.getparent()
    inherited = {} if parent is None else parent.nsmap
    return [
        (prefix, uri)
        for prefix, uri in element.nsmap.items()
        if prefix is not None
        and inherited.get(prefix) != uri
        and uri not in _BUILT_IN_URIS
    ]


def _namespace(
    namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None,
    prefix: str,
    uri: str,
) -> prov.identifier.Namespace:
    """The namespace a ``prefix`` bound to ``uri`` names. The XSD and PROV
    namespaces are this package's canonical objects; any other is one
    ``Namespace`` per ``(prefix, uri)`` for the length of a read, and ``None``
    returns a new one.
    """
    if uri == XML_XSD_URI:
        return XSD  # use the standard xsd namespace (i.e. with #)
    if uri == PROV.uri:
        return PROV
    if namespaces is None:
        return prov.identifier.Namespace(prefix, uri)
    key = (prefix, uri)
    namespace = namespaces.get(key)
    if namespace is None:
        namespace = namespaces[key] = prov.identifier.Namespace(prefix, uri)
    return namespace


def _resolved(
    name: prov.identifier.QualifiedName | str, shown: str
) -> prov.identifier.QualifiedName:
    """``name``, or the model's refusal when it is the sentence saying why
    ``shown`` does not resolve."""
    if isinstance(name, str):
        raise ProvExceptionInvalidQualifiedName(shown, name)
    return name


def _bare_name(
    ns_uri: str, qname_str: str, scope: prov.model.ProvBundle | None
) -> prov.identifier.QualifiedName:
    """A bare name under the in-scope ``xmlns`` ``ns_uri``."""
    if ns_uri == XML_XSD_URI:
        return XSD[qname_str]  # use the standard xsd namespace (i.e. with #)
    if scope is None:
        raise ProvXMLException(
            f'Could not create a valid QualifiedName for "{qname_str}"'
        )
    enclosing = scope.document
    default = scope.get_default_namespace() or (
        None if enclosing is None else enclosing.get_default_namespace()
    )
    if default is not None and default.uri == ns_uri:
        return default[qname_str]
    raise ProvXMLException(
        f'the name "{qname_str}" is under an xmlns declaration ({ns_uri}) on an '
        "element, which has no scope in PROV; declare the default on the "
        "document or the bundle, or use a prefix"
    )


def xml_qname_to_QualifiedName(
    element: etree._Element,
    qname_str: str,
    *,
    namespaces: dict[tuple[str, str], prov.identifier.Namespace] | None = None,
    scope: prov.model.ProvBundle | None = None,
) -> prov.identifier.QualifiedName:
    """Resolve an XML QName-like string to a :class:`~prov.identifier.QualifiedName`.

    Args:
        element: The etree element ``qname_str`` was read from; its
            ``nsmap`` (in scope at that point in the document) is used to
            resolve the prefix.
        qname_str: A ``"prefix:localpart"`` string, or a bare local name to
            be resolved against the default namespace; an empty prefix
            (``":localpart"``) reads as a name with no colon. A name the
            ``nsmap`` does not resolve goes to the model when ``scope`` is
            given.
        namespaces: The read's ``(prefix, uri)`` map of namespaces; ``None``
            creates a namespace per call.
        scope: The document or bundle a bare name resolves in; its default
            namespace names the bare name when it has the in-scope ``xmlns``
            IRI.

    Returns:
        The resolved qualified name. The XSD and PROV namespaces are mapped
        to this package's canonical :data:`~prov.constants.XSD`/
        :data:`~prov.constants.PROV` namespace objects; any other namespace
        URI becomes one :class:`~prov.identifier.Namespace` per
        ``(prefix, uri)`` for the length of a read.

    Raises:
        ProvExceptionInvalidQualifiedName: If ``scope`` is given and the
            model refuses ``qname_str``, a name whose prefix ``element``
            does not declare or one with no colon and no default
            namespace in scope.
        ProvXMLException: If ``scope`` is ``None`` and the ``nsmap`` does
            not resolve ``qname_str``, or a bare name sits under an
            ``xmlns`` that is not the XSD namespace and not the default of
            ``scope``.
    """
    nsmap = element.nsmap
    prefix, local = qname_str.split(":", 1) if ":" in qname_str else ("", qname_str)
    if prefix and prefix in nsmap:
        return _namespace(namespaces, prefix, nsmap[prefix])[local]
    if not prefix and None in nsmap:
        return _bare_name(nsmap[None], local, scope)
    if scope is None:
        raise ProvXMLException(
            f'Could not create a valid QualifiedName for "{qname_str}"'
        )
    return _resolved(resolve_name(scope, qname_str), qname_str)


def _ns(ns: str, tag: str) -> str:
    # Clark notation ("{uri}tag") as used by lxml/ElementTree
    return f"{{{ns}}}{tag}"


def _ns_prov(tag: str) -> str:
    return _ns(DEFAULT_NAMESPACES["prov"].uri, tag)


def _ns_xsi(tag: str) -> str:
    return _ns(XSI.uri, tag)


def _ns_xml(tag: str) -> str:
    NS_XML = "http://www.w3.org/XML/1998/namespace"
    return _ns(NS_XML, tag)


# NCName character classes (XML 1.0 5th-edition Name productions, minus ':')
# live in prov.identifier, shared with the PROV-N lexer's PN_CHARS classes.
# Used here to detect/escape attribute-name local parts that are not legal
# NCNames when used as PROV-XML element tags (#289).
_NCNAME_START_RE = re.compile(f"[{_NCNAME_START_CHARS}]")
_NCNAME_CHAR_RE = re.compile(f"[{_NCNAME_CHARS}]")
_NCNAME_RE = re.compile(f"[{_NCNAME_START_CHARS}][{_NCNAME_CHARS}]*")
# One escaped char: _x + 4 (BMP) or 8 (astral) uppercase hex digits + _
_XML_NAME_ESCAPE_RE = re.compile(r"_x[0-9A-F]{4}(?:[0-9A-F]{4})?_")


def _escape_ncname_localpart(local: str) -> str:
    """Escape NCName-illegal characters in an attribute-name local part.

    PROV attribute names are written as PROV-XML element tags, but an
    attribute's local part is not guaranteed to be a legal XML NCName (it
    may start with a digit, contain ``'``, ``(``, ``,`` etc. — none of
    which prov itself restricts, per #257's no-assertion-time-enforcement
    stance). Rather than raising, illegal characters are escaped using the
    ``_xHHHH_`` convention (as used by the OpenXML/SQL Server ecosystems
    for the same problem), so the name round-trips losslessly instead of
    being rejected or silently corrupted.

    A literal run that itself looks like an escape sequence gets its
    introducing underscore self-escaped as ``_x005F_`` so decoding via
    :func:`_unescape_ncname_localpart` is always the exact inverse of this
    function, including for names produced by this package itself (#289):
    ``"_x0041_"`` (a literal name that happens to look like an escaped
    ``"A"``) becomes ``"_x005F_x0041_"``, not ``"_x0041_"`` unchanged
    (which would decode back to ``"A"``) or ``"A"`` (which would lose the
    original name). The same applies when the look-alike run is embedded
    inside an otherwise-legal name, e.g. ``"prefix_x0041_suffix"``.

    Names that are already legal NCNames and contain no ``_xHHHH_``-shaped
    run are returned unchanged, so existing output is byte-identical.
    """
    if not _XML_NAME_ESCAPE_RE.search(local) and _NCNAME_RE.fullmatch(local):
        return local
    out = []
    for i, char in enumerate(local):
        char_re = _NCNAME_START_RE if i == 0 else _NCNAME_CHAR_RE
        if char == "_" and _XML_NAME_ESCAPE_RE.match(local, i):
            out.append("_x005F_")
        elif char_re.fullmatch(char):
            out.append(char)
        else:
            code = ord(char)
            out.append(f"_x{code:04X}_" if code <= 0xFFFF else f"_x{code:08X}_")
    return "".join(out)


def _unescape_ncname_localpart(local: str) -> str:
    """Invert :func:`_escape_ncname_localpart`."""
    return _XML_NAME_ESCAPE_RE.sub(lambda m: chr(int(m.group(0)[2:-1], 16)), local)

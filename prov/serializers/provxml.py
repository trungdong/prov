from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Lion Krischer'
__email__ = 'krischer@geophysik.uni-muenchen.de'

import datetime
import logging
from lxml import etree
import io
import warnings

logger = logging.getLogger(__name__)

import prov
import prov.identifier
from prov.model import DEFAULT_NAMESPACES, sorted_attributes
from prov.constants import *  # NOQA


# Create a dictionary containing all top-level PROV XML elements for an easy
# mapping.
FULL_NAMES_MAP = dict(PROV_N_MAP)
FULL_NAMES_MAP.update(ADDITIONAL_N_MAP)
# Inverse mapping.
FULL_PROV_RECORD_IDS_MAP = dict((FULL_NAMES_MAP[rec_type_id], rec_type_id) for
                                rec_type_id in FULL_NAMES_MAP)


class ProvXMLException(prov.Error):
    pass


class ProvXMLSerializer(prov.serializers.Serializer):
    """PROV-XML serializer for :class:`~prov.model.ProvDocument`
    """
    def serialize(self, stream, force_types=False, **kwargs):
        """
        Serializes a :class:`~prov.model.ProvDocument` instance to `PROV-XML <http://www.w3.org/TR/prov-xml/>`_.

        :param stream: Where to save the output.
        :type force_types: boolean, optional
        :param force_types: Will force xsd:types to be written for most
            attributes mainly PROV-"attributes", e.g. tags not in the
            PROV namespace. Off by default meaning xsd:type attributes will
            only be set for prov:type, prov:location, and prov:value as is
            done in the official PROV-XML specification. Furthermore the
            types will always be set if the Python type requires it. False
            is a good default and it should rarely require changing.
        """
        xml_root = self.serialize_bundle(bundle=self.document,
                                         force_types=force_types)
        for bundle in self.document.bundles:
            self.serialize_bundle(bundle=bundle, element=xml_root,
                                  force_types=force_types)
        # No encoding must be specified when writing to String object which
        # does not have the concept of an encoding as it should already
        # represent unicode code points.
        et = etree.ElementTree(xml_root)
        if isinstance(stream, io.TextIOBase):
            stream.write(etree.tostring(et, xml_declaration=True,
                                        pretty_print=True).decode('utf-8'))
        else:
            et.write(stream, pretty_print=True, xml_declaration=True,
                     encoding="UTF-8")

    def serialize_bundle(self, bundle, element=None, force_types=False):
        """
        Serializes a bundle or document to PROV XML.

        :param bundle: The bundle or document.
        :param element: The XML element to write to. Will be created if None.
        :type force_types: boolean, optional
        :param force_types: Will force xsd:types to be written for most
            attributes mainly PROV-"attributes", e.g. tags not in the
            PROV namespace. Off by default meaning xsd:type attributes will
            only be set for prov:type, prov:location, and prov:value as is
            done in the official PROV-XML specification. Furthermore the
            types will always be set if the Python type requires it. False
            is a good default and it should rarely require changing.
        """
        # Build the namespace map for lxml and attach it to the root XML
        # element. No dictionary comprehension in Python 2.6!
        nsmap = dict((ns.prefix, ns.uri) for ns in
                     self.document._namespaces.get_registered_namespaces())
        if self.document._namespaces._default:
            nsmap[None] = self.document._namespaces._default.uri
        for namespace in bundle.namespaces:
            if namespace not in nsmap:
                nsmap[namespace.prefix] = namespace.uri

        for key, value in DEFAULT_NAMESPACES.items():
            uri = value.uri
            if value.prefix == "xsd":
                # The XSD namespace for some reason has no hash at the end
                # for PROV XML, but for all other serializations it does.
                uri = uri.rstrip("#")
            nsmap[value.prefix] = uri

        if element is not None:
            xml_bundle_root = etree.SubElement(
                element, _ns_prov("bundleContent"), nsmap=nsmap)
        else:
            xml_bundle_root = etree.Element(_ns_prov("document"), nsmap=nsmap)

        if bundle.identifier:
            xml_bundle_root.attrib[_ns_prov("id")] = unicode(bundle.identifier)

        for record in bundle._records:
            rec_type = record.get_type()
            identifier = unicode(record._identifier) \
                if record._identifier else None

            if identifier:
                attrs = {_ns_prov("id"): identifier}
            else:
                attrs = None

            # Derive the record label from its attributes which is sometimes
            # needed.
            attributes = list(record.attributes)
            rec_label = self._derive_record_label(rec_type, attributes)

            elem = etree.SubElement(xml_bundle_root,
                                    _ns_prov(rec_label), attrs)

            for attr, value in sorted_attributes(rec_type, attributes):
                subelem = etree.SubElement(
                    elem, _ns(attr.namespace.uri, attr.localpart))
                if isinstance(value, prov.model.Literal):
                    if value.datatype not in \
                            [None, PROV["InternationalizedString"]]:
                        subelem.attrib[_ns_xsi("type")] = "%s:%s" % (
                            value.datatype.namespace.prefix,
                            value.datatype.localpart)
                    if value.langtag is not None:
                        subelem.attrib[_ns_xml("lang")] = value.langtag
                    v = value.value
                elif isinstance(value, prov.model.QualifiedName):
                    if attr not in PROV_ATTRIBUTE_QNAMES:
                        subelem.attrib[_ns_xsi("type")] = "xsd:QName"
                    v = unicode(value)
                elif isinstance(value, datetime.datetime):
                    v = value.isoformat()
                else:
                    v = unicode(value)

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
                ALWAYS_CHECK = (bool, datetime.datetime, int, float, long,
                                prov.identifier.Identifier)
                if (force_types or
                        type(value) in ALWAYS_CHECK or
                        attr in [PROV_TYPE, PROV_LOCATION, PROV_VALUE]) and \
                        _ns_xsi("type") not in subelem.attrib and \
                        not unicode(value).startswith("prov:") and \
                        not (attr in PROV_ATTRIBUTE_QNAMES and v) and \
                        attr not in [PROV_ATTR_TIME, PROV_LABEL]:
                    xsd_type = None
                    if isinstance(value, bool):
                        xsd_type = XSD_BOOLEAN
                        v = v.lower()
                    elif isinstance(value, (str, unicode)):
                        xsd_type = XSD_STRING
                    elif isinstance(value, float):
                        xsd_type = XSD_DOUBLE
                    elif isinstance(value, (int, long)):
                        xsd_type = XSD_INT
                    elif isinstance(value, datetime.datetime):
                        # Exception of the exception, while technically
                        # still correct, do not write XSD dateTime type for
                        # attributes in the PROV namespaces as the type is
                        # already declared in the XSD and PROV XML also does
                        # not specify it in the docs.
                        if attr.namespace.prefix != "prov" \
                                or "time" not in attr.localpart.lower():
                            xsd_type = XSD_DATETIME
                    elif isinstance(value, prov.identifier.Identifier):
                        xsd_type = XSD_ANYURI

                    if xsd_type is not None:
                        subelem.attrib[_ns_xsi("type")] = unicode(xsd_type)

                if attr in PROV_ATTRIBUTE_QNAMES and v:
                    subelem.attrib[_ns_prov("ref")] = v
                else:
                    subelem.text = v
        return xml_bundle_root

    def _add_xml_namespaces_to_bundle(self, xml_doc, bundle):
        """
        Helper function adding the namespaces defined in the etree to the
        bundle.

        :param xml_doc: An etree element.
        :param bundle: A prov bundle object.
        """
        # Do not add namespaces already defined in the parent document in
        # case it is a bundle.
        doc_ns = [(i.prefix, i.uri) for i in bundle.document.namespaces] \
            if bundle.document is not None else []
        for key, value in xml_doc.nsmap.items():
            if (key, value) in doc_ns:
                continue
            elif key == "xsd":
                value = value.rstrip("#") + "#"
            elif key is None:
                bundle.set_default_namespace(value)
            else:
                bundle.add_namespace(key, value)

    def deserialize(self, stream, **kwargs):
        """
        Deserialize from `PROV-XML <http://www.w3.org/TR/prov-xml/>`_ representation to a
        :class:`~prov.model.ProvDocument` instance.

        :param stream: Input data.
        """
        if isinstance(stream, io.TextIOBase):
            with io.BytesIO() as buf:
                buf.write(stream.read().encode('utf-8'))
                buf.seek(0, 0)
                xml_doc = etree.parse(buf).getroot()
        else:
            xml_doc = etree.parse(stream).getroot()

        # Remove all comments.
        for c in xml_doc.xpath("//comment()"):
            p = c.getparent()
            p.remove(c)

        document = prov.model.ProvDocument()
        self.deserialize_subtree(xml_doc, document)
        return document

    def deserialize_subtree(self, xml_doc, bundle):
        """
        Deserialize an etree element containing a PROV document or a bundle
        and write it to the provided internal object.

        :param xml_doc: An etree element containing the information to read.
        :param bundle: The bundle object to write to.
        """
        self._add_xml_namespaces_to_bundle(xml_doc, bundle)

        # No dictionary comprehension in Python 2.6.
        r_nsmap = dict((value, key) for (key, value) in xml_doc.nsmap.items())

        for element in xml_doc:
            qname = etree.QName(element)
            if qname.namespace != DEFAULT_NAMESPACES["prov"].uri:
                raise ProvXMLException("Non PROV element discovered in "
                                       "document or bundle.")
            # Ignore the <prov:other> element storing non-PROV information.
            if qname.localname == "other":
                warnings.warn(
                    "Document contains non-PROV information in "
                    "<prov:other>. It will be ignored in this package.",
                    UserWarning)
                continue

            id_tag = _ns_prov("id")
            rec_id = element.attrib[id_tag] if id_tag in element.attrib \
                else None

            # Recursively read bundles.
            if qname.localname == "bundleContent":
                self._add_xml_namespaces_to_bundle(element, bundle)
                b = bundle.bundle(identifier=rec_id)
                self.deserialize_subtree(element, b)
                continue

            attributes, other_attributes = self._extract_attributes(
                element, r_nsmap, bundle.namespaces)

            # Map the record type to its base type.
            q_prov_name = FULL_PROV_RECORD_IDS_MAP[qname.localname]
            rec_type = PROV_BASE_CLS[q_prov_name]

            if _ns_xsi("type") in element.attrib:
                value = element.attrib[_ns_xsi("type")]
                other_attributes.append((PROV["type"], value))

            rec = bundle.new_record(rec_type, rec_id, attributes,
                                    other_attributes)

            # Add the actual type in case a base type has been used.
            if rec_type != q_prov_name:
                rec.add_asserted_type(q_prov_name)
        return bundle

    def _derive_record_label(self, rec_type, attributes):
        """
        Helper function trying to derive the record label taking care of
        subtypes and what not. It will also remove the type declaration for
        the attributes if it was used to specialize the type.

        :param rec_type: The type of records.
        :param attributes: The attributes of the record.
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

    def _extract_attributes(self, element, r_nsmap, namespaces):
        """
        Extract the PROV attributes from an etree element.

        :param element: The lxml.etree.Element instance.
        :param r_nsmap: A reverse namespace map going from prefix to
            namespace URI.
        :param namespaces: The namespace set defined for the current bundle.
        """
        attributes = []
        other_attributes = []
        for subel in element:
            sqname = etree.QName(subel)
            if sqname.namespace == DEFAULT_NAMESPACES["prov"].uri:
                _t = PROV[sqname.localname]
                d = attributes
            else:
                _t = "%s:%s" % (r_nsmap[sqname.namespace],
                                sqname.localname)
                d = other_attributes

            for key, value in subel.attrib.items():
                if key == _ns_xsi("type"):
                    try:
                        _namespace, _localpart = subel.text.split(":")
                    except ValueError:
                        _namespace, _localpart = None, subel.text
                    # If it is an xsd:QName, make sure it is returned as a
                    # QualifiedName instance!
                    if value == "xsd:QName" and _namespace and \
                            _namespace != "prov":
                        _ns_obj = Namespace(_namespace,
                                            subel.nsmap[_namespace])
                        if _ns_obj not in namespaces:
                            raise ProvXMLException(
                                "QualifiedName '%s' has an unknown namespace."
                                % subel.text)
                        _v = prov.identifier.QualifiedName(_ns_obj, _localpart)
                    else:
                        _v = prov.model.Literal(
                            subel.text,
                            XSD[value.split(":")[1]])
                elif key == _ns_prov("ref"):
                    _v = value
                elif key == _ns_xml("lang"):
                    _v = prov.model.Literal(subel.text, langtag=value)
                else:
                    warnings.warn(
                        "The element '%s' contains an attribute %s='%s' "
                        "which is not representable in the prov module's "
                        "internal data model and will thus be ignored." %
                        (_t, unicode(key), unicode(value)), UserWarning)

            if not subel.attrib:
                _v = subel.text

            d.append((_t, _v))

        return attributes, other_attributes


def _ns(ns, tag):
    return "{%s}%s" % (ns, tag)


def _ns_prov(tag):
    return _ns(DEFAULT_NAMESPACES['prov'].uri, tag)


def _ns_xsi(tag):
    return _ns(DEFAULT_NAMESPACES['xsi'].uri, tag)


def _ns_xml(tag):
    NS_XML = "http://www.w3.org/XML/1998/namespace"
    return _ns(NS_XML, tag)

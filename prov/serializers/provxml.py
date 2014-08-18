"""
PROV-XML serializers for ProvDocument
"""
__author__ = 'Lion Krischer'
__email__ = 'krischer@geophysik.uni-muenchen.de'

import datetime
import logging
from lxml import etree
import warnings

logger = logging.getLogger(__name__)

import prov
from prov.model import PROV_REC_CLS
from prov.constants import *  # NOQA

NS_PROV = prov.constants.PROV.uri
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_XML = "http://www.w3.org/XML/1998/namespace"

FULL_NAMES_MAP = dict(PROV_N_MAP)
FULL_NAMES_MAP.update(ADDITIONAL_N_MAP)
FULL_PROV_RECORD_IDS_MAP = dict((FULL_NAMES_MAP[rec_type_id], rec_type_id) for
                                 rec_type_id in FULL_NAMES_MAP)


class ProvXMLException(prov.Error):
    pass


class ProvXMLSerializer(prov.Serializer):
    def serialize(self, stream, force_types=False, **kwargs):
        """
        :param stream: Where to save the output.
        :type force_types: boolean, optional
        :param force_types: Will force xsd:types to be written for most
            attributes mainly only PROV-"attributes", e.g. tags not in the
            PROV namespace. Off by default meaning xsd:type attributes will
            only be set for prov:type, prov:location, and prov:value as is
            done in the official PROV-XML specification.
        """
        xml_root = self.serialize_bundle(bundle=self.document,
                                         force_types=force_types)
        for bundle in self.document.bundles:
            self.serialize_bundle(bundle=bundle, element=xml_root,
                                  force_types=force_types)
        et = etree.ElementTree(xml_root)
        et.write(stream, pretty_print=True, xml_declaration=True,
                 encoding="UTF-8")

    def serialize_bundle(self, bundle, element=None, force_types=False):
        # Build the namespace map for lxml and attach it to the root XML
        # element. No dictionary comprehension in Python 2.6!
        nsmap = dict((ns.prefix, ns.uri) for ns in
                     self.document._namespaces.get_registered_namespaces())
        if self.document._namespaces._default:
            nsmap[None] = self.document._namespaces._default.uri
        # Add the prov, XSI, and XSD namespaces by default.
        nsmap["prov"] = NS_PROV
        nsmap["xsi"] = NS_XSI
        # The XSD namespace for some reason has no hash at the end for PROV
        # XML but for all other serializations it does.
        nsmap["xsd"] = prov.constants.XSD.uri.rstrip("#")

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

            # The bundle record is still of type entity. In PROV XML it
            # actually is a proper bundle element. Loop through the
            # attributes to check if an attribute designates the current
            # element as a bundle element.
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
                        subelem.attrib[_ns(NS_XML, "lang")] = value.langtag
                    v = value.value
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
                if (force_types or
                        isinstance(value, bool) or
                        attr in [PROV_TYPE, PROV_LOCATION, PROV_VALUE]) and \
                        _ns_xsi("type") not in subelem.attrib and \
                        not str(value).startswith("prov:") and \
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
                    elif isinstance(value, int):
                        xsd_type = XSD_INT
                    elif isinstance(value, datetime.datetime):
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

    def deserialize(self, stream, **kwargs):
        xml_doc = etree.parse(stream).getroot()

        # Remove all comments.
        for c in xml_doc.xpath("//comment()"):
            p = c.getparent()
            p.remove(c)

        document = prov.model.ProvDocument()
        self.deserialize_subtree(xml_doc, document)
        return document

    def deserialize_subtree(self, xml_doc, bundle):
        # Do not add namespaces already defined in the parent document in
        # case it is a bundle.
        doc_ns = [(i.prefix, i.uri) for i in bundle.document.namespaces] \
            if bundle.document is not None else []
        for key, value in xml_doc.nsmap.items():
            if (key, value) in doc_ns:
                continue
            if key == "xsd":
                value = value.rstrip("#") + "#"
            bundle.add_namespace(key, value)

        # No dictionary comprehension in Python 2.6.
        r_nsmap = dict((value, key) for (key, value) in xml_doc.nsmap.items())

        for element in xml_doc:
            qname = etree.QName(element)
            if qname.namespace != NS_PROV:
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
                b = bundle.bundle(identifier=rec_id)
                self.deserialize_subtree(element, b)
                continue

            attributes, other_attributes = self._extract_attributes(
                element, r_nsmap)

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
        tries to derive the record label taking care of subtypes and what
        not. It will also remove the type declaration for the attributes if
        it was used to specialize the type .
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

    def _extract_attributes(self, element, r_nsmap):
        """
        Extract the PROV attributes from an etree element.

        :param element: The lxml.etree.Element instance.
        :param r_nsmap: A reverse namespace map going from prefix to
            namespace URI.
        """
        attributes = []
        other_attributes = []
        for subel in element:
            sqname = etree.QName(subel)
            if sqname.namespace == NS_PROV:
                _t = PROV[sqname.localname]
                d = attributes
            else:
                _t = "%s:%s" % (r_nsmap[sqname.namespace],
                                sqname.localname)
                d = other_attributes

            for key, value in subel.attrib.items():
                if key == _ns_xsi("type"):
                    _v = prov.model.Literal(
                        subel.text,
                        XSD[value.split(":")[1]])
                elif key == _ns_prov("ref"):
                    _v = value
                elif key == _ns(NS_XML, "lang"):
                    _v = prov.model.Literal(subel.text, langtag=value)
                else:
                    warnings.warn(
                        "The element '%s' contains an attribute %s='%s' "
                        "which is not representable in the prov module's "
                        "internal data model and will thus be ignored." %
                        (_t, str(key), str(value)), UserWarning)

            if not subel.attrib:
                _v = subel.text

            d.append((_t, _v))

        return attributes, other_attributes


def sorted_attributes(element, attributes):
    """
    Helper function sorting attributes into the order required by PROV-XML.
    """
    attributes = list(attributes)
    order = list(PROV_REC_CLS[element].FORMAL_ATTRIBUTES)

    # Append label, location, role, type, and value attributes. This is
    # universal amongst all elements.
    order.extend([PROV_LABEL, PROV_LOCATION, PROV_ROLE, PROV_TYPE,
                  PROV_VALUE])

    sorted_elements = []
    for item in order:
        this_type_list = []
        for e in list(attributes):
            if e[0] != item:
                continue
            this_type_list.append(e)
            attributes.remove(e)
        this_type_list.sort(key=lambda x: (str(x[0]), str(x[1])))
        sorted_elements.extend(this_type_list)
    # Add remaining attributes. According to the spec, the other attributes
    # have a fixed alphabetical order.
    attributes.sort(key=lambda x: (str(x[0]), str(x[1])))
    sorted_elements.extend(attributes)

    return sorted_elements


def _ns(ns, tag):
    return "{%s}%s" % (ns, tag)


def _ns_prov(tag):
    return _ns(NS_PROV, tag)


def _ns_xsi(tag):
    return _ns(NS_XSI, tag)

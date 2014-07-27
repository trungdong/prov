"""
PROV-XML serializers for ProvDocument
"""
__author__ = 'Lion Krischer'
__email__ = 'krischer@geophysik.uni-muenchen.de'

import datetime
import logging
from lxml import etree

logger = logging.getLogger(__name__)

import prov
from prov.constants import *

NS_PROV = "http://www.w3.org/ns/prov#"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_XSD = "http://www.w3.org/2001/XMLSchema"

# Force the order of child elements as it matters in XML. Not specified
# elements will keep the original order. Label, location, role, type,
# and value attributes will always come after the specified attributes. Any
# other attributes will come after that.
ELEMENT_ORDER = {
    PROV_ACTIVITY: [PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME],
    PROV_GENERATION: [PROV_ATTR_ENTITY, PROV_ATTR_ACTIVITY, PROV_ATTR_TIME],
    PROV_USAGE: [PROV_ATTR_ACTIVITY, PROV_ATTR_ENTITY, PROV_ATTR_TIME],
    PROV_COMMUNICATION: [PROV_ATTR_INFORMED, PROV_ATTR_INFORMANT],
    PROV_START: [PROV_ATTR_ACTIVITY, PROV_ATTR_TRIGGER, PROV_ATTR_STARTER,
                 PROV_ATTR_TIME],
    PROV_END: [PROV_ATTR_ACTIVITY, PROV_ATTR_TRIGGER, PROV_ATTR_ENDER,
               PROV_ATTR_TIME],
    PROV_INVALIDATION: [PROV_ATTR_ENTITY, PROV_ATTR_ACTIVITY, PROV_ATTR_TIME],
    PROV_DERIVATION: [PROV_ATTR_GENERATED_ENTITY, PROV_ATTR_USED_ENTITY,
                      PROV_ATTR_ACTIVITY, PROV_GENERATION, PROV_USAGE],
    PROV_REVISION: [PROV_ATTR_GENERATED_ENTITY, PROV_ATTR_USED_ENTITY,
                    PROV_ATTR_ACTIVITY, PROV_GENERATION, PROV_USAGE],
    PROV_QUOTATION: [PROV_ATTR_GENERATED_ENTITY, PROV_ATTR_USED_ENTITY,
                     PROV_ATTR_ACTIVITY, PROV_GENERATION, PROV_USAGE],
    PROV_ATTRIBUTION: [PROV_ATTR_ENTITY, PROV_AGENT],
    PROV_ASSOCIATION: [PROV_ATTR_ACTIVITY, PROV_AGENT, PROV_ATTR_PLAN],
    PROV_DELEGATION: [PROV_ATTR_DELEGATE, PROV_ATTR_RESPONSIBLE,
                      PROV_ATTR_ACTIVITY],
    PROV_INFLUENCE: [PROV_ATTR_INFLUENCEE, PROV_ATTR_INFLUENCER],
    PROV_SPECIALIZATION: [PROV_ATTR_SPECIFIC_ENTITY, PROV_ATTR_GENERAL_ENTITY],
    PROV_MEMBERSHIP: [PROV_ATTR_COLLECTION, PROV_ATTR_ENTITY]
}

def sorted_attributes(element, attributes):
    """
    Helper function sorting attributes into the order required by PROV-XML.
    """
    attributes = list(attributes)
    if element in ELEMENT_ORDER:
        order = list(ELEMENT_ORDER[element])
    else:
        order = []
    # Append label, location, role, type, and value attributes. This is
    # universal amongst all elements.
    order.extend([PROV_LABEL, PROV_LOCATION, PROV_ROLE, PROV_TYPE,
                  PROV_VALUE])

    sorted_elements = []
    for item in order:
        for e in list(attributes):
            if e[0] != item:
                continue
            sorted_elements.append(e)
            attributes.remove(e)
    # Add remaining attributes.
    sorted_elements.extend(attributes)

    return sorted_elements


class ProvXMLException(prov.Error):
    pass


class ProvXMLSerializer(prov.Serializer):
    def serialize(self, stream, **kwargs):
        # Build the namespace map for lxml and attach it to the root XML
        # element.
        nsmap = {ns.prefix: ns.uri for ns in
                 self.document._namespaces.get_registered_namespaces()}
        if self.document._namespaces._default:
            nsmap[None] = self.document._namespaces._default.uri
        # Add the prov, XSI, and XSD namespaces by default.
        nsmap["prov"] = NS_PROV
        nsmap["xsi"] = NS_XSI
        nsmap["xsd"] = NS_XSD

        xml_root = etree.Element(_ns_prov("document"), nsmap=nsmap)

        for record in self.document._records:
            rec_type = record.get_type()
            rec_label = PROV_N_MAP[rec_type]
            identifier = unicode(record._identifier) \
                if record._identifier else None

            if identifier:
                attrs = {_ns_prov("id"): identifier}
            else:
                attrs = None

            elem = etree.SubElement(xml_root, _ns_prov(rec_label), attrs)

            for attr, value in sorted_attributes(rec_type, record.attributes):
                subelem = etree.SubElement(
                    elem, _ns(attr.namespace.uri, attr.localpart))
                if isinstance(value, prov.model.Literal):
                    subelem.attrib[_ns_xsi("type")] = "%s:%s" % (
                        value.datatype.namespace.prefix,
                        value.datatype.localpart)
                    v = value.value
                elif isinstance(value, datetime.datetime):
                    v = value.isoformat()
                else:
                    v = str(value)

                # If it is a type element and does not yet have an
                # associated xsi type, try to infer it from the value.
                if attr == PROV_TYPE and _ns_xsi("type") not in subelem.attrib:
                    xsd_type = None
                    if isinstance(value, (str, unicode)):
                        xsd_type = XSD_STRING
                    elif isinstance(value, float):
                        xsd_type = XSD_DOUBLE
                    elif isinstance(value, int):
                        xsd_type = XSD_INT
                    elif isinstance(value, bool):
                        xsd_type = XSD_BOOLEAN
                    elif isinstance(value, datetime.datetime):
                        xsd_type = XSD_DATETIME

                    if xsd_type is not None:
                        subelem.attrib[_ns_xsi("type")] = str(xsd_type)

                if attr in PROV_ATTRIBUTE_QNAMES and v:
                    subelem.attrib[_ns_prov("ref")] = v
                else:
                    subelem.text = v

        et = etree.ElementTree(xml_root)
        et.write(stream, pretty_print=True)

    def deserialize(self, stream, **kwargs):
        xml_doc = etree.parse(stream).getroot()

        document = prov.model.ProvDocument()
        for key, value in xml_doc.nsmap.items():
            document.add_namespace(key, value)

        r_nsmap = {value: key for key, value in xml_doc.nsmap.items()}

        for element in xml_doc:
            if isinstance(element, etree._Comment):
                continue
            qname = etree.QName(element)
            if qname.namespace == NS_PROV:
                rec_type = PROV_RECORD_IDS_MAP[qname.localname]

                id_tag = _ns_prov("id")
                rec_id = element.attrib[id_tag] if id_tag in element.attrib \
                    else None

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

                    if len(subel.attrib) > 1:
                        raise NotImplementedError
                    elif len(subel.attrib) == 1:
                        key, value = subel.attrib.items()[0]
                        if key == _ns_xsi("type"):
                            _v = prov.model.Literal(
                                subel.text,
                                XSD[value.split(":")[1]])
                        elif key == _ns_prov("ref"):
                            _v = value
                        else:
                            raise NotImplementedError
                    else:
                        _v = subel.text
                    d.append((_t, _v))
                document.add_record(rec_type, rec_id, attributes,
                                    other_attributes)
            else:
                raise NotImplementedError
        return document


def _ns(ns, tag):
    return "{%s}%s" % (ns, tag)


def _ns_prov(tag):
    return _ns(NS_PROV, tag)


def _ns_xsi(tag):
    return _ns(NS_XSI, tag)

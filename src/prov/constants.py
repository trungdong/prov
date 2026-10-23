"""The PROV vocabulary as module-level data: namespaces, qualified names and tables."""

from prov.identifier import Namespace

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


#: The ``xsd`` namespace, ``http://www.w3.org/2001/XMLSchema#``.
XSD = Namespace("xsd", "http://www.w3.org/2001/XMLSchema#")
#: The ``prov`` namespace, ``http://www.w3.org/ns/prov#``.
PROV = Namespace("prov", "http://www.w3.org/ns/prov#")
#: The ``xsi`` namespace, ``http://www.w3.org/2001/XMLSchema-instance``.
XSI = Namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

#  C1. Entities/Activities
#: The record type ``prov:Entity``.
PROV_ENTITY = PROV["Entity"]
#: The record type ``prov:Activity``.
PROV_ACTIVITY = PROV["Activity"]
#: The record type ``prov:Generation``.
PROV_GENERATION = PROV["Generation"]
#: The record type ``prov:Usage``.
PROV_USAGE = PROV["Usage"]
#: The record type ``prov:Communication``.
PROV_COMMUNICATION = PROV["Communication"]
#: The record type ``prov:Start``.
PROV_START = PROV["Start"]
#: The record type ``prov:End``.
PROV_END = PROV["End"]
#: The record type ``prov:Invalidation``.
PROV_INVALIDATION = PROV["Invalidation"]

#  C2. Derivations
#: The record type ``prov:Derivation``.
PROV_DERIVATION = PROV["Derivation"]

#  C3. Agents/Responsibility
#: The record type ``prov:Agent``.
PROV_AGENT = PROV["Agent"]
#: The record type ``prov:Attribution``.
PROV_ATTRIBUTION = PROV["Attribution"]
#: The record type ``prov:Association``.
PROV_ASSOCIATION = PROV["Association"]
#: The record type ``prov:Delegation``.
PROV_DELEGATION = PROV["Delegation"]
#: The record type ``prov:Influence``.
PROV_INFLUENCE = PROV["Influence"]
#  C4. Bundles
#: The record type ``prov:Bundle``.
PROV_BUNDLE = PROV["Bundle"]
#  C5. Alternate
#: The record type ``prov:Alternate``.
PROV_ALTERNATE = PROV["Alternate"]
#: The record type ``prov:Specialization``.
PROV_SPECIALIZATION = PROV["Specialization"]
#: The record type ``prov:Mention``.
PROV_MENTION = PROV["Mention"]
#  C6. Collections
#: The record type ``prov:Membership``.
PROV_MEMBERSHIP = PROV["Membership"]

# Productions 24 to 26 of PROV-N give these relations neither an identifier
# nor an attribute block. Underscore-named so the star import into prov.model
# does not export it.
_PROV_N_BARE_RELATIONS = frozenset(
    {PROV_ALTERNATE, PROV_SPECIALIZATION, PROV_MEMBERSHIP}
)

PROV_N_MAP = {
    PROV_ENTITY: "entity",
    PROV_ACTIVITY: "activity",
    PROV_GENERATION: "wasGeneratedBy",
    PROV_USAGE: "used",
    PROV_COMMUNICATION: "wasInformedBy",
    PROV_START: "wasStartedBy",
    PROV_END: "wasEndedBy",
    PROV_INVALIDATION: "wasInvalidatedBy",
    PROV_DERIVATION: "wasDerivedFrom",
    PROV_AGENT: "agent",
    PROV_ATTRIBUTION: "wasAttributedTo",
    PROV_ASSOCIATION: "wasAssociatedWith",
    PROV_DELEGATION: "actedOnBehalfOf",
    PROV_INFLUENCE: "wasInfluencedBy",
    PROV_ALTERNATE: "alternateOf",
    PROV_SPECIALIZATION: "specializationOf",
    PROV_MENTION: "mentionOf",
    PROV_MEMBERSHIP: "hadMember",
    PROV_BUNDLE: "bundle",
}
"""Maps each top-level PROV record type QualifiedName to its PROV-N keyword."""

# Records defined as subtypes in PROV-N but top level types in for example
# PROV XML also need a mapping.
ADDITIONAL_N_MAP = {
    PROV["Revision"]: "wasRevisionOf",
    PROV["Quotation"]: "wasQuotedFrom",
    PROV["PrimarySource"]: "hadPrimarySource",
    PROV["SoftwareAgent"]: "softwareAgent",
    PROV["Person"]: "person",
    PROV["Organization"]: "organization",
    PROV["Plan"]: "plan",
    PROV["Collection"]: "collection",
    PROV["EmptyCollection"]: "emptyCollection",
}
"""Maps PROV-N subtype QualifiedNames (top-level types in e.g. PROV-XML) to
their PROV-N keyword; not included in :data:`PROV_N_MAP` itself."""

# Maps qualified names from the PROV namespace to their base class. If it
# has no baseclass it maps to itsself. This is needed for example for PROV
# XML (de)serializer where extended types are used a lot.
PROV_BASE_CLS = {
    PROV_ENTITY: PROV_ENTITY,
    PROV_ACTIVITY: PROV_ACTIVITY,
    PROV_GENERATION: PROV_GENERATION,
    PROV_USAGE: PROV_USAGE,
    PROV_COMMUNICATION: PROV_COMMUNICATION,
    PROV_START: PROV_START,
    PROV_END: PROV_END,
    PROV_INVALIDATION: PROV_INVALIDATION,
    PROV_DERIVATION: PROV_DERIVATION,
    PROV["Revision"]: PROV_DERIVATION,
    PROV["Quotation"]: PROV_DERIVATION,
    PROV["PrimarySource"]: PROV_DERIVATION,
    PROV_AGENT: PROV_AGENT,
    PROV["SoftwareAgent"]: PROV_AGENT,
    PROV["Person"]: PROV_AGENT,
    PROV["Organization"]: PROV_AGENT,
    PROV_ATTRIBUTION: PROV_ATTRIBUTION,
    PROV_ASSOCIATION: PROV_ASSOCIATION,
    PROV["Plan"]: PROV_ENTITY,
    PROV_DELEGATION: PROV_DELEGATION,
    PROV_INFLUENCE: PROV_INFLUENCE,
    PROV_ALTERNATE: PROV_ALTERNATE,
    PROV_SPECIALIZATION: PROV_SPECIALIZATION,
    PROV_MENTION: PROV_MENTION,
    PROV["Collection"]: PROV_ENTITY,
    PROV["EmptyCollection"]: PROV_ENTITY,
    PROV_MEMBERSHIP: PROV_MEMBERSHIP,
    PROV_BUNDLE: PROV_ENTITY,
}
"""Maps each PROV record/subtype QualifiedName to its base record type
QualifiedName (mapping to itself if it has no base type)."""

# Identifiers for PROV's attributes
#: The formal attribute ``prov:entity``.
PROV_ATTR_ENTITY = PROV["entity"]
#: The formal attribute ``prov:activity``.
PROV_ATTR_ACTIVITY = PROV["activity"]
#: The formal attribute ``prov:trigger``.
PROV_ATTR_TRIGGER = PROV["trigger"]
#: The formal attribute ``prov:informed``.
PROV_ATTR_INFORMED = PROV["informed"]
#: The formal attribute ``prov:informant``.
PROV_ATTR_INFORMANT = PROV["informant"]
#: The formal attribute ``prov:starter``.
PROV_ATTR_STARTER = PROV["starter"]
#: The formal attribute ``prov:ender``.
PROV_ATTR_ENDER = PROV["ender"]
#: The formal attribute ``prov:agent``.
PROV_ATTR_AGENT = PROV["agent"]
#: The formal attribute ``prov:plan``.
PROV_ATTR_PLAN = PROV["plan"]
#: The formal attribute ``prov:delegate``.
PROV_ATTR_DELEGATE = PROV["delegate"]
#: The formal attribute ``prov:responsible``.
PROV_ATTR_RESPONSIBLE = PROV["responsible"]
#: The formal attribute ``prov:generatedEntity``.
PROV_ATTR_GENERATED_ENTITY = PROV["generatedEntity"]
#: The formal attribute ``prov:usedEntity``.
PROV_ATTR_USED_ENTITY = PROV["usedEntity"]
#: The formal attribute ``prov:generation``.
PROV_ATTR_GENERATION = PROV["generation"]
#: The formal attribute ``prov:usage``.
PROV_ATTR_USAGE = PROV["usage"]
#: The formal attribute ``prov:specificEntity``.
PROV_ATTR_SPECIFIC_ENTITY = PROV["specificEntity"]
#: The formal attribute ``prov:generalEntity``.
PROV_ATTR_GENERAL_ENTITY = PROV["generalEntity"]
#: The formal attribute ``prov:alternate1``.
PROV_ATTR_ALTERNATE1 = PROV["alternate1"]
#: The formal attribute ``prov:alternate2``.
PROV_ATTR_ALTERNATE2 = PROV["alternate2"]
#: The formal attribute ``prov:bundle``.
PROV_ATTR_BUNDLE = PROV["bundle"]
#: The formal attribute ``prov:influencee``.
PROV_ATTR_INFLUENCEE = PROV["influencee"]
#: The formal attribute ``prov:influencer``.
PROV_ATTR_INFLUENCER = PROV["influencer"]
#: The formal attribute ``prov:collection``.
PROV_ATTR_COLLECTION = PROV["collection"]

#  Literal properties
#: The literal-valued formal attribute ``prov:time``.
PROV_ATTR_TIME = PROV["time"]
#: The literal-valued formal attribute ``prov:startTime``.
PROV_ATTR_STARTTIME = PROV["startTime"]
#: The literal-valued formal attribute ``prov:endTime``.
PROV_ATTR_ENDTIME = PROV["endTime"]


PROV_ATTRIBUTE_QNAMES = {
    PROV_ATTR_ENTITY,
    PROV_ATTR_ACTIVITY,
    PROV_ATTR_TRIGGER,
    PROV_ATTR_INFORMED,
    PROV_ATTR_INFORMANT,
    PROV_ATTR_STARTER,
    PROV_ATTR_ENDER,
    PROV_ATTR_AGENT,
    PROV_ATTR_PLAN,
    PROV_ATTR_DELEGATE,
    PROV_ATTR_RESPONSIBLE,
    PROV_ATTR_GENERATED_ENTITY,
    PROV_ATTR_USED_ENTITY,
    PROV_ATTR_GENERATION,
    PROV_ATTR_USAGE,
    PROV_ATTR_SPECIFIC_ENTITY,
    PROV_ATTR_GENERAL_ENTITY,
    PROV_ATTR_ALTERNATE1,
    PROV_ATTR_ALTERNATE2,
    PROV_ATTR_BUNDLE,
    PROV_ATTR_INFLUENCEE,
    PROV_ATTR_INFLUENCER,
    PROV_ATTR_COLLECTION,
}
"""Set of QualifiedName-valued formal attributes of PROV records."""
PROV_ATTRIBUTE_LITERALS = {PROV_ATTR_TIME, PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME}
"""Set of literal-valued (non-QualifiedName) formal attributes of PROV records."""

# Set of formal attributes of PROV records
PROV_ATTRIBUTES = PROV_ATTRIBUTE_QNAMES | PROV_ATTRIBUTE_LITERALS
"""All formal attributes of PROV records, QualifiedName- and literal-valued."""
PROV_RECORD_ATTRIBUTES = [(attr, str(attr)) for attr in PROV_ATTRIBUTES]
"""``(QualifiedName, str)`` pairs for every entry in :data:`PROV_ATTRIBUTES`."""

PROV_RECORD_IDS_MAP = {
    PROV_N_MAP[rec_type_id]: rec_type_id for rec_type_id in PROV_N_MAP
}
"""Inverse of :data:`PROV_N_MAP`: maps each PROV-N keyword back to its record
type QualifiedName."""
PROV_ID_ATTRIBUTES_MAP = dict(PROV_RECORD_ATTRIBUTES)
"""Maps each formal attribute QualifiedName to its string form."""
# inverse of PROV_ID_ATTRIBUTES_MAP: maps each attribute name back to its QName
PROV_ATTRIBUTES_ID_MAP = {
    attribute: prov_id for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES
}
"""Inverse of :data:`PROV_ID_ATTRIBUTES_MAP`: maps each attribute's string
form back to its QualifiedName."""

# Extra definition for convenience
#: The attribute ``prov:type``: a further type asserted on a record.
PROV_TYPE = PROV["type"]
#: The attribute ``prov:label``: a human-readable label.
PROV_LABEL = PROV["label"]
#: The attribute ``prov:value``: an entity's value.
PROV_VALUE = PROV["value"]
#: The attribute ``prov:location``.
PROV_LOCATION = PROV["location"]
#: The attribute ``prov:role`` of an entity or agent in a relation.
PROV_ROLE = PROV["role"]

#: The datatype ``prov:QUALIFIED_NAME`` of a literal holding a qualified name.
PROV_QUALIFIEDNAME = PROV["QUALIFIED_NAME"]
#: The datatype ``prov:InternationalizedString`` of a language-tagged literal.
PROV_INTERNATIONALIZEDSTRING = PROV["InternationalizedString"]

# XSD DATA TYPES
#: The datatype ``xsd:anyURI``.
XSD_ANYURI = XSD["anyURI"]
#: The datatype ``xsd:QName``.
XSD_QNAME = XSD["QName"]
#: The datatype ``xsd:dateTime``.
XSD_DATETIME = XSD["dateTime"]
#: The datatype ``xsd:time``.
XSD_TIME = XSD["time"]
#: The datatype ``xsd:date``.
XSD_DATE = XSD["date"]
#: The datatype ``xsd:string``.
XSD_STRING = XSD["string"]
#: The datatype ``xsd:boolean``.
XSD_BOOLEAN = XSD["boolean"]
# All XSD Integer types
#: The datatype ``xsd:integer``.
XSD_INTEGER = XSD["integer"]
#: The datatype ``xsd:long``.
XSD_LONG = XSD["long"]
#: The datatype ``xsd:int``.
XSD_INT = XSD["int"]
#: The datatype ``xsd:short``.
XSD_SHORT = XSD["short"]
#: The datatype ``xsd:byte``.
XSD_BYTE = XSD["byte"]
#: The datatype ``xsd:nonNegativeInteger``.
XSD_NONNEGATIVEINTEGER = XSD["nonNegativeInteger"]
#: The datatype ``xsd:unsignedLong``.
XSD_UNSIGNEDLONG = XSD["unsignedLong"]
#: The datatype ``xsd:unsignedInt``.
XSD_UNSIGNEDINT = XSD["unsignedInt"]
#: The datatype ``xsd:unsignedShort``.
XSD_UNSIGNEDSHORT = XSD["unsignedShort"]
#: The datatype ``xsd:unsignedByte``.
XSD_UNSIGNEDBYTE = XSD["unsignedByte"]
#: The datatype ``xsd:positiveInteger``.
XSD_POSITIVEINTEGER = XSD["positiveInteger"]
#: The datatype ``xsd:nonPositiveInteger``.
XSD_NONPOSITIVEINTEGER = XSD["nonPositiveInteger"]
#: The datatype ``xsd:negativeInteger``.
XSD_NEGATIVEINTEGER = XSD["negativeInteger"]
# All XSD real number types
#: The datatype ``xsd:float``.
XSD_FLOAT = XSD["float"]
#: The datatype ``xsd:double``.
XSD_DOUBLE = XSD["double"]
#: The datatype ``xsd:decimal``.
XSD_DECIMAL = XSD["decimal"]

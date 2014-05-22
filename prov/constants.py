#  # PROV record constants - PROV-DM

# Built-in namespaces
from prov.identifier import Namespace

XSD = Namespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
PROV = Namespace('prov', 'http://www.w3.org/ns/prov#')

#  C1. Entities/Activities
PROV_ENTITY = PROV['Entity']
PROV_ACTIVITY = PROV['Activity']
PROV_GENERATION = PROV['Generation']
PROV_USAGE = PROV['Usage']
PROV_COMMUNICATION = PROV['Communication']
PROV_START = PROV['Start']
PROV_END = PROV['End']
PROV_INVALIDATION = PROV['Invalidation']

#  C2. Derivations
PROV_DERIVATION = PROV['Derivation']

#  C3. Agents/Responsibility
PROV_AGENT = PROV['Agent']
PROV_ATTRIBUTION = PROV['Attribution']
PROV_ASSOCIATION = PROV['Association']
PROV_DELEGATION = PROV['Delegation']
PROV_INFLUENCE = PROV['Influence']
#  C4. Bundles
PROV_BUNDLE = PROV['Bundle']
#  C5. Alternate
PROV_ALTERNATE = PROV['Alternate']
PROV_SPECIALIZATION = PROV['Specialization']
PROV_MENTION = PROV['Mention']
#  C6. Collections
PROV_MEMBERSHIP = PROV['Membership']

PROV_N_MAP = {
    PROV_ENTITY:               u'entity',
    PROV_ACTIVITY:             u'activity',
    PROV_GENERATION:           u'wasGeneratedBy',
    PROV_USAGE:                u'used',
    PROV_COMMUNICATION:        u'wasInformedBy',
    PROV_START:                u'wasStartedBy',
    PROV_END:                  u'wasEndedBy',
    PROV_INVALIDATION:         u'wasInvalidatedBy',
    PROV_DERIVATION:           u'wasDerivedFrom',
    PROV_AGENT:                u'agent',
    PROV_ATTRIBUTION:          u'wasAttributedTo',
    PROV_ASSOCIATION:          u'wasAssociatedWith',
    PROV_DELEGATION:           u'actedOnBehalfOf',
    PROV_INFLUENCE:            u'wasInfluencedBy',
    PROV_ALTERNATE:            u'alternateOf',
    PROV_SPECIALIZATION:       u'specializationOf',
    PROV_MENTION:              u'mentionOf',
    PROV_MEMBERSHIP:           u'hadMember',
    PROV_BUNDLE:               u'bundle',
}

# Identifiers for PROV's attributes
PROV_ATTR_ENTITY = PROV['entity']
PROV_ATTR_ACTIVITY = PROV['activity']
PROV_ATTR_TRIGGER = PROV['trigger']
PROV_ATTR_INFORMED = PROV['informed']
PROV_ATTR_INFORMANT = PROV['informant']
PROV_ATTR_STARTER = PROV['starter']
PROV_ATTR_ENDER = PROV['ender']
PROV_ATTR_AGENT = PROV['agent']
PROV_ATTR_PLAN = PROV['plan']
PROV_ATTR_DELEGATE = PROV['delegate']
PROV_ATTR_RESPONSIBLE = PROV['responsible']
PROV_ATTR_GENERATED_ENTITY = PROV['generatedEntity']
PROV_ATTR_USED_ENTITY = PROV['usedEntity']
PROV_ATTR_GENERATION = PROV['generation']
PROV_ATTR_USAGE = PROV['usage']
PROV_ATTR_SPECIFIC_ENTITY = PROV['specificEntity']
PROV_ATTR_GENERAL_ENTITY = PROV['generalEntity']
PROV_ATTR_ALTERNATE1 = PROV['alternate1']
PROV_ATTR_ALTERNATE2 = PROV['alternate2']
PROV_ATTR_BUNDLE = PROV['bundle']
PROV_ATTR_INFLUENCEE = PROV['influencee']
PROV_ATTR_INFLUENCER = PROV['influencer']
PROV_ATTR_COLLECTION = PROV['collection']

#  Literal properties
PROV_ATTR_TIME = PROV['time']
PROV_ATTR_STARTTIME = PROV['startTime']
PROV_ATTR_ENDTIME = PROV['endTime']


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
    PROV_ATTR_COLLECTION
}
PROV_ATTRIBUTE_LITERALS = {PROV_ATTR_TIME, PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME}
# Set of formal attributes of PROV records
PROV_ATTRIBUTES = PROV_ATTRIBUTE_QNAMES | PROV_ATTRIBUTE_LITERALS
PROV_RECORD_ATTRIBUTES = list((attr, unicode(attr)) for attr in PROV_ATTRIBUTES)

PROV_RECORD_IDS_MAP = dict((PROV_N_MAP[rec_type_id], rec_type_id) for rec_type_id in PROV_N_MAP)
PROV_ID_ATTRIBUTES_MAP = dict((prov_id, attribute) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)
PROV_ATTRIBUTES_ID_MAP = dict((attribute, prov_id) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)

# Extra definition for convenience
PROV_TYPE = PROV['type']
PROV_LABEL = PROV['label']
PROV_VALUE = PROV['value']

#  # PROV record constants - PROV-DM

# Built-in namespaces
from prov.identifier import Namespace

XSD = Namespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
PROV = Namespace('prov', 'http://www.w3.org/ns/prov#')

#  C1. Entities/Activities
PROV_REC_ENTITY = 1
PROV_REC_ACTIVITY = 2
PROV_REC_GENERATION = 11
PROV_REC_USAGE = 12
PROV_REC_COMMUNICATION = 13
PROV_REC_START = 14
PROV_REC_END = 15
PROV_REC_INVALIDATION = 16

#  C2. Derivations
PROV_REC_DERIVATION = 21

#  C3. Agents/Responsibility
PROV_REC_AGENT = 3
PROV_REC_ATTRIBUTION = 31
PROV_REC_ASSOCIATION = 32
PROV_REC_DELEGATION = 33
PROV_REC_INFLUENCE = 34
#  C4. Bundles
PROV_REC_BUNDLE = 4  # This is the lowest value, so bundle(s) in JSON will be decoded first
#  C5. Alternate
PROV_REC_ALTERNATE = 51
PROV_REC_SPECIALIZATION = 52
PROV_REC_MENTION = 53
#  C6. Collections
PROV_REC_MEMBERSHIP = 61

PROV_RECORD_TYPES = (
    (PROV_REC_ENTITY, u'Entity'),
    (PROV_REC_ACTIVITY, u'Activity'),
    (PROV_REC_GENERATION, u'Generation'),
    (PROV_REC_USAGE, u'Usage'),
    (PROV_REC_COMMUNICATION, u'Communication'),
    (PROV_REC_START, u'Start'),
    (PROV_REC_END, u'End'),
    (PROV_REC_INVALIDATION, u'Invalidation'),
    (PROV_REC_DERIVATION, u'Derivation'),
    (PROV_REC_AGENT, u'Agent'),
    (PROV_REC_ATTRIBUTION, u'Attribution'),
    (PROV_REC_ASSOCIATION, u'Association'),
    (PROV_REC_DELEGATION, u'Delegation'),
    (PROV_REC_INFLUENCE, u'Influence'),
    (PROV_REC_BUNDLE, u'Bundle'),
    (PROV_REC_ALTERNATE, u'Alternate'),
    (PROV_REC_SPECIALIZATION, u'Specialization'),
    (PROV_REC_MENTION, u'Mention'),
    (PROV_REC_MEMBERSHIP, u'Membership'),
)

PROV_N_MAP = {
    PROV_REC_ENTITY:               u'entity',
    PROV_REC_ACTIVITY:             u'activity',
    PROV_REC_GENERATION:           u'wasGeneratedBy',
    PROV_REC_USAGE:                u'used',
    PROV_REC_COMMUNICATION:        u'wasInformedBy',
    PROV_REC_START:                u'wasStartedBy',
    PROV_REC_END:                  u'wasEndedBy',
    PROV_REC_INVALIDATION:         u'wasInvalidatedBy',
    PROV_REC_DERIVATION:           u'wasDerivedFrom',
    PROV_REC_AGENT:                u'agent',
    PROV_REC_ATTRIBUTION:          u'wasAttributedTo',
    PROV_REC_ASSOCIATION:          u'wasAssociatedWith',
    PROV_REC_DELEGATION:           u'actedOnBehalfOf',
    PROV_REC_INFLUENCE:            u'wasInfluencedBy',
    PROV_REC_ALTERNATE:            u'alternateOf',
    PROV_REC_SPECIALIZATION:       u'specializationOf',
    PROV_REC_MENTION:              u'mentionOf',
    PROV_REC_MEMBERSHIP:           u'hadMember',
    PROV_REC_BUNDLE:               u'bundle',
}

#  # Identifiers for PROV's attributes
PROV_ATTR_ENTITY = 1
PROV_ATTR_ACTIVITY = 2
PROV_ATTR_TRIGGER = 3
PROV_ATTR_INFORMED = 4
PROV_ATTR_INFORMANT = 5
PROV_ATTR_STARTER = 6
PROV_ATTR_ENDER = 7
PROV_ATTR_AGENT = 8
PROV_ATTR_PLAN = 9
PROV_ATTR_DELEGATE = 10
PROV_ATTR_RESPONSIBLE = 11
PROV_ATTR_GENERATED_ENTITY = 12
PROV_ATTR_USED_ENTITY = 13
PROV_ATTR_GENERATION = 14
PROV_ATTR_USAGE = 15
PROV_ATTR_SPECIFIC_ENTITY = 16
PROV_ATTR_GENERAL_ENTITY = 17
PROV_ATTR_ALTERNATE1 = 18
PROV_ATTR_ALTERNATE2 = 19
PROV_ATTR_BUNDLE = 20
PROV_ATTR_INFLUENCEE = 21
PROV_ATTR_INFLUENCER = 22
PROV_ATTR_COLLECTION = 23

#  Literal properties
PROV_ATTR_TIME = 100
PROV_ATTR_STARTTIME = 101
PROV_ATTR_ENDTIME = 102

PROV_RECORD_ATTRIBUTES = (
    #  Relations properties
    (PROV_ATTR_ENTITY, u'prov:entity'),
    (PROV_ATTR_ACTIVITY, u'prov:activity'),
    (PROV_ATTR_TRIGGER, u'prov:trigger'),
    (PROV_ATTR_INFORMED, u'prov:informed'),
    (PROV_ATTR_INFORMANT, u'prov:informant'),
    (PROV_ATTR_STARTER, u'prov:starter'),
    (PROV_ATTR_ENDER, u'prov:ender'),
    (PROV_ATTR_AGENT, u'prov:agent'),
    (PROV_ATTR_PLAN, u'prov:plan'),
    (PROV_ATTR_DELEGATE, u'prov:delegate'),
    (PROV_ATTR_RESPONSIBLE, u'prov:responsible'),
    (PROV_ATTR_GENERATED_ENTITY, u'prov:generatedEntity'),
    (PROV_ATTR_USED_ENTITY, u'prov:usedEntity'),
    (PROV_ATTR_GENERATION, u'prov:generation'),
    (PROV_ATTR_USAGE, u'prov:usage'),
    (PROV_ATTR_SPECIFIC_ENTITY, u'prov:specificEntity'),
    (PROV_ATTR_GENERAL_ENTITY, u'prov:generalEntity'),
    (PROV_ATTR_ALTERNATE1, u'prov:alternate1'),
    (PROV_ATTR_ALTERNATE2, u'prov:alternate2'),
    (PROV_ATTR_BUNDLE, u'prov:bundle'),
    (PROV_ATTR_INFLUENCEE, u'prov:influencee'),
    (PROV_ATTR_INFLUENCER, u'prov:influencer'),
    (PROV_ATTR_COLLECTION, u'prov:collection'),
    #  Literal properties
    (PROV_ATTR_TIME, u'prov:time'),
    (PROV_ATTR_STARTTIME, u'prov:startTime'),
    (PROV_ATTR_ENDTIME, u'prov:endTime'),
)

PROV_ATTRIBUTE_LITERALS = {PROV_ATTR_TIME, PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME}

PROV_RECORD_IDS_MAP = dict((PROV_N_MAP[rec_type_id], rec_type_id) for rec_type_id in PROV_N_MAP)
PROV_ID_ATTRIBUTES_MAP = dict((prov_id, attribute) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)
PROV_ATTRIBUTES_ID_MAP = dict((attribute, prov_id) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)


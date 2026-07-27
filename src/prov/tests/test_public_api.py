"""Guards the public API surface for the 2.x line.

Two different questions are answered here:

- ``test_names_importable`` checks *intent*: a curated allowlist of the names
  that are load-bearing public API and must stay importable from their
  historic location. It is deliberately incomplete -- it does not enumerate
  everything ``prov.model`` exports.
- ``test_prov_model_namespace_snapshot`` checks *fact*: exactly what
  ``dir(prov.model)`` exports today, compared against a checked-in list.
  ``prov/model/__init__.py`` re-exports every public name at its historic
  ``prov.model`` location and then deletes the submodule attributes,
  deliberately freezing ``dir(prov.model)`` to the pre-split namespace; this
  test is what actually holds that freeze in place.
"""

import importlib
import importlib.util
import io

import prov.model
import prov.serializers
from prov.model import ProvDocument
from prov.tests.examples import primer_example

PUBLIC_API = {
    "prov": ["Error", "read"],
    "prov.model": [
        # containers
        "ProvDocument",
        "ProvBundle",
        # base classes
        "ProvRecord",
        "ProvElement",
        "ProvRelation",
        # elements
        "ProvEntity",
        "ProvActivity",
        "ProvAgent",
        # relations
        "ProvGeneration",
        "ProvUsage",
        "ProvCommunication",
        "ProvStart",
        "ProvEnd",
        "ProvInvalidation",
        "ProvDerivation",
        "ProvAttribution",
        "ProvAssociation",
        "ProvDelegation",
        "ProvInfluence",
        "ProvSpecialization",
        "ProvAlternate",
        "ProvMention",
        "ProvMembership",
        # exceptions
        "ProvException",
        "ProvWarning",
        "ProvExceptionInvalidQualifiedName",
        "ProvElementIdentifierRequired",
        "ProvUnificationError",
        # identifiers & literals (historically importable from prov.model too)
        "Namespace",
        "QualifiedName",
        "Identifier",
        "Literal",
        "NamespaceManager",
        "PROV",
        "XSD",
        "XSI",
        "parse_xsd_datetime",
        "sorted_attributes",
    ],
    "prov.identifier": ["Identifier", "QualifiedName", "Namespace"],
    "prov.constants": [
        "PROV_ENTITY",
        "PROV_ACTIVITY",
        "PROV_AGENT",
        "PROV_GENERATION",
        "PROV_USAGE",
        "PROV_COMMUNICATION",
        "PROV_START",
        "PROV_END",
        "PROV_INVALIDATION",
        "PROV_DERIVATION",
        "PROV_ATTRIBUTION",
        "PROV_ASSOCIATION",
        "PROV_DELEGATION",
        "PROV_INFLUENCE",
        "PROV_SPECIALIZATION",
        "PROV_ALTERNATE",
        "PROV_MENTION",
        "PROV_MEMBERSHIP",
        "PROV_BUNDLE",
        "PROV_N_MAP",
        "PROV_BASE_CLS",
        "PROV_TYPE",
        "PROV_LABEL",
        "PROV_VALUE",
        "PROV_LOCATION",
        "PROV_ROLE",
    ],
    "prov.serializers": ["get", "Serializer", "Registry", "DoNotExist"],
    "prov.dot": ["prov_to_dot"],
    "prov.graph": ["prov_to_graph", "graph_to_prov"],
}

# Modules importable only when their optional extra is installed (3.0);
# the informative failure without the extra is covered by test_minimal_install.
OPTIONAL_MODULE_REQUIREMENTS = {
    "prov.dot": "pydot",
    "prov.graph": "networkx",
}


# Exact snapshot of the non-dunder names in sorted(dir(prov.model)),
# generated at commit dccff00217b745a8107379742a7157366703b5bd (166 names).
# Unlike PUBLIC_API above, this is not curated -- it is every non-dunder
# name the module exports, including re-exported stdlib/typing imports and
# internal constants, because the freeze in prov/model/__init__.py applies
# to all of them.
#
# Dunder names (__author__, __file__, __loader__, ...) are excluded: some
# are CPython import-machinery details (__cached__, __file__, __loader__,
# __path__, __spec__) that can legitimately vary or go missing under a
# frozen build, zipapp, or non-standard loader, and asserting on them would
# misdirect a future contributor toward "fix the code" when the real cause
# is the install mechanism.
#
# If this test fails:
# - an *added* name from an intentional change (new alias, new constant,
#   ...) means updating this list in the same PR;
# - a *removed* or *renamed* name is a breaking change to a namespace that
#   is deliberately frozen -- do not "fix" the test to match, fix the code
#   (or, if the removal is genuinely intended, that decision belongs in the
#   PR description, not a silent test edit).
PROV_MODEL_DIR_SNAPSHOT = [
    "ADDITIONAL_N_MAP",
    "ActivityRef",
    "AgentRef",
    "Any",
    "AttributePair",
    "Callable",
    "DATATYPE_PARSERS",
    "DEFAULT_NAMESPACES",
    "DatetimeOrStr",
    "EntityRef",
    "Error",
    "GenerationRef",
    "IOBase",
    "Identifier",
    "InfluencerRef",
    "Iterable",
    "Literal",
    "NSCollection",
    "NameValuePair",
    "Namespace",
    "NamespaceManager",
    "OptionalID",
    "PROV",
    "PROV_ACTIVITY",
    "PROV_AGENT",
    "PROV_ALTERNATE",
    "PROV_ASSOCIATION",
    "PROV_ATTRIBUTES",
    "PROV_ATTRIBUTES_ID_MAP",
    "PROV_ATTRIBUTE_LITERALS",
    "PROV_ATTRIBUTE_QNAMES",
    "PROV_ATTRIBUTION",
    "PROV_ATTR_ACTIVITY",
    "PROV_ATTR_AGENT",
    "PROV_ATTR_ALTERNATE1",
    "PROV_ATTR_ALTERNATE2",
    "PROV_ATTR_BUNDLE",
    "PROV_ATTR_COLLECTION",
    "PROV_ATTR_DELEGATE",
    "PROV_ATTR_ENDER",
    "PROV_ATTR_ENDTIME",
    "PROV_ATTR_ENTITY",
    "PROV_ATTR_GENERAL_ENTITY",
    "PROV_ATTR_GENERATED_ENTITY",
    "PROV_ATTR_GENERATION",
    "PROV_ATTR_INFLUENCEE",
    "PROV_ATTR_INFLUENCER",
    "PROV_ATTR_INFORMANT",
    "PROV_ATTR_INFORMED",
    "PROV_ATTR_PLAN",
    "PROV_ATTR_RESPONSIBLE",
    "PROV_ATTR_SPECIFIC_ENTITY",
    "PROV_ATTR_STARTER",
    "PROV_ATTR_STARTTIME",
    "PROV_ATTR_TIME",
    "PROV_ATTR_TRIGGER",
    "PROV_ATTR_USAGE",
    "PROV_ATTR_USED_ENTITY",
    "PROV_BASE_CLS",
    "PROV_BUNDLE",
    "PROV_COMMUNICATION",
    "PROV_DELEGATION",
    "PROV_DERIVATION",
    "PROV_END",
    "PROV_ENTITY",
    "PROV_GENERATION",
    "PROV_ID_ATTRIBUTES_MAP",
    "PROV_INFLUENCE",
    "PROV_INTERNATIONALIZEDSTRING",
    "PROV_INVALIDATION",
    "PROV_LABEL",
    "PROV_LOCATION",
    "PROV_MEMBERSHIP",
    "PROV_MENTION",
    "PROV_N_MAP",
    "PROV_QUALIFIEDNAME",
    "PROV_RECORD_ATTRIBUTES",
    "PROV_RECORD_IDS_MAP",
    "PROV_REC_CLS",
    "PROV_ROLE",
    "PROV_SPECIALIZATION",
    "PROV_START",
    "PROV_TYPE",
    "PROV_USAGE",
    "PROV_VALUE",
    "PathLike",
    "ProvActivity",
    "ProvAgent",
    "ProvAlternate",
    "ProvAssociation",
    "ProvAttribution",
    "ProvBundle",
    "ProvCommunication",
    "ProvDelegation",
    "ProvDerivation",
    "ProvDocument",
    "ProvElement",
    "ProvElementIdentifierRequired",
    "ProvEnd",
    "ProvEntity",
    "ProvException",
    "ProvExceptionInvalidQualifiedName",
    "ProvGeneration",
    "ProvInfluence",
    "ProvInvalidation",
    "ProvMembership",
    "ProvMention",
    "ProvRecord",
    "ProvRelation",
    "ProvSpecialization",
    "ProvStart",
    "ProvUnificationError",
    "ProvUsage",
    "ProvWarning",
    "QualifiedName",
    "QualifiedNameCandidate",
    "RecordAttributesArg",
    "StreamOrPath",
    "SupportedXSDParsedTypes",
    "Union",
    "UsageRef",
    "XSD",
    "XSD_ANYURI",
    "XSD_BOOLEAN",
    "XSD_BYTE",
    "XSD_DATATYPE_PARSERS",
    "XSD_DATE",
    "XSD_DATETIME",
    "XSD_DECIMAL",
    "XSD_DOUBLE",
    "XSD_FLOAT",
    "XSD_INT",
    "XSD_INTEGER",
    "XSD_LONG",
    "XSD_NEGATIVEINTEGER",
    "XSD_NONNEGATIVEINTEGER",
    "XSD_NONPOSITIVEINTEGER",
    "XSD_POSITIVEINTEGER",
    "XSD_QNAME",
    "XSD_SHORT",
    "XSD_STRING",
    "XSD_TIME",
    "XSD_UNSIGNEDBYTE",
    "XSD_UNSIGNEDINT",
    "XSD_UNSIGNEDLONG",
    "XSD_UNSIGNEDSHORT",
    "XSI",
    "canonical_xsd_datatype",
    "datetime",
    "defaultdict",
    "encoding_provn_value",
    "first",
    "io",
    "itertools",
    "logger",
    "logging",
    "os",
    "parse_boolean",
    "parse_xsd_datetime",
    "parse_xsd_types",
    "serializers",
    "shutil",
    "sorted_attributes",
    "tempfile",
    "typing",
    "urlparse",
]


def test_prov_model_namespace_snapshot():
    actual = sorted(
        name
        for name in dir(prov.model)
        if not (name.startswith("__") and name.endswith("__"))
    )
    expected = sorted(PROV_MODEL_DIR_SNAPSHOT)
    added = sorted(set(actual) - set(expected))
    removed = sorted(set(expected) - set(actual))
    assert not added and not removed, (
        f"prov.model namespace drifted from the checked-in snapshot: "
        f"added={added!r} removed={removed!r}"
    )


def test_names_importable():
    missing = []
    for module_name, names in PUBLIC_API.items():
        requirement = OPTIONAL_MODULE_REQUIREMENTS.get(module_name)
        if requirement and importlib.util.find_spec(requirement) is None:
            continue
        module = importlib.import_module(module_name)
        for name in names:
            if not hasattr(module, name):
                missing.append(f"{module_name}.{name}")
    assert missing == [], f"Public API names missing: {missing}"


def test_serializer_registry_formats():
    for fmt in ("json", "xml", "rdf", "provn"):
        # get() raises DoNotExist for unknown formats
        assert issubclass(prov.serializers.get(fmt), prov.serializers.Serializer)


def test_round_trip_each_format():
    document = primer_example()
    for fmt in ("json", "xml", "rdf"):
        stream = io.StringIO()
        document.serialize(destination=stream, format=fmt)
        stream.seek(0)
        round_tripped = ProvDocument.deserialize(source=stream, format=fmt)
        assert document == round_tripped, fmt
    # PROV-N is write-only: serialize must succeed
    assert document.serialize(format="provn")

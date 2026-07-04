"""Guards the public API surface for the 2.x line.

Every name listed here must remain importable from its historic location.
Additions are fine; removals or moves are a breaking change (3.0 only).
"""

import importlib
import io
import unittest

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


class TestPublicAPI(unittest.TestCase):
    def test_names_importable(self):
        missing = []
        for module_name, names in PUBLIC_API.items():
            module = importlib.import_module(module_name)
            for name in names:
                if not hasattr(module, name):
                    missing.append(f"{module_name}.{name}")
        self.assertEqual(missing, [], f"Public API names missing: {missing}")

    def test_serializer_registry_formats(self):
        for fmt in ("json", "xml", "rdf", "provn"):
            with self.subTest(format=fmt):
                # get() raises DoNotExist for unknown formats
                self.assertTrue(
                    issubclass(prov.serializers.get(fmt), prov.serializers.Serializer)
                )

    def test_round_trip_each_format(self):
        document = primer_example()
        for fmt in ("json", "xml", "rdf"):
            with self.subTest(format=fmt):
                stream = io.StringIO()
                document.serialize(destination=stream, format=fmt)
                stream.seek(0)
                round_tripped = ProvDocument.deserialize(source=stream, format=fmt)
                self.assertEqual(document, round_tripped, fmt)
        # PROV-N is write-only: serialize must succeed
        self.assertTrue(document.serialize(format="provn"))


if __name__ == "__main__":
    unittest.main()

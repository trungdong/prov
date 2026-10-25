"""The error each format's reader raises for a model rejection.

These classes import their format's third-party library (rdflib, lxml), so the
map lives apart from ``conftest.py``, which the minimal-install tests also load.
"""

from prov.serializers import ProvSerializationError
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provjsonld import ProvJSONLDException
from prov.serializers.provn import ProvNSyntaxError
from prov.serializers.provrdf import ProvRDFException
from prov.serializers.provxml import ProvXMLException

READER_ERRORS: dict[str, type[ProvSerializationError]] = {
    "json": ProvJSONException,
    "xml": ProvXMLException,
    "rdf": ProvRDFException,
    "jsonld": ProvJSONLDException,
    "provn": ProvNSyntaxError,
}

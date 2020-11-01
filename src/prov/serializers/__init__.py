from prov import Error

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

__all__ = ["get", "Serializer"]


class Serializer(object):
    """Serializer for PROV documents."""

    document = None
    """PROV document to serialise."""

    def __init__(self, document=None):
        """
        Constructor.

        :param document: Document to serialize.
        """
        self.document = document

    def serialize(self, stream, **kwargs):
        """
        Abstract method for serializing.

        :param stream: Stream object to serialize the document into.
        """

    def deserialize(self, stream, **kwargs):
        """
        Abstract method for deserializing.

        :param stream: Stream object to deserialize the document from.
        """


class DoNotExist(Error):
    """Exception for the case a serializer is not available."""

    pass


class Registry:
    """Registry of serializers."""

    serializers = None
    """Property caching all available serializers in a dict."""

    @staticmethod
    def load_serializers():
        """Loads all available serializers into the registry."""
        from prov.serializers.provjson import ProvJSONSerializer
        from prov.serializers.provn import ProvNSerializer
        from prov.serializers.provxml import ProvXMLSerializer
        from prov.serializers.provrdf import ProvRDFSerializer

        Registry.serializers = {
            "json": ProvJSONSerializer,
            "rdf": ProvRDFSerializer,
            "provn": ProvNSerializer,
            "xml": ProvXMLSerializer,
        }


def get(format_name):
    """
    Returns the serializer class for the specified format. Raises a DoNotExist
    """
    # Lazily initialize the list of serializers to avoid cyclic imports
    if Registry.serializers is None:
        Registry.load_serializers()
    try:
        return Registry.serializers[format_name]
    except KeyError:
        raise DoNotExist('No serializer available for the format "%s"' % format_name)

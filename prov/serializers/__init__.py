from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Trung Dong Huynh'
__email__ = 'trungdong@donggiang.com'

__all__ = [
    'get'
]

from prov import Error


class Serializer(object):
    def __init__(self, document=None):
        self.document = document

    def serialize(self, stream, **kwargs):
        """
        Abstract method for serializing
        """

    def deserialize(self, stream, **kwargs):
        """
        Abstract method for deserializing
        """


class DoNotExist(Error):
    pass


class Registry:
    serializers = None

    @staticmethod
    def load_serializers():
        from prov.serializers.provjson import ProvJSONSerializer
        from prov.serializers.provn import ProvNSerializer
        from prov.serializers.provxml import ProvXMLSerializer
        from prov.serializers.provjsonld import ProvJSONLDSerializer

        Registry.serializers = {
            'json': ProvJSONSerializer,
            'provn': ProvNSerializer,
            'xml': ProvXMLSerializer,
            'jsonld': ProvJSONLDSerializer
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
        raise DoNotExist(
            'No serializer available for the format "%s"' % format_name
        )



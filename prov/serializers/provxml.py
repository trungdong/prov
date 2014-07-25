"""PROV-XML serializers for ProvDocument

"""
__author__ = 'Lion Krischer'
__email__ = 'krischer@geophysik.uni-muenchen.de'

import logging
logger = logging.getLogger(__name__)

from prov import Serializer, Error


class ProvXMLException(Error):
    pass


class ProvXMLSerializer(Serializer):
    def serialize(self, stream, **kwargs):
        pass

    def deserialize(self, stream, **kwargs):
        pass

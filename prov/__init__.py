__author__ = 'Trung Dong Huynh'
__email__ = 'trungdong@donggiang.com'
__version__ = '1.0.0'

__all__ = ["model"]


class Error(Exception):
    """Base class for all errors in this package."""
    pass


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
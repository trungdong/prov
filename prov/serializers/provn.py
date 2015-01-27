from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Trung Dong Huynh'
__email__ = 'trungdong@donggiang.com'

import io
import logging
logger = logging.getLogger(__name__)

from prov.serializers import Serializer


class ProvNSerializer(Serializer):
    """PROV-N serializer for ProvDocument

    """
    def serialize(self, stream, **kwargs):
        """
        Serializes a :class:`prov.model.ProvDocument` instance to a
        `PROV-N <http://www.w3.org/TR/prov-n/>`_.

        :param stream: Where to save the output.
        """
        provn_content = self.document.get_provn()
        if isinstance(stream, io.BytesIO):
            provn_content = provn_content.encode('utf-8')
        stream.write(provn_content)

    def deserialize(self, stream, **kwargs):
        raise NotImplementedError

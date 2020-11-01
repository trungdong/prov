__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

import io

from prov.serializers import Serializer


class ProvNSerializer(Serializer):
    """PROV-N serializer for ProvDocument"""

    def serialize(self, stream, **kwargs):
        """
        Serializes a :class:`prov.model.ProvDocument` instance to a
        `PROV-N <http://www.w3.org/TR/prov-n/>`_.

        :param stream: Where to save the output.
        """
        provn_content = self.document.get_provn()
        if not isinstance(stream, io.TextIOBase):
            provn_content = provn_content.encode("utf-8")
        stream.write(provn_content)

    def deserialize(self, stream, **kwargs):
        raise NotImplementedError

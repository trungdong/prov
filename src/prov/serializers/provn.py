__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

import io
from typing import Any

from prov.model import ProvDocument
from prov.serializers import Serializer


class ProvNSerializer(Serializer):
    """PROV-N serializer for ProvDocument"""

    def serialize(self, stream: io.IOBase, **args: Any) -> None:
        """
        Serializes a :class:`prov.model.ProvDocument` instance to a
        `PROV-N <http://www.w3.org/TR/prov-n/>`_.

        :param stream: Where to save the output.
        """
        if self.document is None:
            raise Exception("No document to serialize")

        provn_content = self.document.get_provn()
        stream.write(
            provn_content
            if isinstance(stream, io.TextIOBase)
            else provn_content.encode("utf-8")
        )

    def deserialize(self, stream: io.IOBase, **args: Any) -> ProvDocument:
        raise NotImplementedError

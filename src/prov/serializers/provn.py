__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

import io
from typing import Any

from prov.model import ProvDocument
from prov.serializers import Serializer, _is_text_stream


class ProvNSerializer(Serializer):
    """PROV-N serializer for ProvDocument.

    Write-only: PROV-N has no deserializer in this package (see
    :meth:`deserialize`).
    """

    def serialize(self, stream: io.IOBase, **args: Any) -> None:
        """Serialize ``self.document`` to `PROV-N <http://www.w3.org/TR/prov-n/>`_.

        Args:
            stream: Stream to write the output to. Text streams receive the
                PROV-N text directly; other (binary) streams receive it
                UTF-8-encoded.
            **args: Unused; accepted for interface compatibility with
                :meth:`Serializer.serialize`.

        Raises:
            Exception: If ``self.document`` is ``None``.
        """
        if self.document is None:
            raise Exception("No document to serialize")

        provn_content = self.document.get_provn()
        stream.write(
            provn_content if _is_text_stream(stream) else provn_content.encode("utf-8")
        )

    def deserialize(self, stream: io.IOBase, **args: Any) -> ProvDocument:
        """Not implemented: PROV-N has no parser in this package.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError

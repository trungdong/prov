__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

import io
import os
import sys
import warnings
from types import FrameType
from typing import Any

import prov
from prov.model import ProvDocument, ProvWarning
from prov.serializers import Serializer, _is_text_stream
from prov.serializers.provn_lexer import ProvNSyntaxError
from prov.serializers.provn_parser import PROFILES, ProvNParser

__all__ = ["PROFILES", "ProvNSerializer", "ProvNSyntaxError"]

_PROV_PACKAGE_DIR = os.path.dirname(os.path.abspath(prov.__file__))
# prov.tests lives inside the package directory but is caller code (this
# module's own test suite exercises deserialize() directly), not part of
# the deserialize() call chain being walked past below.
_PROV_TESTS_DIR = os.path.join(_PROV_PACKAGE_DIR, "tests") + os.sep


def _external_stacklevel() -> int:
    """``warnings.warn()`` stacklevel that reaches the caller's caller.

    Walks the real call stack outward from this function's caller until a
    frame's file sits outside the ``prov`` package (or inside its own test
    suite), since a fixed level would be wrong for one of the several ways
    to reach here (a direct ``ProvDocument.deserialize()`` call,
    ``prov.read()`` with an explicit format, or ``prov.read()``
    auto-detecting) each adding a different number of ``prov``-internal
    frames. Falls back to ``3`` (the direct-call depth) if every frame up to
    the top of the stack is inside ``prov``, which should not happen in
    practice.
    """
    frame: FrameType | None = sys._getframe(1)
    level = 1
    while frame is not None:
        filename = os.path.abspath(frame.f_code.co_filename)
        if not filename.startswith(_PROV_PACKAGE_DIR) or filename.startswith(
            _PROV_TESTS_DIR
        ):
            return level
        frame = frame.f_back
        level += 1
    return 3


class ProvNSerializer(Serializer):
    """PROV-N serializer and deserializer for ProvDocument."""

    def serialize(self, stream: io.IOBase, strict: bool = False, **args: Any) -> None:
        """Serialize ``self.document`` to `PROV-N <http://www.w3.org/TR/prov-n/>`_.

        Args:
            stream: Stream to write the output to. Text streams receive the
                PROV-N text directly; other (binary) streams receive it
                UTF-8-encoded.
            strict: Write ``prov:mentionOf`` instead of the bare
                ``mentionOf`` keyword so the output parses under the strict
                PROV-N profile.
            **args: Unused; accepted for interface compatibility with
                :meth:`Serializer.serialize`.

        Raises:
            Exception: If ``self.document`` is ``None``.
        """
        if self.document is None:
            raise Exception("No document to serialize")

        provn_content = self.document.get_provn(strict=strict)
        stream.write(
            provn_content if _is_text_stream(stream) else provn_content.encode("utf-8")
        )

    def deserialize(
        self, stream: io.IOBase, profile: str = "default", **args: Any
    ) -> ProvDocument:
        """Parse PROV-N text from ``stream`` into a new document.

        Args:
            stream: Text or binary stream holding PROV-N; binary content is
                decoded as UTF-8.
            profile: ``"strict"`` (the Recommendation grammar only),
                ``"default"`` (plus the bare ``mentionOf`` keyword and the
                shorthand keywords ``prov`` and ProvToolbox write) or
                ``"lenient"`` (as ``default``, skipping any statement that
                fails to parse with a :class:`~prov.model.ProvWarning`).
            **args: Unused; accepted for interface compatibility.

        Returns:
            The parsed :class:`~prov.model.ProvDocument`.

        Raises:
            ProvNSyntaxError: On the first tokenisation or, outside the
                ``lenient`` profile, parse error, with line and column.
            ValueError: If ``profile`` is not one of :data:`PROFILES`.
        """
        content = stream.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        parser = ProvNParser(content, profile)
        document = parser.parse()
        # Warned here, not inside the parser, so a single stacklevel
        # attributes every skip -- document-level or inside a bundle alike
        # -- to the caller of ProvDocument.deserialize(). The level is
        # computed dynamically (see _external_stacklevel()) since the
        # caller may be ProvDocument.deserialize() directly or reach here
        # via prov.read(), each adding a different number of frames.
        if parser.skipped:
            stacklevel = _external_stacklevel()
            for message in parser.skipped:
                warnings.warn(message, ProvWarning, stacklevel=stacklevel)
        return document

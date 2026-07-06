from __future__ import annotations  # needed for | type annotations in Python < 3.10

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prov.model import ProvDocument

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"
__version__ = "2.4.0"

__all__ = ["Error", "model", "read"]


class Error(Exception):
    """Base class for all errors in this package."""

    pass


def read(
    source: str | bytes | os.PathLike[str], format: str | None = None
) -> ProvDocument | None:
    """Read a :class:`~prov.model.ProvDocument` from a file, path, or string.

    If ``format`` is not given, the format is detected lazily by trying each
    registered serializer's ``deserialize()`` in turn and returning the first
    one that succeeds. The deserializers should fail fairly early when data of
    the wrong type is passed to them thus the try/except is likely cheap. One
    could of course also do some more advanced format auto-detection but I am
    not sure that is necessary.

    The downside of auto-detection is that no proper error messages will be
    produced; pass the ``format`` parameter explicitly to get the actual
    traceback from the matching deserializer.

    Args:
        source: File-like stream, path, or raw content to deserialize.
        format: Serialization format to use (e.g. ``"json"``, ``"xml"``,
            ``"rdf"``, ``"provn"``). If ``None``, every registered format is
            tried in turn.

    Returns:
        The deserialized :class:`~prov.model.ProvDocument`.

    Raises:
        TypeError: If ``format`` is ``None`` and none of the registered
            serializers could deserialize ``source``.
    """
    # Lazy imports to not globber the namespace.
    from prov.model import ProvDocument
    from prov.serializers import Registry

    Registry.load_serializers()
    assert Registry.serializers is not None  # populated by load_serializers()
    serializers = Registry.serializers.keys()

    if format:
        return ProvDocument.deserialize(source=source, format=format.lower())

    for format in serializers:
        try:
            return ProvDocument.deserialize(source=source, format=format)
        except (TypeError, ValueError, AttributeError, KeyError):
            # Catch specific exceptions that can occur during deserialization
            # This allows for better debugging information
            continue
    else:
        raise TypeError(
            "Could not read from the source. To get a proper "
            "error message, specify the format with the 'format' "
            "parameter."
        )

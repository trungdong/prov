from __future__ import annotations  # needed for | type annotations in Python < 3.10

import io
import logging
import os
import warnings
from typing import IO, TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from prov.model import ProvDocument

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"
__version__ = "2.5.0"

__all__ = ["Error", "model", "read"]


class Error(Exception):
    """Base class for all errors in this package."""

    pass


def read(
    source: io.IOBase | IO[Any] | str | bytes | os.PathLike[str],
    format: str | None = None,
) -> ProvDocument | None:
    """Read a :class:`~prov.model.ProvDocument` from a file, path, or string.

    A ``str``/``bytes`` source naming an existing file is read from that
    file; any other ``str``/``bytes`` is parsed as raw document content.

    If ``format`` is not given, the format is detected by trying each
    registered deserializer in turn and returning the first that both
    succeeds and produces a non-empty document (a parse yielding no records
    or bundles -- e.g. rdflib parsing empty/foreign input to an empty graph
    -- is treated as "not this format"; registered namespaces are not used
    as a signal here since the rdf deserializer always registers rdflib's
    own default-bound namespace prefixes on every successful parse, empty
    or not). Auto-detection swallows all deserializer errors; pass
    ``format`` explicitly to get the actual traceback from the matching
    deserializer.

    A seekable stream ``source`` (e.g. an open file object, ``io.StringIO``,
    ``io.BytesIO``) is rewound to its starting position before each
    auto-detection attempt, so every candidate format sees the full content.
    A non-seekable stream is consumed by the first candidate; pass
    ``format`` explicitly for those.

    Args:
        source: File-like stream, path to an existing file, or raw content.
        format: Serialization format to use (e.g. ``"json"``, ``"xml"``,
            ``"rdf"``, ``"provn"``). If ``None``, every registered format is
            tried in turn.

    Returns:
        The deserialized :class:`~prov.model.ProvDocument`.

    Raises:
        TypeError: If ``format`` is ``None`` and no registered serializer
            produced a non-empty document from ``source``.
    """
    # Lazy imports to not globber the namespace.
    from prov.model import ProvDocument
    from prov.serializers import Registry

    Registry.load_serializers()
    assert Registry.serializers is not None  # populated by load_serializers()
    serializers = Registry.serializers.keys()

    src: io.IOBase | IO[Any] | str | bytes | os.PathLike[str] | None = source
    content: str | bytes | None = None
    if isinstance(src, (str, bytes)) and not os.path.isfile(src):
        # Not a path to an existing file: treat the string itself as raw
        # document content.
        content, src = src, None

    # A stream source (as opposed to a path) is duck-typed on read(),
    # matching ProvBundle.deserialize()'s own convention (#240). Only a
    # seekable stream can be rewound between auto-detect attempts below.
    stream: IO[Any] | None = (
        cast(IO[Any], src) if src is not None and hasattr(src, "read") else None
    )
    start_pos: int | None = None
    if stream is not None and hasattr(stream, "seekable") and stream.seekable():
        start_pos = stream.tell()

    if format:
        try:
            return ProvDocument.deserialize(
                source=src, content=content, format=format.lower()
            )
        except Exception:
            if content is not None:
                warnings.warn(
                    "read() source is not a path to an existing file and "
                    "was parsed as raw content; if you meant a file path, "
                    "check that it exists",
                    UserWarning,
                    stacklevel=2,
                )
            raise

    # Failed-candidate diagnostics (e.g. rdflib's "does not look like a
    # valid URI" logger warnings) are noise by definition here: every
    # candidate's exception is swallowed below, so nothing about a failed
    # attempt is ever surfaced to the caller anyway. Raise rdflib's logger
    # level for the duration of auto-detection only -- the explicit-format
    # path above is unaffected and still shows real diagnostics.
    rdflib_term_logger = logging.getLogger("rdflib.term")
    previous_level = rdflib_term_logger.level
    rdflib_term_logger.setLevel(logging.ERROR)
    try:
        for format in serializers:
            if start_pos is not None:
                assert stream is not None
                stream.seek(start_pos)
            try:
                document = ProvDocument.deserialize(
                    source=src, content=content, format=format
                )
            except Exception:
                # Any failure from a candidate deserializer means "not this
                # format" -- move on to the next candidate.
                continue
            if document.get_records() or document.has_bundles():
                return document
            # A parse producing a completely empty document (e.g. rdflib
            # accepts empty input, or the xml deserializer walking a
            # childless foreign root) is treated as not detected. Registered
            # namespaces are deliberately not consulted: the rdf deserializer
            # always copies rdflib's own default-bound namespace prefixes onto
            # the document on every successful parse, so that signal is always
            # truthy and would defeat this check for the rdf format.
    finally:
        rdflib_term_logger.setLevel(previous_level)

    message = (
        "Could not read from the source. To get a proper "
        "error message, specify the format with the 'format' "
        "parameter."
    )
    if content is not None:
        message += (
            " Note: the source is not a path to an existing file and was "
            "parsed as raw content."
        )
    raise TypeError(message)

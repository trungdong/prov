from __future__ import annotations  # defer eval: TYPE_CHECKING names in signatures

import io
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from prov import Error

if TYPE_CHECKING:
    from prov.model import ProvDocument

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

__all__ = [
    "ProvFormatNotDetected",
    "ProvSerializationError",
    "Registry",
    "Serializer",
    "get",
]


def _is_text_stream(stream: io.IOBase) -> bool:
    """Return whether ``stream`` accepts/produces ``str`` rather than bytes.

    ``isinstance(stream, io.TextIOBase)`` alone misses file-like wrappers
    such as ``tempfile.NamedTemporaryFile``'s ``_TemporaryFileWrapper``,
    which proxy a text stream without subclassing ``io.TextIOBase``. Such
    wrappers expose the underlying text stream's ``encoding`` attribute,
    while binary streams (``io.BytesIO``, buffered readers/writers) have no
    ``encoding``, so the extra check only ever reclassifies text-stream
    proxies that would otherwise crash on bytes (#240).
    """
    return isinstance(stream, io.TextIOBase) or hasattr(stream, "encoding")


class Serializer(ABC):
    """Serializer for PROV documents."""

    document = None
    """PROV document to serialise."""

    deserialize_options: ClassVar[frozenset[str]] = frozenset()
    """Keyword arguments :meth:`deserialize` accepts beyond ``stream``;
    :func:`prov.read` forwards only these."""

    serialize_options: ClassVar[frozenset[str]] = frozenset()
    """Keyword arguments :meth:`serialize` accepts beyond ``stream`` that the
    command line may name with ``-w``."""

    def __init__(self, document: ProvDocument | None = None):
        """Create a serializer bound to a document.

        Args:
            document: Document this serializer will serialize, or
                deserialize into. May be ``None`` when only deserialization
                (which produces its own new document) is needed.
        """
        self.document = document

    @abstractmethod
    def serialize(self, stream: io.IOBase, **args: Any) -> None:
        """Serialize ``self.document`` and write it to a stream.

        Subclasses implement this to encode the bound document and write the
        result to ``stream``.

        Args:
            stream: Stream to write the serialized document into.
            **args: Format-specific serialization options, passed through by
                subclasses.
        """

    @abstractmethod
    def deserialize(self, stream: io.IOBase, **args: Any) -> ProvDocument:
        """Read and parse a document from a stream.

        Subclasses implement this to parse ``stream`` and build a new
        :class:`~prov.model.ProvDocument` from it.

        Args:
            stream: Stream to deserialize the document from.
            **args: Format-specific deserialization options, passed through
                by subclasses.

        Returns:
            The deserialized :class:`~prov.model.ProvDocument`.
        """


class DoNotExist(Error):
    """Exception for the case a serializer is not available."""


class ProvSerializationError(Error):
    """A document cannot be read from or written to a format.

    Each format's error derives from it. A reader raises its own subclass for
    input it cannot decode. When the model refuses a record or a namespace
    that the reader builds, the reader's error locates the record or the
    declaration, carries the model's sentence and sets the model's exception
    as ``__cause__``. A fault that the reader finds itself has no cause.
    """


class ProvFormatNotDetected(ProvSerializationError, TypeError):
    """:func:`prov.read` could not detect the format of its source.

    Also a :class:`TypeError`, so ``except TypeError`` around
    :func:`prov.read` keeps working.

    The start of the source, after any whitespace, can name one reader. A
    ``{`` names PROV-JSONLD when the first 4096 characters hold ``"@context"``
    or ``"@graph"``, and PROV-JSON otherwise. The word ``document`` names
    PROV-N. When that reader rejected the source with its own
    :class:`ProvSerializationError`, that error is the ``__cause__``, so the
    traceback shows the reader's message and position. Any other start, such
    as ``<`` or ``@prefix``, names no reader, and the exception has no cause.
    Neither has one when the named reader raised another error, such as the
    parsing library's error for malformed JSON or the :class:`ValueError` for
    an unsupported ``profile``, or when a non-seekable stream cannot be read
    again. Pass ``format`` to :func:`prov.read` to get a reader's error on
    its own.
    """


class Registry:
    """Registry of serializers."""

    serializers: ClassVar[dict[str, type[Serializer]] | None] = None
    """Property caching all available serializers in a dict."""

    @staticmethod
    def load_serializers() -> None:
        """Load all serializers whose optional dependencies are installed.

        ``json`` and ``provn`` have no optional dependencies and are always
        registered. ``rdf`` (needs ``rdflib``) and ``xml`` (needs ``lxml``)
        are registered only if their extra is installed, so that ``import
        prov`` and JSON/PROV-N work in a minimal install; requesting an
        unavailable format then raises an informative :class:`DoNotExist`
        (see :func:`get`) rather than a bare ``ModuleNotFoundError``.

        :func:`get` and :func:`prov.read` call it on first use. The registry
        order is ``json, rdf, provn, xml, jsonld``, and :func:`prov.read`
        tries the formats in that order when it detects one, as
        :ref:`auto-detect` describes for streams.
        """
        from prov.serializers.provjson import ProvJSONSerializer
        from prov.serializers.provjsonld import ProvJSONLDSerializer
        from prov.serializers.provn import ProvNSerializer

        serializers: dict[str, type[Serializer]] = {
            "json": ProvJSONSerializer,
        }
        try:
            from prov.serializers.provrdf import ProvRDFSerializer
        except ImportError:  # pragma: no cover -- rdflib (rdf extra) absent; covered by the minimal-install CI job
            pass
        else:
            serializers["rdf"] = ProvRDFSerializer
        serializers["provn"] = ProvNSerializer
        try:
            from prov.serializers.provxml import ProvXMLSerializer
        except ImportError:  # pragma: no cover -- lxml (xml extra) absent; covered by the minimal-install CI job
            pass
        else:
            serializers["xml"] = ProvXMLSerializer
        serializers["jsonld"] = ProvJSONLDSerializer
        Registry.serializers = serializers


#: Formats provided by optional extras, used to build the DoNotExist message
#: in :func:`get` when the corresponding dependency is not installed.
_OPTIONAL_FORMAT_EXTRAS = {"rdf": "rdf", "xml": "xml"}


def get(format_name: str) -> type[Serializer]:
    """Return the serializer class registered for a format.

    Args:
        format_name: Registry key, e.g. ``"json"``, ``"xml"``, ``"rdf"``,
            ``"provn"``, ``"jsonld"``.

    Returns:
        The :class:`Serializer` subclass for the format.

    Raises:
        DoNotExist: If no serializer is registered under ``format_name``.
    """
    # Lazily initialize the list of serializers to avoid cyclic imports
    if Registry.serializers is None:
        Registry.load_serializers()
    serializers = Registry.serializers
    # load_serializers() (just above) always populates Registry.serializers.
    if serializers is None:  # pragma: no cover
        raise AssertionError("Registry.serializers is not populated")
    try:
        return serializers[format_name]
    except KeyError as e:
        extra = _OPTIONAL_FORMAT_EXTRAS.get(format_name)
        # The informative-message branch is reachable only when the optional
        # extra is absent; the minimal-install CI job exercises it.
        if extra is not None:  # pragma: no cover
            raise DoNotExist(
                f'Serializer for the "{format_name}" format requires the '
                f'"{extra}" extra; install it with: pip install "prov[{extra}]"'
            ) from e
        raise DoNotExist(
            f'No serializer available for the format "{format_name}"'
        ) from e

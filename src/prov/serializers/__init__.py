from __future__ import annotations  # needed for | type annotations in Python < 3.10

import io
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from prov import Error

if TYPE_CHECKING:
    from prov.model import ProvDocument

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"

__all__ = ["Registry", "Serializer", "get"]


class Serializer(ABC):
    """Serializer for PROV documents."""

    document = None
    """PROV document to serialise."""

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
        pass  # pragma: no cover -- abstract body, never executed directly

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
        pass  # pragma: no cover -- abstract body, never executed directly


class DoNotExist(Error):
    """Exception for the case a serializer is not available."""

    pass


class Registry:
    """Registry of serializers."""

    serializers: ClassVar[dict[str, type[Serializer]] | None] = None
    """Property caching all available serializers in a dict."""

    @staticmethod
    def load_serializers() -> None:
        """Populate :attr:`serializers` with the four built-in serializer classes.

        Imports the ``json``, ``rdf``, ``provn``, and ``xml`` serializer
        modules lazily (to avoid import cycles) and (re-)registers them in
        :attr:`serializers`, unconditionally overwriting any previous
        contents.
        """
        from prov.serializers.provjson import ProvJSONSerializer
        from prov.serializers.provn import ProvNSerializer
        from prov.serializers.provrdf import ProvRDFSerializer
        from prov.serializers.provxml import ProvXMLSerializer

        Registry.serializers = {
            "json": ProvJSONSerializer,
            "rdf": ProvRDFSerializer,
            "provn": ProvNSerializer,
            "xml": ProvXMLSerializer,
        }


def get(format_name: str) -> type[Serializer]:
    """Return the serializer class registered for a format.

    Args:
        format_name: Registry key, e.g. ``"json"``, ``"xml"``, ``"rdf"``,
            ``"provn"``.

    Returns:
        The :class:`Serializer` subclass for the format.

    Raises:
        DoNotExist: If no serializer is registered under ``format_name``.
    """
    # Lazily initialize the list of serializers to avoid cyclic imports
    if Registry.serializers is None:
        Registry.load_serializers()
    serializers = Registry.serializers
    assert serializers is not None  # load_serializers() always populates it
    try:
        return serializers[format_name]
    except KeyError as e:
        raise DoNotExist(
            f'No serializer available for the format "{format_name}"'
        ) from e

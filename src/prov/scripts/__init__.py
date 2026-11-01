import io
import os
import sys
from argparse import ArgumentParser
from collections.abc import Callable, Mapping
from typing import Any, BinaryIO, cast

import prov
from prov.model import ProvDocument
from prov.serializers import Registry


def _run(prog: str, action: Callable[[], int]) -> int:
    """Return ``action()``, 130 on Ctrl-C, or 2 after one ``prog: error: ...`` line.

    ``SystemExit`` from argparse or :func:`_open_binary` passes through.
    """
    try:
        return action()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        sys.stderr.write(f"{prog}: error: {exc}\n")
        return 2


def _format_names() -> str:
    """Name the registered serializer formats, e.g. ``json, rdf, provn, xml or jsonld``."""
    if Registry.serializers is None:
        Registry.load_serializers()
    names = list(Registry.serializers or ())
    return f"{', '.join(names[:-1])} or {names[-1]}"


_EXTENSIONS: dict[str, tuple[str, dict[str, str]]] = {
    ".json": ("json", {}),
    ".provn": ("provn", {}),
    ".xml": ("xml", {}),
    ".provx": ("xml", {}),
    ".jsonld": ("jsonld", {}),
    ".ttl": ("rdf", {"rdf_format": "turtle"}),
    ".trig": ("rdf", {"rdf_format": "trig"}),
    ".nt": ("rdf", {"rdf_format": "nt"}),
    ".nq": ("rdf", {"rdf_format": "nquads"}),
    ".rdf": ("rdf", {"rdf_format": "xml"}),
}
"""Format and reader or writer options by lower-cased file extension, dot included."""


def _format_from_extension(path: str) -> tuple[str, dict[str, str]] | None:
    """Return the format and options ``path``'s extension names, else ``None``."""
    row = _EXTENSIONS.get(os.path.splitext(path)[1].lower())
    return None if row is None else (row[0], dict(row[1]))


def _input_format(path: str, flag: str) -> tuple[str, dict[str, str]]:
    """Resolve the input format and reader options for ``path`` and the ``-i`` ``flag``.

    An explicit flag is used as given, with no options. ``auto`` takes the
    extension's row, else stays ``auto`` for content detection.
    """
    flag = flag.lower()
    if flag != "auto":
        return flag, {}
    return _format_from_extension(path) or ("auto", {})


def _read(stream: BinaryIO, format: str, options: Mapping[str, Any]) -> ProvDocument:
    """Read a document from ``stream`` in ``format``, passing ``options`` to the reader.

    ``auto`` detects the format from the content. Detection rewinds the
    stream between candidate readers, so a stream that cannot seek (a pipe)
    is read into memory first, as ``BytesIO`` for bytes and ``StringIO`` for text.
    """
    if format == "auto":
        if not stream.seekable():
            content = stream.read()
            stream = cast(
                BinaryIO,
                io.BytesIO(content)
                if isinstance(content, bytes)
                else io.StringIO(content),
            )
        # prov.read() is annotated "| None", but every path returns a document.
        return cast(ProvDocument, prov.read(stream, None, **options))
    return cast(ProvDocument, prov.read(stream, format, **options))


def _open_binary(
    parser: ArgumentParser, path: str, mode: str, standard_name: str
) -> tuple[BinaryIO, bool]:
    """Open ``path`` in binary ``mode``, or return the standard stream for ``"-"``.

    ``standard_name`` is ``"stdin"`` or ``"stdout"``; its ``.buffer`` is
    resolved only when ``path`` is ``"-"``, so the other standard stream is
    never touched. A standard stream with no ``.buffer`` (a text-only stream,
    e.g. an ``io.StringIO`` substituted under a test harness) is returned as
    it is, since every deserializer accepts a text stream. The second
    element says whether the caller owns the returned stream and must close
    it; the standard streams belong to the process. An unopenable path is
    reported through :meth:`argparse.ArgumentParser.error`, which exits with
    status 2 like argparse's own file handling did.
    """
    if path == "-":
        standard = getattr(sys, standard_name)
        return cast(BinaryIO, getattr(standard, "buffer", standard)), False
    try:
        return cast(BinaryIO, open(path, mode)), True
    except OSError as exc:
        parser.error(f"can't open '{path}': {exc}")

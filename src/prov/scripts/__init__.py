import contextlib
import io
import os
import sys
from argparse import ArgumentParser
from collections.abc import Callable, Mapping
from typing import IO, Any, cast

import prov
from prov.model import ProvDocument
from prov.serializers import Registry


def _run(prog: str, action: Callable[[], int]) -> int:
    """Return ``action()``, 130 on Ctrl-C, or 2 after one ``prog: error: ...`` line.

    ``action`` builds the parser too, so an interrupt or an import failure while
    the registry loads is handled here. A message that spans several lines is
    joined into one, and an empty message becomes the exception's class name.

    ``SystemExit`` from argparse or :func:`_open_binary` passes through.
    """
    try:
        return action()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        lines = (line.strip() for line in str(exc).splitlines())
        message = " ".join(line for line in lines if line) or type(exc).__name__
        sys.stderr.write(f"{prog}: error: {message}\n")
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


def _input_format(path: str, flag: str) -> tuple[str, dict[str, str]]:
    """Resolve the input format and reader options for ``path`` and the ``-i`` ``flag``.

    An explicit flag is used as given, with no options. ``auto`` takes the
    extension's row, else stays ``auto`` for content detection.
    """
    flag = flag.lower()
    if flag != "auto":
        return flag, {}
    row = _EXTENSIONS.get(os.path.splitext(path)[1].lower())
    return ("auto", {}) if row is None else (row[0], dict(row[1]))


def _read(stream: IO[Any], format: str, options: Mapping[str, Any]) -> ProvDocument:
    """Read a document from ``stream`` in ``format``, passing ``options`` to the reader.

    ``auto`` detects the format from the content. Detection rewinds the
    stream between candidate readers, so a stream that cannot seek (a pipe, or
    one with no ``seekable`` method) is read into memory first, as ``BytesIO``
    for bytes and ``StringIO`` for text.
    """
    auto = format.lower() == "auto"
    if auto:
        seekable = getattr(stream, "seekable", None)
        if seekable is None or not seekable():
            content = stream.read()
            stream = (
                io.BytesIO(content)
                if isinstance(content, bytes)
                else io.StringIO(content)
            )
    # prov.read() is annotated "| None", but every path returns a document.
    return cast(ProvDocument, prov.read(stream, None if auto else format, **options))


def _open_binary(
    parser: ArgumentParser, path: str, mode: str, standard_name: str
) -> contextlib.AbstractContextManager[IO[Any]]:
    """Open ``path`` in binary ``mode``, or wrap the standard stream for ``"-"``.

    The result is a context manager. A path yields the opened file, closed on
    exit. ``"-"`` yields the standard stream inside a
    :func:`contextlib.nullcontext`, so the process's own stream is never
    closed.

    ``standard_name`` is ``"stdin"`` or ``"stdout"``; its ``.buffer`` is
    resolved only when ``path`` is ``"-"``, so the other standard stream is
    never touched. A standard stream with no ``.buffer`` (a text-only stream,
    e.g. an ``io.StringIO`` substituted under a test harness) is used as it
    is, since every deserializer accepts a text stream. An unopenable path is
    reported through :meth:`argparse.ArgumentParser.error`, which exits with
    status 2 like argparse's own file handling did.
    """
    if path == "-":
        standard = getattr(sys, standard_name)
        return contextlib.nullcontext(getattr(standard, "buffer", standard))
    try:
        return open(path, mode)
    except OSError as exc:
        parser.error(f"can't open '{path}': {exc}")

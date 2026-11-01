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


def _read(stream: BinaryIO, format: str, options: Mapping[str, Any]) -> ProvDocument:
    """Read a document from ``stream`` in ``format``, passing ``options`` to the reader."""
    # prov.read() is annotated "| None", but every path returns a document.
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

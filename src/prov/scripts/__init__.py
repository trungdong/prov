import contextlib
import io
import os
import re
import sys
from argparse import ArgumentParser, ArgumentTypeError
from collections.abc import Callable, Mapping, Sequence
from typing import IO, Any, cast

import prov
from prov.model import ProvDocument
from prov.serializers import ProvFormatNotDetected, Registry, Serializer


def _run(prog: str, action: Callable[[], int]) -> int:
    """Return ``action()``, 130 on Ctrl-C, or 2 after one ``prog: error: ...`` line.

    ``action`` builds the parser too, so an interrupt or an import failure while
    the registry loads is handled here. A failed detection also appends its
    ``__cause__``, the reader's own error, after one space when it has one. A
    message that spans several lines is joined into one, and an empty message
    becomes the exception's class name.

    ``SystemExit`` from argparse or :func:`_open_binary` passes through.
    """
    try:
        return action()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        text = str(exc)
        if isinstance(exc, ProvFormatNotDetected) and exc.__cause__ is not None:
            text += " " + str(exc.__cause__)
        lines = (line.strip() for line in text.splitlines())
        message = " ".join(line for line in lines if line) or type(exc).__name__
        sys.stderr.write(f"{prog}: error: {message}\n")
        return 2


def _registered() -> Mapping[str, type[Serializer]]:
    """Return the registered serializer classes by format name."""
    if Registry.serializers is None:
        Registry.load_serializers()
    return Registry.serializers or {}


def _format_names() -> str:
    """Name the registered serializer formats, e.g. ``json, rdf, provn, xml or jsonld``."""
    names = list(_registered())
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


def _pair(text: str) -> tuple[str, str]:
    """Split ``NAME=VALUE`` at the first ``=``, as the argparse ``type`` of an option flag.

    A flag without ``=`` or with an empty name is an ``ArgumentTypeError``,
    since no keyword is named ``""``.
    """
    name, equals, value = text.partition("=")
    if not equals or not name:
        raise ArgumentTypeError(f"{text!r} is not NAME=VALUE")
    return name, value


_KEYWORDS = {"none": None, "true": True, "false": False}
_INTEGER = re.compile(r"[+-]?[0-9]+", re.ASCII)


def _typed(value: str) -> Any:
    """Type an option value.

    ``none``, ``true`` and ``false`` in any case are ``None``, ``True`` and
    ``False``, an optionally signed run of ASCII digits is an ``int``, and
    anything else is the string as given.
    """
    word = value.lower()
    if word in _KEYWORDS:
        return _KEYWORDS[word]
    return int(value) if _INTEGER.fullmatch(value) else value


def _options(
    pairs: Sequence[tuple[str, str]],
    role: str,
    fmt: str,
    declared: frozenset[str] | None,
) -> dict[str, Any]:
    """Type ``pairs`` into keyword options for the ``fmt`` ``role`` (``writer`` or ``reader``).

    A later pair replaces an earlier one of the same name. A name outside
    ``declared`` is a ``ValueError`` in ``prov.read()``'s sentence. ``None``
    for ``declared`` skips the check, which leaves an unavailable format to the
    library's own error.
    """
    if declared is not None:
        unknown = sorted({name for name, _ in pairs} - declared)
        if unknown:
            accepted = ", ".join(sorted(declared)) or "none"
            raise ValueError(
                f"the {fmt!r} {role} accepts no option {unknown[0]!r}; "
                f"it accepts: {accepted}"
            )
    return {name: _typed(value) for name, value in pairs}


def _reader_names(fmt: str) -> frozenset[str] | None:
    """Return the options the ``fmt`` reader declares.

    ``auto`` returns the union over every registered reader, and a format
    that is not registered returns ``None``.
    """
    classes = _registered()
    if fmt == "auto":
        return frozenset().union(*(cls.deserialize_options for cls in classes.values()))
    cls = classes.get(fmt)
    return None if cls is None else cls.deserialize_options


def _option_names(attr: str) -> str:
    """List the names each registered format declares in ``attr``, for ``--help``.

    A format that declares none is left out.
    """
    return "; ".join(
        f"{fmt}: {', '.join(sorted(names))}"
        for fmt, cls in sorted(_registered().items())
        if (names := getattr(cls, attr))
    )


def _read(stream: IO[Any], fmt: str, options: Mapping[str, Any]) -> ProvDocument:
    """Read a document from ``stream`` in ``fmt``, passing ``options`` to the reader.

    ``auto`` detects the format from the content. Detection rewinds the
    stream between candidate readers, so a stream that cannot seek (a pipe, or
    one with no ``seekable`` method) is read into memory first, as ``BytesIO``
    for bytes and ``StringIO`` for text.
    """
    auto = fmt.lower() == "auto"
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
    return cast(ProvDocument, prov.read(stream, None if auto else fmt, **options))


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

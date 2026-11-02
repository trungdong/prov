"""Convert a PROV document between PROV-JSON, PROV-N, PROV-XML, PROV-O, PROV-JSONLD
and Graphviz output formats."""

import contextlib
import importlib
import io
import os
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections.abc import Mapping
from typing import IO, Any, cast

import prov
from prov import serializers
from prov.model import ProvDocument
from prov.scripts import (
    _format_names,
    _input_format,
    _open_binary,
    _option_names,
    _options,
    _pair,
    _read,
    _reader_names,
    _registered,
    _run,
)

_PROG = "prov-convert"

GRAPHVIZ_SUPPORTED_FORMATS = {
    "bmp",
    "canon",
    "cmap",
    "cmapx",
    "cmapx_np",
    "dot",
    "eps",
    "fig",
    "gtk",
    "gv",
    "ico",
    "imap",
    "imap_np",
    "ismap",
    "jpe",
    "jpeg",
    "jpg",
    "pdf",
    "plain",
    "plain-ext",
    "png",
    "ps",
    "ps2",
    "svg",
    "svgz",
    "tif",
    "tiff",
    "tk",
    "vml",
    "vmlz",
    "x11",
    "xdot",
    "xlib",
}
"""Graphviz output format names accepted by :func:`convert_file` in addition
to the formats registered in :class:`~prov.serializers.Registry`."""


_GRAPHVIZ_OPTIONS = frozenset(
    {
        "show_nary",
        "use_labels",
        "direction",
        "show_element_attributes",
        "show_relation_attributes",
    }
)
"""The keywords of :func:`~prov.dot.prov_to_dot` that a Graphviz output format takes."""

_LEXERS = {
    "provn": "provn",
    "json": "json",
    "jsonld": "jsonld",
    "xml": "xml",
    "dot": "graphviz",
}
"""The Pygments lexer name for each output format that has one, except ``rdf``."""

_RDF_LEXERS = {"turtle": "turtle", "xml": "xml", "json-ld": "jsonld"}
"""The Pygments lexer name for each ``rdf_format`` that has one."""


class CLIError(Exception):
    """A fatal error that :func:`main` reports as one ``prov-convert: error:`` line."""

    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


def convert_file(
    infile: IO[Any],
    outfile: IO[Any],
    output_format: str,
    input_format: str = "json",
    *,
    reader_options: Mapping[str, Any] | None = None,
    writer_options: Mapping[str, Any] | None = None,
    color: bool = False,
) -> None:
    """Read a PROV document from ``infile`` and write it to ``outfile`` in ``output_format``.

    ``infile`` is read in ``input_format`` (default PROV-JSON; ``"auto"``
    detects the format from the content). A name in
    :data:`GRAPHVIZ_SUPPORTED_FORMATS` is rendered through
    :func:`~prov.dot.prov_to_dot` (with ``writer_options``) and Graphviz, and any other
    ``output_format`` is written by
    :meth:`~prov.model.ProvDocument.serialize`. With ``color`` the output is
    highlighted with ANSI escape sequences.

    Args:
        infile: File-like object (opened in binary mode) to read the source
            document from.
        outfile: File-like object (opened in binary mode) to write the
            converted output to.
        output_format: Target format name (e.g. ``"json"``, ``"xml"``,
            ``"rdf"``, ``"jsonld"``, ``"provn"``, or a Graphviz output format such as
            ``"svg"``/``"pdf"``/``"png"``).
        input_format: Source format name, any registered serializer format, or
            ``"auto"`` to detect it from the content.
        reader_options: Keyword options for the input format's reader.
        writer_options: Keyword options for the output format's writer, or for
            :func:`~prov.dot.prov_to_dot` with a Graphviz format.
        color: Colour the output with Pygments when the format has a lexer
            (see ``--color``). A format without a lexer, and output that holds a
            carriage return, is written plain.

    Raises:
        CLIError: If ``input_format`` is not a registered serializer format,
            or if ``output_format`` is not a Graphviz format and not a
            registered serializer format. The message is the serializer
            registry's, which names the extra a missing format needs.
        ImportError: If ``color`` is true and Pygments is not installed.
        TypeError: If ``writer_options`` names a keyword that
            :func:`~prov.dot.prov_to_dot` does not accept.

    A writer's own error for a value it rejects (such as the ``ValueError``
    for an unknown ``context``) and a reader's error propagate unchanged.
    """
    try:
        prov_doc = _read(infile, input_format, reader_options or {})
    except serializers.DoNotExist as e:
        raise CLIError(str(e)) from e

    options = writer_options or {}
    lexer = _lexer_name(output_format, options) if color else None
    if lexer is None:
        _write_document(prov_doc, outfile, output_format, options)
        return
    buffer = io.BytesIO()
    _write_document(prov_doc, buffer, output_format, options)
    data = buffer.getvalue()
    if b"\r" not in data:
        data = _highlight(data.decode("utf-8"), lexer).encode("utf-8")
    outfile.write(data)


def _write_document(
    prov_doc: ProvDocument,
    stream: IO[Any],
    output_format: str,
    options: Mapping[str, Any],
) -> None:
    """Write ``prov_doc`` to ``stream`` in ``output_format`` with the writer ``options``."""
    if output_format in GRAPHVIZ_SUPPORTED_FORMATS:
        from prov.dot import prov_to_dot

        dot = prov_to_dot(prov_doc, **options)
        # pydot's stub says create() returns `str`, but its own docstring
        # says (and it actually does, for binary Graphviz formats) return
        # `bytes`; this is an inaccuracy in pydot's stub, not a bug here.
        stream.write(cast(bytes, dot.create(format=output_format)))
        return
    try:
        prov_doc.serialize(stream, format=output_format, **options)
    except serializers.DoNotExist as e:
        raise CLIError(str(e)) from e


def _lexer_name(fmt: str, writer_options: Mapping[str, Any]) -> str | None:
    """Return the Pygments lexer name for the ``fmt`` output, or ``None`` if it has none.

    ``rdf`` keys on the ``rdf_format`` writer option, which defaults to ``trig``.
    The other Graphviz formats have no lexer in the map.
    """
    if fmt == "rdf":
        return _RDF_LEXERS.get(writer_options.get("rdf_format", "trig"))
    return _LEXERS.get(fmt)


def _highlight(text: str, lexer_name: str) -> str:
    """Colour ``text`` with the ``lexer_name`` lexer and Pygments' 16-colour formatter.

    Removing the escape sequences gives ``text`` back, provided it holds no
    carriage return, which Pygments turns into a line feed.
    """
    from pygments import highlight
    from pygments.formatters import TerminalFormatter
    from pygments.lexers import get_lexer_by_name

    lexer = get_lexer_by_name(lexer_name, stripnl=False, ensurenl=False)
    return highlight(text, lexer, TerminalFormatter())


def _use_color(choice: str, outfile: str) -> bool:
    """Decide whether the output is coloured, from ``--color``, ``outfile`` and the environment.

    ``auto`` colours standard output on a terminal that supports it, when
    Pygments imports. ``always`` without Pygments is a :class:`CLIError`.
    """
    if choice == "never":
        return False
    if choice == "auto" and not _on_color_terminal(outfile):
        return False
    try:
        importlib.import_module("pygments")
    except ImportError:
        if choice == "always":
            raise CLIError(
                '--color=always needs the optional "pygments" extra; '
                'install "prov[pygments]"'
            ) from None
        return False
    return True


def _on_color_terminal(outfile: str) -> bool:
    """Return whether ``auto`` may colour.

    It may when the output is standard output on a terminal, ``NO_COLOR`` is
    unset or empty and ``TERM`` is not ``dumb``.
    """
    isatty = getattr(sys.stdout, "isatty", None)
    return (
        outfile == "-"
        and callable(isatty)
        and bool(isatty())
        and not os.environ.get("NO_COLOR")
        and os.environ.get("TERM") != "dumb"
    )


def _output_format(path: str, flag: str) -> tuple[str, dict[str, str]]:
    """Resolve the output format and writer options for ``path`` and the ``-f`` ``flag``.

    An explicit flag is used as given, with no options. ``auto`` takes the
    extension's row, else a Graphviz format named by the extension, else
    PROV-JSON, which is also the format for standard output.
    """
    fmt, options = _input_format(path, flag)
    if fmt != "auto":
        return fmt, options
    graphviz = os.path.splitext(path)[1][1:].lower()
    return (graphviz if graphviz in GRAPHVIZ_SUPPORTED_FORMATS else "json"), {}


def _writer_names(fmt: str) -> frozenset[str] | None:
    """Return the options the ``fmt`` writer declares, or ``None`` if it is not registered."""
    if fmt in GRAPHVIZ_SUPPORTED_FORMATS:
        return _GRAPHVIZ_OPTIONS
    cls = _registered().get(fmt)
    return None if cls is None else cls.serialize_options


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog=_PROG,
        description="Convert a PROV document between formats.",
        epilog="""examples:
  prov-convert doc.json doc.provn
  prov-convert doc.provn doc.xml
  prov-convert doc.json doc.svg
  prov-convert -f jsonld < doc.json > doc.jsonld
  prov-convert -f provn -w width=none doc.json doc.provn
  prov-convert -i provn -r profile=lenient doc.provn doc.json
  prov-convert --color always -f provn doc.json | less -R
""",
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input-format",
        default="auto",
        help=(
            f"input format: {_format_names()}, or auto to use the file "
            "extension, else the content; default: %(default)s"
        ),
    )
    parser.add_argument(
        "-f",
        "--format",
        default="auto",
        help=(
            f"output format: {_format_names()}, a Graphviz output format "
            "(e.g. svg, pdf, png), or auto to use the file extension, else "
            "json; default: %(default)s"
        ),
    )
    parser.add_argument(
        "-w",
        "--writer-option",
        action="append",
        type=_pair,
        metavar="NAME=VALUE",
        help=(
            "pass an option to the writer, repeatable; none, true and false (any "
            "case) and integers are typed, anything else is a string; accepted "
            f"names: {_option_names('serialize_options')}; "
            f"Graphviz formats: {', '.join(sorted(_GRAPHVIZ_OPTIONS))}"
        ),
    )
    parser.add_argument(
        "-r",
        "--reader-option",
        action="append",
        type=_pair,
        metavar="NAME=VALUE",
        help=(
            "pass an option to the reader, repeatable, typed like -w; accepted "
            f"names: {_option_names('deserialize_options')}"
        ),
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help=(
            "colour the output with Pygments; auto does so for standard output on "
            "a terminal, unless NO_COLOR is set to a value or TERM is dumb, and "
            "always colours a file or pipe too; default: %(default)s"
        ),
    )
    parser.add_argument(
        "infile", nargs="?", default="-", help="input file (default: stdin)"
    )
    parser.add_argument(
        "outfile", nargs="?", default="-", help="output file (default: stdout)"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {prov.__version__}"
    )
    return parser


def _convert(argv: list[str] | None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_format, reader_table = _input_format(args.infile, args.input_format)
    output_format, writer_table = _output_format(args.outfile, args.format)
    reader_options = _options(
        args.reader_option or [],
        "reader",
        input_format,
        _reader_names(input_format),
        reader_table,
    )
    writer_options = _options(
        args.writer_option or [],
        "writer",
        output_format,
        _writer_names(output_format),
        writer_table,
    )
    color = _use_color(args.color, args.outfile)
    with contextlib.ExitStack() as streams:
        infile = streams.enter_context(_open_binary(parser, args.infile, "rb", "stdin"))
        outfile = streams.enter_context(
            _open_binary(parser, args.outfile, "wb", "stdout")
        )
        convert_file(
            infile,
            outfile,
            output_format,
            input_format,
            reader_options=reader_options,
            writer_options=writer_options,
            color=color,
        )
        outfile.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the ``prov-convert`` command-line tool.

    Parses ``-f/--format``, ``-i/--input-format``, the repeatable
    ``-w/--writer-option`` and ``-r/--reader-option`` (``NAME=VALUE``), ``--color``, an
    optional input file (default stdin), and an optional output file (default
    stdout), then
    converts between them via :func:`convert_file`. Files are opened after
    parsing; the standard streams are used for ``-`` and are not closed.

    Args:
        argv: The command-line arguments, without the program name. ``None``
            means ``sys.argv[1:]``. ``sys.argv`` is never modified.

    Returns:
        ``0`` on success, ``2`` after printing ``prov-convert: error: ...``
        to stderr when reading or converting fails, or ``130`` on
        ``KeyboardInterrupt``. A usage error exits through argparse with
        status 2.
    """
    return _run(_PROG, lambda: _convert(argv))


if __name__ == "__main__":
    sys.exit(main())

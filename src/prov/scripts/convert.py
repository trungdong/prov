"""Convert a PROV document between PROV-JSON, PROV-N, PROV-XML, PROV-O, PROV-JSONLD and Graphviz output formats."""

import os
import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from collections.abc import Mapping
from typing import Any, BinaryIO, cast

import prov
from prov import serializers
from prov.scripts import (
    _format_from_extension,
    _format_names,
    _input_format,
    _open_binary,
    _read,
    _run,
)

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


class CLIError(Exception):
    """A fatal error that :func:`main` reports as one ``prov-convert: error:`` line."""

    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


def convert_file(
    infile: BinaryIO,
    outfile: BinaryIO,
    output_format: str,
    input_format: str = "json",
    *,
    reader_options: Mapping[str, Any] | None = None,
    writer_options: Mapping[str, Any] | None = None,
) -> None:
    """Read a PROV document from ``infile`` and write it to ``outfile`` in ``output_format``.

    ``infile`` is read in ``input_format`` (default PROV-JSON; ``"auto"``
    detects the format from the content). A name in
    :data:`GRAPHVIZ_SUPPORTED_FORMATS` is rendered through
    :func:`~prov.dot.prov_to_dot` and Graphviz, and any other
    ``output_format`` is written by
    :meth:`~prov.model.ProvDocument.serialize`.

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
        writer_options: Keyword options for the output format's writer.

    Raises:
        CLIError: If ``input_format`` is not a registered serializer format,
            or if ``output_format`` is not a Graphviz format and not a
            registered serializer format.
    """
    try:
        prov_doc = _read(infile, input_format, reader_options or {})
    except serializers.DoNotExist as e:
        raise CLIError(f'Input format "{input_format}" is not supported.') from e

    if output_format in GRAPHVIZ_SUPPORTED_FORMATS:
        from prov.dot import prov_to_dot

        dot = prov_to_dot(prov_doc)
        # pydot's stub says create() returns `str`, but its own docstring
        # says (and it actually does, for binary Graphviz formats) return
        # `bytes`; this is an inaccuracy in pydot's stub, not a bug here.
        content = cast(bytes, dot.create(format=output_format))
        outfile.write(content)
        return
    try:
        prov_doc.serialize(outfile, format=output_format, **(writer_options or {}))
    except serializers.DoNotExist as e:
        raise CLIError(f'Output format "{output_format}" is not supported.') from e


def _output_format(path: str, flag: str) -> tuple[str, dict[str, str]]:
    """Resolve the output format and writer options for ``path`` and the ``-f`` ``flag``.

    An explicit flag is used as given, with no options. ``auto`` takes the
    extension's row, else a Graphviz format named by the extension, else
    PROV-JSON, which is also the format for standard output.
    """
    flag = flag.lower()
    if flag != "auto":
        return flag, {}
    row = _format_from_extension(path)
    if row is not None:
        return row
    graphviz = os.path.splitext(path)[1][1:].lower()
    return (graphviz if graphviz in GRAPHVIZ_SUPPORTED_FORMATS else "json"), {}


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="prov-convert",
        description="Convert a PROV document between formats.",
        epilog="""examples:
  prov-convert doc.json doc.provn
  prov-convert doc.provn doc.xml
  prov-convert doc.json doc.svg
  prov-convert -f jsonld < doc.json > doc.jsonld
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
        "infile", nargs="?", default="-", help="input file (default: stdin)"
    )
    parser.add_argument(
        "outfile", nargs="?", default="-", help="output file (default: stdout)"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {prov.__version__}"
    )
    return parser


def _convert(parser: ArgumentParser, args: Namespace) -> int:
    owned: list[BinaryIO] = []
    try:
        infile, owns_infile = _open_binary(parser, args.infile, "rb", "stdin")
        if owns_infile:
            owned.append(infile)
        outfile, owns_outfile = _open_binary(parser, args.outfile, "wb", "stdout")
        if owns_outfile:
            owned.append(outfile)
        input_format, reader_options = _input_format(args.infile, args.input_format)
        output_format, writer_options = _output_format(args.outfile, args.format)
        convert_file(
            infile,
            outfile,
            output_format,
            input_format,
            reader_options=reader_options,
            writer_options=writer_options,
        )
        outfile.flush()
    finally:
        for stream in owned:
            stream.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the ``prov-convert`` command-line tool.

    Parses ``-f/--format``, ``-i/--input-format``, an optional input file
    (default stdin), and an optional output file (default stdout), then
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
    parser = _build_parser()
    args = parser.parse_args(argv)
    return _run("prov-convert", lambda: _convert(parser, args))


if __name__ == "__main__":
    sys.exit(main())

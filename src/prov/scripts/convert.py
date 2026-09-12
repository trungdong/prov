#!/usr/bin/env python
"""
convert -- Convert a PROV document between PROV-JSON, PROV-N, PROV-XML, PROV-O, PROV-JSONLD and graphical formats

@author:     Trung Dong Huynh

@copyright:  2026 Trung Dong Huynh

@license:    MIT License

@contact:    trungdong@donggiang.com
@deffield    updated: 2026-09-12
"""

import logging
import os
import sys
import traceback
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from typing import BinaryIO, cast

from prov import serializers
from prov.model import ProvDocument

logger = logging.getLogger(__name__)

__all__: list[str] = []
__version__ = 0.1
__date__ = "2014-03-14"
__updated__ = "2026-09-12"

DEBUG = 0
TESTRUN = 0
PROFILE = 0

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
    """Generic exception to raise and log different fatal errors."""

    def __init__(self, msg: str):
        super().__init__(type(self))
        self.msg = f"E: {msg}"

    def __str__(self) -> str:
        return self.msg


def _open_binary(
    parser: ArgumentParser, path: str, mode: str, standard_name: str
) -> tuple[BinaryIO, bool]:
    """Open ``path`` in binary ``mode``, or return the standard stream for ``"-"``.

    ``standard_name`` is ``"stdin"`` or ``"stdout"``; its ``.buffer`` is
    resolved only when ``path`` is ``"-"``, so the other standard stream is
    never touched. The second element says whether the caller owns the
    returned stream and must close it; the standard streams belong to the
    process. An unopenable path is reported through
    :meth:`argparse.ArgumentParser.error`, which exits with status 2 like
    argparse's own file handling did.
    """
    if path == "-":
        return cast(BinaryIO, getattr(sys, standard_name).buffer), False
    try:
        return cast(BinaryIO, open(path, mode)), True
    except OSError as exc:
        parser.error(f"can't open '{path}': {exc}")


def convert_file(
    infile: BinaryIO,
    outfile: BinaryIO,
    output_format: str,
    input_format: str = "json",
) -> None:
    """Read a PROV document from ``infile`` and write it to ``outfile`` in ``output_format``.

    ``infile`` is read in ``input_format`` (default PROV-JSON) through
    :meth:`~prov.model.ProvDocument.deserialize`. For ``output_format``,
    ``"provn"`` is written directly via
    :meth:`~prov.model.ProvDocument.get_provn`, a name in
    :data:`GRAPHVIZ_SUPPORTED_FORMATS` is rendered through
    :func:`~prov.dot.prov_to_dot` and Graphviz, and any other format is
    delegated to :meth:`~prov.model.ProvDocument.serialize`.

    Args:
        infile: File-like object (opened in binary mode) to read the source
            document from.
        outfile: File-like object (opened in binary mode) to write the
            converted output to.
        output_format: Target format name (e.g. ``"json"``, ``"xml"``,
            ``"rdf"``, ``"jsonld"``, ``"provn"``, or a Graphviz output format such as
            ``"svg"``/``"pdf"``/``"png"``).
        input_format: Source format name, any registered serializer format.

    Raises:
        CLIError: If ``input_format`` is not a registered serializer format,
            or if ``output_format`` is not ``"provn"``, not a Graphviz
            format, and not a registered serializer format.
    """
    try:
        prov_doc = ProvDocument.deserialize(infile, format=input_format)
    except serializers.DoNotExist as e:
        raise CLIError(f'Input format "{input_format}" is not supported.') from e

    # Formats not supported by prov.serializers
    if output_format == "provn":
        outfile.write(prov_doc.get_provn().encode())
    elif output_format in GRAPHVIZ_SUPPORTED_FORMATS:
        from prov.dot import prov_to_dot

        dot = prov_to_dot(prov_doc)
        # pydot's stub says create() returns `str`, but its own docstring
        # says (and it actually does, for binary Graphviz formats) return
        # `bytes`; this is an inaccuracy in pydot's stub, not a bug here.
        content = cast(bytes, dot.create(format=output_format))
        outfile.write(content)
    else:
        # Try supported serializers:
        try:
            prov_doc.serialize(outfile, format=output_format)
        except serializers.DoNotExist as e:
            raise CLIError(f'Output format "{output_format}" is not supported.') from e


def main(argv: list[str] | None = None) -> int:  # IGNORE:C0111
    """Run the ``prov-convert`` command-line tool.

    Parses ``-f/--format``, ``-i/--input-format``, an optional input file
    (default stdin), and an optional output file (default stdout), then
    converts between them via :func:`convert_file`. Files are opened after
    parsing; the standard streams are used for ``-`` and are not closed.

    Args:
        argv: Extra command-line arguments. If not ``None``, they are
            appended to ``sys.argv`` (which is *not* replaced) before
            argument parsing, so ``sys.argv[0]`` is still used as the
            program name.

    Returns:
        ``0`` on success or on ``KeyboardInterrupt``; ``2`` if an exception
        was raised while parsing arguments or converting the file (unless
        ``DEBUG``/``TESTRUN`` is set, in which case the exception
        propagates instead).
    """

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = f"v{__version__}"
    program_build_date = str(__updated__)
    program_version_message = f"%(prog)s {program_version} ({program_build_date})"
    program_shortdesc = __doc__.split("\n")[1]
    program_license = f"""{program_shortdesc}

  Copyright 2026 Trung Dong Huynh.

  Licensed under the MIT License
  https://github.com/trungdong/prov/blob/main/LICENSE

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
"""

    try:
        # Setup argument parser
        parser = ArgumentParser(
            description=program_license, formatter_class=RawDescriptionHelpFormatter
        )
        parser.add_argument(
            "-i",
            "--input-format",
            dest="input_format",
            action="store",
            default="json",
            help="input format: json, xml, rdf, jsonld or provn",
        )
        parser.add_argument(
            "-f",
            "--format",
            dest="format",
            action="store",
            default="json",
            help="output format: json, xml, rdf, jsonld, provn, or a Graphviz output format (e.g. svg, pdf, png)",
        )
        parser.add_argument(
            "infile", nargs="?", default="-", help="input file (default: stdin)"
        )
        parser.add_argument(
            "outfile", nargs="?", default="-", help="output file (default: stdout)"
        )
        parser.add_argument(
            "-V", "--version", action="version", version=program_version_message
        )

        args = parser.parse_args()
        owned: list[BinaryIO] = []
        try:
            infile, owns_infile = _open_binary(parser, args.infile, "rb", "stdin")
            if owns_infile:
                owned.append(infile)
            outfile, owns_outfile = _open_binary(parser, args.outfile, "wb", "stdout")
            if owns_outfile:
                owned.append(outfile)
            convert_file(
                infile, outfile, args.format.lower(), args.input_format.lower()
            )
            outfile.flush()
        finally:
            for stream in owned:
                stream.close()

        return 0
    except KeyboardInterrupt:
        # handle keyboard interrupt
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            traceback.print_exc()
            raise e
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    logging.basicConfig(level=(logging.DEBUG if DEBUG else logging.INFO))
    if TESTRUN:
        import doctest

        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats

        profile_filename = "converter_profile.txt"
        cProfile.run("main()", profile_filename)
        with open("profile_stats.txt", "wb") as statsfile:
            p = pstats.Stats(profile_filename, stream=statsfile)
            stats = p.strip_dirs().sort_stats("cumulative")
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())

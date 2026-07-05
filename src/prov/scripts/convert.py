#!/usr/bin/env python
"""
convert -- Convert PROV-JSON to RDF, PROV-N, PROV-XML, or graphical formats (SVG, PDF, PNG)

@author:     Trung Dong Huynh

@copyright:  2025 Trung Dong Huynh

@license:    MIT License

@contact:    trungdong@donggiang.com
@deffield    updated: 2025-06-07
"""

from __future__ import annotations

import io
import logging
import os
import sys
import traceback
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter
from typing import cast

from prov import serializers
from prov.model import ProvDocument

logger = logging.getLogger(__name__)

__all__: list[str] = []
__version__ = 0.1
__date__ = "2014-03-14"
__updated__ = "2025-06-07"

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


def convert_file(infile: io.FileIO, outfile: io.FileIO, output_format: str) -> None:
    """Read a PROV document from ``infile`` and write it to ``outfile`` in ``output_format``.

    ``infile`` is auto-detected across all registered deserialization
    formats (see :meth:`~prov.model.ProvDocument.deserialize`). For
    ``output_format``, ``"provn"`` is written directly via
    :meth:`~prov.model.ProvDocument.get_provn`, a name in
    :data:`GRAPHVIZ_SUPPORTED_FORMATS` is rendered through
    :func:`~prov.dot.prov_to_dot` and Graphviz, and any other format is
    delegated to :meth:`~prov.model.ProvDocument.serialize`.

    Args:
        infile: File-like object to read the source document from.
        outfile: File-like object (opened in binary mode) to write the
            converted output to.
        output_format: Target format name (e.g. ``"json"``, ``"xml"``,
            ``"rdf"``, ``"provn"``, or a Graphviz output format such as
            ``"svg"``/``"pdf"``/``"png"``).

    Raises:
        CLIError: If ``output_format`` is not ``"provn"``, not a Graphviz
            format, and not a registered serializer format.
    """
    prov_doc = ProvDocument.deserialize(infile)

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

    Parses ``-f/--format``, an optional input file (default stdin), and an
    optional output file (default stdout), then converts between them via
    :func:`convert_file`.

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

  Copyright 2025 Trung Dong Huynh.

  Licensed under the MIT License
  https://github.com/trungdong/prov/blob/master/LICENSE

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
            "-f",
            "--format",
            dest="format",
            action="store",
            default="json",
            help="output format: json, xml, provn, or one supported by GraphViz (e.g. svg, pdf)",
        )
        parser.add_argument("infile", nargs="?", type=FileType("r"), default=sys.stdin)
        parser.add_argument(
            "outfile", nargs="?", type=FileType("wb"), default=sys.stdout
        )
        parser.add_argument(
            "-V", "--version", action="version", version=program_version_message
        )

        args = None
        try:
            # Process arguments
            args = parser.parse_args()
            convert_file(args.infile, args.outfile, args.format.lower())
        finally:
            if args:
                if args.infile:
                    args.infile.close()
                if args.outfile:
                    args.outfile.close()

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

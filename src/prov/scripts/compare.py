"""Compare two PROV documents in any registered format for equivalence."""

import contextlib
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import prov
from prov.scripts import _format_names, _input_format, _open_binary, _read, _run

_PROG = "prov-compare"


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog=_PROG,
        description="Compare two PROV documents for equivalence.",
        epilog="""exit status is 0 if the documents are equal, 1 if they differ and 2 on an error.

examples:
  prov-compare a.provn b.xml
  prov-compare a.json b.json
  prov-compare -f json -F xml doc.json doc.xml
  prov-compare -F provn doc.json doc.provn
  prov-compare -f json -F xml - doc.xml < doc.json
""",
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument("file1", help="first document ('-' reads standard input)")
    parser.add_argument("file2", help="second document ('-' reads standard input)")
    parser.add_argument(
        "-f",
        "--format1",
        default="auto",
        help=(
            f"file 1's format: {_format_names()}, or auto to use the file "
            "extension, else the content; default: %(default)s"
        ),
    )
    parser.add_argument(
        "-F",
        "--format2",
        default="auto",
        help=(
            f"file 2's format: {_format_names()}, or auto to use the file "
            "extension, else the content; default: %(default)s"
        ),
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {prov.__version__}"
    )
    return parser


def _compare(argv: list[str] | None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.file1 == "-" and args.file2 == "-":
        parser.error("only one of file1 and file2 may be '-' (standard input)")
    with contextlib.ExitStack() as streams:
        sources = []
        for path, flag in ((args.file1, args.format1), (args.file2, args.format2)):
            stream = streams.enter_context(_open_binary(parser, path, "rb", "stdin"))
            sources.append((stream, *_input_format(path, flag)))
        doc1, doc2 = (_read(*source) for source in sources)
        return int(doc1 != doc2)


def main(argv: list[str] | None = None) -> int:
    """Run the ``prov-compare`` command-line tool.

    Parses two positional file arguments plus ``-f/--format1`` and
    ``-F/--format2`` (each defaulting to ``"auto"``, which takes the file
    extension, else the content), reads both files, and compares the
    resulting documents for equality. Files are opened after parsing; ``-``
    stands for standard input for at most one of them and is not closed; an
    unopenable path is a usage error (exit 2).

    Args:
        argv: The command-line arguments, without the program name. ``None``
            means ``sys.argv[1:]``. ``sys.argv`` is never modified.

    Returns:
        ``0`` if the two documents are equal, ``1`` if they differ, ``2``
        after printing ``prov-compare: error: ...`` to stderr when reading
        fails, or ``130`` on ``KeyboardInterrupt``. A usage error exits
        through argparse with status 2.
    """
    return _run(_PROG, lambda: _compare(argv))


if __name__ == "__main__":
    sys.exit(main())

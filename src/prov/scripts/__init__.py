import sys
from argparse import ArgumentParser
from typing import BinaryIO, cast


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

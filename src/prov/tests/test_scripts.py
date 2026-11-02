"""In-process coverage tests for the ``prov-convert`` / ``prov-compare``
console scripts (``src/prov/scripts/convert.py`` and ``compare.py``).

``test_cli_smoke.py`` runs these scripts in a subprocess, which exercises the
end-to-end console-script wiring but contributes nothing to coverage
measurement. This module calls ``main()`` (and, for ``convert``,
``convert_file()``) directly in-process so the bulk of both modules is
actually measured, while leaving the smoke test untouched.

``main(argv)`` parses ``argv`` and leaves ``sys.argv`` alone; ``main()`` with
no argument parses ``sys.argv[1:]``. Most tests patch ``sys.argv`` and call
``main()``; those that pass ``argv`` leave ``sys.argv`` untouched.
"""

import contextlib
import inspect
import io
import re
import shutil
import subprocess  # nosec B404
import sys
import warnings
from pathlib import Path
from typing import NoReturn, cast

import pytest
from pygments.util import ClassNotFound

import prov
from prov.model import ProvDocument
from prov.scripts import _format_names, _pair, _run, _typed
from prov.scripts.compare import (
    _build_parser as compare_build_parser,
    main as compare_main,
)
from prov.scripts.convert import (
    _GRAPHVIZ_OPTIONS,
    GRAPHVIZ_SUPPORTED_FORMATS,
    CLIError,
    _build_parser as convert_build_parser,
    _output_format,
    convert_file,
    main as convert_main,
)
from prov.serializers import Registry
from prov.tests.conftest import ex_document, unresolved_sentence
from prov.tests.examples import primer_example, w3c_publication_1


@pytest.fixture
def infile(tmp_path):
    path = tmp_path / "doc.json"
    primer_example().serialize(str(path), format="json")
    return path


class _Pipe:
    """Makes a stream read like a pipe."""

    def seekable(self) -> bool:
        return False

    def seek(self, *args, **kwargs) -> NoReturn:
        raise io.UnsupportedOperation("seek")


class NonSeekableBytes(_Pipe, io.BytesIO):
    """A binary stream that reads like a pipe."""


class NonSeekableText(_Pipe, io.StringIO):
    """A text-only stream (no ``.buffer``) that reads like a pipe."""


class ReadOnlyBytes:
    """A stream with a ``read`` method and nothing else."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, *args) -> bytes:
        return self._data


STDIN_STREAMS = {
    "seekable-bytes": lambda data: io.TextIOWrapper(io.BytesIO(data)),
    "pipe-bytes": lambda data: io.TextIOWrapper(NonSeekableBytes(data)),
    "pipe-text": lambda data: NonSeekableText(data.decode()),
    "no-seekable": ReadOnlyBytes,
}

EXTRAS = {"xml": "lxml", "rdf": "rdflib"}
TURTLE = {"rdf_format": "turtle"}
needs_dot = pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not installed"
)


def _write(path, fmt: str, **options) -> None:
    primer_example().serialize(str(path), format=fmt, **options)


def _read_back(path, fmt: str, **options) -> ProvDocument:
    return ProvDocument.deserialize(str(path), format=fmt, **options)


# prov-convert.


def test_convert_to_xml(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_format_is_case_insensitive(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "XML", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_parses_explicit_argv_and_leaves_sys_argv_alone(
    infile, tmp_path
) -> None:
    outfile = tmp_path / "doc.xml"
    before = list(sys.argv)
    rc = convert_main(["-f", "xml", str(infile), str(outfile)])
    assert rc == 0
    assert sys.argv == before
    assert b"<prov:document" in outfile.read_bytes()


def test_convert_to_provn(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.provn"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "provn", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    content = outfile.read_text(encoding="utf-8")
    assert content
    # PROV-N documents open/close with these keywords.
    assert content.startswith("document")
    assert "endDocument" in content
    # serialize(format="provn") writes exactly get_provn(), byte for byte.
    expected = ProvDocument.deserialize(str(infile), format="json").get_provn()
    assert outfile.read_bytes() == expected.encode()


@needs_dot
def test_convert_to_dot(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.dot"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "dot", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_the_graphviz_writer_options_are_prov_to_dots_keywords() -> None:
    pytest.importorskip("pydot")
    from prov.dot import prov_to_dot

    parameters = set(inspect.signature(prov_to_dot).parameters)
    assert parameters - {"bundle"} == _GRAPHVIZ_OPTIONS


@needs_dot
def test_convert_to_rendered_graphviz_format(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.svg"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "svg", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_unsupported_format_returns_2_and_writes_one_error_line(
    infile, tmp_path, capsys
) -> None:
    rc = convert_main(["-f", "bogus", str(infile), str(tmp_path / "doc.bogus")])
    assert rc == 2
    assert (
        capsys.readouterr().err
        == 'prov-convert: error: No serializer available for the format "bogus"\n'
    )


def test_convert_file_raises_cli_error_for_unsupported_format(infile, tmp_path) -> None:
    # Exercise convert_file() directly for the CLIError branch.
    # The message carries no prefix.
    assert "bogus" not in GRAPHVIZ_SUPPORTED_FORMATS
    with (
        open(infile) as in_stream,
        open(tmp_path / "doc.bogus", "wb") as out_stream,
        pytest.raises(CLIError) as ctx,
    ):
        convert_file(in_stream, out_stream, "bogus")
    assert str(ctx.value) == 'No serializer available for the format "bogus"'
    assert ctx.value.msg == 'No serializer available for the format "bogus"'


def test_convert_missing_input_file_exits_2(infile, tmp_path, monkeypatch) -> None:
    # A path that cannot be opened is reported through parser.error(),
    # which exits 2; that SystemExit propagates out of main() rather than
    # being caught by the `except Exception` handler.
    missing = tmp_path / "does-not-exist.json"
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(missing), str(outfile)]
    )
    monkeypatch.setenv("COLUMNS", "200")
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)
    with pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 2
    usage, error = stderr.getvalue().splitlines()
    assert usage.startswith("usage: prov-convert ")
    assert error.startswith("prov-convert: error: can't open ")


def test_convert_closes_files_even_when_conversion_fails(
    infile, tmp_path, monkeypatch
) -> None:
    outfile = tmp_path / "doc.xml"
    captured = {}

    def spy_convert_file(in_stream, out_stream, *args, **kwargs) -> NoReturn:
        captured["infile"] = in_stream
        captured["outfile"] = out_stream
        raise RuntimeError("boom")

    monkeypatch.setattr("prov.scripts.convert.convert_file", spy_convert_file)
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 2
    assert captured["infile"].closed
    assert captured["outfile"].closed


@pytest.fixture
def provn_infile(tmp_path):
    path = tmp_path / "doc.provn"
    primer_example().serialize(str(path), format="provn")
    return path


# argparse.FileType is deprecated from Python 3.14 (#441); the scripts must
# not use it on any interpreter.
@pytest.mark.filterwarnings("error::PendingDeprecationWarning")
@pytest.mark.filterwarnings("error::DeprecationWarning")
def test_convert_from_provn(provn_infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-convert", "-i", "provn", "-f", "json", str(provn_infile), str(outfile)],
    )
    assert convert_main() == 0
    assert ProvDocument.deserialize(str(outfile), format="json") == primer_example()


def test_convert_from_xml(tmp_path, monkeypatch) -> None:
    pytest.importorskip("lxml")
    infile = tmp_path / "doc.xml"
    primer_example().serialize(str(infile), format="xml")
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-i", "xml", str(infile), str(outfile)]
    )
    assert convert_main() == 0
    assert ProvDocument.deserialize(str(outfile), format="json") == primer_example()


def test_convert_unknown_input_format_exits_2(
    infile, tmp_path, monkeypatch, capsys
) -> None:
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-i", "nope", str(infile), str(outfile)]
    )
    assert convert_main() == 2
    assert (
        capsys.readouterr().err
        == 'prov-convert: error: No serializer available for the format "nope"\n'
    )


def test_convert_reads_provn_from_stdin(provn_infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(sys, "argv", ["prov-convert", "-i", "provn", "-f", "json"])
    monkeypatch.setattr(
        sys, "stdin", io.TextIOWrapper(io.BytesIO(provn_infile.read_bytes()))
    )
    with outfile.open("wb") as out:
        monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(out))
        assert convert_main() == 0
    assert ProvDocument.deserialize(str(outfile), format="json") == primer_example()


def test_convert_works_with_stdin_set_to_none(infile, tmp_path, monkeypatch) -> None:
    # Both files given explicitly, so sys.stdin is never touched; this must
    # succeed even when sys.stdin is None (e.g. under some process
    # supervisors).
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-convert", "-i", "json", "-f", "xml", str(infile), str(outfile)],
    )
    monkeypatch.setattr(sys, "stdin", None)
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_leaves_standard_streams_open(provn_infile, monkeypatch) -> None:
    # "-" (the default) means the standard streams, which belong to the
    # caller: the tool must not close them after use.
    stdin = io.TextIOWrapper(io.BytesIO(provn_infile.read_bytes()))
    stdout = io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(sys, "argv", ["prov-convert", "-i", "provn", "-f", "json"])
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    assert convert_main() == 0
    assert not stdin.buffer.closed
    assert not stdout.buffer.closed
    stdout.flush()
    written = stdout.buffer.getvalue().decode("utf-8")
    assert ProvDocument.deserialize(content=written, format="json") == primer_example()


def test_convert_unwritable_output_path_exits_2(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "no-such-dir" / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 2


@pytest.mark.parametrize(
    ("in_name", "in_format", "in_options", "out_name", "out_format", "out_options"),
    [
        pytest.param("doc.provn", "provn", {}, "out.json", "json", {}, id="provn-in"),
        pytest.param("IN.PROVN", "provn", {}, "OUT.XML", "xml", {}, id="upper-case"),
        pytest.param("doc.json", "json", {}, "out.xml", "xml", {}, id="xml-out"),
        pytest.param("doc.provx", "xml", {}, "out.json", "json", {}, id="provx-in"),
        pytest.param("doc.txt", "json", {}, "out.json", "json", {}, id="txt-in"),
        pytest.param("doc.ttl", "rdf", TURTLE, "out.json", "json", {}, id="ttl-in"),
        pytest.param(
            "doc.rdf", "rdf", {"rdf_format": "xml"}, "out.json", "json", {}, id="rdf-in"
        ),
        pytest.param("doc.json", "json", {}, "out.ttl", "rdf", TURTLE, id="ttl-out"),
    ],
)
def test_convert_detects_formats_from_extensions(
    tmp_path, in_name, in_format, in_options, out_name, out_format, out_options
) -> None:
    for name in (in_format, out_format):
        if name in EXTRAS:
            pytest.importorskip(EXTRAS[name])
    source = tmp_path / in_name
    target = tmp_path / out_name
    _write(source, in_format, **in_options)
    assert convert_main([str(source), str(target)]) == 0
    assert _read_back(target, out_format, **out_options) == primer_example()


def test_convert_detects_the_content_when_the_extension_is_unknown(tmp_path) -> None:
    # "doc" has no extension and sits in a directory whose name looks like PROV-N.
    folder = tmp_path / "a.provn"
    folder.mkdir()
    source = folder / "doc"
    target = tmp_path / "out.json"
    _write(source, "provn")
    assert convert_main([str(source), str(target)]) == 0
    assert _read_back(target, "json") == primer_example()


def test_convert_accepts_auto_in_any_case(tmp_path) -> None:
    source = tmp_path / "doc.provn"
    target = tmp_path / "out.xml"
    _write(source, "provn")
    assert convert_main(["-i", "AUTO", "-f", "auto", str(source), str(target)]) == 0
    assert _read_back(target, "xml") == primer_example()
    # convert_file() takes the name in any case too.
    with open(source, "rb") as in_stream, open(tmp_path / "copy.json", "wb") as out:
        convert_file(in_stream, out, "json", "AUTO")
    assert _read_back(tmp_path / "copy.json", "json") == primer_example()


def test_convert_explicit_flags_replace_the_extension_table(tmp_path) -> None:
    rdflib_parsers = pytest.importorskip("rdflib.plugins.parsers.notation3")
    source = tmp_path / "doc.json"
    target = tmp_path / "out.ttl"
    _write(source, "json")
    assert convert_main(["-f", "rdf", str(source), str(target)]) == 0
    assert _read_back(target, "rdf", rdf_format="trig") == primer_example()
    # The table's Turtle would read back here; the default TriG does not.
    with pytest.raises(rdflib_parsers.BadSyntax):
        _read_back(target, "rdf", rdf_format="turtle")


JSONLD_IN_JSON = (
    "'@context' is not a recognised PROV-N record-type keyword "
    "(e.g. 'entity', 'activity', 'wasGeneratedBy')"
)
NOT_DETECTED = (
    "Could not read from the source. To get a proper error message, "
    "specify the format with the 'format' parameter."
)


@pytest.mark.parametrize(
    ("name", "write", "flags", "message"),
    [
        pytest.param(
            "doc.json",
            lambda path: _write(path, "jsonld"),
            [],
            JSONLD_IN_JSON,
            id="jsonld-in-json-file",
        ),
        pytest.param(
            "export.xml",
            lambda path: _write(path, "json"),
            [],
            None,
            id="json-in-xml-file",
        ),
        pytest.param(
            "doc.provn",
            lambda path: _write(path, "provn"),
            ["-i", "json"],
            None,
            id="the-flag-wins-over-the-extension",
        ),
        pytest.param(
            "in.rdf",
            lambda path: _write(path, "rdf", rdf_format="xml"),
            ["-i", "rdf"],
            None,
            id="the-flag-drops-the-rdf-format",
        ),
        pytest.param(
            "doc.dat",
            lambda path: path.write_text("not a PROV document"),
            [],
            NOT_DETECTED,
            id="garbage",
        ),
        pytest.param(
            "doc.dat",
            lambda path: path.write_text("{}"),
            [],
            NOT_DETECTED,
            id="empty-document",
        ),
    ],
)
def test_convert_detection_errors_exit_2_with_one_line(
    tmp_path, capsys, name, write, flags, message
) -> None:
    source = tmp_path / name
    write(source)
    target = tmp_path / "out.json"
    assert convert_main([*flags, str(source), str(target)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("prov-convert: error: ")
    assert err.count("\n") == 1 and err.endswith("\n")
    if message is not None:
        assert err == f"prov-convert: error: {message}\n"


def test_convert_a_broken_document_on_stdin_exits_2_with_one_line(
    tmp_path, capsys, monkeypatch
) -> None:
    data = b"document\n  entity(ex:a)\nendDocument\n"
    monkeypatch.setattr(sys, "stdin", STDIN_STREAMS["pipe-bytes"](data))
    assert convert_main(["-", str(tmp_path / "out.json")]) == 2
    reason = unresolved_sentence("ex:a", "its prefix 'ex' is not declared")
    expected = f"{NOT_DETECTED} line 2, column 10: {reason}"
    assert capsys.readouterr().err == f"prov-convert: error: {expected}\n"


@pytest.mark.parametrize("stream", STDIN_STREAMS)
@pytest.mark.parametrize("fmt", ["json", "provn"])
def test_convert_detects_a_document_on_stdin(
    tmp_path, monkeypatch, stream, fmt
) -> None:
    data = primer_example().serialize(format=fmt).encode()
    monkeypatch.setattr(sys, "stdin", STDIN_STREAMS[stream](data))
    target = tmp_path / "out.json"
    assert convert_main(["-", str(target)]) == 0
    assert _read_back(target, "json") == primer_example()


def test_convert_an_empty_document_on_stdin_exits_2(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert convert_main([]) == 2
    assert capsys.readouterr().err == f"prov-convert: error: {NOT_DETECTED}\n"


@pytest.mark.parametrize(
    ("path", "flag", "expected"),
    [
        pytest.param("OUT.svg", "auto", ("svg", {}), id="graphviz"),
        pytest.param("out.dot", "AUTO", ("dot", {}), id="dot"),
        pytest.param("out.xml", "auto", ("xml", {}), id="table-first"),
        pytest.param("out.ttl", "auto", ("rdf", TURTLE), id="rdf-options"),
        pytest.param("out.jsonld", "auto", ("jsonld", {}), id="jsonld"),
        pytest.param("out.trig", "auto", ("rdf", {"rdf_format": "trig"}), id="trig"),
        pytest.param("out.nt", "auto", ("rdf", {"rdf_format": "nt"}), id="nt"),
        pytest.param("out.nq", "auto", ("rdf", {"rdf_format": "nquads"}), id="nq"),
        pytest.param("out.provx", "auto", ("xml", {}), id="provx"),
        pytest.param("out.rdf", "auto", ("rdf", {"rdf_format": "xml"}), id="rdf-xml"),
        pytest.param("out.provn", "auto", ("provn", {}), id="provn"),
        pytest.param("out.JSON", "auto", ("json", {}), id="json-upper-case"),
        pytest.param("-", "auto", ("json", {}), id="stdout"),
        pytest.param("out.bogus", "auto", ("json", {}), id="unknown"),
        pytest.param("out.", "auto", ("json", {}), id="bare-dot"),
        pytest.param("out.ttl", "RDF", ("rdf", {}), id="flag-drops-options"),
        pytest.param("out.svg", "xml", ("xml", {}), id="flag-wins"),
    ],
)
def test_output_format_resolution(path, flag, expected) -> None:
    assert _output_format(path, flag) == expected


# Options.

# The default profile refuses it and the lenient profile skips it with a warning.
UNKNOWN_STATEMENT = (
    "document\nprefix ex <http://example.org/>\nentity(ex:e2)\nfoo(ex:e1)\nendDocument"
)
# The default profile reads the bare mentionOf and the strict profile refuses it.
BARE_MENTION = (
    "document\nprefix ex <http://example.org/>\nentity(ex:e1)\n"
    "mentionOf(ex:e1, ex:e0, ex:b)\nendDocument"
)
# Under the default width the PROV-N writer wraps the wide statement.
ONE_LINE = b'ex:e1, [prov:label="Report", ex:note='


def _options_document() -> ProvDocument:
    """A document on which every writer option changes the output."""
    doc = ex_document()
    doc.entity("ex:e1", {"prov:label": "Report", "ex:note": "x" * 80})
    doc.entity("ex:e2")
    doc.alternateOf("ex:e1", "ex:e2").add_attributes({"ex:why": "x"})
    return doc


def _written(doc: ProvDocument, fmt: str, **options) -> bytes:
    """The bytes the library writes for ``doc`` with ``options``."""
    if fmt == "dot":
        from prov.dot import prov_to_dot

        return cast(bytes, prov_to_dot(doc, **options).create(format="dot"))
    buffer = io.BytesIO()
    doc.serialize(buffer, format=fmt, **options)
    return buffer.getvalue()


def _no_option(role: str, fmt: str, name: str, accepted: str) -> str:
    """The sentence for a ``fmt`` ``role`` (``writer`` or ``reader``) given option ``name``."""
    return f"the {fmt!r} {role} accepts no option {name!r}; it accepts: {accepted}"


@pytest.fixture
def options_infile(tmp_path):
    path = tmp_path / "doc.json"
    _options_document().serialize(str(path), format="json")
    return path


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("none", None),
        ("None", None),
        ("NONE", None),
        ("true", True),
        ("TRUE", True),
        ("False", False),
        ("80", 80),
        ("-1", -1),
        ("+5", 5),
        ("007", 7),
        ("trig", "trig"),
        ("", ""),
        ("1.5", "1.5"),
        ("1_0", "1_0"),
        ("\u0663", "\u0663"),
        ("5\n", "5\n"),
        (" 5", " 5"),
    ],
)
def test_option_values_are_typed(value, expected) -> None:
    typed = _typed(value)
    assert typed == expected
    assert type(typed) is type(expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("direction=a=b", ("direction", "a=b")), ("width=", ("width", ""))],
)
def test_an_option_splits_at_the_first_equals(text, expected) -> None:
    assert _pair(text) == expected


@pytest.mark.parametrize(
    ("main", "flags"),
    [
        (convert_main, ["-w", "width"]),
        (convert_main, ["-w", "=1"]),
        (convert_main, ["--reader-option", "profile"]),
        (compare_main, ["-r", "profile"]),
        (compare_main, ["-R", "=1"]),
    ],
)
def test_an_option_without_a_name_or_equals_is_a_usage_error(
    main, flags, infile, capsys
) -> None:
    with pytest.raises(SystemExit) as ctx:
        main([*flags, str(infile), str(infile)])
    assert ctx.value.code == 2
    assert "is not NAME=VALUE" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("flags", "fmt", "options", "shows"),
    [
        pytest.param(
            ["-f", "provn", "-w", "width=none"],
            "provn",
            {"width": None},
            ONE_LINE,
            id="none",
        ),
        pytest.param(
            ["-f", "provn", "-w", "width=40", "-w", "width=none"],
            "provn",
            {"width": None},
            ONE_LINE,
            id="last-wins",
        ),
        pytest.param(
            ["-f", "provn", "-w", "strict=true"],
            "provn",
            {"strict": True},
            b"",
            id="strict",
        ),
        pytest.param(
            ["-f", "json", "-w", "indent=2"], "json", {"indent": 2}, b"", id="json"
        ),
        pytest.param(
            ["-f", "jsonld", "-w", "context=embed"],
            "jsonld",
            {"context": "embed"},
            b"",
            id="jsonld",
        ),
        pytest.param(
            ["-f", "xml", "-w", "force_types=true"],
            "xml",
            {"force_types": True},
            b"",
            id="xml",
        ),
        pytest.param(
            ["-f", "dot", "-w", "use_labels=true"],
            "dot",
            {"use_labels": True},
            b"",
            id="dot",
            marks=needs_dot,
        ),
    ],
)
def test_writer_options_reach_the_writer(
    options_infile, tmp_path, flags, fmt, options, shows
) -> None:
    if fmt in EXTRAS:
        pytest.importorskip(EXTRAS[fmt])
    target = tmp_path / "out.dat"
    doc = _read_back(options_infile, "json")
    with warnings.catch_warnings():
        # The strict profile warns for each statement it drops.
        warnings.simplefilter("ignore")
        assert convert_main([*flags, str(options_infile), str(target)]) == 0
        written = target.read_bytes()
        assert written == _written(doc, fmt, **options)
        # The option changes the output, so the row pins more than the default.
        assert written != _written(doc, fmt)
    assert shows in written


def test_rdf_format_names_the_turtle_writer_and_reader(tmp_path) -> None:
    pytest.importorskip("rdflib")
    source = tmp_path / "doc.json"
    turtle = tmp_path / "out.dat"
    back = tmp_path / "back.json"
    _write(source, "json")
    flags = ["-f", "rdf", "-w", "rdf_format=turtle"]
    assert convert_main([*flags, str(source), str(turtle)]) == 0
    assert _read_back(turtle, "rdf", **TURTLE) == primer_example()
    # The extension is unknown, so -i names the format and -r its syntax. The
    # default RDF reader refuses RDF/XML, so only the option makes it read.
    xml = tmp_path / "doc.dat"
    _write(xml, "rdf", rdf_format="xml")
    flags = ["-i", "rdf", str(xml), str(back)]
    assert convert_main(flags) == 2
    assert convert_main(["-r", "rdf_format=xml", *flags]) == 0
    assert _read_back(back, "json") == primer_example()


@pytest.mark.parametrize(
    ("text", "profile", "plain_code", "code", "errors"),
    [(BARE_MENTION, "strict", 0, 2, 1), (UNKNOWN_STATEMENT, "lenient", 2, 0, 0)],
    ids=["strict", "lenient"],
)
def test_reader_options_reach_the_reader(
    tmp_path, capsys, text, profile, plain_code, code, errors
) -> None:
    source = tmp_path / "doc.provn"
    target = tmp_path / "out.json"
    source.write_text(text)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Without the option the default profile gives the other result.
        assert convert_main([str(source), str(target)]) == plain_code
        capsys.readouterr()
        flags = ["-r", f"profile={profile}"]
        assert convert_main([*flags, str(source), str(target)]) == code
    assert capsys.readouterr().err.count("prov-convert: error: ") == errors


@pytest.mark.parametrize(
    ("flags", "target_name", "message", "extras"),
    [
        pytest.param(
            ["-f", "provn", "-w", "wdith=1"],
            "out.provn",
            _no_option("writer", "provn", "wdith", "strict, width"),
            (),
            id="provn-writer",
        ),
        pytest.param(
            ["-f", "svg", "-w", "labels=true"],
            "out.svg",
            _no_option(
                "writer",
                "svg",
                "labels",
                "direction, show_element_attributes, show_nary, "
                "show_relation_attributes, use_labels",
            ),
            (),
            id="graphviz-writer",
        ),
        pytest.param(
            ["-w", "width=1"],
            "out.ttl",
            _no_option("writer", "rdf", "width", "rdf_format"),
            ("rdflib",),
            id="the-extensions-format",
        ),
        pytest.param(
            ["-i", "json", "-r", "profile=x"],
            "out.dat",
            _no_option("reader", "json", "profile", "none"),
            (),
            id="json-reader",
        ),
        pytest.param(
            ["-i", "json", "-r", "object_hook=x"],
            "out.dat",
            _no_option("reader", "json", "object_hook", "none"),
            (),
            id="json-callable",
        ),
        pytest.param(
            ["-i", "rdf", "-r", "relation_mapper=x"],
            "out.dat",
            _no_option("reader", "rdf", "relation_mapper", "rdf_format"),
            ("rdflib",),
            id="rdf-mapper",
        ),
        pytest.param(
            ["-f", "bogus", "-w", "x=1"],
            "out.dat",
            'No serializer available for the format "bogus"',
            (),
            id="unknown-format",
        ),
        pytest.param(
            ["-i", "xml", "-r", "profile=x"],
            "out.dat",
            _no_option("reader", "xml", "profile", "none"),
            ("lxml",),
            id="xml-reader",
        ),
    ],
)
def test_an_undeclared_option_exits_2_before_the_output_is_opened(
    infile, tmp_path, capsys, flags, target_name, message, extras
) -> None:
    for extra in extras:
        pytest.importorskip(extra)
    target = tmp_path / target_name
    target.write_bytes(b"keep")
    assert convert_main([*flags, str(infile), str(target)]) == 2
    assert capsys.readouterr().err == f"prov-convert: error: {message}\n"
    assert target.read_bytes() == b"keep"


@pytest.mark.parametrize(
    ("name", "code", "stderr"),
    [
        ("profile", 0, ""),
        (
            "porfile",
            2,
            "prov-convert: error: "
            + _no_option("reader", "auto", "porfile", "profile, rdf_format")
            + "\n",
        ),
    ],
    ids=["member", "typo"],
)
def test_a_reader_option_is_checked_against_every_reader_under_detection(
    monkeypatch, capsys, name, code, stderr
) -> None:
    pytest.importorskip("rdflib")
    monkeypatch.setattr(
        sys, "stdin", STDIN_STREAMS["pipe-bytes"](UNKNOWN_STATEMENT.encode())
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert convert_main(["-r", f"{name}=lenient"]) == code
    assert capsys.readouterr().err == stderr


# Colour.

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _converted(infile, monkeypatch, flags, *, outfile=None, tty=False, env=None) -> str:
    """Run ``prov-convert`` and return what it wrote to ``outfile`` or standard output.

    Standard output reports ``tty`` from ``isatty``, and ``NO_COLOR`` and
    ``TERM`` are ``env``'s, else unset.
    """
    for name in ("NO_COLOR", "TERM"):
        monkeypatch.delenv(name, raising=False)
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)
    stdout = io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(stdout, "isatty", lambda: tty)
    monkeypatch.setattr(sys, "stdout", stdout)
    paths = [str(infile)] if outfile is None else [str(infile), str(outfile)]
    assert convert_main([*flags, *paths]) == 0
    if outfile is not None:
        return outfile.read_bytes().decode("utf-8")
    return cast(io.BytesIO, stdout.buffer).getvalue().decode("utf-8")


def run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - nosemgrep
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("flags", "name", "coloured"),
    [
        pytest.param(["-f", "provn"], "out.dat", True, id="provn"),
        pytest.param(["-f", "json"], "out.dat", True, id="json"),
        pytest.param(["-f", "jsonld"], "out.dat", True, id="jsonld"),
        pytest.param(["-f", "xml"], "out.dat", True, id="xml"),
        pytest.param(["-f", "dot"], "out.dat", True, id="dot", marks=needs_dot),
        pytest.param(["-f", "rdf"], "out.dat", False, id="rdf-trig"),
        pytest.param(
            ["-f", "rdf", "-w", "rdf_format=turtle"], "out.dat", True, id="rdf-turtle"
        ),
        pytest.param([], "out.ttl", True, id="ttl-extension"),
        pytest.param([], "out.trig", False, id="trig-extension"),
        pytest.param(
            ["-f", "svg", "-w", "use_labels=true"],
            "out.dat",
            False,
            id="svg",
            marks=needs_dot,
        ),
    ],
)
def test_color_always_colours_a_format_that_has_a_lexer(
    infile, tmp_path, monkeypatch, flags, name, coloured
) -> None:
    always = _converted(
        infile, monkeypatch, ["--color", "always", *flags], outfile=tmp_path / name
    )
    assert ("\x1b[" in always) is coloured


@pytest.mark.parametrize(
    "fmt", ["provn", "json", "jsonld", "xml", pytest.param("dot", marks=needs_dot)]
)
def test_color_only_adds_escape_sequences(infile, tmp_path, monkeypatch, fmt) -> None:
    # RDF is left out because its blank nodes differ between two runs.
    outputs = [
        _converted(
            infile,
            monkeypatch,
            ["--color", choice, "-f", fmt],
            outfile=tmp_path / choice,
        )
        for choice in ("always", "never")
    ]
    always, never = outputs
    assert ANSI.sub("", always) == never


def test_color_writes_plain_when_the_output_holds_a_carriage_return(
    tmp_path, monkeypatch
) -> None:
    # Pygments turns a carriage return into a line feed.
    doc = ex_document()
    doc.entity("ex:e1", {"prov:label": "line1\r\nline2\rx"})
    source = tmp_path / "doc.json"
    doc.serialize(str(source), format="json")
    flags = ["-f", "provn"]
    always = _converted(
        source, monkeypatch, ["--color", "always", *flags], outfile=tmp_path / "a.dat"
    )
    assert "\r" in always
    assert "\x1b[" not in always


def test_color_always_writes_text_to_a_text_only_stream(infile, monkeypatch) -> None:
    texts = []
    for choice in ("never", "always"):
        stdout = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stdout)
        flags = ["--color", choice, "-f", "provn", str(infile)]
        assert convert_main(flags) == 0
        texts.append(stdout.getvalue())
    never, always = texts
    assert "\x1b[" in always
    assert ANSI.sub("", always) == never


@pytest.mark.parametrize("error", [ClassNotFound, ImportError])
def test_color_writes_plain_when_the_lexer_cannot_be_fetched(
    infile, tmp_path, monkeypatch, capsys, error
) -> None:
    def fetch(*args, **kwargs) -> NoReturn:
        raise error("no lexer")

    monkeypatch.setattr("pygments.lexers.get_lexer_by_name", fetch)
    flags = ["-f", "provn"]
    always = _converted(
        infile, monkeypatch, ["--color", "always", *flags], outfile=tmp_path / "a.dat"
    )
    never = _converted(
        infile, monkeypatch, ["--color", "never", *flags], outfile=tmp_path / "n.dat"
    )
    assert always == never
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    ("choice", "tty", "env", "to_file", "coloured"),
    [
        pytest.param("auto", True, {}, False, True, id="terminal"),
        pytest.param("auto", True, {"NO_COLOR": ""}, False, True, id="empty-no-color"),
        pytest.param("auto", True, {"NO_COLOR": "1"}, False, False, id="no-color"),
        pytest.param("auto", True, {"TERM": "dumb"}, False, False, id="dumb"),
        pytest.param("auto", True, {}, True, False, id="output-file"),
        pytest.param("auto", False, {}, False, False, id="pipe"),
        pytest.param("never", True, {}, False, False, id="never"),
        pytest.param("always", False, {"NO_COLOR": "1"}, False, True, id="always"),
    ],
)
def test_color_follows_the_flag_the_output_and_the_environment(
    infile, tmp_path, monkeypatch, choice, tty, env, to_file, coloured
) -> None:
    text = _converted(
        infile,
        monkeypatch,
        ["--color", choice, "-f", "provn"],
        outfile=tmp_path / "out.dat" if to_file else None,
        tty=tty,
        env=env,
    )
    assert text.startswith(("document", "\x1b["))
    assert ("\x1b[" in text) is coloured


@pytest.mark.parametrize(
    ("choice", "code", "prefix", "stderr"),
    [
        pytest.param(
            "always",
            2,
            "",
            'prov-convert: error: --color=always needs the optional "pygments" extra; '
            'install "prov[pygments]"\n',
            id="always",
        ),
        pytest.param("auto", 0, "document", "", id="auto"),
    ],
)
def test_color_without_pygments(infile, choice, code, prefix, stderr) -> None:
    # The child is on a terminal with Pygments unimportable. Standard output
    # stays empty under "always" and plain under "auto"; the exit status is
    # main()'s return value.
    result = run_isolated(
        "import io, os, sys\n"
        "sys.modules['pygments'] = None\n"
        "os.environ.pop('NO_COLOR', None)\n"
        "os.environ['TERM'] = 'xterm'\n"
        "from prov.scripts.convert import main\n"
        "out = io.TextIOWrapper(io.BytesIO())\n"
        "out.isatty = lambda: True\n"
        "sys.stdout = out\n"
        f"rc = main(['--color', {choice!r}, '-f', 'provn', {str(infile)!r}])\n"
        "sys.__stdout__.write(out.buffer.getvalue().decode())\n"
        "sys.exit(rc)\n"
    )
    assert result.returncode == code
    assert result.stderr == stderr
    assert bool(result.stdout) == bool(prefix)
    assert result.stdout.startswith(prefix)
    assert "\x1b" not in result.stdout


# prov-compare.


@pytest.fixture
def compare_files(tmp_path):
    json_file = tmp_path / "doc.json"
    xml_file = tmp_path / "doc.xml"
    doc = primer_example()
    doc.serialize(str(json_file), format="json")
    doc.serialize(str(xml_file), format="xml")
    return json_file, xml_file


# argparse.FileType is deprecated from Python 3.14 (#441); the scripts must
# not use it on any interpreter.
@pytest.mark.filterwarnings("error::PendingDeprecationWarning")
@pytest.mark.filterwarnings("error::DeprecationWarning")
def test_equivalent_documents_return_0(compare_files, monkeypatch) -> None:
    json_file, xml_file = compare_files
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-compare", "-f", "json", "-F", "xml", str(json_file), str(xml_file)],
    )
    rc = compare_main()
    assert rc == 0


def test_compare_provn_to_json_returns_0(tmp_path, monkeypatch) -> None:
    provn_file = tmp_path / "doc.provn"
    json_file = tmp_path / "doc.json"
    doc = primer_example()
    doc.serialize(str(provn_file), format="provn")
    doc.serialize(str(json_file), format="json")
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-compare", "-f", "provn", "-F", "json", str(provn_file), str(json_file)],
    )
    rc = compare_main()
    assert rc == 0


def test_different_documents_return_1(compare_files, tmp_path, monkeypatch) -> None:
    json_file, _xml_file = compare_files
    other_file = tmp_path / "other.json"
    w3c_publication_1().serialize(str(other_file), format="json")
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(json_file), str(other_file)])
    rc = compare_main()
    assert rc == 1


def test_bad_format_returns_2_and_writes_one_error_line(compare_files, capsys) -> None:
    json_file, xml_file = compare_files
    rc = compare_main(["-f", "bogus", str(json_file), str(xml_file)])
    assert rc == 2
    assert (
        capsys.readouterr().err
        == 'prov-compare: error: No serializer available for the format "bogus"\n'
    )


def test_missing_file_exits_2(compare_files, tmp_path, monkeypatch) -> None:
    json_file, _xml_file = compare_files
    missing = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(missing), str(json_file)])
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 2


def test_closes_both_files_on_error(compare_files, monkeypatch) -> None:
    json_file, xml_file = compare_files
    captured_sources = []
    original_deserialize = ProvDocument.deserialize

    def spy_deserialize(source=None, content=None, **kwargs):
        captured_sources.append(source)
        if len(captured_sources) == 2:
            raise RuntimeError("boom")
        kwargs.setdefault("format", "json")
        return original_deserialize(source=source, content=content, **kwargs)

    monkeypatch.setattr(ProvDocument, "deserialize", staticmethod(spy_deserialize))
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(json_file), str(xml_file)])
    rc = compare_main()
    assert rc == 2
    assert len(captured_sources) == 2
    for source in captured_sources:
        assert source.closed


def test_compare_one_positional_exits_2(compare_files, monkeypatch) -> None:
    json_file, _xml_file = compare_files
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(json_file)])
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 2


def test_compare_reads_one_file_from_stdin_for_dash(compare_files, monkeypatch) -> None:
    json_file, xml_file = compare_files
    stdin = io.TextIOWrapper(io.BytesIO(json_file.read_bytes()))
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(
        sys, "argv", ["prov-compare", "-f", "json", "-F", "xml", "-", str(xml_file)]
    )
    assert compare_main() == 0
    assert not stdin.buffer.closed


def test_compare_reads_a_text_only_stdin_for_dash(compare_files, monkeypatch) -> None:
    json_file, xml_file = compare_files
    monkeypatch.setattr(sys, "stdin", io.StringIO(json_file.read_text()))
    monkeypatch.setattr(sys, "argv", ["prov-compare", "-F", "xml", "-", str(xml_file)])
    assert compare_main() == 0


def test_compare_two_dashes_exits_2(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prov-compare", "-", "-"])
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 2


@pytest.fixture
def provn_and_xml(tmp_path):
    pytest.importorskip("lxml")
    provn_file = tmp_path / "a.provn"
    xml_file = tmp_path / "b.xml"
    _write(provn_file, "provn")
    _write(xml_file, "xml")
    return provn_file, xml_file


@pytest.mark.parametrize("flags", [[], ["-f", "auto", "-F", "AUTO"]])
def test_compare_detects_formats_from_extensions(provn_and_xml, flags) -> None:
    provn_file, xml_file = provn_and_xml
    assert compare_main([*flags, str(provn_file), str(xml_file)]) == 0


def test_compare_detects_a_document_on_stdin(provn_and_xml, monkeypatch) -> None:
    provn_file, xml_file = provn_and_xml
    stdin = STDIN_STREAMS["pipe-bytes"](provn_file.read_bytes())
    monkeypatch.setattr(sys, "stdin", stdin)
    assert compare_main(["-", str(xml_file)]) == 0


def test_compare_a_flag_replaces_the_extension(provn_and_xml, capsys) -> None:
    provn_file, xml_file = provn_and_xml
    assert compare_main(["-f", "json", str(provn_file), str(xml_file)]) == 2
    assert capsys.readouterr().err.startswith("prov-compare: error: ")


def test_compare_passes_each_file_its_own_reader_options(tmp_path, capsys) -> None:
    pytest.importorskip("rdflib")
    provn_file = tmp_path / "a.provn"
    xml_file = tmp_path / "b.dat"
    provn_file.write_text(UNKNOWN_STATEMENT)
    files = [str(provn_file), str(xml_file)]
    flags = ["-r", "profile=lenient", "-F", "rdf", "-R", "rdf_format=xml"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # The same document as the lenient PROV-N reading, as RDF/XML.
        lenient = ProvDocument.deserialize(
            content=UNKNOWN_STATEMENT, format="provn", profile="lenient"
        )
        lenient.serialize(str(xml_file), format="rdf", rdf_format="xml")
        assert compare_main([*flags, *files]) == 0
        # Dropping either option, or giving it to the other file, fails.
        assert compare_main([*flags[2:], *files]) == 2
        assert compare_main([*flags[:2], "-F", "rdf", *files]) == 2
        swapped = ["-R", "profile=lenient", "-F", "rdf", "-r", "rdf_format=xml"]
        assert compare_main([*swapped, *files]) == 2
    capsys.readouterr()
    # Each name is checked against its own file's format.
    assert compare_main(["-F", "rdf", "-R", "porfile=x", *files]) == 2
    sentence = _no_option("reader", "rdf", "porfile", "rdf_format")
    assert capsys.readouterr().err == f"prov-compare: error: {sentence}\n"
    assert compare_main(["-r", "rdf_format=x", "-F", "rdf", *files]) == 2
    assert (
        "the 'provn' reader accepts no option 'rdf_format'" in capsys.readouterr().err
    )


# Both tools.


@pytest.mark.parametrize("flag", ["-V", "--version"])
@pytest.mark.parametrize(
    ("main", "prog"), [(convert_main, "prov-convert"), (compare_main, "prov-compare")]
)
def test_version_prints_the_package_version(main, prog, flag, monkeypatch) -> None:
    # Files are opened after parsing, so a plain StringIO stdout (no .buffer)
    # must do.
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    with pytest.raises(SystemExit) as ctx:
        main([flag])
    assert ctx.value.code == 0
    assert stdout.getvalue() == f"{prog} {prov.__version__}\n"


# Each entry is followed by the next flag, which ends it.
READER_NAMES = "accepted names: provn: profile; rdf: rdf_format"
WRITER_NAMES = (
    "accepted names: json: ensure_ascii, indent, sort_keys; "
    "jsonld: context, ensure_ascii, indent, sort_keys; provn: strict, width; "
    "rdf: rdf_format; xml: force_types; Graphviz formats: direction, "
    "show_element_attributes, show_nary, show_relation_attributes, use_labels"
)


@pytest.mark.parametrize(
    ("main", "entries"),
    [(convert_main, [WRITER_NAMES, READER_NAMES]), (compare_main, [READER_NAMES])],
    ids=["convert", "compare"],
)
def test_help_is_one_description_with_examples(main, entries) -> None:
    # --help formats usage to sys.stdout, which may have no .buffer attribute
    # (e.g. under contextlib.redirect_stdout(io.StringIO())).
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit) as ctx:
        main(["--help"])
    assert ctx.value.code == 0
    out = buf.getvalue()
    assert out.startswith("usage:")
    assert "Copyright" not in out
    assert "USAGE" not in out
    assert "examples:" in out
    flat = " ".join(out.split())
    assert _format_names() in flat
    assert ("Graphviz" in out) == (main is convert_main)
    for entry in entries:
        assert f"{entry} -" in flat


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("tool", "build_parser"),
    [("convert", convert_build_parser), ("compare", compare_build_parser)],
)
def test_reference_page_names_every_flag_and_positional(tool, build_parser) -> None:
    page = REPO_ROOT / "docs" / "reference" / f"prov-{tool}.md"
    if not page.is_file():
        pytest.skip(f"{page.name} only exists in a source checkout")
    text = page.read_text()
    names = [
        name
        for action in build_parser()._actions
        for name in (action.option_strings or [action.dest])
    ]
    missing = [name for name in names if f"`{name}`" not in text]
    assert not missing, f"{page.name} does not show {missing} as inline code"


def raise_keyboard_interrupt(*args, **kwargs) -> NoReturn:
    raise KeyboardInterrupt


@pytest.mark.parametrize(
    ("main", "patched", "args"),
    [
        (convert_main, "prov.scripts.convert.convert_file", ["-f", "xml"]),
        (compare_main, "prov.scripts.compare._read", []),
        (convert_main, "prov.scripts.convert._build_parser", []),
        (compare_main, "prov.scripts.compare._build_parser", []),
    ],
    ids=["convert", "compare", "convert-start-up", "compare-start-up"],
)
def test_keyboard_interrupt_returns_130_silently(
    main, patched, args, infile, tmp_path, monkeypatch, capsys
) -> None:
    # prov-compare opens both paths, so the second one must exist.
    second = tmp_path / "second.json"
    second.write_bytes(infile.read_bytes())
    monkeypatch.setattr(patched, raise_keyboard_interrupt)
    assert main([*args, str(infile), str(second)]) == 130
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    ("exc", "message"),
    [
        pytest.param(Exception(), "Exception", id="empty"),
        pytest.param(ValueError("a\n\n  b \n"), "a b", id="blank-line"),
    ],
)
def test_run_prints_one_error_line(exc, message, capsys) -> None:
    def action() -> NoReturn:
        raise exc

    assert _run("x", action) == 2
    assert capsys.readouterr().err == f"x: error: {message}\n"


def test_a_missing_extra_prints_the_install_hint(
    infile, tmp_path, monkeypatch, capsys
) -> None:
    # A minimal install registers no "xml" serializer; the library's hint
    # reaches stderr whole from both tools.
    Registry.load_serializers()
    assert Registry.serializers is not None
    minimal = {k: v for k, v in Registry.serializers.items() if k != "xml"}
    monkeypatch.setattr(Registry, "serializers", minimal)
    hint = (
        'Serializer for the "xml" format requires the "xml" extra; '
        'install it with: pip install "prov[xml]"'
    )
    assert convert_main(["-f", "xml", str(infile), str(tmp_path / "out.dat")]) == 2
    assert capsys.readouterr().err == f"prov-convert: error: {hint}\n"
    assert compare_main(["-F", "xml", str(infile), str(infile)]) == 2
    assert capsys.readouterr().err == f"prov-compare: error: {hint}\n"

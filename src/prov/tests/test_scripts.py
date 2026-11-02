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
import io
import shutil
import sys
import warnings
from typing import NoReturn, cast

import pytest

import prov
from prov.model import ProvDocument
from prov.scripts import _format_names, _pair, _run, _typed
from prov.scripts.compare import main as compare_main
from prov.scripts.convert import (
    _GRAPHVIZ_OPTIONS,
    GRAPHVIZ_SUPPORTED_FORMATS,
    CLIError,
    _output_format,
    convert_file,
    main as convert_main,
)
from prov.serializers import Registry
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
HAS_DOT = shutil.which("dot") is not None
# The strict profile refuses it and the lenient profile skips it with a warning.
UNKNOWN_STATEMENT = (
    "document\nprefix ex <http://example.org/>\nentity(ex:e2)\nfoo(ex:e1)\nendDocument"
)


def _write(path, fmt: str, **options) -> None:
    primer_example().serialize(str(path), format=fmt, **options)


def _read_back(path, fmt: str, **options) -> ProvDocument:
    return ProvDocument.deserialize(str(path), format=fmt, **options)


def _options_document() -> ProvDocument:
    """A document on which every writer option changes the output."""
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
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


@pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not installed"
)
def test_convert_to_dot(infile, tmp_path, monkeypatch) -> None:
    outfile = tmp_path / "doc.dot"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "dot", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


@pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not installed"
)
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
    ("flags", "fmt", "options"),
    [
        pytest.param(
            ["-f", "provn", "-w", "width=none"], "provn", {"width": None}, id="none"
        ),
        pytest.param(
            ["-f", "provn", "-w", "width=40", "-w", "width=none"],
            "provn",
            {"width": None},
            id="last-wins",
        ),
        pytest.param(
            ["-f", "provn", "-w", "strict=true"], "provn", {"strict": True}, id="strict"
        ),
        pytest.param(
            ["-f", "json", "-w", "indent=2"], "json", {"indent": 2}, id="json"
        ),
        pytest.param(
            ["-f", "jsonld", "-w", "context=embed"],
            "jsonld",
            {"context": "embed"},
            id="jsonld",
        ),
        pytest.param(
            ["-f", "xml", "-w", "force_types=true"],
            "xml",
            {"force_types": True},
            id="xml",
        ),
        pytest.param(
            ["-f", "dot", "-w", "use_labels=true"],
            "dot",
            {"use_labels": True},
            id="dot",
            marks=pytest.mark.skipif(not HAS_DOT, reason="graphviz not installed"),
        ),
    ],
)
def test_writer_options_reach_the_writer(tmp_path, flags, fmt, options) -> None:
    if fmt in EXTRAS:
        pytest.importorskip(EXTRAS[fmt])
    source = tmp_path / "doc.json"
    target = tmp_path / "out.dat"
    _options_document().serialize(str(source), format="json")
    doc = _read_back(source, "json")
    with warnings.catch_warnings():
        # The strict profile warns for each statement it drops.
        warnings.simplefilter("ignore")
        assert convert_main([*flags, str(source), str(target)]) == 0
        assert target.read_bytes() == _written(doc, fmt, **options)
        # The option changes the output, so the row pins more than the default.
        assert target.read_bytes() != _written(doc, fmt)


def test_the_wide_provn_statement_is_one_line_under_width_none(tmp_path) -> None:
    source = tmp_path / "doc.json"
    target = tmp_path / "out.provn"
    _options_document().serialize(str(source), format="json")
    assert convert_main(["-w", "width=none", str(source), str(target)]) == 0
    assert any(
        "e1" in line and "ex:note" in line for line in target.read_text().splitlines()
    )
    assert convert_main([str(source), str(target)]) == 0
    assert not any(
        "e1" in line and "ex:note" in line for line in target.read_text().splitlines()
    )


def test_rdf_format_names_the_turtle_writer_and_reader(tmp_path) -> None:
    pytest.importorskip("rdflib")
    source = tmp_path / "doc.json"
    turtle = tmp_path / "out.dat"
    back = tmp_path / "back.json"
    _write(source, "json")
    flags = ["-f", "rdf", "-w", "rdf_format=turtle"]
    assert convert_main([*flags, str(source), str(turtle)]) == 0
    assert _read_back(turtle, "rdf", **TURTLE) == primer_example()
    # The extension is unknown, so -i names the format and -r its syntax.
    flags = ["-i", "rdf", "-r", "rdf_format=turtle"]
    assert convert_main([*flags, str(turtle), str(back)]) == 0
    assert _read_back(back, "json") == primer_example()


@pytest.mark.parametrize(("profile", "code"), [("strict", 2), ("lenient", 0)])
def test_reader_options_reach_the_reader(tmp_path, capsys, profile, code) -> None:
    source = tmp_path / "doc.provn"
    target = tmp_path / "out.json"
    source.write_text(UNKNOWN_STATEMENT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert (
            convert_main(["-r", f"profile={profile}", str(source), str(target)]) == code
        )
    assert capsys.readouterr().err.startswith("prov-convert: error: ") == bool(code)


JSON_READER_NAMES = (
    "object_hook, object_pairs_hook, parse_constant, parse_float, parse_int"
)
RDF_READER_NAMES = "predicate_mapper, rdf_format, relation_mapper"


def _writer_sentence(fmt: str, name: str, accepted: str) -> str:
    return f"the {fmt!r} writer accepts no option {name!r}; it accepts: {accepted}"


def _reader_sentence(fmt: str, name: str, accepted: str) -> str:
    return f"the {fmt!r} reader accepts no option {name!r}; it accepts: {accepted}"


@pytest.mark.parametrize(
    ("flags", "target_name", "message", "extras"),
    [
        pytest.param(
            ["-f", "provn", "-w", "wdith=1"],
            "out.provn",
            _writer_sentence("provn", "wdith", "strict, width"),
            (),
            id="provn-writer",
        ),
        pytest.param(
            ["-f", "svg", "-w", "labels=true"],
            "out.svg",
            _writer_sentence(
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
            _writer_sentence("rdf", "width", "rdf_format"),
            ("rdflib",),
            id="the-extensions-format",
        ),
        pytest.param(
            ["-i", "json", "-r", "profile=x"],
            "out.dat",
            _reader_sentence("json", "profile", JSON_READER_NAMES),
            (),
            id="json-reader",
        ),
        pytest.param(
            ["-i", "xml", "-r", "profile=x"],
            "out.dat",
            _reader_sentence("xml", "profile", "none"),
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


def test_an_unavailable_format_keeps_the_librarys_error(
    infile, tmp_path, capsys
) -> None:
    target = tmp_path / "out.dat"
    assert convert_main(["-f", "bogus", "-w", "x=1", str(infile), str(target)]) == 2
    assert capsys.readouterr().err == (
        'prov-convert: error: No serializer available for the format "bogus"\n'
    )


@pytest.mark.parametrize(
    ("name", "code"), [("profile", 0), ("porfile", 2)], ids=["member", "typo"]
)
def test_a_reader_option_is_checked_against_every_reader_under_detection(
    monkeypatch, capsys, name, code
) -> None:
    pytest.importorskip("rdflib")
    monkeypatch.setattr(
        sys, "stdin", STDIN_STREAMS["pipe-bytes"](UNKNOWN_STATEMENT.encode())
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert convert_main(["-r", f"{name}=lenient"]) == code
    err = capsys.readouterr().err
    if code:
        union = f"{JSON_READER_NAMES}, predicate_mapper, profile, rdf_format, relation_mapper"
        sentence = _reader_sentence("auto", name, union)
        assert err == f"prov-convert: error: {sentence}\n"
    else:
        assert err == ""


def test_a_reader_rejects_a_value_it_cannot_use(infile, tmp_path, capsys) -> None:
    flags = ["-i", "json", "-r", "object_hook=x"]
    assert convert_main([*flags, str(infile), str(tmp_path / "out.json")]) == 2
    err = capsys.readouterr().err
    assert err == "prov-convert: error: 'str' object is not callable\n"


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
    turtle_file = tmp_path / "b.dat"
    _write(provn_file, "provn")
    _write(turtle_file, "rdf", **TURTLE)
    files = [str(provn_file), str(turtle_file)]
    flags = ["-r", "profile=lenient", "-F", "rdf", "-R", "rdf_format=turtle"]
    assert compare_main([*flags, *files]) == 0
    # Each name is checked against its own file's format.
    assert compare_main(["-F", "rdf", "-R", "porfile=x", *files]) == 2
    sentence = _reader_sentence("rdf", "porfile", RDF_READER_NAMES)
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


@pytest.mark.parametrize("main", [convert_main, compare_main])
def test_help_is_one_description_with_examples(main) -> None:
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
    # Every declared name of every format is listed; a format with none is not.
    assert Registry.serializers is not None
    for fmt, cls in Registry.serializers.items():
        declared = [cls.deserialize_options]
        if main is convert_main:
            declared.append(cls.serialize_options)
        for names in filter(None, declared):
            assert f"{fmt}: {', '.join(sorted(names))}" in flat
    if main is convert_main:
        assert f"Graphviz formats: {', '.join(sorted(_GRAPHVIZ_OPTIONS))}" in flat


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

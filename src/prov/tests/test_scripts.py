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
from typing import NoReturn

import pytest

import prov
from prov.model import ProvDocument
from prov.scripts.compare import main as compare_main
from prov.scripts.convert import (
    GRAPHVIZ_SUPPORTED_FORMATS,
    CLIError,
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
        == 'prov-convert: error: Output format "bogus" is not supported.\n'
    )


def test_convert_file_raises_cli_error_for_unsupported_format(infile, tmp_path) -> None:
    # Exercise convert_file() directly for the CLIError branch: the message
    # carries no prefix.
    assert "bogus" not in GRAPHVIZ_SUPPORTED_FORMATS
    with (
        open(infile) as in_stream,
        open(tmp_path / "doc.bogus", "wb") as out_stream,
        pytest.raises(CLIError) as ctx,
    ):
        convert_file(in_stream, out_stream, "bogus")
    assert str(ctx.value) == 'Output format "bogus" is not supported.'
    assert ctx.value.msg == 'Output format "bogus" is not supported.'


def test_convert_missing_input_file_exits_2(infile, tmp_path, monkeypatch) -> None:
    # A path that cannot be opened is reported through parser.error(),
    # which exits 2; that SystemExit propagates out of main() rather than
    # being caught by the `except Exception` handler.
    missing = tmp_path / "does-not-exist.json"
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(missing), str(outfile)]
    )
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 2


def test_convert_version_exits_0_without_stdout_buffer(monkeypatch) -> None:
    # Files are opened after parsing, so --version never needs
    # sys.stdout.buffer; a plain StringIO stdout must do.
    monkeypatch.setattr(sys, "argv", ["prov-convert", "--version"])
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 0


def raise_keyboard_interrupt(*args, **kwargs) -> NoReturn:
    raise KeyboardInterrupt


@pytest.mark.parametrize(
    ("main", "patched", "args"),
    [
        (convert_main, "prov.scripts.convert.convert_file", ["-f", "xml"]),
        (compare_main, "prov.scripts.compare._read", []),
    ],
    ids=["convert", "compare"],
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
    assert "nope" in capsys.readouterr().err


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


def test_convert_help_under_redirected_stdout(monkeypatch) -> None:
    # --help formats usage to sys.stdout; the old sys.stdout.buffer default
    # broke when stdout was something without a .buffer attribute (e.g.
    # contextlib.redirect_stdout(io.StringIO())).
    monkeypatch.setattr(sys, "argv", ["prov-convert", "--help"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 0
    assert buf.getvalue().startswith("usage:")


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


def test_version_exits_0(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prov-compare", "--version"])
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 0


def test_closes_both_files_on_error(compare_files, monkeypatch) -> None:
    json_file, xml_file = compare_files
    captured_sources = []
    original_deserialize = ProvDocument.deserialize

    def spy_deserialize(source=None, content=None, format="json", **kwargs):
        captured_sources.append(source)
        if len(captured_sources) == 2:
            raise RuntimeError("boom")
        return original_deserialize(
            source=source, content=content, format=format, **kwargs
        )

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
    monkeypatch.setattr(
        sys, "argv", ["prov-compare", "-f", "json", "-F", "xml", "-", str(xml_file)]
    )
    assert compare_main() == 0


def test_compare_two_dashes_exits_2(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prov-compare", "-", "-"])
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 2


@pytest.mark.parametrize(
    ("main", "prog"), [(convert_main, "prov-convert"), (compare_main, "prov-compare")]
)
def test_version_prints_the_package_version(main, prog, capsys) -> None:
    with pytest.raises(SystemExit) as ctx:
        main(["-V"])
    assert ctx.value.code == 0
    assert capsys.readouterr().out == f"{prog} {prov.__version__}\n"


@pytest.mark.parametrize("main", [convert_main, compare_main])
def test_help_is_one_description_with_examples(main, capsys) -> None:
    with pytest.raises(SystemExit) as ctx:
        main(["--help"])
    assert ctx.value.code == 0
    out = capsys.readouterr().out
    assert "Copyright" not in out
    assert "USAGE" not in out
    assert "examples:" in out
    assert Registry.serializers is not None
    for name in Registry.serializers:
        assert name in out
    assert ("Graphviz" in out) == (main is convert_main)

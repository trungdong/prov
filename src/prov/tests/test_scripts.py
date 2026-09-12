"""In-process coverage tests for the ``prov-convert`` / ``prov-compare``
console scripts (``src/prov/scripts/convert.py`` and ``compare.py``).

``test_cli_smoke.py`` runs these scripts in a subprocess, which exercises the
end-to-end console-script wiring but contributes nothing to coverage
measurement. This module calls ``main()`` (and, for ``convert``,
``convert_file()``) directly in-process so the bulk of both modules is
actually measured, while leaving the smoke test untouched.

Quirk worth flagging: ``main(argv)`` *extends* ``sys.argv`` rather than
replacing it (see ``if argv is None: argv = sys.argv else: sys.argv.extend
(argv)``). So the pattern used throughout is to patch ``sys.argv`` to the
full desired argv (program name included) and then call ``main()`` with no
argument, rather than passing ``argv=[...]`` to ``main()``.
"""

import contextlib
import io
import shutil
import sys
import warnings

import pytest

from prov.model import ProvDocument
from prov.scripts.compare import main as compare_main
from prov.scripts.convert import (
    GRAPHVIZ_SUPPORTED_FORMATS,
    CLIError,
    convert_file,
    main as convert_main,
)
from prov.tests.examples import primer_example, w3c_publication_1


@pytest.fixture
def infile(tmp_path):
    path = tmp_path / "doc.json"
    primer_example().serialize(str(path), format="json")
    return path


def test_convert_to_xml(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_format_is_case_insensitive(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "XML", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_explicit_argv_extends_sys_argv(infile, tmp_path, monkeypatch):
    # Pin the documented quirk: main(argv) *extends* sys.argv rather than
    # replacing it, and argparse then reads the combined sys.argv. A
    # future "fix" that silently changes this to replacement should trip
    # this test so the behaviour change is a deliberate (3.0) decision.
    outfile = tmp_path / "doc.xml"
    argv = ["-f", "xml", str(infile), str(outfile)]
    monkeypatch.setattr(sys, "argv", ["prov-convert"])
    rc = convert_main(argv)
    assert sys.argv == ["prov-convert", *argv]
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_to_provn(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.provn"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "provn", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    content = outfile.read_text(encoding="utf-8")
    assert content
    # Sanity-check this really went through get_provn(), not a serializer:
    # PROV-N documents open/close with these keywords.
    assert content.startswith("document")
    assert "endDocument" in content


@pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not installed"
)
def test_convert_to_dot(infile, tmp_path, monkeypatch):
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
def test_convert_to_rendered_graphviz_format(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.svg"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "svg", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0
    assert outfile.stat().st_size > 0


def test_convert_unsupported_format_returns_2_and_writes_stderr(
    infile, tmp_path, monkeypatch
):
    outfile = tmp_path / "doc.bogus"
    stderr = io.StringIO()
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "bogus", str(infile), str(outfile)]
    )
    monkeypatch.setattr(sys, "stderr", stderr)
    rc = convert_main()
    assert rc == 2
    assert 'E: Output format "bogus" is not supported.' in stderr.getvalue()


def test_convert_file_raises_cli_error_for_unsupported_format(infile, tmp_path):
    # Exercise convert_file() directly for the CLIError branch and its
    # __str__ (the "E: ..." prefix).
    assert "bogus" not in GRAPHVIZ_SUPPORTED_FORMATS
    with (
        open(infile) as in_stream,
        open(tmp_path / "doc.bogus", "wb") as out_stream,
        pytest.raises(CLIError) as ctx,
    ):
        convert_file(in_stream, out_stream, "bogus")
    assert str(ctx.value) == 'E: Output format "bogus" is not supported.'


def test_convert_missing_input_file_exits_2(infile, tmp_path, monkeypatch):
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


def test_convert_version_exits_0_without_stdout_buffer(monkeypatch):
    # Files are opened after parsing, so --version never needs
    # sys.stdout.buffer; a plain StringIO stdout must do.
    monkeypatch.setattr(sys, "argv", ["prov-convert", "--version"])
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 0


def test_convert_returns_0_on_keyboard_interrupt(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.xml"

    def raise_keyboard_interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("prov.scripts.convert.convert_file", raise_keyboard_interrupt)
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    rc = convert_main()
    assert rc == 0


def test_convert_closes_files_even_when_conversion_fails(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.xml"
    captured = {}

    def spy_convert_file(in_stream, out_stream, output_format, input_format="json"):
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


def test_convert_from_provn(provn_infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-convert", "-i", "provn", "-f", "json", str(provn_infile), str(outfile)],
    )
    assert convert_main() == 0
    assert ProvDocument.deserialize(str(outfile), format="json") == primer_example()


def test_convert_from_xml(tmp_path, monkeypatch):
    pytest.importorskip("lxml")
    infile = tmp_path / "doc.xml"
    primer_example().serialize(str(infile), format="xml")
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-i", "xml", str(infile), str(outfile)]
    )
    assert convert_main() == 0
    assert ProvDocument.deserialize(str(outfile), format="json") == primer_example()


def test_convert_unknown_input_format_exits_2(infile, tmp_path, monkeypatch, capsys):
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-i", "nope", str(infile), str(outfile)]
    )
    assert convert_main() == 2
    assert "nope" in capsys.readouterr().err


def test_convert_reads_provn_from_stdin(provn_infile, tmp_path, monkeypatch):
    outfile = tmp_path / "doc.json"
    monkeypatch.setattr(sys, "argv", ["prov-convert", "-i", "provn", "-f", "json"])
    monkeypatch.setattr(
        sys, "stdin", io.TextIOWrapper(io.BytesIO(provn_infile.read_bytes()))
    )
    with outfile.open("wb") as out:
        monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(out))
        assert convert_main() == 0
    assert ProvDocument.deserialize(str(outfile), format="json") == primer_example()


def test_convert_help_under_redirected_stdout(monkeypatch):
    # --help formats usage to sys.stdout; the old sys.stdout.buffer default
    # broke when stdout was something without a .buffer attribute (e.g.
    # contextlib.redirect_stdout(io.StringIO())).
    monkeypatch.setattr(sys, "argv", ["prov-convert", "--help"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 0
    assert buf.getvalue().startswith("usage:")


def test_convert_works_with_stdin_set_to_none(infile, tmp_path, monkeypatch):
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


def test_convert_leaves_standard_streams_open(provn_infile, monkeypatch):
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


def test_convert_unwritable_output_path_exits_2(infile, tmp_path, monkeypatch):
    outfile = tmp_path / "no-such-dir" / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        convert_main()
    assert ctx.value.code == 2


def test_convert_raises_no_pending_deprecation_warning(infile, tmp_path, monkeypatch):
    # argparse.FileType is deprecated from Python 3.14 (#441); the scripts
    # must not use it on any interpreter.
    outfile = tmp_path / "doc.xml"
    monkeypatch.setattr(
        sys, "argv", ["prov-convert", "-f", "xml", str(infile), str(outfile)]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", PendingDeprecationWarning)
        warnings.simplefilter("error", DeprecationWarning)
        assert convert_main() == 0


@pytest.fixture
def compare_files(tmp_path):
    json_file = tmp_path / "doc.json"
    xml_file = tmp_path / "doc.xml"
    doc = primer_example()
    doc.serialize(str(json_file), format="json")
    doc.serialize(str(xml_file), format="xml")
    return json_file, xml_file


def test_equivalent_documents_return_0(compare_files, monkeypatch):
    json_file, xml_file = compare_files
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-compare", "-f", "json", "-F", "xml", str(json_file), str(xml_file)],
    )
    rc = compare_main()
    assert rc == 0


def test_compare_provn_to_json_returns_0(tmp_path, monkeypatch):
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


def test_different_documents_return_1(compare_files, tmp_path, monkeypatch):
    json_file, _xml_file = compare_files
    other_file = tmp_path / "other.json"
    w3c_publication_1().serialize(str(other_file), format="json")
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(json_file), str(other_file)])
    rc = compare_main()
    assert rc == 1


def test_bad_format_returns_2_and_writes_stderr(compare_files, monkeypatch):
    json_file, xml_file = compare_files
    stderr = io.StringIO()
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-compare", "-f", "bogus", str(json_file), str(xml_file)],
    )
    monkeypatch.setattr(sys, "stderr", stderr)
    rc = compare_main()
    assert rc == 2
    # Unlike convert.py's unsupported-format case, this failure comes
    # straight out of the serializer registry (no CLIError wrapping), so
    # there is no "E: " prefix -- just the program name and message.
    assert 'No serializer available for the format "bogus"' in stderr.getvalue()


def test_missing_file_exits_2(compare_files, tmp_path, monkeypatch):
    json_file, _xml_file = compare_files
    missing = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(missing), str(json_file)])
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 2


def test_version_exits_0(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prov-compare", "--version"])
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 0


def test_closes_both_files_on_error(compare_files, monkeypatch):
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


def test_compare_one_positional_exits_2(compare_files, monkeypatch):
    json_file, _xml_file = compare_files
    monkeypatch.setattr(sys, "argv", ["prov-compare", str(json_file)])
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as ctx:
        compare_main()
    assert ctx.value.code == 2


def test_compare_raises_no_pending_deprecation_warning(compare_files, monkeypatch):
    json_file, xml_file = compare_files
    monkeypatch.setattr(
        sys,
        "argv",
        ["prov-compare", "-f", "json", "-F", "xml", str(json_file), str(xml_file)],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", PendingDeprecationWarning)
        warnings.simplefilter("error", DeprecationWarning)
        assert compare_main() == 0

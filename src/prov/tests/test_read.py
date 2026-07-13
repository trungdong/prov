"""Exercises prov.read(), the documented convenience entry point that wraps
ProvDocument.deserialize() with lazy format auto-detection."""

import io
import json
import logging
import pathlib
import warnings
from unittest import mock

import pytest

import prov
from prov.serializers import DoNotExist
from prov.serializers.provjson import ProvJSONSerializer
from prov.serializers.provn import ProvNSerializer
from prov.serializers.provrdf import ProvRDFSerializer
from prov.serializers.provxml import ProvXMLSerializer
from prov.tests.examples import primer_example


@pytest.fixture
def document():
    return primer_example()


def _write(document, tmp_path, fmt, filename, **kwargs):
    path = tmp_path / filename
    document.serialize(destination=str(path), format=fmt, **kwargs)
    return path


# -- explicit format= for each serializer ---------------------------------


def test_read_explicit_json_format(document, tmp_path):
    path = _write(document, tmp_path, "json", "doc.json")
    result = prov.read(str(path), format="json")
    assert result == document


def test_read_explicit_xml_format(document, tmp_path):
    path = _write(document, tmp_path, "xml", "doc.xml")
    result = prov.read(str(path), format="xml")
    assert result == document


def test_read_explicit_rdf_format(document, tmp_path):
    # Default rdf_format is "trig" on both the write and read sides.
    path = _write(document, tmp_path, "rdf", "doc.rdf")
    result = prov.read(str(path), format="rdf")
    assert result == document


def test_read_explicit_format_is_lowercased(document, tmp_path):
    path = _write(document, tmp_path, "json", "doc-upper.json")
    result = prov.read(str(path), format="JSON")
    assert result == document


# -- source can be a str path, a PathLike, or a file object ---------------


def test_read_accepts_pathlib_path(document, tmp_path):
    path = _write(document, tmp_path, "json", "doc-path.json")
    result = prov.read(pathlib.Path(path), format="json")
    assert result == document


def test_read_accepts_file_object(document, tmp_path):
    path = _write(document, tmp_path, "json", "doc-fileobj.json")
    with open(path) as f:
        result = prov.read(f, format="json")
    assert result == document


# -- format=None auto-detection -------------------------------------------


def test_read_auto_detects_json(document, tmp_path):
    path = _write(document, tmp_path, "json", "auto.json")
    result = prov.read(str(path))
    assert result == document


def test_read_auto_detects_rdf(document, tmp_path):
    # rdf is attempted (as trig, the default) right after json, so a
    # trig-serialized document round trips through auto-detection.
    path = _write(document, tmp_path, "rdf", "auto.rdf")
    result = prov.read(str(path))
    assert result == document


def test_read_auto_detects_xml(document, tmp_path):
    # #239: the rdf candidate raises rdflib's BadSyntax (a SyntaxError) on
    # XML input; read() must treat any candidate failure as "try the next
    # format" so the xml deserializer is reached.
    path = _write(document, tmp_path, "xml", "auto.xml")
    result = prov.read(str(path))
    assert result == document


def test_read_unknown_format_propagates_do_not_exist(document, tmp_path):
    path = _write(document, tmp_path, "json", "doc-unknown-fmt.json")
    with pytest.raises(DoNotExist):
        prov.read(str(path), format="nonexistent")


def test_read_auto_detect_swallows_any_deserializer_error():
    # Since #239, ANY exception from a candidate deserializer means "not
    # this format"; when every candidate fails, read() raises its own
    # TypeError rather than leaking the last candidate's error.
    def boom(self, stream, **kwargs):
        raise RuntimeError("arbitrary deserializer failure")

    with (
        mock.patch.object(ProvJSONSerializer, "deserialize", boom),
        mock.patch.object(ProvRDFSerializer, "deserialize", boom),
        mock.patch.object(ProvNSerializer, "deserialize", boom),
        mock.patch.object(ProvXMLSerializer, "deserialize", boom),
        pytest.raises(TypeError) as ctx,
    ):
        prov.read(io.StringIO("garbage"))
    assert "specify the format" in str(ctx.value)


# -- raw-content strings/bytes (not a file path) ----------------------------


def test_read_accepts_raw_content_string_with_explicit_format(document):
    content = document.serialize(format="json")
    assert prov.read(content, format="json") == document


def test_read_auto_detects_raw_content_string(document):
    content = document.serialize(format="json")
    assert prov.read(content) == document


def test_read_accepts_raw_content_bytes_with_explicit_format(document):
    content = document.serialize(format="json").encode()
    assert prov.read(content, format="json") == document


def test_read_auto_detects_raw_content_bytes(document):
    content = document.serialize(format="json").encode()
    assert prov.read(content) == document


def test_read_accepts_bytes_file_path(document, tmp_path):
    # A bytes source naming an existing file is a path, not raw content.
    path = _write(document, tmp_path, "json", "doc-bytes-path.json")
    assert prov.read(str(path).encode(), format="json") == document


# -- empty / unparseable input raises TypeError -----------------------------


def test_read_empty_file_raises_type_error(tmp_path):
    # #239: rdflib parses empty (trig) input successfully, which used to
    # yield a silent empty document; an empty parse is not a detection.
    path = tmp_path / "empty.json"
    path.touch()
    with pytest.raises(TypeError):
        prov.read(str(path))


def test_read_empty_string_raises_type_error():
    with pytest.raises(TypeError):
        prov.read("")


def test_read_garbage_content_raises_type_error():
    # A str that is not an existing file path is treated as raw content.
    with pytest.raises(TypeError):
        prov.read("no/such/file.json")


# -- Fix A: seekable streams are rewound between auto-detect attempts ------


def test_read_auto_detects_xml_from_seekable_stringio(document):
    xml_str = document.serialize(format="xml")
    stream = io.StringIO(xml_str)
    result = prov.read(stream)
    assert result == document


def test_read_auto_detects_xml_from_seekable_bytesio(document):
    xml_bytes = document.serialize(format="xml").encode()
    stream = io.BytesIO(xml_bytes)
    result = prov.read(stream)
    assert result == document


def test_read_auto_detects_json_from_seekable_stream_still_works(document):
    # Regression guard: json is the first candidate tried, so the rewind
    # added for other formats must not break the already-working case.
    json_str = document.serialize(format="json")
    stream = io.StringIO(json_str)
    result = prov.read(stream)
    assert result == document


# -- Fix B: rdflib logger noise is suppressed during auto-detect only ------


def test_read_auto_detect_xml_produces_no_rdflib_term_warnings(
    document, tmp_path, caplog
):
    path = _write(document, tmp_path, "xml", "auto-quiet.xml")
    with caplog.at_level(logging.WARNING, logger="rdflib.term"):
        result = prov.read(str(path))
    assert result == document
    assert [r for r in caplog.records if r.name == "rdflib.term"] == []


# -- Fix C: diagnostic hint when a nonexistent-path string is parsed as ----
# -- raw content -------------------------------------------------------------


def test_read_explicit_format_nonexistent_path_warns_raw_content_hint():
    with (
        pytest.raises(json.JSONDecodeError),
        pytest.warns(UserWarning, match="raw content"),
    ):
        prov.read("no/such/file.json", format="json")


def test_read_explicit_format_valid_raw_content_emits_no_warning(document):
    content = document.serialize(format="json")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert prov.read(content, format="json") == document


def test_read_auto_detect_nonexistent_path_type_error_has_both_hints():
    with pytest.raises(TypeError) as ctx:
        prov.read("no/such/file.json")
    message = str(ctx.value)
    assert "specify the format" in message
    assert "raw content" in message

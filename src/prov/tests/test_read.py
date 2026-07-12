"""Exercises prov.read(), the documented convenience entry point that wraps
ProvDocument.deserialize() with lazy format auto-detection."""

import io
import pathlib
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


# -- raw-content strings (not a file path) ---------------------------------


def test_read_accepts_raw_content_string_with_explicit_format(document):
    content = document.serialize(format="json")
    assert prov.read(content, format="json") == document


def test_read_auto_detects_raw_content_string(document):
    content = document.serialize(format="json")
    assert prov.read(content) == document


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

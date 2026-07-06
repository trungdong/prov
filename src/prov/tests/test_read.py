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


def test_read_auto_detect_of_xml_hits_uncaught_rdf_syntax_error(document, tmp_path):
    """
    Documents actual current behaviour rather than the aspirational
    "xml auto-detects too": Registry order is json, rdf, provn, xml
    (see prov.serializers.Registry.load_serializers). For an XML
    document, the json attempt fails cleanly (caught ValueError), but
    the *rdf* candidate -- deserialized with its default "trig" format
    -- raises rdflib's BadSyntax, a SyntaxError. read() only catches
    (TypeError, ValueError, AttributeError, KeyError), so this
    propagates and auto-detection never reaches the real xml
    serializer. This is a known limitation (see
    docs/test-gap-checklist.md, T13 item on the auto-detection
    exception whitelist), not something fixed by this test-only change.
    """
    path = _write(document, tmp_path, "xml", "auto.xml")
    with pytest.raises(SyntaxError):
        prov.read(str(path))


def test_read_unknown_format_propagates_do_not_exist(document, tmp_path):
    path = _write(document, tmp_path, "json", "doc-unknown-fmt.json")
    with pytest.raises(DoNotExist):
        prov.read(str(path), format="nonexistent")


def test_read_raises_type_error_when_all_serializers_fail_to_parse():
    """
    The final "exhausted all serializers" branch of read() can only be
    reached if every registered deserializer raises one of the caught
    exception types. In practice ProvNSerializer.deserialize() always
    raises NotImplementedError (uncaught by read()) regardless of
    content, and the rdf/xml parsers raise SyntaxError subclasses on
    garbage, so that branch is unreachable via any real file. (The real
    json deserializer already fails with a caught JSONDecodeError; it
    is mocked here too only for uniformity.) Mock the deserializers to
    make the branch reachable and pin the resulting error message.
    """

    def boom(self, stream, **kwargs):
        raise ValueError("simulated parse failure")

    with (
        mock.patch.object(ProvJSONSerializer, "deserialize", boom),
        mock.patch.object(ProvRDFSerializer, "deserialize", boom),
        mock.patch.object(ProvNSerializer, "deserialize", boom),
        mock.patch.object(ProvXMLSerializer, "deserialize", boom),
        pytest.raises(TypeError) as ctx,
    ):
        prov.read(io.StringIO("garbage"))
    assert "specify the format" in str(ctx.value)


def test_read_auto_detect_only_swallows_the_documented_exception_types():
    """
    Pins the intended behaviour of the auto-detection loop (checklist
    item under prov/__init__.py, T13): only (TypeError, ValueError,
    AttributeError, KeyError) from a candidate deserializer are caught
    and treated as "try the next format"; anything else must propagate
    immediately rather than being swallowed.
    """

    def boom(self, stream, **kwargs):
        raise RuntimeError("not one of the caught types")

    with (
        mock.patch.object(ProvJSONSerializer, "deserialize", boom),
        pytest.raises(RuntimeError),
    ):
        prov.read(io.StringIO("garbage"))

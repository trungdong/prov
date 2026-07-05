import io
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import prov
from prov.serializers import DoNotExist
from prov.serializers.provjson import ProvJSONSerializer
from prov.serializers.provn import ProvNSerializer
from prov.serializers.provrdf import ProvRDFSerializer
from prov.serializers.provxml import ProvXMLSerializer
from prov.tests.examples import primer_example


class TestRead(unittest.TestCase):
    """Exercises prov.read(), the documented convenience entry point that
    wraps ProvDocument.deserialize() with lazy format auto-detection."""

    def setUp(self):
        self.document = primer_example()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write(self, fmt, filename, **kwargs):
        path = os.path.join(self.tmpdir.name, filename)
        self.document.serialize(destination=path, format=fmt, **kwargs)
        return path

    # -- explicit format= for each serializer -----------------------------

    def test_read_explicit_json_format(self):
        path = self._write("json", "doc.json")
        result = prov.read(path, format="json")
        self.assertEqual(result, self.document)

    def test_read_explicit_xml_format(self):
        path = self._write("xml", "doc.xml")
        result = prov.read(path, format="xml")
        self.assertEqual(result, self.document)

    def test_read_explicit_rdf_format(self):
        # Default rdf_format is "trig" on both the write and read sides.
        path = self._write("rdf", "doc.rdf")
        result = prov.read(path, format="rdf")
        self.assertEqual(result, self.document)

    def test_read_explicit_format_is_lowercased(self):
        path = self._write("json", "doc-upper.json")
        result = prov.read(path, format="JSON")
        self.assertEqual(result, self.document)

    # -- source can be a str path, a PathLike, or a file object -----------

    def test_read_accepts_pathlib_path(self):
        path = self._write("json", "doc-path.json")
        result = prov.read(pathlib.Path(path), format="json")
        self.assertEqual(result, self.document)

    def test_read_accepts_file_object(self):
        path = self._write("json", "doc-fileobj.json")
        with open(path) as f:
            result = prov.read(f, format="json")
        self.assertEqual(result, self.document)

    # -- format=None auto-detection ----------------------------------------

    def test_read_auto_detects_json(self):
        path = self._write("json", "auto.json")
        result = prov.read(path)
        self.assertEqual(result, self.document)

    def test_read_auto_detects_rdf(self):
        # rdf is attempted (as trig, the default) right after json, so a
        # trig-serialized document round trips through auto-detection.
        path = self._write("rdf", "auto.rdf")
        result = prov.read(path)
        self.assertEqual(result, self.document)

    def test_read_auto_detect_of_xml_hits_uncaught_rdf_syntax_error(self):
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
        path = self._write("xml", "auto.xml")
        with self.assertRaises(SyntaxError):
            prov.read(path)

    def test_read_unknown_format_propagates_do_not_exist(self):
        path = self._write("json", "doc-unknown-fmt.json")
        with self.assertRaises(DoNotExist):
            prov.read(path, format="nonexistent")

    def test_read_raises_type_error_when_all_serializers_fail_to_parse(self):
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
            self.assertRaises(TypeError) as ctx,
        ):
            prov.read(io.StringIO("garbage"))
        self.assertIn("specify the format", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

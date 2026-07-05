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

import io
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

from prov.model import ProvDocument
from prov.scripts.compare import main as compare_main
from prov.scripts.convert import (
    GRAPHVIZ_SUPPORTED_FORMATS,
    CLIError,
    convert_file,
    main as convert_main,
)
from prov.tests.examples import primer_example, w3c_publication_1


class TestConvertMain(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.infile = os.path.join(self.tmpdir.name, "doc.json")
        primer_example().serialize(self.infile, format="json")

    def _outfile(self, name):
        return os.path.join(self.tmpdir.name, name)

    def test_convert_to_xml(self):
        outfile = self._outfile("doc.xml")
        with unittest.mock.patch.object(
            sys, "argv", ["prov-convert", "-f", "xml", self.infile, outfile]
        ):
            rc = convert_main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.getsize(outfile) > 0)

    def test_convert_format_is_case_insensitive(self):
        outfile = self._outfile("doc.xml")
        with unittest.mock.patch.object(
            sys, "argv", ["prov-convert", "-f", "XML", self.infile, outfile]
        ):
            rc = convert_main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.getsize(outfile) > 0)

    def test_convert_explicit_argv_extends_sys_argv(self):
        # Pin the documented quirk: main(argv) *extends* sys.argv rather than
        # replacing it, and argparse then reads the combined sys.argv. A
        # future "fix" that silently changes this to replacement should trip
        # this test so the behaviour change is a deliberate (3.0) decision.
        outfile = self._outfile("doc.xml")
        argv = ["-f", "xml", self.infile, outfile]
        with unittest.mock.patch.object(sys, "argv", ["prov-convert"]):
            rc = convert_main(argv)
            self.assertEqual(sys.argv, ["prov-convert", *argv])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.getsize(outfile) > 0)

    def test_convert_to_provn(self):
        outfile = self._outfile("doc.provn")
        with unittest.mock.patch.object(
            sys, "argv", ["prov-convert", "-f", "provn", self.infile, outfile]
        ):
            rc = convert_main()
        self.assertEqual(rc, 0)
        with open(outfile, encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(content)
        # Sanity-check this really went through get_provn(), not a serializer:
        # PROV-N documents open/close with these keywords.
        self.assertTrue(content.startswith("document"))
        self.assertIn("endDocument", content)

    @unittest.skipUnless(shutil.which("dot"), "graphviz 'dot' binary not installed")
    def test_convert_to_dot(self):
        outfile = self._outfile("doc.dot")
        with unittest.mock.patch.object(
            sys, "argv", ["prov-convert", "-f", "dot", self.infile, outfile]
        ):
            rc = convert_main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.getsize(outfile) > 0)

    @unittest.skipUnless(shutil.which("dot"), "graphviz 'dot' binary not installed")
    def test_convert_to_rendered_graphviz_format(self):
        outfile = self._outfile("doc.svg")
        with unittest.mock.patch.object(
            sys, "argv", ["prov-convert", "-f", "svg", self.infile, outfile]
        ):
            rc = convert_main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.getsize(outfile) > 0)

    def test_convert_unsupported_format_returns_2_and_writes_stderr(self):
        outfile = self._outfile("doc.bogus")
        stderr = io.StringIO()
        with (
            unittest.mock.patch.object(
                sys, "argv", ["prov-convert", "-f", "bogus", self.infile, outfile]
            ),
            unittest.mock.patch.object(sys, "stderr", stderr),
        ):
            rc = convert_main()
        self.assertEqual(rc, 2)
        self.assertIn('E: Output format "bogus" is not supported.', stderr.getvalue())

    def test_convert_file_raises_cli_error_for_unsupported_format(self):
        # Exercise convert_file() directly for the CLIError branch and its
        # __str__ (the "E: ..." prefix).
        self.assertNotIn("bogus", GRAPHVIZ_SUPPORTED_FORMATS)
        with (
            open(self.infile) as infile,
            open(self._outfile("doc.bogus"), "wb") as outfile,
            self.assertRaises(CLIError) as ctx,
        ):
            convert_file(infile, outfile, "bogus")
        self.assertEqual(
            str(ctx.exception), 'E: Output format "bogus" is not supported.'
        )

    def test_convert_missing_input_file_exits_2(self):
        # FileType('r') fails to open a nonexistent path *inside argparse*,
        # which calls parser.error() -> sys.exit(2); that SystemExit
        # propagates straight out of main() without being caught by the
        # `except Exception` handler.
        missing = self._outfile("does-not-exist.json")
        outfile = self._outfile("doc.xml")
        stderr = io.StringIO()
        with (
            unittest.mock.patch.object(
                sys, "argv", ["prov-convert", "-f", "xml", missing, outfile]
            ),
            unittest.mock.patch.object(sys, "stderr", stderr),
            self.assertRaises(SystemExit) as ctx,
        ):
            convert_main()
        self.assertEqual(ctx.exception.code, 2)

    def test_convert_version_exits_0(self):
        with (
            unittest.mock.patch.object(sys, "argv", ["prov-convert", "--version"]),
            unittest.mock.patch.object(sys, "stdout", io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            convert_main()
        self.assertEqual(ctx.exception.code, 0)

    def test_convert_returns_0_on_keyboard_interrupt(self):
        outfile = self._outfile("doc.xml")
        with (
            unittest.mock.patch(
                "prov.scripts.convert.convert_file", side_effect=KeyboardInterrupt
            ),
            unittest.mock.patch.object(
                sys, "argv", ["prov-convert", "-f", "xml", self.infile, outfile]
            ),
        ):
            rc = convert_main()
        self.assertEqual(rc, 0)

    def test_convert_closes_files_even_when_conversion_fails(self):
        outfile = self._outfile("doc.xml")
        captured = {}

        def spy_convert_file(infile, outfile, output_format):
            captured["infile"] = infile
            captured["outfile"] = outfile
            raise RuntimeError("boom")

        with (
            unittest.mock.patch(
                "prov.scripts.convert.convert_file", side_effect=spy_convert_file
            ),
            unittest.mock.patch.object(
                sys, "argv", ["prov-convert", "-f", "xml", self.infile, outfile]
            ),
        ):
            rc = convert_main()
        self.assertEqual(rc, 2)
        self.assertTrue(captured["infile"].closed)
        self.assertTrue(captured["outfile"].closed)


class TestCompareMain(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.json_file = os.path.join(self.tmpdir.name, "doc.json")
        self.xml_file = os.path.join(self.tmpdir.name, "doc.xml")
        doc = primer_example()
        doc.serialize(self.json_file, format="json")
        doc.serialize(self.xml_file, format="xml")

    def test_equivalent_documents_return_0(self):
        with unittest.mock.patch.object(
            sys,
            "argv",
            [
                "prov-compare",
                "-f",
                "json",
                "-F",
                "xml",
                self.json_file,
                self.xml_file,
            ],
        ):
            rc = compare_main()
        self.assertEqual(rc, 0)

    def test_different_documents_return_1(self):
        other_file = os.path.join(self.tmpdir.name, "other.json")
        w3c_publication_1().serialize(other_file, format="json")
        with unittest.mock.patch.object(
            sys, "argv", ["prov-compare", self.json_file, other_file]
        ):
            rc = compare_main()
        self.assertEqual(rc, 1)

    def test_bad_format_returns_2_and_writes_stderr(self):
        stderr = io.StringIO()
        with (
            unittest.mock.patch.object(
                sys,
                "argv",
                ["prov-compare", "-f", "bogus", self.json_file, self.xml_file],
            ),
            unittest.mock.patch.object(sys, "stderr", stderr),
        ):
            rc = compare_main()
        self.assertEqual(rc, 2)
        # Unlike convert.py's unsupported-format case, this failure comes
        # straight out of the serializer registry (no CLIError wrapping), so
        # there is no "E: " prefix -- just the program name and message.
        self.assertIn(
            'No serializer available for the format "bogus"', stderr.getvalue()
        )

    def test_missing_file_exits_2(self):
        missing = os.path.join(self.tmpdir.name, "does-not-exist.json")
        with (
            unittest.mock.patch.object(
                sys, "argv", ["prov-compare", missing, self.json_file]
            ),
            unittest.mock.patch.object(sys, "stderr", io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            compare_main()
        self.assertEqual(ctx.exception.code, 2)

    def test_version_exits_0(self):
        with (
            unittest.mock.patch.object(sys, "argv", ["prov-compare", "--version"]),
            unittest.mock.patch.object(sys, "stdout", io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            compare_main()
        self.assertEqual(ctx.exception.code, 0)

    def test_closes_both_files_on_error(self):
        captured_sources = []
        original_deserialize = ProvDocument.deserialize

        def spy_deserialize(source=None, content=None, format="json", **kwargs):
            captured_sources.append(source)
            if len(captured_sources) == 2:
                raise RuntimeError("boom")
            return original_deserialize(
                source=source, content=content, format=format, **kwargs
            )

        with (
            unittest.mock.patch.object(
                ProvDocument, "deserialize", staticmethod(spy_deserialize)
            ),
            unittest.mock.patch.object(
                sys, "argv", ["prov-compare", self.json_file, self.xml_file]
            ),
        ):
            rc = compare_main()
        self.assertEqual(rc, 2)
        self.assertEqual(len(captured_sources), 2)
        for source in captured_sources:
            self.assertTrue(source.closed)


if __name__ == "__main__":
    unittest.main()

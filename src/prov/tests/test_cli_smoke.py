"""Smoke tests for the prov-convert / prov-compare console scripts.

Downstream packagers ship these entry points; they must keep working
throughout the 2.x line. Full CLI coverage is a Phase 2 task.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from prov.tests.examples import primer_example


def _console_script(name):
    # Prefer the script installed alongside the interpreter running this
    # test (the uv env under test) over a same-named script that might
    # appear earlier on PATH (e.g. a stray global `pip install prov` on a
    # contributor's machine).
    candidate = os.path.join(os.path.dirname(sys.executable), name)
    return candidate if os.path.exists(candidate) else shutil.which(name)


class TestCLISmoke(unittest.TestCase):
    def test_entry_point_functions_exist(self):
        from prov.scripts.compare import main as compare_main
        from prov.scripts.convert import main as convert_main

        self.assertTrue(callable(convert_main))
        self.assertTrue(callable(compare_main))

    def test_console_scripts_installed(self):
        for script in ("prov-convert", "prov-compare"):
            self.assertIsNotNone(_console_script(script), f"{script} not installed")

    def test_prov_convert_and_compare_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            infile = os.path.join(tmp, "doc.json")
            outfile = os.path.join(tmp, "doc.xml")
            primer_example().serialize(infile, format="json")

            # prov-convert positional args are: infile outfile; -f/--format
            # selects the *output* format (default json).
            result = subprocess.run(
                [_console_script("prov-convert"), "-f", "xml", infile, outfile],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(os.path.getsize(outfile) > 0)

            # prov-compare positional args are: file1 file2; -f/--format1 and
            # -F/--format2 select each file's format independently (both
            # default to json). main() returns `doc1 != doc2` as an int
            # (False/0 == equivalent, True/1 == different), which becomes
            # the process exit code via sys.exit(). The JSON document and
            # its XML round trip are semantically equivalent, so we expect
            # exit code 0 here.
            result = subprocess.run(
                [
                    _console_script("prov-compare"),
                    "-f",
                    "json",
                    "-F",
                    "xml",
                    infile,
                    outfile,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

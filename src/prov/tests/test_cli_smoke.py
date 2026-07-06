"""Smoke tests for the prov-convert / prov-compare console scripts.

Downstream packagers ship these entry points; they must keep working
throughout the 2.x line. Full CLI coverage is a Phase 2 task.
"""

import os
import shutil
import subprocess
import sys

from prov.scripts.compare import main as compare_main
from prov.scripts.convert import main as convert_main
from prov.tests.examples import primer_example


def _console_script(name):
    # Prefer the script installed alongside the interpreter running this
    # test (the uv env under test) over a same-named script that might
    # appear earlier on PATH (e.g. a stray global `pip install prov` on a
    # contributor's machine).
    candidate = os.path.join(os.path.dirname(sys.executable), name)
    return candidate if os.path.exists(candidate) else shutil.which(name)


def test_entry_point_functions_exist():
    assert callable(convert_main)
    assert callable(compare_main)


def test_console_scripts_installed():
    for script in ("prov-convert", "prov-compare"):
        assert _console_script(script) is not None, f"{script} not installed"


def test_prov_convert_and_compare_end_to_end(tmp_path):
    infile = tmp_path / "doc.json"
    outfile = tmp_path / "doc.xml"
    primer_example().serialize(str(infile), format="json")

    # prov-convert positional args are: infile outfile; -f/--format
    # selects the *output* format (default json).
    result = subprocess.run(
        [_console_script("prov-convert"), "-f", "xml", str(infile), str(outfile)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert outfile.stat().st_size > 0

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
            str(infile),
            str(outfile),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

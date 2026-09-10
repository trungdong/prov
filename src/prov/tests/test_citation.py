"""Repository metadata files must agree with the package.

These files live at the repository root, not in the package, so the tests
skip when run from an installed wheel.
"""

import json
import re
from pathlib import Path

import pytest

import prov

REPO_ROOT = Path(__file__).resolve().parents[3]
CITATION_FILE = REPO_ROOT / "CITATION.cff"
ZENODO_FILE = REPO_ROOT / ".zenodo.json"

pytestmark = pytest.mark.skipif(
    not CITATION_FILE.is_file(), reason="CITATION.cff only exists in a source checkout"
)


def test_citation_version_matches_package_version():
    match = re.search(
        r'^version:\s*"?([^"\n]+?)"?\s*$', CITATION_FILE.read_text(), re.MULTILINE
    )
    assert match is not None, "CITATION.cff has no version line"
    assert match.group(1) == prov.__version__


def test_zenodo_metadata_names_the_maintainer():
    metadata = json.loads(ZENODO_FILE.read_text())
    assert metadata["license"] == "MIT"
    assert metadata["creators"][0]["orcid"] == "0000-0003-4937-2473"

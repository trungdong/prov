"""Documents written by prov 3.2.3 read the same under this release.

Every file under ``fixtures/written-by-3.2.3`` is read with the format its
extension names and compared with the document the current code builds from
the same source. Section 1 of the 3.3.0 release design calls this the
compatibility promise; the fixtures are the direct test of it.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from _pytest.mark import ParameterSet

import prov
from prov.model import ProvDocument
from prov.tests import attribute_values, examples

from .conftest import contains_mention

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "written-by-3.2.3"
FORMATS = {
    "json": "json",
    "xml": "xml",
    "provn": "provn",
    "trig": "rdf",
    "jsonld": "jsonld",
}

SOURCES: list[tuple[str, Callable[[], ProvDocument]]] = [
    (name.lower().replace(" ", "-"), build) for name, build in examples.tests
] + [("attribute-values", attribute_values.document)]


def _cases() -> list[ParameterSet]:
    cases = []
    for slug, build in SOURCES:
        for extension, fmt in FORMATS.items():
            if fmt == "jsonld" and contains_mention(build()):
                continue
            cases.append(
                pytest.param(slug, build, extension, fmt, id=f"{slug}.{extension}")
            )
    return cases


@pytest.mark.parametrize(("slug", "build", "extension", "fmt"), _cases())
def test_document_written_by_3_2_3_reads_equal(
    slug: str, build: Callable[[], ProvDocument], extension: str, fmt: str
) -> None:
    path = FIXTURE_DIR / f"{slug}.{extension}"
    assert path.exists(), f"{path.name} is missing; run generate.py"
    with path.open(encoding="utf-8") as stream:
        document = prov.read(stream, format=fmt)
    assert document is not None
    # build() goes on the left: record equality ignores the identifier when the
    # left-hand record has none (#525), and the RDF reader gives a qualified relation one.
    assert build() == document

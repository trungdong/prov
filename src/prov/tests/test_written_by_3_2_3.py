"""Documents written by prov 3.2.3 read the same under this release.

Every file under ``fixtures/written-by-3.2.3`` is read with the format its
extension names and compared with the document the current code builds from
the same source. A document prov 3.2.3 wrote reads the same under this
release, and the fixtures test that directly.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import prov
from prov.model import ProvDocument
from prov.tests import attribute_values, examples

from .conftest import contains_mention

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "written-by-3.2.3"
# Maps each format to its file extension. Keep in step with FORMATS in
# fixtures/written-by-3.2.3/generate.py.
FORMATS = {
    "json": "json",
    "xml": "xml",
    "provn": "provn",
    "rdf": "trig",
    "jsonld": "jsonld",
}

SOURCES: list[tuple[str, Callable[[], ProvDocument]]] = [
    (name.lower().replace(" ", "-"), build) for name, build in examples.tests
] + [("attribute-values", attribute_values.document)]


def _cases() -> list[ParameterSet]:
    cases = []
    for slug, build in SOURCES:
        mention = contains_mention(build())
        for fmt, extension in FORMATS.items():
            if fmt == "jsonld" and mention:
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
    assert document == build()

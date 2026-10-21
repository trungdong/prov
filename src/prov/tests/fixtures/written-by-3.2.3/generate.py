"""Write the canonical documents with the prov release this directory names.

Run from the repository root with the published wheel, never the working tree:

    uvx --from "prov[rdf,xml]==3.2.3" \
        python -I src/prov/tests/fixtures/written-by-3.2.3/generate.py

``-I`` keeps the current directory and the user site off ``sys.path``, and the
script refuses to run when prov is imported from inside this repository. The
example and corpus modules are loaded from this checkout by path, so they are
the ones the test compares against; they import only names every 3.x release
has.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import prov
import prov.model

HERE = Path(__file__).resolve().parent
TESTS = HERE.parents[1]
# Maps each format to its file extension. Keep in step with FORMATS in
# test_written_by_3_2_3.py.
FORMATS = {
    "json": "json",
    "xml": "xml",
    "provn": "provn",
    "rdf": "trig",
    "jsonld": "jsonld",
}


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TESTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _contains_mention(document: prov.model.ProvDocument) -> bool:
    """As ``conftest.contains_mention``, which cannot be imported here."""
    records = list(document.get_records())
    for bundle in document.bundles:
        records.extend(bundle.get_records())
    return any(isinstance(record, prov.model.ProvMention) for record in records)


def main() -> None:
    if not prov.__version__.startswith("3.2.3"):
        sys.exit(f"this directory is written by prov 3.2.3, not {prov.__version__}")
    if Path(prov.__file__).resolve().is_relative_to(HERE.parents[4]):
        sys.exit(
            "prov is imported from inside this repository; run this with the"
            " published prov 3.2.3 wheel (see the docstring)"
        )
    examples = _load("examples")
    attribute_values = _load("attribute_values")
    sources = [(_slug(name), build) for name, build in examples.tests]
    sources.append(("attribute-values", attribute_values.document))
    for slug, build in sources:
        document = build()
        for fmt, extension in FORMATS.items():
            if fmt == "jsonld" and _contains_mention(document):
                continue
            (HERE / f"{slug}.{extension}").write_text(
                document.serialize(format=fmt), encoding="utf-8"
            )


if __name__ == "__main__":
    main()

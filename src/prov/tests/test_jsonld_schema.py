"""Validate serializer output against the vendored PROV-JSONLD JSON Schema.

Serializes each of the 8 canonical `examples.tests` documents and validates the
resulting JSON-LD against the vendored `prov-jsonld.schema.json` (Draft-07)
schema (`src/prov/tests/schemas/`, see that directory's README.md for
provenance). Documents containing a `mentionOf` statement have no PROV-JSONLD
representation (the submission defines no `Mention` term); serializing them
must raise `ProvJSONLDException` instead.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from prov.model import ProvDocument, ProvMention  # noqa: E402
from prov.serializers.provjsonld import ProvJSONLDException  # noqa: E402
from prov.tests import examples  # noqa: E402

SCHEMA_PATH = Path(__file__).parent / "schemas" / "prov-jsonld.schema.json"


@pytest.fixture(scope="module")
def prov_jsonld_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def _contains_mention(document: ProvDocument) -> bool:
    records = list(document.get_records())
    for bundle in document.bundles:
        records.extend(bundle.get_records())
    return any(isinstance(r, ProvMention) for r in records)


@pytest.mark.parametrize(
    "make_document",
    [pytest.param(fn, id=name) for name, fn in examples.tests],
)
def test_example_documents_validate_against_prov_jsonld_schema(
    prov_jsonld_validator, make_document
):
    document = make_document()
    if _contains_mention(document):
        with pytest.raises(ProvJSONLDException):
            document.serialize(format="jsonld")
        return
    container = json.loads(document.serialize(format="jsonld"))
    errors = sorted(prov_jsonld_validator.iter_errors(container), key=str)
    assert not errors, "\n".join(str(e) for e in errors)

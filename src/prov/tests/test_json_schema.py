"""Validate PROV-JSON output against the member submission's JSON schema (roadmap step 30).

Serializes each of the 8 canonical `examples.tests` documents and validates the
resulting JSON against the vendored `prov-json.schema.json` (Draft-04) schema
(`src/prov/tests/schemas/`, see that directory's README.md for provenance).

Audit authority: docs/superpowers/specs/2026-07-10-conformance-audit-findings.md
section 3.2.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from prov.tests import examples  # noqa: E402

SCHEMA_PATH = Path(__file__).parent / "schemas" / "prov-json.schema.json"


@pytest.fixture(scope="module")
def prov_json_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


@pytest.mark.parametrize(
    "make_document",
    [pytest.param(fn, id=name) for name, fn in examples.tests],
)
def test_example_documents_validate_against_prov_json_schema(
    prov_json_validator, make_document
):
    container = json.loads(make_document().serialize(format="json"))
    errors = sorted(prov_json_validator.iter_errors(container), key=str)
    assert not errors, "\n".join(str(e) for e in errors)

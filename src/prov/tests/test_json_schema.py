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

# --- Triage: filed defect (strict xfail) -------------------------------------
#
# `encode_json_representation`'s `LITERAL_XSDTYPE_MAP` branch
# (`serializers/provjson.py`) puts the raw Python `int`/`float` value straight
# into the typed-literal `$` property instead of stringifying it, unlike every
# other branch of that function. The submission's prose (SS2.2) and its own
# vendored schema (`definitions.typedLiteral.properties.$`) both require `$`
# to be a JSON string; a bare `int`/`float` attribute value therefore
# serializes as schema-invalid PROV-JSON. `Bundle1`/`Bundle2` hit this via a
# plain-`int` `ex:version` attribute; `datatypes` hits it via `ex:int`,
# `ex:float`, and `ex:long` (the latter also mutates the asserted datatype,
# tracked separately as #235 -- the `$`-typing defect here is independent and
# also affects `ex:int`/`ex:float`, which #235 does not touch). Any fix
# changes serialized output, so it's 3.0 material under the 2.x output freeze.
NON_STRING_DOLLAR_XFAIL = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="#246: PROV-JSON conformance -- plain int/float attribute values "
    "are encoded with a JSON-number '$', not the string '$' required by the "
    "submission's typed-literal schema",
)

_EXAMPLE_MARKS = {
    "Bundle1": NON_STRING_DOLLAR_XFAIL,
    "Bundle2": NON_STRING_DOLLAR_XFAIL,
    "datatypes": NON_STRING_DOLLAR_XFAIL,
}


@pytest.fixture(scope="module")
def prov_json_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


@pytest.mark.parametrize(
    "make_document",
    [
        pytest.param(fn, id=name, marks=_EXAMPLE_MARKS.get(name, ()))
        for name, fn in examples.tests
    ],
)
def test_example_documents_validate_against_prov_json_schema(
    prov_json_validator, make_document
):
    container = json.loads(make_document().serialize(format="json"))
    errors = sorted(prov_json_validator.iter_errors(container), key=str)
    assert not errors, "\n".join(str(e) for e in errors)

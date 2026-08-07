"""Validate serializer output against the vendored PROV-JSONLD JSON Schema.

Serializes each of the 9 canonical `examples.tests` documents and validates the
resulting JSON-LD against the vendored `prov-jsonld.schema.json` (Draft-07)
schema (`src/prov/tests/schemas/`, see that directory's README.md for
provenance). Documents containing a `mentionOf` statement have no PROV-JSONLD
representation (the submission defines no `Mention` term); serializing them
must raise `ProvJSONLDException` instead.

Both `context="url"` (canonical) and `context="embed"` output are exercised,
but only `url`-mode `@context` is validated verbatim against the schema. The
submission schema's `Context` production only permits an array of URL
strings and objects whose *every* value is a plain string; the vendored §5
context embeds nested per-type term definitions (e.g. `"@version": 1.1`,
`"Entity": {"@id": "prov:Entity", "@context": {...}}`), so no embedded
context can ever satisfy that production -- this is a spec conflict, not an
encoder bug (maintainer ruling 2026-08-07). For `embed` mode we therefore
substitute the canonical context URL for the embedded context object before
validating, which still proves everything else in the output (the `@graph`
and the namespace map) is schema-valid; embed mode's JSON-LD validity proper
is covered separately by the pyld expansion tests added in a later task.
"""

import json
from pathlib import Path
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")

from prov.model import ProvDocument  # noqa: E402
from prov.serializers.provjsonld import ProvJSONLDException  # noqa: E402
from prov.tests import examples  # noqa: E402

from .conftest import contains_mention  # noqa: E402

EX_URI = "http://example.org/"

SCHEMA_PATH = Path(__file__).parent / "schemas" / "prov-jsonld.schema.json"

#: The canonical context URL substituted for an embedded context object
#: before schema validation (see module docstring).
CANONICAL_CONTEXT_URL = "https://openprovenance.org/prov-jsonld/context.jsonld"


@pytest.fixture(scope="module")
def prov_jsonld_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def _canonicalize_embedded_context(container: dict[str, Any]) -> dict[str, Any]:
    """Replace an embedded context object with the canonical context URL.

    The submission schema's ``Context`` production cannot describe an
    embedded context (see module docstring), so ``context="embed"`` output
    is made schema-shaped by substituting the URL string a
    ``context="url"`` document would have carried in its place. Everything
    else in ``container`` -- the namespace map and the whole ``@graph`` --
    is left untouched and still fully validated.

    Args:
        container: A decoded PROV-JSONLD document object (as produced by
            ``json.loads(document.serialize(format="jsonld", context="embed"))``).

    Returns:
        ``container`` unchanged, except any dict item of its top-level
        ``@context`` array whose values are themselves dicts (i.e. the
        embedded submission context) is replaced by
        :data:`CANONICAL_CONTEXT_URL`.
    """
    container["@context"] = [
        CANONICAL_CONTEXT_URL
        if isinstance(item, dict) and any(isinstance(v, dict) for v in item.values())
        else item
        for item in container["@context"]
    ]
    return container


@pytest.mark.parametrize(
    "make_document",
    [pytest.param(fn, id=name) for name, fn in examples.tests],
)
@pytest.mark.parametrize("context", ["url", "embed"])
def test_example_documents_validate_against_prov_jsonld_schema(
    prov_jsonld_validator, make_document, context
):
    document = make_document()
    if contains_mention(document):
        with pytest.raises(ProvJSONLDException):
            document.serialize(format="jsonld", context=context)
        return
    container = json.loads(document.serialize(format="jsonld", context=context))
    if context == "embed":
        container = _canonicalize_embedded_context(container)
    errors = sorted(prov_jsonld_validator.iter_errors(container), key=str)
    assert not errors, "\n".join(str(e) for e in errors)


def test_default_namespace_attributes_validate_against_prov_jsonld_schema(
    prov_jsonld_validator,
):
    """A default-namespace attribute must not encode to a bare (unprefixed) key.

    When this test was first written, none of the canonical
    ``examples.tests`` documents set a default namespace, so this gap went
    uncaught: a bare key like ``"mine"`` matches none of the schema's
    ``patternProperties`` (which all require a ``prefix:local`` shape)
    under its ``additionalProperties: false``. ``examples.tests`` has since
    grown a 9th document ("Default namespace attributes") that does set one
    -- covering the gap through the parametrized test above too -- but this
    dedicated test is kept for its sharper failure message and its coverage
    of the reserved-term collision (``"type"``) alongside the plain one.
    """
    document = ProvDocument()
    document.set_default_namespace(EX_URI)
    document.entity("e1", {"mine": "x", "type": "y"})
    container = json.loads(document.serialize(format="jsonld"))
    errors = sorted(prov_jsonld_validator.iter_errors(container), key=str)
    assert not errors, "\n".join(str(e) for e in errors)

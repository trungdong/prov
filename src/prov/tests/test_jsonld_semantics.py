"""Prove PROV-JSONLD output is valid JSON-LD with the intended semantics.

Flattens serializer output with the real ``pyld`` JSON-LD processor,
substituting the vendored context for the remote context URL so the tests
run fully offline: pyld never dereferences
:data:`~prov.serializers.provjsonld.JSONLD_CONTEXT_URL`. This is a semantic
check on top of ``test_jsonld_schema.py``'s syntactic (JSON Schema)
validation -- it proves the emitted terms expand to the *intended* RDF IRIs
and datatypes, not merely that the document is schema-shaped.
"""

import json
from typing import Any

import pytest
from pyld import jsonld

from prov.model import Literal, ProvDocument
from prov.serializers.provjsonld import _load_vendored_context

PROV_NS = "http://www.w3.org/ns/prov#"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"

#: Both ``serialize(format="jsonld", ...)`` context modes; see module docstring.
CONTEXT_MODES = ["url", "embed"]


def _flatten(document: ProvDocument, context: str) -> dict[str, dict[str, Any]]:
    """Serialize ``document``, flatten it with pyld, and index nodes by ``@id``.

    The ``@context`` array's URL entry (``context="url"``) is replaced by
    the vendored context object so pyld resolves every term locally;
    ``context="embed"`` output already carries that same object in its
    place, so the substitution is a no-op for it -- either way pyld never
    makes a network request. JSON-LD *flattening* (rather than plain
    expansion) is used because it is what resolves the submission's
    ``@reverse``-encoded edges (e.g. ``qualifiedGeneration``) onto the
    referring node as an ordinary forward property, which is what the
    assertions below check.

    Args:
        document: Document to serialize and flatten.
        context: ``"url"`` or ``"embed"``, passed through to ``serialize()``.

    Returns:
        The flattened node map, keyed by each node's ``@id`` (relations
        without an explicit identifier surface here under a blank node id
        minted by pyld).
    """
    container = json.loads(document.serialize(format="jsonld", context=context))
    container["@context"] = [
        item if isinstance(item, dict) else _load_vendored_context()
        for item in container["@context"]
    ]
    flattened = jsonld.flatten(container)
    return {node["@id"]: node for node in flattened if "@id" in node}


@pytest.mark.parametrize("context", CONTEXT_MODES)
def test_expansion_entity_and_generation(context):
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")
    doc.activity("ex:a1", "2011-11-16T16:05:00")
    doc.wasGeneratedBy("ex:e1", "ex:a1")

    by_id = _flatten(doc, context)

    e1 = by_id["http://example.org/e1"]
    assert f"{PROV_NS}Entity" in e1["@type"]
    # The Generation statement's "entity" attribute is encoded via the
    # context's @reverse qualifiedGeneration edge; flattening resolves it
    # onto e1 as a forward property pointing at the (blank-node) Generation.
    assert f"{PROV_NS}qualifiedGeneration" in e1

    a1 = by_id["http://example.org/a1"]
    start = a1[f"{PROV_NS}startedAtTime"][0]
    assert start["@type"] == XSD_DATETIME
    assert start["@value"] == "2011-11-16T16:05:00"


@pytest.mark.parametrize("context", CONTEXT_MODES)
def test_expansion_language_tagged_label(context):
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", (("prov:label", Literal("bonjour", langtag="fr")),))

    by_id = _flatten(doc, context)

    label = by_id["http://example.org/e1"][RDFS_LABEL][0]
    assert label["@value"] == "bonjour"
    assert label["@language"] == "fr"

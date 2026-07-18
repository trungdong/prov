"""
Created on Aug 13, 2015

@author: Trung Dong Huynh
"""

import datetime

import pytest

pydot = pytest.importorskip("pydot")

from prov.dot import htlm_link_if_uri, prov_to_dot
from prov.model import ProvDocument
from prov.tests import examples

MIN_SVG_SIZE = 850


@pytest.mark.parametrize(
    "build", [pytest.param(fn, id=name) for name, fn in examples.tests]
)
def test_svg_render(build):
    """One-way output SVG with prov.dot to exercise its code.

    Very naive check of the returned SVG content as we have no way to check
    the graphical content.
    """
    dot = prov_to_dot(build())
    svg_content = dot.create(format="svg", encoding="utf-8")
    assert len(svg_content) > MIN_SVG_SIZE, (
        "The size of the generated SVG content should be greater than "
        f"{MIN_SVG_SIZE} bytes"
    )


# Covers dot.htlm_link_if_uri() (docs/test-gap-checklist.md, T13 item under
# dot.py); not called internally by prov_to_dot() but a module-level function
# usable by external callers.


def test_value_with_uri_becomes_a_link():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    e1 = doc.entity("ex:e1")
    result = htlm_link_if_uri(e1.identifier)
    assert "<a href=" in result
    assert "http://example.org/e1" in result


def test_plain_value_returned_as_str():
    assert htlm_link_if_uri("just a string") == "just a string"


# Covers the direction-validation fallback in prov_to_dot() (docs/test-gap-
# checklist.md, T13 item under dot.py).


def test_invalid_direction_falls_back_to_bt():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    dot = prov_to_dot(doc, direction="SIDEWAYS")
    assert dot.get_rankdir() == "BT"


def test_valid_direction_is_preserved():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    dot = prov_to_dot(doc, direction="LR")
    assert dot.get_rankdir() == "LR"


def test_use_labels_with_explicit_label_differing_from_identifier():
    """Covers the use_labels=True node-rendering branch (docs/test-gap-
    checklist.md, T13 item under dot.py). The label==identifier branch
    (dot.py:281-282) is unreachable via any real record: ProvRecord.label
    always returns a plain `str`, while `.identifier` is a QualifiedName, and
    `str.__eq__`/`QualifiedName.__eq__` can never consider the two equal --
    confirmed empirically; left deferred (see checklist)."""
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", other_attributes={"prov:label": "My Entity"})

    dot = prov_to_dot(doc, use_labels=True)
    svg_content = dot.create(format="svg", encoding="utf-8")
    assert b"My Entity" in svg_content


def test_show_element_attributes_false_skips_annotation():
    """Covers prov_to_dot(show_element_attributes=False) (docs/test-gap-
    checklist.md, T13 item under dot.py); every other test in this module
    leaves it at its True default."""
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", other_attributes={"ex:extra": "value"})

    dot = prov_to_dot(doc, show_element_attributes=False)
    svg_content = dot.create(format="svg", encoding="utf-8")
    assert b"value" not in svg_content


def test_unresolvable_unification_falls_back_to_original_bundle():
    """Covers prov_to_dot()'s ``except ProvException`` fallback when
    ``bundle.unified()`` cannot merge two relations that share an identifier
    but disagree on a formal attribute (the "scruffy" pattern -- see
    test_statements.py's RDF_SCRUFFY_SKIP cases for the same shape).

    Previously exercised incidentally by the pre-migration dot suite
    rendering all 185 shared statement/attribute documents (one of which was
    scruffy); reducing the dot render-smoke to the 8 canonical examples
    (design doc §3) dropped that incidental coverage, so this test restores
    it directly (coverage report -m showed src/prov/dot.py:443-446 newly
    uncovered after the reduction)."""
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity(identifier="ex:e1")
    doc.activity(identifier="ex:a1")
    doc.generation(
        "ex:e1", "ex:a1", identifier="ex:gen1", time=datetime.datetime(2020, 1, 1)
    )
    doc.generation(
        "ex:e1", "ex:a1", identifier="ex:gen1", time=datetime.datetime(2020, 1, 2)
    )

    # bundle.unified() raises ProvException here (conflicting prov:time
    # values for the same identifier); prov_to_dot() must catch it and fall
    # back to rendering the original, non-unified bundle rather than raising.
    dot = prov_to_dot(doc)
    svg_content = dot.create(format="svg", encoding="utf-8")
    assert len(svg_content) > MIN_SVG_SIZE

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


# Covers dot.htlm_link_if_uri() (planning/test-gap-checklist.md, T13 item under
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
    ``bundle.unified()`` raises ``ProvUnificationError`` because two relations
    share an identifier but disagree on a formal attribute (the "scruffy"
    pattern -- see
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

    # bundle.unified() raises ProvUnificationError here (conflicting prov:time
    # values for the same identifier); prov_to_dot() must catch it — the
    # exception is a ProvException — and fall back to rendering the original,
    # non-unified bundle rather than raising.
    dot = prov_to_dot(doc)
    svg_content = dot.create(format="svg", encoding="utf-8")
    assert len(svg_content) > MIN_SVG_SIZE


# Link and label hardening: identifier URIs and labels are document content
# and rendered SVG makes link attributes live.


def _node_with_label_fragment(dot, fragment):
    """The one node whose label contains ``fragment``."""
    matches = [n for n in dot.get_nodes() if fragment in (n.get_label() or "")]
    assert len(matches) == 1, fragment
    return matches[0]


def _assert_javascript_links_dropped(doc):
    """``ex:safe`` keeps its links; the ``js:`` node and annotation get none."""
    dot = prov_to_dot(doc)

    safe = _node_with_label_fragment(dot, "ex:safe")
    assert safe.get("URL") == '"http://example.org/safe"'
    payload = _node_with_label_fragment(dot, "js:payload")
    assert payload.get("URL") is None
    annotation = _node_with_label_fragment(dot, "ex:link")
    assert 'href="http://example.org/link"' in annotation.get_label()
    assert 'href="javascript' not in annotation.get_label()
    assert 'href=" javascript' not in annotation.get_label()


def test_javascript_scheme_identifier_gets_no_url_or_href():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.add_namespace("js", "javascript:")
    doc.entity(
        "ex:safe", other_attributes={"ex:link": doc.valid_qualified_name("js:alert")}
    )
    doc.entity("js:payload", other_attributes={"js:attr": "value"})

    _assert_javascript_links_dropped(doc)


@pytest.mark.parametrize(
    "namespace_uri",
    ["javascript&#58;", "javascript&#x3A;", "javascript&colon;", " javascript:"],
    ids=["decimal-ref", "hex-ref", "named-ref", "leading-space"],
)
def test_encoded_or_padded_javascript_scheme_gets_no_url_or_href(namespace_uri):
    # Graphviz passes character references through to SVG, where the consumer
    # decodes them, so the scheme check must run on the decoded form.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.add_namespace("js", namespace_uri)
    js = doc.valid_qualified_name("js:alert")
    doc.entity("ex:safe", other_attributes={"ex:link": js})
    doc.entity("js:payload")

    _assert_javascript_links_dropped(doc)


def test_bundle_with_javascript_identifier_gets_no_url():
    doc = ProvDocument()
    doc.add_namespace("js", "javascript:")
    bundle = doc.bundle("js:bundle")
    bundle.entity("js:e1")

    dot = prov_to_dot(doc)

    (cluster,) = dot.get_subgraphs()
    assert cluster.get("URL") is None


def test_html_label_special_characters_are_escaped():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", other_attributes={"prov:label": 'A<b> & "c"'})

    dot = prov_to_dot(doc, use_labels=True)
    dot_text = dot.to_string()

    assert "A&lt;b&gt; &amp; &quot;c&quot;" in dot_text
    assert 'A<b> & "c"' not in dot_text
    assert len(dot.create(format="svg")) > 0


def test_quoted_label_escapes_double_quote():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity('ex:e"1')

    dot = prov_to_dot(doc)
    dot_text = dot.to_string()

    assert 'label="ex:e\\"1"' in dot_text
    assert len(dot.create(format="svg")) > 0


def test_unset_endpoint_is_drawn_to_a_blank_node_with_a_warning():
    from prov.model import ProvWarning

    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1")
    document.generation(entity="ex:e1", activity=None)
    with pytest.warns(ProvWarning, match=r"Generation.*prov:activity") as record:
        dot = prov_to_dot(document)
    assert sum(issubclass(w.category, ProvWarning) for w in record) == 1
    assert len(dot.get_edges()) == 1


def test_complete_relation_draws_without_warning():
    import warnings

    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1")
    document.activity("ex:a1")
    document.wasGeneratedBy("ex:e1", "ex:a1")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prov_to_dot(document)

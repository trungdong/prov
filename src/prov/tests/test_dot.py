"""
Created on Aug 13, 2015

@author: Trung Dong Huynh
"""

import datetime
import shutil
import warnings

import pytest

pydot = pytest.importorskip("pydot")

from prov.dot import htlm_link_if_uri, prov_to_dot
from prov.model import Identifier, ProvBundle, ProvDocument, ProvUnificationError
from prov.tests import examples

MIN_SVG_SIZE = 850


@pytest.mark.parametrize(
    "build", [pytest.param(fn, id=name) for name, fn in examples.tests]
)
def test_svg_render(build) -> None:
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


def test_value_with_uri_becomes_a_link() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    e1 = doc.entity("ex:e1")
    result = htlm_link_if_uri(e1.identifier)
    assert "<a href=" in result
    assert "http://example.org/e1" in result


def test_plain_value_returned_as_str() -> None:
    assert htlm_link_if_uri("just a string") == "just a string"


# Covers the direction-validation fallback in prov_to_dot() (docs/test-gap-
# checklist.md, T13 item under dot.py).


def test_invalid_direction_falls_back_to_bt() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    dot = prov_to_dot(doc, direction="SIDEWAYS")
    assert dot.get_rankdir() == "BT"


def test_valid_direction_is_preserved() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    dot = prov_to_dot(doc, direction="LR")
    assert dot.get_rankdir() == "LR"


def test_use_labels_draws_the_label_over_the_identifier_or_the_identifier_once() -> (
    None
):
    """With ``use_labels=True`` an element with a ``prov:label`` shows the label as
    the node text and its identifier beneath; an element without one shows its
    identifier once, as ``use_labels=False`` does."""
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", other_attributes={"prov:label": "My Entity"})
    doc.entity("ex:e2")

    dot = prov_to_dot(doc, use_labels=True)

    labelled = _node_with_label_fragment(dot, "<My Entity<br")
    assert labelled.get_label() == (
        '<My Entity<br /><font color="#333333" point-size="10">ex:e1</font>>'
    )
    unlabelled = _node_with_label_fragment(dot, "ex:e2")
    assert unlabelled.get_label() == '"ex:e2"'
    assert dot.create(format="svg", encoding="utf-8")


def test_show_element_attributes_false_skips_annotation() -> None:
    """Covers prov_to_dot(show_element_attributes=False) (docs/test-gap-
    checklist.md, T13 item under dot.py); every other test in this module
    leaves it at its True default."""
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", other_attributes={"ex:extra": "value"})

    dot = prov_to_dot(doc, show_element_attributes=False)
    svg_content = dot.create(format="svg", encoding="utf-8")
    assert b"value" not in svg_content


def test_unresolvable_unification_falls_back_to_original_bundle() -> None:
    """Covers prov_to_dot()'s ``except ProvException`` fallback when
    ``bundle.unified()`` raises ``ProvUnificationError`` because two relations
    share an identifier but disagree on a formal attribute (the "scruffy"
    pattern -- see
    test_statements.py's test_scruffy_relation for the same shape)."""
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


def _assert_javascript_links_dropped(doc) -> None:
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


def test_javascript_scheme_identifier_gets_no_url_or_href() -> None:
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
def test_encoded_or_padded_javascript_scheme_gets_no_url_or_href(namespace_uri) -> None:
    # Graphviz passes character references through to SVG, where the consumer
    # decodes them, so the scheme check must run on the decoded form.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.add_namespace("js", namespace_uri)
    js = doc.valid_qualified_name("js:alert")
    doc.entity("ex:safe", other_attributes={"ex:link": js})
    doc.entity("js:payload")

    _assert_javascript_links_dropped(doc)


def test_bundle_with_javascript_identifier_gets_no_url() -> None:
    doc = ProvDocument()
    doc.add_namespace("js", "javascript:")
    bundle = doc.bundle("js:bundle")
    bundle.entity("js:e1")

    dot = prov_to_dot(doc)

    (cluster,) = dot.get_subgraphs()
    assert cluster.get("URL") is None


def test_html_label_special_characters_are_escaped() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1", other_attributes={"prov:label": 'A<b> & "c"'})

    dot = prov_to_dot(doc, use_labels=True)
    dot_text = dot.to_string()

    assert "A&lt;b&gt; &amp; &quot;c&quot;" in dot_text
    assert 'A<b> & "c"' not in dot_text
    assert len(dot.create(format="svg")) > 0


def test_quoted_string_escapes_double_quote() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", 'http://example.org/"x/')
    doc.entity("ex:e1")

    dot = prov_to_dot(doc)
    dot_text = dot.to_string()

    assert 'URL="http://example.org/\\"x/e1"' in dot_text
    assert len(dot.create(format="svg")) > 0


def test_sub_minute_utc_offset_attribute_is_rendered_as_utc() -> None:
    # xsd:dateTime allows no seconds in a timezone offset (#341 scope
    # extension): the attribute-annotation label must show the UTC
    # equivalent of a sub-minute offset, not the illegal offset text.
    odd_offset = datetime.timezone(datetime.timedelta(seconds=30))
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.activity(
        "ex:a", startTime=datetime.datetime(2026, 9, 12, 10, 0, 30, tzinfo=odd_offset)
    )

    dot = prov_to_dot(doc)
    dot_text = dot.to_string()

    assert "2026-09-12T10:00:00+00:00" in dot_text
    assert "+00:00:30" not in dot_text


def test_anyuri_value_is_linked_and_shown_as_its_text() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e", {"ex:v": Identifier("http://example.org/v")})
    dot_text = prov_to_dot(doc).to_string()
    assert 'href="http://example.org/v"' in dot_text
    assert "xsd:anyURI" not in dot_text


def test_unset_endpoint_is_drawn_to_a_blank_node_with_a_warning() -> None:
    from prov.model import ProvWarning

    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1")
    document.generation(entity="ex:e1", activity=None)
    with pytest.warns(ProvWarning, match=r"Generation.*prov:activity") as record:
        dot = prov_to_dot(document)
    assert sum(issubclass(w.category, ProvWarning) for w in record) == 1
    assert len(dot.get_edges()) == 1


def test_unset_endpoint_inside_a_bundle_reports_the_prov_to_dot_call_site() -> None:
    from prov.model import ProvWarning

    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    bundle = document.bundle("ex:b")
    bundle.entity("ex:e1")
    bundle.generation(entity="ex:e1", activity=None)
    with pytest.warns(ProvWarning, match=r"Generation.*prov:activity") as record:
        prov_to_dot(document)
    assert len(record) == 1
    # The extra _add_bundle frame nested bundles add must not change which
    # frame the warning is attributed to: still this test module, not a
    # frame inside prov.dot.
    assert record[0].filename == __file__


def test_complete_relation_draws_without_warning() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1")
    document.activity("ex:a1")
    document.wasGeneratedBy("ex:e1", "ex:a1")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prov_to_dot(document)


def _nested_bundle() -> ProvBundle:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    bundle = document.bundle("ex:b")
    bundle.entity("ex:e1")
    return bundle


def _standalone_bundle() -> ProvBundle:
    bundle = ProvBundle()
    bundle.add_namespace("ex", "http://example.org/")
    bundle.entity("ex:e1")
    return bundle


def _bundle_with_conflicting_generations() -> ProvBundle:
    bundle = _nested_bundle()
    bundle.activity("ex:a1")
    for day in (1, 2):
        bundle.generation(
            "ex:e1",
            "ex:a1",
            identifier="ex:gen1",
            time=datetime.datetime(2020, 1, day),
        )
    return bundle


_NEEDS_DOT = pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not available"
)
_NOT_A_DOCUMENT = (
    "Drawing a bundle that is not a document is deprecated and 4.0 draws "
    "documents only; pass the ProvDocument"
)


@pytest.mark.parametrize(
    ("build", "via_plot", "warnings_expected", "needle", "drawn"),
    [
        pytest.param(_nested_bundle, False, 1, 'label="ex:e1"', 1, id="nested-bundle"),
        pytest.param(
            _standalone_bundle, False, 1, 'label="ex:e1"', 1, id="standalone-bundle"
        ),
        pytest.param(
            _bundle_with_conflicting_generations,
            False,
            1,
            "label=wasGeneratedBy",
            2,
            id="non-unifying-bundle",
        ),
        pytest.param(
            _nested_bundle, True, 1, None, None, id="plot-bundle", marks=_NEEDS_DOT
        ),
        pytest.param(
            lambda: _nested_bundle().document,
            True,
            0,
            None,
            None,
            id="plot-document",
            marks=_NEEDS_DOT,
        ),
    ],
)
def test_drawing_a_bundle_that_is_not_a_document_warns_once(
    build, via_plot, warnings_expected, needle, drawn, tmp_path
) -> None:
    """A bundle that is not a document draws with one ``DeprecationWarning``
    attributed to the caller, and a document draws with none."""
    subject = build()
    path = tmp_path / "out.svg"

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        if via_plot:
            subject.plot(filename=path)
        else:
            dot = prov_to_dot(subject)

    assert len(record) == warnings_expected
    if warnings_expected:
        assert issubclass(record[0].category, DeprecationWarning)
        assert _NOT_A_DOCUMENT in str(record[0].message)
        assert record[0].filename == __file__
    if via_plot:
        assert path.stat().st_size > 0
    else:
        assert dot.to_string().count(needle) == drawn


def test_prov_to_dot_draws_a_document_unified_rejects_as_asserted() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.association("ex:a1", agent="ex:ag1", identifier="ex:assoc1")
    document.association("ex:a1", agent="ex:ag1", plan="ex:pl1", identifier="ex:assoc1")
    with pytest.raises(ProvUnificationError, match="an absent prov:plan means none"):
        _ = document.unified()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dot = prov_to_dot(document)
    # Nothing is merged, so both associations are drawn.
    assert dot.to_string().count("label=wasAssociatedWith") == 2

"""
Created on Aug 13, 2015

@author: Trung Dong Huynh
"""

import unittest

# Skipping SVG tests if pydot is not installed
from importlib.util import find_spec

if find_spec("pydot") is not None:
    from prov.dot import htlm_link_if_uri, prov_to_dot
    from prov.model import ProvDocument
    from prov.tests.test_model import AllTestsBase
    from prov.tests.utility import DocumentBaseTestCase

    class SVGDotOutputTest(DocumentBaseTestCase, AllTestsBase):
        """
        One-way output SVG with prov.dot to exercise its code
        """

        MIN_SVG_SIZE = 850

        def do_tests(self, prov_doc, msg=None):
            dot = prov_to_dot(prov_doc)
            svg_content = dot.create(format="svg", encoding="utf-8")
            # Very naive check of the returned SVG content as we have no way to check the graphical content
            self.assertGreater(
                len(svg_content),
                self.MIN_SVG_SIZE,
                "The size of the generated SVG content should be greater than "
                f"{self.MIN_SVG_SIZE} bytes",
            )

    class HtlmLinkIfUriTest(unittest.TestCase):
        """Covers dot.htlm_link_if_uri() (docs/test-gap-checklist.md, T13
        item under dot.py); not called internally by prov_to_dot() but a
        module-level function usable by external callers."""

        def test_value_with_uri_becomes_a_link(self):
            doc = ProvDocument()
            doc.add_namespace("ex", "http://example.org/")
            e1 = doc.entity("ex:e1")
            result = htlm_link_if_uri(e1.identifier)
            self.assertIn("<a href=", result)
            self.assertIn("http://example.org/e1", result)

        def test_plain_value_returned_as_str(self):
            self.assertEqual(htlm_link_if_uri("just a string"), "just a string")

    class ProvToDotDirectionTest(unittest.TestCase):
        """Covers the direction-validation fallback in prov_to_dot()
        (docs/test-gap-checklist.md, T13 item under dot.py)."""

        def setUp(self):
            self.doc = ProvDocument()
            self.doc.add_namespace("ex", "http://example.org/")
            self.doc.entity("ex:e1")

        def test_invalid_direction_falls_back_to_bt(self):
            dot = prov_to_dot(self.doc, direction="SIDEWAYS")
            self.assertEqual(dot.get_rankdir(), "BT")

        def test_valid_direction_is_preserved(self):
            dot = prov_to_dot(self.doc, direction="LR")
            self.assertEqual(dot.get_rankdir(), "LR")

    class ProvToDotUseLabelsTest(unittest.TestCase):
        """Covers the use_labels=True node-rendering branch
        (docs/test-gap-checklist.md, T13 item under dot.py). The
        label==identifier branch (dot.py:281-282) is unreachable via any
        real record: ProvRecord.label always returns a plain `str`, while
        `.identifier` is a QualifiedName, and `str.__eq__`/`QualifiedName.
        __eq__` can never consider the two equal -- confirmed empirically;
        left deferred (see checklist)."""

        def test_use_labels_with_explicit_label_differing_from_identifier(self):
            doc = ProvDocument()
            doc.add_namespace("ex", "http://example.org/")
            doc.entity("ex:e1", other_attributes={"prov:label": "My Entity"})

            dot = prov_to_dot(doc, use_labels=True)
            svg_content = dot.create(format="svg", encoding="utf-8")
            self.assertIn(b"My Entity", svg_content)

    class ProvToDotShowElementAttributesTest(unittest.TestCase):
        """Covers prov_to_dot(show_element_attributes=False) (docs/test-gap-
        checklist.md, T13 item under dot.py); every other test in this
        module leaves it at its True default."""

        def test_show_element_attributes_false_skips_annotation(self):
            doc = ProvDocument()
            doc.add_namespace("ex", "http://example.org/")
            doc.entity("ex:e1", other_attributes={"ex:extra": "value"})

            dot = prov_to_dot(doc, show_element_attributes=False)
            svg_content = dot.create(format="svg", encoding="utf-8")
            self.assertNotIn(b"value", svg_content)


if __name__ == "__main__":
    unittest.main()

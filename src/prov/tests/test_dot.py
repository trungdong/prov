"""
Created on Aug 13, 2015

@author: Trung Dong Huynh
"""
import unittest

# Skipping SVG tests if pydot is not installed
from importlib.util import find_spec

if find_spec("pydot") is not None:

    from prov.dot import prov_to_dot
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
                "The size of the generated SVG content should be greater than %d bytes"
                % self.MIN_SVG_SIZE,
            )


if __name__ == "__main__":
    unittest.main()

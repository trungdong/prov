"""
Created on Aug 13, 2015

@author: Trung Dong Huynh
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest

# Skiping SVG tests if pydot is not installed
from pkgutil import find_loader
if find_loader("pydot") is not None:

    from prov.dot import prov_to_dot
    from prov.tests.test_model import AllTestsBase
    from prov.tests.utility import DocumentBaseTestCase


    class SVGDotOutputTest(DocumentBaseTestCase, AllTestsBase):
        """
        One-way output SVG with prov.dot to exercise its code
        """
        MIN_SVG_SIZE = 900

        def do_tests(self, prov_doc, msg=None):
            dot = prov_to_dot(prov_doc)
            svg_content = dot.create(format="svg")
            # Very naive check of the returned SVG content as we have no way to check the graphical content
            self.assertGreater(
                len(svg_content), self.MIN_SVG_SIZE,
                "The size of the generated SVG content (%d) should be greater than %d bytes" %
                    (len(svg_content), self.MIN_SVG_SIZE)
            )


if __name__ == '__main__':
    unittest.main()

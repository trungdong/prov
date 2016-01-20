"""
Created on Aug 13, 2015

@author: Trung Dong Huynh
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest

from prov.dot import prov_to_dot
from prov.tests.test_model import AllTestsBase
from prov.tests.utility import DocumentBaseTestCase


class SVGDotOutputTest(DocumentBaseTestCase, AllTestsBase):
    """
    One-way output SVG with prov.dot to exercise its code
    """
    def do_tests(self, prov_doc, msg=None):
        dot = prov_to_dot(prov_doc)
        svg_content = dot.create(format="svg")


if __name__ == '__main__':
    unittest.main()

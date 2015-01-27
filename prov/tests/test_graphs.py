from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest
from prov.tests.examples import tests
from prov.graph import prov_to_graph


class ProvGraphTestCase(unittest.TestCase):
    def test_simple_graph_conversion(self):
        for name, doc_func in tests:
            nx_graph = prov_to_graph(doc_func())

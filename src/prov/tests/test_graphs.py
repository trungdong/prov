import unittest

from prov.graph import graph_to_prov, prov_to_graph
from prov.tests.examples import tests


class ProvGraphTestCase(unittest.TestCase):
    def test_simple_graph_conversion(self):
        for name, doc_func in tests:
            prov_org = doc_func()
            g = prov_to_graph(prov_org)
            if prov_org.has_bundles():
                # Cannot round-trip with documents containing bundles, skipping
                continue
            prov_doc = graph_to_prov(g)
            self.assertEqual(
                prov_doc,
                prov_org,
                f"Round trip graph conversion for '{name}' failed.",
            )

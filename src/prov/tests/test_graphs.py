import unittest
from prov.tests.examples import tests
from prov.graph import prov_to_graph, graph_to_prov


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
                "Round trip graph conversion for '{}' failed.".format(name),
            )

import unittest

import networkx as nx

from prov.graph import graph_to_prov, prov_to_graph
from prov.model import ProvActivity, ProvDocument, ProvEntity
from prov.tests.examples import primer_example, tests


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

    def test_round_trip_against_unified_document(self):
        # prov_to_graph() unifies the document internally before building
        # the graph, so a round trip should match the *unified* document,
        # not necessarily the original one record-for-record.
        prov_org = primer_example()
        g = prov_to_graph(prov_org)
        prov_doc = graph_to_prov(g)
        self.assertEqual(prov_doc, prov_org.unified())


class ProvToGraphTestCase(unittest.TestCase):
    def setUp(self):
        self.document = ProvDocument()
        self.document.add_namespace("ex", "http://example.org/")

    def test_relation_with_missing_end_is_skipped(self):
        # A generation record with no activity: the "if qn1 and qn2" guard
        # should skip adding an edge for it since one QualifiedName is None.
        self.document.generation(entity="ex:e1", activity=None)

        g = prov_to_graph(self.document)

        self.assertEqual(list(g.edges()), [])

    def test_relation_endpoints_get_inferred_nodes(self):
        # Neither ex:e2 nor ex:a2 is declared as an element record; both
        # ends should be inferred with the correct PROV class via
        # INFERRED_ELEMENT_CLASS.
        self.document.wasGeneratedBy("ex:e2", "ex:a2")

        g = prov_to_graph(self.document)

        nodes_by_id = {str(n.identifier): n for n in g.nodes()}
        self.assertEqual(len(nodes_by_id), 2)
        self.assertIsInstance(nodes_by_id["ex:e2"], ProvEntity)
        self.assertIsInstance(nodes_by_id["ex:a2"], ProvActivity)
        # Inferred nodes are placeholders, not attached to any bundle.
        self.assertIsNone(nodes_by_id["ex:e2"].bundle)
        self.assertIsNone(nodes_by_id["ex:a2"].bundle)
        self.assertEqual(len(g.edges()), 1)

    def test_relation_with_uninferrable_endpoint_type_is_skipped(self):
        # ProvInfluence's formal attributes (influencee/influencer) are not
        # keys of INFERRED_ELEMENT_CLASS, so a generic influence relation
        # between two undeclared identifiers hits the "except KeyError:
        # continue" branch and is dropped, while later relations are still
        # processed normally.
        self.document.influence("ex:inf1", "ex:inf2")
        self.document.wasGeneratedBy("ex:e2", "ex:a2")

        g = prov_to_graph(self.document)

        self.assertEqual(len(g.nodes()), 2)
        self.assertEqual(len(g.edges()), 1)
        (_, _, edge_data) = next(iter(g.edges(data=True)))
        self.assertEqual(edge_data["relation"].get_type().localpart, "Generation")


class GraphToProvTestCase(unittest.TestCase):
    def test_ignores_non_record_and_bundle_less_nodes(self):
        document = ProvDocument()
        document.add_namespace("ex", "http://example.org/")
        ghost_id = document.valid_qualified_name("ex:ghost")

        g = nx.MultiDiGraph()
        g.add_node("not-a-prov-record")
        # An inferred element, exactly as prov_to_graph() constructs one:
        # bundle=None, so graph_to_prov() must not add it as a record.
        ghost = ProvEntity(None, ghost_id)
        g.add_node(ghost)

        prov_doc = graph_to_prov(g)

        self.assertEqual(list(prov_doc.get_records()), [])

    def test_ignores_edges_without_relation_key(self):
        g = nx.MultiDiGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b")  # no relation= kwarg in the edge data

        prov_doc = graph_to_prov(g)

        self.assertEqual(list(prov_doc.get_records()), [])

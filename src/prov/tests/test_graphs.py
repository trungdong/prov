import warnings

import pytest

nx = pytest.importorskip("networkx", reason="prov.graph requires the graph extra")

from prov.constants import PROV_ATTR_COLLECTION, PROV_ATTR_ENTITY, PROV_MEMBERSHIP
from prov.graph import graph_to_prov, prov_to_graph
from prov.model import (
    ProvActivity,
    ProvDocument,
    ProvEntity,
    ProvRecord,
    ProvRelation,
    ProvUnificationError,
    ProvWarning,
)
from prov.tests.examples import tests


def _is_drawn(record: ProvRecord) -> bool:
    """Whether ``prov_to_graph()`` keeps the record: every element, and a
    relation whose first two formal attributes are both set."""
    return not isinstance(record, ProvRelation) or all(
        value for _, value in record.formal_attributes[:2]
    )


def test_simple_graph_conversion() -> None:
    # The two bundle examples hold generations with no activity, at the top
    # level and inside a bundle, which prov_to_graph() skips with a warning;
    # every other record of the flattened, unified document comes back.
    for name, doc_func in tests:
        prov_org = doc_func()
        expected = {
            record
            for record in prov_org.flattened().unified().get_records()
            if _is_drawn(record)
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ProvWarning)
            prov_doc = graph_to_prov(prov_to_graph(prov_org))
        assert set(prov_doc.get_records()) == expected, (
            f"Round trip graph conversion for '{name}' failed."
        )


@pytest.fixture
def document() -> ProvDocument:
    d = ProvDocument()
    d.add_namespace("ex", "http://example.org/")
    return d


def test_round_trip_of_a_graph_of_inferred_endpoints_under_a_default() -> None:
    document = ProvDocument()
    document.set_default_namespace("http://d.example.org/")
    document.wasDerivedFrom("e2", "e1")

    result = graph_to_prov(prov_to_graph(document))

    assert result.get_default_namespace() == document.get_default_namespace()
    assert result == document.unified()


def test_relation_with_missing_end_is_skipped_with_warning(document) -> None:
    # A generation record with no activity: one endpoint is None, so the
    # relation cannot become an edge. The drop is reported, not silent.
    document.generation(entity="ex:e1", activity=None)

    with pytest.warns(ProvWarning, match="Generation") as record:
        g = prov_to_graph(document)

    assert list(g.edges()) == []
    assert sum(issubclass(w.category, ProvWarning) for w in record) == 1


def test_relation_endpoints_get_inferred_nodes(document) -> None:
    # Neither ex:e2 nor ex:a2 is declared as an element record; both
    # ends should be inferred with the correct PROV class via
    # INFERRED_ELEMENT_CLASS.
    document.wasGeneratedBy("ex:e2", "ex:a2")

    g = prov_to_graph(document)

    nodes_by_id = {str(n.identifier): n for n in g.nodes()}
    assert len(nodes_by_id) == 2
    assert isinstance(nodes_by_id["ex:e2"], ProvEntity)
    assert isinstance(nodes_by_id["ex:a2"], ProvActivity)
    # Inferred nodes are placeholders, not attached to any bundle.
    assert nodes_by_id["ex:e2"].bundle is None
    assert nodes_by_id["ex:a2"].bundle is None
    assert len(g.edges()) == 1


def test_relation_with_uninferrable_endpoint_type_is_skipped_with_warning(
    document,
) -> None:
    # prov:influencee/prov:influencer are the only first-two formal
    # attributes with no INFERRED_ELEMENT_CLASS entry, so an influence
    # between undeclared identifiers cannot get placeholder nodes. It is
    # reported and dropped; later relations are still processed.
    document.influence("ex:inf1", "ex:inf2")
    document.wasGeneratedBy("ex:e2", "ex:a2")

    with pytest.warns(ProvWarning, match="Influence") as record:
        g = prov_to_graph(document)

    assert sum(issubclass(w.category, ProvWarning) for w in record) == 1
    assert len(g.nodes()) == 2
    assert len(g.edges()) == 1
    (_, _, edge_data) = next(iter(g.edges(data=True)))
    assert edge_data["relation"].get_type().localpart == "Generation"


def test_complete_document_emits_no_warning(document) -> None:
    document.entity("ex:e1")
    document.activity("ex:a1")
    document.wasGeneratedBy("ex:e1", "ex:a1")
    document.influence("ex:e1", "ex:a1")

    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        g = prov_to_graph(document)

    assert len(g.edges()) == 2


def test_ignores_non_record_and_bundle_less_nodes() -> None:
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

    assert list(prov_doc.get_records()) == []


def test_ignores_edges_without_relation_key() -> None:
    g = nx.MultiDiGraph()
    g.add_node("a")
    g.add_node("b")
    g.add_edge("a", "b")  # no relation= kwarg in the edge data

    prov_doc = graph_to_prov(g)

    assert list(prov_doc.get_records()) == []


def test_ignores_edges_whose_relation_is_not_a_prov_record() -> None:
    g = nx.MultiDiGraph()
    g.add_node("a")
    g.add_node("b")
    g.add_edge("a", "b", relation="not-a-record")

    prov_doc = graph_to_prov(g)

    assert list(prov_doc.get_records()) == []


def test_equal_memberships_sharing_an_identifier_give_one_edge(
    document: ProvDocument,
) -> None:
    # unified() keeps one of two equal memberships (#548), so one edge is drawn.
    document.entity("ex:c")
    document.entity("ex:e")
    attributes = {PROV_ATTR_COLLECTION: "ex:c", PROV_ATTR_ENTITY: "ex:e"}
    for _ in range(2):
        document.new_record(PROV_MEMBERSHIP, "ex:m", attributes)
    assert prov_to_graph(document).number_of_edges() == 1


@pytest.mark.parametrize(
    "in_bundles",
    [
        pytest.param(False, id="same-scope"),
        # Each bundle unifies on its own; the flattened document does not (N28).
        pytest.param(True, id="two-bundles"),
    ],
)
def test_prov_to_graph_raises_when_unified_does(
    document: ProvDocument, in_bundles: bool
) -> None:
    first, second = (
        (document.bundle("ex:b1"), document.bundle("ex:b2"))
        if in_bundles
        else (document, document)
    )
    first.association("ex:a1", agent="ex:ag1", identifier="ex:assoc1")
    second.association("ex:a1", agent="ex:ag1", plan="ex:pl1", identifier="ex:assoc1")
    with pytest.raises(ProvUnificationError, match="an absent prov:plan means none"):
        _ = prov_to_graph(document)


def test_records_inside_a_bundle_are_nodes_and_edges(document: ProvDocument) -> None:
    # Flattening lifts the bundle's records, so the generation inside the
    # bundle reaches the activity declared at the top level: two declared
    # nodes, no inferred placeholder, one edge.
    document.activity("ex:a1")
    bundle = document.bundle("ex:b")
    bundle.entity("ex:e1")
    bundle.wasGeneratedBy("ex:e1", "ex:a1")

    g = prov_to_graph(document)

    assert {str(n.identifier) for n in g.nodes()} == {"ex:a1", "ex:e1"}
    assert all(n.bundle is not None for n in g.nodes())
    assert g.number_of_edges() == 1
    assert graph_to_prov(g) == document.flattened().unified()


def test_one_identifier_in_two_bundles_gives_one_node(document: ProvDocument) -> None:
    document.bundle("ex:b1").entity("ex:e", {"ex:v": 1})
    document.bundle("ex:b2").entity("ex:e", {"ex:w": 2})

    g = prov_to_graph(document)

    (node,) = g.nodes()
    assert dict(node.attributes) == {
        document.valid_qualified_name("ex:v"): 1,
        document.valid_qualified_name("ex:w"): 2,
    }


def test_bundle_default_namespace_round_trips_through_the_graph(
    document: ProvDocument,
) -> None:
    # flattened() declares dn for the bundle's default, so the bare name keeps
    # a spelling in the graph's document and in the one built back from it.
    bundle = document.bundle("ex:b")
    bundle.set_default_namespace("http://bun.org/")
    bundle.entity("inner")
    bundle.entity("ex:outer")
    bundle.wasDerivedFrom("inner", "ex:outer")

    result = graph_to_prov(prov_to_graph(document))

    assert result == document.flattened().unified()
    assert {ns.prefix: ns.uri for ns in result.get_registered_namespaces()} == {
        "ex": "http://example.org/",
        "dn": "http://bun.org/",
    }
    assert "entity(dn:inner)" in result.get_provn()

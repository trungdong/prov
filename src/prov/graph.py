from __future__ import annotations

from typing import Any

try:
    import networkx as nx
except ImportError as e:  # pragma: no cover -- networkx (graph extra) absent; covered by the minimal-install CI job
    raise ModuleNotFoundError(
        'prov.graph requires the optional "graph" extra; '
        'install "prov[graph]" to use NetworkX graph interop'
    ) from e

from prov.identifier import QualifiedName
from prov.model import (
    PROV_ATTR_ACTIVITY,
    PROV_ATTR_AGENT,
    PROV_ATTR_ALTERNATE1,
    PROV_ATTR_ALTERNATE2,
    PROV_ATTR_BUNDLE,
    PROV_ATTR_COLLECTION,
    PROV_ATTR_DELEGATE,
    PROV_ATTR_ENDER,
    PROV_ATTR_ENTITY,
    PROV_ATTR_GENERAL_ENTITY,
    PROV_ATTR_GENERATED_ENTITY,
    PROV_ATTR_INFORMANT,
    PROV_ATTR_INFORMED,
    PROV_ATTR_PLAN,
    PROV_ATTR_RESPONSIBLE,
    PROV_ATTR_SPECIFIC_ENTITY,
    PROV_ATTR_STARTER,
    PROV_ATTR_TRIGGER,
    PROV_ATTR_USED_ENTITY,
    ProvActivity,
    ProvAgent,
    ProvBundle,
    ProvDocument,
    ProvElement,
    ProvEntity,
    ProvRecord,
    ProvRelation,
)

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


INFERRED_ELEMENT_CLASS = {
    PROV_ATTR_ENTITY: ProvEntity,
    PROV_ATTR_ACTIVITY: ProvActivity,
    PROV_ATTR_AGENT: ProvAgent,
    PROV_ATTR_TRIGGER: ProvEntity,
    PROV_ATTR_GENERATED_ENTITY: ProvEntity,
    PROV_ATTR_USED_ENTITY: ProvEntity,
    PROV_ATTR_DELEGATE: ProvAgent,
    PROV_ATTR_RESPONSIBLE: ProvAgent,
    PROV_ATTR_SPECIFIC_ENTITY: ProvEntity,
    PROV_ATTR_GENERAL_ENTITY: ProvEntity,
    PROV_ATTR_ALTERNATE1: ProvEntity,
    PROV_ATTR_ALTERNATE2: ProvEntity,
    PROV_ATTR_COLLECTION: ProvEntity,
    PROV_ATTR_INFORMED: ProvActivity,
    PROV_ATTR_INFORMANT: ProvActivity,
    PROV_ATTR_BUNDLE: ProvBundle,
    PROV_ATTR_PLAN: ProvEntity,
    PROV_ATTR_ENDER: ProvEntity,
    PROV_ATTR_STARTER: ProvEntity,
}
"""Maps a relation's first/second formal attribute (e.g. ``PROV_ATTR_ENTITY``)
to the :class:`~prov.model.ProvElement` subclass used to create a bare node
for an element referenced by a relation but not otherwise declared."""


def prov_to_graph(prov_document: ProvDocument) -> nx.MultiDiGraph[Any]:
    """Convert a :class:`~prov.model.ProvDocument` to a `MultiDiGraph
    <https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html>`_
    instance of the `NetworkX <https://networkx.github.io/>`_ library.

    The document is first :meth:`~prov.model.ProvBundle.unified` so that
    records referring to the same real-world thing are merged before the
    graph is built. Every PROV element becomes a graph node. Each relation
    becomes an edge between the elements named in its first two formal
    attributes, with the relation record stored under the edge's
    ``"relation"`` attribute; if either of those two elements was not
    already added as a node, a bare node is created for it using
    :data:`INFERRED_ELEMENT_CLASS`. Relations whose first two formal
    attributes are not both populated, or whose attribute type is not in
    :data:`INFERRED_ELEMENT_CLASS`, are silently skipped.

    Args:
        prov_document: The :class:`~prov.model.ProvDocument` instance to
            convert.

    Returns:
        A NetworkX ``MultiDiGraph`` with PROV elements as nodes and PROV
        relations as edges.
    """
    g: nx.MultiDiGraph[Any] = nx.MultiDiGraph()
    unified = prov_document.unified()
    node_map: dict[QualifiedName | None, ProvRecord] = {}
    for element in unified.get_records(ProvElement):
        g.add_node(element)
        node_map[element.identifier] = element

    for relation in unified.get_records(ProvRelation):
        # taking the first two elements of a relation
        attr_pair_1, attr_pair_2 = relation.formal_attributes[:2]
        # only need the QualifiedName (i.e. the value of the attribute)
        qn1, qn2 = attr_pair_1[1], attr_pair_2[1]
        if qn1 and qn2:  # only proceed if both ends of the relation exist
            try:
                if qn1 not in node_map:
                    node_map[qn1] = INFERRED_ELEMENT_CLASS[attr_pair_1[0]](None, qn1)
                if qn2 not in node_map:
                    node_map[qn2] = INFERRED_ELEMENT_CLASS[attr_pair_2[0]](None, qn2)
            except KeyError:
                # Unsupported attribute; cannot infer the type of the element
                continue  # skipping this relation
            g.add_edge(node_map[qn1], node_map[qn2], relation=relation)
    return g


def graph_to_prov(g: nx.MultiDiGraph[Any]) -> ProvDocument:
    """Convert a `MultiDiGraph
    <https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html>`_
    that was previously produced by :func:`prov_to_graph` back to a
    :class:`~prov.model.ProvDocument`.

    Every node that is a :class:`~prov.model.ProvRecord` already attached to
    a bundle is added to the new document; nodes without a bundle (e.g. bare
    nodes inferred by :func:`prov_to_graph`) are skipped. Every edge whose
    ``"relation"`` data is a :class:`~prov.model.ProvRecord` is likewise
    added; edges without relation data are skipped.

    Args:
        g: The graph instance to convert.

    Returns:
        A new :class:`~prov.model.ProvDocument` containing the elements and
        relations recovered from ``g``.
    """
    prov_doc = ProvDocument()
    for n in g.nodes():
        if isinstance(n, ProvRecord) and n.bundle is not None:
            prov_doc.add_record(n)
    for _, _, edge_data in g.edges(data=True):
        try:
            relation = edge_data["relation"]
            if isinstance(relation, ProvRecord):
                prov_doc.add_record(relation)
        except KeyError:
            pass

    return prov_doc

import networkx as nx
from prov.model import (
    ProvDocument,
    ProvRecord,
    ProvElement,
    ProvEntity,
    ProvActivity,
    ProvAgent,
    ProvRelation,
    PROV_ATTR_ENTITY,
    PROV_ATTR_ACTIVITY,
    PROV_ATTR_AGENT,
    PROV_ATTR_TRIGGER,
    PROV_ATTR_GENERATED_ENTITY,
    PROV_ATTR_USED_ENTITY,
    PROV_ATTR_DELEGATE,
    PROV_ATTR_RESPONSIBLE,
    PROV_ATTR_SPECIFIC_ENTITY,
    PROV_ATTR_GENERAL_ENTITY,
    PROV_ATTR_ALTERNATE1,
    PROV_ATTR_ALTERNATE2,
    PROV_ATTR_COLLECTION,
    PROV_ATTR_INFORMED,
    PROV_ATTR_INFORMANT,
    PROV_ATTR_BUNDLE,
    PROV_ATTR_PLAN,
    PROV_ATTR_ENDER,
    PROV_ATTR_STARTER,
    ProvBundle,
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


def prov_to_graph(prov_document):
    """
    Convert a :class:`~prov.model.ProvDocument` to a `MultiDiGraph
    <https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html>`_
    instance of the `NetworkX <https://networkx.github.io/>`_ library.

    :param prov_document: The :class:`~prov.model.ProvDocument` instance to convert.
    """
    g = nx.MultiDiGraph()
    unified = prov_document.unified()
    node_map = dict()
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


def graph_to_prov(g):
    """
    Convert a `MultiDiGraph
    <https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html>`_
    that was previously produced by :func:`prov_to_graph` back to a
    :class:`~prov.model.ProvDocument`.

    :param g: The graph instance to convert.
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

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Trung Dong Huynh'
__email__ = 'trungdong@donggiang.com'

import networkx as nx

from prov.model import ProvEntity, ProvActivity, ProvAgent, ProvElement, ProvRelation,\
    PROV_ATTR_ENTITY, PROV_ATTR_ACTIVITY, PROV_ATTR_AGENT, PROV_ATTR_TRIGGER, PROV_ATTR_GENERATED_ENTITY,\
    PROV_ATTR_USED_ENTITY, PROV_ATTR_DELEGATE, PROV_ATTR_RESPONSIBLE, PROV_ATTR_SPECIFIC_ENTITY,\
    PROV_ATTR_GENERAL_ENTITY, PROV_ATTR_ALTERNATE1, PROV_ATTR_ALTERNATE2, PROV_ATTR_COLLECTION, PROV_ATTR_INFORMED,\
    PROV_ATTR_INFORMANT

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
    PROV_ATTR_INFORMANT: ProvActivity
}


def prov_to_graph(prov_document):
    """ Convert a :class:`~prov.model.ProvDocument` to a
    `MultiDiGraph <http://networkx.github.io/documentation/latest/reference/classes.multidigraph.html>`_
    instance of the `NetworkX <https://networkx.github.io/>`_ library.

    :param prov_document: The :class:`~prov.model.ProvDocument` instance to convert.
    """
    g = nx.MultiDiGraph()
    unified = prov_document.unified()
    node_map = dict((element.identifier, element) for element in unified.get_records(ProvElement))
    for relation in unified.get_records(ProvRelation):
        attr_pair_1, attr_pair_2 = relation.formal_attributes[:2]  # taking the first two elements of a relation
        qn1, qn2 = attr_pair_1[1], attr_pair_2[1]  # only need the QualifiedName (i.e. the value of the attribute)
        if qn1 and qn2:  # only proceed if both ends of the relation exist
            try:
                if qn1 not in node_map:
                    node_map[qn1] = INFERRED_ELEMENT_CLASS[attr_pair_1[0]](None, qn1)
                if qn2 not in node_map:
                    node_map[qn2] = INFERRED_ELEMENT_CLASS[attr_pair_2[0]](None, qn2)
            except KeyError:
                # Unsuported attribute; cannot infer the type of the element
                continue  # skiping this relation
            g.add_edge(node_map[qn1], node_map[qn2], relation=relation)
    return g

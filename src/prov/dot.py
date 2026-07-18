"""Graphical visualisation support for prov.model.

This module produces graphical visualisation for provenance graphs.
Requires pydot module and Graphviz.

References:

* pydot homepage: https://github.com/erocarrera/pydot
* Graphviz:       http://www.graphviz.org/
* DOT Language:   http://www.graphviz.org/doc/info/lang.html

.. moduleauthor:: Trung Dong Huynh <trungdong@donggiang.com>
"""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

from datetime import datetime
from html import escape
from typing import Any

try:
    import pydot
except ImportError as e:
    raise ModuleNotFoundError(
        'prov.dot requires the optional "dot" extra; '
        'install "prov[dot]" to use graphical export'
    ) from e

from prov.graph import INFERRED_ELEMENT_CLASS
from prov.identifier import QualifiedName
from prov.model import (
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ALTERNATE,
    PROV_ASSOCIATION,
    PROV_ATTRIBUTE_QNAMES,
    PROV_ATTRIBUTION,
    PROV_BUNDLE,
    PROV_COMMUNICATION,
    PROV_DELEGATION,
    PROV_DERIVATION,
    PROV_END,
    PROV_ENTITY,
    PROV_GENERATION,
    PROV_INFLUENCE,
    PROV_INVALIDATION,
    PROV_MEMBERSHIP,
    PROV_MENTION,
    PROV_SPECIALIZATION,
    PROV_START,
    PROV_USAGE,
    Identifier,
    ProvActivity,
    ProvAgent,
    ProvBundle,
    ProvElement,
    ProvEntity,
    ProvException,
    ProvRecord,
    sorted_attributes,
)

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


# Visual styles for various elements (nodes) and relations (edges)
# see http://graphviz.org/content/attrs
GENERIC_NODE_STYLE = {
    None: {
        "shape": "oval",
        "style": "filled",
        "fillcolor": "lightgray",
        "color": "dimgray",
    },
    ProvEntity: {
        "shape": "oval",
        "style": "filled",
        "fillcolor": "lightgray",
        "color": "dimgray",
    },
    ProvActivity: {
        "shape": "box",
        "style": "filled",
        "fillcolor": "lightgray",
        "color": "dimgray",
    },
    ProvAgent: {
        "shape": "house",
        "style": "filled",
        "fillcolor": "lightgray",
        "color": "dimgray",
    },
    ProvBundle: {
        "shape": "folder",
        "style": "filled",
        "fillcolor": "lightgray",
        "color": "dimgray",
    },
}  # type: dict[type[ProvElement | ProvBundle] | None, dict[str, Any]]
# Value type is widened to Any (rather than str) because mypy treats a
# dict[str, str] unpacked via `**style` as needing to satisfy *every*
# named parameter pydot.Node/Edge/Cluster declare (e.g. `obj_dict`), not
# just their `**attrs: Any` catch-all, due to dict invariance; see
# https://github.com/python/mypy/issues/6799
DOT_PROV_STYLE: dict[Any, dict[str, Any]] = {
    # Generic node
    0: {
        "shape": "oval",
        "style": "filled",
        "fillcolor": "lightgray",
        "color": "dimgray",
    },
    # Elements
    PROV_ENTITY: {
        "shape": "oval",
        "style": "filled",
        "fillcolor": "#FFFC87",
        "color": "#808080",
    },
    PROV_ACTIVITY: {
        "shape": "box",
        "style": "filled",
        "fillcolor": "#9FB1FC",
        "color": "#0000FF",
    },
    PROV_AGENT: {"shape": "house", "style": "filled", "fillcolor": "#FED37F"},
    PROV_BUNDLE: {"shape": "folder", "style": "filled", "fillcolor": "aliceblue"},
    # Relations
    PROV_GENERATION: {
        "label": "wasGeneratedBy",
        "fontsize": "10.0",
        "color": "darkgreen",
        "fontcolor": "darkgreen",
    },
    PROV_USAGE: {
        "label": "used",
        "fontsize": "10.0",
        "color": "red4",
        "fontcolor": "red",
    },
    PROV_COMMUNICATION: {"label": "wasInformedBy", "fontsize": "10.0"},
    PROV_START: {"label": "wasStartedBy", "fontsize": "10.0"},
    PROV_END: {"label": "wasEndedBy", "fontsize": "10.0"},
    PROV_INVALIDATION: {"label": "wasInvalidatedBy", "fontsize": "10.0"},
    PROV_DERIVATION: {"label": "wasDerivedFrom", "fontsize": "10.0"},
    PROV_ATTRIBUTION: {
        "label": "wasAttributedTo",
        "fontsize": "10.0",
        "color": "#FED37F",
    },
    PROV_ASSOCIATION: {
        "label": "wasAssociatedWith",
        "fontsize": "10.0",
        "color": "#FED37F",
    },
    PROV_DELEGATION: {
        "label": "actedOnBehalfOf",
        "fontsize": "10.0",
        "color": "#FED37F",
    },
    PROV_INFLUENCE: {"label": "wasInfluencedBy", "fontsize": "10.0", "color": "grey"},
    PROV_ALTERNATE: {"label": "alternateOf", "fontsize": "10.0"},
    PROV_SPECIALIZATION: {"label": "specializationOf", "fontsize": "10.0"},
    PROV_MENTION: {"label": "mentionOf", "fontsize": "10.0"},
    PROV_MEMBERSHIP: {"label": "hadMember", "fontsize": "10.0"},
}

ANNOTATION_STYLE: dict[str, Any] = {
    "shape": "note",
    "color": "gray",
    "fontcolor": "black",
    "fontsize": "10",
}
ANNOTATION_LINK_STYLE: dict[str, Any] = {
    "arrowhead": "none",
    "style": "dashed",
    "color": "gray",
}
ANNOTATION_START_ROW = '<<TABLE cellpadding="0" border="0">'
ANNOTATION_ROW_TEMPLATE = """    <TR>
        <TD align=\"left\" href=\"%s\">%s</TD>
        <TD align=\"left\"%s>%s</TD>
    </TR>"""
ANNOTATION_END_ROW = "    </TABLE>>"


def htlm_link_if_uri(value: Any) -> str:
    """Render an attribute value as an HTML anchor if it has a ``uri``, else as plain text.

    Args:
        value: Attribute value to render; typically an
            :class:`~prov.identifier.Identifier`/:class:`~prov.identifier.QualifiedName`
            (which have a ``uri`` attribute) or a plain literal.

    Returns:
        An ``<a href="...">`` HTML fragment linking to ``value.uri`` if
        ``value`` has a ``uri`` attribute, otherwise ``str(value)``.
    """
    try:
        uri = value.uri
        return f'<a href="{uri}">{value!s}</a>'
    except AttributeError:
        return str(value)


def prov_to_dot(
    bundle: ProvBundle,
    show_nary: bool = True,
    use_labels: bool = False,
    direction: str = "BT",
    show_element_attributes: bool = True,
    show_relation_attributes: bool = True,
) -> pydot.Dot:
    """Convert a provenance bundle/document into a DOT graphical representation.

    The bundle is first :meth:`~prov.model.ProvBundle.unified`; if that
    raises :class:`~prov.model.ProvException` (the bundle cannot be
    unified), the original, non-unified bundle is rendered instead.

    Args:
        bundle: The provenance bundle/document to be converted.
        show_nary: Show all elements of n-ary relations (i.e. relations with
            more than two formal attributes), not just the first two.
        use_labels: Use the ``prov:label`` property of an element as its
            displayed name (instead of its identifier), where available.
        direction: Direction of the graph, passed to Graphviz as
            ``rankdir``. Valid values are ``"BT"`` (default), ``"TB"``,
            ``"LR"``, ``"RL"``; any other value is silently replaced with
            ``"BT"``.
        show_element_attributes: Show attributes of elements as annotation
            nodes.
        show_relation_attributes: Show attributes of relations as annotation
            nodes.

    Returns:
        The :class:`pydot.Dot` graph object.
    """
    if direction not in {"BT", "TB", "LR", "RL"}:
        # Invalid direction is provided
        direction = "BT"  # reset it to the default value
    maindot = pydot.Dot(graph_type="digraph", rankdir=direction, charset="utf-8")

    node_map = {}  # type: dict[str, pydot.Node]
    count = [0, 0, 0, 0]  # counters for node ids

    def _bundle_to_dot(dot: pydot.Dot | pydot.Cluster, bundle: ProvBundle) -> None:
        def _attach_attribute_annotation(node: pydot.Node, record: ProvRecord) -> None:
            # Adding a node to show all attributes
            attributes = [
                (attr_name, value)
                for attr_name, value in record.attributes
                if attr_name not in PROV_ATTRIBUTE_QNAMES
            ]

            if not attributes:
                return  # No attribute to display

            # Sort the attributes.
            attributes = sorted_attributes(record.get_type(), attributes)

            ann_rows = [ANNOTATION_START_ROW]
            ann_rows.extend(
                ANNOTATION_ROW_TEMPLATE
                % (
                    attr.uri,
                    escape(str(attr)),
                    f' href="{value.uri}"' if isinstance(value, Identifier) else "",
                    escape(
                        str(value)
                        if not isinstance(value, datetime)
                        else str(value.isoformat())
                    ),
                )
                for attr, value in attributes
            )
            ann_rows.append(ANNOTATION_END_ROW)
            count[3] += 1
            annotations = pydot.Node(
                f"ann{count[3]}", label="\n".join(ann_rows), **ANNOTATION_STYLE
            )
            dot.add_node(annotations)
            dot.add_edge(pydot.Edge(annotations, node, **ANNOTATION_LINK_STYLE))

        def _add_bundle(bundle: ProvBundle) -> pydot.Cluster:
            count[2] += 1
            subdot = pydot.Cluster(
                graph_name=f"c{count[2]}",
                URL=f'"{bundle.identifier.uri}"',  # type: ignore[union-attr]
            )
            # set_label is generated at runtime by pydot via setattr() for
            # every Graphviz attribute (see pydot.core.__generate_attribute_methods),
            # so it exists on Cluster instances but isn't visible to mypy.
            subdot.set_label(f'"{bundle.identifier!s}"')  # type: ignore[attr-defined]
            _bundle_to_dot(subdot, bundle)
            # pydot types Graph.add_subgraph() as accepting only a Subgraph,
            # but Cluster (a Graph subclass, not a Subgraph subclass) is the
            # documented/idiomatic way to add a cluster subgraph in pydot.
            dot.add_subgraph(subdot)  # type: ignore[arg-type]
            return subdot

        def _add_node(record: ProvRecord) -> pydot.Node:
            count[0] += 1
            node_id = f"n{count[0]}"
            if use_labels:
                if record.label == record.identifier:
                    node_label = f'"{record.label}"'
                else:
                    # Fancier label if both are different. The label will be
                    # the main node text, whereas the identifier will be a
                    # kind of subtitle.
                    node_label = (
                        f"<{record.label}<br />"
                        f'<font color="#333333" point-size="10">'
                        f"{record.identifier}</font>>"
                    )
            else:
                node_label = f'"{record.identifier}"'

            uri = record.identifier.uri  # type: ignore[union-attr]
            style = DOT_PROV_STYLE[record.get_type()]
            node = pydot.Node(node_id, label=node_label, URL=f'"{uri}"', **style)
            node_map[uri] = node
            dot.add_node(node)

            if show_element_attributes:
                _attach_attribute_annotation(node, rec)
            return node

        def _add_generic_node(
            qname: QualifiedName, prov_type: type[ProvElement] | None = None
        ) -> pydot.Node:
            count[0] += 1
            node_id = f"n{count[0]}"
            node_label = f'"{qname}"'

            uri = qname.uri
            style = GENERIC_NODE_STYLE[prov_type] if prov_type else DOT_PROV_STYLE[0]
            node = pydot.Node(node_id, label=node_label, URL=f'"{uri}"', **style)
            node_map[uri] = node
            dot.add_node(node)
            return node

        def _get_bnode() -> pydot.Node:
            count[1] += 1
            bnode_id = f"b{count[1]}"
            bnode = pydot.Node(bnode_id, label='""', shape="point", color="gray")
            dot.add_node(bnode)
            return bnode

        def _get_node(
            qname: QualifiedName | None,
            prov_type: type[ProvElement] | None = None,
        ) -> pydot.Node:
            if qname is None:
                return _get_bnode()
            uri = qname.uri
            if uri not in node_map:
                _add_generic_node(qname, prov_type)
            return node_map[uri]

        records = bundle.get_records()
        relations = []
        for rec in records:
            if rec.is_element():
                _add_node(rec)
            else:
                # Saving the relations for later processing
                relations.append(rec)

        if not bundle.is_bundle():
            # `bundle.bundles` is evaluated once before the loop starts, so
            # reassigning `bundle` as the loop variable here is safe.
            for bundle in bundle.bundles:  # noqa: B020
                _add_bundle(bundle)

        for rec in relations:
            args = rec.args
            # skipping empty records
            if not args:
                continue
            # picking element nodes
            attr_names, nodes = zip(
                *(
                    (attr_name, value)
                    for attr_name, value in rec.formal_attributes
                    if attr_name in PROV_ATTRIBUTE_QNAMES
                ),
                strict=False,
            )
            inferred_types = list(map(INFERRED_ELEMENT_CLASS.get, attr_names))
            other_attributes = [
                (attr_name, value)
                for attr_name, value in rec.attributes
                if attr_name not in PROV_ATTRIBUTE_QNAMES
            ]
            add_attribute_annotation = show_relation_attributes and other_attributes
            add_nary_elements = len(nodes) > 2 and show_nary
            style = DOT_PROV_STYLE[rec.get_type()]
            if len(nodes) < 2:  # too few elements for a relation?
                continue  # cannot draw this

            if add_nary_elements or add_attribute_annotation:
                # a blank node for n-ary relations or the attribute annotation
                bnode = _get_bnode()

                # the first segment
                dot.add_edge(
                    pydot.Edge(
                        _get_node(nodes[0], inferred_types[0]),
                        bnode,
                        arrowhead="none",
                        **style,
                    )
                )
                style = dict(style)  # copy the style
                del style["label"]  # not showing label in the second segment
                # the second segment
                dot.add_edge(
                    pydot.Edge(bnode, _get_node(nodes[1], inferred_types[1]), **style)
                )
                if add_nary_elements:
                    style["color"] = "gray"  # all remaining segment to be gray
                    style["fontcolor"] = "dimgray"  # text in darker gray
                    for attr_name, node, inferred_type in zip(
                        attr_names[2:], nodes[2:], inferred_types[2:], strict=False
                    ):
                        if node is not None:
                            style["label"] = attr_name.localpart
                            dot.add_edge(
                                pydot.Edge(
                                    bnode, _get_node(node, inferred_type), **style
                                )
                            )
                if add_attribute_annotation:
                    _attach_attribute_annotation(bnode, rec)
            else:
                # show a simple binary relation with no annotation
                dot.add_edge(
                    pydot.Edge(
                        _get_node(nodes[0], inferred_types[0]),
                        _get_node(nodes[1], inferred_types[1]),
                        **style,
                    )
                )

    try:
        unified = bundle.unified()
    except ProvException:
        # Could not unify this bundle
        # try the original document anyway
        unified = bundle

    _bundle_to_dot(maindot, unified)
    return maindot

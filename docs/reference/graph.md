# prov.graph

`prov.graph` converts between a {py:class}`~prov.model.ProvDocument` and a
[NetworkX](https://networkx.org/) `MultiDiGraph`, with one node per element (entity,
activity, agent) and one edge per relation, so NetworkX's graph algorithms can run over a
provenance graph. It needs the `graph` extra. {doc}`../howto/networkx` has worked examples.

```{eval-rst}
.. autofunction:: prov.graph.prov_to_graph

.. autofunction:: prov.graph.graph_to_prov
```

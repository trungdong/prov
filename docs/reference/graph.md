# prov.graph

`prov.graph` converts between a {py:class}`~prov.model.ProvDocument` and a
[NetworkX](https://networkx.org/) `MultiDiGraph`, one node per element (entity, activity,
agent) and one edge per relation, so graph algorithms NetworkX provides (and `prov` does
not implement) can run directly over a provenance graph. See {doc}`../howto/networkx` for
worked examples.

```{eval-rst}
.. autofunction:: prov.graph.prov_to_graph

.. autofunction:: prov.graph.graph_to_prov
```

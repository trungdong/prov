# Convert to/from a NetworkX graph

`prov.graph` converts a document to and from a
[NetworkX](https://networkx.org/) `MultiDiGraph`, useful for running graph algorithms
(centrality, shortest paths, community detection, ...) that `prov` itself does not
implement. `networkx` is a core dependency — no extra install needed.

## Document to graph

{py:func}`~prov.graph.prov_to_graph` returns one node per element (entity/activity/agent)
and one edge per relation. It unifies the document first, so records describing the same
identifier are merged into a single node:

```python
import prov.model as pm
from prov.graph import prov_to_graph

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

g = prov_to_graph(document)

print(list(g.nodes()))
# [<ProvEntity: e1>, <ProvActivity: a1>]
print(list(g.edges(data=True)))
# [(<ProvEntity: e1>, <ProvActivity: a1>, {'relation': <ProvGeneration: (e1, a1)>})]
```

Each node *is* the `prov` element record (a {py:class}`~prov.model.ProvElement`); each edge
carries the originating {py:class}`~prov.model.ProvRelation` under the `"relation"` key so
you don't lose PROV-specific information (relation type, extra attributes) while using
NetworkX.

## Run a NetworkX algorithm

Because nodes are hashable `prov` objects, any NetworkX algorithm works directly:

```python
import networkx as nx

print(nx.is_directed_acyclic_graph(g))
```

## Graph back to document

{py:func}`~prov.graph.graph_to_prov` reverses the conversion for a graph previously
produced by `prov_to_graph` (or built to match its shape — nodes are `ProvRecord`
instances with a bundle, edges carry a `"relation"` record in their data):

```python
from prov.graph import graph_to_prov

reloaded = graph_to_prov(g)
assert reloaded == document
```

## Round trip

```python
g = prov_to_graph(document)
reloaded = graph_to_prov(g)
assert reloaded == document
```

# Convert to and from a NetworkX graph

`prov.graph` converts a document to and from a [NetworkX](https://networkx.org/)
`MultiDiGraph`, so you can run graph algorithms such as centrality, shortest paths or
community detection over it. It needs the `graph` extra:

```bash
python -m pip install "prov[graph]"
```

## Document to graph

{py:func}`~prov.graph.prov_to_graph` returns one node per element (entity, activity or
agent) and one edge per relation. It unifies the document first, so records that share an
identifier become one node:

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

Each node is the {py:class}`~prov.model.ProvElement` record itself. Each edge carries its
{py:class}`~prov.model.ProvRelation` under the `"relation"` key, so the relation type and
its attributes stay available while you work in NetworkX.

A relation whose endpoint is unset, or undeclared with a type that cannot be inferred, is
dropped with a {py:class}`~prov.model.ProvWarning`.

## Run a NetworkX algorithm

Nodes are hashable `prov` objects, so any NetworkX algorithm works directly:

```python
import networkx as nx

print(nx.is_directed_acyclic_graph(g))
```

## Graph back to document

{py:func}`~prov.graph.graph_to_prov` reverses the conversion. The graph must have the
shape `prov_to_graph` produces. Nodes are {py:class}`~prov.model.ProvRecord` instances
with a bundle, and each edge carries a `"relation"` record in its data:

```python
from prov.graph import graph_to_prov

reloaded = graph_to_prov(g)
assert reloaded == document
```

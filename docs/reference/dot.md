# prov.dot

`prov.dot` renders a {py:class}`~prov.model.ProvDocument` as a
[pydot](https://pypi.org/project/pydot/) `Dot` graph, which a local
[Graphviz](https://graphviz.org/) install writes out as PNG, SVG or PDF. A plain
{py:class}`~prov.model.ProvBundle` warns `DeprecationWarning`, and 4.0 draws documents
only. It needs the `dot` extra. {doc}`../howto/graphics` covers the Graphviz setup, worked
examples and how to draw one bundle.

```{eval-rst}
.. py:module:: prov.dot

.. autofunction:: prov.dot.prov_to_dot
```

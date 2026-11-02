# prov.dot

`prov.dot` renders a {py:class}`~prov.model.ProvDocument` as a
[pydot](https://pypi.org/project/pydot/) `Dot` graph, which a local
[Graphviz](https://graphviz.org/) install writes out as PNG, SVG or PDF. `prov.dot` needs
the `dot` extra. {doc}`../howto/graphics` covers the Graphviz setup and worked examples,
and its "Draw one bundle" section covers a bundle that is not a document.

```{eval-rst}
.. py:module:: prov.dot

.. autofunction:: prov.dot.prov_to_dot
```

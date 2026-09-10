# prov.dot

`prov.dot` renders a {py:class}`~prov.model.ProvBundle` or
{py:class}`~prov.model.ProvDocument` as a [pydot](https://pypi.org/project/pydot/) `Dot`
graph, which a local [Graphviz](https://graphviz.org/) install writes out as PNG, SVG or
PDF. It needs the `dot` extra. {doc}`../howto/graphics` covers the Graphviz setup and
worked examples.

```{eval-rst}
.. autofunction:: prov.dot.prov_to_dot
```

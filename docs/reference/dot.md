# prov.dot

`prov.dot` renders a {py:class}`~prov.model.ProvBundle`/{py:class}`~prov.model.ProvDocument`
as a [pydot](https://pypi.org/project/pydot/) `Dot` graph, which can then be written out as
PNG, SVG, or PDF via a local [Graphviz](https://graphviz.org/) install. See
{doc}`../howto/graphics` for the Graphviz setup notes and end-to-end examples.

```{eval-rst}
.. autofunction:: prov.dot.prov_to_dot
```

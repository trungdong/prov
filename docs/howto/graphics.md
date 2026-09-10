# Render a document as a graph (PNG, SVG, PDF)

`prov.dot` turns a document into a [pydot](https://pypi.org/project/pydot/) graph, which
Graphviz can write in any format it supports. It needs the `dot` extra and a local
Graphviz install.

```bash
python -m pip install "prov[dot]"
```

```{important}
The `dot` extra installs the `pydot` and `networkx` packages. Rendering also needs the
Graphviz `dot` executable, which you install separately:

- macOS: `brew install graphviz`
- Debian and Ubuntu: `apt install graphviz`
- Windows: the installer from <https://graphviz.org/download/>

Without it every `write_*()` call below fails, usually with an error about the missing
`dot` executable. Check with `dot -V` that Graphviz is on your `PATH` before debugging
your own code.
```

## Convert a document to a `pydot.Dot`

```python
import prov.model as pm
from prov.dot import prov_to_dot

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

dot = prov_to_dot(document)
```

## Write PNG, SVG or PDF

`pydot.Dot` has a `write_<format>` method for each Graphviz output format:

```python
dot.write_png("document.png")
dot.write_svg("document.svg")
dot.write_pdf("document.pdf")
```

## Layout direction

`direction` sets the rank direction. The default is `"BT"`, bottom to top. The other
values are `"TB"`, `"LR"` and `"RL"`:

```python
dot_lr = prov_to_dot(document, direction="LR")
dot_lr.write_svg("document-lr.svg")
```

## Hide attribute annotations

By default every element and relation gets a note node listing its non-formal attributes.
Turn either off to declutter a dense graph:

```python
dot_plain = prov_to_dot(
    document,
    show_element_attributes=False,
    show_relation_attributes=False,
)
```

## Use labels instead of identifiers

Pass `use_labels=True` to show each element's `prov:label` as the node text. An element
without a label falls back to its identifier:

```python
document.entity("e1", {pm.PROV_LABEL: "Crime report"})
dot_labelled = prov_to_dot(document, use_labels=True)
```

## Hide n-ary relation elements

A relation with more than two formal attributes, such as a `wasDerivedFrom` that also
records an activity, usage and generation, draws every element by default. Set
`show_nary=False` to draw only the first two:

```python
dot_binary = prov_to_dot(document, show_nary=False)
```

## All together

```python
dot = prov_to_dot(
    document,
    show_nary=True,
    use_labels=False,
    direction="BT",
    show_element_attributes=True,
    show_relation_attributes=True,
)
```

{py:func}`prov.dot.prov_to_dot` documents every parameter.

# Render a document as a graph (PNG/SVG/PDF)

`prov.dot` turns a document into a [pydot](https://pypi.org/project/pydot/) graph, which
can then be written out in any format Graphviz supports.

```{important}
Rendering needs a local **Graphviz** installation (the `dot` executable) in addition to the
`pydot` Python package (which is a core dependency of `prov`, always installed). Installing
`pydot` alone is not enough — this is the most common source of confusion:

- **macOS**: `brew install graphviz`
- **Debian/Ubuntu**: `apt install graphviz`
- **Windows**: download and run the installer from <https://graphviz.org/download/>

Without it, `dot.write_*()` calls below fail (typically with a `FileNotFoundError` for the
`dot` executable, surfaced by `pydot` as an assertion/`Exception` depending on version) —
verify Graphviz is on `PATH` with `dot -V` before debugging your own code.
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

## Write PNG, SVG, or PDF

`pydot.Dot` has a `write_<format>` method for most Graphviz output formats:

```python
dot.write_png("document.png")
dot.write_svg("document.svg")
dot.write_pdf("document.pdf")
```

## Layout direction

`direction` controls the rank direction Graphviz lays the graph out in — `"BT"`
(bottom-to-top, the default), `"TB"`, `"LR"`, or `"RL"`:

```python
dot_lr = prov_to_dot(document, direction="LR")
dot_lr.write_svg("document-lr.svg")
```

## Hide attribute annotations

By default every element and relation gets an attached note node listing its non-formal
attributes. Turn either off to declutter dense graphs:

```python
dot_plain = prov_to_dot(
    document,
    show_element_attributes=False,
    show_relation_attributes=False,
)
```

## Use labels instead of identifiers

Pass `use_labels=True` to show each element's `prov:label` (falling back to its
identifier) as the node text instead of always showing the identifier:

```python
document.entity("e1", {pm.PROV_LABEL: "Crime report"})
dot_labelled = prov_to_dot(document, use_labels=True)
```

## Hide n-ary relation elements

Relations with more than two formal attributes (e.g. a `wasDerivedFrom` recording an
activity and usage/generation) render every element by default. Set `show_nary=False` to
draw only the first two:

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

See {py:func}`prov.dot.prov_to_dot` for the full parameter reference.

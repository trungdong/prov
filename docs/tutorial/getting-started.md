# Getting started

This tutorial walks you through the whole life cycle of a provenance document with
`prov`: building it in memory, printing it as [PROV-N](https://www.w3.org/TR/prov-n/),
saving it to (and loading it back from) [PROV-JSON](https://www.w3.org/Submission/prov-json/),
and rendering it as a diagram. Every code block runs as written; paste them into a Python
session in order, or copy them into a script.

If you have not installed the library yet, see {doc}`../installation`. To follow the
visualisation section you will also need a local [Graphviz](https://graphviz.org/) install
(more on that below).

## Build a document

A {py:class}`~prov.model.ProvDocument` is the top-level container for provenance
statements. We start by declaring the namespaces our identifiers live in — a *default*
namespace for the things this document is primarily about, and an `ex` prefix for
everything else.

```python
import prov.model as prov

document = prov.ProvDocument()
document.set_default_namespace("http://anotherexample.org/")
document.add_namespace("ex", "http://example.org/")
```

Now we add an **entity** — the file whose provenance we are describing. Attributes are
given as a list (or dict) of `(name, value)` pairs. Names can be `prov:*` constants such
as {py:data}`prov.model.PROV_TYPE` or any prefixed name like `ex:path`.

```python
e2 = document.entity("e2", (
    (prov.PROV_TYPE, "File"),
    ("ex:path", "/shared/crime.txt"),
    ("ex:creator", "Alice"),
    ("ex:content", "There was a lot of crime in London last month"),
))
```

Next, the **activity** that produced the file, an **agent** responsible for it, and the
relations that tie them together. The factory methods return the record they create, so
you can pass either the record objects (`e2`, `a1`) or their string identifiers as
references.

```python
a1 = document.activity("a1", "2024-07-09T16:39:38", None, {prov.PROV_TYPE: "edit"})

# Pass extra attributes with the ``other_attributes`` keyword.
document.wasGeneratedBy(e2, a1, other_attributes={"ex:fct": "save"})
document.wasAssociatedWith("a1", "ag2", None, None, {prov.PROV_ROLE: "author"})
document.agent("ag2", {prov.PROV_TYPE: "prov:Person", "ex:name": "Bob"})
```

That is a complete provenance document. Print it in PROV-N, the human-readable notation
from the PROV specification:

```python
print(document.get_provn())
```

```text
document
  default <http://anotherexample.org/>
  prefix ex <http://example.org/>

  entity(e2, [prov:type="File", ex:path="/shared/crime.txt", ex:creator="Alice", ex:content="There was a lot of crime in London last month"])
  activity(a1, 2024-07-09T16:39:38, -, [prov:type="edit"])
  wasGeneratedBy(e2, a1, -, [ex:fct="save"])
  wasAssociatedWith(a1, ag2, -, [prov:role="author"])
  agent(ag2, [prov:type="prov:Person", ex:name="Bob"])
endDocument
```

## Save it and load it back

{py:meth}`~prov.model.ProvDocument.serialize` writes the document out. With no
destination it returns a string; given a file path it writes the file. The default format
is PROV-JSON.

```python
document.serialize("article-prov.json")
```

{py:meth}`~prov.model.ProvDocument.deserialize` is the inverse. It accepts a file path or
an open stream as `source`, or a string via the `content` keyword. Because a round trip
through PROV-JSON preserves the model exactly, the loaded document compares equal to the
original:

```python
loaded = prov.ProvDocument.deserialize("article-prov.json")
assert loaded == document
```

## Visualise it

The {py:mod}`prov.dot` module turns a document into a [pydot](https://pypi.org/project/pydot/)
graph, which you can write straight to an image file:

```python
from prov.dot import prov_to_dot

dot = prov_to_dot(document)
dot.write_png("article-prov.png")
```

```{note}
Rendering to PNG/PDF/SVG needs a local **Graphviz** installation (the `dot` executable),
not just the `pydot` Python package. Install it from your package manager (for example
`brew install graphviz` or `apt install graphviz`) or from <https://graphviz.org/download/>.
For styling options — direction, labels, hiding attributes — see the graphics how-to guide.
```

## Bundles

A **bundle** is a named set of statements with its own namespaces, letting you describe
the provenance of provenance. A {py:class}`~prov.model.ProvDocument` is the only kind of
bundle that may contain other, named bundles. Note how the same local name `e001` refers
to two different entities because each bundle resolves it against a different default
namespace:

```python
d = prov.ProvDocument()
d.set_default_namespace("http://example.org/0/")
d.add_namespace("ex1", "http://example.org/1/")
d.add_namespace("ex2", "http://example.org/2/")

d.entity("e001")

bundle = d.bundle("e001")
bundle.set_default_namespace("http://example.org/2/")
bundle.entity("e001")

print(d.get_provn())
```

```text
document
  default <http://example.org/0/>
  prefix ex1 <http://example.org/1/>
  prefix ex2 <http://example.org/2/>

  entity(e001)
  bundle e001
    default <http://example.org/2/>

    entity(e001)
  endBundle
endDocument
```

## Where next

- **How-to guides** — task-focused recipes: serialising to the other formats (PROV-XML,
  PROV-O/RDF, PROV-N), producing graphics, converting to and from a NetworkX graph, and
  using the command-line tools.
- **Reference** — the full API, generated from the source, under {doc}`../reference/index`.
- **The PROV data model** — for the concepts behind entities, activities, agents and the
  relations between them, read the W3C
  [PROV-DM Primer](https://www.w3.org/TR/prov-primer/).

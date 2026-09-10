# Getting started

This tutorial follows one provenance document through its life cycle. You build it in
memory, print it as [PROV-N](https://www.w3.org/TR/prov-n/), save it as
[PROV-JSON](https://www.w3.org/submissions/prov-json/), load it back and render it as a
diagram. Every code block runs as written. Paste them into a Python session in order, or
copy them into a script.

If you have not installed the library yet, see {doc}`../installation`. The visualisation
section also needs a local [Graphviz](https://graphviz.org/) install.

## Build a document

A {py:class}`~prov.model.ProvDocument` is the top-level container for provenance
statements. Start by declaring the namespaces your identifiers live in. The default
namespace is for the things this document is about, and the `ex` prefix is for everything
else.

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://anotherexample.org/")
document.add_namespace("ex", "http://example.org/")
```

Now add an **entity**, the file whose provenance you are describing. Attributes are a list
or dict of `(name, value)` pairs. A name is either a `prov:` constant such as
{py:data}`prov.model.PROV_TYPE` or a prefixed name such as `ex:path`.

```python
e2 = document.entity("e2", (
    (pm.PROV_TYPE, "File"),
    ("ex:path", "/shared/crime.txt"),
    ("ex:creator", "Alice"),
    ("ex:content", "There was a lot of crime in London last month"),
))
```

Next add the **activity** that produced the file, an **agent** responsible for it, and the
relations that tie them together. Each factory method returns the record it creates, so you
can refer to a record either by the object (`e2`, `a1`) or by its identifier string.

```python
a1 = document.activity("a1", "2024-07-09T16:39:38", None, {pm.PROV_TYPE: "edit"})

# Pass extra attributes with the ``other_attributes`` keyword.
document.wasGeneratedBy(e2, a1, other_attributes={"ex:fct": "save"})
document.wasAssociatedWith("a1", "ag2", other_attributes={pm.PROV_ROLE: "author"})
document.agent("ag2", {pm.PROV_TYPE: pm.PROV["Person"], "ex:name": "Bob"})
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
  agent(ag2, [prov:type='prov:Person', ex:name="Bob"])
endDocument
```

## Save it and load it back

{py:meth}`~prov.model.ProvDocument.serialize` writes the document out. With no destination
it returns a string. With a file path it writes the file. The default format is PROV-JSON.

```python
document.serialize("article-prov.json")
```

{py:meth}`~prov.model.ProvDocument.deserialize` is the inverse. It accepts a file path or
an open stream as `source`, or a string through the `content` keyword. A round trip
through PROV-JSON preserves the model exactly, so the loaded document compares equal to the
original:

```python
loaded = pm.ProvDocument.deserialize("article-prov.json")
assert loaded == document
```

## Visualise it

{py:mod}`prov.dot` turns a document into a [pydot](https://pypi.org/project/pydot/) graph,
which you can write straight to an image file. This needs the `dot` extra.

```python
from prov.dot import prov_to_dot

dot = prov_to_dot(document)
dot.write_png("article-prov.png")
```

```{note}
Rendering to PNG, PDF or SVG needs a local Graphviz installation, not just the `pydot`
package. Install it from your package manager, for example `brew install graphviz` or
`apt install graphviz`, or from <https://graphviz.org/download/>. The {doc}`../howto/graphics`
guide covers layout direction, labels and hiding attributes.
```

## Bundles

A **bundle** is a named set of statements with its own namespaces. It lets you describe the
provenance of provenance. Only a {py:class}`~prov.model.ProvDocument` may contain named
bundles. In the example below the local name `e001` names two different entities, because
each bundle resolves it against its own default namespace:

```python
d = pm.ProvDocument()
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

- The how-to guides cover the other formats ({doc}`../howto/provxml`,
  {doc}`../howto/provo-rdf`, {doc}`../howto/provn`, {doc}`../howto/provjsonld`), graphics,
  NetworkX conversion and the command-line tools.
- {doc}`../reference/index` documents the full API, generated from the source.
- {doc}`../explanation/prov-dm` explains entities, activities, agents and the relations
  between them. The W3C [PROV-DM Primer](https://www.w3.org/TR/prov-primer/) is the
  authoritative introduction.

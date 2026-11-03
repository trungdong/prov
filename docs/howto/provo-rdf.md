# Work with PROV-O (RDF)

[PROV-O](https://www.w3.org/TR/prov-o/) needs the `rdf` extra, which installs `rdflib`:

```bash
python -m pip install "prov[rdf]"
```

`format="rdf"` selects PROV-O; `rdf_format` chooses the RDF syntax and defaults to
`"trig"`.

## Round trip

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

document.serialize("document.trig", format="rdf")
loaded = pm.ProvDocument.deserialize("document.trig", format="rdf")
assert loaded == document
```

{doc}`read-write` covers strings, streams and {py:func}`prov.read`.

## Choose the RDF syntax

`rdf_format` accepts any syntax `rdflib` can write, such as `"turtle"`, `"xml"` for
RDF/XML, `"nt"` or `"nquads"`, and the reader takes the same keyword:

```python
turtle_str = document.serialize(format="rdf", rdf_format="turtle")
loaded = pm.ProvDocument.deserialize(content=turtle_str, format="rdf", rdf_format="turtle")
```

```{important}
A syntax with named graphs, such as `"trig"` or `"nquads"`, keeps each bundle, and a triple
syntax such as `"turtle"` flattens every bundle into one graph, so keep the default TriG if
your document has bundles. {doc}`../reference/conformance` states the other limits of
PROV-O.
```

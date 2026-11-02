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
A triple syntax such as `"turtle"` loses which bundle each statement came from, so keep
the default TriG if your document has bundles. The PROV-O notes in
{doc}`../reference/conformance` say which syntaxes keep them.
```

## Limitations

{doc}`../reference/conformance` states the limits of PROV-O in C1, C10, C11 and C12 and in
its PROV-O notes.

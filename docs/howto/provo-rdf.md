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
Only quad-based syntaxes, `"trig"` and `"nquads"`, keep bundles as separate named graphs.
Triple-based syntaxes such as `"turtle"` and `"xml"` flatten every bundle into one graph
and lose which bundle each statement came from. Keep the default TriG if your document has
bundles.
```

## Limitations

Two relations that share an identifier and differ in a formal attribute cannot round-trip,
because PROV-O names a relation by its identifier; reading such RDF raises
`prov.serializers.provrdf.ProvRDFException`
({doc}`../reference/conformance`, C1). On the same page, C10 covers literals rdflib
rewrites on read, and C11 a decimal `NaN` beside a number, which rdflib cannot write.

The reader declares the source's own prefixes and the namespaces its names use, and an
unused declaration does not survive a round trip ({doc}`../reference/conformance`, PROV-O).

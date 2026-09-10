# Work with PROV-O (RDF)

[PROV-O](https://www.w3.org/TR/prov-o/) needs the `rdf` extra, which installs `rdflib`:

```bash
python -m pip install "prov[rdf]"
```

Two keywords are involved. `format="rdf"` selects PROV-O. `rdf_format` chooses the
concrete RDF syntax and defaults to `"trig"`.

## Serialize to a file

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

document.serialize("document.trig", format="rdf")  # rdf_format="trig" is the default
```

## Serialize to a string

```python
trig_str = document.serialize(format="rdf")
```

## Choose a different RDF syntax

`rdf_format` accepts any syntax `rdflib` can write, such as `"turtle"`, `"xml"` for
RDF/XML, `"nt"` or `"nquads"`:

```python
turtle_str = document.serialize(format="rdf", rdf_format="turtle")
print(turtle_str)
```

```{important}
Only quad-based syntaxes, `"trig"` and `"nquads"`, keep bundles as separate named graphs.
Triple-based syntaxes such as `"turtle"` and `"xml"` flatten every bundle into one graph
and lose which bundle each statement came from. Keep the default TriG if your document has
bundles.
```

## Deserialize from a file or stream

```python
loaded = pm.ProvDocument.deserialize("document.trig", format="rdf")
assert loaded == document
```

Pass the matching `rdf_format` when the input is not TriG:

```python
loaded = pm.ProvDocument.deserialize(content=turtle_str, format="rdf", rdf_format="turtle")
```

## Deserialize from a string

```python
loaded = pm.ProvDocument.deserialize(content=trig_str, format="rdf")
```

## Auto-detect the format with `prov.read()`

{py:func}`prov.read` tries PROV-O second, after PROV-JSON. See {ref}`auto-detect` in the
PROV-JSON guide for how detection works and when to pass `format=` instead.

```python
import prov

loaded = prov.read("document.trig")
assert loaded == document
```

## Common errors

Malformed RDF raises `rdflib`'s own parser error:

```python
try:
    pm.ProvDocument.deserialize(content="not rdf", format="rdf")
except Exception as e:
    print(f"{type(e).__name__}")
```

```text
BadSyntax
```

Two relations that share an identifier but differ in a formal attribute cannot round-trip
through PROV-O. Decoding such RDF raises `prov.model.ProvException`.
{doc}`../reference/conformance` explains why.

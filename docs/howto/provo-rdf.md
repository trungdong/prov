# Work with PROV-O (RDF)

[PROV-O](https://www.w3.org/TR/prov-o/) support needs the optional `rdflib` dependency:

```bash
python -m pip install "prov[rdf]"
```

The serialization format is selected with `format="rdf"`. A second, RDF-specific keyword,
`rdf_format`, chooses the concrete RDF syntax (`"trig"` by default) — do not confuse the
two.

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

## Choose a different RDF syntax

`rdf_format` accepts anything `rdflib` can serialize to, e.g. `"turtle"`, `"xml"`
(RDF/XML), `"nt"`, `"nquads"`:

```python
turtle_str = document.serialize(format="rdf", rdf_format="turtle")
print(turtle_str)
```

```{important}
Only quad-based syntaxes (`"trig"` — the default — and `"nquads"`) preserve **bundles** as
separate named graphs. Triple-based syntaxes such as `"turtle"` or `"xml"` flatten every
bundle's statements into a single graph, discarding which bundle each statement came from.
Stick with the default TriG if your document has bundles.
```

## Serialize to a string

```python
trig_str = document.serialize(format="rdf")
```

## Deserialize from a file or stream

```python
loaded = pm.ProvDocument.deserialize("document.trig", format="rdf")
assert loaded == document
```

Pass the matching `rdf_format` if the input is not TriG:

```python
loaded = pm.ProvDocument.deserialize(content=turtle_str, format="rdf", rdf_format="turtle")
```

## Deserialize from a string

```python
loaded = pm.ProvDocument.deserialize(content=trig_str, format="rdf")
```

## Auto-detect the format with `prov.read()`

PROV-O/RDF is the second format `prov.read()` tries (after PROV-JSON), so genuine RDF
content auto-detects reliably:

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

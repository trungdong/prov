# Work with PROV-N

```{important}
**PROV-N is write-only.** `prov` can produce [PROV-N](https://www.w3.org/TR/prov-n/) text,
but there is no parser: deserializing PROV-N raises `NotImplementedError`. If you need to
read a document back, save it in PROV-JSON, PROV-XML, or PROV-O/RDF instead.
```

PROV-N needs no extra dependency.

## Get the PROV-N text directly

{py:meth}`~prov.model.ProvBundle.get_provn` returns the notation as a string without going
through the serializer registry at all — this is the simplest way to print or inspect it:

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

print(document.get_provn())
```

## Serialize to a file

`format="provn"` goes through the same {py:meth}`~prov.model.ProvDocument.serialize` API
as the other formats, for consistency with tooling that dispatches on `format`:

```python
document.serialize("document.provn", format="provn")
```

## Serialize to a string

```python
provn_str = document.serialize(format="provn")
assert provn_str == document.get_provn()
```

## Deserializing raises `NotImplementedError`

There is no PROV-N reader, in the library or via `prov.read()`'s auto-detection:

```python
try:
    pm.ProvDocument.deserialize("document.provn", format="provn")
except NotImplementedError:
    print("PROV-N has no deserializer")
```

If your workflow needs a round trip, keep a PROV-JSON (or PROV-XML/RDF) copy alongside any
PROV-N output — see {doc}`provjson`.

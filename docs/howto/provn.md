# Work with PROV-N

```{important}
PROV-N is write-only. `prov` produces [PROV-N](https://www.w3.org/TR/prov-n/) text but has
no parser, so deserializing PROV-N raises `NotImplementedError`. Save a document in
PROV-JSON, PROV-JSONLD, PROV-XML or PROV-O if you need to read it back.
```

PROV-N needs no extra.

## Get the PROV-N text directly

{py:meth}`~prov.model.ProvBundle.get_provn` returns the notation as a string. This is the
simplest way to print or inspect a document:

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
as the other formats, for tooling that dispatches on `format`:

```python
document.serialize("document.provn", format="provn")
```

## Serialize to a string

```python
provn_str = document.serialize(format="provn")
assert provn_str == document.get_provn()
```

## Attribute order is stable

A record stores its attribute values in the order they were added, and every format
writes them in that order. Two runs of the same program produce the same text, so PROV-N
output is safe to use in doctests and golden files:

```python
document.entity("e2", [(pm.PROV_TYPE, "foo"), (pm.PROV_TYPE, "bar")])
print(document.get_provn())
# entity(e2, [prov:type="foo", prov:type="bar"])
```

## Deserializing raises `NotImplementedError`

There is no PROV-N reader, in the library or in `prov.read()`'s auto-detection:

```python
try:
    pm.ProvDocument.deserialize("document.provn", format="provn")
except NotImplementedError:
    print("PROV-N has no deserializer")
```

Keep a copy in another format alongside any PROV-N output if your workflow needs a round
trip. See {doc}`provjson`.

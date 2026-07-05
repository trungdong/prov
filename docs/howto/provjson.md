# Work with PROV-JSON

[PROV-JSON](https://openprovenance.org/prov-json/) is the default format used by
{py:meth}`~prov.model.ProvDocument.serialize`/{py:meth}`~prov.model.ProvDocument.deserialize`.
It needs no extra dependency — the serializer is always available.

## Serialize to a file

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
document.entity("e1")

document.serialize("document.json")  # format="json" is the default
```

## Serialize to a string

Omit `destination` (or pass `None`) to get the serialization back as a string:

```python
json_str = document.serialize()
print(json_str)
```

## Deserialize from a file or stream

```python
loaded = pm.ProvDocument.deserialize("document.json")
assert loaded == document
```

`source` also accepts an open stream:

```python
with open("document.json") as f:
    loaded = pm.ProvDocument.deserialize(f)
```

## Deserialize from a string

Use the `content` keyword instead of `source`:

```python
loaded = pm.ProvDocument.deserialize(content=json_str, format="json")
```

## Auto-detect the format with `prov.read()`

{py:func}`prov.read` tries every registered deserializer in turn — PROV-JSON, then
PROV-O/RDF, then PROV-N, then PROV-XML — until one succeeds, so it works without knowing
the format up front. PROV-JSON is tried first, so valid PROV-JSON content always
auto-detects correctly:

```python
import prov

loaded = prov.read("document.json")
assert loaded == document
```

Passing `format="json"` explicitly skips the trial-and-error and gives a proper traceback
if the content is not valid JSON.

## Common errors

Malformed JSON raises the standard library's decoder error, not a `prov`-specific
exception:

```python
try:
    pm.ProvDocument.deserialize(content="not json", format="json")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
```

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

Calling `prov.read()` without `format` on content that matches none of the registered
formats only raises the documented fallback `TypeError` ("Could not read from the
source...") if every deserializer it tries fails with one of `TypeError`, `ValueError`,
`AttributeError`, or `KeyError` — those are the only exceptions `read()` catches while it
tries formats in turn. In practice the RDF deserializer (tried before PROV-XML) usually
raises an `rdflib` parser error first, which is *not* in that list, so it propagates
immediately instead. Either way: pass `format=` explicitly if you want a predictable,
format-specific error.

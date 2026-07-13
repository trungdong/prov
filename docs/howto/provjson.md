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
PROV-O/RDF, then PROV-N, then PROV-XML — until one both succeeds and produces a non-empty
document, so it works without knowing the format up front. PROV-JSON is tried first, so
valid PROV-JSON content always auto-detects correctly:

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

Since 2.5.0, `prov.read()` swallows *every* candidate deserializer's failure during
auto-detection — including a candidate that raises, and a candidate that parses
successfully but yields an empty document (e.g. an empty file) — and always raises the
fallback `TypeError` ("Could not read from the source...") once every registered format has
been tried without success. Pass `format=` explicitly if you want a predictable,
format-specific error instead of that generic `TypeError`.

# Work with PROV-JSON

[PROV-JSON](https://www.w3.org/submissions/prov-json/) is the default format for
{py:meth}`~prov.model.ProvDocument.serialize` and
{py:meth}`~prov.model.ProvDocument.deserialize`. It needs no extra.

## Serialize to a file

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
document.entity("e1")

document.serialize("document.json")  # format="json" is the default
```

## Serialize to a string

Omit `destination`, or pass `None`, to get the serialization back as a string:

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

(auto-detect)=

## Auto-detect the format with `prov.read()`

{py:func}`prov.read` reads a document without being told its format. It tries every
registered deserializer in turn, in the order PROV-JSON, PROV-O (RDF), PROV-N, PROV-XML,
PROV-JSONLD, and returns the first result that is a non-empty document. PROV-JSON is tried
first, so valid PROV-JSON always auto-detects.

```python
import prov

loaded = prov.read("document.json")
assert loaded == document
```

A seekable stream, such as an open file or `io.StringIO`, is rewound between attempts. A
non-seekable stream is consumed by the first attempt, so pass `format=` for those.

Auto-detection swallows every deserializer's error. When no format succeeds it raises a
generic `TypeError`. Pass `format=` explicitly when you want the real error from one
deserializer.

## Common errors

Malformed JSON raises the standard library's decoder error:

```python
try:
    pm.ProvDocument.deserialize(content="not json", format="json")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
```

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

Valid JSON with the wrong structure raises
`prov.serializers.provjson.ProvJSONException`:

```python
from prov.serializers.provjson import ProvJSONException

try:
    pm.ProvDocument.deserialize(content='{"entity": "oops"}', format="json")
except ProvJSONException as e:
    print(f"{type(e).__name__}: {e}")
```

```text
ProvJSONException: The 'entity' value must be a JSON object; found str: 'oops'
```

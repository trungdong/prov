# Work with PROV-JSON

[PROV-JSON](https://www.w3.org/submissions/prov-json/) is the default format for
{py:meth}`~prov.model.ProvDocument.serialize` and
{py:meth}`~prov.model.ProvDocument.deserialize`. It needs no extra.

## Round trip

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
document.entity("e1")

document.serialize("document.json")  # format="json" is the default
loaded = pm.ProvDocument.deserialize("document.json")
assert loaded == document
```

{doc}`read-write` covers strings, streams and {py:func}`prov.read`, which tries PROV-JSON
first.

## Options

Keyword arguments go to `json.dump`, so `indent=2` pretty-prints:

```python
print(document.serialize(indent=2))
```

## Errors

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

## Limitations

None. Every concept in {doc}`../reference/conformance` round-trips through PROV-JSON.

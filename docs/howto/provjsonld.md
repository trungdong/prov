# Work with PROV-JSONLD

[PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/) is a W3C member submission
that represents the PROV Data Model in JSON-LD. Select it with `format="jsonld"`. It needs
no extra.

## Serialize to a file

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

document.serialize("document.jsonld", format="jsonld")
```

## Serialize to a string

```python
jsonld_str = document.serialize(format="jsonld", indent=2)
print(jsonld_str)
```

```text
{
  "@context": [
    {
      "@vocab": "http://example.org/",
      "@base": "http://example.org/"
    },
    "https://openprovenance.org/prov-jsonld/context.jsonld"
  ],
  "@graph": [
    {
      "@type": "Entity",
      "@id": "e1"
    },
    {
      "@type": "Activity",
      "@id": "a1"
    },
    {
      "@type": "Generation",
      "entity": "e1",
      "activity": "a1"
    }
  ]
}
```

The first entry of `@context` holds the document's namespace prefixes. The default
namespace appears as both `@vocab` and `@base`. `@vocab` expands unprefixed property
names, and `@base` expands unprefixed `@id` values such as `e1`, which would otherwise
resolve against the document's own location. The second entry references the submission's context, which resolves the
unprefixed types such as `Entity` and `Generation`. A named bundle nests inside the
top-level `@graph` as an object with `@type: "Bundle"`, its own `@context` and its own
`@graph`.

## Choose how the context is referenced

The `context` keyword controls the second entry of `@context`:

- `context="url"`, the default, references the submission's context by URL, as above. The
  output is smaller, but a consumer needs network access to process it as JSON-LD.
- `context="embed"` inlines the context object, so the document is self-contained:

  ```python
  document.serialize(format="jsonld", context="embed")
  ```

Any other value raises `ValueError`. Use `context="embed"` for output that will be
archived or processed offline.

## Deserialize from a file or stream

```python
loaded = pm.ProvDocument.deserialize("document.jsonld", format="jsonld")
assert loaded == document
```

`source` also accepts an open stream:

```python
with open("document.jsonld") as f:
    loaded = pm.ProvDocument.deserialize(f, format="jsonld")
```

## Deserialize from a string

```python
loaded = pm.ProvDocument.deserialize(content=jsonld_str, format="jsonld")
```

## Auto-detect the format with `prov.read()`

{py:func}`prov.read` tries PROV-JSONLD last, after the four other formats, so valid
PROV-JSONLD still auto-detects. See {ref}`auto-detect` in the PROV-JSON guide for how
detection works and when to pass `format=` instead.

```python
import prov

loaded = prov.read("document.jsonld")
assert loaded == document
```

## Input scope

The deserializer accepts the submission's compacted shape only. That is one JSON object per
PROV-DM statement under a top-level `"@graph"`, which is the shape this serializer writes.
It does not run a JSON-LD processor, so expanded or flattened JSON-LD is rejected even when
it is otherwise valid PROV-JSONLD. It does accept
[ProvToolbox](https://lucmoreau.github.io/ProvToolbox/)'s `prov:`-prefixed spellings of
the type and special terms, such as `"prov:Entity"` and `"prov:type"`.

Malformed or unrecognised JSON-LD raises
`prov.serializers.provjsonld.ProvJSONLDException`:

```python
from prov.serializers.provjsonld import ProvJSONLDException

try:
    pm.ProvDocument.deserialize(content='{"entity": {"ex:e1": {}}}', format="jsonld")
except ProvJSONLDException as e:
    print(f"{type(e).__name__}: {e}")
```

```text
ProvJSONLDException: A PROV-JSONLD document requires both "@context" and "@graph"; found keys ['entity']
```

Input that is not valid JSON at all raises the standard library's decoder error instead:

```python
try:
    pm.ProvDocument.deserialize(content="not json", format="jsonld")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
```

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## Limitations

The submission defines no term for `mentionOf`, PROV-DM's Mention relation, so
PROV-JSONLD cannot represent it. `serialize()` raises `ProvJSONLDException` for any
document containing a {py:class}`~prov.model.ProvMention` record:

```python
document = pm.ProvDocument()
document.add_namespace("ex", "http://example.org/")
document.mention("ex:e2", "ex:e1", "ex:b")
try:
    document.serialize(format="jsonld")
except ProvJSONLDException as e:
    print(f"{type(e).__name__}: {e}")
```

```text
ProvJSONLDException: PROV-JSONLD cannot represent mentionOf: the submission defines no Mention term; see docs/reference/conformance.md
```

This is a limitation of the submission, not of the library. {doc}`../reference/conformance`
records it alongside the equivalent PROV-O limitation.

## Media type and file extension

The submission associates PROV-JSONLD with the `application/ld+json` media type, and files
conventionally use the `.jsonld` extension. `prov` dispatches on neither. The format is
selected with `format="jsonld"` or auto-detected from content. Use them anyway for
interoperability with other JSON-LD tooling.

# Work with PROV-JSONLD

[PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/) is a W3C member submission
describing a JSON-LD representation of the PROV Data Model. It is selected with
`format="jsonld"`. Like PROV-JSON, it needs no extra dependency — the serializer is
implemented against the standard library only and is always available.

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
      "@vocab": "http://example.org/"
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

A document's registered namespace prefixes (and its default namespace, as `@vocab`) become
the first entry of `@context`; every unprefixed `@type` (`Entity`, `Activity`, `Generation`,
...) is resolved against the submission's context, referenced as the second entry. Named
bundles nest as `{"@type": "Bundle", "@id", "@context", "@graph"}` objects inside the
top-level `@graph`.

## Choose how the context is referenced

The `context` keyword controls how the submission's context (the second entry of
`@context`) is emitted:

- `context="url"` (the default) references it by URL, exactly as shown above. This is the
  smaller, more common output, but a consumer needs network access to resolve
  `https://openprovenance.org/prov-jsonld/context.jsonld` to fully process the document as
  JSON-LD.
- `context="embed"` inlines the vendored context object instead, so the document is fully
  self-contained:

  ```python
  document.serialize(format="jsonld", context="embed")
  ```

Any other value raises `ValueError`. Prefer `context="embed"` when the output needs to be
processed offline or archived without a dependency on the submission's context URL staying
reachable.

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

{py:func}`prov.read` tries every registered deserializer in turn — PROV-JSON, PROV-O/RDF,
PROV-N, PROV-XML, then PROV-JSONLD last — until one both succeeds and produces a non-empty
document:

```python
import prov

loaded = prov.read("document.jsonld")
assert loaded == document
```

Passing `format="jsonld"` explicitly skips the trial-and-error and gives a proper traceback
if the content is not valid PROV-JSONLD.

## Input scope

The deserializer only accepts the submission's canonical §4 *compacted* shape — one JSON
object per PROV-DM statement under a top-level `"@graph"`, exactly the shape this
serializer writes. It does not run general-purpose JSON-LD processing (no expansion,
flattening, or framing), so expanded or flattened JSON-LD that is otherwise valid
PROV-JSONLD is rejected. Malformed or unrecognised JSON-LD raises
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

Malformed JSON itself (not valid JSON at all) raises the standard library's decoder error,
not `ProvJSONLDException`:

```python
try:
    pm.ProvDocument.deserialize(content="not json", format="jsonld")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
```

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

The decoder additionally tolerates [ProvToolbox](https://lucmoreau.github.io/ProvToolbox/)'s
`prov:`-prefixed spellings of the type and special terms (`"prov:Entity"` alongside
`"Entity"`, `"prov:type"` alongside `"type"`), so documents produced by that reference
implementation read in without modification.

## Limitations

`mentionOf` (PROV-DM's Mention relation) cannot be represented: the submission defines no
JSON-LD term for it. `serialize()` raises `ProvJSONLDException` for any document containing
a `ProvMention` record:

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
ProvJSONLDException: PROV-JSONLD cannot represent mentionOf (None): the submission defines no Mention term; see docs/reference/conformance.md
```

This is a permanent limitation of the PROV-JSONLD submission, not a gap in this library; see
{doc}`../reference/conformance` for the full write-up alongside the equivalent PROV-O
limitation.

## Media type and file extension

The submission associates PROV-JSONLD with the `application/ld+json` media type; by
convention, files use the `.jsonld` extension, as in the examples above. `prov` does not
dispatch on either of these — the format is always selected via `format="jsonld"` or
auto-detected by content — but they are worth using for interoperability with other JSON-LD
tooling.

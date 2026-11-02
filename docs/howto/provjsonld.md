# Work with PROV-JSONLD

[PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/) is a W3C member submission
that represents the PROV Data Model in JSON-LD. Select it with `format="jsonld"`; it needs no extra.
The submission defines no Mention term, so a document with a
{py:class}`~prov.model.ProvMention` cannot be written or read.
{doc}`../reference/conformance` states the format's other limits and what its reader
accepts and drops.

## Round trip

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

document.serialize("document.jsonld", format="jsonld")
loaded = pm.ProvDocument.deserialize("document.jsonld", format="jsonld")
assert loaded == document
```

{doc}`read-write` covers strings, streams and {py:func}`prov.read`.

## Output shape

```python
print(document.serialize(format="jsonld", indent=2))
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

The first `@context` entry holds the namespace prefixes, with the default namespace as
`@vocab` and `@base`; the second references the submission's context. A named bundle nests
inside `@graph` as an object with `@type: "Bundle"`, its own `@context` and `@graph`.

## Choose how the context is referenced

The `context` keyword controls the second entry of `@context`. `context="url"`, the
default, references the submission's context by URL, so a consumer needs network access to
process the output as JSON-LD. `context="embed"` inlines the context object, for output
that is archived or processed offline. Any other value raises `ValueError`.

```python
document.serialize(format="jsonld", context="embed")
```

# Read and write documents

{py:meth}`~prov.model.ProvDocument.serialize` writes a document in any supported format,
{py:meth}`~prov.model.ProvDocument.deserialize` reads one when you know the format, and
{py:func}`prov.read` reads one when you do not. Every format takes the same three kinds of
destination and source: a path, a string and an open stream.

## Write to a file, a string or a stream

```python
import io
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

document.serialize("document.json")  # a path; format="json" is the default
text = document.serialize(format="provn")  # no destination: the text comes back
with io.StringIO() as stream:
    document.serialize(stream, format="xml")  # an open text or binary stream
    xml_text = stream.getvalue()
```

The format is never inferred from a file extension; pass `format=` for anything but
PROV-JSON. Keyword arguments beyond `format` go to the format's writer, such as `indent=2`
for the two JSON formats.

## Read from a file, a string or a stream

`source` takes a path or an open stream; `content` takes the text itself:

```python
loaded = pm.ProvDocument.deserialize("document.json")  # a path
loaded = pm.ProvDocument.deserialize(content=text, format="provn")  # the text
with open("document.json") as f:
    loaded = pm.ProvDocument.deserialize(f)  # an open stream
assert loaded == document
```

(auto-detect)=

## Detect the format with `prov.read()`

{py:func}`prov.read` reads a document without being told its format. It tries every
registered deserializer in turn, in the order PROV-JSON, PROV-O (RDF), PROV-N, PROV-XML,
PROV-JSONLD, and returns the first result that is a non-empty document.

```python
import prov

loaded = prov.read("document.json")
assert loaded == document
```

A seekable stream, such as an open file or `io.StringIO`, is rewound between attempts. A
non-seekable stream is consumed by the first attempt, so pass `format=` for those.

Auto-detection treats each deserializer's error as "not this format" and raises
`TypeError` when no format succeeds. When the content starts the way PROV-JSON, PROV-JSONLD
or PROV-N starts and that reader rejected it, the reader's own error is the `TypeError`'s
`__cause__`. Pass `format=` to get the error from one deserializer on its own. Keyword
arguments such as `profile` reach each candidate that declares them.

## Formats

| Format | `format=` | Extra | Read | Write | Usual extension | Media type |
| --- | --- | --- | --- | --- | --- | --- |
| [PROV-JSON](provjson) | `json` (default) | none | ✓ | ✓ | `.json` | `application/json` |
| [PROV-JSONLD](provjsonld) | `jsonld` | none | ✓ | ✓ | `.jsonld` | `application/ld+json` |
| [PROV-N](provn) | `provn` | none | ✓ | ✓ | `.provn` | `text/provenance-notation` |
| [PROV-XML](provxml) | `xml` | `xml` | ✓ | ✓ | `.provx` | `application/provenance+xml` |
| [PROV-O (RDF)](provo-rdf) | `rdf` | `rdf` | ✓ | ✓ | `.trig` by default | that of the RDF syntax, `application/trig` by default |

{doc}`../installation` lists the extras. `prov` dispatches on neither the extension nor
the media type; they are conventions for other tools.

## How errors surface

Each reader raises its format's own exception for input it cannot represent:
`ProvJSONException`, `ProvJSONLDException`, {py:class}`~prov.serializers.provn.ProvNSyntaxError`,
`ProvXMLException`, and {py:class}`~prov.model.ProvException` for PROV-O. Input that is not
well-formed in the underlying syntax raises the parsing library's own error first:
`json.JSONDecodeError` for the two JSON formats, `lxml`'s `XMLSyntaxError` and `rdflib`'s
`BadSyntax`.

```python
try:
    pm.ProvDocument.deserialize(content="not json", format="json")
except Exception as error:
    print(f"{type(error).__name__}: {error}")
```

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## Attribute order is stable

A record stores its attribute values in the order they were added, and every format
writes them in that order. Two runs of the same program produce the same text, so the
output is safe to use in doctests and golden files:

```python
document.entity("e2", [(pm.PROV_TYPE, "foo"), (pm.PROV_TYPE, "bar")])
print(document.get_provn())
# entity(e2, [prov:type="foo", prov:type="bar"])
```

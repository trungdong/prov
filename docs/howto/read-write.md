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

`source` takes a path or an open stream; `content` takes the text itself, as `str` or `bytes`:

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
{py:class}`~prov.serializers.ProvFormatNotDetected` when no format succeeds. It is a
`TypeError`, so `except TypeError` keeps working, and a
{py:class}`~prov.serializers.ProvSerializationError`. When the content starts the way
PROV-JSON, PROV-JSONLD or PROV-N starts and that reader rejected it, the reader's own error
is its `__cause__`. Pass `format=` to get the error from one deserializer on its own.
Keyword arguments such as `profile` reach each candidate that declares them.

## Formats

Every format reads and writes.

| Format | `format=` | Extra | Usual extension | Media type |
| --- | --- | --- | --- | --- |
| [PROV-JSON](provjson) | `json` (default) | none | `.json` | `application/json` |
| [PROV-JSONLD](provjsonld) | `jsonld` | none | `.jsonld` | `application/ld+json` |
| [PROV-N](provn) | `provn` | none | `.provn` | `text/provenance-notation` |
| [PROV-XML](provxml) | `xml` | `xml` | `.provx` | `application/provenance+xml` |
| [PROV-O (RDF)](provo-rdf) | `rdf` | `rdf` | `.trig` by default | that of the RDF syntax, `application/trig` by default |

{doc}`../installation` lists the extras. `prov` dispatches on neither the extension nor
the media type; they are conventions for other tools.

## How errors surface

Each reader raises its format's own exception for input it cannot represent:
`prov.serializers.provjson.ProvJSONException`,
`prov.serializers.provjsonld.ProvJSONLDException`,
{py:class}`~prov.serializers.provn.ProvNSyntaxError`,
`prov.serializers.provxml.ProvXMLException` and
`prov.serializers.provrdf.ProvRDFException`. All five derive from
{py:class}`~prov.serializers.ProvSerializationError`, which sits under `prov.Error`
beside {py:class}`~prov.model.ProvException`.

When the model rejects a record a reader builds, such as a value no PROV form holds or a
name that does not resolve, the reader raises its own error. The message names the record
and carries the model's sentence, and the model's exception is the error's `__cause__`.
Code that builds the record itself gets the model's exception.

Choose the `except` clause by what the code handles:

| Clause | Catches |
|---|---|
| `except ProvSerializationError` | a failure to read or write a document in any format, a reader's rejection of a record included, and the writers' error for a serializer with no document |
| `except ProvException` | a refusal by the model when code builds or changes a record, and `ProvNSyntaxError`, which stays a `ProvException` through 3.x |
| `except prov.Error` | both of the above, and `DoNotExist` |

Input that is not well-formed in the underlying syntax raises the parsing library's own
error, which is outside the base: `json.JSONDecodeError` for the two JSON formats,
`lxml`'s `XMLSyntaxError`, and the error of the rdflib parser for the chosen `rdf_format`,
`BadSyntax` for TriG and Turtle.

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

# Work with PROV-XML

[PROV-XML](https://www.w3.org/TR/prov-xml/) support needs the optional `lxml` dependency:

```bash
python -m pip install "prov[xml]"
```

## Serialize to a file

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
document.entity("e1")

document.serialize("document.xml", format="xml")
```

## Serialize to a string

```python
xml_str = document.serialize(format="xml")
print(xml_str)
```

## Force xsd:type attributes

By default `xsi:type` is only written for `prov:type`, `prov:location`, and `prov:value`,
matching the PROV-XML spec examples. Pass `force_types=True` to write it for every
non-`prov:` attribute too:

```python
xml_str_typed = document.serialize(format="xml", force_types=True)
```

## Deserialize from a file or stream

```python
loaded = pm.ProvDocument.deserialize("document.xml", format="xml")
assert loaded == document
```

## Deserialize from a string

```python
loaded = pm.ProvDocument.deserialize(content=xml_str, format="xml")
```

## Auto-detect the format with `prov.read()`

`prov.read()` tries each registered deserializer in turn — PROV-JSON, then PROV-O/RDF, then
PROV-N, then PROV-XML — treating any failure from a candidate as "not this format" and
moving on to the next one, stopping at the first deserializer that both succeeds and
produces a non-empty document. Valid PROV-XML therefore auto-detects, whether the source is
a file path or raw content:

```python
import prov

loaded = prov.read("document.xml")  # no format given
assert loaded == document
```

A seekable stream source (an open file object, `io.StringIO`, `io.BytesIO`, ...) is rewound
between auto-detection attempts, so it also auto-detects; a non-seekable stream is consumed
by the first candidate, so pass `format="xml"` explicitly for those.

Passing `format="xml"` explicitly skips the trial-and-error and gives the real traceback if
the content is not valid PROV-XML:

```python
loaded = prov.read("document.xml", format="xml")
assert loaded == document
```

## Common errors

Malformed XML raises `lxml`'s own syntax error, not a `prov`-specific exception:

```python
try:
    pm.ProvDocument.deserialize(content="not xml", format="xml")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
```

```text
XMLSyntaxError: Start tag expected, '<' not found, line 1, column 1 (<string>, line 1)
```

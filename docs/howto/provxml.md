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

`prov.read()` tries PROV-JSON, then PROV-O/RDF, then PROV-N, then PROV-XML, stopping at the
first deserializer that succeeds. In practice this means **plain PROV-XML content almost
never auto-detects**: the RDF (TriG) parser is tried before the XML one, and on real
PROV-XML input it fails with an `rdflib` syntax error rather than one of the exception
types `read()` catches (`TypeError`, `ValueError`, `AttributeError`, `KeyError`) — so that
error propagates before PROV-XML ever gets a turn:

```python
import prov

try:
    prov.read("document.xml")  # no format given
except Exception as e:
    print(f"{type(e).__name__}: autodetect did not reach the XML deserializer")

loaded = prov.read("document.xml", format="xml")  # works
assert loaded == document
```

Always pass `format="xml"` explicitly when reading PROV-XML; do not rely on autodetection
for this format.

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

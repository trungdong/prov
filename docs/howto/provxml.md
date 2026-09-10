# Work with PROV-XML

[PROV-XML](https://www.w3.org/TR/prov-xml/) needs the `xml` extra, which installs `lxml`:

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

## Write `xsi:type` on every attribute

By default `xsi:type` is written only for `prov:type`, `prov:location` and `prov:value`,
matching the examples in the PROV-XML specification. Pass `force_types=True` to write it
for every non-`prov:` attribute too:

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

{py:func}`prov.read` tries PROV-XML fourth, after PROV-JSON, PROV-O and PROV-N. Valid
PROV-XML auto-detects from a file path, raw content or a seekable stream. See
{ref}`auto-detect` in the PROV-JSON guide for how detection works and when to pass
`format=` instead.

```python
import prov

loaded = prov.read("document.xml")
assert loaded == document
```

## Common errors

Malformed XML raises `lxml`'s own syntax error:

```python
try:
    pm.ProvDocument.deserialize(content="not xml", format="xml")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
```

```text
XMLSyntaxError: Start tag expected, '<' not found, line 1, column 1 (<string>, line 1)
```

The parser does not resolve external DTD entities and never touches the network. A
document that relies on entity expansion reads back with those values empty.

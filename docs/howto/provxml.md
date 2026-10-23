# Work with PROV-XML

[PROV-XML](https://www.w3.org/TR/prov-xml/) needs the `xml` extra, which installs `lxml`:

```bash
python -m pip install "prov[xml]"
```

## Round trip

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
document.entity("e1")

document.serialize("document.provx", format="xml")
loaded = pm.ProvDocument.deserialize("document.provx", format="xml")
assert loaded == document
```

{doc}`read-write` covers strings, streams and {py:func}`prov.read`.

## Write `xsi:type` on every attribute

By default `xsi:type` is written only for `prov:type`, `prov:location` and `prov:value`,
matching the examples in the PROV-XML specification. Pass `force_types=True` to write it
for every non-`prov:` attribute too:

```python
xml_str_typed = document.serialize(format="xml", force_types=True)
```

## Limitations

An attribute name that is not an XML name is escaped on write and unescaped on read
({doc}`../reference/conformance`, C3). The parser does not resolve external DTD entities
and never touches the network, so a document that relies on entity expansion reads back
with those values empty.

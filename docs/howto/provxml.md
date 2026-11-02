# Work with PROV-XML

[PROV-XML](https://www.w3.org/TR/prov-xml/) needs the `xml` extra, which installs `lxml`:

```bash
python -m pip install "prov[xml]"
```

{doc}`../reference/conformance` states how the format escapes an attribute name that is not
an NCName and what its reader accepts.

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

# Work with PROV-N

`prov` reads and writes [PROV-N](https://www.w3.org/TR/prov-n/), the W3C notation for
PROV. Neither direction needs an extra.

## Get the PROV-N text directly

{py:meth}`~prov.model.ProvBundle.get_provn` returns the notation as a string. This is the
simplest way to print or inspect a document:

```python
import prov.model as pm

document = pm.ProvDocument()
document.set_default_namespace("http://example.org/")
e = document.entity("e1")
a = document.activity("a1")
document.wasGeneratedBy(e, a)

print(document.get_provn())
```

## Serialize to a file

`format="provn"` goes through the same {py:meth}`~prov.model.ProvDocument.serialize` API
as the other formats, for tooling that dispatches on `format`:

```python
document.serialize("document.provn", format="provn")
```

## Serialize to a string

```python
provn_str = document.serialize(format="provn")
assert provn_str == document.get_provn()
```

## Read a file or a string

{py:meth}`~prov.model.ProvDocument.deserialize` with `format="provn"` parses PROV-N text:

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn")
document = pm.ProvDocument.deserialize(content=provn_str, format="provn")
```

{py:func}`prov.read` detects PROV-N without a `format` argument, because a PROV-N
document starts with the `document` keyword:

```python
import prov

document = prov.read("document.provn")
```

## Choose a parsing profile

The parser accepts three dialects, selected with `profile`:

| Profile | Accepts |
| --- | --- |
| `strict` | The Recommendation grammar only, with at most one `default` declaration, before any `prefix` declaration, no declaration of `prov` or `xsd`, every statement before the first bundle, and no identifier or attribute block on `alternateOf`, `specializationOf` or `hadMember`. Mention is `prov:mentionOf`, as PROV-Links spells it, and `-` is not accepted where the grammar has a plain identifier. |
| `default` | The grammar plus the bare `mentionOf` keyword. The Recommendation has no Mention production, and every existing producer, `prov` and ProvToolbox included, writes the bare keyword, so refusing it would refuse every file in circulation. |
| `lenient` | As `default`. A statement that fails to parse, or that the model rejects, is skipped with a `ProvWarning` naming its line and column; a bundle whose identifier duplicates another is skipped whole. Extensibility expressions (`prefix:name(...)`) are skipped this way. |

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn", profile="strict")
```

Use `strict` to check that a document conforms to the Recommendation, `default` for
files other tools wrote, and `lenient` to salvage what a damaged file still holds. The
lenient profile recovers from parse errors and from statements the model rejects. A
tokenisation error, such as an unterminated string, IRI or comment, and a duplicate prefix
declaration still raise in every profile; a bundle whose identifier is already taken is
skipped whole under `lenient`. A statement that breaks a rule the strict and default
profiles enforce, such as an attribute named after one of its own arguments, fails to
parse too, so `lenient` skips it.

## Handle syntax errors

A syntax error raises {py:class}`~prov.serializers.provn.ProvNSyntaxError`, which
carries the line, the column and what the parser expected:

```python
from prov.serializers.provn import ProvNSyntaxError

try:
    pm.ProvDocument.deserialize(content="document\n  entity(ex:e1)\nendDocument", format="provn")
except ProvNSyntaxError as error:
    print(error.line, error.column, error.message)
    # 2 10 cannot resolve 'ex:e1': prefix 'ex' is not declared
```

With {py:func}`prov.read` and no `format`, a document that starts with `document` and
that the PROV-N reader rejects raises `TypeError` with the `ProvNSyntaxError` as its
`__cause__`; pass `format="provn"` to get the error on its own.

## Write strictly conformant output

`get_provn()` and `serialize(format="provn")` write the bare `mentionOf` keyword by
default, which ProvToolbox reads, and write an identifier or attribute block on
`alternateOf`, `specializationOf` and `hadMember` when a record carries one, which the
grammar does not allow. Pass `strict=True` to write `prov:mentionOf` and to drop those
identifiers and attribute blocks, each with a {py:class}`~prov.model.ProvWarning` that
names the record, so the output parses under the `strict` profile:

```python
document.serialize("document.provn", format="provn", strict=True)
```

## Large documents

The parser tokenises the whole document before it builds any record, so peak memory
during a parse is about 4 KiB per statement on CPython 3.12. A 100,000-statement,
7.5 MiB document peaks near 400 MiB. Throughput on a 2023 laptop is on the order of
20,000 statements per second, and `get_provn()` writes an order of magnitude faster than
that. Neither figure is a limit, but a document of several million statements needs
memory to match.

## Convert on the command line

`prov-convert` reads PROV-N with `-i provn`:

```bash
prov-convert -i provn -f json document.provn document.json
```

See {doc}`cli`.

## Attribute order is stable

A record stores its attribute values in the order they were added, and every format
writes them in that order. Two runs of the same program produce the same text, so PROV-N
output is safe to use in doctests and golden files:

```python
document.entity("e2", [(pm.PROV_TYPE, "foo"), (pm.PROV_TYPE, "bar")])
print(document.get_provn())
# entity(e2, [prov:type="foo", prov:type="bar"])
```

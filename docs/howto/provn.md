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
| `strict` | The W3C grammar only. Mention is written `prov:mentionOf`, as in the PROV-Links note. |
| `default` | The grammar plus the bare `mentionOf` keyword that `prov` and ProvToolbox write. The Recommendation has no Mention production; PROV-Links spells it `prov:mentionOf`. |
| `lenient` | As `default`. A statement that fails to parse is skipped with a {py:class}`~prov.model.ProvWarning` naming its line and column, and parsing resumes at the next statement. |

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn", profile="strict")
```

Use `strict` to check that a document conforms to the Recommendation, `default` for
files other tools wrote, and `lenient` to salvage what a damaged file still holds. The
lenient profile recovers from parse errors and from statements the model rejects; a
tokenisation error, such as an unterminated string, IRI or comment, still raises.

## Handle syntax errors

A syntax error raises {py:class}`~prov.serializers.provn_lexer.ProvNSyntaxError`, which
carries the line, the column and what the parser expected:

```python
from prov.serializers.provn import ProvNSyntaxError

try:
    pm.ProvDocument.deserialize(content="document\n  entity(ex:e1)\nendDocument", format="provn")
except ProvNSyntaxError as error:
    print(error.line, error.column, error.message)
    # 2 10 cannot resolve 'ex:e1': prefix 'ex' is not declared
```

With {py:func}`prov.read` and no `format`, a PROV-N error is swallowed like any other
candidate format's error; pass `format="provn"` to see it.

## Write strictly conformant output

`get_provn()` and `serialize(format="provn")` write the bare `mentionOf` keyword by
default, which ProvToolbox reads. Pass `strict=True` to write `prov:mentionOf` instead, so
the output parses under the `strict` profile:

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

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

A statement with an attribute block that is wider than 80 columns, indentation included,
wraps before the block. {py:meth}`~prov.model.ProvRecord.get_provn` gives the rule. Pass
`width` to change the limit, or `width=None` to never wrap:

```python
one_line = document.get_provn(width=None)
wider = document.serialize(format="provn", width=100)
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

{py:meth}`~prov.model.ProvDocument.deserialize` with `format="provn"` parses PROV-N text,
and {py:func}`prov.read` detects it with no `format` argument ({doc}`read-write`). The parser reads the whole document into memory first, so
memory grows with the number of statements.

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn")
document = pm.ProvDocument.deserialize(content=provn_str, format="provn")
```

## Choose a parsing profile

The parser accepts three dialects, selected with `profile`:

| Profile | Accepts |
| --- | --- |
| `strict` | The Recommendation grammar only, with at most one `default` declaration, before any `prefix` declaration, no declaration of `prov` or `xsd`, every statement before the first bundle, and no identifier or attribute block on `alternateOf`, `specializationOf` or `hadMember`. Mention is `prov:mentionOf`, as PROV-Links spells it, and `-` is not accepted where the grammar has a plain identifier. |
| `default` | The grammar plus the bare `mentionOf` keyword. The Recommendation has no Mention production, and every existing producer, `prov` and ProvToolbox included, writes the bare keyword, so refusing it would refuse every file in circulation. |
| `lenient` | As `default`. A statement that fails to parse, or that the model rejects, is skipped with a {py:class}`~prov.model.ProvWarning` naming its line and column; a bundle whose identifier duplicates another is skipped whole. Extensibility expressions (`prefix:name(...)`) are skipped this way. |

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn", profile="strict")
```

Use `strict` to check that a document conforms to the Recommendation, `default` for
files other tools wrote, and `lenient` to salvage what a damaged file still holds. A
tokenisation error, such as an unterminated string, IRI or comment, and a duplicate prefix
declaration raise in every profile.

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

## Convert on the command line

`prov-convert` reads PROV-N with `-i provn`:

```bash
prov-convert -i provn -f json document.provn document.json
```

See {doc}`cli`.

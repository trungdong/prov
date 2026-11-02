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
document.entity(
    "report",
    {
        "prov:label": "Quarterly sales report",
        "prov:type": "Report",
        "prov:location": "https://example.org/reports/2026/q3/sales.pdf",
    },
)

print(document.get_provn())
```

```text
document
  default <http://example.org/>

  entity(report,
         [prov:label="Quarterly sales report",
          prov:type="Report",
          prov:location="https://example.org/reports/2026/q3/sales.pdf"])
endDocument
```

A statement with an attribute block that is wider than 80 columns, indentation included,
wraps. The keyword, the identifier and the formal arguments stay on the first line, and the
attribute block follows with one attribute per line.
{py:meth}`~prov.model.ProvRecord.get_provn` gives the rule. Pass `width` to change the
limit, or `width=None` to never wrap:

```python
one_line = document.get_provn(width=None)
wider = document.serialize(format="provn", width=200)
```

## Write PROV-N

`serialize` takes `format="provn"` like every other format, and the keyword arguments
`width` and `strict` reach the PROV-N writer. {doc}`read-write` shows the path, string and
stream forms. A string and `get_provn()` agree:

```python
document.serialize("document.provn", format="provn")
provn_str = document.serialize(format="provn")
assert provn_str == document.get_provn()
```

`prov-convert` takes the same options with `-w`. See {doc}`../reference/prov-convert`.

## Read PROV-N

{py:meth}`~prov.model.ProvDocument.deserialize` with `format="provn"` parses PROV-N text,
and {py:func}`prov.read` detects it with no `format` argument ({doc}`read-write`). The
parser reads the whole document into memory first, so memory grows with the number of
statements.

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn")
document = pm.ProvDocument.deserialize(content=provn_str, format="provn")
```

## Handle syntax errors

A syntax error raises {py:class}`~prov.serializers.provn.ProvNSyntaxError`, which
carries the line, the column and what the parser expected:

```python
from prov.serializers.provn import ProvNSyntaxError

try:
    pm.ProvDocument.deserialize(content="document\n  entity(ex:e1)\nendDocument", format="provn")
except ProvNSyntaxError as error:
    print(error.line, error.column, error.message)
```

```text
2 10 the qualified name 'ex:e1' does not resolve, because its prefix 'ex' is not declared
```

(provn-profiles)=

## Choose a parsing profile

The parser accepts three dialects, selected with `profile`:

| Profile | Accepts | Use it |
| --- | --- | --- |
| `strict` | The Recommendation grammar only | to check that a document conforms |
| `default` | The grammar, plus the forms listed below | for files other tools wrote |
| `lenient` | As `default`, and skips what fails | to salvage what a damaged file holds |

```python
document = pm.ProvDocument.deserialize("document.provn", format="provn", profile="strict")
```

The Recommendation has no Mention production. Every existing producer writes the bare
keyword, `prov` and ProvToolbox included, so `default` and `lenient` accept it.

`strict` refuses these, which `default` and `lenient` accept:

- `mentionOf` without the `prov:` prefix. PROV-Links spells it `prov:mentionOf`.
- A `-` where the grammar has a plain identifier.
- A `default` declaration after a `prefix` declaration.
- A declaration of the prefix `prov` or `xsd` with its standard IRI. Any other IRI for
  either prefix raises under every profile.
- A statement after the first bundle.
- An identifier or attribute block on `alternateOf`, `specializationOf` or `hadMember`.

`lenient` skips a statement that fails to parse, or that the model rejects, with a
{py:class}`~prov.model.ProvWarning` that names its line and column. It also skips the whole
of a bundle whose identifier duplicates another. A `hadMember`, `alternateOf`,
`specializationOf` or `mentionOf` that is missing a party is skipped with a
`ProvWarning` under `default` too, and raises under `strict`.

A tokenisation error, such as an unterminated string, IRI or comment, raises in every
profile. So do a repeated `default` declaration and a duplicate prefix declaration.

## Syntax highlighting

Pygments finds the PROV-N lexer by name once `prov` is installed, under `provn` and
`prov-n`. An environment without Pygments gets it from the `pygments` extra,
`python -m pip install "prov[pygments]"`. This command highlights a file:

```bash
pygmentize -l provn -f html document.provn
```

Python callers fetch the lexer the same way:

```python
from pygments.lexers import get_lexer_by_name

lexer = get_lexer_by_name("provn")
```

Sphinx, MkDocs and Pelican look a code fence's language up by name, so a `provn` fence
highlights with no PROV-N-specific configuration. In a Jupyter notebook, one line in the
nbconvert configuration highlights cells that start with `%%provn` when the notebook is
exported. `prov` provides no `%%provn` cell magic, so such a cell does not run unless you
define the magic yourself:

```python
c.HighlightMagicsPreprocessor.languages = {"%%provn": "provn"}
```

## Edge cases

### Write strictly conformant output

`get_provn()` and `serialize(format="provn")` write the bare `mentionOf` keyword by
default, which ProvToolbox reads. They also write an identifier or attribute block on
`alternateOf`, `specializationOf` and `hadMember` when a record carries one, which the
grammar does not allow. Pass `strict=True` to write `prov:mentionOf` and to drop those
identifiers and attribute blocks. Each drop issues a {py:class}`~prov.model.ProvWarning`
that names the record. The output then parses under the `strict` profile:

```python
document.serialize("document.provn", format="provn", strict=True)
```

### Extensibility expressions

Every profile reads an [extensibility expression](https://www.w3.org/TR/prov-n/#extensibility),
a statement of the form `prefix:name(...)`. The parser drops the expression with a
{py:class}`~prov.model.ProvWarning` that names the predicate and its position.

The parser counts the brackets that an expression's arguments open, and not the `(` of the
expression itself. An expression nested more than 32 levels deep raises a
{py:class}`~prov.serializers.provn.ProvNSyntaxError`. Under `lenient`, the parser skips
that statement as it skips any statement that fails to parse.

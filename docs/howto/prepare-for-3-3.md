# Prepare for prov 3.3.0

`prov` 3.3.0 rejects some input that 3.2.x reads, and reads a few other inputs
differently. From 3.2.3, `prov` warns about each such input with a
{py:class}`~prov.model.ProvFutureRejectionWarning` where it reads the input, and
still reads it as before. This guide shows how to find every such input in your
documents and code.

## Turn the warnings into errors

`ProvFutureRejectionWarning` is a subclass of {py:class}`~prov.model.ProvWarning`.
A filter on the subclass stops at the first affected input and leaves the other
`ProvWarning`s alone, such as the statements the `lenient` PROV-N profile skips.

When running pytest:

```bash
pytest -W error::prov.model.ProvFutureRejectionWarning
```

In a pytest configuration:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error::prov.model.ProvFutureRejectionWarning"]
```

In code:

```python
import warnings

from prov.model import ProvFutureRejectionWarning

warnings.simplefilter("error", ProvFutureRejectionWarning)
```

Python's own `-W` option and the `PYTHONWARNINGS` environment variable cannot
name this class, because Python reads them before it can import `prov`. Use
pytest's option, a pytest configuration or a filter in code instead.

`prov` 3.3.0 keeps the class, so these filters keep working after the upgrade.

## Read the message

Each message ends with what 3.3.0 does instead, such as
"prov 3.3.0 will reject this". A message from a reader starts with the position
of the input: the line and column in PROV-N, or the record identifier and
attribute name in PROV-JSON.

## PROV-N declarations

| Warning | Example | Write instead |
|---|---|---|
| `'default' is declared twice in this scope` | `default <http://a/>` followed by `default <http://b/>` | One `default` declaration. `prov` 3.2 uses the last one. |
| `'…' is not a PROV-N prefix name` | `prefix _ <http://x/>`, `prefix a/b <http://x/>` | A prefix that starts with a letter, such as `prefix ab <http://x/>`. |
| `prefix 'xsi' is not declared` | `[xsi:type="ex:T"]` with no `prefix xsi` line | Add `prefix xsi <http://www.w3.org/2001/XMLSchema-instance>`. |
| `'default' follows a 'prefix' declaration` (strict profile) | `prefix ex <…>` followed by `default <…>` | The `default` declaration first. |
| `prefix 'prov' is predeclared` or `prefix 'xsd' is predeclared` (strict profile) | `prefix prov <http://www.w3.org/ns/prov#>` | No declaration. Both prefixes are predeclared. |

`prov` 3.2.2 and earlier wrote `xsi:` names without a `prefix xsi` line. Reading
such a file and writing it again with `prov` 3.2.3 adds the declaration.

## PROV-N whitespace

| Warning | Example | Write instead |
|---|---|---|
| `U+00A0 is not PROV-N whitespace` | `entity(ex:e)` followed by a no-break space | A space, tab, CR or LF. |
| `U+1680 is not PROV-N whitespace` | `entity(` followed by U+1680 and `ex:e)` | A space, tab, CR or LF. 3.3.0 reads U+1680 as part of a name. |

The same warning names any other Unicode whitespace character between tokens,
such as U+000C (form feed) or U+2028 (line separator). Whitespace inside a
string, an IRI or a comment does not warn.

## PROV-N statements

| Warning | Example | Write instead |
|---|---|---|
| `'prov:activity' names the 'activity' argument of 'wasGeneratedBy'` | `wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])` | The value as the argument, `wasGeneratedBy(ex:e, ex:a, -)`. |
| `a statement follows a bundle` (strict profile) | `entity(ex:f)` after `endBundle` | Every statement before the first bundle. |
| `'hadMember' has an identifier` (strict profile) | `hadMember(ex:m; ex:c, ex:e)` | `hadMember(ex:c, ex:e)`. |
| `'specializationOf' has an attribute block` (strict profile) | `specializationOf(ex:e2, ex:e1, [ex:k="x"])` | `specializationOf(ex:e2, ex:e1)`. |

The identifier and attribute-block warnings name whichever of `alternateOf`,
`specializationOf` and `hadMember` carries one. The `default` and `lenient`
profiles accept the three strict-profile constructs in this table without a
warning.

## Times

| Warning | Example | Write instead |
|---|---|---|
| `… has a timezone offset beyond ±14:00. prov 3.3.0 will reject this` | `activity(ex:a, 2012-01-01T00:00:00+15:00, -)` | The same instant with an offset from -14:00 to +14:00, such as `2011-12-31T23:00:00+14:00`. |
| `… has a timezone offset beyond ±14:00. prov 3.3.0 will keep it as a Literal` | `[ex:t="2011-11-16T16:05:33+15:00" %% xsd:dateTime]` | The same instant with an offset from -14:00 to +14:00, such as `"2011-11-16T15:05:33+14:00" %% xsd:dateTime`. |

The first warning covers every time of a statement: the time of a relation, an
activity's start and end times, and `prov:time` given as an attribute, from any
format or from code. An `xsd:dateTime` value of any other attribute is not a
time of the statement, so 3.3.0 does not reject it. 3.3.0 reads the value as a
`Literal` with its text, not as a `datetime`.

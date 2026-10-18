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
attribute name in PROV-JSON. A message about a language tag, a local part or
a Python value comes from the model, wherever the value was read or built, so
it names the value instead. So does a message about a qualified-name value
built in code or read from PROV-JSONLD or RDF. A message from `unified()`
starts with the identifier of the records it merges.

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

Each warning fires when the time is first asserted. `unified()`, `flattened()`,
`update()`, `add_record()` and copies of the record or the document do not warn
again.

## Language tags

| Warning | Example | Write instead |
|---|---|---|
| `the language tag 'en_US' of 'hi' is not a BCP 47 tag` | `Literal("hi", langtag="en_US")`, or `{"$": "hi", "lang": "en_US"}` in PROV-JSON | A BCP 47 tag, such as `en-US`. |
| `the language tag of 'hi' is empty` | `Literal("hi", langtag="")`, or `{"$": "hi", "lang": ""}` in PROV-JSON | No language tag. |

`prov` checks only the form of the tag. A tag is letters, followed by any
number of groups of letters and digits that each start with a hyphen. `prov`
does not look the tag up in the BCP 47 registry. The PROV-N reader already
rejects these tags.

## Local parts

| Warning | Example | Write instead |
|---|---|---|
| `the local part 'a b' of <http://example.org/a b> contains a character PROV-N cannot write` | `ex:a b`, `ex:a"b`, `ex:50%` | A local part without the character, such as `ex:a_b`, or with it percent-encoded, such as `ex:a%20b`, which is a different IRI. |

A local part cannot hold a space, a control character or another character
that PROV-N can write only by percent-encoding it, such as `"` or `|`. Nor can
it hold a `%` that two hexadecimal digits do not follow, or start with U+00B7
(middle dot), U+203F (undertie), U+2040 (character tie) or a combining mark
from U+0300 to U+036F. The PROV-N writer percent-encodes such a character, so
a PROV-N reader recovers a different IRI. The characters `= ' ( ) , : ; [ ]`
are written with a backslash instead, and do not warn.

The warning fires when the name is first built. `unified()`, `flattened()` and
copies of the document reuse the name and do not warn again. The XML reader
builds each occurrence of a name afresh, so it warns once for each.

## Python values

| Warning | Example | Write instead |
|---|---|---|
| `the value datetime.date(2026, 1, 1) of ex:due has type datetime.date. prov 3.3.0 will store it as a Literal of type xsd:date` | `{"ex:due": datetime.date(2026, 1, 1)}` | The `Literal` 3.3.0 stores, such as `Literal("2026-01-01", XSD["date"])`. |
| `the value Fraction(1, 3) of ex:ratio has type fractions.Fraction, which has no PROV form. prov 3.3.0 will reject this` | `{"ex:ratio": Fraction(1, 3)}` | A value with a PROV form, such as the `float` `1 / 3`, or a `Literal` with an XSD datatype. |

An attribute value has a PROV form when it is a `str`, `int`, `float`, `bool`,
`datetime.datetime`, `Identifier`, `QualifiedName`, `Literal` or record, or an
instance of a subclass of one of them. `prov` 3.2.x stores a value of any other
type as given, and no format can write it faithfully. 3.3.0 stores a value of a
type in the table below as a `Literal` of its datatype, and rejects a value of
any other type.

| Python type | 3.3.0 datatype |
|---|---|
| `decimal.Decimal` | `xsd:decimal` |
| `datetime.date` | `xsd:date` |
| `datetime.time` | `xsd:time` |
| `datetime.timedelta` | `xsd:duration` |
| `uuid.UUID` | `xsd:anyURI` |
| `bytes`, `bytearray`, `memoryview` | `xsd:base64Binary` |

In 3.3.0, a converted value reads back as the `Literal`, not as the Python
value. The readers never build these types unless a `json.load` option asks for
one. With `parse_float=decimal.Decimal`, for example, the PROV-JSON and
PROV-JSONLD readers read each bare JSON number with a fraction or an exponent
as a `Decimal`, and warn for each such number.

The warning fires when the value is first asserted. `unified()`, `flattened()`,
`update()`, `add_record()` and copies of the record or the document do not warn
again.

## Qualified names

| Warning | Example | Write instead |
|---|---|---|
| `the qualified name 'zz:x' does not resolve, because its prefix 'zz' is not declared; it is kept as a Literal` | `[ex:k='zz:x']` in PROV-N, `{"$": "zz:x", "type": "xsd:QName"}` in PROV-JSON, or `Literal("zz:x", XSD_QNAME)` in code, with no `zz` prefix | A declared prefix, such as `prefix zz <http://example.org/zz/>` in PROV-N or a `zz` entry in `"prefix"` in PROV-JSON. |
| `the qualified name 'http://example.org/x' does not resolve, because its prefix 'http' is not declared; it reads as ex:x` | `[ex:k="http://example.org/x" %% prov:QUALIFIED_NAME]` in PROV-N, or `"http://example.org/x"` as a PROV-JSON record key | The qualified name, `ex:x`. |
| `the qualified name 'not a name' does not resolve, because it has no prefix and no default namespace is declared; it is kept as a Literal` | `[ex:k="not a name" %% prov:QUALIFIED_NAME]` | A qualified name with a declared prefix, or a string if the value is not a name. |
| `the qualified name 'zz:a' does not resolve, because its prefix 'zz' is not declared; it is dropped` | `"prov:activity": "zz:a"` in PROV-JSON, or `"zz:a"` among the members of `hadMember` | A declared prefix. |

A value typed `prov:QUALIFIED_NAME` or `xsd:QName` holds a qualified name, and
so does `'zz:x'` in PROV-N. 3.3.0 splits its text at the first `:` and looks the
prefix up in the declarations in scope. `prov` 3.2.x keeps a value whose prefix
is not declared as a `Literal`. It also reads a full IRI typed
`prov:QUALIFIED_NAME`, or written `'…'` in PROV-N, as a name in a declared
namespace that the IRI starts with, so `http://example.org/x` reads as `ex:x`.
3.3.0 reads that text as the prefix `http` and rejects it, unless a prefix named
`http` is declared.

The PROV-JSON reader applies the same rule to a record key that is a full IRI.
It also warns when it drops a formal attribute value or a `hadMember` member
that does not resolve, such as `"prov:activity": "zz:a"`.

The PROV-N and PROV-JSON readers warn with the position of the value, and the
model does not warn again. The model warns about a value built in code or read
from another format when the value is first asserted, and names the attribute
after the value, as in `the qualified name 'zz:x' of ex:k does not resolve`. In
code, a plain string given as an identifier, such as
`bundle.entity("http://example.org/e1")`, still compacts in 3.3.0, and does not
warn.

## Unification

| Warning | Example | Write instead |
|---|---|---|
| `ex:assoc: an absent prov:plan means none, so it does not unify with ex:p; unified() merges the records and keeps ex:p. prov 3.3.0 will raise ProvUnificationError` | `wasAssociatedWith(ex:assoc; ex:a, ex:ag, ex:p)` and `wasAssociatedWith(ex:assoc; ex:a, ex:ag, -)` | The same plan on every record with that identifier, or a plan on none of them. |
| `ex:d: an absent prov:activity means none, so it does not unify with ex:a; …` | `wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, -, -)` and `wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)` | The same activity on every record with that identifier, or an activity on none of them. |
| `ex:d: an absent prov:generation on a derivation with no activity means none, so it does not unify with ex:g; …` | `wasDerivedFrom(ex:d; ex:e2, ex:e1, -, ex:g, -)` and `wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)` | The same generation on every record with that identifier, or the activity of the derivation on each. The same holds for `prov:usage`. |

`unified()` merges records that share an identifier, and an absent formal
attribute usually unifies with any value. PROV-CONSTRAINTS makes a few positions
non-expandable, where an absent value means "none" and unifies only with another
absent value. They are the plan of an association, the activity of a
derivation, and the generation and usage of a derivation that names no
activity. `wasRevisionOf`, `wasQuotedFrom` and `hadPrimarySource` are
derivations and follow the same rule. In 3.2.x `unified()` still merges an
absent value in one of these positions with a present one and keeps the present
value. 3.3.0 raises {py:class}`~prov.model.ProvUnificationError`.

`unified()` warns once for each set of records of one type that share an
identifier, at the first such position in the order of the statement's
arguments, which is where 3.3.0 raises.

`prov_to_graph()` and `prov_to_dot()` call `unified()`, so they warn about the
same documents. In 3.3.0 `prov_to_graph()` raises, and `prov_to_dot()` draws the
document as asserted, without merging any records.

## PROV-JSON

| Warning | Example | Write instead |
|---|---|---|
| `the key '…' is repeated in a JSON object` | `{"ex:k": "a", "ex:k": "b"}` | One key. For an attribute with several values, an array, `"ex:k": ["a", "b"]`. |
| `'…' is not an xsd:dateTime and is dropped` | `"prov:startTime": "2011-11-16"` | A full `xsd:dateTime`, such as `"2011-11-16T00:00:00"`, or no time. |
| `the value is written as an array` | `"prov:entity": ["ex:e"]` | The value, `"prov:entity": "ex:e"`. |
| `the value is null and is dropped` | `"ex:k": null` | No attribute. |
| `the value object has the unknown key '…'` | `{"$": "1", "datatype": "xsd:int"}` | Only `$`, `type` and `lang`, as in `{"$": "1", "type": "xsd:int"}`. |
| `the value object's "$" is …, not a string` | `{"$": 1}` | A string, as in `{"$": "1", "type": "xsd:int"}`. |
| `the datatype '…' does not resolve and is dropped` | `{"$": "1", "type": "foo:int"}` with no `foo` prefix | A declared prefix, such as `xsd:int`, or a `foo` entry in `"prefix"`. |

A number in `$` typed the way `prov` 2.x and earlier wrote it, an integer as
`xsd:int` or `xsd:long` or a number with a fraction or exponent as `xsd:double`,
does not warn.
`{"$": 1, "type": "xsd:int"}` and `{"$": 1.5, "type": "xsd:double"}` read in 3.3.0 as
they do now.

The repeated-key warning names only the key, because Python's JSON parser
reports no position for it.

Every other message starts with the record identifier and the attribute name,
as in `record 'ex:g', attribute 'prov:entity': the value is written as an array`.
A formal attribute is one of the record's arguments in PROV-N, such as
`prov:entity` or `prov:time`. The members of `hadMember` are an array by design
and do not warn.

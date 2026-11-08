# Attribute values and equality

This page covers how a record stores an attribute value, and when two records, bundles,
documents or values are equal.

(python-values)=

## Python values

A record stores each attribute value in the form shown below, and `get_attribute()` returns
a set of those stored forms. A `Decimal`, `date`, `time`, `timedelta`, `UUID`, `bytes`,
`bytearray`, `memoryview` or `Identifier` is stored as a {py:class}`~prov.model.Literal` of
its XSD datatype, and a record as its identifier. Every other type below keeps its Python
type. A subclass of a listed type counts as that type. A value of any other type, such as a
`Fraction` or a `list`, raises {py:class}`~prov.model.ProvValueError`. So does a value of a
listed type that has no lexical form.

| Python type | Datatype | Lexical form |
| --- | --- | --- |
| `str` | `xsd:string` | the text as given |
| `bool` | `xsd:boolean` | `true` or `false` |
| `int` | `xsd:int` within 32 bits, `xsd:long` within 64 bits, `xsd:integer` beyond | its digits |
| `float` | `xsd:double` | `repr()`, or `NaN`, `INF` or `-INF` |
| `datetime.datetime` | `xsd:dateTime` | `isoformat()`; an offset that is not a whole number of minutes becomes UTC, and one beyond ±14:00 is an error |
| `decimal.Decimal` | `xsd:decimal` | `format(value, "f")`, so `Decimal("1E+2")` is `100`; `NaN`, an infinity or a value too long to write is an error |
| `datetime.date` | `xsd:date` | `isoformat()` |
| `datetime.time` | `xsd:time` | `isoformat()`; an offset that is not a whole number of minutes or is beyond ±14:00 is an error |
| `datetime.timedelta` | `xsd:duration` | days, hours, minutes and seconds, such as `P1DT2H`, `-PT1H30M` or `PT0S` |
| `uuid.UUID` | `xsd:anyURI` | `urn:uuid:…` |
| `bytes`, `bytearray`, `memoryview` | `xsd:base64Binary` | standard base64 |
| {py:class}`~prov.identifier.Identifier` | `xsd:anyURI` | the IRI |
| {py:class}`~prov.identifier.QualifiedName` | `xsd:QName` | the prefixed name, resolved in the record's bundle |
| {py:class}`~prov.model.ProvRecord` | `xsd:QName` | the record's identifier |
| {py:class}`~prov.model.Literal` | its own | its own text |

A `Literal` built directly from a Python value keeps the datatype it is given, unless a
language tag overrides it, so a `bytes` value under `xsd:duration` is its base64 text under
that datatype. It stores three forms that the table does not cover. A `float` given the
datatype `xsd:decimal` is stored as its decimal text, so `0.1` gives `0.1`, `1e22` gives
`10000000000000000000000`, `nan` gives `NaN` and the infinities give `Infinity` and
`-Infinity`. A bytes-like value given the datatype `xsd:hexBinary` is stored as uppercase
hex, so `b"\xab\xcd"` gives `ABCD`. Any other value with no form in the table is stored
through `str()`, so a `list` gives `[1, 2]` and a `Fraction` gives `1/3`.

A `Literal` is kept as it is, except that one with the datatype and spelling prov writes
for a plain value, such as `Literal("5", XSD_INT)` for `5`, is stored as that value, and so
is an `xsd:string` `Literal` or an `xsd:dateTime` `Literal` with a valid text. A `None`
value is skipped.

(equality)=

## Equality

Records compare by type, identifier and attributes; a record without an identifier equals
only a record without one. Two attribute values are the same value when they have the same
datatype and the same value in that datatype's value space. `xsd:boolean`, `xsd:decimal`,
`xsd:double`, `xsd:float` and `xsd:integer` with its subtypes have a value space here,
every other datatype compares by text, and a text outside its datatype's lexical space
or a subtype's range compares as text. Those value spaces ignore leading and trailing
spaces, tabs, carriage returns and line feeds, so `Literal(" 5 ", XSD_INT)` is the value
`5`. An `xsd:float` is keyed as a Python `float`, so two texts that differ only beyond
single precision are two values. Language tags compare case-insensitively, so `Literal("a", None, "EN")` equals `Literal("a", None, "en")`.

A plain Python value takes the datatype the writers give it (see {ref}`python-values`), so
`5` and `Literal("05", XSD_INT)` are one value and `5` and `Literal("5", XSD_LONG)` are
two. A `NaN` is one value with itself. `hash()` follows `==` on records and literals. A
bundle compares as a set of records, not by its identifier; a document also matches its
bundles by identifier, and a bundle never equals a document.

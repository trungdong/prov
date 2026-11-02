# prov.model

`prov.model` is the in-memory object model for [PROV-DM](https://www.w3.org/TR/prov-dm/)
documents. A {py:class}`~prov.model.ProvDocument` contains
{py:class}`~prov.model.ProvBundle` objects, which hold records. Records are elements
(entities, activities, agents) and the relations between them. The namespace machinery
that builds and resolves their identifiers lives here too. The
{doc}`../tutorial/getting-started` walks through building a document with this API, and
the [PROV-DM Primer](https://www.w3.org/TR/prov-primer/) covers the concepts behind the
classes.

## Documents and bundles

```{eval-rst}
.. py:module:: prov.model

.. autoclass:: prov.model.ProvDocument
   :members:
   :show-inheritance:

   .. automethod:: plot

.. autoclass:: prov.model.ProvBundle
   :members:
   :show-inheritance:
```

## Records

Every statement is a {py:class}`~prov.model.ProvRecord`. Elements and relations share its
attribute, comparison and PROV-N methods, so those are documented once here.

```{eval-rst}
.. autoclass:: prov.model.ProvRecord
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvElement
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvRelation
   :members:
   :show-inheritance:
```

## Elements

```{eval-rst}
.. autoclass:: prov.model.ProvEntity
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvActivity
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvAgent
   :members:
   :show-inheritance:
```

## Relations

```{eval-rst}
.. autoclass:: prov.model.ProvGeneration
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvUsage
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvCommunication
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvStart
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvEnd
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvInvalidation
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvDerivation
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvAttribution
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvAssociation
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvDelegation
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvInfluence
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvSpecialization
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvAlternate
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvMention
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvMembership
   :members:
   :show-inheritance:
```

(equality)=

## Equality

Records compare by type, identifier and attributes; a record without an identifier equals
only a record without one. Two attribute values are the same value when they have the same
datatype and the same value in that datatype's value space. `xsd:boolean`, `xsd:decimal`,
`xsd:double`, `xsd:float` and `xsd:integer` with its subtypes have a value space here,
every other datatype compares by text, and a text outside its datatype's lexical space
or a subtype's range compares as text. An `xsd:float` is keyed as a Python `float`, so two
texts that differ only beyond single precision are two values. Language tags compare
case-insensitively, so `Literal("a", None, "EN")` equals `Literal("a", None, "en")`.

A plain Python value takes the datatype the writers give it (see {ref}`python-values`), so
`5` and `Literal("05", XSD_INT)` are one value and `5` and `Literal("5", XSD_LONG)` are
two. A `NaN` is one value with itself. `hash()` follows `==` on records and literals. A
bundle compares as a set of records, not by its identifier; a document also matches its
bundles by identifier, and a bundle never equals a document.

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

A `Literal` built directly from a Python value stores three forms that the table does not
cover. A `float` given the datatype `xsd:decimal` is stored as its decimal text, so `0.1`
gives `0.1`, `1e22` gives `10000000000000000000000`, `nan` gives `NaN` and the infinities
give `Infinity` and `-Infinity`. A bytes-like value given the datatype `xsd:hexBinary` is
stored as uppercase hex, so `b"\xab\xcd"` gives `ABCD`. Any other value with no form in the
table is stored through `str()`, so a `list` gives `[1, 2]` and a `Fraction` gives `1/3`.

A `Literal` is kept as it is, except that one with the datatype and spelling prov writes
for a plain value, such as `Literal("5", XSD_INT)` for `5`, is stored as that value, and so
is an `xsd:string` `Literal` or an `xsd:dateTime` `Literal` with a valid text. A `None`
value is skipped.

## Namespaces and literals

```{eval-rst}
.. autoclass:: prov.model.NamespaceManager
   :members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: prov.model.Literal
   :members:
   :show-inheritance:
```

## Type aliases

The signatures above name these aliases. {py:data}`~prov.model.AttributeValue` is the type
of the values a dict of attributes may hold; {doc}`../howto/typing` shows how to use it when
a type checker reports a call.

```{eval-rst}
.. The aliases are re-exports, and autodata reads an attribute docstring only from
   the module named in the directive, so their descriptions live here.

.. autodata:: prov.model.AttributeValue
   :no-value:

   A value accepted for a record attribute, before coercion. :ref:`python-values` lists
   what each type becomes.

.. autodata:: prov.model.RecordAttributesArg
   :no-value:

   The attributes of a record: a mapping from attribute name to value, or pairs of name
   and value in a sequence, a set or an iterator.

.. py:data:: OptionalID

   An identifier as a qualified name, a string or an ``Identifier``, or ``None``.

.. autodata:: prov.model.EntityRef
   :no-value:

   An entity, or its identifier as a qualified name, a string or an ``Identifier``.

.. autodata:: prov.model.ActivityRef
   :no-value:

   An activity, or its identifier.

.. autodata:: prov.model.AgentRef
   :no-value:

   An agent, or an entity or activity acting as one, or its identifier.

.. autodata:: prov.model.InfluencerRef
   :no-value:

   Any element, or its identifier.

.. autodata:: prov.model.GenerationRef
   :no-value:

   A generation record, or its identifier.

.. autodata:: prov.model.UsageRef
   :no-value:

   A usage record, or its identifier.

.. autodata:: prov.model.StreamOrPath
   :no-value:

   An open stream, or a path as a string, bytes or ``os.PathLike``.

.. py:data:: QualifiedNameCandidate

   A qualified name, or a string or ``Identifier`` the bundle resolves to one.

.. py:data:: DatetimeOrStr

   A ``datetime``, or an ``xsd:dateTime`` string parsed with :func:`~prov.model.parse_xsd_datetime`.

.. py:data:: NSCollection

   Namespaces to register: a mapping from prefix to URI, or ``Namespace`` objects.
```

## Functions and tables

```{eval-rst}
.. autofunction:: prov.model.parse_xsd_datetime

.. py:data:: PROV_REC_CLS

   Maps each record type to the class that represents it; the lookup
   :meth:`~prov.model.ProvBundle.new_record` and the deserializers use.
```

## Exceptions

{doc}`serializers` shows how these classes and the serialisation errors relate.

```{eval-rst}
.. autoclass:: prov.Error
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvException
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvWarning
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvFutureRejectionWarning
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvExceptionInvalidQualifiedName
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvElementIdentifierRequired
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvMissingFormalAttribute
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvValueError
   :members:
   :show-inheritance:

.. autoclass:: prov.model.ProvUnificationError
   :members:
   :show-inheritance:
```

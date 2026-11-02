# Upgrading to prov 3.3.0

Find the message `prov` 3.3.0 raised, or the input it reads differently from 3.2.3, in
the section for that kind of input. Each table gives the error, the input that causes it
and what to write instead, and the text after the table says what 3.2.3 did with the same
input. On `prov` 3.2.3, the page at
<https://prov.readthedocs.io/en/3.2.3/howto/prepare-for-3-3.html> shows how to turn that
release's warnings into errors and find these inputs before upgrading.

## Read the message

A message from a reader starts with the position of the input, which is the line and
column in PROV-N, or the record identifier and attribute name in PROV-JSON. A language
tag, a local part, a namespace prefix, a namespace IRI, a Python value, a qualified-name
value or a time offset beyond ±14:00 is rejected by the model, and the model's sentence
names the value. A reader's error names the record (the subject in PROV-O), or the
declaration. It carries that sentence, and its `__cause__` is the model's error. Code that
builds the value gets the model's error on its own. A message from `unified()` names the
identifier of the records it cannot merge.

With `prov.read()` and no `format=`, a PROV-JSON, PROV-JSONLD or PROV-N input (it starts
with `{` or the word `document`) that the reader rejects raises `ProvFormatNotDetected`, a `TypeError`, whose `__cause__` is the
reader's error with the rule and its position. That holds for a rejection by the model
too, since the reader wraps it. A PROV-XML or PROV-O input chains nothing, because its
start (`<`) does not name its reader. Pass `format=` to see the rule on its own.

Around a read, `except prov.serializers.ProvSerializationError` catches a reader's
rejection, and `except prov.Error` catches that and the model's refusal both. A syntax
error from the parsing library, such as `json.JSONDecodeError` under an explicit `format=`,
is outside both.
{doc}`read-write` has the `except` table, and {doc}`../reference/serializers` holds the
exception tree.

## PROV-N declarations

The `strict`, `default` and `lenient` profiles are in {ref}`provn-profiles`.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `'default' is declared twice in this scope` | [#508](https://github.com/trungdong/prov/issues/508) | `default <http://a/>` followed by `default <http://b/>` | One `default` declaration. `prov` 3.2.3 used the last one. |
| `'…' is not a PROV-N prefix name` | [#511](https://github.com/trungdong/prov/issues/511), [#729](https://github.com/trungdong/prov/issues/729) | `prefix _ <http://x/>`, `prefix a/b <http://x/>`, `prefix a\.b <http://x/>` | A prefix that starts with a letter, such as `prefix ab <http://x/>`, and holds no escape. |
| `'default' follows a 'prefix' declaration` (strict profile) | [#519](https://github.com/trungdong/prov/issues/519) | `prefix ex <…>` followed by `default <…>` | The `default` declaration first. |
| `prefix 'prov' is predeclared` or `prefix 'xsd' is predeclared` (strict profile) | [#519](https://github.com/trungdong/prov/issues/519) | `prefix prov <http://www.w3.org/ns/prov#>` | No declaration. Both prefixes are predeclared. |

Each is a `ProvNSyntaxError` at the declaration. 3.2.3 warned with the same text, except
that a prefix name that held an escape read with the escape removed, so `prefix a\.b`
declared `a.b`. An `xsi:` name with no `prefix xsi` line is under {ref}`xsi-prefix`.

## PROV-N whitespace

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `U+00A0 is not PROV-N whitespace` | [#509](https://github.com/trungdong/prov/issues/509) | `entity(ex:e)` followed by a no-break space | A space, tab, CR or LF. |

Each is a `ProvNSyntaxError` at the character, and the same error names any other Unicode
whitespace character between tokens, such as U+000C (form feed) or U+2028 (line
separator). U+1680 is a name character, so `entity(` followed by U+1680 and `ex:e)` fails
at the name instead. Whitespace inside a string, an IRI or a comment is unchanged.

## PROV-N escapes

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `escape '\u' needs four uppercase hex digits` | [#729](https://github.com/trungdong/prov/issues/729) | `"caf\u00e9"` | `"caf\u00E9"`. |

The same holds in an IRI, and `\U` takes eight uppercase hex digits. The error is a
`ProvNSyntaxError` at the escape under every profile. In 3.2.3 the reader took a lowercase
digit and read the escape as its character.

## PROV-N statements

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `'prov:activity' names the 'activity' argument of 'wasGeneratedBy'` | [#523](https://github.com/trungdong/prov/issues/523) | `wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])` | The value as the argument, `wasGeneratedBy(ex:e, ex:a, -)`. |
| `a statement follows a bundle` (strict profile) | [#519](https://github.com/trungdong/prov/issues/519) | `entity(ex:f)` after `endBundle` | Every statement before the first bundle. |
| `'hadMember' has an identifier` (strict profile) | [#519](https://github.com/trungdong/prov/issues/519) | `hadMember(ex:m; ex:c, ex:e)` | `hadMember(ex:c, ex:e)`. |
| `'specializationOf' has an attribute block` (strict profile) | [#519](https://github.com/trungdong/prov/issues/519) | `specializationOf(ex:e2, ex:e1, [ex:k="x"])` | `specializationOf(ex:e2, ex:e1)`. |

Each is a `ProvNSyntaxError` at the attribute name, the statement, the identifier or the
`[`. The identifier and attribute-block errors name whichever of `alternateOf`,
`specializationOf` and `hadMember` carries one. The `default` and `lenient` profiles
accept the three strict-profile constructs in this table. Under `lenient`, the first row
is a skipped statement with a `ProvWarning`, like any statement that fails to parse. In
3.2.3 a `lenient` read kept that statement and warned, so an `error` filter on
`ProvFutureRejectionWarning` raised then and does not now.

The strict writer drops what the strict reader rejects:

| Warning | Issue | Example | Write instead |
|---|---|---|---|
| `strict=True drops the identifier ex:m of hadMember(ex:c, ex:e), because PROV-N gives hadMember no identifier` | [#569](https://github.com/trungdong/prov/issues/569) | `document.new_record(PROV_MEMBERSHIP, "ex:m", {PROV_ATTR_COLLECTION: "ex:c", PROV_ATTR_ENTITY: "ex:e"})`, or `document.membership("ex:c", "ex:e")` followed by `add_attributes()`, written with `strict=True`. A `hadMember` read from PROV-JSON with several members gives every member its identifier and attributes. | The record without them, or `get_provn()` without `strict=True`, which keeps both. |

## Times

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `… has a timezone offset beyond ±14:00` | [#513](https://github.com/trungdong/prov/issues/513) | `activity(ex:a, 2012-01-01T00:00:00+15:00, -)`, or `datetime(2012, 1, 1, tzinfo=timezone(timedelta(hours=15)))` as any attribute value | The same instant with an offset from -14:00 to +14:00, such as `2011-12-31T23:00:00+14:00`. |
| `invalid xsd:dateTime '…'` (PROV-N), `expected an xsd:dateTime, found '…'` (PROV-JSON), `… is not an xsd:dateTime` (PROV-JSONLD), `Invalid value for attribute prov:startTime: …` (PROV-XML) or `Invalid xsd:dateTime value: '…'` (code) | [#514](https://github.com/trungdong/prov/issues/514) | `used(ex:a, ex:e, 2012-12-03T21:08:16.1234567Z)` | At most six fractional digits, `2012-12-03T21:08:16.123456Z`. 3.2.3 truncated the fraction to microseconds without a message. A typed `xsd:dateTime` value of an ordinary attribute keeps the `Literal`. PROV-O reads it truncated to microseconds. |

The offset error is a `ProvValueError` where the time is asserted, from code, for every
time of a statement and for a Python `datetime` as the value of any attribute. A reader
raises its format's error with it as the cause. 3.2.3 warned only for a time of a
statement. A typed `xsd:dateTime` value of an ordinary attribute with such an offset,
`[ex:t="2011-11-16T16:05:33+15:00" %% xsd:dateTime]`, is not an error. 3.3.0 keeps it as a
`Literal` with its text, where 3.2.3 read it as a `datetime` and warned. A PROV-N read
raises a `ProvNSyntaxError` at the statement, and the `lenient` profile skips the
statement with a `ProvWarning`.

A time string must be in the `xsd:dateTime` lexical form, `YYYY-MM-DDThh:mm:ss`, with
optional fractional seconds and `Z` or an `hh:mm` offset, so `2012-12-03T21:08Z`,
`20121203T210816Z` and `2012-W01-1T21:08:16Z` are not times. From code, such a string is a
`ProvException`. From code, PROV-JSON, PROV-JSONLD and PROV-XML, 3.2.3 read the other ISO
8601 forms Python reads and did not warn. Its PROV-N reader already rejected them.

## Language tags

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the language tag 'en_US' of 'hi' is not a BCP 47 tag` | [#472](https://github.com/trungdong/prov/issues/472) | `Literal("hi", langtag="en_US")`, or `{"$": "hi", "lang": "en_US"}` in PROV-JSON | A BCP 47 tag, such as `en-US`. |
| `the language tag of 'hi' is empty` | [#472](https://github.com/trungdong/prov/issues/472) | `Literal("hi", langtag="")`, or `{"$": "hi", "lang": ""}` in PROV-JSON | No language tag. |

Each is a `ProvValueError` when the `Literal` is built, from code or from a pickle written
by an earlier release. A reader raises its format's error with it as the cause. C5 and C6
on {doc}`../reference/conformance` give the form a tag takes. The PROV-N reader of 3.2.3
rejected these tags already.

## Local parts

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the local part 'a b' of <http://example.org/a b> contains a character PROV-N cannot write` | [#524](https://github.com/trungdong/prov/issues/524) | `ex:a b`, `ex:a"b` or `ex:50%` as a name in code, PROV-JSON, PROV-JSONLD, PROV-XML or PROV-O, or as the text of a `prov:QUALIFIED_NAME` value in PROV-N | A local part without the character, such as `ex:a_b`, or with it percent-encoded, such as `ex:a%20b`, which is a different IRI. |

The error is a `ProvExceptionInvalidQualifiedName` when the name is built, from code or
from a pickle written by an earlier release; its message is
`Invalid Qualified Name: ex:a b,` followed by the text in the table. A reader raises its
format's error with it as the cause. In PROV-N the sentence appears for a
`prov:QUALIFIED_NAME` value, as a `ProvNSyntaxError` at the statement, and the `lenient`
profile skips the statement with a `ProvWarning`. Bare `ex:a b` in PROV-N text is a syntax
error, as it was in 3.2.3. C4 on
{doc}`../reference/conformance` gives the rule. The same error rejects a `%` that two
hexadecimal digits do not follow, and a local part that starts with U+00B7 (middle dot),
U+203F (undertie), U+2040 (character tie) or a combining mark from U+0300 to U+036F.
3.2.3 percent-encoded such a character when it wrote PROV-N, so a PROV-N reader recovered
a different IRI. The characters `= ' ( ) , : ; [ ]` are written with a backslash instead,
and are accepted.

## Namespace prefixes

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the prefix '1a' is not a PN_PREFIX, so no format can write it` | [#668](https://github.com/trungdong/prov/issues/668) | `1a`, `_a`, the integer `1` in code, or a key holding `:`, such as `a:b`, in a PROV-JSONLD `@context` | A prefix that starts with a letter, such as `a1` or `ex`. |
| `the namespace IRI '@id' cannot start with '@'` | [#668](https://github.com/trungdong/prov/issues/668) | `prefix id <@id>` in PROV-N, `"id": "@id"` in a PROV-JSONLD `@context`, or `Namespace("id", "@id")` in code | An absolute IRI, such as `http://example.org/`. |
| `the namespace IRI 5 is not a string` (`… IRI None is not a string` for `null`) | [#668](https://github.com/trungdong/prov/issues/668) | `{"prefix": {"ex": 5}}` or `{"prefix": {"ex": null}}` in PROV-JSON, or `Namespace("ex", 5)` in code | The IRI as a string, such as `"http://example.org/"`. |
| `Not a valid URI to create a namespace.` | [#653](https://github.com/trungdong/prov/issues/653) | `{"prefix": {"ex": ""}}` or `{"prefix": {"default": ""}}` in PROV-JSON, or `{"@context": {"ex": ""}}` in PROV-JSONLD | An absolute IRI, or no entry. |

Each is a `ProvValueError` when the `Namespace` is built, from code or from a reader.
PROV-N refuses the declaration at its token with a `ProvNSyntaxError`, and the other
readers raise their format's error with the model's error as the cause, naming the prefix
and the IRI, as in `prefix 'ex', IRI 5: the namespace IRI 5 is not a string`. A PROV-XML
read raises it at the `bundleContent` element that declares the prefix, or at the first
name under a prefix the document element declares, and raises the model's refusal of an
`xmlns` on the document element at `<prov:document>`. C4 on
{doc}`../reference/conformance` gives the form a prefix takes.

3.2.3 accepted a prefix that is not a `PN_PREFIX` and wrote text that did not read back.
It also accepted an integer prefix and an IRI that starts with `@`. For a namespace IRI
that is not a string it raised `AttributeError`, and for a `null` or blank IRI in
PROV-JSON, or a blank IRI in PROV-JSONLD, a bare `ValueError`, which `except ValueError`
around a read caught. The format's error is not a `ValueError`. From code, the `Namespace`
constructor's refusal of a blank IRI is a `ProvValueError`, which `except ValueError`
still catches.

## Default namespaces

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `a namespace needs a prefix; a default namespace is set with set_default_namespace()` | [#649](https://github.com/trungdong/prov/pull/649) | `Namespace("", "http://example.org/")` | `document.set_default_namespace("http://example.org/")`. |
| `a default namespace is set with set_default_namespace(), not add_namespace()` | [#649](https://github.com/trungdong/prov/pull/649) | `document.add_namespace(other.get_default_namespace())` | `document.set_default_namespace(other.get_default_namespace().uri)`. |
| `Invalid Qualified Name: e1, the name 'e1' is in the default namespace http://dn/, which is not the default namespace in scope; declare a prefix for it` | [#473](https://github.com/trungdong/prov/issues/473) | `target.update(source)`, where `source` declares the default `http://dn/` and holds `entity(e1)`, and `target` declares another default or none; or a document-default name asserted in a bundle that declares its own default | A prefix for the IRI, such as `target.add_namespace("dn", "http://dn/")` before the `update()`. |
| `Invalid Qualified Name: http://dn/, the qualified name 'http://dn/' does not resolve, because the IRI http://dn/ is the default namespace and has no qualified-name form; declare a prefix for it` | [#473](https://github.com/trungdong/prov/issues/473) | `document.entity("http://dn/")` where `http://dn/` is the default namespace | An identifier with a local part, such as `document.entity("e1")`. |
| `cannot declare default <http://bn/>: this bundle holds e001, which would read as http://bn/e001` | [#573](https://github.com/trungdong/prov/issues/573) | `bundle = document.bundle("e001")` under the document's default namespace, then `bundle.set_default_namespace("http://bn/")` | A prefixed bundle identifier, such as `document.bundle("ex:e001")`. |
| `cannot declare prefix ex <http://other.org/>: this bundle holds ex:b2, which would read as http://other.org/b2` | [#573](https://github.com/trungdong/prov/issues/573) | `bundle = document.bundle("ex:b2")`, then `bundle.add_namespace("ex", "http://other.org/")` | Another prefix for the other IRI, such as `bundle.add_namespace("other", "http://other.org/")`. |
| `The "prefix" object declares two different default namespaces, under "" (…) and "default" (…)`, or `A @context entry declares two different default namespaces, under "@vocab" and ""` | [#654](https://github.com/trungdong/prov/issues/654) | `{"prefix": {"": "http://a/", "default": "http://b/"}}` in PROV-JSON, or `{"@vocab": "http://b/", "": "http://a/"}` in a PROV-JSONLD `@context` | One default entry, such as `"default": "http://b/"` in PROV-JSON or `"@vocab": "http://b/"` in PROV-JSONLD. |

From code, the first row is a `ProvValueError`, the third and fourth a
`ProvExceptionInvalidQualifiedName`, and the second, fifth and sixth a `ProvException`.
The last row is the reader's `ProvJSONException` or `ProvJSONLDException`. 3.2.3 accepted
a namespace with no prefix and made it the default of the first scope that met a name from
it. It made a copied default-namespace name the target's default when the target had none,
and wrote the name under a `dn` prefix it minted when the target had another default. It
raised `ProvElementIdentifierRequired` for an identifier equal to the default namespace
IRI. It accepted a declaration that changed a name the bundle held, so a prefixed bundle
identifier read back under the IRI the bundle bound the prefix to. For two default entries
in one object it took `"default"` or `@vocab` as the default, and wrote the `""` entry as
a nameless PROV-N `prefix`, or as `prefix _1` when the default entry came first, in a
PROV-JSON `prefix` object or a PROV-JSONLD context.

## Python values

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the value Fraction(1, 3) of ex:ratio has type fractions.Fraction, which has no PROV form` | [#482](https://github.com/trungdong/prov/issues/482) | `{"ex:ratio": Fraction(1, 3)}` | A value with a PROV form, such as the `float` `1 / 3`, or a `Literal` with an XSD datatype. |
| `the value Decimal('NaN') of ex:ratio has no xsd:decimal form` | [#482](https://github.com/trungdong/prov/issues/482) | `{"ex:ratio": Decimal("NaN")}` | A finite `Decimal`, or the `float` `nan`, which `xsd:double` holds. |
| `the datatype 'ex:type' of 'x' is not a QualifiedName` | [#705](https://github.com/trungdong/prov/issues/705) | `Literal("x", "ex:type")` | The resolved name, such as `Namespace("ex", "http://example.org/")["type"]`. |

The error is a `ProvValueError` where the value is asserted, and the datatype error is one
where the `Literal` is built, from code or from a pickle written by an earlier release.
{ref}`python-values` lists the Python types that have a PROV form, with the datatype and
lexical form each takes. A `Decimal`, `date`, `time`, `timedelta`, `UUID`, `bytes`,
`bytearray` or `memoryview` is stored as a `Literal` of its XSD datatype, as 3.2.3 said it
would be. 3.2.3 stored a value of any other type as given, and no format could write it
faithfully.

A converted value reads back as the `Literal`, not as the Python value, from
`get_attribute()` and from every format, except that an `xsd:duration` read from RDF comes
back in rdflib's normalised form, so a zero `timedelta` reads as `P0D`
([#620](https://github.com/trungdong/prov/issues/620),
{doc}`../reference/conformance`, C10). The readers never build these types unless a
`json.load` option asks for one. With `parse_float=decimal.Decimal`, the PROV-JSON and
PROV-JSONLD readers read each bare JSON number with a fraction or an exponent as a
`Decimal`, which is stored as an `xsd:decimal` `Literal`.

An `Identifier` given as a value is stored as a `Literal` typed `xsd:anyURI`, the form
every writer wrote for it and every reader now builds, so `isinstance(value, Identifier)`
no longer matches a stored value. Test a stored value with
`isinstance(value, Literal) and value.datatype == XSD_ANYURI`, and read its IRI from
`value.value`. A `QualifiedName` value is unchanged. 3.2.3 did not warn about this.

## Qualified names

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the qualified name 'zz:x' does not resolve, because its prefix 'zz' is not declared` | [#516](https://github.com/trungdong/prov/issues/516) | `[ex:k='zz:x']` in PROV-N, `{"$": "zz:x", "type": "xsd:QName"}` in PROV-JSON, or `Literal("zz:x", XSD_QNAME)` in code, with no `zz` prefix | A declared prefix, such as `prefix zz <http://example.org/zz/>` in PROV-N or a `zz` entry in `"prefix"` in PROV-JSON. |
| `the qualified name 'http://example.org/x' does not resolve, because its prefix 'http' is not declared` | [#553](https://github.com/trungdong/prov/issues/553), or [#551](https://github.com/trungdong/prov/issues/551) in PROV-JSON | `[ex:k="http://example.org/x" %% prov:QUALIFIED_NAME]` in PROV-N, `{"@value": "http://example.org/x", "@type": "xsd:QName"}` in PROV-JSONLD, or `"http://example.org/x"` as a PROV-JSON record key, attribute name, formal attribute, `hadMember` member or bundle key | The qualified name, `ex:x`. |
| `the qualified name 'zz:t' of ex:a does not resolve, because its prefix 'zz' is not declared` | [#673](https://github.com/trungdong/prov/issues/673) | `{"@value": "1", "@type": "zz:t"}` in PROV-JSONLD, with no `zz` entry in the `@context` | A `zz` entry in the `@context`, or a datatype in a declared namespace, such as `xsd:integer`. |
| `the qualified name '_:b1' of ex:a does not resolve, because its prefix '_' is reserved for blank nodes` | [#673](https://github.com/trungdong/prov/issues/673) | `{"@value": "1", "@type": "_:b1"}` in PROV-JSONLD | A datatype in a declared namespace, such as `xsd:integer`, since a blank node names no datatype. |
| `A value object for 'ex:a' must hold a string "@type"; found {'@value': '1', '@type': None}` | [#673](https://github.com/trungdong/prov/issues/673) | `{"@value": "1", "@type": null}` or a number, a boolean, a list or an object as the `@type` in PROV-JSONLD | A datatype's qualified name as a string, such as `"xsd:integer"`, or no `@type` for a plain string. |
| `A value object for 'ex:a' cannot hold both "@language" and "@type"; found {'@value': 'x', '@language': 'en', '@type': 'xsd:string'}` | [#673](https://github.com/trungdong/prov/issues/673) | `{"@value": "x", "@language": "en", "@type": "xsd:string"}` in PROV-JSONLD | `@language` alone for a language-tagged string, or `@type` alone for a typed value. |
| `Invalid Qualified Name: zz:e, the qualified name 'zz:e' does not resolve, because its prefix 'zz' is not declared` | [#727](https://github.com/trungdong/prov/pull/727) | `doc.entity("zz:e")`, `doc.used("ex:a", "ex:e", identifier="zz:u")`, `doc.bundle("zz:b")` or `doc.add_bundle(b, "zz:b")` in code, or an `"@id"` of `zz:e` in PROV-JSONLD, with no `zz` prefix declared. 3.2.3 raised `ProvElementIdentifierRequired` for an element, with `An identifier is missing. All PROV elements require a valid identifier.`, built the relation with no identifier and raised `ProvException` from `bundle()` | A declared prefix, or no identifier for a relation that has none. A PROV-JSONLD relation's `"@id": "_:u"` reads as one with no identifier. |
| `Invalid Qualified Name: zz:a, the qualified name 'zz:a' of prov:activity does not resolve, because its prefix 'zz' is not declared` | [#727](https://github.com/trungdong/prov/pull/727) | `doc.used("zz:a", "ex:e")` in code. `doc.entity("ex:e", {"zz:a": 1})` raises the same sentence without `of prov:activity`. 3.2.3 raised `Invalid Qualified Name: zz:a` alone | A declared prefix. |
| `the qualified name 'not a name' does not resolve, because it has no prefix and no default namespace is declared` | [#516](https://github.com/trungdong/prov/issues/516) | `[ex:k="not a name" %% prov:QUALIFIED_NAME]` | A qualified name with a declared prefix, or a string if the value is not a name. |
| `the qualified name 'zz:a' does not resolve, because its prefix 'zz' is not declared` | [#516](https://github.com/trungdong/prov/issues/516) | `"prov:activity": "zz:a"` in PROV-JSON, or `"zz:a"` among the members of `hadMember` | A declared prefix. |
| `the qualified name 'http://example.org/e' does not resolve, because its prefix 'http' is not declared` | [#553](https://github.com/trungdong/prov/issues/553) | `entity(http://example.org/e)` in PROV-N, or the IRI as a formal argument, an attribute name or a datatype | The qualified name, `ex:e`. |
| `the qualified name 'g1' does not resolve, because it has no prefix and no default namespace is declared` | [#622](https://github.com/trungdong/prov/pull/622) | `"wasGeneratedBy": {"g1": {…}}` in PROV-JSON with no `default` entry | A prefixed key, or `_:g1` for a relation with no identifier. |
| `the qualified name 'zz:x' does not resolve, because its prefix 'zz' is not declared` | [#677](https://github.com/trungdong/prov/issues/677) | `prov:id="zz:x"` or `<prov:type xsi:type="xsd:QName">zz:x</prov:type>` in PROV-XML with no `xmlns:zz` in scope, with or without an `xmlns` | A declared prefix, such as `xmlns:zz="http://example.org/zz/"` on the document element. |

In PROV-N the error is a `ProvNSyntaxError` at the value or the name, and the `lenient`
profile skips the statement with a `ProvWarning`. In PROV-JSON it is a `ProvJSONException`
that names the record and the attribute. From code it is a
`ProvExceptionInvalidQualifiedName` raised where the value is asserted, which names the
attribute after the value: `Invalid Qualified Name: zz:x, the qualified name 'zz:x' of ex:k
does not resolve, because its prefix 'zz' is not declared`. The PROV-JSONLD reader raises
`ProvJSONLDException`, which names the statement before the model's error, as in
`prov:Entity 'ex:e': Invalid Qualified Name: zz:x, …`, with that error as the cause. The
PROV-O reader raises `ProvRDFException` with it as the cause. The PROV-XML reader raises
`ProvXMLException` with it as the cause, naming the element and the line, for a name whose
prefix no element in scope declares and the document has not already registered, in a record
or bundle `prov:id`, a `prov:ref`, `xsd:QName` text, `xsi:type` or a reference given as
element text, for a name with no colon and no `xmlns` in scope, and for an empty `xsd:QName`
element.

`prov` 3.2.3 read a PROV-XML name whose prefix is not declared, in a `prov:id`, `prov:ref`,
`xsd:QName` text or `xsi:type`, under an `xmlns` as a local part of the default namespace,
so `zz:x` became the default namespace's `zz:x`, and without an `xmlns` raised a
`ProvXMLException` naming no element. It returned reference text as written for the model
to resolve against its registry, so a full IRI such as `http://example.org/e1` read as
`ex:e1` once an earlier name had registered `ex`, and a prefix the document element
declared that no earlier name had used was rejected. The full IRI is rejected now, and a
prefix declared in scope resolves. A file 3.2.3 wrote with a default-namespace local part
holding `:`, such as `a:b`, has that shape in `prov:id`, `prov:ref` and `xsd:QName` text.
Declare a prefix for the default namespace IRI, such as `xmlns:dn="http://example.org/"`,
and write the name under it, `dn:a:b`.

Whitespace around a name in `xsd:QName` text or reference text is stripped. 3.2.3 rejected
it in reference text and, in `xsd:QName` text, read it under an `xmlns` as part of a
default-namespace local part and raised a `ProvXMLException` without one. An empty
`xsd:QName` element raised a `TypeError` in 3.2.3.

A value typed `prov:QUALIFIED_NAME` or `xsd:QName` holds a qualified name, and so does
`'zz:x'` in PROV-N. `prov` splits its text at the first `:` and looks the prefix up in the
declarations in scope, the bundle's and then the document's, and never matches a declared
namespace IRI against the text. So `http://example.org/x` is the prefix `http`, rejected
unless a prefix named `http` is declared, and a prefix the document declares is found from
a bundle before the bundle's own namespaces could compact the text. A value whose prefix
is declared is stored as a `QualifiedName`, in code and from every format, and
`get_attribute()` returns it. In code, and for an `xsd:QName` value read from PROV-N or
PROV-O, 3.2.3 kept such a value as a `Literal`. `prov` 3.2.x kept a value whose prefix was
not declared as a `Literal`, and its PROV-JSON and PROV-JSONLD readers read a full IRI as a
name in a declared namespace the IRI starts with, as its PROV-N reader did for a
`prov:QUALIFIED_NAME` value. Its PROV-N reader kept an `xsd:QName` value with a full IRI as
a `Literal` and warned. The rows for #553 and #622 are
positions 3.2.3 read without a warning.

A formal attribute is one of the record's arguments in PROV-N, such as `prov:entity` or
`prov:activity`. The PROV-JSON reader applies the same rule to a record key, a bundle key,
an attribute name, a formal attribute value other than a time and a `hadMember` member.
3.2.3 dropped a formal attribute value or a `hadMember` member that did not resolve, with a
warning.

In PROV-JSONLD, the context marks the values of `type`, `role` and `location` as IRIs, so
a bare string there is an IRI, as a `{"@id": …}` node reference is. When a declared
namespace compacts the IRI, the value is that qualified name, and when none does, the
reader rejects it with `ProvJSONLDException`, as it rejects a node reference. 3.2.3 kept
that string as an `xsd:QName` `Literal` and warned that 3.3.0 would reject it, and read a
node reference no namespace compacts as an `Identifier`. A reference to a blank node,
`{"@id": "_:b1"}` or `"_:b1"`, names no record, so the reader drops that value with a
`ProvWarning`. An `xsd:QName` or `prov:QUALIFIED_NAME` value object holding a full IRI or
an undeclared prefix is rejected by the model, and the reader's error names the record.

In code, a plain string given as an identifier, such as
`bundle.entity("http://example.org/e1")`, still compacts when no prefix named `http` is
declared.

(xsi-prefix)=

## The `xsi` prefix

3.2.3 held `xsi` among its built-in prefixes, beside `prov` and `xsd`, so an `xsi:` name
resolved with no declaration. 3.3.0 keeps `prov` and `xsd` only, so outside PROV-XML an
`xsi:` name needs a declaration like any other prefix. For such a name the PROV-N reader of
3.2.3 warned `prefix 'xsi' is not declared`, and code, PROV-JSON and PROV-JSONLD accepted it
without a warning.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the qualified name 'xsi:type' does not resolve, because its prefix 'xsi' is not declared` | [#510](https://github.com/trungdong/prov/issues/510) | `[xsi:type="ex:T"]` in PROV-N with no `prefix xsi` line | Add `prefix xsi <http://www.w3.org/2001/XMLSchema-instance>`. |
| `Invalid Qualified Name: xsi:type, the qualified name 'xsi:type' does not resolve, because its prefix 'xsi' is not declared` | [#510](https://github.com/trungdong/prov/issues/510) | `doc.entity("ex:e", {"xsi:type": "ex:T"})` in code, or an `"xsi:type"` key in PROV-JSONLD, with no `xsi` prefix declared; in PROV-JSON the reader rejects the key with the record and attribute, as in "Qualified names" | A declaration, such as `doc.add_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")` or an `xsi` entry in `"prefix"` in PROV-JSON, or a name built from `prov.constants.XSI`. |
| `PROV-XML binds the prefix 'xsi' to <http://www.w3.org/2001/XMLSchema-instance>, but the document binds it to <…>` | [#510](https://github.com/trungdong/prov/issues/510) | `prefix xsi <http://other/>` in PROV-N, written to PROV-XML | Another prefix for that namespace. |

In PROV-N the error is a `ProvNSyntaxError` at the name. An `xsi:` identifier with no
declaration raises `ProvExceptionInvalidQualifiedName` in code, as the attribute name does,
and the PROV-JSONLD reader raises `ProvJSONLDException` with it as the cause. PROV-XML
documents are unchanged, because the PROV-XML codec reads and writes `xsi:type` itself.
The PROV-XML writer of 3.2.3 renamed a prefix `xsi` bound to another IRI to `xsi_1`.

`prov.model.DEFAULT_NAMESPACES` has no `xsi` key. Code that read
`DEFAULT_NAMESPACES["xsi"]` uses `prov.constants.XSI` instead.

`prov` 3.2.2 and earlier wrote `xsi:` names to PROV-N without a `prefix xsi` line, and 3.2.x
wrote them to PROV-JSON and PROV-JSONLD without an `xsi` entry in the prefix map. Add the
declaration for `http://www.w3.org/2001/XMLSchema-instance` to such a file before reading
it. For PROV-N, `prov` 3.2.3 also adds the line when it reads the file and writes it again,
so an environment that still has 3.2.3 can convert the file before the upgrade.

## Unification

`prov` 3.3.0 raises {py:class}`~prov.model.ProvUnificationError` for each of these. The
message starts with the identifier of the records that do not unify.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `ex:assoc: an absent prov:plan means none, so it does not unify with ex:p` | [#547](https://github.com/trungdong/prov/issues/547) | `wasAssociatedWith(ex:assoc; ex:a, ex:ag, ex:p)` and `wasAssociatedWith(ex:assoc; ex:a, ex:ag, -)` | The same plan on every record with that identifier, or a plan on none of them. |
| `ex:d: an absent prov:activity means none, so it does not unify with ex:a` | [#547](https://github.com/trungdong/prov/issues/547) | `wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, -, -)` and `wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)` | The same activity on every record with that identifier, or an activity on none of them. |
| `ex:d: an absent prov:generation on a derivation with no activity means none, so it does not unify with ex:g` | [#547](https://github.com/trungdong/prov/issues/547) | `wasDerivedFrom(ex:d; ex:e2, ex:e1, -, ex:g, -)` and `wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)` | The same generation on every record with that identifier, or the activity of the derivation on each. The same holds for `prov:usage`. |

{doc}`../explanation/unification-flattening` gives the positions where an absent value
means none and unifies only with another absent value. `wasRevisionOf`, `wasQuotedFrom`
and `hadPrimarySource` are derivations and follow the same rule. `prov` 3.2.3 merged an
absent value in one of these positions with a present one, kept the present value and
warned.

`unified()` raises for the first such position in the order of the statement's
arguments. A conflict between two present values, in any position, raises first.

`prov_to_graph()` flattens the document and then calls `unified()`, so it raises for the
same documents and for a document whose bundles disagree about a shared identifier.
`prov_to_dot()` draws such a document as asserted, without merging any records.

## Membership

`prov` 3.3.0 raises {py:class}`~prov.model.ProvException` for this call.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `Cannot have more than one value for attribute prov:entity` | [#700](https://github.com/trungdong/prov/issues/700) | `add_attributes([(PROV_ATTR_COLLECTION, "ex:c"), ("prov:entity", "ex:e1"), ("prov:entity", "ex:e2")])` on a `hadMember` record | One `hadMember` per entity. |

A PROV-XML `prov:hadMember` with several `<prov:entity>` children reads as one record per
entity, each with the element's identifier and attributes, as PROV-JSON and PROV-JSONLD
already read a list, where 3.2.3 read one record holding every entity.

## Relations missing a party

`prov` 3.3.0 raises {py:class}`~prov.model.ProvMissingFormalAttribute`, a
{py:class}`~prov.model.ProvException`, for this call.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `hadMember requires a value for prov:entity` | [#710](https://github.com/trungdong/prov/issues/710) | `doc.membership("ex:c", None)` | Both parties, or no record. |

Every reader except the PROV-N `strict` profile skips a `hadMember`, `alternateOf`,
`specializationOf` or `mentionOf` that is missing a party with a
{py:class}`~prov.model.ProvWarning`, and the rest of the document reads. The `strict`
profile raises a `ProvNSyntaxError`. A `mentionOf` may still omit its bundle, and
PROV-JSONLD has no term for `mentionOf`, so it cannot carry one. A document whose only
statements are such relations reads as empty, so {py:func}`prov.read` without a `format`
cannot detect it, and passing `format=` reads it with the warnings.

## Bundles

`prov` 3.3.0 raises {py:class}`~prov.model.ProvException` for this call, and 3.2.3 did not
warn about it.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the bundle belongs to another document; a bundle is not moved between documents` | [#649](https://github.com/trungdong/prov/pull/649) | `d2.add_bundle(d1.bundle("ex:b"))` | Build the bundle in its target document, or `update()` a fresh bundle of the target document from it. `update()` registers every prefixed namespace by itself. A bundle whose bare names use a default namespace needs that default declared first, on the target document or on the fresh bundle, where it was declared in the source. {doc}`graphics` shows this in its "Draw one bundle" section. |

## Equality

`==` on records, bundles, documents and `Literal` values follows one rule in 3.3.0, and
3.2.3 did not warn about any of these changes. Code that compares documents, holds records
in a set or asserts the type `get_attribute()` returns may see a different result.

| Compared | 3.2.3 | 3.3.0 |
|---|---|---|
| A relation without an identifier and the same relation with one | equal when the anonymous one is on the left | never equal ([#525](https://github.com/trungdong/prov/issues/525)) |
| A document and a copy with an extra bundle | equal from the left, unequal from the right | unequal from either side |
| `Literal("05", XSD_INT)` and `Literal("5", XSD_INT)`; `"+5"` and `"5"` as `xsd:long`; `"05"` and `"5"` as `xsd:integer` or `xsd:short`; `"1e0"` and `"1.0E0"` as `xsd:float` | two values | one value ([#527](https://github.com/trungdong/prov/issues/527)) |
| `"1e1"` and `"10"` as `xsd:decimal` | one value, through `Decimal()` in the caller's context | two values, because `"1e1"` is outside the lexical space and compares as text ([#593](https://github.com/trungdong/prov/issues/593), [#594](https://github.com/trungdong/prov/issues/594), [#595](https://github.com/trungdong/prov/issues/595)) |
| `NaN` and `NaN` as `xsd:double`, in a record | two values | one value |
| `"True"` or `"TRUE"` as `xsd:boolean`, `"inf"` as `xsd:double`, `" 5"` or `"1_000"` as `xsd:int` | read as `True`, `inf`, `5`, `1000` | kept as a `Literal` with its text, which compares as text |
| `get_attribute()` on `"05" %% xsd:int` or `"1" %% xsd:boolean` | `5`, `True` | `Literal("05", XSD_INT)`, `Literal("1", XSD_BOOLEAN)`; PROV-O still reads `5` and `True` |
| `Literal(True).value`, `Literal(float("inf")).value`, `Literal(Decimal("1E+2"), XSD_DECIMAL).value`, `Literal(datetime(2012, 1, 1), XSD_DATETIME).value` | `"True"`, `"inf"`, `"1E+2"`, `"2012-01-01 00:00:00"` | `"true"`, `"INF"`, `"100"`, `"2012-01-01T00:00:00"` |
| A PROV-O relation written as a blank node, under a default namespace | identifier from the blank node's label | no identifier |
| `unified()` on two equal statements, such as two `hadMember(ex:m; ex:c, ex:e)` | both kept | one kept ([#548](https://github.com/trungdong/prov/issues/548), [#124](https://github.com/trungdong/prov/issues/124)) |

{ref}`equality` gives the rule. `prov-compare` applies the same `==`, so its exit code
changes for the same documents.

`get_records(ProvEntity)` returns a list where 3.2.3 returned a one-shot iterator
([#491](https://github.com/trungdong/prov/issues/491)); write `next(iter(...))` to take
the first record.

## PROV-JSON

`prov` 3.3.0 raises `ProvJSONException` for each of these. The message starts with the
record identifier and the attribute name, as in `record 'ex:g', attribute 'prov:entity':
the value is written as an array`; a repeated key names only the key, because Python's
JSON parser reports no position for it.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the key '…' is repeated in a JSON object` | [#532](https://github.com/trungdong/prov/issues/532) | `{"ex:k": "a", "ex:k": "b"}` | One key. For an attribute with several values, an array, `"ex:k": ["a", "b"]`. |
| `expected an xsd:dateTime, found '…'` | [#555](https://github.com/trungdong/prov/issues/555) | `"prov:startTime": "2011-11-16"` | A full `xsd:dateTime`, such as `"2011-11-16T00:00:00"`, or no time. |
| `the value is written as an array` | [#531](https://github.com/trungdong/prov/issues/531) | `"prov:entity": ["ex:e"]` | The value, `"prov:entity": "ex:e"`. The members of `hadMember` are an array by design. |
| `the value is null` | [#528](https://github.com/trungdong/prov/issues/528) | `"ex:k": null`, or `"prov:activity": null` | No attribute. |
| `the value is …, not a qualified name` | [#597](https://github.com/trungdong/prov/issues/597) | `"prov:activity": 5` | A qualified name, as in `"prov:activity": "ex:a"`, or no attribute. |
| `the value object has the unknown key '…'` | [#529](https://github.com/trungdong/prov/issues/529) | `{"$": "1", "datatype": "xsd:int"}` | Only `$`, `type` and `lang`, as in `{"$": "1", "type": "xsd:int"}`. |
| `the value object's "$" is …, not a string` | [#529](https://github.com/trungdong/prov/issues/529) | `{"$": 1}` | A string, as in `{"$": "1", "type": "xsd:int"}`. |
| `the value object's "type" is …, not a string` | [#552](https://github.com/trungdong/prov/issues/552) | `{"$": "1", "type": 5}` | A qualified name, as in `{"$": "1", "type": "xsd:int"}`. |
| `the qualified name '…' does not resolve, because its prefix '…' is not declared` | [#552](https://github.com/trungdong/prov/issues/552) | `{"$": "1", "type": "foo:int"}` with no `foo` prefix | A declared prefix, such as `xsd:int`, or a `foo` entry in `"prefix"`. |
| `record 'zz:e': the qualified name 'zz:e' does not resolve, because its prefix 'zz' is not declared` | [#551](https://github.com/trungdong/prov/issues/551) | `"entity": {"zz:e": {}}`, or `"zz:k": "v"` as an attribute, with no `zz` prefix | A `zz` entry in `"prefix"`, such as `"zz": "http://example.org/zz/"`. |

For a record key or an attribute name whose prefix is not declared, 3.2.3 raised the
model's `ProvElementIdentifierRequired` or `ProvExceptionInvalidQualifiedName`.
`ProvJSONException` is not a `ProvException`, so `except ProvException` around the read no
longer catches it.

A number in `$` typed the way `prov` 2.x and earlier wrote it still reads. That is an
integer as `xsd:int` or `xsd:long`, or a number with a fraction or exponent as
`xsd:double`, in a value object with no `lang`, so `{"$": 1, "type": "xsd:int"}` and
`{"$": 1.5, "type": "xsd:double"}` read as they did.

The error for a value that is not a qualified name covers a `hadMember` member and a
formal attribute other than a time. A time written as a value object goes through the
value-object checks first, so an unknown key, a `$` or `type` that is not a string, or
an undeclared datatype gives the message in the table; a value object of any other
datatype, or with a `lang`, is not an `xsd:dateTime`.

A record key has no attribute, so its message starts with `record 'ex:g'` and a colon.
A bundle key starts with `bundle 'ex:b'` and a colon.

## PROV-JSONLD

`prov` 3.3.0 raises `ProvJSONLDException` for each of these.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the key 'ex:k' is repeated in a JSON object` | [#532](https://github.com/trungdong/prov/issues/532) | `"ex:k": ["a"], "ex:k": ["b"]` in one node object | One key holding every value, `"ex:k": ["a", "b"]`. |
| `prov:Activity 'ex:a': The 'startTime' attribute is not an xsd:dateTime: '2011-11-16'` | [#514](https://github.com/trungdong/prov/issues/514) | `"startTime": "2011-11-16"` on a `prov:Activity` | A full `xsd:dateTime`, such as `"2011-11-16T00:00:00"`, or no time. |

The repeated-key message names only the key, because Python's JSON parser reports no
position for it. 3.2.3 kept the last value of a repeated key without a message, and read a
statement whose formal time it could not parse without that time.

## PROV-XML

`prov` 3.3.0 raises `ProvXMLException` for this input.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `the name "e1" is under an xmlns declaration (http://inner.org/) on an element, which has no scope in PROV; declare the default on the document or the bundle, or use a prefix` | [#649](https://github.com/trungdong/prov/pull/649) | `<prov:entity prov:id="e1" xmlns="http://inner.org/"/>` | The `xmlns` on `prov:document` or `prov:bundleContent`, or a prefix, as in `xmlns:in="http://inner.org/"` and `prov:id="in:e1"`. |

3.2.3 made that namespace the default of the first scope that met it.

The PROV-XML reader also reads three inputs differently:

| Read | Issue | 3.2.3 | 3.3.0 |
|---|---|---|---|
| An `xmlns` on `prov:document` that no name uses | [#649](https://github.com/trungdong/prov/pull/649) | dropped | the document's default namespace, which the PROV-JSON, PROV-JSONLD, PROV-N and PROV-XML writers declare |
| An `xmlns:un` on `prov:bundleContent` that no name uses | [#649](https://github.com/trungdong/prov/pull/649) | dropped | registered on the bundle, so `bundle.get_registered_namespaces()` lists it and the writers declare it inside the bundle |
| `xsi:type=":t"` under an `xmlns`, the form 3.2.3 wrote for a datatype in the default namespace | [#570](https://github.com/trungdong/prov/issues/570) | the local part `:t` in the default namespace | the default namespace's `t` |

Remove an unused declaration from the file if the output must not declare it.

## PROV-O

`prov` 3.3.0 raises `ProvRDFException` for this input.

| Error | Issue | Example | Write instead |
|---|---|---|---|
| `Cannot split IRI 'urn:example:t=' into a namespace and a local part: it contains no '#' or '/' separator.` | [#665](https://github.com/trungdong/prov/issues/665) | `"1"^^<urn:example:t=>` as a literal's datatype, or `<urn:example:t=>` as a subject, a predicate or the object of a relation | An IRI with a `/` or `#` before its local part, such as `<urn:example:t/x>`. |

3.2.3 read such a datatype as plain text and lost it, and raised
`ProvExceptionInvalidQualifiedName` for an untyped relation object. For the other
positions it raised a bare `ValueError` with the same sentence, which `except ValueError`
around a read caught. `ProvRDFException` is not a `ValueError`.

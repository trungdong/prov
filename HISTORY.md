# History

## 3.3.0 (unreleased)

### Rejected input

From 3.3.0, the reader or the model that warned about an input in `prov` 3.2.3 with a
`ProvFutureRejectionWarning` rejects it at the same position, or reads it as the warning
said. The [how-to](https://prov.readthedocs.io/en/latest/howto/prepare-for-3-3.html)
lists each error message with what to write instead. 3.3.0 rejects these inputs.

- In PROV-N, a repeated `default` declaration, a declared prefix that is not a
  `PN_PREFIX`, and a Unicode whitespace character other than space, tab, CR and LF
  between tokens, each a `ProvNSyntaxError` at the declaration or the character
  ([#508](https://github.com/trungdong/prov/issues/508),
  [#511](https://github.com/trungdong/prov/issues/511),
  [#509](https://github.com/trungdong/prov/issues/509)). U+1680, which 3.2.3 also warned
  about, reads as a name character
- Under the `strict` profile, a `default` declaration after a `prefix` declaration, a
  declaration of `prov` or `xsd`, a statement after a bundle, and an identifier or an
  attribute block on `alternateOf`, `specializationOf` or `hadMember`
  ([#519](https://github.com/trungdong/prov/issues/519))
- In PROV-N, an `xsi:` name with no `prefix xsi` declaration, a `ProvNSyntaxError` that
  names the missing declaration ([#510](https://github.com/trungdong/prov/issues/510))
- In PROV-N, an attribute named after one of the statement's own arguments, such as
  `prov:activity` on `wasGeneratedBy`, a `ProvNSyntaxError` at the attribute. The
  `lenient` profile skips the statement with a `ProvWarning`, as it skips any statement
  that fails to parse, where 3.2.3 read the statement and warned
  ([#523](https://github.com/trungdong/prov/issues/523))
- A time whose timezone offset is beyond ±14:00, which XSD 1.1 gives no `xsd:dateTime`
  form, a `ProvValueError` where the time is asserted, from any reader or from code. A
  typed `xsd:dateTime` value of an ordinary attribute with such an offset stays a `Literal`
  with its text, where 3.2.3 read it as a `datetime` and warned
  ([#513](https://github.com/trungdong/prov/issues/513))
- A language tag that is not shaped like a BCP 47 tag, or is empty, a `ProvValueError`
  when the `Literal` is built, from any reader or from code. The PROV-N writer no longer
  rewrites `en_US` as `en-US` or drops an empty tag, since no such tag can be held
  ([#472](https://github.com/trungdong/prov/issues/472))
- A local part that PROV-N could write only by percent-encoding it, such as `ex:a b`, a
  `ProvExceptionInvalidQualifiedName` naming the character when the name is built, from
  any reader, from code or from a pickle. The PROV-N writer no longer percent-encodes,
  since no such name can be held; a local part with a metacharacter is still written with
  a backslash escape ([#524](https://github.com/trungdong/prov/issues/524))

### Changes with no prior warning

- `xsi` is no longer a built-in prefix outside PROV-XML. An `xsi:` name in code,
  PROV-JSON or PROV-JSONLD needs a declaration like any other prefix. Without one, the
  model raises `ProvExceptionInvalidQualifiedName` for an attribute name and
  `ProvElementIdentifierRequired` for an identifier. PROV-JSON and PROV-JSONLD that 3.2.x
  wrote with `xsi:` names have no `xsi` entry in their prefix map, so add one before
  reading them with 3.3.0. A `QualifiedName` built from `prov.constants.XSI` declares
  itself when it is asserted. `prov.model.DEFAULT_NAMESPACES` no longer has an `xsi` key.
  PROV-XML still writes and reads `xsi:type` as before, and its writer raises
  `ProvXMLException` for a document that binds `xsi` to another IRI, which 3.2.x renamed
  to `xsi_1`
  ([#510](https://github.com/trungdong/prov/issues/510))
- A Python `datetime` with a timezone offset beyond ±14:00 is rejected as the value of
  any attribute, not only as a time of the statement, because no writer could emit it as
  an `xsd:dateTime`. 3.2.3 warned only in a time position
  ([#513](https://github.com/trungdong/prov/issues/513))
- `parse_xsd_datetime`, and so every reader and every time given as a string in code,
  reads only the `xsd:dateTime` lexical form of XSD 1.1: a date, `T`, a time with optional
  fractional seconds, and `Z` or an `hh:mm` offset. The other ISO 8601 forms that Python's
  `fromisoformat` reads, such as `2012-12-03T21:08Z` without seconds, the basic format
  `20121203T210816Z`, a week date or a comma before the fraction, are no longer read. On
  Python 3.10 a few more forms read, such as `2012-12-03T21:08:16.5 +01:00`, because
  `prov` padded the fraction before parsing; that padding went with the 3.10 floor
  ([#513](https://github.com/trungdong/prov/issues/513))
- `ProvValueError`, a subclass of both `ProvException` and `ValueError`, is the error for
  a value a `Literal` or an attribute cannot hold. `ProvExceptionInvalidQualifiedName`
  gains a `detail` attribute and prints it after the name

### Output changes

- The PROV-JSONLD writer writes a qualified name under any attribute other than
  `prov:type`, `prov:location` and `prov:role` as a node reference, `{"@id": "ex:shed"}`,
  the form the 2026-10-14 revision of the PROV-JSONLD schema specifies. A JSON-LD
  processor now reads the value as the IRI it names, as PROV-O holds it
  ([#564](https://github.com/trungdong/prov/issues/564),
  [#545](https://github.com/trungdong/prov/issues/545)). Earlier releases wrote an
  `xsd:QName` value object. `prov` 3.2.2 and earlier cannot read the new form
  (`missing "@value"`); 3.2.3 reads it
- A PROV-N document that declares `prefix xsi <…>` at an IRI other than the XML Schema
  Instance one is written back under `xsi`. 3.2.x renamed it to `xsi_1`
  ([#510](https://github.com/trungdong/prov/issues/510))
- `get_provn(strict=True)` and `serialize(format="provn", strict=True)` write
  `alternateOf`, `specializationOf` and `hadMember` without an identifier or attribute
  block, which the PROV-N grammar does not give them, so a strict write reads under the
  `strict` profile. Each dropped item is a `ProvWarning` naming the record. A `hadMember`
  read from PROV-JSON with several members carries its identifier and attributes on every
  member, so that is where the warning most often appears. The default writer keeps both
  ([#569](https://github.com/trungdong/prov/issues/569))

### Project

- `prov` requires Python 3.11 or later. Python 3.10 reached its end of life on
  2026-10-31, and pip installs the last 3.2.x release on it instead
- The prefix map and the membership fan-out that PROV-JSON and PROV-JSONLD share
  live in `prov.serializers._json_common`. Nothing changes in what either format
  reads or writes ([#589](https://github.com/trungdong/prov/issues/589))
- The checks `prov` runs on an attribute value at assertion live in
  `prov.model._values`, and the test suite reads every canonical document as
  `prov` 3.2.3 wrote it. Nothing changes in what `prov` accepts or writes
  ([#591](https://github.com/trungdong/prov/issues/591))
- The check that a qualified-name value resolves by its prefix is one function
  in `prov.model._values`, called at assertion and by the PROV-N, PROV-JSON and
  PROV-JSONLD readers. Nothing changes in what `prov` accepts, warns about or
  writes ([#587](https://github.com/trungdong/prov/issues/587))

## 3.2.3 (2026-10-19)

3.2.3 is a bug-fix release that also warns about input 3.3.0 rejects or reads
differently. No dependency or Python-floor changes; one additive class,
`prov.model.ProvFutureRejectionWarning`. In the PROV-JSON read benchmark, the new checks
make reading about 8% slower than in 3.2.2.

Five kinds of fix change behaviour that existing code may rely on:

- Some errors change type. An empty PROV-N namespace IRI raises `ProvNSyntaxError`, not
  `ValueError` (#512). A PROV-JSON formal attribute written as an empty array raises
  `ProvJSONException`, not `IndexError`. So does a time written as a value object that
  is not an `xsd:dateTime`, which raised `AttributeError` (#554)
- A PROV-JSONLD value with both `@id` and `@value`, which read as the `@value`, now
  raises `ProvJSONLDException` (#545)
- An ill-formed typed literal, such as `"abc" %% xsd:int`, stays a `Literal` instead of
  raising (#522)
- `unified()` leaves `alternateOf`, `specializationOf`, `mentionOf` and `hadMember`
  records out of the merge by identifier, so equal ones stay two and differing ones no
  longer raise (#530). `prov_to_graph()` and `prov_to_dot()` draw such records as
  separate edges
- The writers change their output for non-finite doubles (#550), a prefix named
  `default` (#518), default-namespace names containing `:` (#517) and `xsi:` names
  (#510)

### Warnings ahead of 3.3.0

`prov` now emits `ProvFutureRejectionWarning`, a new subclass of `ProvWarning`, for
input that 3.3.0 rejects or reads differently, and still reads that input as before.
Each message ends with the issue that tracks the 3.3.0 rule, such as `(#529)`. The
warnings cover:

- PROV-N: a repeated `default`, a prefix name PROV-N does not allow, an `xsi:` name with
  no `prefix xsi`, whitespace PROV-N does not allow, an attribute named after one of the
  statement's arguments, and four `strict`-profile rules (#508, #509, #510, #511, #519,
  #523)
- Any reader or code: timezone offsets beyond ±14:00, malformed language tags, local
  parts PROV-N cannot write, Python values with no PROV form, and qualified names that
  do not resolve or are full IRIs (#472, #482, #513, #516, #524, #553)
- PROV-JSON: repeated keys, malformed times, one-element arrays, nulls, names that are
  not strings, unknown value-object keys, a `$` that is not a string, undeclared
  datatypes, and full IRIs as names (#528, #529, #531, #532, #551, #552, #555, #597)
- `unified()`: an empty non-expandable position merged with a filled one (#547)

[Prepare for prov 3.3.0](https://prov.readthedocs.io/en/latest/howto/prepare-for-3-3.html)
lists every message, the input that triggers it and what to write instead. It also shows
how to turn the warnings into errors to check a corpus.

### Fixes

- The PROV-JSONLD reader accepts a qualified name written as a node reference,
  `{"@id": "ex:shed"}`, under any attribute (#545). The 2026-10-14 revision of the
  PROV-JSONLD schema adds this form, and ProvToolbox 2.2.5 writes it for a qualified name
  under any attribute other than `prov:type`, `prov:location` and `prov:role`. The reader
  raised `ProvJSONLDException` for the missing `"@value"`. A node reference with a key
  other than `@id` now raises `ProvJSONLDException`. Before, one that also had an
  `"@value"` read as that value, and its `"@id"` was dropped
- `prov.read()` without a format no longer shows `prov`'s warnings from a format it tried
  and set aside. Under an `error` filter, a warning from the format it settles on now
  raises from `read()`. Before, the warning made `read()` give up on that format and try
  the next one
- The PROV-N reader treats `xsi` as an ordinary prefix, as PROV-N reserves only `prov`
  and `xsd` (#510). `prefix xsi <http://example.org/>` raised "prefix 'xsi' is reserved".
  An `xsi:` name now resolves against the document's own declaration. The PROV-N
  writer declares `prefix xsi` whenever it writes an `xsi:` name
- An empty namespace IRI in PROV-N, `prefix z <>` or `default <>`, raises
  `ProvNSyntaxError` at the IRI under every profile (#512). It raised a bare `ValueError`
  with no position. Code that catches `ValueError` around such a document no longer
  catches it, since `ProvNSyntaxError` is not a `ValueError` subclass
- The PROV-N reader decodes the code point escapes `\uXXXX` and `\UXXXXXXXX` in
  strings and IRIs, as PROV-N section 6 allows (#521). `"caf\u00E9"` raised
  "unknown string escape '\u'". An escape that is not a Unicode scalar value, or that
  encodes a character an IRI cannot contain, raises `ProvNSyntaxError` at the escape
- The PROV-JSON and PROV-JSONLD writers write a default-namespace name whose local part
  contains `:`, such as PROV-N's `a\:b`, through a prefix bound to the default namespace
  IRI (#517). They wrote it as `a:b`, which reads back as the name `b` under the prefix
  `a`. When no prefix is bound to that IRI, the writer declares `dn`, or `dn_1` or the
  next free suffix if `dn` is taken
- The PROV-JSON writer renames a prefix called `default` to `default_1`, or the next free
  suffix (#518). PROV-JSON uses the `default` key for the default namespace, so the
  prefix read back as the default namespace and the names that used it did not resolve
- Every writer spells the non-finite doubles `INF`, `-INF` and `NaN`, the `xsd:double`
  lexical forms (#550). The PROV-N, PROV-JSON, PROV-JSONLD and PROV-XML writers wrote
  Python's `inf`, `-inf` and `nan`, which are outside the lexical space, and the PROV-O
  writer did the same in RDF/XML, N-Triples and N-Quads. Every reader accepts both. A
  float subclass, such as `numpy.float64`, is written as the plain float it holds
- The PROV-N writer warns with a `ProvWarning` when it writes a `%` as `%25` because two
  hexadecimal digits do not follow it, as it already did for the characters it
  percent-encodes (#524). A PROV-N reader keeps the `%25`, so it recovers a different IRI
- The PROV-N writer escapes an `xsd:anyURI` value as it does a string (#526). A value
  containing `"`, `\`, a carriage return or a line feed produced PROV-N that the reader
  rejected
- A typed literal whose text is outside its datatype's lexical space, such as
  `"abc" %% xsd:int`, stays a `Literal` with its text and datatype, as
  `"maybe" %% xsd:boolean` already did (#522). An ill-formed `xsd:int`, `xsd:long`,
  `xsd:integer` or `xsd:double` raised `ValueError` from every reader and from the model.
  The PROV-N reader reported it as a syntax error, and its `lenient` profile skipped the
  statement. The PROV-O reader also raised `ValueError` for an ill-formed `xsd:dateTime`,
  `xsd:gYear` or `xsd:gYearMonth`
- `prov:time`, `prov:startTime` and `prov:endTime` accept a `Literal` typed
  `xsd:dateTime`, so PROV-N's `[prov:time="2012-01-01T00:00:00" %% xsd:dateTime]` reads
  (#515). It raised "Invalid value for attribute prov:time", and so did the model given
  the same `Literal` in code. Text outside the `xsd:dateTime` lexical space still raises
- The PROV-JSON reader accepts `prov:time`, `prov:startTime` and `prov:endTime` written
  as a value object, `{"$": "2012-01-01T00:00:00", "type": "xsd:dateTime"}` (#554). It
  raised `AttributeError`. Any other value object, such as one with another datatype or
  an ill-formed text, and a time that is neither a string nor a value object, raise
  `ProvJSONException` naming the record and the attribute
- A PROV-JSON formal attribute written as an empty array, such as `"prov:entity": []`,
  raises `ProvJSONException` naming the record and the attribute. It raised a bare
  `IndexError`. The `ProvJSONException` for an array of several values now names the
  record and the attribute too, and its message no longer goes to the
  `prov.serializers.provjson` logger first
- `unified()` leaves `alternateOf`, `specializationOf`, `mentionOf` and `hadMember`
  records out of the merge by identifier, since PROV-DM and PROV-Links give these
  relations no identifier (#530). Two such records that shared an identifier and
  differed raised `ProvUnificationError`; they now pass through unchanged. Two equal
  ones were merged into one record and now stay two, until `unified()` removes
  duplicates in 3.3.0 (#548). `prov_to_graph()` and `prov_to_dot()` call `unified()`,
  so they draw such records as separate edges. On a document that failed to unify only
  because of such records, `prov_to_graph()` no longer raises and `prov_to_dot()` no
  longer falls back to the bundle as asserted
- The PROV-JSON reader gives every record of a `hadMember` whose `prov:entity` is an
  array the membership's identifier and attributes (#530). Only the first record had
  them, so the same collection read differently depending on which member came first.
  A membership with several members and no `prov:collection` reads; it raised
  `KeyError`. A later member that does not resolve, such as one with an undeclared
  prefix or a null, now reads as a membership with no entity, as the first member
  already did, instead of raising `ProvExceptionInvalidQualifiedName`
- The PROV-JSONLD reader keeps the `@id` of a `Membership` with several members on every
  record it reads, as it already did for one member (#530). 3.2.1 dropped the `@id`
  with a `ProvWarning`, because `unified()` raised on records sharing it

### Project

- Python 3.15 is supported and tested in CI, so 3.2.x covers CPython 3.10 to 3.15 and
  PyPy 3.11. No code changes were needed (#542)

## 3.2.2 (2026-09-18)

3.2.2 is a bug-fix release. No dependency or Python-floor changes; one additive type
alias, `prov.model.AttributeValue`.

### Fixes

- Attribute arguments type-check for callers under `mypy --strict` and pyright without a
  `cast` (#474). `RecordAttributesArg` rejected `dict[QualifiedName, str]` and similar
  dicts because `dict` is invariant in its key type, and its `Iterable` alternative stopped
  mypy inferring an inline dict literal. The alias is now covariant in its key type and
  names the values a dict may hold as `AttributeValue`: `str`, `int`, `float`, `bool`,
  `datetime`, `Identifier`, `QualifiedName`, `Literal`, `ProvRecord`, and `None`, which
  is skipped. The values in a list, tuple, set or iterator of pairs stay `Any`, as in
  3.2.1. One kind of call that type-checked under 3.2.1 is now reported by type checkers,
  with no change at runtime. A value whose static type is `Iterable[...]` or
  `Collection[...]`, whether a variable, a parameter or a function's return, is no longer
  accepted; type it as a `Sequence`, a `Set` or an `Iterator`, or wrap it in `list()`.
  One case still needs an annotation under mypy. A dict that is built before the call
  and holds values of more than one type, such as `{"ex:a": 1, "ex:b": "x"}`, is
  inferred as `dict[str, object]` and reported; annotate the variable as
  `dict[str, AttributeValue]`. Pyright accepts the call without the annotation
- `ProvRecord.add_attributes` accepts a generator. It iterated its argument twice, so a
  generator was consumed by the first pass and the record silently gained no attributes.
  The bundle factory methods were unaffected
- A mapping that is not a `dict`, such as `types.MappingProxyType`, is read through its
  `items()` wherever attributes are accepted. It was iterated as bare keys and failed

## 3.2.1 (2026-09-13)

3.2.1 is a bug-fix release. No dependency or Python-floor changes; one additive class
attribute, `Serializer.deserialize_options`.

### Fixes

- The `default` PROV-N profile no longer accepts the typed-element and derivation
  shorthand keywords `person`, `organization`, `softwareAgent`, `collection`,
  `emptyCollection`, `plan`, `wasRevisionOf`, `wasQuotedFrom` and `hadPrimarySource`.
  3.2.0 described them as keywords `prov` and ProvToolbox write; neither does, and
  ProvToolbox's reader rejects them. `default` is now the Recommendation grammar plus the
  bare `mentionOf` keyword, which both tools write. A shorthand keyword raises
  `ProvNSyntaxError` under `strict` and `default` and is skipped with a `ProvWarning`
  under `lenient`
- Under the `strict` PROV-N profile, the error for a bare `mentionOf` says that
  `prov:mentionOf` is the strict spelling and that the `default` profile accepts the bare
  keyword
- The `lenient` PROV-N profile warns once for every skipped statement. Consecutive
  unparsable statements, such as a run of `provext:` extensibility expressions, were
  skipped as one with a single `ProvWarning` naming only the first; resynchronisation
  now stops at any name followed by `(`, not only at a keyword the parser knows
- The PROV-XML deserializer no longer turns a reference element that has no `prov:ref`
  into an identifier made of its whitespace. ProvToolbox writes a `hadMember` member as
  `<entity><entity prov:ref="..."/></entity>`; the nested reference is now used, with a
  `ProvWarning`, and a reference element with neither a `prov:ref` nor text raises
  `ProvXMLException`
- The PROV-JSONLD deserializer accepts an array-valued `entity` on a `Membership`
  statement, which the submission (section 4.18) allows and ProvToolbox always writes,
  decoding one `hadMember` per member; an empty array raises `ProvJSONLDException`
- PROV-N output spells `xsd:boolean` values `"true"` and `"false"` instead of `"1"` and
  `"0"`. Both are legal lexical forms and the parser reads all four, but every other
  producer writes the words
- `prov-convert` and `prov-compare` open their files after parsing arguments instead of
  through `argparse.FileType`, which Python 3.14 deprecates; standard input and output are
  used when no file or `-` is given and are no longer closed by the tool, `--version` and
  `--help` no longer need a binary stdout, and `prov-compare` reports a missing file
  argument as a usage error. The own-warnings CI guard runs on Python 3.14 and treats
  `PendingDeprecationWarning` as an error
  ([#441](https://github.com/trungdong/prov/issues/441))
- PROV-XML reader warnings (`<prov:other>` skipped, unrepresentable attribute, nested
  reference) are attributed to the caller of `deserialize()` or `prov.read()` rather than to
  a frame inside `prov`, as the PROV-N reader's already are
- `Identifier`, `QualifiedName`, `Namespace` and `Literal` pickle under every protocol,
  load pickles written by 3.1.1 and by 3.2.0, and recompute their hash when loaded, so an
  object unpickled in another process (a `multiprocessing` worker, a disk cache) matches
  equal objects in sets and dicts again; `weakref.ref` works on them. 3.2.0's `__slots__`
  had pickled the stored hash and broken protocols 0 and 1
- An `Identifier` hashes by its URI alone, as a `QualifiedName` already did, so two
  identifiers that compare equal always hash equal
- `add_namespace()` clears the qualified-name resolution cache when the URI was already
  registered under another prefix, so resolving the same text before and after the
  call gives the same result; 3.2.0's cache had made it order-dependent
- A URI equal to the default namespace itself is no longer compacted to a qualified name
  with an empty local part, and the PROV-N writer raises instead of writing an empty
  identifier for one; `prefix:` with an empty local part is still written and read
- PROV-N parser: a prefix declared twice in one scope is a `ProvNSyntaxError` (the
  Recommendation forbids it); a bare qualified-name literal with an escaped colon and no
  default namespace is an error instead of resolving in the wrong namespace; a duplicate
  bundle identifier is a positioned `ProvNSyntaxError`, and `lenient` skips that bundle
  whole; an all-digit local name is accepted as an attribute name and as a datatype; a
  leading byte order mark is skipped; a carriage return ends a short string like a line
  feed; a `bytearray` stream is decoded
- The `lenient` PROV-N profile no longer swallows a `bundle` header or `endDocument` that
  follows a statement missing its closing bracket
- PROV-N output names a bundle with a prefixed identifier when the bundle declares a default
  namespace different from the one its identifier lives in, adding the prefix declaration
  inside the bundle, so the identifier's IRI survives re-reading; a bare name was resolved
  against the bundle's own default
- The PROV-N writer warns with `ProvWarning` when it percent-encodes a character a local
  part cannot express, encodes a lone surrogate instead of raising `UnicodeEncodeError`,
  percent-encodes a leading character PN_LOCAL forbids first, and raises `ProvException` for
  a namespace URI that is not an IRI
- `prov.read()` forwards each deserializer the options it declares (`profile` for PROV-N;
  `rdf_format`, `relation_mapper` and `predicate_mapper` for PROV-O), so auto-detection can
  read non-TriG RDF with `rdf_format`, and an option a format does not accept raises a
  `TypeError` naming the format and its options instead of a JSON or rdflib error
- `prov.read()` forwards the `json.load` options (`object_hook`, `object_pairs_hook`,
  `parse_float`, `parse_int`, `parse_constant`) to the PROV-JSON and PROV-JSONLD
  deserializers, which document them
- The PROV-O deserializer warns with `ProvWarning` when it mints a prefix for an attribute
  predicate under a namespace declared neither in the document nor in the graph; 3.2.0
  minted it silently where 3.1.1 raised
- A PROV-JSONLD `Membership` with an `@id` and several members decodes to unidentified
  `hadMember` records with a `ProvWarning`, since records sharing one identifier cannot be
  unified; with one member the `@id` is kept
- `prov-convert` and `prov-compare` accept a text-only standard stream for `-`
- Every serializer converts to UTC a datetime whose offset is not a whole number of
  minutes, since `xsd:dateTime` allows no seconds in an offset

## 3.2.0 (2026-09-12)

### PROV-N

- PROV-N can now be read as well as written: `ProvDocument.deserialize(format="provn")`,
  `prov.read()` (including auto-detection) and `prov-compare` accept PROV-N text, parsed
  by a hand-written recursive-descent parser with no new dependency
  ([#122](https://github.com/trungdong/prov/issues/122))
- Three parsing profiles, selected with `profile=`: `strict` accepts the W3C grammar only;
  `default` also accepts the bare `mentionOf` keyword and the shorthand keywords
  (`person`, `organization`, `softwareAgent`, `collection`, `emptyCollection`, `plan`,
  `wasRevisionOf`, `wasQuotedFrom`, `hadPrimarySource`) that `prov` and ProvToolbox write;
  `lenient` skips any statement that fails to parse with a `ProvWarning` naming its line
  and column and resumes at the next statement
- `prov.serializers.provn.ProvNSyntaxError` (a `ProvException`) reports the line, column
  and expectation of every syntax error
- `get_provn(strict=True)` and `serialize(format="provn", strict=True)` write `prov:mentionOf`
  instead of the bare `mentionOf` keyword, so the output parses under the strict profile;
  the default output is unchanged
- `prov-convert` gains `-i/--input-format`, so it reads PROV-N (or any other registered
  format), not only PROV-JSON
- PROV-N output percent-encodes every local part character `PN_LOCAL` cannot express, not
  just the earlier fixed set; a tab, a non-ASCII letter or any other codepoint outside
  `PN_CHARS`, `PN_CHARS_OTHER` and the backslash-escaped metacharacters is now
  percent-encoded instead of written raw, which previously produced PROV-N the parser
  could not read back

### Performance

- `NamespaceManager` caches string-to-`QualifiedName` resolutions per manager, cleared
  whenever a namespace is added or the default namespace changes, so deserialising a
  document no longer re-resolves the same identifier text for every record that mentions
  it (PROV-O deserialisation about 9% faster on the benchmark suite; construction through
  the API is unchanged, as its cost lies elsewhere)
- `Identifier`, `QualifiedName`, `Namespace` and `Literal` declare `__slots__` and
  `QualifiedName` stores its hash at construction, cutting the cost of the many hash
  lookups a record's attributes require; the `__slots__` memory saving is offset by the
  stored hash value each `Identifier`/`QualifiedName` now retains, so overall memory per
  record is essentially unchanged

### Fixes

- PROV-N output escapes a leading `-` or `.` and a trailing `.` in a local part, as the
  grammar requires; other occurrences of `-` and `.` stay unescaped
- PROV-N output percent-encodes a local part character that `PN_LOCAL` cannot express even
  escaped (a space, `<`, `>`, `"`, `{`, `}`, `|`, `^`, `` ` ``, `\`, or a bare `%` not followed
  by two hex digits); the local part changes on such a round trip (`a b` becomes `a%20b`), a
  documented limitation rather than a bug
- PROV-N output writes a `Literal` with an empty language tag as a plain string, the same as
  one with no language tag at all; the model and the other serializers are unaffected, so a
  `Literal("hi", langtag="")` still writes PROV-XML's `xml:lang=""`
- PROV-N output writes an underscore-separated language tag (e.g. `en_US`) with a hyphen
  (`en-US`), the separator the grammar and BCP 47 both use
- PROV-N output escapes a carriage return in a short string as `\r` instead of writing it raw,
  which the grammar forbids
- PROV-N input accepts a bare, unprefixed local name that starts with a digit (for example
  `entity(4567)`), as `PN_LOCAL` allows; the lexer previously read it as an integer literal
  and the parser rejected it as an identifier
- `prov.dot` warns with `ProvWarning` when a relation's endpoint is unset (it is drawn to a
  blank node, as before), instead of staying silent, matching what `prov_to_graph()` does
  since 3.1.1; the warning is attributed to the caller's own frame even for a relation
  inside a nested bundle
- PROV-O decoding resolves attribute keys against the namespaces declared in the RDF
  source, so a key whose local part ends in a PROV-N metacharacter (`= ' , : ; [ ]`) under
  a namespace no identifier uses now reads back; the last generation-time exclusion in the
  round-trip property test is lifted
- `ProvDocument.deserialize()` reads a path source as UTF-8 in binary mode, matching how
  `serialize()` writes one, instead of the text mode locale encoding, which could raise
  `UnicodeDecodeError` or read non-ASCII content back wrongly under a non-UTF-8 locale

### Tests

- The shared round-trip suite and the Hypothesis round-trip property now cover PROV-N,
  so every statement form, attribute datatype and qualified-name shape is written and
  read back through the new parser
- A PROV-N conformance corpus: every example in the PROV-N and PROV-DM Recommendations
  parses under the strict profile and round-trips through the writer, ProvToolbox's own
  PROV-N test documents parse, and the PROV-N that ProvToolbox writes for the shared test
  corpus reads back equal to the PROV-JSON fixture of the same name

### Documentation

- The PROV-N how-to covers reading, the three profiles, syntax errors and strict output;
  the conformance page treats PROV-N as a round-trip format and lists the corpus findings;
  the What's new page describes 3.2.0

### Project

- A benchmark suite under `benchmarks/` with a non-blocking CI job that fails on a 20% regression against a committed baseline
- `pre-commit run --all-files` now passes on a clean checkout. The vendored W3C schemas are
  excluded from the whitespace hooks and the Codacy configuration file ends with a newline
- The citation tests skip from an installed wheel when either repository metadata file is
  absent
- `Identifier`, `QualifiedName`, `Namespace` and `Literal` declare their identity fields
  `Final`, so type checkers reject reassignment of a field that equality and hashing depend
  on

## 3.1.1 (2026-09-10)

3.1.1 is a point release: bug fixes, hardening of the graphical export, test
coverage for long-open issues, a "What's new in 3" page, and community and
citation files for the repository. No API, dependency or Python-floor changes.

### Fixes

- `ProvBundle.__eq__` (and therefore `ProvDocument.__eq__`) compares equal
  bundles in linear time by testing record-set equality first, falling back
  to the record-by-record search only when the sets differ
- `NamespaceManager.get_namespace()` looks a URI up by index instead of
  scanning every known namespace; where a URI is both registered and the
  default namespace, the registered one is now returned consistently
- PROV-XML and PROV-O serializers declare a bundle's namespaces in
  registration order instead of hash-seed-dependent set order, and
  `ProvDocument.add_bundle()` registers a copied document's namespaces in the
  same order; PROV-XML byte output changes for bundles carrying two or more
  of their own namespaces
  ([#337](https://github.com/trungdong/prov/issues/337))
- `prov.graph.prov_to_graph()` warns with `prov.model.ProvWarning` when it
  drops a relation (an unset endpoint, or an undeclared endpoint whose type
  cannot be inferred, which only a `wasInfluencedBy` can trigger) instead of
  skipping it silently
- The PROV-O deserializer no longer warns "attributes were not converted"
  for documents that decode cleanly; the warning fires only when a subject
  is left with unconverted attributes and names only those subjects

### Security

- `prov.dot` no longer writes identifier URIs into Graphviz `URL`/`href`
  link attributes unless the scheme is `http`, `https`, `mailto`, `urn` or
  absent, and escapes labels and identifiers in both HTML-like and quoted
  node labels; a hostile document could previously plant `javascript:` links
  or break out of a label in rendered SVG. The scheme is checked on the
  decoded form of the URI, because Graphviz passes HTML character
  references such as `&#58;` through to SVG unchanged and every consumer
  decodes them, so an undecoded check could not catch a namespace URI that
  smuggled a `javascript:` link this way. Annotation-row `href` values are
  now HTML-escaped too. Ordinary documents render byte-identically, except
  that identifier URIs containing `&` now change bytes in the escaped
  `href`

### Tests

- Regression test pinning insertion-ordered attribute output in PROV-N and
  PROV-JSON; the non-determinism reported in
  [#130](https://github.com/trungdong/prov/issues/130) was removed by the
  3.0.0 attribute-storage rework and the guarantee is now documented in the
  PROV-N how-to
- The PROV-XML serializer's `force_types` parameter is now covered in both
  states ([#338](https://github.com/trungdong/prov/issues/338))

### Documentation

- `README.md` and `SECURITY.md` now state the 2.x support policy as it
  stands: security fixes only, with 2.5.3 the last back-port release
- New [What's new in 3](https://prov.readthedocs.io/en/latest/whats-new-3.html)
  page summarising the 3.x line for projects still on 2.x, linked from the
  README
- New [architecture overview](https://prov.readthedocs.io/en/latest/explanation/architecture.html)
  under Explanation

### Project

- A non-blocking CI job fails if `prov` raises a `DeprecationWarning` or
  `FutureWarning` of its own
  ([#340](https://github.com/trungdong/prov/issues/340))
- Design specs, implementation plans and the test-gap checklist moved from
  `docs/` to a top-level `planning/` directory; the published documentation
  is unaffected
- Contributor Covenant 2.1 code of conduct, issue forms, a pull-request
  template, `CITATION.cff` (kept in step with `prov.__version__` by a test)
  and `.zenodo.json`; contributions are accepted under the project's MIT
  licence on an inbound-equals-outbound basis and the contributor licence
  agreements in `cla/` are removed

## 3.1.0 (2026-08-07)

- New PROV-JSONLD serializer and deserializer, selected with `format="jsonld"`
  (`src/prov/serializers/provjsonld.py`): implements the W3C member submission
  ["A JSON-LD Representation for the PROV Data Model"](https://www.w3.org/submissions/prov-jsonld/),
  the canonical §4 compacted shape only, with no runtime dependency beyond the
  standard library. Registered in `prov.serializers.Registry` and included in
  `prov.read()`'s format auto-detection. See
  [Work with PROV-JSONLD](https://github.com/trungdong/prov/blob/main/docs/howto/provjsonld.md)
- `serialize(format="jsonld", ...)` takes a `context` keyword: `"url"` (the
  default) references the submission's context by URL; `"embed"` inlines the
  vendored context object for fully self-contained output; any other value
  raises `ValueError`
- The deserializer additionally tolerates ProvToolbox's `prov:`-prefixed
  spellings of the type and special terms, and is exercised against both the
  submission's own example and a vendored ProvToolbox fixture
  (`src/prov/tests/jsonld/`)
- `jsonld` joins `json`/`xml`/`rdf` in the shared round-trip test matrix
  (`SHARED_TARGETS` in `src/prov/tests/conftest.py`); output is additionally
  validated against the submission's vendored JSON Schema in both context
  modes (`context="embed"` after substituting the canonical context URL for
  the embedded object, since the schema's `Context` production cannot
  describe an embedded context) and, for `context="embed"`, additionally
  proven valid JSON-LD via `pyld` flatten
- **Known limitation:** the PROV-JSONLD submission defines no term for
  `mentionOf` (PROV-DM's Mention relation); `serialize()` raises
  `prov.serializers.provjsonld.ProvJSONLDException` for any document
  containing a `ProvMention` record, and the deserializer raises the same
  exception on an input statement typed `"Mention"`. This is a permanent
  limitation of the submission, not a `prov` defect. See
  `docs/reference/conformance.md`

## 3.0.0 (2026-07-27)

3.0.0 is the compatibility release: the one release the roadmap allows to
change behaviour and drop dependencies, closing out the standards-conformance
work (PROV-DM, PROV-CONSTRAINTS, PROV-O) that a backward-compatible 2.x series
could not fix. See
[Upgrading to 3.0](https://github.com/trungdong/prov/blob/main/docs/upgrading-3.0.md)
for what changed and what to do about it.

### Breaking changes

- `ProvBundle.unified()` / `ProvDocument.unified()` implement
  PROV-CONSTRAINTS key constraints (22/23) with pairwise term unification of
  formal attributes: records sharing an identifier whose formal attributes
  hold different concrete values now raise the new documented
  `prov.model.ProvUnificationError` instead of silently unioning; absent
  formal attributes unify with concrete values; extra attributes keep
  set-union semantics; bundles unify independently ([#253](https://github.com/trungdong/prov/issues/253))
- `unified()` rejects same-identifier records of incompatible types
  (entity vs activity, distinct relation kinds, PROV-CONSTRAINTS 53/54/55)
  with `ProvUnificationError` instead of merging them order-dependently
  into the first record's type; spec-permitted overlaps (an agent that is
  also an entity or activity) are kept as separate records ([#253](https://github.com/trungdong/prov/issues/253))
- Attribute values that are Python-equal but differently typed (`2` vs
  `2.0`, `1` vs `True`) are all retained on a record instead of
  collapsing to whichever was asserted first. This is visible in attribute
  iteration, record equality and hashing, and serialization. Attributes now
  iterate in assertion order rather than an arbitrary hash order, which makes
  `args`, `formal_attributes`, `get_startTime()` and `get_endTime()`
  deterministic. `ProvRecord.get_attribute()`, `get_asserted_types()` and
  the `value` property still return a plain `set`, but it is now built
  fresh on every call, so mutating it no longer writes through to the record:
  `record.get_asserted_types().add(qn)` now silently does nothing ([#34](https://github.com/trungdong/prov/issues/34))
- `pydot` and `networkx` are no longer unconditional runtime
  dependencies. `import prov.dot` now requires the `dot` extra
  (`pip install "prov[dot]"`) and `import prov.graph` the `graph`
  extra; without them the import raises `ModuleNotFoundError` naming the
  extra to install. The `plot` extra now pulls in `pydot`/`networkx`
  as well, since `plot()` renders through `prov.dot`. See
  `docs/upgrading-3.0.md`
- The `rdf` extra now requires `rdflib>=7.0.0` (previously `>=6.0.0`);
  round-trip behaviour is unchanged
- `python-dateutil` dropped. `prov` now has no unconditional
  runtime dependencies. Datetime strings are parsed as `xsd:dateTime`
  (ISO 8601 plus the hour-24 end-of-day form) via the standard library;
  factory `time=`/`startTime=`/`endTime=` parameters raise
  `ProvException` on invalid input instead of leaking a raw dateutil
  error, and non-ISO forms previously tolerated by dateutil (e.g.
  `"Nov 7, 2011"`) are no longer accepted ([#237](https://github.com/trungdong/prov/issues/237))
- The misspelled `prov.model.GenrationRef` type alias is renamed
  `GenerationRef`; the old spelling is removed rather than kept as a
  deprecated alias

### Conformance and correctness fixes

- When an attribute is asserted twice with an equal value of equal type, e.g.
  `Literal("10", XSD_DECIMAL)` and `Literal("10.00", XSD_DECIMAL)` ([#77](https://github.com/trungdong/prov/issues/77)),
  or `Literal("hi", langtag="en")` and `Literal("hi", langtag="EN")`
  ([#259](https://github.com/trungdong/prov/issues/259)), the record retains the first value asserted, as in 2.x ([#34](https://github.com/trungdong/prov/issues/34))
- Numeric datatype fidelity: `Literal` values typed `xsd:long` (and the
  rest of the XSD integer family) keep their asserted datatype instead of
  being silently re-typed `xsd:int` ([#235](https://github.com/trungdong/prov/issues/235)); PROV-N output types plain
  integers by magnitude (`xsd:int`/`xsd:long`/`xsd:integer`) so
  out-of-int32 values are no longer emitted as invalid bare int literals
  ([#249](https://github.com/trungdong/prov/issues/249)), and plain floats as full-precision `xsd:double` instead of
  `%g`-truncated `xsd:float` ([#251](https://github.com/trungdong/prov/issues/251))
- Literal semantics: string literals have one canonical serialized form (RDF
  output no longer decorates plain strings with `^^xsd:string`) ([#89](https://github.com/trungdong/prov/issues/89));
  `xsd:decimal` literals compare and hash in value space ([#77](https://github.com/trungdong/prov/issues/77)); language
  tags compare case-insensitively per RDF 1.1 while preserving their
  original case in output ([#259](https://github.com/trungdong/prov/issues/259))
- PROV-XML round trip preserves attributes whose value is the empty string;
  previously they were silently dropped on deserialization ([#224](https://github.com/trungdong/prov/issues/224))
- PROV-XML serializes attribute names containing characters illegal in an
  XML NCName using the reversible `_xHHHH_` escaping convention instead
  of raising `ValueError`; the deserializer applies the inverse, so such
  names round-trip ([#289](https://github.com/trungdong/prov/issues/289))
- The PROV-JSON deserializer raises `ProvJSONException` on structurally
  malformed input instead of leaking raw `KeyError`/`AttributeError`
  ([#228](https://github.com/trungdong/prov/issues/228))
- PROV-JSON typed literals always encode `$` as a string, and plain
  integers are typed by magnitude across PROV-JSON/PROV-XML/PROV-O output
  (`xsd:int`/`xsd:long`/`xsd:integer`), fixing schema-invalid output
  for out-of-int32 values ([#244](https://github.com/trungdong/prov/issues/244), [#246](https://github.com/trungdong/prov/issues/246), [#256](https://github.com/trungdong/prov/issues/256))
- PROV-JSON encodes QualifiedName attribute values as `xsd:QName` typed
  literals per the PROV-JSON submission (previously the non-standard
  `prov:QUALIFIED_NAME`, which remains accepted on input) ([#168](https://github.com/trungdong/prov/issues/168)), and
  `prov:QUALIFIED_NAME`-typed `Literal` values are resolved to
  QualifiedNames at assertion time, restoring round-trip equality ([#238](https://github.com/trungdong/prov/issues/238))
- PROV-O: documents containing multiple same-identifier relations with
  differing formal attributes ("scruffy" statements) are documented as a
  PROV-O representational limitation. They serialize but do not round-trip
  through RDF, and deserializing such RDF now raises an error naming the
  limitation; all other formats are unaffected ([#217](https://github.com/trungdong/prov/issues/217))
- PROV-O: a related gap is recorded, not fixed. An attribute key whose local
  part ends in a PROV-N metacharacter ([#223](https://github.com/trungdong/prov/issues/223)) can fail to round-trip through
  RDF when its namespace has not already been registered by another qualified
  name; `docs/reference/conformance.md` documents it as an open defect
  ([#341](https://github.com/trungdong/prov/issues/341))
- PROV-O (RDF) round-trip fidelity: mixed XSD-datatype attribute sets
  survive deserialization with their asserted datatypes intact ([#218](https://github.com/trungdong/prov/issues/218)), and
  `xsd:double` values are emitted at full precision instead of rdflib's
  6-significant-digit canonical form ([#225](https://github.com/trungdong/prov/issues/225))
- PROV-O output: anonymous qualified Communication/Attribution/Delegation/
  Influence nodes now carry their influencer property (`prov:activity`/
  `prov:agent`/`prov:agent`/`prov:influencer`) as the PROV-O
  qualification tables require, and the RDF round trip no longer collapses
  distinct anonymous delegations sharing a (delegate, activity) pair
  ([#250](https://github.com/trungdong/prov/issues/250), [#226](https://github.com/trungdong/prov/issues/226))
- PROV-O output emits `alternateOf` with the PROV-DM argument order
  (`alt1 prov:alternateOf alt2`); previously subject and object were
  transposed on both write and read ([#258](https://github.com/trungdong/prov/issues/258))
- PROV-O (RDF) deserialization returns `xsd:base64Binary` literals as
  their base64 text; previously the value was wrapped in a Python bytes
  repr (`b'…'`), corrupting the round trip ([#288](https://github.com/trungdong/prov/issues/288))
- PROV-O (RDF) deserialization reconciles `prov:startedAtTime`/
  `prov:endedAtTime` asserted directly on a qualified `prov:Start`/
  `prov:End` node into the relation's formal `prov:time` attribute;
  previously the formal attribute was left `None` and the value misfiled as
  an extra attribute ([#299](https://github.com/trungdong/prov/issues/299))
- PROV-O (RDF) round trip: an anonymous Communication/Attribution/Influence
  relation carrying extra attributes now deserializes back into a single
  record instead of two ([#303](https://github.com/trungdong/prov/issues/303))
- PROV-O (RDF) round trip: a qualified name whose local part ends in a PROV-N
  metacharacter (`= ' , : ; [ ]`) now deserializes instead of raising
  `ValueError: Can't split ...`; serialized output is unchanged ([#294](https://github.com/trungdong/prov/issues/294))
- PROV-N output escapes qualified-name local parts per the grammar's
  `PN_CHARS_ESC` production, so identifiers containing `' ( ) , : ; [ ]
  =` no longer produce invalid PROV-N ([#223](https://github.com/trungdong/prov/issues/223))
- PROV-N continues to emit Mention as bare `mentionOf(...)`, the
  de-facto syntax of the reference implementations for the last decade,
  rather than the `prov:mentionOf` form derivable from the PROV-Links
  note; now documented as a deliberate deviation ([#248](https://github.com/trungdong/prov/issues/248))

### Improvements

- Bundle-local and default namespace prefixes are now bound into RDF
  serialization alongside document-level ones, so turtle/TriG output uses
  the declared prefixes instead of auto-minted `ns1:`-style fallbacks
  ([#96](https://github.com/trungdong/prov/issues/96))
- Security: PROV-XML parsing no longer resolves DTD entities and never
  touches the network (`resolve_entities=False`, `no_network=True`),
  closing an XXE surface on untrusted input ([#273](https://github.com/trungdong/prov/issues/273))
- New public type aliases in `prov.model`, joining the existing
  `NameValuePair`: `AttributePair` (an attribute name/value pair before
  qualified-name resolution), `InfluencerRef` (the `influencer` parameter
  of `wasInfluencedBy()` and `influence()`) and `StreamOrPath` (the
  source and destination parameters of `read()`, `serialize()` and
  `deserialize()`)

### Internal

- The PROV-O (RDF) serializer's encode/decode container functions were
  decomposed into per-record-type dispatch, with byte-identical output ([#274](https://github.com/trungdong/prov/issues/274))
- Functions across the model, the serializers and `prov.dot` were refactored
  below the project's complexity threshold, with byte-identical behaviour
  ([#275](https://github.com/trungdong/prov/issues/275))
- Code-quality passes across `src/prov/` (type-alias adoption, removal of a
  permanently-disabled branch in the PROV-O (RDF) encoder, and readability
  clean-ups) with no change in behaviour
- Test infrastructure: the RDF fixture-comparison helper `find_diff()` now
  detects single-triple differences, which it previously missed ([#304](https://github.com/trungdong/prov/issues/304))

## 2.5.1 (2026-07-13)

- `prov.read()` polish following 2.5.0's [#239](https://github.com/trungdong/prov/issues/239): seekable streams are now
  rewound between auto-detection attempts (so e.g. a PROV-XML stream
  auto-detects instead of being consumed by the first candidate); rdflib's
  "does not look like a valid URI" logger noise from swallowed candidate
  attempts is suppressed during auto-detection; and when a `str`/`bytes`
  source that is not an existing file path fails to parse, the error now
  carries a hint that it was treated as raw content
- Documentation: the PROV-XML and PROV-JSON how-to pages no longer describe
  the pre-2.5.0 `read()` auto-detection behaviour (exception whitelist,
  "XML never auto-detects")

## 2.5.0 (2026-07-13)

- New record-level chaining convenience methods ([#154](https://github.com/trungdong/prov/issues/154)):
  `ProvEntity.wasRevisionOf()`, `.wasQuotedFrom()`, `.hadPrimarySource()`,
  `.mentionOf()`, and `.wasInfluencedBy()` on `ProvEntity`,
  `ProvActivity` and `ProvAgent`, mirroring the existing
  `e1.wasDerivedFrom(e2)` style for the remaining relation types
- The PROV-XML deserializer now raises `ProvXMLException` when a record's
  child element carries only unrecognised XML attributes, instead of leaking a
  raw `UnboundLocalError` or silently reusing the previous attribute's value
  ([#254](https://github.com/trungdong/prov/issues/254))
- `ProvDocument.serialize()` and `deserialize()` now accept any writable/
  readable file-like object (e.g. `tempfile.NamedTemporaryFile`), instead of
  only `io.IOBase` instances; previously such destinations were silently
  treated as file paths, writing to a repr-named file in the working
  directory. The serializers' text/binary stream detection now also
  recognises such wrapper objects as text streams ([#240](https://github.com/trungdong/prov/issues/240))
- `prov.read()` fixes ([#239](https://github.com/trungdong/prov/issues/239)): valid PROV-XML is now auto-detected (the RDF
  parser's `BadSyntax` no longer aborts detection); a `str`/`bytes`
  source that is not an existing file path is parsed as raw content, as the
  documentation always advertised; and input that no deserializer can
  meaningfully parse (e.g. an empty file) now raises `TypeError` instead of
  silently returning an empty document
- Documentation: the agent-subtype idiom now correctly uses qualified names
  (`PROV["Person"]`) for `prov:type` values; the previously documented
  string form asserted a plain string, which does not denote the pre-defined
  PROV type ([#236](https://github.com/trungdong/prov/issues/236))

## 2.4.0 (2026-07-06)

- **Documentation overhaul**: the documentation has been reorganised along the
  Diátaxis framework (tutorials, how-to guides, reference, explanations), with
  new furo/MyST/napoleon/intersphinx tooling behind the Sphinx build. Closes
  [#141](https://github.com/trungdong/prov/issues/141) (graphics export how-to) and [#83](https://github.com/trungdong/prov/issues/83) (`prov-convert`/`prov-compare` CLI
  tools how-to). ([#210](https://github.com/trungdong/prov/issues/210), [#211](https://github.com/trungdong/prov/issues/211), [#212](https://github.com/trungdong/prov/issues/212), [#213](https://github.com/trungdong/prov/issues/213), [#214](https://github.com/trungdong/prov/issues/214), [#215](https://github.com/trungdong/prov/issues/215), [#216](https://github.com/trungdong/prov/issues/216))
- **Test suite redesigned as pytest-native**: shared statement/attribute/qname
  coverage is now expressed once and parametrized across a document x format
  matrix (json/xml/rdf/model) instead of being copy-pasted per serializer;
  Hypothesis property-based round-trip tests generate documents across the
  full feature set; a malformed-input corpus exercises each deserializer's
  error handling. ([#219](https://github.com/trungdong/prov/issues/219), [#220](https://github.com/trungdong/prov/issues/220), [#221](https://github.com/trungdong/prov/issues/221), [#222](https://github.com/trungdong/prov/issues/222), [#227](https://github.com/trungdong/prov/issues/227), [#229](https://github.com/trungdong/prov/issues/229))
- **`prov.model` split into a package** (`prov.model.records`,
  `prov.model.namespaces`, `prov.model.bundle`) for maintainability, with
  no import-path changes: every historic `from prov.model import X` still
  works identically. ([#231](https://github.com/trungdong/prov/issues/231))
- Minor Makefile/CLAUDE.md cleanup for contributors. ([#209](https://github.com/trungdong/prov/issues/209))
- The serializer registry now degrades gracefully when the optional `rdf`
  (`rdflib`) or `xml` (`lxml`) extra is not installed: `import prov`
  and the JSON/PROV-N serializers work in a minimal install, and requesting
  the `rdf`/`xml` format raises an informative `DoNotExist` naming the
  missing extra instead of a bare `ModuleNotFoundError`. ([#230](https://github.com/trungdong/prov/issues/230))
- Deprecation warnings signposting planned 3.0 changes: importing
  `prov.dot`/`prov.graph` now emits a `DeprecationWarning` naming the
  future `prov[dot]`/`prov[graph]` extras those modules will require, and
  `ProvBundle.unified()`/`ProvDocument.unified()` emit a `FutureWarning`
  about the upcoming PROV-CONSTRAINTS unification rework. Both warnings are
  hidden by default (standard `DeprecationWarning`/`FutureWarning`
  semantics) and link to the new
  [Upgrading to 3.0](https://github.com/trungdong/prov/blob/main/docs/upgrading-3.0.md)
  guide, which tables every planned 3.0 change and what to do about it

## 2.3.0 (2026-07-05)

- **Dropped Python 3.9 support; minimum is now Python 3.10** (security fixes
  in transitive dependencies are only released for Python 3.10+) ([#189](https://github.com/trungdong/prov/issues/189))
- **Widened `rdflib` to `>=6.0.0,<8`** (was `>=4.2.1,<7`): rdflib 7 now
  supported; the floor rose because 4.2.1 no longer installs on supported
  Pythons ([#207](https://github.com/trungdong/prov/issues/207))
- Diagnostic improvement: `DoNotExist` (serializer lookup) and the CLI's
  `CLIError` now set `__cause__` via exception chaining, so tracebacks
  show the original error; exception types and messages are unchanged, so
  existing `except` blocks are unaffected ([#200](https://github.com/trungdong/prov/issues/200))
- Whole package passes `mypy --strict`; ships a `py.typed` marker
  (PEP 561) so downstream type-checkers see inline types ([#192](https://github.com/trungdong/prov/issues/192), [#193](https://github.com/trungdong/prov/issues/193), [#194](https://github.com/trungdong/prov/issues/194))
- Coverage raised to 97%, enforced in CI; new tests for the CLI scripts,
  `prov.read()` auto-detection, graph interop, and the serializer
  registry ([#201](https://github.com/trungdong/prov/issues/201), [#202](https://github.com/trungdong/prov/issues/202), [#203](https://github.com/trungdong/prov/issues/203), [#204](https://github.com/trungdong/prov/issues/204))
- Internal code quality: ruff rule families I/C4/SIM/RUF/UP045/UP031 enabled
  and long-standing lint suppressions resolved ([#195](https://github.com/trungdong/prov/issues/195), [#196](https://github.com/trungdong/prov/issues/196), [#197](https://github.com/trungdong/prov/issues/197), [#198](https://github.com/trungdong/prov/issues/198),
  [#199](https://github.com/trungdong/prov/issues/199), [#200](https://github.com/trungdong/prov/issues/200)); dependency audit documented in `docs/dependencies.md`; tox
  removed (use `uv run --python 3.X pytest` for local multi-version
  testing) ([#205](https://github.com/trungdong/prov/issues/205))
- Security hygiene: `SECURITY.md`, Dependabot version updates, and a
  documented support policy ([#190](https://github.com/trungdong/prov/issues/190))
- Fixed ReadTheDocs build (Sphinx pinned `<9`) ([#187](https://github.com/trungdong/prov/issues/187))

## 2.2.0 (2026-07-03)

- Fixed graphical output when a filename is supplied ([#164](https://github.com/trungdong/prov/issues/164))
- Fixed PROV-XML deserialization when prov is the default namespace ([#155](https://github.com/trungdong/prov/issues/155))
- New `plot` extra: `pip install prov[plot]` for matplotlib support ([#166](https://github.com/trungdong/prov/issues/166))
- Marked as Production/Stable; added Python 3.14 to the test matrix
- Tooling: ruff (lint+format), pytest runner, uv-based CI, automated PyPI
  releases via Trusted Publishing. No public API changes

## 2.1.1 (2025-06-24)

- No change - fixing the previous botched release

## 2.1.0 (2025-06-24)

- Added type annotations and mypy checks
- Added support for Python 3.13

## 2.0.2 (2025-06-07)

- Removed support for EOL Python 3.8
- Using pyproject.toml for project configurations (instead of setup.py)

## 2.0.1 (2024-06-10)

- Removed support for EOL Python 3.6 and 3.7
- Minor documentation update ([#153](https://github.com/trungdong/prov/issues/153))
- Stopped using deepcopy when duplicating Namespace ([#158](https://github.com/trungdong/prov/issues/158))
- Restricting rdflib package version to "<7" ([#156](https://github.com/trungdong/prov/issues/156))
- Raise an exception when an empty URI is registered as a namespace ([#142](https://github.com/trungdong/prov/issues/142))
- Ensure rdflib 6+ returns bytes when serializing tests (fixed [#151](https://github.com/trungdong/prov/issues/151))
- Removed fancy label output for bundle

## 2.0.0 (2020-11-01)

- Removed support for EOL Python 2
- Testing against Python 3.6+ and Pypy3

## Earlier releases

Releases before 2.0.0 are recorded in the
[changelog archive](https://github.com/trungdong/prov/blob/main/docs/changelog-archive.md).

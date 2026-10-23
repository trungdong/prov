# Developer guide

How `prov` is built inside, for anyone changing it. {doc}`explanation/architecture` gives
the overview a user needs; {doc}`contributing` gives the process and the checks every pull
request must pass.

## The PROV-N parser

PROV-N is read by two pure-Python modules with no dependency, `prov.serializers.provn_lexer`
and `prov.serializers.provn_parser`, wired into the registry by `prov.serializers.provn`.

The lexer is a regex-driven scanner with a fixed sequence of token classes. At each position
it skips whitespace and comments, then tries the token classes in that order and takes the
first match. The order encodes the grammar's precedence rules. Delimited tokens (IRIs in
angle brackets, quoted strings, quoted qualified names) come first, then `xsd:dateTime`, then
integers and qualified names, since a digit run can start any of the three. Between an
integer and a qualified name reading of the same run, the scanner takes the longer match and
prefers the integer reading on a tie, matching the Recommendation's guidance. One rule is
context-sensitive.
`@` starts a language tag only when the previous token was a string, since `@` is also a
legal character inside a local name. The rule that a local name may contain but not end
with `.` lives in the name regex itself, so the scanner never backtracks. The character
classes are the same Unicode tables the PROV-XML serializer uses for NCNames, shared through
`prov.identifier`. Every token carries its line and column.

The parser is recursive descent with one token of lookahead. Every PROV-N statement begins
with a keyword and every keyword is followed by `(`, so after one token the parser knows
which rule it is in. Each grammar production is a method (document, declarations, bundle,
statement, expression, attributes, literal), and the expression rule is table-driven rather
than one method per keyword. A keyword maps to a record type and the set of legal argument
counts; the positional arguments are read as a flat list, the count is checked, and each
position is mapped onto the record class's `FORMAL_ATTRIBUTES` in order, with `-` markers
omitted. Records are built through the same {py:meth}`~prov.model.ProvBundle.new_record`
call the PROV-JSON deserializer uses, so literal typing and namespace handling are shared
rather than reimplemented. The optional identifier before a relation's arguments, the one
place the grammar needs a second token of lookahead, is handled by reading the first
argument and then checking for `;`.

The three profiles share one parser. The profile selects whether the bare `mentionOf`
keyword that `prov` and ProvToolbox write is accepted alongside the Recommendation's
keywords, and whether a required-position check rejects `-` where the grammar demands an
identifier. The `lenient` profile adds panic-mode error
recovery. When a statement fails, the parser records the error, skips tokens until it
reaches a synchronisation point (any name followed by `(`, or a structural
keyword such as `endBundle` at the statement's own bracket depth) and resumes; the skipped
statements are reported as {py:class}`~prov.model.ProvWarning` by the serializer, attributed
to the caller's frame.

Errors are {py:class}`~prov.serializers.provn.ProvNSyntaxError` and carry the line and
column of the token at fault. The tokens are produced eagerly, before any statement is
parsed, so a tokenisation error is raised first in every profile.

## Conventions for serializers

The PROV-N reader and writer set the pattern for any new serializer.

- One place handles error position. A format's exception type carries the line and column
  (or the equivalent locator), formats its own message and pickles; only the scanner and the
  parser construct it, and every message names what was expected and what was found.
- Grammar clauses are cited on the code that implements them. Each regex or table names the
  production it encodes and says where it departs from a library default such as `\s` or `\d`
  and why.
- Tables where the grammar is tabular. Keywords and arities are data, derived from the
  model where they can be, and a test cross-checks them against the record classes.
- Records are built through {py:meth}`~prov.model.ProvBundle.new_record` with the same
  arguments the PROV-JSON deserializer passes, so a serializer adds no typing or namespace
  logic of its own.
- Recoverable problems are collected by the parser and reported once by the serializer,
  attributed to the caller's frame, so a parser has no `warnings` import.
- Section comments and method order follow the grammar, so a reader can jump to a
  production. Tests are one case per token class or production and one per boundary, named
  for the scenario they pin.
- A serializer declares the keyword arguments its `deserialize()` accepts in
  `deserialize_options`; `prov.read()` forwards only those.

## Tests

The test suite lives inside the package, at `src/prov/tests/`, and ships with it. Shared
coverage runs once per target through a parametrised round-trip fixture. The targets are the
in-memory model and the five round-trippable formats, PROV-JSON, PROV-XML, PROV-O,
PROV-JSONLD and PROV-N. This exercises a new record type or attribute shape against every
target at once, and per-format modules keep only what is specific to that format.
`examples.py` holds the canonical example documents that several modules and the DOT smoke
tests reuse, and a Hypothesis property test round-trips generated documents through those
same five formats.

A top-level `benchmarks/` directory, outside the package, holds a pytest-benchmark suite
and `ab.py`, which times two versions of the library on one machine. A non-blocking CI job
runs it on every change against the change's first parent.

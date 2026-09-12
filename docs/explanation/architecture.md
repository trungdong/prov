# Architecture

`prov` is one package, `src/prov/`, in layers that depend in one direction with one
deliberate exception. `prov.model` imports `prov.serializers` so that `serialize()` and
`deserialize()` can dispatch through the registry, and the format modules import
`prov.model` back. The registry breaks the cycle by importing the format modules lazily,
on first use. Reading the layers in order gives the shape of the library.

## Layers

| Module | Responsibility | Depends on |
|---|---|---|
| `prov.identifier` | `Identifier`, `QualifiedName`, `Namespace`: the names records are made of | standard library |
| `prov.constants` | The PROV vocabulary as `QualifiedName` constants (`PROV_ENTITY`, `PROV_ATTR_ACTIVITY`, ...), plus the tables that map record types to classes and to their PROV-N, PROV-JSON and PROV-XML spellings | `prov.identifier` |
| `prov.model` | The in-memory data model: records, bundles, documents and namespace management | `prov.identifier`, `prov.constants`, `prov.serializers` (for `serialize()`/`deserialize()` dispatch) |
| `prov.serializers` | One module per format behind a registry; `ProvDocument.serialize()`, `ProvDocument.deserialize()` and `prov.read()` dispatch through it | `prov.model`, plus `rdflib` (`provrdf`) and `lxml` (`provxml`) behind extras |
| `prov.graph` | `prov_to_graph()` / `graph_to_prov()`: conversion to and from a NetworkX `MultiDiGraph` | `prov.identifier`, `prov.model`, `networkx` (extra `graph`) |
| `prov.dot` | `prov_to_dot()`: Graphviz rendering via pydot | `prov.identifier`, `prov.graph`, `prov.model`, `pydot` (extra `dot`) |
| `prov.scripts` | The `prov-convert` and `prov-compare` command-line tools | `prov.model`, `prov.serializers` |

`prov.model` is a package (`records.py`, `bundle.py`, `namespaces.py`) whose `__init__.py`
re-exports every public name at its historic `prov.model` location. User code imports from
`prov.model` and never from the submodules. Both `prov.model.__init__` and
`prov.model.bundle` import `prov.serializers` at module load time.

## The object model

A `ProvRecord` is a PROV type, an optional identifier and an ordered multi-valued attribute
map. `ProvElement` (entity, activity, agent) and `ProvRelation` (generation, usage,
derivation and the rest) split the PROV-DM world between them. Each concrete class declares
its formal attributes in order. Everything else on the record is an "other" attribute.

A {py:class}`~prov.model.ProvBundle` owns records and a namespace manager, and offers a
factory method per record type (`entity()`, `wasGeneratedBy()`, ...). A
{py:class}`~prov.model.ProvDocument` is a bundle that can also contain named bundles, and
is the unit that serializes. Records are created through the bundle so that identifiers
resolve against its namespaces. The bundle records every namespace a record mentions.

Two transformations produce new documents rather than mutating the original.
{py:meth}`~prov.model.ProvDocument.flattened` lifts bundle contents to the top level, and
{py:meth}`~prov.model.ProvBundle.unified` merges records that share an identifier under the
PROV-CONSTRAINTS rules. See {doc}`unification-flattening`.

## Serializers and format detection

Each serializer subclasses {py:class}`~prov.serializers.Serializer` and implements
`serialize()` and `deserialize()`. `prov.serializers.Registry` holds them under their
format names in insertion order, `json`, `rdf`, `provn`, `xml`, `jsonld`, and
{py:func}`prov.serializers.get` resolves a name to a class.

{py:func}`prov.read` reads a file, path or string without a `format` by trying the
registered formats in that order until one succeeds, rewinding the stream between attempts
where it can. The order is part of the contract, because `json` is tried first and it is
the only attempt that can succeed on a non-seekable stream.

The registry is populated lazily, on the first call to {py:func}`prov.serializers.get` or
{py:func}`prov.read`, by `Registry.load_serializers()`. Formats whose parser is an optional
dependency (`rdf`, `xml`) are registered only if that dependency imports successfully.
Otherwise they are left out of the registry, so its shape depends on what is installed.
Requesting a format that is not registered raises {py:class}`~prov.serializers.DoNotExist`,
naming the extra to install when the format is one of the optional ones.

### The PROV-N parser

PROV-N is read by two pure-Python modules with no dependency, `prov.serializers.provn_lexer`
and `prov.serializers.provn_parser`, wired into the registry by `prov.serializers.provn`.

The lexer is a regex-driven scanner with an ordered token table. At each position it skips
whitespace and comments, then tries the token classes in a fixed order and takes the first
match. The order encodes the grammar's precedence rules. Delimited tokens (IRIs in angle
brackets, quoted strings, quoted qualified names) come first, then `xsd:dateTime` before
integers before qualified names, because a digit run can start any of the three and the
Recommendation asks tokenisers to prefer the integer reading. One rule is context-sensitive.
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

The three profiles share one parser. The profile selects which keyword table is consulted
(the Recommendation's keywords alone, or also the shorthand keywords and the bare
`mentionOf` that `prov` and ProvToolbox write) and whether a required-position check rejects
`-` where the grammar demands an identifier. The `lenient` profile adds panic-mode error
recovery. When a statement fails, the parser records the error, skips tokens until it
reaches a synchronisation point (a statement keyword followed by `(`, or a structural
keyword such as `endBundle` at the statement's own bracket depth) and resumes; the skipped
statements are reported as {py:class}`~prov.model.ProvWarning` by the serializer, attributed
to the caller's frame.

Errors are {py:class}`~prov.serializers.provn_lexer.ProvNSyntaxError` and carry the line and
column of the token at fault. The tokens are produced eagerly, before any statement is
parsed, so a tokenisation error is raised first in every profile.

## Extras

The core package has no runtime dependencies. `rdflib` sits behind the `rdf` extra, `lxml`
behind `xml`, `networkx` behind `graph`, `pydot` and `networkx` behind `dot`, and
`matplotlib`, `pydot` and `networkx` behind `plot` (see {doc}`../installation`). `prov.graph`
and `prov.dot` raise `ModuleNotFoundError` naming the extra when imported without it.

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
with a committed baseline that a non-blocking CI job compares against.

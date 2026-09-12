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

PROV-N is read by a two-module parser in `prov.serializers.provn_lexer` (a tokeniser with
line and column tracking) and `prov.serializers.provn_parser` (a recursive-descent parser,
one function per grammar production, building records through `ProvBundle.new_record()`
like the PROV-JSON deserializer). Three profiles, `strict`, `default` and `lenient`, decide
how much beyond the W3C grammar the parser accepts.

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

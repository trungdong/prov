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
| `prov.pygments` | `ProvNLexer`, the PROV-N lexer that Pygments loads through the `pygments.lexers` entry point | `pygments` (extra `pygments`) |
| `prov.scripts` | The `prov-convert` and `prov-compare` command-line tools | `prov`, `prov.model`, `prov.serializers`, `prov.dot` for Graphviz formats, and Pygments (extra `pygments`) reached by name for `--color` |

`prov.model` is a package (`records.py`, `bundle.py`, `namespaces.py`, `_values.py` for assertion-time value checks) whose `__init__.py`
re-exports every public name at its historic `prov.model` location. User code imports from
`prov.model` and never from the submodules. Both `prov.model.__init__` and
`prov.model.bundle` import `prov.serializers` at module load time.

## The object model

A `ProvRecord` is a PROV type, an optional identifier and an ordered multi-valued attribute
map. `ProvElement` (entity, activity, agent) and `ProvRelation` (generation, usage,
derivation and the rest) split the PROV-DM world between them. Each concrete class declares
its formal attributes in order. Everything else on the record is an "other" attribute.

A {py:class}`~prov.model.ProvBundle` owns records and a namespace manager that registers
the namespaces the bundle binds and those its records use that no enclosing scope declares,
and offers a factory method per record type (`entity()`, `wasGeneratedBy()`, ...). A
{py:class}`~prov.model.ProvDocument` is a bundle that can also contain named bundles, and
is the unit that serializes. Records are created through the bundle so that identifiers
resolve against its namespaces.

Two transformations leave the original untouched. {py:meth}`~prov.model.ProvDocument.unified`
merges records that share an identifier under the PROV-CONSTRAINTS rules and returns a new
document. {py:meth}`~prov.model.ProvDocument.flattened` lifts bundle contents to the top
level and returns a new document, or the document itself when it has no bundles. See
{doc}`unification-flattening`.

## Serializers and format detection

Each serializer subclasses {py:class}`~prov.serializers.Serializer` and implements
`serialize()` and `deserialize()`. `prov.serializers.Registry` holds them under their
format names, and {py:func}`prov.serializers.get` resolves a name to a class.
{ref}`auto-detect` gives the registry order and shows how {py:func}`prov.read` walks it.

{py:meth}`Registry.load_serializers() <prov.serializers.Registry.load_serializers>` fills
the registry on first use and leaves out a format whose optional parser is not installed.

## Extras

The core package has no runtime dependencies. Each optional capability sits behind an
extra, and {doc}`../installation` lists which extra installs which package. `prov.graph`,
`prov.dot` and `prov.pygments` raise `ModuleNotFoundError` naming the extra when imported
without it. `prov.pygments` imports nothing from `prov`, and {doc}`../development` gives
the reason.

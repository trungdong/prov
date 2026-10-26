# Developer guide

This page describes how `prov` is built inside, for anyone changing it.
{doc}`explanation/architecture` gives the overview a user needs; {doc}`contributing` gives the process and the checks every pull
request must pass.

## The PROV-N parser

PROV-N is read by two pure-Python modules with no dependency,
`prov.serializers.provn_lexer` and `prov.serializers.provn_parser`, wired into the registry
by `prov.serializers.provn`. Their module docstrings hold the internals, which are the lexer's
token order and line tracking and the parser's keyword table, profiles and error recovery.
The API reference does not document either module, so read the docstrings in the source.

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

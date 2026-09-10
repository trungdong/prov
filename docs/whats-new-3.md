# What's new in 3

This page is for projects still on `prov` 2.x, or pinned to an older release. It says what
the 3.x line changed, what it costs to move, and why the pin can go.

## Nothing to install that you do not use

3.0.0 removed every unconditional runtime dependency. `pip install prov` installs the
library alone; each format or capability that needs a third-party package is an extra:

| Extra | Enables | Pulls in |
|---|---|---|
| `rdf` | PROV-O (RDF) serializer and deserializer | `rdflib` |
| `xml` | PROV-XML serializer and deserializer | `lxml` |
| `graph` | NetworkX conversion (`prov.graph`) | `networkx` |
| `dot` | Graphviz export (`prov.dot`) | `pydot`, `networkx` |
| `plot` | `ProvBundle.plot()` | `matplotlib`, `pydot`, `networkx` |

PROV-JSON, PROV-N and PROV-JSONLD need no extra. See {doc}`installation`.

## Standards conformance, audited

Before 3.0.0 the library was audited against W3C PROV-DM, PROV-CONSTRAINTS, PROV-O,
PROV-XML and PROV-JSON. The {doc}`reference/conformance` page records, concept by concept,
how each serializer round-trips it and which gaps are permanent limitations of a format
rather than defects. The audit's fixes shipped in 3.0.0, each with tests showing the old and
new behaviour.

## Unification follows PROV-CONSTRAINTS

`unified()` implements the PROV-CONSTRAINTS key constraints: records sharing an identifier
are merged by term unification of their formal attributes, and records that cannot be
merged (different concrete values for the same formal attribute, or incompatible types)
raise `ProvUnificationError` instead of being silently combined. Bundles unify
independently. See {doc}`explanation/unification-flattening`.

## PROV-JSONLD

3.1.0 added a serializer and deserializer for
[PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/), selected with
`format="jsonld"`, implemented with the standard library alone. It joins PROV-JSON,
PROV-XML and PROV-O in the shared round-trip test matrix and in `prov.read()`'s format
auto-detection. See {doc}`howto/provjsonld`.

## Typed and documented

Every public name carries type hints and the package ships `py.typed`, so type checkers see
the API. The documentation is organised as tutorial, how-to guides, reference and
explanation, and the API reference is generated from the docstrings.

## Moving from 2.x

For most code the upgrade needs no change. The two things that can need attention are the
extras above (install the ones you use) and `unified()` raising on records it previously
merged silently. {doc}`upgrading-3.0` lists every change, what triggers it, and what to do.

## The 2.x line

The most recent 2.x release receives security fixes only; 2.5.3 was the last release to
carry bug fixes back-ported from 3.x. See
[SECURITY.md](https://github.com/trungdong/prov/blob/main/SECURITY.md).

## If you pin `prov==2.1.1` or `prov==1.5.1`

Those pins predate the 3.x work. Both versions are outside the support policy, and both
predate the 2.x line. Lift the pin to `prov>=3` and add the extras your code uses.
Please open an issue if anything in the upgrade guide does not cover your case.

## What comes next

[ROADMAP.md](https://github.com/trungdong/prov/blob/main/ROADMAP.md) has the ordered list
of planned releases. Next is a PROV-N parser (3.2.0), making the notation readable as well
as writable. Python 3.10 support ends in the first release after its end of life on
2026-10-31.

# What's new in 3

This page is for projects still on `prov` 2.x, or pinned to an older release. It says what
the 3.x line changed, what it costs to move, and why the pin can go.

## Nothing to install that you do not use

3.0.0 removed every unconditional runtime dependency. `pip install prov` installs the
library alone, with PROV-JSON, PROV-N and PROV-JSONLD. PROV-O, PROV-XML and the graph tools
each sit behind an extra, which {doc}`installation` lists.

## Standards conformance, audited

Before 3.0.0 the library was audited against W3C PROV-DM, PROV-N, PROV-CONSTRAINTS,
PROV-O, PROV-XML and PROV-JSON. The {doc}`reference/conformance` page records, concept by
concept, how each serializer round-trips it and which gaps are permanent limitations of a
format rather than defects. The audit's fixes shipped in 3.0.0, each with tests showing the
old and new behaviour.

## Unification follows PROV-CONSTRAINTS

`unified()` implements the PROV-CONSTRAINTS key constraints. Records sharing an identifier
are merged by term unification of their formal attributes. Records that cannot be merged,
because they hold different concrete values for the same formal attribute or have
incompatible types, raise `ProvUnificationError` instead of being silently combined.
Bundles unify independently. See {doc}`explanation/unification-flattening`.

## PROV-JSONLD

3.1.0 added a serializer and deserializer for
[PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/), selected with
`format="jsonld"` and implemented with the standard library alone. It joins PROV-JSON,
PROV-XML and PROV-O in the shared round-trip test matrix and in `prov.read()`'s format
auto-detection. See {doc}`howto/provjsonld`.

## Two-way PROV-N

3.2.0 added a PROV-N parser, so the notation `prov` has always written can now be read:
`format="provn"` in `deserialize()`, auto-detected by `prov.read()`, and accepted by
`prov-convert -i provn`. The parser is hand-written and needs no extra. Three profiles
select how much beyond the W3C grammar it accepts; the default reads what `prov` and
ProvToolbox write. PROV-N joins the shared round-trip test matrix, and a conformance corpus
checks every example of the PROV-N and PROV-DM Recommendations. See {doc}`howto/provn`.

## Typed and documented

Every public name carries type hints and the package ships `py.typed`, so type checkers
see the API. The documentation is organised as tutorial, how-to guides, reference and
explanation, and the API reference is generated from the docstrings.

## Moving from 2.x

For most code the upgrade needs no change. Two things can need attention. Install the
extras your code uses, and expect `unified()` to raise on records it previously merged
silently. {doc}`upgrading-3.0` lists every change, what triggers it, and what to do. A pin
to an older release such as `prov==2.1.1` or `prov==1.5.1` predates the 3.x work and the
current support policy; lift it to `prov>=3` and add the extras your code uses, and open
an issue if the upgrade guide does not cover your case.

## The 2.x line

The most recent 2.x release receives security fixes only. 2.5.3 was the last release to
carry bug fixes back-ported from 3.x. See
[SECURITY.md](https://github.com/trungdong/prov/blob/main/SECURITY.md).

## What comes next

[ROADMAP.md](https://github.com/trungdong/prov/blob/main/ROADMAP.md) lists the planned
releases in order. 3.3.0 requires Python 3.11 or later under the support policy, because
Python 3.10's support ends on 2026-10-31. On Python 3.10, pip installs the last 3.2.x
release instead.

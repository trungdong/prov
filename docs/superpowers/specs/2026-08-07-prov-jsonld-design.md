# PROV-JSONLD support (release 3.1.0) — design

**Date:** 2026-08-07
**Status:** Approved
**Roadmap context:** Phase 5, steps 40–44 of the
[modernisation roadmap](2026-07-03-modernisation-roadmap-design.md); community summary in
`ROADMAP.md` (3.1.0 row).

## Goal

Add a serializer and deserializer for
[PROV-JSONLD](https://www.w3.org/submissions/prov-jsonld/), the W3C member submission for
representing PROV-DM natively in JSON-LD. Purely additive: no existing behaviour changes,
no new runtime dependencies, ships as minor release 3.1.0.

## Decisions (with rationale)

| Decision | Choice | Rationale |
|---|---|---|
| Parser input scope | **Canonical §4 compacted shape only** | Deterministic, dependency-free, mirrors how `provjson.py` treats PROV-JSON. Other JSON-LD forms (expanded, flattened, differently compacted) are rejected with a clear error. A pyld-based normalisation layer can be added later if users ask (file a backlog issue at implementation time if demand appears). |
| `@context` on output | **Reference the canonical context URL by default; embed opt-in** | Matches the submission's own examples and ProvToolbox output; smaller documents. `context="embed"` inlines the vendored §5 context for offline/self-contained use. *(Supersedes the roadmap step 40 note's lean toward embed-by-default — decided 2026-08-07.)* |
| Internal architecture | **Declarative mapping table + thin engine** | One module-level table (record class ↔ `@type` term ↔ ordered formal-attribute keys) drives both encode and decode, so the two directions cannot drift and conformance auditing is a table-vs-§4 comparison. Special-case overrides where the submission deviates from the tabular pattern. |
| Validation depth | **pyld processor tests + ProvToolbox interop fixtures + submission examples** | pyld (test-only dependency) proves emitted documents are valid JSON-LD against the real context; vendored ProvToolbox-generated fixtures prove cross-implementation interop; the submission's own examples anchor spec conformance. |
| rdflib involvement | **None** | Fixed by roadmap step 40: native JSON implementation like `provjson.py`. |

## Target format (established against the submission and ProvToolbox)

A PROV-JSONLD document is:

```json
{
  "@context": [ { "<prefix>": "<namespace-uri>", ... }, "<canonical context URL>" ],
  "@graph": [ { "@type": "prov:Entity", "@id": "ex:e1", ... }, ... ]
}
```

- Each `@graph` member is one PROV-DM statement, dispatched on `@type`
  (`prov:Entity`, `prov:Activity`, `prov:Agent`, `prov:Generation`, `prov:Derivation`, …).
- Formal attributes use fixed keys defined per record type by the §5 context
  (`entity`, `activity`, `agent`, `generatedEntity`, `usedEntity`, `time`, …), with
  `@id`-typed terms holding qualified-name strings.
- Other attributes appear under their prefixed names as arrays of JSON-LD value objects
  (`{"@value": ..., "@type": ...}`, `{"@value": ..., "@language": ...}`) or `@id` strings,
  per the context's term typing. `prov:type`, `prov:role`, `prov:label`, `prov:location`
  have dedicated context terms.
- Records may be anonymous (no `@id`), e.g. an unidentified Derivation.
- Bundles are nested objects in the top-level `@graph`:
  `{ "@context": { <bundle namespace map> }, "@id": "<bundle id>", "@graph": [ ... ] }`.
- Known deviations from the tabular pattern, handled as explicit overrides:
  `prov:Activity` carries `startTime`/`endTime` directly; Delegation uses
  `responsible`/`delegate`; `mentionOf` references a bundle. The exact §4 tables are
  transcribed during implementation with the submission as the authority.
- The exact canonical context URL is taken from the submission at implementation time
  (ProvToolbox uses `http://openprovenance.org/prov-jsonld.json`).

**Fidelity goal:** PROV-JSONLD is a native PROV-DM representation, so round-trips are
expected lossless for the full shared corpus — **zero permanent skips**, unlike PROV-O
(#217). If implementation uncovers a construct the submission genuinely cannot represent,
it is documented in the conformance matrix with a tracking issue, not silently skipped.

## Module architecture

New module `src/prov/serializers/provjsonld.py` (flat one-module-per-format layout):

- `ProvJSONLDSerializer(Serializer)` with `serialize()`/`deserialize()`;
  `ProvJSONLDException(Error)` mirroring `ProvJSONException`.
- **Mapping table**: module-level, built on `prov.constants` (the existing
  identifier↔class authority) — it adds only the JSON-LD-specific surface
  (`@type` term and formal-attribute key names per record class), never duplicating
  vocabulary already in `constants.py`.
- **Encoder walk**: document → `{@context, @graph}`; records looked up in the table;
  formal attributes under fixed keys; extra attributes as value-object arrays; bundles
  as nested `@graph` objects.
- **Decoder walk**: strict canonical-shape parser. Validates top-level
  `@context`/`@graph`; dispatches on `@type` via the same table; reconstructs a
  `ProvDocument` (and bundles). Unknown `@type`, missing required keys, or malformed
  value objects raise `ProvJSONLDException` naming the offending record — same
  error-quality bar as the 2.5.0 PROV-XML deserializer work.
- **Vendored context**: the submission's §5 context JSON ships as package data (like the
  vendored XSD/JSON schemas), used by `context="embed"` and by tests.
- Anonymous records: emitted without `@id`; on decode they become records without an
  identifier. The `AnonymousIDGenerator` pattern from `provjson.py` is reused only if
  decoding turns out to need stable ids.

## Public API surface

- **Registration**: format name `"jsonld"` in the serializer `Registry`. No optional
  extra — the implementation is stdlib-only, always available (like `json`).
  `prov.read(..., format="jsonld")`, `ProvDocument.serialize(format="jsonld")`, and the
  CLI tools pick it up through the registry; `.jsonld` added to `prov-convert`'s
  extension→format inference.
- **Auto-detection**: appended to `prov.read()`'s detection sequence. The strict shape
  check makes cross-detection safe: PROV-JSON (an object keyed by record-type sections,
  no `@graph`) fails the JSON-LD shape check and vice versa. A cheap
  `@graph`/`@context` sniff short-circuits before full decoding.
- **Serialize options** (via `**args`, like existing serializers):
  `context="url"` (default) | `context="embed"`. Nothing else in 3.1.0.
- **Media type**: `application/ld+json`, recorded in docs and the conformance matrix
  only.
- **Typing/docs**: fully typed under `mypy --strict` and docstringed from day one.
  `test_public_api.py` gains the new names; `prov.serializers` namespace conventions
  respected.
- **Errors**: `ProvJSONLDException` exported alongside the other serializer exceptions;
  auto-detection swallows it like the rest.

## Testing

- **Shared coverage**: `"jsonld"` joins `ROUNDTRIP_FORMATS` in `conftest.py`, so
  `test_statements.py`, `test_attributes.py`, `test_qnames.py`, `test_examples.py` run
  against it via the `roundtrip` fixture with zero expected skips. The Hypothesis
  property round-trip picks the format up from the same constant with no new
  generation-time exclusions.
- **`test_jsonld.py`** (format-specific): encoder internals, `context` option output
  shapes, strict-shape rejection (PROV-JSON input, expanded-form JSON-LD, unknown
  `@type`), error-message quality, fixture-dir round-trips over a new
  `src/prov/tests/jsonld/` directory.
- **Fixtures**: the submission's examples plus a corpus generated once from the local
  ProvToolbox checkout (`~/projects/ProvToolbox/modules-core/prov-jsonld`), vendored
  under `tests/jsonld/`. Our deserializer must read ProvToolbox output to the expected
  documents. No Java in CI.
- **pyld tests**: `pyld` in the test dependency group only; a test module expands
  emitted documents with a real JSON-LD processor and asserts the expected term IRIs
  result — validating against the real context, not just our reading of it.
- **Suite invariant**: pass count rises; CLAUDE.md's invariant line and skip breakdown
  updated in the same PR that changes them. `test_read.py` gains auto-detection cases;
  CLI smoke tests gain `jsonld`.

## Documentation

- How-to page for the format in the existing how-to section.
- JSON-LD column in `docs/reference/conformance.md` (the matrix is revisited at every
  release).
- CHANGELOG entry; `ROADMAP.md` stamped on release.

## Release

- **3.1.0**, purely additive minor release.
- Python floor stays **3.10** (roadmap EOL policy; expected to ship before 2026-10-31).
- Same release mechanics as 3.0.0: gated PyPI publish, conda-forge follow-up.
- Work lands as focused PRs per roadmap step, green CI before merge.

## Out of scope

- Accepting non-canonical JSON-LD forms (expanded/flattened) — possible later via an
  optional pyld normalisation layer, only if user demand appears.
- PROV-N parsing (Phase 5b, release 3.2.0).
- Any behaviour change to existing serializers.

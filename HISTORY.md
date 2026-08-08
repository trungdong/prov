# History

## 2.5.3 (unreleased)

- Escaped PROV-N metacharacters (`= ' ( ) , : ; [ ]`) in the local parts of
  qualified names, so identifiers containing them serialise to valid PROV-N
  (#223). Backslashes in string literals are now escaped before quotes.
- Anonymous `prov:qualified*` nodes for communication, attribution,
  delegation and influence now carry their own influencer property, as the
  PROV-O qualification tables require, so a qualification node is
  interpretable without its shorthand binary triple (#250). Decoding uses
  that property to tell several same-kind qualification nodes apart instead
  of guessing (#226).
- PROV-XML now round-trips empty-string attribute values, which previously
  vanished entirely because lxml reports an empty element's text as `None`
  (#224), and escapes attribute-name local parts that are not legal XML
  NCNames using the `_xHHHH_` convention instead of emitting invalid XML
  (#289).
- The PROV-JSON deserializer now raises `ProvJSONException` with a message
  naming the offending construct when given malformed input, instead of
  letting `KeyError`, `AttributeError` or `TypeError` escape (#228).
- `prov:startedAtTime` and `prov:endedAtTime` asserted directly on a
  qualified `prov:Start`/`prov:End` node are now decoded into the relation's
  formal `prov:time` attribute, instead of being stripped into extra
  attributes (#299).
- Anonymous attribution, communication and influence relations carrying
  extra attributes now reconcile onto their `prov:qualified*` node when
  decoded from RDF, as delegation and association already did, instead of
  producing a duplicate record (#303).
- Qualified names whose local part ends in a PROV-N metacharacter now
  round-trip through PROV-O instead of raising `ValueError: Can't split` from
  rdflib during deserialization (#294). Encoded output is unchanged.
- `prov.read()` now populates the serializer registry only when it is empty,
  instead of discarding and rebuilding it on every call. No observable
  behaviour change (#353).

## 2.5.2 (2026-08-08)

- Security: PROV-XML parsing no longer resolves DTD entities and never
  touches the network (`resolve_entities=False`, `no_network=True`),
  closing an XXE surface on untrusted input. Both `etree.parse()` call
  sites previously inherited lxml's process-global default parser, which
  any other library in the same process can repoint via
  `etree.set_default_parser()` — with a permissive parser installed that
  way, an external entity resolved and leaked the referenced file's
  contents through `ProvDocument.deserialize()` (#273)
- Security: CI workflows now pin every third-party action to a commit SHA
  rather than a mutable tag, and the CI workflow's `GITHUB_TOKEN` is
  restricted to `contents: read`
- Test infrastructure: the RDF fixture-comparison helper `find_diff()` now
  detects single-triple differences, which it previously missed (#304)
- Documentation: the support policy on this branch is brought in line with
  the 3.x line's — the 2.x release receives security fixes plus bug fixes
  back-ported from 3.x up to and including 2.6.0, after which it reverts to
  security fixes only. The previous text still described 2.x as the only
  maintained line, which predates the 3.0.0 release

## 2.5.1 (2026-07-13)

- `prov.read()` polish following 2.5.0's #239: seekable streams are now
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

- New record-level chaining convenience methods (#154):
  `ProvEntity.wasRevisionOf()`, `.wasQuotedFrom()`, `.hadPrimarySource()`,
  `.mentionOf()`, and `.wasInfluencedBy()` on `ProvEntity`,
  `ProvActivity` and `ProvAgent` — mirroring the existing
  `e1.wasDerivedFrom(e2)` style for the remaining relation types
- The PROV-XML deserializer now raises `ProvXMLException` when a record's
  child element carries only unrecognised XML attributes, instead of leaking a
  raw `UnboundLocalError` or silently reusing the previous attribute's value
  (#254)
- `ProvDocument.serialize()` and `deserialize()` now accept any writable/
  readable file-like object (e.g. `tempfile.NamedTemporaryFile`), instead of
  only `io.IOBase` instances; previously such destinations were silently
  treated as file paths, writing to a repr-named file in the working
  directory. The serializers' text/binary stream detection now also
  recognises such wrapper objects as text streams (#240)
- `prov.read()` fixes (#239): valid PROV-XML is now auto-detected (the RDF
  parser's `BadSyntax` no longer aborts detection); a `str`/`bytes`
  source that is not an existing file path is parsed as raw content, as the
  documentation always advertised; and input that no deserializer can
  meaningfully parse (e.g. an empty file) now raises `TypeError` instead of
  silently returning an empty document
- Documentation: the agent-subtype idiom now correctly uses qualified names
  (`PROV["Person"]`) for `prov:type` values; the previously documented
  string form asserted a plain string, which does not denote the pre-defined
  PROV type (#236)

## 2.4.0 (2026-07-06)

- **Documentation overhaul**: the documentation has been reorganised along the
  Diátaxis framework (tutorials, how-to guides, reference, explanations), with
  new furo/MyST/napoleon/intersphinx tooling behind the Sphinx build. Closes
  #141 (graphics export how-to) and #83 (`prov-convert`/`prov-compare` CLI
  tools how-to). (#210, #211, #212, #213, #214, #215, #216)
- **Test suite redesigned as pytest-native**: shared statement/attribute/qname
  coverage is now expressed once and parametrized across a document x format
  matrix (json/xml/rdf/model) instead of being copy-pasted per serializer;
  Hypothesis property-based round-trip tests generate documents across the
  full feature set; a malformed-input corpus exercises each deserializer's
  error handling. (#219, #220, #221, #222, #227, #229)
- **`prov.model` split into a package** (`prov.model.records`,
  `prov.model.namespaces`, `prov.model.bundle`) for maintainability, with
  no import-path changes: every historic `from prov.model import X` still
  works identically. (#231)
- Minor Makefile/CLAUDE.md cleanup for contributors. (#209)
- The serializer registry now degrades gracefully when the optional `rdf`
  (`rdflib`) or `xml` (`lxml`) extra is not installed: `import prov`
  and the JSON/PROV-N serializers work in a minimal install, and requesting
  the `rdf`/`xml` format raises an informative `DoNotExist` naming the
  missing extra instead of a bare `ModuleNotFoundError`. (#230)
- Deprecation warnings signposting planned 3.0 changes: importing
  `prov.dot`/`prov.graph` now emits a `DeprecationWarning` naming the
  future `prov[dot]`/`prov[graph]` extras those modules will require, and
  `ProvBundle.unified()`/`ProvDocument.unified()` emit a `FutureWarning`
  about the upcoming PROV-CONSTRAINTS unification rework. Both warnings are
  hidden by default (standard `DeprecationWarning`/`FutureWarning`
  semantics) and link to the new
  [Upgrading to 3.0](https://github.com/trungdong/prov/blob/master/docs/upgrading-3.0.md)
  guide, which tables every planned 3.0 change and what to do about it.

## 2.3.0 (2026-07-05)

- **Dropped Python 3.9 support; minimum is now Python 3.10** (security fixes
  in transitive dependencies are only released for Python 3.10+) (#189)
- **Widened `rdflib` to `>=6.0.0,<8`** (was `>=4.2.1,<7`): rdflib 7 now
  supported; the floor rose because 4.2.1 no longer installs on supported
  Pythons (#207)
- Diagnostic improvement: `DoNotExist` (serializer lookup) and the CLI's
  `CLIError` now set `__cause__` via exception chaining, so tracebacks
  show the original error; exception types and messages are unchanged, so
  existing `except` blocks are unaffected (#200)
- Whole package passes `mypy --strict`; ships a `py.typed` marker
  (PEP 561) so downstream type-checkers see inline types (#192, #193, #194)
- Coverage raised to 97%, enforced in CI; new tests for the CLI scripts,
  `prov.read()` auto-detection, graph interop, and the serializer
  registry (#201, #202, #203, #204)
- Internal code quality: ruff rule families I/C4/SIM/RUF/UP045/UP031 enabled
  and long-standing lint suppressions resolved (#195, #196, #197, #198,
  #199, #200); dependency audit documented in `docs/dependencies.md`; tox
  removed (use `uv run --python 3.X pytest` for local multi-version
  testing) (#205)
- Security hygiene: `SECURITY.md`, Dependabot version updates, and a
  documented support policy (#190)
- Fixed ReadTheDocs build (Sphinx pinned `<9`) (#187)

## 2.2.0 (2026-07-03)

- Fixed graphical output when a filename is supplied (#164)
- Fixed PROV-XML deserialization when prov is the default namespace (#155)
- New `plot` extra: `pip install prov[plot]` for matplotlib support (#166)
- Marked as Production/Stable; added Python 3.14 to the test matrix
- Tooling: ruff (lint+format), pytest runner, uv-based CI, automated PyPI
  releases via Trusted Publishing. No public API changes.

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
- Minor documentation update (#153)
- Stopped using deepcopy when duplicating Namespace (#158)
- Restricting rdflib package version to "<7" (#156)
- Raise an exception when an empty URI is registered as a namespace (#142)
- Ensure rdflib 6+ returns bytes when serializing tests (fixed #151)
- Removed fancy label output for bundle

## 2.0.0 (2020-11-01)

- Removed support for EOL Python 2
- Testing against Python 3.6+ and Pypy3

## Earlier releases

Releases before 2.0.0 are recorded in the
[changelog archive](https://github.com/trungdong/prov/blob/master/docs/changelog-archive.md).

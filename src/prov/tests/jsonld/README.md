# Vendored PROV-JSONLD interop fixtures

These files are vendored, third-party PROV-JSONLD documents used by the
`test_interop_*` tests in `test_jsonld.py` to prove `prov`'s PROV-JSONLD
decoder can read other implementations' output, not just its own.

## Files and sources

| File                              | Source                                                                                      | Retrieved  |
|------------------------------------|-----------------------------------------------------------------------------------------------|------------|
| `submission-example-3.jsonld`      | Example 1, §3 of <https://www.w3.org/submissions/prov-jsonld/> (the W3C member submission)    | 2026-08-07 |
| `provtoolbox-mini-primer.jsonld`   | ProvToolbox `modules-core/prov-jsonld/src/test/resources/mini-primer.jsonld` @ `a145a9e`      | 2026-08-07 |

`submission-example-3.jsonld` is copied verbatim from the submission's own
worked example: the PROV-N Primer's "Derek's article" scenario, rendered in
the submission's canonical compacted shape (bare, unprefixed `@type`/term
names such as `"Entity"`, `"generatedEntity"`, `"type"`, resolved against the
context URL `https://openprovenance.org/prov-jsonld/context.jsonld`). It is
vendored so `test_interop_submission_example` exercises the decoder against
prose from the spec itself, not just documents this library's own encoder
produced.

`provtoolbox-mini-primer.jsonld` is copied verbatim from ProvToolbox, the
Java PROV reference implementation, at commit `a145a9e` (2020-02-18). It
encodes the same underlying scenario but in ProvToolbox's older,
`prov:`-prefixed dialect (`"@type": "prov:Entity"`, `"prov:type"`, and a
context URL of `http://openprovenance.org/prov-jsonld.json` rather than the
submission's `https://openprovenance.org/prov-jsonld/context.jsonld`) — this
library's decoder tolerates that spelling deliberately (see
`_strip_prov_prefix` in `src/prov/serializers/provjsonld.py`), and this
fixture is what exercises that tolerance end to end. It also differs from
the submission example in one substantive way: `ex:derek`'s `foaf:mbox` is an
empty plain string (`{"@value": ""}`) rather than the submission's
`"<mailto:derek@example.org>"` — this is ProvToolbox's fixture as retrieved,
not a transcription error, so the test's expected document reproduces it
verbatim rather than the submission's mbox value. It also carries a trailing
tab on one line (its `"@language" : "EN"` line), preserved here rather than
stripped, since the point of vendoring is to keep the file byte-identical to
upstream; this is why `.pre-commit-config.yaml` excludes this directory from
the trailing-whitespace/EOF-newline hooks, the same as the `json`/`xml`/
`rdf`/`unification` fixture directories.

## Licence

`submission-example-3.jsonld` is redistributed here as permitted under the
**W3C Software and Document Licence**
(<https://www.w3.org/copyright/software-license-2023/>); it is copyright ©
World Wide Web Consortium (MIT, ERCIM, Keio, Beihang) and included unmodified
for the sole purpose of interop testing in this project's test suite.

`provtoolbox-mini-primer.jsonld` is redistributed from ProvToolbox
(<https://github.com/trungdong/ProvToolbox>), an MIT-licensed project
(copyright King's College London and the University of Southampton),
included unmodified for the same purpose.

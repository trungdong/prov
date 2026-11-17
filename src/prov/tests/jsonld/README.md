# Vendored PROV-JSONLD interop fixtures

These files are vendored, third-party PROV-JSONLD documents used by the
`test_interop_*` tests in `test_jsonld.py` to prove `prov`'s PROV-JSONLD
decoder can read other implementations' output, not just its own.

## Files and sources

| File                              | Source                                                                                      | Retrieved  |
|------------------------------------|-----------------------------------------------------------------------------------------------|------------|
| `submission-example-3.jsonld`      | Example 1, §3 of <https://www.w3.org/submissions/prov-jsonld/> (the W3C member submission)    | 2026-08-07 |
| `provtoolbox-node-reference.jsonld` | ProvToolbox `modules-core/prov-jsonld/src/test/resources/prov-jsonld-7/node-reference.jsonld` @ `21a37e0` | 2026-10-16 |
| `provtoolbox-string.jsonld` | ProvToolbox `modules-core/prov-jsonld/src/test/resources/prov-jsonld-7/string.jsonld` @ `21a37e0` | 2026-10-16 |
| `provtoolbox-string-with-colon.jsonld` | ProvToolbox `modules-core/prov-jsonld/src/test/resources/prov-jsonld-7/string-with-colon.jsonld` @ `21a37e0` | 2026-10-16 |

`submission-example-3.jsonld` is the submission's worked example, the PROV-N
Primer's "Derek's article" scenario in the submission's compacted shape (bare
`@type` and term names such as `"Entity"` and `"generatedEntity"`, resolved
against the context URL `https://openprovenance.org/prov-jsonld/context.jsonld`).

The three `provtoolbox-*` fixtures from `prov-jsonld-7/` are copied verbatim from
ProvToolbox at commit `21a37e0` (tagged `ProvToolbox-2.2.5`). They pin the
attribute-value rule of the 2026-10-14 schema revision
([openprov/prov-jsonld#7](https://github.com/openprov/prov-jsonld/issues/7), still
open). `provtoolbox-node-reference.jsonld` holds the qualified name `ex:shed` as a
node reference, `{"@id": "ex:shed"}`. `provtoolbox-string.jsonld` holds
`"ex:shed"` as a bare string under an extension property, which is an
`xsd:string`. `provtoolbox-string-with-colon.jsonld` holds `"Meeting at
10:30"`, a string with a colon that is not a qualified name.

## Licence

`submission-example-3.jsonld` is redistributed here as permitted under the
**W3C Software and Document Licence**
(<https://www.w3.org/copyright/software-license-2023/>); it is copyright ©
World Wide Web Consortium (MIT, ERCIM, Keio, Beihang) and included unmodified
for the sole purpose of interop testing in this project's test suite.

The three `prov-jsonld-7/` fixtures are redistributed from ProvToolbox
(<https://github.com/trungdong/ProvToolbox>), an MIT-licensed project (copyright King's
College London and the University of Southampton), included unmodified for the same
purpose.

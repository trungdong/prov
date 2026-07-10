# Vendored W3C PROV conformance schemas

These schema files are vendored so the `test_xml_schema.py` and
`test_json_schema.py` modules can validate `prov`'s serializer output against
the official PROV-XML schema and the PROV-JSON member submission's JSON
schema **offline** (no network access required in CI). They are unmodified
except for one XSD `schemaLocation` rewritten from an absolute `w3.org` URL
to a relative, in-tree path (noted below) so the XSD set forms a closed,
offline-resolvable set; `prov-json.schema.json` is byte-for-byte the
submission's schema (pretty-printed) with no rewrites needed (it has no
external `$ref`s).

## Files and sources

| File                    | Source URL                                                         | Retrieved  |
|-------------------------|----------------------------------------------------------------------|------------|
| `prov.xsd`               | <https://www.w3.org/ns/prov.xsd>                                    | 2026-07-10 |
| `prov-core.xsd`          | <https://www.w3.org/ns/prov-core.xsd>                               | 2026-07-10 |
| `prov-dictionary.xsd`    | <https://www.w3.org/ns/prov-dictionary.xsd>                         | 2026-07-10 |
| `prov-links.xsd`         | <https://www.w3.org/ns/prov-links.xsd>                              | 2026-07-10 |
| `xml.xsd`                | <https://www.w3.org/2001/xml.xsd>                                   | 2026-07-10 |
| `prov-json.schema.json`  | <https://www.w3.org/submissions/prov-json/schema>                   | 2026-07-10 |

`prov.xsd` is the entry point referenced by the PROV-XML specification
(<https://www.w3.org/TR/prov-xml/>); it `xs:include`s `prov-core.xsd`,
`prov-dictionary.xsd`, and `prov-links.xsd`. `prov-core.xsd` in turn
`xs:import`s the standard XML-attributes schema (`xml:lang`/`xml:base`/etc.),
which is vendored here as `xml.xsd`. That import's `schemaLocation` was
rewritten from `http://www.w3.org/2001/xml.xsd` to the relative `xml.xsd` so
`lxml.etree.XMLSchema` can compile the whole set without any network access.
No other `schemaLocation` values were changed — the `prov-core.xsd` /
`prov-dictionary.xsd` / `prov-links.xsd` includes were already relative
filenames in the upstream documents.

`prov-core.xsd` also declares (but never uses) an `xs:import` for the
`http://www.w3.org/1999/xhtml/datatypes/` namespace with no `schemaLocation`;
this is harmless (no element or type from that namespace is actually
referenced) and was left as-is.

Closure was verified by grepping every vendored file for `schemaLocation=`
and `xs:import`/`xs:include` elements and confirming each target is itself
vendored in this directory; see the roadmap step 30 audit notes
(`docs/superpowers/specs/2026-07-10-conformance-audit-findings.md`, §3.1)
for the verification transcript.

`prov-json.schema.json` is the schema linked from §2.3 ("Validating PROV-JSON
Documents") of *A JSON Representation for the PROV Data Model* (the PROV-JSON
member submission, <https://www.w3.org/submissions/prov-json/>), retrieved
from the URL that section links to
(<https://www.w3.org/submissions/prov-json/schema>). It declares
`"$schema": "http://json-schema.org/draft-04/schema#"` — `jsonschema>=4`
still ships a `Draft4Validator`, so it is used as-is (no upgrade/rewrite);
`test_json_schema.py` selects the validator dynamically via
`jsonschema.validators.validator_for(schema)` rather than hard-coding that
draft. Two authoring quirks in the schema itself were noted during the audit
(not fixed here — the file is vendored verbatim) and are recorded in
`docs/superpowers/specs/2026-07-10-conformance-audit-findings.md` §3.2: the
`wasEndedby` property key (both at the document root and inside
`definitions.bundle`) is misspelled — the submission's own prose (§3.2.5) and
`prov`'s serializer both use `wasEndedBy` — and the document-root object sets
`"additionalProperties": false` while `definitions.bundle` does not, so a
`mentionOf` relation (a PROV-Links extension postdating this submission, and
therefore absent from the schema entirely) is only accepted inside a named
bundle, not at the document root.

## Licence

The XSD files are W3C Recommendation-track normative schemas; the PROV-JSON
schema is linked from a W3C Member Submission (not Recommendation-track, but
published under the same W3C document terms). All are redistributed here as
permitted under the **W3C Software and Document Licence**:
<https://www.w3.org/copyright/software-license-2023/> (formerly
<https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document>).
They are copyright © World Wide Web Consortium (MIT, ERCIM, Keio, Beihang)
and are included unmodified (aside from the single XSD relative-path rewrite
noted above) for the sole purpose of offline schema validation in this
project's test suite.

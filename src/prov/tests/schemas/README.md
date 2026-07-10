# Vendored W3C PROV-XML schemas

These XSD files are vendored so `test_xml_schema.py` can validate `prov`'s XML
serializer output against the official PROV-XML schema **offline** (no network
access required in CI). They are unmodified except for one `schemaLocation`
rewritten from an absolute `w3.org` URL to a relative, in-tree path (noted
below) so the schema set forms a closed, offline-resolvable set.

## Files and sources

| File                  | Source URL                                       | Retrieved  |
|-----------------------|---------------------------------------------------|------------|
| `prov.xsd`             | <https://www.w3.org/ns/prov.xsd>                  | 2026-07-10 |
| `prov-core.xsd`        | <https://www.w3.org/ns/prov-core.xsd>             | 2026-07-10 |
| `prov-dictionary.xsd`  | <https://www.w3.org/ns/prov-dictionary.xsd>       | 2026-07-10 |
| `prov-links.xsd`       | <https://www.w3.org/ns/prov-links.xsd>            | 2026-07-10 |
| `xml.xsd`              | <https://www.w3.org/2001/xml.xsd>                 | 2026-07-10 |

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

## Licence

These files are W3C Recommendation-track normative schemas, redistributed
here as permitted under the **W3C Software and Document Licence**:
<https://www.w3.org/copyright/software-license-2023/> (formerly
<https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document>).
They are copyright © World Wide Web Consortium (MIT, ERCIM, Keio, Beihang)
and are included unmodified (aside from the single relative-path rewrite
noted above) for the sole purpose of offline schema validation in this
project's test suite.

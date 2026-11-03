# Vendored W3C PROV conformance schemas

These schema files are vendored so the `test_xml_schema.py` and
`test_json_schema.py` modules can validate `prov`'s serializer output against
the official PROV-XML schema and the PROV-JSON member submission's JSON
schema **offline** (no network access required in CI). They are unmodified
except for one XSD `schemaLocation` rewritten from an absolute `w3.org` URL
to a relative, in-tree path (noted below) so the XSD set forms a closed,
offline-resolvable set; `prov-json.schema.json` is byte-for-byte the
submission's schema (pretty-printed), which has no external `$ref`s.

## Files and sources

| File                    | Source URL                                                         | Retrieved  |
|-------------------------|----------------------------------------------------------------------|------------|
| `prov.xsd`               | <https://www.w3.org/ns/prov.xsd>                                    | 2026-07-10 |
| `prov-core.xsd`          | <https://www.w3.org/ns/prov-core.xsd>                               | 2026-07-10 |
| `prov-dictionary.xsd`    | <https://www.w3.org/ns/prov-dictionary.xsd>                         | 2026-07-10 |
| `prov-links.xsd`         | <https://www.w3.org/ns/prov-links.xsd>                              | 2026-07-10 |
| `xml.xsd`                | <https://www.w3.org/2001/xml.xsd>                                   | 2026-07-10 |
| `prov-json.schema.json`  | <https://www.w3.org/submissions/prov-json/schema>                   | 2026-07-10 |
| `prov-jsonld.schema.json` | <https://openprovenance.org/prov-jsonld/schema-2026-10-14.json>    | 2026-10-16 |

`prov.xsd` is the entry point of the PROV-XML specification
(<https://www.w3.org/TR/prov-xml/>). It `xs:include`s `prov-core.xsd`,
`prov-dictionary.xsd` and `prov-links.xsd`, and `prov-core.xsd` `xs:import`s
`xml.xsd`. That import's `schemaLocation` is rewritten from
`http://www.w3.org/2001/xml.xsd` to the relative `xml.xsd`, so
`lxml.etree.XMLSchema` compiles the whole set offline. No other
`schemaLocation` changed, and every include and import target is in this
directory. `prov-core.xsd` also declares an `xs:import` for the
`http://www.w3.org/1999/xhtml/datatypes/` namespace with no `schemaLocation`.
Nothing references that namespace, and the import stays as published.

`prov-json.schema.json` is the schema that section 2.3 of the PROV-JSON member
submission (<https://www.w3.org/submissions/prov-json/>) links. It declares
`"$schema": "http://json-schema.org/draft-04/schema#"`, and `test_json_schema.py`
selects the validator with `jsonschema.validators.validator_for(schema)`. The
file is vendored verbatim, with two quirks in the schema itself:

- The property key `wasEndedby` (at the document root and in `definitions.bundle`)
  is misspelt, where the submission's prose and `prov`'s serializer use `wasEndedBy`.
- The document root sets `"additionalProperties": false` and `definitions.bundle`
  does not, so a `mentionOf` relation, which the schema lacks entirely, is accepted
  only inside a named bundle.

`prov-jsonld.schema.json` is the 2026-10-14 revision of the PROV-JSONLD JSON
Schema. It revises the member submission's schema
(<https://www.w3.org/submissions/prov-jsonld/schema.json>) for
[openprov/prov-jsonld#7](https://github.com/openprov/prov-jsonld/issues/7), which is
still open: a `node_reference` (`{"@id": ...}`) is accepted in every value array,
a bare string under an extension property or `value` is any string
(`ArrayOfStringValues`), and the statement `@type` patterns are anchored. It
declares `"$schema": "http://json-schema.org/draft-07/schema#"`. The matching
context file is package data at `src/prov/serializers/prov-jsonld-context.jsonld`
(from <https://www.w3.org/submissions/prov-jsonld/context.jsonld>), because the
serializer's `context="embed"` option embeds it.

## Licence

The PROV-JSONLD schema is the 2026-10-14 revision of the member submission's
schema, published in the
[openprov/prov-jsonld](https://github.com/openprov/prov-jsonld) repository by
the submission's authors, Luc Moreau and Trung Dong Huynh. It is included
unmodified for the same purpose as the files below.

The XSD files are W3C Recommendation-track normative schemas; the PROV-JSON
schema is linked from a W3C Member Submission (not Recommendation-track, but
published under the same W3C document terms). Both are redistributed here as
permitted under the **W3C Software and Document Licence**:
<https://www.w3.org/copyright/software-license-2023/> (formerly
<https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document>).
They are copyright © World Wide Web Consortium (MIT, ERCIM, Keio, Beihang)
and are included unmodified (aside from the single XSD relative-path rewrite
noted above) for the sole purpose of offline schema validation in this
project's test suite.

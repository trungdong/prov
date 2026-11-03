# PROV-N conformance corpus

Fixtures for `test_provn_corpus.py`, in four directories:

| Directory | Source | Licence | Profile |
|---|---|---|---|
| `spec/prov-n/` | Examples in the [PROV-N Recommendation](https://www.w3.org/TR/2013/REC-prov-n-20130430/), extracted by `extract_spec_examples.py`; fragments are wrapped in a document declaring a default namespace and the prefixes they use | W3C Document Licence | strict |
| `spec/prov-dm/` | Examples in the [PROV-DM Recommendation](https://www.w3.org/TR/2013/REC-prov-dm-20130430/), same treatment | W3C Document Licence | strict |
| `provtoolbox/` | `modules-core/prov-n/src/test/resources/prov/*.provn` from [ProvToolbox](https://github.com/lucmoreau/ProvToolbox) | MIT | default |
| `provtoolbox-corpus/` | PROV-N that ProvToolbox's writer produced from the shared test corpus (`modules-legacy/prov-n` test output); each file has a PROV-JSON fixture of the same name in `../json/` | MIT | default |

## Exclusion sets

Each set is a dictionary in `test_provn_corpus.py`, whose entries carry the reason for each file. The module's dictionaries are the only list of names.

- `EXCLUDED_SPEC_EXAMPLES` holds the specification examples that are not complete statements, that the formal grammar rejects although the Recommendation's prose presents them as valid, or that use an undeclared prefix in a qualified-name value.
- `EXCLUDED_PROVTOOLBOX_DOCUMENTS` holds the three hand-written ProvToolbox documents that fall outside what a document under the default profile can express.
- `KNOWN_DIFFERENCES` holds the `provtoolbox-corpus/` files whose output differs from the PROV-JSON fixture of the same name, either because the generator embedded the wall-clock time of the corpus build or because its datatype palette lacks three datatypes.

## JSON fixtures with no ProvToolbox counterpart

`test_every_json_fixture_has_a_counterpart_or_is_listed` reads this list. A JSON fixture with no `provtoolbox-corpus/` file must appear here.

`attr_association_one_role_attr43`, `attr_association_one_role_attr44`,
`attr_entity_one_attr43`, `attr_entity_one_attr44`,
`attr_entity_one_location_attr43`, `attr_entity_one_location_attr44`,
`attr_entity_one_other_attr43`, `attr_entity_one_other_attr44`,
`attr_entity_one_value_attr43`, `attr_entity_one_value_attr44`.

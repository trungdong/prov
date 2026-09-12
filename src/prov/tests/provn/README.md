# PROV-N conformance corpus

Fixtures for `test_provn_corpus.py`. Three sets:

| Directory | Source | Licence | Profile |
|---|---|---|---|
| `spec/prov-n/` | Examples in the [PROV-N Recommendation](https://www.w3.org/TR/2013/REC-prov-n-20130430/), extracted by `extract_spec_examples.py`; fragments are wrapped in a document declaring a default namespace and the prefixes they use | W3C Document Licence | strict |
| `spec/prov-dm/` | Examples in the [PROV-DM Recommendation](https://www.w3.org/TR/2013/REC-prov-dm-20130430/), same treatment | W3C Document Licence | strict |
| `provtoolbox/` | `modules-core/prov-n/src/test/resources/prov/*.provn` from [ProvToolbox](https://github.com/lucmoreau/ProvToolbox) | MIT | default |
| `provtoolbox-corpus/` | PROV-N that ProvToolbox's writer produced from the shared test corpus (`modules-legacy/prov-n` test output); each file has a PROV-JSON fixture of the same name in `../json/` | MIT | default |

## Specification examples that do not parse

Each of these is either not a complete PROV-N statement, or a statement the formal grammar
rejects even though the Recommendation's prose presents it as valid. Listed in
`EXCLUDED_SPEC_EXAMPLES`.

- `prov-n-example-16.provn` - the sixth `wasGeneratedBy` variant reuses `tr:WD-prov-dm-20111215`
  as its time argument, which is not a dateTime; a copy-paste artefact in the Recommendation's
  own text
- `prov-n-example-37.provn` - `wasAssociatedWith(ex:a1, ex:ag1)` gives the agent without the
  paired plan; production [20] requires them together
- `prov-n-example-52.provn`, `prov-n-example-53.provn` - a bare typed-literal pair, not a
  statement
- `prov-n-example-54.provn` - a bare qualified-name literal pair, not a statement
- `prov-n-example-55.provn`, `prov-n-example-56.provn` - a list of bare literals, not a
  statement
- `prov-n-example-59.provn` - a literal ellipsis elides the rest of the example, not complete
  PROV-N
- `prov-n-example-61.provn` - the bundle identifier `b` has no declared default namespace; the
  example illustrates qualified-name resolution for `ex:e001`, not the bundle name itself
- `prov-n-example-63.provn`, `prov-n-example-64.provn` - `dictExt:hadMembers(...)` is an
  extensibility expression (`prefix:name(...)`), unsupported by design
- `prov-dm-example-03.provn`, `prov-dm-example-04.provn` - `used`/`wasGeneratedBy` give only the
  entity/activity without the paired time; the formal grammar requires them together
- `prov-dm-example-05.provn`, `prov-dm-example-06.provn` - a literal ellipsis elides the
  bundle's content, not complete PROV-N
- `prov-dm-example-16.provn` - `wasGeneratedBy` gives only the entity without the paired time
- `prov-dm-example-19.provn` - a spec typo leaves the agent's attribute list missing its
  closing `]`
- `prov-dm-example-24.provn` - `wasAssociatedWith` and `wasGeneratedBy` give only the
  activity/entity without the paired plan or time
- `prov-dm-example-34.provn`, `prov-dm-example-52.provn` - `wasAssociatedWith` gives only the
  activity and agent without the paired plan
- `prov-dm-example-53.provn`, `prov-dm-example-56.provn`, `prov-dm-example-63.provn` - `used`
  gives only the activity and entity without the paired time
- `prov-dm-example-55.provn` - `used`/`wasGeneratedBy` give only the activity/entity without
  the paired time
- `prov-dm-example-57.provn` - a list of bare literals, not a statement
- `prov-dm-example-58.provn` - a bare typed-literal pair, not a statement
- `prov-dm-example-59.provn` - a bare qualified-name literal, not a statement

## ProvToolbox documents that do not parse under the default profile

Listed in `EXCLUDED_PROVTOOLBOX_DOCUMENTS`.

- `container0.provn` - several entity identifiers are bare local names (`\\--`, `\\-`, `\\.`)
  with no default namespace declared anywhere in the document
- `container1.provn`, `prov-family.provn`, `prov-family-graphics.provn` - use the
  PROV-Dictionary keyword `derivedByInsertionFrom`, out of scope
- `container2.provn` - `%% <http://example.org/type>` uses a bare IRI as a datatype; production
  [53] requires `datatype` to be a `qualifiedName`

## JSON fixtures with no ProvToolbox counterpart

`attr_association_one_role_attr43`, `attr_association_one_role_attr44`,
`attr_entity_one_attr43`, `attr_entity_one_attr44`,
`attr_entity_one_location_attr43`, `attr_entity_one_location_attr44`,
`attr_entity_one_other_attr43`, `attr_entity_one_other_attr44`,
`attr_entity_one_value_attr43`, `attr_entity_one_value_attr44`. These were added to
the JSON corpus after the ProvToolbox output was generated.

## Known differences

ProvToolbox's shared Java test-data generator (`RoundTripFromJavaTest`/`ProvFrameworkTest`)
has moved on since the PROV-JSON fixtures were captured, so its freshly-built PROV-N no longer
matches them byte for byte. Two kinds of drift, both listed in `KNOWN_DIFFERENCES`:

**Dynamic timestamp** (80 files) - the generator calls `newTimeNow()` for a record's
time or for a demonstration `xsd:dateTime` value, embedding the wall-clock time at the corpus
build rather than the fixture's fixed value:

`activity3.provn`, `activity5.provn`, `activity6.provn`, `activity7.provn`, `activity8.provn`, `activity9.provn`, `agent6.provn`, `agent7.provn`, `agent8.provn`, `association7.provn`, `association9.provn`, `attr_association_one_role_attr27.provn`, `attr_association_one_role_attr32.provn`, `attr_entity_one_attr27.provn`, `attr_entity_one_attr32.provn`, `attr_entity_one_location_attr27.provn`, `attr_entity_one_location_attr32.provn`, `attr_entity_one_other_attr27.provn`, `attr_entity_one_other_attr32.provn`, `attr_entity_one_value_attr27.provn`, `attr_entity_one_value_attr32.provn`, `attribution7.provn`, `attribution8.provn`, `communication6.provn`, `communication7.provn`, `delegation7.provn`, `delegation8.provn`, `derivation8.provn`, `derivation9.provn`, `end10.provn`, `end7.provn`, `end8.provn`, `entity10.provn`, `entity5.provn`, `entity6.provn`, `entity7.provn`, `entity8.provn`, `entity9.provn`, `generation4.provn`, `generation5.provn`, `generation7.provn`, `influence6.provn`, `influence7.provn`, `invalidation4.provn`, `invalidation5.provn`, `invalidation7.provn`, `scruffy-end1-M.provn`, `scruffy-end1-S.provn`, `scruffy-end2-M.provn`, `scruffy-end2-S.provn`, `scruffy-end3-M.provn`, `scruffy-end3-S.provn`, `scruffy-end4-M.provn`, `scruffy-end4-S.provn`, `scruffy-generation1-M.provn`, `scruffy-generation1-S.provn`, `scruffy-generation2-M.provn`, `scruffy-generation2-S.provn`, `scruffy-invalidation1-M.provn`, `scruffy-invalidation1-S.provn`, `scruffy-invalidation2-M.provn`, `scruffy-invalidation2-S.provn`, `scruffy-start1-M.provn`, `scruffy-start1-S.provn`, `scruffy-start2-M.provn`, `scruffy-start2-S.provn`, `scruffy-start3-M.provn`, `scruffy-start3-S.provn`, `scruffy-start4-M.provn`, `scruffy-start4-S.provn`, `scruffy-usage1-M.provn`, `scruffy-usage1-S.provn`, `scruffy-usage2-M.provn`, `scruffy-usage2-S.provn`, `start10.provn`, `start7.provn`, `start8.provn`, `usage4.provn`, `usage5.provn`, `usage7.provn`

**Datatype-palette drift** (79 files) - the generator's shared
`addTypes()`/`addLocations()` helper has gained `xsd:gMonth`, `xsd:yearMonthDuration` and
`xsd:dayTimeDuration` since the fixture was captured, so these files' position in an indexed
demonstration series (or their combined type/location list) no longer lines up with the JSON
fixture of the same name:

`attr_activity0.provn`, `attr_agent0.provn`, `attr_association0.provn`, `attr_association_one_role_attr29.provn`, `attr_association_one_role_attr30.provn`, `attr_association_one_role_attr31.provn`, `attr_association_one_role_attr33.provn`, `attr_association_one_role_attr34.provn`, `attr_association_one_role_attr35.provn`, `attr_association_one_role_attr36.provn`, `attr_association_one_role_attr37.provn`, `attr_association_one_role_attr38.provn`, `attr_association_one_role_attr39.provn`, `attr_association_one_role_attr40.provn`, `attr_association_one_role_attr41.provn`, `attr_association_one_role_attr42.provn`, `attr_attribution0.provn`, `attr_communication0.provn`, `attr_delegation0.provn`, `attr_derivation0.provn`, `attr_end0.provn`, `attr_entity0.provn`, `attr_entity_one_attr29.provn`, `attr_entity_one_attr30.provn`, `attr_entity_one_attr31.provn`, `attr_entity_one_attr33.provn`, `attr_entity_one_attr34.provn`, `attr_entity_one_attr35.provn`, `attr_entity_one_attr36.provn`, `attr_entity_one_attr37.provn`, `attr_entity_one_attr38.provn`, `attr_entity_one_attr39.provn`, `attr_entity_one_attr40.provn`, `attr_entity_one_attr41.provn`, `attr_entity_one_attr42.provn`, `attr_entity_one_location_attr29.provn`, `attr_entity_one_location_attr30.provn`, `attr_entity_one_location_attr31.provn`, `attr_entity_one_location_attr33.provn`, `attr_entity_one_location_attr34.provn`, `attr_entity_one_location_attr35.provn`, `attr_entity_one_location_attr36.provn`, `attr_entity_one_location_attr37.provn`, `attr_entity_one_location_attr38.provn`, `attr_entity_one_location_attr39.provn`, `attr_entity_one_location_attr40.provn`, `attr_entity_one_location_attr41.provn`, `attr_entity_one_location_attr42.provn`, `attr_entity_one_other_attr29.provn`, `attr_entity_one_other_attr30.provn`, `attr_entity_one_other_attr31.provn`, `attr_entity_one_other_attr33.provn`, `attr_entity_one_other_attr34.provn`, `attr_entity_one_other_attr35.provn`, `attr_entity_one_other_attr36.provn`, `attr_entity_one_other_attr37.provn`, `attr_entity_one_other_attr38.provn`, `attr_entity_one_other_attr39.provn`, `attr_entity_one_other_attr40.provn`, `attr_entity_one_other_attr41.provn`, `attr_entity_one_other_attr42.provn`, `attr_entity_one_value_attr29.provn`, `attr_entity_one_value_attr30.provn`, `attr_entity_one_value_attr31.provn`, `attr_entity_one_value_attr33.provn`, `attr_entity_one_value_attr34.provn`, `attr_entity_one_value_attr35.provn`, `attr_entity_one_value_attr36.provn`, `attr_entity_one_value_attr37.provn`, `attr_entity_one_value_attr38.provn`, `attr_entity_one_value_attr39.provn`, `attr_entity_one_value_attr40.provn`, `attr_entity_one_value_attr41.provn`, `attr_entity_one_value_attr42.provn`, `attr_generation0.provn`, `attr_influence0.provn`, `attr_invalidation0.provn`, `attr_start0.provn`, `attr_usage0.provn`

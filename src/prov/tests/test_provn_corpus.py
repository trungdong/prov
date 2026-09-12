"""PROV-N conformance corpus (src/prov/tests/provn/README.md).

Three sets: the examples of the PROV-N and PROV-DM Recommendations (strict
grammar, and round-trip through our writer), ProvToolbox's own PROV-N test
documents (default profile), and the PROV-N that ProvToolbox's writer
produced from the shared test corpus, compared for equality with the
PROV-JSON fixture of the same name (the interoperability claim)."""

from pathlib import Path

import pytest

from prov.model import ProvDocument

CORPUS = Path(__file__).parent / "provn"
JSON_FIXTURES = Path(__file__).parent / "json"

# Specification examples that are not complete statements, or that the
# formal grammar rejects even though the Recommendation's prose presents
# them as valid; keep this list in step with provn/README.md.
EXCLUDED_SPEC_EXAMPLES: dict[str, str] = {
    "prov-n-example-16.provn": (
        "the sixth wasGeneratedBy variant reuses tr:WD-prov-dm-20111215 as its "
        "time argument, which is not a dateTime; a copy-paste artefact in the "
        "Recommendation's own text"
    ),
    "prov-n-example-37.provn": (
        "wasAssociatedWith(ex:a1, ex:ag1) gives the agent without the paired "
        "plan; production [20] requires them together"
    ),
    "prov-n-example-52.provn": "a bare typed-literal pair, not a statement",
    "prov-n-example-53.provn": "a bare typed-literal pair, not a statement",
    "prov-n-example-54.provn": "a bare qualified-name literal pair, not a statement",
    "prov-n-example-55.provn": "a list of bare literals, not a statement",
    "prov-n-example-56.provn": "a list of bare literals, not a statement",
    "prov-n-example-59.provn": (
        "a literal ellipsis elides the rest of the example, not complete PROV-N"
    ),
    "prov-n-example-61.provn": (
        "the bundle identifier 'b' has no declared default namespace; the "
        "example illustrates qualified-name resolution for ex:e001, not the "
        "bundle name itself"
    ),
    "prov-n-example-63.provn": (
        "the dictionary set-of-pairs literal '{(\"k1\",e1), ...}' is "
        "PROV-Dictionary syntax the lexer has no punctuation for, "
        "unsupported by design"
    ),
    "prov-n-example-64.provn": (
        "dictExt:hadMembers(...) is an extensibility expression "
        "(prefix:name(...)), unsupported by design"
    ),
    "prov-dm-example-03.provn": (
        "used and wasGeneratedBy give only the entity/activity without the "
        "paired time; the formal grammar requires them together"
    ),
    "prov-dm-example-04.provn": (
        "used and wasGeneratedBy give only the entity/activity without the paired time"
    ),
    "prov-dm-example-05.provn": (
        "a literal ellipsis elides the bundle's content, not complete PROV-N"
    ),
    "prov-dm-example-06.provn": (
        "a literal ellipsis elides the bundle's content, not complete PROV-N"
    ),
    "prov-dm-example-16.provn": "wasGeneratedBy gives only the entity without the paired time",
    "prov-dm-example-19.provn": "a spec typo leaves the agent's attribute list missing its closing ']'",
    "prov-dm-example-24.provn": (
        "wasAssociatedWith and wasGeneratedBy give only the activity/entity "
        "without the paired plan or time"
    ),
    "prov-dm-example-34.provn": (
        "wasAssociatedWith gives only the activity and agent without the paired plan"
    ),
    "prov-dm-example-52.provn": (
        "wasAssociatedWith gives only the activity and agent without the paired plan"
    ),
    "prov-dm-example-53.provn": "used gives only the activity and entity without the paired time",
    "prov-dm-example-55.provn": (
        "used and wasGeneratedBy give only the activity/entity without the paired time"
    ),
    "prov-dm-example-56.provn": "used gives only the activity and entity without the paired time",
    "prov-dm-example-57.provn": "a list of bare literals, not a statement",
    "prov-dm-example-58.provn": "a bare typed-literal pair, not a statement",
    "prov-dm-example-59.provn": "a bare qualified-name literal, not a statement",
    "prov-dm-example-63.provn": "used gives only the activity and entity without the paired time",
}

# ProvToolbox-written documents that legitimately differ from our JSON
# fixture, because ProvToolbox's own test-data generator has moved on since
# the fixture was captured. Each entry is documented on
# docs/reference/conformance.md.
_REASON_DYNAMIC_TIME = (
    "ProvToolbox's shared Java test-data generator calls newTimeNow() for this "
    "record's dateTime demonstration value(s), embedding the wall-clock time at "
    "the corpus build rather than the JSON fixture's fixed value"
)
_REASON_PALETTE_DRIFT = (
    "ProvToolbox's shared addTypes()/addLocations() helper "
    "(ProvFrameworkTest.java) does not cover xsd:gMonth, "
    "xsd:yearMonthDuration or xsd:dayTimeDuration, each of which the "
    "PROV-JSON fixture's datatype/location list carries six times, so this "
    "file's position in the indexed demonstration series (or its combined "
    "type/location list) no longer lines up with the JSON fixture of the "
    "same name"
)
_DYNAMIC_TIME_DIFFERENCES = [
    "activity3.provn",
    "activity5.provn",
    "activity6.provn",
    "activity7.provn",
    "activity8.provn",
    "activity9.provn",
    "agent6.provn",
    "agent7.provn",
    "agent8.provn",
    "association7.provn",
    "association9.provn",
    "attr_association_one_role_attr27.provn",
    "attr_association_one_role_attr32.provn",
    "attr_entity_one_attr27.provn",
    "attr_entity_one_attr32.provn",
    "attr_entity_one_location_attr27.provn",
    "attr_entity_one_location_attr32.provn",
    "attr_entity_one_other_attr27.provn",
    "attr_entity_one_other_attr32.provn",
    "attr_entity_one_value_attr27.provn",
    "attr_entity_one_value_attr32.provn",
    "attribution7.provn",
    "attribution8.provn",
    "communication6.provn",
    "communication7.provn",
    "delegation7.provn",
    "delegation8.provn",
    "derivation8.provn",
    "derivation9.provn",
    "end10.provn",
    "end7.provn",
    "end8.provn",
    "entity10.provn",
    "entity5.provn",
    "entity6.provn",
    "entity7.provn",
    "entity8.provn",
    "entity9.provn",
    "generation4.provn",
    "generation5.provn",
    "generation7.provn",
    "influence6.provn",
    "influence7.provn",
    "invalidation4.provn",
    "invalidation5.provn",
    "invalidation7.provn",
    "scruffy-end1-M.provn",
    "scruffy-end1-S.provn",
    "scruffy-end2-M.provn",
    "scruffy-end2-S.provn",
    "scruffy-end3-M.provn",
    "scruffy-end3-S.provn",
    "scruffy-end4-M.provn",
    "scruffy-end4-S.provn",
    "scruffy-generation1-M.provn",
    "scruffy-generation1-S.provn",
    "scruffy-generation2-M.provn",
    "scruffy-generation2-S.provn",
    "scruffy-invalidation1-M.provn",
    "scruffy-invalidation1-S.provn",
    "scruffy-invalidation2-M.provn",
    "scruffy-invalidation2-S.provn",
    "scruffy-start1-M.provn",
    "scruffy-start1-S.provn",
    "scruffy-start2-M.provn",
    "scruffy-start2-S.provn",
    "scruffy-start3-M.provn",
    "scruffy-start3-S.provn",
    "scruffy-start4-M.provn",
    "scruffy-start4-S.provn",
    "scruffy-usage1-M.provn",
    "scruffy-usage1-S.provn",
    "scruffy-usage2-M.provn",
    "scruffy-usage2-S.provn",
    "start10.provn",
    "start7.provn",
    "start8.provn",
    "usage4.provn",
    "usage5.provn",
    "usage7.provn",
]
_PALETTE_DRIFT_DIFFERENCES = [
    "attr_activity0.provn",
    "attr_agent0.provn",
    "attr_association0.provn",
    "attr_association_one_role_attr29.provn",
    "attr_association_one_role_attr30.provn",
    "attr_association_one_role_attr31.provn",
    "attr_association_one_role_attr33.provn",
    "attr_association_one_role_attr34.provn",
    "attr_association_one_role_attr35.provn",
    "attr_association_one_role_attr36.provn",
    "attr_association_one_role_attr37.provn",
    "attr_association_one_role_attr38.provn",
    "attr_association_one_role_attr39.provn",
    "attr_association_one_role_attr40.provn",
    "attr_association_one_role_attr41.provn",
    "attr_association_one_role_attr42.provn",
    "attr_attribution0.provn",
    "attr_communication0.provn",
    "attr_delegation0.provn",
    "attr_derivation0.provn",
    "attr_end0.provn",
    "attr_entity0.provn",
    "attr_entity_one_attr29.provn",
    "attr_entity_one_attr30.provn",
    "attr_entity_one_attr31.provn",
    "attr_entity_one_attr33.provn",
    "attr_entity_one_attr34.provn",
    "attr_entity_one_attr35.provn",
    "attr_entity_one_attr36.provn",
    "attr_entity_one_attr37.provn",
    "attr_entity_one_attr38.provn",
    "attr_entity_one_attr39.provn",
    "attr_entity_one_attr40.provn",
    "attr_entity_one_attr41.provn",
    "attr_entity_one_attr42.provn",
    "attr_entity_one_location_attr29.provn",
    "attr_entity_one_location_attr30.provn",
    "attr_entity_one_location_attr31.provn",
    "attr_entity_one_location_attr33.provn",
    "attr_entity_one_location_attr34.provn",
    "attr_entity_one_location_attr35.provn",
    "attr_entity_one_location_attr36.provn",
    "attr_entity_one_location_attr37.provn",
    "attr_entity_one_location_attr38.provn",
    "attr_entity_one_location_attr39.provn",
    "attr_entity_one_location_attr40.provn",
    "attr_entity_one_location_attr41.provn",
    "attr_entity_one_location_attr42.provn",
    "attr_entity_one_other_attr29.provn",
    "attr_entity_one_other_attr30.provn",
    "attr_entity_one_other_attr31.provn",
    "attr_entity_one_other_attr33.provn",
    "attr_entity_one_other_attr34.provn",
    "attr_entity_one_other_attr35.provn",
    "attr_entity_one_other_attr36.provn",
    "attr_entity_one_other_attr37.provn",
    "attr_entity_one_other_attr38.provn",
    "attr_entity_one_other_attr39.provn",
    "attr_entity_one_other_attr40.provn",
    "attr_entity_one_other_attr41.provn",
    "attr_entity_one_other_attr42.provn",
    "attr_entity_one_value_attr29.provn",
    "attr_entity_one_value_attr30.provn",
    "attr_entity_one_value_attr31.provn",
    "attr_entity_one_value_attr33.provn",
    "attr_entity_one_value_attr34.provn",
    "attr_entity_one_value_attr35.provn",
    "attr_entity_one_value_attr36.provn",
    "attr_entity_one_value_attr37.provn",
    "attr_entity_one_value_attr38.provn",
    "attr_entity_one_value_attr39.provn",
    "attr_entity_one_value_attr40.provn",
    "attr_entity_one_value_attr41.provn",
    "attr_entity_one_value_attr42.provn",
    "attr_generation0.provn",
    "attr_influence0.provn",
    "attr_invalidation0.provn",
    "attr_start0.provn",
    "attr_usage0.provn",
]
KNOWN_DIFFERENCES: dict[str, str] = {
    **dict.fromkeys(_DYNAMIC_TIME_DIFFERENCES, _REASON_DYNAMIC_TIME),
    **dict.fromkeys(_PALETTE_DRIFT_DIFFERENCES, _REASON_PALETTE_DRIFT),
}

# ProvToolbox's own hand-written PROV-N test documents that fall outside
# what a document under the default profile can express. Documented in
# provn/README.md.
EXCLUDED_PROVTOOLBOX_DOCUMENTS: dict[str, str] = {
    "container0.provn": (
        "several entity identifiers are bare local names ('\\--', '\\-', "
        "'\\.') with no default namespace declared anywhere in the document"
    ),
    "container1.provn": (
        "derivedByInsertionFrom's dictionary set-of-pairs literal "
        "'{(\"k1\", ex:e2)}' is PROV-Dictionary syntax the lexer has no "
        "punctuation for, unsupported by design"
    ),
    "container2.provn": (
        "'%% <http://example.org/type>' uses a bare IRI as a datatype; "
        "production [53] requires datatype to be a qualifiedName"
    ),
    "prov-family.provn": (
        "derivedByInsertionFrom's dictionary set-of-pairs literal "
        "'{('tr:prov-dm', tr2011:WD-prov-dm-20111018)}' is PROV-Dictionary "
        "syntax the lexer has no punctuation for, unsupported by design"
    ),
    "prov-family-graphics.provn": (
        "derivedByInsertionFrom's dictionary set-of-pairs literal "
        "'{('tr:prov-dm', tr2011:WD-prov-dm-20111018)}' is PROV-Dictionary "
        "syntax the lexer has no punctuation for, unsupported by design"
    ),
}


def _files(subdir: str) -> list[Path]:
    return sorted((CORPUS / subdir).glob("*.provn"))


def _param(subdir: str, excluded: dict[str, str] | None = None):
    params = []
    for path in _files(subdir):
        marks = []
        if excluded and path.name in excluded:
            marks.append(pytest.mark.xfail(strict=True, reason=excluded[path.name]))
        params.append(pytest.param(path, id=path.name, marks=marks))
    return params


@pytest.mark.parametrize("path", _param("spec/prov-n", EXCLUDED_SPEC_EXAMPLES))
def test_prov_n_spec_examples_parse_strictly_and_round_trip(path):
    document = ProvDocument.deserialize(str(path), format="provn", profile="strict")
    reloaded = ProvDocument.deserialize(
        content=document.get_provn(strict=True), format="provn", profile="strict"
    )
    assert reloaded == document


@pytest.mark.parametrize("path", _param("spec/prov-dm", EXCLUDED_SPEC_EXAMPLES))
def test_prov_dm_spec_examples_parse_strictly_and_round_trip(path):
    document = ProvDocument.deserialize(str(path), format="provn", profile="strict")
    reloaded = ProvDocument.deserialize(
        content=document.get_provn(strict=True), format="provn", profile="strict"
    )
    assert reloaded == document


@pytest.mark.parametrize("path", _param("provtoolbox", EXCLUDED_PROVTOOLBOX_DOCUMENTS))
def test_provtoolbox_documents_parse(path):
    document = ProvDocument.deserialize(str(path), format="provn")
    assert document.get_records() or document.has_bundles()


@pytest.mark.parametrize("path", _param("provtoolbox-corpus", KNOWN_DIFFERENCES))
def test_provtoolbox_corpus_equals_json_fixture(path):
    expected = ProvDocument.deserialize(
        str(JSON_FIXTURES / f"{path.stem}.json"), format="json"
    )
    document = ProvDocument.deserialize(str(path), format="provn")
    assert document == expected


def test_every_json_fixture_has_a_counterpart_or_is_listed():
    readme = (CORPUS / "README.md").read_text()
    have = {p.stem for p in _files("provtoolbox-corpus")}
    for path in sorted(JSON_FIXTURES.glob("*.json")):
        if path.stem not in have:
            assert path.stem in readme, (
                f"{path.stem} has no counterpart and is not listed"
            )

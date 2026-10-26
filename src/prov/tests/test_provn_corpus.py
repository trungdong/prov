"""PROV-N conformance corpus (src/prov/tests/provn/README.md).

Three sets: the examples of the PROV-N and PROV-DM Recommendations (strict
grammar, and round-trip through our writer), ProvToolbox's own PROV-N test
documents (default profile), and the PROV-N that ProvToolbox's writer
produced from the shared test corpus, compared for equality with the
PROV-JSON fixture of the same name (the interoperability claim).

Each set has a table of files it leaves out, with the reason per file, and
one test that proves the exclusion still holds: an excluded example or
document still fails to parse, and a listed corpus file still differs from
its fixture. A file that starts to pass is removed from its table and from
the README.

A third table, ``IGNORED_EXTENSIONS``, counts the extensibility expressions the
reader drops from a file that otherwise parses. The two parse tests assert that
count as the number of warnings, and that no other warning appears."""

from __future__ import annotations

import warnings
from collections.abc import Collection
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from prov.model import ProvDocument, ProvWarning
from prov.serializers.provn_lexer import ProvNSyntaxError

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

CORPUS = Path(__file__).parent / "provn"
JSON_FIXTURES = Path(__file__).parent / "json"

# The specifications use a prefix in a qualified-name value without declaring
# it; prov rejects the value (#516), and the examples are not normative.
_UNDECLARED_VALUE_PREFIX = (
    "a qualified-name value uses a prefix the example does not declare (#516)"
)

# Specification examples that are not complete statements, that the formal
# grammar rejects even though the Recommendation's prose presents them as valid,
# or that use an undeclared prefix in a value; keep this list in step with
# provn/README.md.
EXCLUDED_SPEC_EXAMPLES: dict[str, str] = {
    "prov-n-example-16.provn": (
        "the sixth wasGeneratedBy variant reuses tr:WD-prov-dm-20111215 as its "
        "time argument, which is not a dateTime; a copy-paste artefact in the "
        "Recommendation's own text"
    ),
    "prov-n-example-34.provn": _UNDECLARED_VALUE_PREFIX,
    "prov-n-example-35.provn": _UNDECLARED_VALUE_PREFIX,
    "prov-n-example-37.provn": (
        "wasAssociatedWith(ex:a1, ex:ag1) gives the agent without the paired "
        "plan; production [20] requires them together"
    ),
    "prov-n-example-51.provn": (
        "a prefix declaration before the default declaration; production [45] "
        "puts the default first"
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
    "prov-dm-example-27.provn": _UNDECLARED_VALUE_PREFIX,
    "prov-dm-example-31.provn": _UNDECLARED_VALUE_PREFIX,
    "prov-dm-example-34.provn": (
        "wasAssociatedWith gives only the activity and agent without the paired plan"
    ),
    "prov-dm-example-42.provn": (
        "statements after the bundle; production [1] puts every expression "
        "before the first bundle"
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
    "prov-dm-example-61.provn": _UNDECLARED_VALUE_PREFIX,
    "prov-dm-example-62.provn": _UNDECLARED_VALUE_PREFIX,
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
        "'\"hello2\"@EN %% xsd:string' at line 12 gives one literal a language "
        "tag and a datatype, which productions [41] and [43] do not allow; the "
        "document also holds wasRevisionOf, wasQuotedFrom and hadPrimarySource, "
        "which PROV-N has no production for, and declares 'bundle ex3:b2' with "
        "ex3 declared nowhere. Its 'prov:' dictionary statements parse as "
        "extensibility expressions"
    ),
    "container2.provn": (
        "'%% <http://example.org/type>' uses a bare IRI as a datatype; "
        "production [53] requires datatype to be a qualifiedName"
    ),
}

# Extensibility expressions the reader drops from a file that parses, one
# warning each, and the records the two family documents hold without them.
IGNORED_EXTENSIONS: dict[str, int] = {
    "prov-n-example-63.provn": 1,
    "prov-n-example-64.provn": 1,
    "prov-family.provn": 12,
    "prov-family-graphics.provn": 12,
}
FAMILY_RECORDS = {"prov-family.provn": 742, "prov-family-graphics.provn": 764}


def _files(subdir: str) -> list[Path]:
    return sorted((CORPUS / subdir).glob("*.provn"))


def _params(subdir: str, excluded: Collection[str]) -> list[ParameterSet]:
    return [
        pytest.param(path, id=path.name)
        for path in _files(subdir)
        if path.name not in excluded
    ]


def _read(path: Path, profile: str = "default") -> ProvDocument:
    return ProvDocument.deserialize(str(path), format="provn", profile=profile)


def _fixture(path: Path) -> ProvDocument:
    return ProvDocument.deserialize(
        str(JSON_FIXTURES / f"{path.stem}.json"), format="json"
    )


SPEC_EXAMPLES = {
    path.name: path for path in _files("spec/prov-n") + _files("spec/prov-dm")
}


def _read_recording_drops(path: Path, profile: str) -> ProvDocument:
    """Read ``path`` and assert it warns only for its dropped extensions."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        document = _read(path, profile)
    expected = IGNORED_EXTENSIONS.get(path.name, 0)
    ours = [w for w in caught if issubclass(w.category, ProvWarning)]
    assert len(ours) == expected
    assert all(
        str(w.message).startswith("PROV-N extensibility expression dropped:")
        for w in ours
    )
    return document


@pytest.mark.parametrize(
    "path",
    _params("spec/prov-n", EXCLUDED_SPEC_EXAMPLES)
    + _params("spec/prov-dm", EXCLUDED_SPEC_EXAMPLES),
)
def test_spec_examples_parse_strictly_and_round_trip(path: Path) -> None:
    document = _read_recording_drops(path, "strict")
    # The writer emits no extensibility expression, so the reparse is silent.
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        reloaded = ProvDocument.deserialize(
            content=document.get_provn(strict=True), format="provn", profile="strict"
        )
    assert reloaded == document


def test_excluded_spec_examples_still_fail_to_parse() -> None:
    for name in EXCLUDED_SPEC_EXAMPLES:
        with pytest.raises(ProvNSyntaxError):
            _ = _read(SPEC_EXAMPLES[name], "strict")


@pytest.mark.parametrize("path", _params("provtoolbox", EXCLUDED_PROVTOOLBOX_DOCUMENTS))
def test_provtoolbox_documents_parse(path: Path) -> None:
    document = _read_recording_drops(path, "default")
    assert document.get_records() or document.has_bundles()
    if path.name in FAMILY_RECORDS:
        assert len(document.get_records()) == FAMILY_RECORDS[path.name]


def test_excluded_provtoolbox_documents_still_fail_to_parse() -> None:
    for name in EXCLUDED_PROVTOOLBOX_DOCUMENTS:
        with pytest.raises(ProvNSyntaxError):
            _ = _read(CORPUS / "provtoolbox" / name)
    # Each counted file is a corpus file that parses, so no key is stale.
    parsed = (SPEC_EXAMPLES.keys() | {p.name for p in _files("provtoolbox")}) - (
        EXCLUDED_SPEC_EXAMPLES.keys() | EXCLUDED_PROVTOOLBOX_DOCUMENTS.keys()
    )
    assert IGNORED_EXTENSIONS.keys() | FAMILY_RECORDS.keys() <= parsed


@pytest.mark.parametrize("path", _params("provtoolbox-corpus", KNOWN_DIFFERENCES))
def test_provtoolbox_corpus_equals_json_fixture(path: Path) -> None:
    assert _read(path) == _fixture(path)


def test_known_differences_still_differ_from_the_json_fixture() -> None:
    for name in KNOWN_DIFFERENCES:
        path = CORPUS / "provtoolbox-corpus" / name
        assert _read(path) != _fixture(path), name


def test_every_json_fixture_has_a_counterpart_or_is_listed() -> None:
    readme = (CORPUS / "README.md").read_text()
    have = {p.stem for p in _files("provtoolbox-corpus")}
    for path in sorted(JSON_FIXTURES.glob("*.json")):
        if path.stem not in have:
            assert path.stem in readme, (
                f"{path.stem} has no counterpart and is not listed"
            )

"""Characterize unified() against the PROV-CONSTRAINTS unification corpus.

``unified()`` implements the specification's key constraints (22 and 23) by
pairwise term unification of formal attributes. Observed outcomes over the
vendored ProvToolbox/W3C corpus (``unification/constraints/``):

- fail-cases whose same-identifier records carry *conflicting concrete* formal
  attribute values are rejected with the documented ``ProvUnificationError``
  (``UNIFICATION_REJECTS`` below);
- every other fail-case still merges (placeholder-vs-concrete conflicts, which
  the model cannot represent — an absent formal attribute is an existential
  that unifies with any concrete value) or passes through untouched
  (uniqueness Constraints 24-29, mandatory-placeholder and impossibility
  cases, all keyed on something other than the record identifier and hence
  outside ``unified()``'s documented scope — they belong to the opt-in
  validation engine, issue #62);
- three ``bundle-*`` files cannot be parsed at all — prov's PROV-XML
  deserializer rejects them with ``ProvXMLException`` (issue #254) — and are
  skipped as parse failures.

Authority: docs/superpowers/specs/2026-07-10-unification-gap-analysis.md and
umbrella issue #253.
"""

import datetime
from pathlib import Path

import pytest

pytest.importorskip("lxml")

from prov.model import ProvDocument, ProvUnificationError

# unified()'s FutureWarning (2.4.0 signpost for the 3.0 rework) is already
# ignored via pyproject.toml's filterwarnings; the mark keeps these tests
# self-contained should that global filter ever change.
pytestmark = pytest.mark.filterwarnings("ignore::FutureWarning")

CORPUS = Path(__file__).parent / "unification" / "constraints"

# prov's PROV-XML deserializer rejects these with ProvXMLException
# (_extract_attributes, provxml.py) because they wrap bundle contents in
# ProvToolbox's <prov:bundle> container instead of the XSD's
# <prov:bundleContent> — issue #254, recorded in the gap analysis.
PARSE_FAILURES = {
    "bundle-fail1.xml",
    "bundle-success1.xml",
    "bundle-success2.xml",
}

# Fail-cases rejected by term unification: their same-identifier records carry
# two *different concrete* values for the same formal attribute, so the records
# cannot be merged. This is the only rejection unified() performs.
UNIFICATION_REJECTS = {
    "association-fail1.xml",
    "association-fail2.xml",
    "association-fail3.xml",
    "delegation-fail1.xml",
    "delegation-fail2.xml",
    "delegation-fail3.xml",
    "end-fail1.xml",
    "end-fail2.xml",
    "end-fail3.xml",
    "end-fail5.xml",
    "generation-fail2.xml",
    "generation-fail3.xml",
    "generation-fail4.xml",
    "invalidation-fail2.xml",
    "invalidation-fail3.xml",
    "invalidation-fail4.xml",
    "start-fail1.xml",
    "start-fail2.xml",
    "start-fail3.xml",
    "start-fail5.xml",
    "start-fail6.xml",
    "start-fail8.xml",
    "usage-fail2.xml",
    "usage-fail3.xml",
    "usage-fail4.xml",
}


def _n_records(document):
    return len(document.get_records()) + sum(
        len(b.get_records()) for b in document.bundles
    )


def _expected_unified_count(document):
    # The exact record count _unified_records() produces, computed from the
    # pre-merge document: per scope (toplevel and each bundle), identified
    # records collapse to one per distinct identifier (regardless of record
    # type), while anonymous records never enter _id_map and ALL pass through
    # unchanged — not even exact duplicates are deduplicated.
    total = 0
    for scope in (document, *document.bundles):
        records = scope.get_records()
        identified = {r.identifier for r in records if r.identifier is not None}
        anonymous = sum(1 for r in records if r.identifier is None)
        total += len(identified) + anonymous
    return total


def _cases():
    for xml_path in sorted(CORPUS.glob("*.xml")):
        expected = "success" if "-success" in xml_path.stem else "fail"
        marks = []
        if xml_path.name in PARSE_FAILURES:
            marks.append(
                pytest.mark.skip(
                    reason="prov cannot parse: ProvToolbox's <prov:bundle> "
                    "dialect is rejected with ProvXMLException (crash fixed "
                    "under #254) — recorded in the gap analysis"
                )
            )
        yield pytest.param(xml_path, expected, id=xml_path.stem, marks=marks)


def test_corpus_inventory():
    # Guard against the vendored corpus being truncated or renamed: 153 files,
    # and the behaviour sets above must keep referring to real fail-cases.
    files = {p.name for p in CORPUS.glob("*.xml")}
    assert len(files) == 153
    assert files >= PARSE_FAILURES
    assert files >= UNIFICATION_REJECTS
    assert all("-fail" in name for name in UNIFICATION_REJECTS)


@pytest.mark.parametrize("xml_path, expected", list(_cases()))
def test_unified_corpus_characterization(xml_path, expected):
    with open(xml_path, "rb") as f:
        document = ProvDocument.deserialize(f, format="xml")
    if expected == "success":
        # Valid instances all unify without complaint, and the result is
        # exactly the identifier-keyed union (verified for the whole corpus:
        # the observed count matches the formula for all 125 non-raising
        # cases). Note this is NOT always the spec's normal form: anonymous
        # records that Constraints 24-27 would fold into an identified one
        # stay separate (gap analysis section 3.4).
        unified = document.unified()
        assert _n_records(unified) == _expected_unified_count(document)
    elif xml_path.name in UNIFICATION_REJECTS:
        # Invalid instance rejected by term unification: two same-identifier
        # records disagree on a formal attribute's concrete value.
        with pytest.raises(ProvUnificationError):
            document.unified()
    else:
        # Invalid instance ("fail" per the corpus label) that unified()
        # nevertheless accepts, producing the plain identifier-keyed union —
        # these fail on constraints outside unified()'s documented scope
        # (see the module docstring).
        unified = document.unified()
        assert _n_records(unified) == _expected_unified_count(document)


# --- Hand-written per-rule gap examples (see the gap-analysis doc, section 3)


def test_conflicting_start_times_fail_to_unify():
    # PROV-CONSTRAINTS Constraint 22 (key-object): two activity records with
    # the same id and different startTime values do not unify; the spec
    # requires the merge (and thus normalization) to FAIL. unified() rejects
    # them with the documented ProvUnificationError, naming the record, the
    # formal attribute and both values.
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.activity("a1", startTime="2011-11-16T16:00:00")
    doc.activity("a1", startTime="2012-01-01T00:00:00")
    with pytest.raises(ProvUnificationError, match="prov:startTime") as ctx:
        doc.unified()
    message = str(ctx.value)
    assert "a1" in message
    assert repr(datetime.datetime(2011, 11, 16, 16, 0)) in message
    assert repr(datetime.datetime(2012, 1, 1, 0, 0)) in message


def test_placeholder_vs_concrete_plan_merges():
    # PROV-CONSTRAINTS §4: the placeholder - is a constant; it unifies only
    # with itself or an existential variable, never with a concrete value.
    # Corpus analogue association-fail4: wasAssociatedWith(assoc1; a1, ag1,
    # ex:pl1) + wasAssociatedWith(assoc1; a1, ag1, -) must FAIL to merge.
    # prov cannot represent - (deserializers drop the distinction), so an
    # absent formal attribute is an existential and unifies with the concrete
    # plan. Locked decision (#253): out of scope by representation.
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.association("a1", agent="ag1", plan="pl1", identifier="assoc1")
    doc.association("a1", agent="ag1", identifier="assoc1")
    unified = doc.unified()
    records = unified.get_records()
    assert len(records) == 1
    assert records[0].get_provn() == "wasAssociatedWith(assoc1; a1, ag1, pl1)"


def test_entity_and_activity_sharing_an_id_currently_merge_into_an_entity():
    # PROV-CONSTRAINTS Constraint 55 (entity-activity-disjoint) makes an
    # entity and an activity with the same identifier INVALID (with
    # Constraint 50, typing). Term unification applies to same-type groups
    # only, so for now they still merge into a copy of whichever record came
    # first — here a ProvEntity — with the activity's formal startTime demoted
    # to an extra literal attribute.
    # Task 2 (#253): type compatibility — this must raise.
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.entity("thing")
    doc.activity("thing", startTime="2011-11-16T16:00:00")
    unified = doc.unified()
    records = unified.get_records()
    assert len(records) == 1
    assert (
        records[0].get_provn()
        == 'entity(thing, [prov:startTime="2011-11-16T16:00:00" %% xsd:dateTime])'
    )


def test_uniqueness_constraints_on_other_keys_are_out_of_scope():
    # PROV-CONSTRAINTS Constraint 24 (unique-generation): two generations of
    # the same (entity, activity) pair must have equal identifiers — two
    # *different* constant identifiers cannot unify, so this instance is
    # INVALID (corpus analogue generation-fail1). unified() keys on the
    # record identifier only and leaves both records untouched: Constraints
    # 24-29 are documented as outside its scope and belong to the opt-in
    # validation engine (#62).
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.entity("e1")
    doc.activity("a1")
    doc.generation("e1", "a1", identifier="gen1")
    doc.generation("e1", "a1", identifier="gen1-other")
    unified = doc.unified()
    assert len(unified.get_records()) == 4  # nothing merged, nothing rejected


def test_compatible_partial_information_merges_like_the_spec_example():
    # PROV-CONSTRAINTS §6.1's worked example — activity(a, t1, _t, [ex:a=1]) +
    # activity(a, _t, t2, [ex:b=2]) merge into activity(a, t1, t2, [ex:a=1,
    # ex:b=2]) — because absent formal attributes unify with concrete ones and
    # extra attributes are unioned.
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.add_namespace("ex", "http://example.org/ns#")
    doc.activity("a", startTime="2011-11-16T16:00:00", other_attributes={"ex:a": 1})
    doc.activity("a", endTime="2011-11-16T18:00:00", other_attributes={"ex:b": 2})
    unified = doc.unified()
    records = unified.get_records()
    assert len(records) == 1
    assert (
        records[0].get_provn()
        == "activity(a, 2011-11-16T16:00:00, 2011-11-16T18:00:00, [ex:a=1, ex:b=2])"
    )


# --- Bundle scoping (PROV-CONSTRAINTS section 7.2)


def test_document_unified_scopes_unification_per_bundle():
    # PROV-CONSTRAINTS 7.2: each bundle is normalized independently; nothing
    # merges across bundle boundaries. ProvDocument.unified() conforms: the
    # top level and each sub-bundle are unified independently of the document
    # and of each other, even when they share record identifiers.
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.entity("e", {"prov:label": "top level"})
    b1 = doc.bundle("b1")
    b1.entity("e", {"prov:label": "in b1 first"})
    b1.entity("e", {"prov:label": "in b1 second"})
    b2 = doc.bundle("b2")
    b2.entity("e", {"prov:label": "in b2"})

    unified = doc.unified()

    assert len(unified.get_records()) == 1  # top level untouched by bundles
    bundles = {str(b.identifier): b for b in unified.bundles}
    assert set(bundles) == {"b1", "b2"}
    # b1's two same-id records merged within b1 only (label set union).
    (b1_record,) = bundles["b1"].get_records()
    assert {str(label) for label in b1_record.get_attribute("prov:label")} == {
        "in b1 first",
        "in b1 second",
    }
    # b2's record did not absorb anything from b1 or the top level.
    (b2_record,) = bundles["b2"].get_records()
    assert {str(label) for label in b2_record.get_attribute("prov:label")} == {"in b2"}


def test_flattened_unified_merges_across_bundle_boundaries():
    # The flattened().unified() idiom (as test_unifying in test_model.py uses)
    # merges same-id records ACROSS bundles — no PROV-CONSTRAINTS rule
    # licenses that (7.2 scopes constraints per bundle). Characterized here as
    # spec-invalid usage that keeps working: flattened() discards the bundle
    # structure first, so unified() only ever sees one scope.
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.entity("e", {"prov:label": "top level"})
    doc.bundle("b1").entity("e", {"prov:label": "in b1"})
    doc.bundle("b2").entity("e", {"prov:label": "in b2"})

    merged = doc.flattened().unified()

    (record,) = merged.get_records()
    assert {str(label) for label in record.get_attribute("prov:label")} == {
        "top level",
        "in b1",
        "in b2",
    }

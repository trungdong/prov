"""Characterize unified() against the PROV-CONSTRAINTS unification corpus.

``unified()`` implements the specification's key constraints (22 and 23) by
pairwise term unification of formal attributes, plus the type compatibility
checks of Constraints 53-55 for same-identifier records of different base
types (see the compatibility table in ``prov.model.bundle``). Observed
outcomes over the vendored ProvToolbox/W3C corpus (``unification/constraints/``):

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

None of the 153 vendored ProvToolbox files exercise the type compatibility
checks: the corpus's fail-cases are all same-type/same-relation conflicts or
fall under the out-of-scope constraints above (audited case by case for
#253's type compatibility step; e.g. ``usage-fail1``'s apparently swapped
entity/activity identifiers are just confusing local names — ``ex:e1`` is
declared and used consistently as the activity, ``ex:a1`` consistently as the
entity — its actual invalidity is the out-of-scope uniqueness-by-pair
Constraint 24 analogue). The disjoint-type chimera (Constraint 55) is instead
exercised by the hand-written ``test_entity_and_activity_sharing_an_id_raises``
below, and the permitted-overlap and disjoint-relation-kind cases
(Constraints 54/53) by ``src/prov/tests/test_unification_rules.py``.

A second, seven-file corpus vendored directly from the W3C Provenance
Working Group (``type-*.provx``, same directory) fills that gap: each case
was designed to probe a same-identifier type-compatibility rule. Per-case
outcome (see ``W3C_RAISES``/``W3C_OUT_OF_SCOPE_REASONS`` below and the
corpus README):

- ``type-f1-FAIL-c50-c55`` (entity + activity, same id) and
  ``type-f3-FAIL-c54`` (entity + wasGeneratedBy, same id) and
  ``type-f4-FAIL-c53`` (wasGeneratedBy + used, same id) all raise
  ``ProvUnificationError`` — squarely Constraints 55, 54 and 53;
- ``type-collection-FAIL-c56`` does not raise: Constraint 56
  (empty-collection membership) is not implemented;
- ``type-f2-FAIL-c50-c55`` does not raise: its invalidity is Constraint 50's
  *typing inference* (an id used in a relation's role argument is thereby
  inferred to carry that role's type), which ``unified()`` does not perform
  — it compares only explicitly-asserted record types;
- ``type-s1-PASS-c50-c55`` (distinct ids) and ``type-s2-PASS-c50-c55``
  (agent + entity, a permitted overlap) both unify without complaint, as
  their own "PASS" label claims.

Authority: docs/superpowers/specs/2026-07-10-unification-gap-analysis.md and
umbrella issue #253.
"""

import datetime
from pathlib import Path

import pytest

pytest.importorskip("lxml")

from prov.model import ProvDocument, ProvUnificationError

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
        # records disagree on a formal attribute's concrete value. Every
        # rejection in this group goes through the same code path
        # (_unify_same_type_group's conflicting-values branch), whose message
        # continues "... has conflicting values ..." -- distinct from the
        # type-compatibility rejection's "... incompatible types ..." (none
        # of these 153 ProvToolbox cases exercise that path; see the module
        # docstring).
        with pytest.raises(ProvUnificationError, match="has conflicting"):
            document.unified()
    else:
        # Invalid instance ("fail" per the corpus label) that unified()
        # nevertheless accepts, producing the plain identifier-keyed union —
        # these fail on constraints outside unified()'s documented scope
        # (see the module docstring).
        unified = document.unified()
        assert _n_records(unified) == _expected_unified_count(document)


# --- W3C type-compatibility corpus (constraints/type-*.provx)
#
# Vendored directly from the W3C Provenance Working Group (see the corpus
# README's "W3C type-compatibility corpus" section for source URLs, retrieval
# date and licence); distinguished from the ProvToolbox corpus above by its
# "type-" prefix and its own "-PASS-"/"-FAIL-cNN[,-cMM...]" naming, where the
# suffix lists every constraint number the case was designed to probe against
# the *full* specification -- not a claim about what unified() must do.

# Cases unified() actually rejects: the same identifier is shared by two
# records whose base types _incompatible_types() forbids combining.
W3C_RAISES = {
    "type-f1-FAIL-c50-c55.provx",  # entity + activity, same id (Constraint 55)
    "type-f3-FAIL-c54.provx",  # entity + wasGeneratedBy, same id (Constraint 54)
    "type-f4-FAIL-c53.provx",  # wasGeneratedBy + used, same id (Constraint 53)
}

# "FAIL" cases unified() does not reject, and why each is genuinely outside
# its documented scope rather than a defect -- see the corpus README's
# "Local quirks" for the fuller explanation.
W3C_OUT_OF_SCOPE_REASONS = {
    "type-collection-FAIL-c56.provx": (
        "Constraint 56 (empty-collection membership) is not implemented."
    ),
    "type-f2-FAIL-c50-c55.provx": (
        "invalid only via Constraint 50's typing inference through a "
        "relation's role argument, which unified() does not perform -- it "
        "compares only explicitly-asserted record types."
    ),
}


def _w3c_cases():
    for provx_path in sorted(CORPUS.glob("type-*.provx")):
        yield pytest.param(provx_path, id=provx_path.stem)


def test_w3c_corpus_inventory():
    # Guard against the vendored W3C corpus being truncated, renamed or
    # silently joining the ProvToolbox corpus's *.xml glob above.
    files = {p.name for p in CORPUS.glob("type-*.provx")}
    assert len(files) == 7
    assert not (files & {p.name for p in CORPUS.glob("*.xml")})
    accounted = W3C_RAISES | set(W3C_OUT_OF_SCOPE_REASONS)
    assert files == accounted | {
        "type-s1-PASS-c50-c55.provx",
        "type-s2-PASS-c50-c55.provx",
    }


@pytest.mark.parametrize("provx_path", list(_w3c_cases()))
def test_w3c_type_compatibility_characterization(provx_path):
    with open(provx_path, "rb") as f:
        document = ProvDocument.deserialize(f, format="xml")
    if provx_path.name in W3C_RAISES:
        # Squarely in unified()'s documented scope: reject the group.
        with pytest.raises(ProvUnificationError, match="incompatible types"):
            document.unified()
    else:
        # Either a "PASS" case, or a "FAIL" case whose invalidity is outside
        # unified()'s documented scope (W3C_OUT_OF_SCOPE_REASONS above) --
        # either way unified() must not raise.
        reason = W3C_OUT_OF_SCOPE_REASONS.get(provx_path.name)
        assert reason or "-PASS-" in provx_path.name
        document.unified()


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


def test_entity_and_activity_sharing_an_id_raises():
    # PROV-CONSTRAINTS Constraint 55 (entity-activity-disjoint) makes an
    # entity and an activity with the same identifier INVALID (with
    # Constraint 50, typing). unified() now rejects the group instead of
    # merging into a copy of whichever record came first (the previous,
    # order-dependent chimera characterized by this test until #253's type
    # compatibility check landed).
    doc = ProvDocument()
    doc.set_default_namespace("http://example.org/")
    doc.entity("thing")
    doc.activity("thing", startTime="2011-11-16T16:00:00")
    with pytest.raises(ProvUnificationError, match="thing"):
        doc.unified()


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

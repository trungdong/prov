"""PROV-CONSTRAINTS unification rules for unified() (3.0 rework, #253).

Scope (documented): key constraints 22/23 + term unification. An absent
formal attribute is an existential ("unknown") and unifies with any
concrete value -- the model cannot represent the spec's placeholder `-`
(deserializers drop the distinction; gap analysis §3.1), so `-`-vs-concrete
failures are out of scope by representation. Constraints 24-29 are deferred
to the #62 validation engine.
"""

import datetime

import pytest

from prov.constants import (
    PROV_ATTR_BUNDLE,
    PROV_ATTR_GENERAL_ENTITY,
    PROV_ATTR_SPECIFIC_ENTITY,
    PROV_MENTION,
)
from prov.model import ProvDocument, ProvUnificationError

T1 = datetime.datetime(2011, 11, 16, 16, 0, 0)
T2 = datetime.datetime(2011, 11, 16, 18, 0, 0)


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def test_spec_worked_example_merges():
    # PROV-CONSTRAINTS §6.1 worked example (Constraint 22).
    document = _doc()
    document.activity("ex:a", startTime=T1, other_attributes={"ex:x": 1})
    document.activity("ex:a", endTime=T2, other_attributes={"ex:y": 2})
    unified = document.unified()
    (activity,) = unified.get_records()
    assert activity.get_startTime() == T1
    assert activity.get_endTime() == T2
    assert len(activity.extra_attributes) == 2  # both ex:x and ex:y present


def test_conflicting_concrete_formal_attributes_raise():
    # Constraint 22: two concrete startTimes cannot unify.
    document = _doc()
    document.activity("ex:a", startTime=T1)
    document.activity("ex:a", startTime=T2)
    with pytest.raises(ProvUnificationError) as ctx:
        document.unified()
    message = str(ctx.value)
    assert "ex:a" in message and "startTime" in message


def test_conflicting_relation_endpoints_raise():
    # Constraint 23: same-id generations of different entities cannot unify.
    document = _doc()
    document.generation("ex:e1", "ex:a1", identifier="ex:gen1")
    document.generation("ex:e2", "ex:a1", identifier="ex:gen1")
    with pytest.raises(ProvUnificationError):
        document.unified()


def test_absent_formal_attribute_unifies_with_concrete():
    # Locked decision: absent == existential (the model cannot express `-`).
    document = _doc()
    document.association("ex:a1", agent="ex:ag1", plan="ex:pl1", identifier="ex:assoc1")
    document.association("ex:a1", agent="ex:ag1", identifier="ex:assoc1")
    unified = document.unified()
    associations = [r for r in unified.get_records() if r.identifier is not None]
    assert len(associations) == 1


def test_unification_is_scoped_per_bundle():
    # §7.2: bundles unify independently; nothing merges across boundaries.
    document = _doc()
    document.activity("ex:a", startTime=T1)
    bundle = document.bundle("ex:b1")
    bundle.activity("ex:a", startTime=T2)  # would conflict if scopes leaked
    unified = document.unified()  # must NOT raise
    assert unified.has_bundles()


def test_entity_activity_same_id_raises_either_order():
    # Constraint 55 (entity-activity-disjoint): the same identifier can
    # never be both an entity and an activity.
    for order in (("entity", "activity"), ("activity", "entity")):
        document = _doc()
        for kind in order:
            getattr(document, kind)("ex:thing")
        with pytest.raises(ProvUnificationError) as ctx:
            document.unified()
        message = str(ctx.value)
        assert "prov:Entity" in message and "prov:Activity" in message


def test_object_type_and_identified_relation_sharing_id_raises():
    # Constraint 54: an object type (entity/activity/agent) sharing an
    # identifier with one of the eleven identified relations is impossible --
    # distinct from Constraint 55 (object-vs-object) and Constraint 53
    # (relation-vs-relation).
    document = _doc()
    document.entity("ex:x")
    document.generation("ex:e1", "ex:a1", identifier="ex:x")
    with pytest.raises(ProvUnificationError) as ctx:
        document.unified()
    message = str(ctx.value)
    assert "prov:Entity" in message and "prov:Generation" in message


def test_agent_entity_overlap_is_permitted_and_unmerged():
    # Constraint 54 does not pair agent with entity: both statements stand.
    document = _doc()
    document.agent("ex:x")
    document.entity("ex:x")
    assert len(document.unified().get_records()) == 2


def test_distinct_relation_kinds_sharing_id_raise():
    # Constraint 53: generation and usage are two of the nine pairwise
    # disjoint relations.
    document = _doc()
    document.generation("ex:e1", "ex:a1", identifier="ex:r1")
    document.usage("ex:a1", "ex:e1", identifier="ex:r1")
    with pytest.raises(ProvUnificationError) as ctx:
        document.unified()
    message = str(ctx.value)
    assert "prov:Generation" in message and "prov:Usage" in message


def test_derivation_and_influence_sharing_id_is_permitted():
    # PROV-CONSTRAINTS §6.4's own worked example: wasInfluencedBy is exempt
    # from Constraint 53's pairwise-disjoint set because it is a superproperty
    # meant to share an identifier with a more specific relation --
    # "wasInfluencedBy(id;e2,e1)" + "wasDerivedFrom(id;e2,e1)" is explicitly
    # valid ("This satisfies the disjointness constraint."). This is the crux
    # of the 53-vs-54 distinction: derivation and influence are both among
    # Constraint 54's eleven identified relations, but neither is an object
    # type, so Constraint 54 does not apply either.
    document = _doc()
    document.derivation("ex:e2", "ex:e1", identifier="ex:r1")
    document.influence("ex:e2", "ex:e1", identifier="ex:r1")
    assert len(document.unified().get_records()) == 2


def test_keyless_relation_sharing_id_with_object_type_is_out_of_scope():
    # Constraint 54's r-set is Constraint 23's eleven *identified* relations;
    # Mention has no identifier in PROV-DM's abstract syntax and so is not
    # among them -- the specification has no opinion on an id it happens to
    # share with an entity. The .mention() convenience method always passes
    # identifier=None, but new_record() (and the PROV-JSON deserializer) can
    # still construct a Mention with an explicit, shared identifier.
    document = _doc()
    document.entity("ex:thing")
    document.new_record(
        PROV_MENTION,
        "ex:thing",
        {
            PROV_ATTR_SPECIFIC_ENTITY: "ex:e1",
            PROV_ATTR_GENERAL_ENTITY: "ex:e2",
            PROV_ATTR_BUNDLE: "ex:b1",
        },
    )
    unified = document.unified()  # must NOT raise
    assert len(unified.get_records()) == 2

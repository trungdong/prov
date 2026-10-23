"""PROV-CONSTRAINTS unification rules for unified() (3.0 rework, #253).

Scope (documented): key constraints 22/23 + term unification. An absent
formal attribute is an existential ("unknown") and unifies with any
concrete value -- the model cannot represent the spec's placeholder `-`
(deserializers drop the distinction; gap analysis §3.1), so `-`-vs-concrete
failures are out of scope by representation. The exception is the
non-expandable positions of PROV-CONSTRAINTS Table 3, where an absent value
can only mean "none", so unified() raises there (#547).
Constraints 24-29 are deferred to the #62 validation engine.
"""

import datetime
import json

import pytest

from prov.constants import (
    PROV_ATTR_BUNDLE,
    PROV_ATTR_GENERAL_ENTITY,
    PROV_ATTR_SPECIFIC_ENTITY,
    PROV_MENTION,
)
from prov.model import (
    ProvActivity,
    ProvDocument,
    ProvEntity,
    ProvException,
    ProvMembership,
    ProvUnificationError,
)

T1 = datetime.datetime(2011, 11, 16, 16, 0, 0)
T2 = datetime.datetime(2011, 11, 16, 18, 0, 0)


def _doc() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def test_spec_worked_example_merges() -> None:
    # PROV-CONSTRAINTS §6.1 worked example (Constraint 22).
    document = _doc()
    document.activity("ex:a", startTime=T1, other_attributes={"ex:x": 1})
    document.activity("ex:a", endTime=T2, other_attributes={"ex:y": 2})
    unified = document.unified()
    (activity,) = unified.get_records()
    assert isinstance(activity, ProvActivity)
    assert activity.get_startTime() == T1
    assert activity.get_endTime() == T2
    assert len(activity.extra_attributes) == 2  # both ex:x and ex:y present


def test_conflicting_concrete_formal_attributes_raise() -> None:
    # Constraint 22: two concrete startTimes cannot unify.
    document = _doc()
    document.activity("ex:a", startTime=T1)
    document.activity("ex:a", startTime=T2)
    with pytest.raises(ProvUnificationError) as ctx:
        document.unified()
    message = str(ctx.value)
    assert "ex:a" in message and "startTime" in message


def test_conflicting_relation_endpoints_raise() -> None:
    # Constraint 23: same-id generations of different entities cannot unify.
    document = _doc()
    document.generation("ex:e1", "ex:a1", identifier="ex:gen1")
    document.generation("ex:e2", "ex:a1", identifier="ex:gen1")
    with pytest.raises(ProvUnificationError):
        document.unified()


def test_unification_is_scoped_per_bundle() -> None:
    # §7.2: bundles unify independently; nothing merges across boundaries.
    document = _doc()
    document.activity("ex:a", startTime=T1)
    bundle = document.bundle("ex:b1")
    bundle.activity("ex:a", startTime=T2)  # would conflict if scopes leaked
    unified = document.unified()  # must NOT raise
    assert unified.has_bundles()


def test_entity_activity_same_id_raises_either_order() -> None:
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


def test_object_type_and_identified_relation_sharing_id_raises() -> None:
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


def test_agent_entity_overlap_is_permitted_and_unmerged() -> None:
    # Constraint 54 does not pair agent with entity: both statements stand.
    document = _doc()
    document.agent("ex:x")
    document.entity("ex:x")
    assert len(list(document.unified().get_records())) == 2


def test_distinct_relation_kinds_sharing_id_raise() -> None:
    # Constraint 53: generation and usage are two of the nine pairwise
    # disjoint relations.
    document = _doc()
    document.generation("ex:e1", "ex:a1", identifier="ex:r1")
    document.usage("ex:a1", "ex:e1", identifier="ex:r1")
    with pytest.raises(ProvUnificationError) as ctx:
        document.unified()
    message = str(ctx.value)
    assert "prov:Generation" in message and "prov:Usage" in message


def test_derivation_and_influence_sharing_id_is_permitted() -> None:
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
    assert len(list(document.unified().get_records())) == 2


def test_keyless_relation_sharing_id_with_object_type_is_out_of_scope() -> None:
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
    assert len(list(unified.get_records())) == 2


def _provn(*statements: str) -> ProvDocument:
    lines = ("document", "prefix ex <http://example.org/>", *statements, "endDocument")
    return ProvDocument.deserialize(content="\n".join(lines), format="provn")


_KEYLESS_STATEMENTS = {
    "hadMember": ("hadMember(ex:m; ex:c, ex:e1)", "hadMember(ex:m; ex:c, ex:e2)"),
    "alternateOf": ("alternateOf(ex:m; ex:a, ex:b1)", "alternateOf(ex:m; ex:a, ex:b2)"),
    "specializationOf": (
        "specializationOf(ex:m; ex:a, ex:b1)",
        "specializationOf(ex:m; ex:a, ex:b2)",
    ),
    "mentionOf": (
        "mentionOf(ex:m; ex:a, ex:b, ex:bun1)",
        "mentionOf(ex:m; ex:a, ex:b, ex:bun2)",
    ),
}


@pytest.mark.parametrize(
    "statements", _KEYLESS_STATEMENTS.values(), ids=_KEYLESS_STATEMENTS.keys()
)
def test_keyless_relations_sharing_an_identifier_are_not_merged(
    statements: tuple[str, str],
) -> None:
    # PROV-DM gives alternateOf, specializationOf, mentionOf and hadMember no
    # identifier (PROV-N productions 24 to 26, PROV-Links for mentionOf), so
    # unified() has nothing to merge them on and keeps them as asserted (#530).
    document = _provn(*statements)
    assert list(document.unified().get_records()) == list(document.get_records())


@pytest.mark.parametrize(
    "statement",
    [
        "hadMember(ex:m; ex:c, ex:e)",
        "used(ex:a, ex:e, -)",
        "used(ex:a, ex:e, -, [ex:k=1])",
    ],
)
def test_a_repeated_statement_is_kept_once(statement: str) -> None:
    # unified() drops a record equal to an earlier one, for every record kind:
    # a keyless relation sharing an identifier and an anonymous relation alike
    # (#548, #124).
    document = _provn(statement, statement)
    assert len(document.unified().get_records()) == 1


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("used(ex:a, ex:e, -, [ex:k=1])", "used(ex:a, ex:e, -, [ex:k=2])"),
        ("used(ex:a, ex:e, -)", "used(ex:a, ex:e, 2011-11-16T16:00:00)"),
        ("used(ex:a, ex:e, -)", "used(ex:u; ex:a, ex:e, -)"),
    ],
)
def test_records_that_differ_stay_two(first: str, second: str) -> None:
    # Two statements that differ in one attribute, in an absent formal or in
    # the identifier are two statements.
    assert len(_provn(first, second).unified().get_records()) == 2


def test_the_first_of_equal_records_keeps_its_position() -> None:
    document = _provn(
        "used(ex:a, ex:e, -)",
        "entity(ex:e)",
        "used(ex:a, ex:e, -)",
        "used(ex:u; ex:a, ex:e, -)",
    )
    records = document.unified().get_records()
    assert [str(r.identifier) for r in records] == ["None", "ex:e", "ex:u"]


def test_records_sharing_an_identifier_with_a_keyless_relation_still_merge() -> None:
    document = _provn(
        "entity(ex:m, [ex:k=1])",
        "entity(ex:m, [ex:k=2])",
        "hadMember(ex:m; ex:c, ex:e)",
    )
    unified = document.unified()
    (entity,) = unified.get_records(ProvEntity)
    assert entity.get_attribute("ex:k") == {1, 2}
    assert len(list(unified.get_records(ProvMembership))) == 1


def test_json_had_member_array_with_an_identifier_unifies() -> None:
    # The PROV-JSON membership of #530, an identifier with two members.
    content = json.dumps(
        {
            "prefix": {"ex": "http://example.org/"},
            "hadMember": {
                "ex:m": {"prov:collection": "ex:c", "prov:entity": ["ex:e1", "ex:e2"]}
            },
        }
    )
    document = ProvDocument.deserialize(content=content, format="json")
    assert len(list(document.unified().get_records(ProvMembership))) == 2


# --- Non-expandable formals (PROV-CONSTRAINTS Definition 4, Table 3; #547)
#
# An absent plan on an association, or an absent activity on a derivation, is
# the constant "none". So are an absent generation and usage on a derivation
# that names no activity. unified() raises where such a value meets a present
# one, at the first such position in the order of the statement's arguments.


ABSENT_NONE_REJECTS = [
    pytest.param(
        [
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, ex:pl1)",
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, -)",
        ],
        "ex:assoc1: an absent prov:plan means none, so it does not unify with ex:pl1",
        id="plan then none",
    ),
    pytest.param(
        [
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, -)",
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, ex:pl1)",
        ],
        "ex:assoc1: an absent prov:plan means none, so it does not unify with ex:pl1",
        id="none then plan",
    ),
    pytest.param(
        [
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)",
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, -, -)",
        ],
        "ex:d: an absent prov:activity means none, so it does not unify with ex:a",
        id="derivation activity",
    ),
    pytest.param(
        [
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)",
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, ex:x, -)",
        ],
        "ex:d: an absent prov:generation on a derivation with no activity means "
        "none, so it does not unify with ex:x",
        id="generation without activity",
    ),
    pytest.param(
        [
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)",
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, ex:x)",
        ],
        "ex:d: an absent prov:usage on a derivation with no activity means "
        "none, so it does not unify with ex:x",
        id="usage without activity",
    ),
    pytest.param(
        [
            # The activity is the first position in PROV-DM order, so it is
            # the one named.
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -)",
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, ex:g, -)",
        ],
        "ex:d: an absent prov:activity means none, so it does not unify with ex:a",
        id="activity before generation",
    ),
    pytest.param(
        [
            # PROV-N writes a revision as a derivation typed prov:Revision.
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, -, -, -, [prov:type='prov:Revision'])",
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, -, -, [prov:type='prov:Revision'])",
        ],
        "ex:d: an absent prov:activity means none, so it does not unify with ex:a",
        id="revision follows the derivation rule",
    ),
    pytest.param(
        [
            "bundle ex:b",
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, -)",
            "wasAssociatedWith(ex:assoc1; ex:a1, -, ex:pl1)",
            "endBundle",
        ],
        "ex:assoc1: an absent prov:plan means none, so it does not unify with ex:pl1",
        id="in a bundle",
    ),
]


@pytest.mark.parametrize(("statements", "message"), ABSENT_NONE_REJECTS)
def test_absent_non_expandable_formal_raises(
    statements: list[str], message: str
) -> None:
    document = _provn(*statements)
    with pytest.raises(ProvUnificationError) as ctx:
        _ = document.unified()
    assert str(ctx.value) == message


UNIFIED_WITHOUT_A_CONFLICT = [
    pytest.param(
        [
            # Generation and usage are expandable once the activity is named.
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, -, -)",
            "wasDerivedFrom(ex:d; ex:e2, ex:e1, ex:a, ex:g, -)",
        ],
        id="generation with activity",
    ),
    pytest.param(
        [
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, -)",
            "wasAssociatedWith(ex:assoc1; ex:a1, -, -)",
        ],
        id="both absent",
    ),
    pytest.param(
        [
            "wasAssociatedWith(ex:assoc1; ex:a1, -, ex:pl1)",
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, ex:pl1)",
        ],
        id="equal plans",
    ),
    pytest.param(
        [
            # The activity of a delegation is expandable.
            "actedOnBehalfOf(ex:del; ex:ag2, ex:ag1, -)",
            "actedOnBehalfOf(ex:del; ex:ag2, ex:ag1, ex:a)",
        ],
        id="delegation activity",
    ),
    pytest.param(
        [
            # The agent of an association is expandable.
            "wasAssociatedWith(ex:assoc1; ex:a1, ex:ag1, ex:pl1)",
            "wasAssociatedWith(ex:assoc1; ex:a1, -, ex:pl1)",
        ],
        id="absent agent",
    ),
]


@pytest.mark.parametrize("statements", UNIFIED_WITHOUT_A_CONFLICT)
def test_expandable_or_matching_formals_unify(statements: list[str]) -> None:
    unified = _provn(*statements).unified()
    assert len(list(unified.get_records())) == 1


def test_conflict_elsewhere_raises_first() -> None:
    document = _doc()
    document.association("ex:a1", agent="ex:ag1", identifier="ex:assoc1")
    document.association("ex:a1", agent="ex:ag2", plan="ex:pl1", identifier="ex:assoc1")
    with pytest.raises(ProvUnificationError, match="conflicting"):
        _ = document.unified()


def test_extra_attribute_conflict_raises_first() -> None:
    # The merged record rebuilds its extra attributes, and a second prov:time
    # still raises there; the non-expandable check waits until the merge
    # succeeds.
    document = _doc()
    document.association(
        "ex:a1",
        agent="ex:ag1",
        identifier="ex:assoc1",
        other_attributes={"prov:time": T1},
    )
    document.association(
        "ex:a1",
        agent="ex:ag1",
        plan="ex:pl1",
        identifier="ex:assoc1",
        other_attributes={"prov:time": T2},
    )
    with pytest.raises(ProvException, match="more than one value"):
        _ = document.unified()

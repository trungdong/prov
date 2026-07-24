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

from prov.model import ProvDocument, ProvUnificationError

# unified() still emits its 2.4.0 FutureWarning signpost (removed in a later
# step of the rework); pyproject.toml ignores it globally, and the mark keeps
# this module self-contained should that filter ever change.
pytestmark = pytest.mark.filterwarnings("ignore::FutureWarning")

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

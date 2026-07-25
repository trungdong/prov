"""Type-aware per-attribute value storage (#34).

Before this fix, ``ProvRecord._attributes`` stored each attribute's values in
a plain Python ``set``, whose membership test is value-based: ``2.0 in {2}``
is ``True``, so ``{2}.add(2.0)`` silently does nothing. A record built with
``[("ex:v", 2), ("ex:v", 2.0)]`` therefore kept only ``2`` -- whichever value
was inserted *first* survived, and the second, Python-equal-but-differently-
typed value was lost without warning. The same collapsing happened for
``1``/``True`` (``bool`` is an ``int`` subtype), at construction, across
separate ``add_attributes()`` calls, and inside ``unified()``'s extra-
attribute union.

This module characterizes the fixed behaviour: both values are now retained,
record equality/hashing can tell the results apart, and the retained values
survive serialization round trips.
"""

import datetime

import pytest

from prov.constants import XSD_DECIMAL
from prov.model import (
    PROV_ATTR_COLLECTION,
    PROV_ATTR_ENTITY,
    Literal,
    ProvDocument,
    ProvEntity,
    ProvException,
    ProvMembership,
    ProvUnificationError,
    TypedValueSet,
)
from prov.tests.conftest import roundtrip_document


@pytest.fixture
def doc():
    d = ProvDocument()
    d.add_namespace("ex", "http://example.org/")
    return d


def _typed(values):
    """(type, value) pairs for a container, order-independent comparison."""
    return {(type(v), v) for v in values}


# --- AC: construction / add_attributes / unified() all retain both values ---


def test_construction_retains_python_equal_differently_typed_values(doc):
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    assert _typed(e.get_attribute("ex:v")) == {(int, 2), (float, 2.0)}


def test_construction_retains_bool_vs_int(doc):
    e = doc.entity("ex:e", [("ex:v", 1), ("ex:v", True)])
    assert _typed(e.get_attribute("ex:v")) == {(int, 1), (bool, True)}


def test_int_vs_bool_that_are_not_equal_is_not_a_regression_case(doc):
    # 2 != True, so this was never collapsed even in 2.x; both values are
    # simply retained as they always were.
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", True)])
    assert _typed(e.get_attribute("ex:v")) == {(int, 2), (bool, True)}


def test_second_add_attributes_call_retains_both_values(doc):
    e = doc.entity("ex:e", [("ex:v", 2)])
    e.add_attributes([("ex:v", 2.0)])
    assert _typed(e.get_attribute("ex:v")) == {(int, 2), (float, 2.0)}


def test_unified_union_retains_both_values(doc):
    doc.entity("ex:e", [("ex:v", 2)])
    doc.entity("ex:e", [("ex:v", 2.0)])
    unified = doc.unified()
    (merged,) = unified.get_records()
    assert _typed(merged.get_attribute("ex:v")) == {(int, 2), (float, 2.0)}


# --- AC: genuine duplicates still dedupe ---


def test_genuine_duplicate_value_still_deduplicates(doc):
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2)])
    assert list(e.get_attribute("ex:v")) == [2]


def test_literal_decimal_value_space_dedup_unchanged(doc):
    e = doc.entity(
        "ex:e",
        [
            ("ex:v", Literal("10", XSD_DECIMAL)),
            ("ex:v", Literal("10.00", XSD_DECIMAL)),
        ],
    )
    # Same Python type (Literal) and the same xsd:decimal value-space value
    # (#77) -- still a single retained value.
    assert len(e.get_attribute("ex:v")) == 1


# --- AC: __eq__/__hash__ distinguish the retained values ---


def test_records_with_different_retained_value_sets_are_not_equal(doc):
    # Same identifier -- equality/hash must fall through to comparing the
    # attribute sets, since it short-circuits on differing identifiers first.
    ident = doc.entity("ex:anchor").identifier
    e_both = ProvEntity(doc, ident, [("ex:v", 2), ("ex:v", 2.0)])
    e_one = ProvEntity(doc, ident, [("ex:v", 2)])

    assert e_both != e_one
    assert hash(e_both) != hash(e_one)


def test_hash_distinguishes_typed_values_even_when_attributes_property_collapses(doc):
    # `attributes` yields plain (name, value) tuples; frozenset() of THOSE
    # would re-collapse (name, 2) and (name, 2.0) because the tuples compare
    # equal. __hash__/__eq__ must not go through that naive path.
    ident = doc.entity("ex:anchor2").identifier
    e_both = ProvEntity(doc, ident, [("ex:v", 2), ("ex:v", 2.0)])
    e_one = ProvEntity(doc, ident, [("ex:v", 2)])
    assert len(e_both.attributes) == 2
    assert len(e_one.attributes) == 1
    assert e_both != e_one
    assert hash(e_both) != hash(e_one)


# --- AC: record equality/hash still order-insensitive ---


def test_equality_and_hash_are_order_insensitive(doc):
    ident = doc.entity("ex:anchor3").identifier
    e_forward = ProvEntity(
        doc, ident, [("ex:v", 2), ("ex:v", 2.0), ("ex:w", True), ("ex:w", 1)]
    )
    e_reverse = ProvEntity(
        doc, ident, [("ex:w", 1), ("ex:w", True), ("ex:v", 2.0), ("ex:v", 2)]
    )
    assert e_forward == e_reverse
    assert hash(e_forward) == hash(e_reverse)


# --- AC: serialization round-trips of a mixed multi-value attribute ---


@pytest.mark.parametrize("fmt", ["json", "xml", "rdf"])
def test_mixed_typed_attribute_round_trips(fmt):
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    reloaded = roundtrip_document(document, fmt)
    assert document == reloaded
    (record,) = reloaded.get_records()
    assert _typed(record.get_attribute("ex:v")) == {(int, 2), (float, 2.0)}


# --- AC: public accessors decided deliberately (TypedValueSet, not a leak) ---


def test_get_attribute_returns_typed_value_set(doc):
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    values = e.get_attribute("ex:v")
    assert isinstance(values, TypedValueSet)
    assert len(values) == 2


def test_get_asserted_types_returns_typed_value_set_and_still_compares_to_plain_set(
    doc,
):
    e = doc.entity("ex:e")
    foo = doc.valid_qualified_name("ex:Foo")
    e.add_asserted_type(foo)
    types = e.get_asserted_types()
    assert isinstance(types, TypedValueSet)
    assert types == {foo}


def test_value_property_returns_typed_value_set(doc):
    e = doc.entity("ex:e", [("prov:value", 2), ("prov:value", 2.0)])
    assert isinstance(e.value, TypedValueSet)
    assert len(e.value) == 2


def test_add_asserted_type_mutates_in_place(doc):
    e = doc.entity("ex:e")
    e.add_asserted_type(doc.valid_qualified_name("ex:Foo"))
    e.add_asserted_type(doc.valid_qualified_name("ex:Bar"))
    assert len(e.get_asserted_types()) == 2


def test_typed_value_set_default_empty_still_falsy_and_equal_to_plain_set(doc):
    e = doc.entity("ex:e")
    assert e.get_asserted_types() == set()
    assert not e.get_asserted_types()
    assert e.value == set()


def test_typed_value_set_discard_is_type_aware():
    values = TypedValueSet([2, 2.0])
    assert len(values) == 2
    values.discard(2.0)  # discard() is a MutableSet abstract method
    assert _typed(values) == {(int, 2)}
    # Discarding a value never inserted is a no-op, like a plain set.
    values.discard(3)
    assert _typed(values) == {(int, 2)}


def test_activity_settime_raw_assignment_stays_consistent(doc):
    # ProvActivity.set_time() assigns straight into _attributes; confirm the
    # value is still retrievable through the normal typed accessors.
    a = doc.activity("ex:a")
    a.set_time(startTime=datetime.datetime(2020, 1, 1))
    assert isinstance(a.get_attribute("prov:startTime"), TypedValueSet)
    assert a.get_startTime() == datetime.datetime(2020, 1, 1)


# --- Inherited issue 1: hadMember multi-value narrowing stays unobservable ---


def test_hadmember_multivalue_narrows_to_one_value_via_public_views(doc):
    # ProvRecord.add_attributes() bypasses its single-value guard for every
    # attribute in a call that also includes prov:collection, so a
    # ProvMembership *can* hold two prov:entity values if constructed
    # directly (ProvBundle.membership() itself never does this). Ruling
    # (task-3-report.md): type-aware storage does not change this, because
    # prov:entity values are always QualifiedNames -- the same Python type --
    # so there is nothing for the new per-attribute container to newly
    # distinguish. `args`/`formal_attributes`/`get_provn()` still narrow to a
    # single (first-inserted) value, exactly as in 2.x. Left alone.
    collection = doc.entity("ex:coll")
    e1 = doc.entity("ex:e1")
    e2 = doc.entity("ex:e2")
    membership = ProvMembership(
        doc,
        None,
        [
            (PROV_ATTR_COLLECTION, collection.identifier),
            (PROV_ATTR_ENTITY, e1.identifier),
            (PROV_ATTR_ENTITY, e2.identifier),
        ],
    )
    assert len(membership.get_attribute(PROV_ATTR_ENTITY)) == 2
    assert membership.args[1] in (e1.identifier, e2.identifier)
    assert membership.formal_attributes[1][1] in (e1.identifier, e2.identifier)
    provn = membership.get_provn()
    assert provn.count(str(e1.identifier)) + provn.count(str(e2.identifier)) == 1


# --- Inherited issue 2: extra attribute sharing a formal-attribute name ---


def test_unified_merge_conflicting_extra_attribute_raises_plain_provexception(doc):
    # Two entities sharing an identifier each assert a *different*
    # prov:startTime as a non-formal (extra) attribute: prov:startTime is
    # not a formal attribute of ProvEntity, but it IS a member of the global
    # PROV_ATTRIBUTES set that ProvRecord.add_attributes()'s single-value
    # cardinality guard checks, so unified()'s merge -- which concatenates
    # extra_attributes across the group and re-asserts them through the
    # merged record's constructor -- still hits that guard. Ruling
    # (task-3-report.md): the guard predates the #253 ProvUnificationError
    # work, is shared by ordinary (non-merge) attribute assertion which has
    # nothing to do with unification, and is deliberately left raising the
    # generic ProvException it always has.
    doc.entity("ex:e", [("prov:startTime", datetime.datetime(2020, 1, 1))])
    doc.entity("ex:e", [("prov:startTime", datetime.datetime(2020, 1, 2))])
    with pytest.raises(ProvException) as exc_info:
        doc.unified()
    assert not isinstance(exc_info.value, ProvUnificationError)

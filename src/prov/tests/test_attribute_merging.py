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

This module characterizes the fixed behaviour: both values are now retained
on the record -- observable through ``attributes``/``extra_attributes``
iteration, record equality/hashing, and serialization -- and the retained
values survive serialization round trips. By maintainer decision (`prov` is
a published dependency of ProvStore), the three narrowing accessors
(``get_attribute()``, ``get_asserted_types()``, ``.value``) deliberately keep
their 2.x return type: a plain ``set`` built fresh from the record's own
type-aware storage, which re-collapses a Python-equal-but-differently-typed
pair exactly as 2.x did. That trade-off, and the accessors' copy semantics,
are characterized below too.
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


def _typed_values_by_name(record, attr_name):
    """(type, value) pairs for one attribute name, read via ``attributes``.

    ``attributes`` (unlike ``get_attribute()``) is the property that still
    exposes every value the record's storage retains (#34).
    """
    qn = record.bundle.valid_qualified_name(attr_name)
    return {(type(v), v) for k, v in record.attributes if k == qn}


# --- AC: construction / add_attributes / unified() all retain both values ---
# (checked via `attributes`, since `get_attribute()` deliberately does not --
# see the "public accessors" section below)


def test_construction_retains_python_equal_differently_typed_values(doc):
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 2), (float, 2.0)}


def test_construction_retains_bool_vs_int(doc):
    e = doc.entity("ex:e", [("ex:v", 1), ("ex:v", True)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 1), (bool, True)}


def test_int_vs_bool_that_are_not_equal_is_not_a_regression_case(doc):
    # 2 != True, so this was never collapsed even in 2.x; both values are
    # simply retained as they always were.
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", True)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 2), (bool, True)}


def test_second_add_attributes_call_retains_both_values(doc):
    e = doc.entity("ex:e", [("ex:v", 2)])
    e.add_attributes([("ex:v", 2.0)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 2), (float, 2.0)}


def test_unified_union_retains_both_values(doc):
    doc.entity("ex:e", [("ex:v", 2)])
    doc.entity("ex:e", [("ex:v", 2.0)])
    unified = doc.unified()
    (merged,) = unified.get_records()
    assert _typed_values_by_name(merged, "ex:v") == {(int, 2), (float, 2.0)}


# --- AC: genuine duplicates still dedupe ---
# (single-value cases: get_attribute() and `attributes` agree here)


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
    # (#77) -- still a single retained value, and it is the *first* one
    # asserted ("10"), matching plain set.add's first-wins semantics and
    # add_attributes()'s own cardinality guard (which also keeps the first
    # value and ignores a later "same value" one).
    (retained,) = e.get_attribute("ex:v")
    assert retained.value == "10"


def test_literal_langtag_case_dedup_keeps_first(doc):
    e = doc.entity(
        "ex:e",
        [
            ("ex:v", Literal("hi", langtag="en")),
            ("ex:v", Literal("hi", langtag="EN")),
        ],
    )
    # Same Python type (Literal) and the same value under langtag
    # case-insensitive equality (#259) -- still a single retained value,
    # and it is the *first* one asserted ("hi"@en), not the second
    # ("hi"@EN); same first-wins rationale as the decimal case above.
    (retained,) = e.get_attribute("ex:v")
    assert retained.langtag == "en"


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
    assert _typed_values_by_name(record, "ex:v") == {(int, 2), (float, 2.0)}


# --- Maintainer decision: public accessors keep their 2.x return type ---
#
# get_attribute()/get_asserted_types()/.value deliberately keep returning a
# plain `set` built fresh from the record's own type-aware storage, instead
# of exposing that storage directly: `prov` is a published dependency of
# ProvStore, so the narrow, 2.x-compatible return type was chosen over a new
# public container type. The accepted consequence is that a Python-equal-
# but-differently-typed pair retained on the record re-collapses in what
# these three accessors return -- exactly the 2.x behaviour -- even though
# the record's own storage, `attributes`/`extra_attributes`, equality/
# hashing and serialization all retain every value (characterized above).


def test_get_attribute_returns_a_plain_set_that_collapses_like_2x(doc):
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    values = e.get_attribute("ex:v")
    # isinstance(), not a live-container leak check in disguise: TypedValueSet
    # is not a set subclass (it's collections.abc.MutableSet, dict-backed),
    # so this still fails if the internal container were ever returned.
    assert isinstance(values, set)
    assert values == {2}  # 2.0 collapses in this copy, exactly as in 2.x


def test_get_attribute_returns_a_copy_not_the_live_container(doc):
    e = doc.entity("ex:e", [("ex:v", 2)])
    values = e.get_attribute("ex:v")
    values.add(999)  # mutating the returned set must not touch storage
    assert e.get_attribute("ex:v") == {2}


def test_get_asserted_types_returns_a_plain_set_and_is_type_preserving(doc):
    # prov:type values are always QualifiedNames, which never collapse under
    # Python equality, so unlike get_attribute()/.value this accessor's
    # plain-set copy never actually loses information in practice.
    e = doc.entity("ex:e")
    foo = doc.valid_qualified_name("ex:Foo")
    bar = doc.valid_qualified_name("ex:Bar")
    e.add_asserted_type(foo)
    e.add_asserted_type(bar)
    types = e.get_asserted_types()
    assert isinstance(types, set)  # not a set subclass, see note above
    assert types == {foo, bar}


def test_value_property_returns_a_plain_set_that_collapses_like_2x(doc):
    e = doc.entity("ex:e", [("prov:value", 2), ("prov:value", 2.0)])
    values = e.value
    assert isinstance(values, set)  # not a set subclass, see note above
    assert values == {2}


def test_add_asserted_type_mutates_live_storage_not_a_copy(doc):
    # add_asserted_type() must keep mutating the record's own storage
    # directly (self._attributes[...].add(...)) rather than a copy, since a
    # copy would have nowhere to persist the mutation to.
    e = doc.entity("ex:e")
    e.add_asserted_type(doc.valid_qualified_name("ex:Foo"))
    e.add_asserted_type(doc.valid_qualified_name("ex:Bar"))
    assert len(e.get_asserted_types()) == 2


def test_accessors_default_empty_still_falsy_and_equal_to_plain_set(doc):
    e = doc.entity("ex:e")
    assert e.get_asserted_types() == set()
    assert not e.get_asserted_types()
    assert e.value == set()


def test_internal_storage_contains_and_discard_are_type_aware(doc):
    # __contains__()/discard() are required MutableSet abstract/mixin
    # methods on the internal per-attribute container; neither is reachable
    # via any public API today (get_attribute() returns a detached plain-set
    # copy, so `in`/`.discard()` on *that* never reach this container), so
    # both are exercised here directly against the record's own storage.
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    container = e._attributes[doc.valid_qualified_name("ex:v")]
    assert len(container) == 2
    assert 2 in container
    assert 2.0 in container
    assert 3 not in container
    container.discard(2.0)
    assert _typed(container) == {(int, 2)}
    container.discard(3)  # no-op, like a plain set
    assert _typed(container) == {(int, 2)}


def test_activity_settime_raw_assignment_still_produces_typed_storage(doc):
    # ProvActivity.set_time() assigns straight into _attributes (not through
    # an accessor); confirm it still produces the internal type-aware
    # container, not a plain set, so a later add_attributes() call on the
    # same attribute would still get type-aware treatment.
    a = doc.activity("ex:a")
    a.set_time(startTime=datetime.datetime(2020, 1, 1))
    container = a._attributes[doc.valid_qualified_name("prov:startTime")]
    assert type(container).__name__ == "TypedValueSet"
    assert a.get_startTime() == datetime.datetime(2020, 1, 1)


# --- Inherited issue 1: hadMember multi-value narrowing stays unobservable ---


def test_hadmember_multivalue_narrows_to_one_value_via_public_views(doc):
    # ProvRecord.add_attributes() bypasses its single-value guard for every
    # attribute in a call that also includes prov:collection, so a
    # ProvMembership *can* hold two prov:entity values if constructed
    # directly (ProvBundle.membership() itself never does this). Maintainer
    # ruling: type-aware storage does not change this, because
    # prov:entity values are always QualifiedNames -- the same Python type --
    # so there is nothing for the new per-attribute container to newly
    # distinguish. `args`/`formal_attributes`/`get_provn()` still narrow to a
    # single (first-inserted) value, exactly as in 2.x. Left alone. (Also:
    # QualifiedNames never collapse, so get_attribute()'s plain-set copy
    # shows both members, unlike the int/float cases above.)
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
    # merged record's constructor -- still hits that guard. Maintainer
    # ruling: the guard predates the #253 ProvUnificationError
    # work, is shared by ordinary (non-merge) attribute assertion which has
    # nothing to do with unification, and is deliberately left raising the
    # generic ProvException it always has.
    doc.entity("ex:e", [("prov:startTime", datetime.datetime(2020, 1, 1))])
    doc.entity("ex:e", [("prov:startTime", datetime.datetime(2020, 1, 2))])
    with pytest.raises(ProvException) as exc_info:
        doc.unified()
    assert not isinstance(exc_info.value, ProvUnificationError)

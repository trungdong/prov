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
values survive serialization round trips. By maintainer decision (downstream
projects depend on the 2.x return types), the three narrowing accessors
(``get_attribute()``, ``get_asserted_types()``, ``.value``) deliberately keep
their 2.x return type: a plain ``set`` built fresh from the record's own
type-aware storage, which re-collapses a Python-equal-but-differently-typed
pair exactly as 2.x did. That trade-off, and the accessors' copy semantics,
are characterized below too.
"""

import datetime
from collections.abc import Callable

import pytest

from prov.constants import (
    PROV_ACTIVITY,
    PROV_DERIVATION,
    PROV_ENTITY,
    PROV_GENERATION,
    PROV_MEMBERSHIP,
    XSD_ANYURI,
    XSD_DECIMAL,
)
from prov.identifier import Identifier
from prov.model import (
    PROV_ATTR_COLLECTION,
    PROV_ATTR_ENTITY,
    PROV_ATTR_USED_ENTITY,
    Literal,
    ProvDerivation,
    ProvDocument,
    ProvEntity,
    ProvException,
    ProvMembership,
    ProvUnificationError,
)
from prov.tests.conftest import ROUNDTRIP_FORMATS, ex_document, roundtrip_document


@pytest.fixture
def doc():
    return ex_document()


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


def test_construction_retains_python_equal_differently_typed_values(doc) -> None:
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 2), (float, 2.0)}


def test_construction_retains_bool_vs_int(doc) -> None:
    e = doc.entity("ex:e", [("ex:v", 1), ("ex:v", True)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 1), (bool, True)}


def test_int_vs_bool_that_are_not_equal_is_not_a_regression_case(doc) -> None:
    # 2 != True, so this was never collapsed even in 2.x; both values are
    # simply retained as they always were.
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", True)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 2), (bool, True)}


def test_second_add_attributes_call_retains_both_values(doc) -> None:
    e = doc.entity("ex:e", [("ex:v", 2)])
    e.add_attributes([("ex:v", 2.0)])
    assert _typed_values_by_name(e, "ex:v") == {(int, 2), (float, 2.0)}


def test_unified_union_retains_both_values(doc) -> None:
    doc.entity("ex:e", [("ex:v", 2)])
    doc.entity("ex:e", [("ex:v", 2.0)])
    unified = doc.unified()
    (merged,) = unified.get_records()
    assert _typed_values_by_name(merged, "ex:v") == {(int, 2), (float, 2.0)}


# --- AC: genuine duplicates still dedupe ---
# (single-value cases: get_attribute() and `attributes` agree here)


def test_genuine_duplicate_value_still_deduplicates(doc) -> None:
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2)])
    assert list(e.get_attribute("ex:v")) == [2]


def test_literal_decimal_value_space_dedup_unchanged(doc) -> None:
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


def test_literal_langtag_case_dedup_keeps_first(doc) -> None:
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


def test_records_with_different_retained_value_sets_are_not_equal(doc) -> None:
    # Same identifier -- equality/hash must fall through to comparing the
    # attribute sets, since it short-circuits on differing identifiers first.
    ident = doc.entity("ex:anchor").identifier
    e_both = ProvEntity(doc, ident, [("ex:v", 2), ("ex:v", 2.0)])
    e_one = ProvEntity(doc, ident, [("ex:v", 2)])

    assert e_both != e_one
    assert hash(e_both) != hash(e_one)


def test_hash_distinguishes_typed_values_even_when_attributes_property_collapses(
    doc,
) -> None:
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


def test_equality_and_hash_are_order_insensitive(doc) -> None:
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
def test_mixed_typed_attribute_round_trips(fmt) -> None:
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
# of exposing that storage directly: downstream projects depend on the 2.x
# return type, so it was kept over a new public container type. The accepted consequence is that a Python-equal-
# but-differently-typed pair retained on the record re-collapses in what
# these three accessors return -- exactly the 2.x behaviour -- even though
# the record's own storage, `attributes`/`extra_attributes`, equality/
# hashing and serialization all retain every value (characterized above).


def test_get_attribute_returns_a_plain_set_that_collapses_like_2x(doc) -> None:
    e = doc.entity("ex:e", [("ex:v", 2), ("ex:v", 2.0)])
    values = e.get_attribute("ex:v")
    # isinstance(), not a live-container leak check in disguise: TypedValueSet
    # is not a set subclass (it's collections.abc.MutableSet, dict-backed),
    # so this still fails if the internal container were ever returned.
    assert isinstance(values, set)
    assert values == {2}  # 2.0 collapses in this copy, exactly as in 2.x


def test_get_attribute_returns_a_copy_not_the_live_container(doc) -> None:
    e = doc.entity("ex:e", [("ex:v", 2)])
    values = e.get_attribute("ex:v")
    values.add(999)  # mutating the returned set must not touch storage
    assert e.get_attribute("ex:v") == {2}


def test_get_asserted_types_returns_a_plain_set_and_is_type_preserving(doc) -> None:
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


def test_value_property_returns_a_plain_set_that_collapses_like_2x(doc) -> None:
    e = doc.entity("ex:e", [("prov:value", 2), ("prov:value", 2.0)])
    values = e.value
    assert isinstance(values, set)  # not a set subclass, see note above
    assert values == {2}


def test_add_asserted_type_mutates_live_storage_not_a_copy(doc) -> None:
    # add_asserted_type() stores into the record's own set, so the assertion
    # persists; get_asserted_types() returns a copy.
    e = doc.entity("ex:e")
    e.add_asserted_type(doc.valid_qualified_name("ex:Foo"))
    e.add_asserted_type(doc.valid_qualified_name("ex:Bar"))
    assert len(e.get_asserted_types()) == 2


def test_accessors_default_empty_still_falsy_and_equal_to_plain_set(doc) -> None:
    e = doc.entity("ex:e")
    assert e.get_asserted_types() == set()
    assert not e.get_asserted_types()
    assert e.value == set()
    assert e.label == "ex:e"


def _generation_and_activity_document(d):
    d.entity("ex:e")
    d.activity("ex:a")
    d.wasGeneratedBy("ex:e", "ex:a")
    return d


def _graph_read(d):
    from prov.graph import prov_to_graph

    prov_to_graph(d)


def _dot_read(d):
    from prov.dot import prov_to_dot

    prov_to_dot(d)


def _record_of_type(d, record_type):
    return next(r for r in d.get_records() if r.get_type() == record_type)


def _keys(d):
    return [list(r._attributes) for r in d.get_records()]


@pytest.mark.parametrize(
    "read",
    [
        pytest.param(
            lambda d: _record_of_type(d, PROV_ENTITY).get_asserted_types(),
            id="asserted-types",
        ),
        pytest.param(
            lambda d: _record_of_type(d, PROV_ENTITY).get_attribute("ex:x"),
            id="get-attribute",
        ),
        pytest.param(lambda d: _record_of_type(d, PROV_GENERATION).args, id="args"),
        pytest.param(
            lambda d: _record_of_type(d, PROV_GENERATION).formal_attributes,
            id="formal-attributes",
        ),
        pytest.param(lambda d: _record_of_type(d, PROV_ENTITY).label, id="label"),
        pytest.param(lambda d: _record_of_type(d, PROV_ENTITY).value, id="value"),
        pytest.param(
            lambda d: _record_of_type(d, PROV_ACTIVITY).get_startTime(),
            id="start-time",
        ),
        pytest.param(
            lambda d: _record_of_type(d, PROV_ACTIVITY).get_endTime(), id="end-time"
        ),
        pytest.param(
            lambda d: _record_of_type(d, PROV_ACTIVITY).args, id="activity-args"
        ),
        pytest.param(lambda d: d.unified(), id="unified"),
        pytest.param(lambda d: d.flattened(), id="flattened"),
        pytest.param(_graph_read, id="graph"),
        pytest.param(_dot_read, id="dot"),
        *[
            pytest.param(lambda d, f=f: d.serialize(format=f), id=f"write-{f}")
            for f in ROUNDTRIP_FORMATS
        ],
    ],
)
def test_a_read_leaves_every_record_unchanged(
    doc, read: Callable[[ProvDocument], object]
) -> None:
    d = _generation_and_activity_document(doc)
    before = _keys(d)

    read(d)

    assert _keys(d) == before


def _generation_with_extras(peek: bool) -> ProvDocument:
    d = _generation_and_activity_document(ex_document())
    g = _record_of_type(d, PROV_GENERATION)
    if peek:
        _ = (g.formal_attributes, g.args, g.label, g.get_attribute("ex:y"))
    g.add_attributes({"ex:x": 1})
    g.add_attributes({"ex:y": 2})
    g.add_attributes({"prov:time": datetime.datetime(2020, 1, 1)})
    return d


@pytest.mark.parametrize("fmt", ["json", "jsonld", "provn"])
def test_reads_do_not_change_the_serialised_output_or_attribute_order(fmt) -> None:
    peeked = _generation_with_extras(peek=True)
    plain = _generation_with_extras(peek=False)
    generation = _record_of_type(peeked, PROV_GENERATION)

    assert peeked.serialize(format=fmt) == plain.serialize(format=fmt)
    assert [str(name) for name in generation._attributes] == [
        "prov:entity",
        "prov:activity",
        "ex:x",
        "ex:y",
        "prov:time",
    ]


def test_a_rejected_duplicate_leaves_the_record_unchanged(doc) -> None:
    r = doc.wasGeneratedBy("ex:e", "ex:a", datetime.datetime(2020, 1, 1))
    keys = list(r._attributes)
    attributes = r.attributes

    with pytest.raises(ProvException):
        r.add_attributes({"prov:time": datetime.datetime(2021, 1, 1)})

    assert list(r._attributes) == keys
    assert r.attributes == attributes


def test_internal_storage_contains_and_discard_are_type_aware(doc) -> None:
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


def test_unpickled_value_set_from_an_earlier_release_is_rekeyed(doc) -> None:
    # A 3.2.x pickle keys the index by (type, value); loading it rebuilds the
    # keys by value, so membership and record equality hold.
    entity = doc.entity("ex:e1", {"ex:v": 5})
    container = entity._attributes[doc.valid_qualified_name("ex:v")]
    cls = type(container)
    restored = cls.__new__(cls)
    restored.__setstate__((None, {"_index": {(int, 5): 5}}))
    assert 5 in restored
    assert list(restored) == [5]
    assert restored == container


def test_unpickled_identifier_value_from_an_earlier_release_writes_as_anyuri(
    doc,
) -> None:
    # A 3.2.x pickle stores an Identifier value raw and __setstate__ re-adds it
    # without coercion; it still writes as an xsd:anyURI literal.
    entity = doc.entity("ex:e", {"ex:v": 1})
    container = entity._attributes[doc.valid_qualified_name("ex:v")]
    container.__setstate__((None, {"_index": {0: Identifier("http://example.org/x")}}))
    provn = doc.get_provn()
    assert 'ex:v="http://example.org/x" %% xsd:anyURI' in provn
    back = type(doc).deserialize(content=provn, format="provn")
    (value,) = back.get_records(ProvEntity)[0].get_attribute("ex:v")
    assert value == Literal("http://example.org/x", XSD_ANYURI)
    assert type(value) is Literal


def test_activity_settime_raw_assignment_still_produces_typed_storage(doc) -> None:
    # ProvActivity.set_time() assigns straight into _attributes (not through
    # an accessor); confirm it still produces the internal type-aware
    # container, not a plain set, so a later add_attributes() call on the
    # same attribute would still get type-aware treatment.
    a = doc.activity("ex:a")
    a.set_time(startTime=datetime.datetime(2020, 1, 1))
    container = a._attributes[doc.valid_qualified_name("prov:startTime")]
    assert type(container).__name__ == "TypedValueSet"
    assert a.get_startTime() == datetime.datetime(2020, 1, 1)


# --- Inherited issue 1: a PROV attribute holds one value, with or without a collection ---


_TWO_ENTITIES = [(PROV_ATTR_ENTITY, "ex:e1"), (PROV_ATTR_ENTITY, "ex:e2")]
_TWO_USED = [(PROV_ATTR_USED_ENTITY, "ex:u1"), (PROV_ATTR_USED_ENTITY, "ex:u2")]
_RECORD_CLASSES = {PROV_MEMBERSHIP: ProvMembership, PROV_DERIVATION: ProvDerivation}


@pytest.mark.parametrize(
    ("record_type", "prior", "pairs", "attr", "one_shot"),
    [
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [(PROV_ATTR_COLLECTION, "ex:c"), *_TWO_ENTITIES],
            "prov:entity",
            False,
            id="constant",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [(PROV_ATTR_COLLECTION, "ex:c"), *_TWO_ENTITIES],
            "prov:entity",
            True,
            id="constant-one-shot-iterator",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [("prov:collection", "ex:c"), *_TWO_ENTITIES],
            "prov:entity",
            False,
            id="string",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [(PROV_ATTR_COLLECTION, None), *_TWO_ENTITIES],
            "prov:entity",
            False,
            id="none-collection",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [("prov:collection", None), *_TWO_ENTITIES],
            "prov:entity",
            False,
            id="string-none",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            _TWO_ENTITIES,
            "prov:entity",
            False,
            id="no-collection",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [("zz:x", None), (PROV_ATTR_COLLECTION, "ex:c"), *_TWO_ENTITIES],
            "prov:entity",
            False,
            id="unresolvable-none-pair",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [(PROV_ATTR_COLLECTION, "ex:c"), _TWO_ENTITIES[0]],
            [_TWO_ENTITIES[1]],
            "prov:entity",
            False,
            id="second-call",
        ),
        pytest.param(
            PROV_MEMBERSHIP,
            [],
            [
                (PROV_ATTR_COLLECTION, "ex:c1"),
                (PROV_ATTR_COLLECTION, "ex:c2"),
                _TWO_ENTITIES[0],
            ],
            "prov:collection",
            False,
            id="two-collections",
        ),
        pytest.param(
            PROV_DERIVATION,
            [],
            [(PROV_ATTR_COLLECTION, "ex:c"), *_TWO_USED],
            "prov:usedEntity",
            False,
            id="derivation",
        ),
    ],
)
def test_a_prov_attribute_holds_one_value_whatever_else_the_call_stores(
    doc, record_type, prior, pairs, attr: str, one_shot: bool
) -> None:
    # A second, different value raises for every PROV attribute of every record
    # type, whether or not the call also stores a prov:collection.
    message = f"Cannot have more than one value for attribute {attr}"
    supplied = iter(pairs) if one_shot else pairs

    if prior:
        record = doc.new_record(record_type, None, prior)
        before = record.attributes
        with pytest.raises(ProvException, match=message):
            record.add_attributes(supplied)
        assert record.attributes == before
    else:
        with pytest.raises(ProvException, match=message):
            doc.new_record(record_type, None, supplied)
        assert not doc.get_records(_RECORD_CLASSES[record_type])


# --- Inherited issue 2: extra attribute sharing a formal-attribute name ---


def test_unified_merge_conflicting_extra_attribute_raises_plain_provexception(
    doc,
) -> None:
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

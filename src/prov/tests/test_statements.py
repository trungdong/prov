"""Pytest-native shared statement round-trip tests.

Migrated from the ``TestStatementsBase`` mixin (``statements.py``): each test
method becomes a module-level function taking the ``roundtrip`` fixture, which
runs it once per target in ``SHARED_TARGETS`` (model/json/xml/rdf). The 14
"scruffy" cases opt out of the shared ``fmt`` fixture with their own explicit
parametrization so the rdf param can be skipped (issue #217; see the
``scruffy_fmt`` decorator below). The legacy mixin remains for the
not-yet-migrated ``test_dot.py``.
"""

import datetime

import pytest

from prov.model import *

EX_NS = Namespace("ex", "http://example.org/")
EX2_NS = Namespace("ex2", "http://example2.org/")

_TIME_2012 = datetime.datetime(
    2012, 12, 3, 21, 8, 16, 686000, tzinfo=datetime.timezone.utc
)

# The 14 "scruffy" documents below add two relations sharing one identifier
# but differing prov:time; PROV-O cannot represent this (both times serialize
# onto the one qualified IRI, and deserialization then raises ProvException:
# "Cannot have more than one value for attribute prov:time"). This is an
# accepted PROV-O representational limitation, not a bug on a fix path, so the
# rdf param is skipped rather than xfailed (design doc §2/§3, issue #217).
RDF_SCRUFFY_SKIP = pytest.mark.skip(
    reason="PROV-O cannot represent same-identifier relations differing by "
    "prov:time — accepted limitation, issue #217",
)

# These functions opt out of the module-wide `fmt` fixture (see conftest.py)
# with their own explicit parametrization so the skip mark attaches only to
# the rdf param; model/json/xml still run normally.
scruffy_fmt = pytest.mark.parametrize(
    "fmt",
    ["model", "json", "xml", pytest.param("rdf", marks=RDF_SCRUFFY_SKIP)],
)


def new_document():
    return ProvDocument()


def add_label(record):
    record.add_attributes([("prov:label", Literal("hello"))])


def add_labels(record):
    record.add_attributes(
        [
            ("prov:label", Literal("hello")),
            ("prov:label", Literal("bye", langtag="en")),
            ("prov:label", Literal("bonjour", langtag="fr")),
        ]
    )


def add_types(record):
    record.add_attributes(
        [
            ("prov:type", "a"),
            ("prov:type", 1),
            ("prov:type", 1.0),
            ("prov:type", True),
            ("prov:type", EX_NS["abc"]),
            ("prov:type", datetime.datetime.now()),
            (
                "prov:type",
                Literal("http://boiled-egg.example.com", datatype=XSD_ANYURI),
            ),
        ]
    )


def add_locations(record):
    record.add_attributes(
        [
            ("prov:Location", "Southampton"),
            ("prov:Location", 1),
            ("prov:Location", 1.0),
            ("prov:Location", True),
            ("prov:Location", EX_NS["london"]),
            ("prov:Location", datetime.datetime.now()),
            ("prov:Location", EX_NS.uri + "london"),
            ("prov:Location", Literal(2002, datatype=XSD["gYear"])),
        ]
    )


def add_value(record):
    record.add_attributes([("prov:value", EX_NS["avalue"])])


def add_further_attributes(record):
    record.add_attributes(
        [
            (EX_NS["tag1"], "hello"),
            (EX_NS["tag2"], "bye"),
            (EX2_NS["tag3"], "hi"),
            (EX_NS["tag1"], "hello\nover\nmore\nlines"),
        ]
    )


def add_further_attributes0(record):
    record.add_attributes(
        [
            (EX_NS["tag1"], "hello"),
            (EX_NS["tag2"], "bye"),
            (EX_NS["tag2"], Literal("hola", langtag="es")),
            (EX2_NS["tag3"], "hi"),
            (EX_NS["tag"], 1),
            (EX_NS["tag"], Literal(1, datatype=XSD_SHORT)),
            (EX_NS["tag"], Literal(1, datatype=XSD_DOUBLE)),
            (EX_NS["tag"], 1.0),
            (EX_NS["tag"], True),
            (EX_NS["tag"], EX_NS.uri + "southampton"),
        ]
    )

    add_further_attributes_with_qnames(record)


def add_further_attributes_with_qnames(record):
    record.add_attributes(
        [
            (EX_NS["tag"], EX2_NS["newyork"]),
            (EX_NS["tag"], EX_NS["london"]),
        ]
    )


# TESTS


# ENTITIES
def test_entity_0(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e0"])
    a.add_attributes(
        [
            (EX_NS["tag2"], Literal("guten tag", langtag="de")),
            ("prov:Location", "un llieu"),
            (PROV["Location"], 1),
            (PROV["Location"], 2.0),
            (PROV["Location"], EX_NS.uri + "london"),
        ]
    )
    roundtrip(document)


def test_entity_1(roundtrip):
    document = new_document()
    document.entity(EX_NS["e1"])
    roundtrip(document)


def test_entity_2(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e2"])
    a.add_attributes([(PROV_LABEL, "entity2")])
    roundtrip(document)


def test_entity_3(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e3"])
    a.add_attributes([(PROV_LABEL, "entity3")])
    add_value(a)
    roundtrip(document)


def test_entity_4(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e4"])
    a.add_attributes([(PROV_LABEL, "entity4")])
    add_labels(a)
    roundtrip(document)


def test_entity_5(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e5"])
    a.add_attributes([(PROV_LABEL, "entity5")])
    add_types(a)
    roundtrip(document)


def test_entity_6(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e6"])
    a.add_attributes([(PROV_LABEL, "entity6")])
    add_locations(a)
    roundtrip(document)


def test_entity_7(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e7"])
    a.add_attributes([(PROV_LABEL, "entity7")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    roundtrip(document)


def test_entity_8(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e8"])
    a.add_attributes([(PROV_LABEL, "entity8")])
    add_types(a)
    add_types(a)
    add_locations(a)
    add_locations(a)
    add_labels(a)
    add_labels(a)
    roundtrip(document)


def test_entity_9(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e9"])
    a.add_attributes([(PROV_LABEL, "entity9")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


def test_entity_10(roundtrip):
    document = new_document()
    a = document.entity(EX_NS["e10"])
    a.add_attributes([(PROV_LABEL, "entity10")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes0(a)
    roundtrip(document)


# ACTIVITIES
def test_activity_1(roundtrip):
    document = new_document()
    document.activity(EX_NS["a1"])
    roundtrip(document)


def test_activity_2(roundtrip):
    document = new_document()
    a = document.activity(EX_NS["a2"])
    a.add_attributes([(PROV_LABEL, "activity2")])
    roundtrip(document)


def test_activity_3(roundtrip):
    document = new_document()
    document.activity(
        EX_NS["a3"],
        startTime=datetime.datetime.now(),
        endTime=datetime.datetime.now(),
    )
    roundtrip(document)


def test_activity_4(roundtrip):
    document = new_document()
    a = document.activity(EX_NS["a4"])
    a.add_attributes([(PROV_LABEL, "activity4")])
    add_labels(a)
    roundtrip(document)


def test_activity_5(roundtrip):
    document = new_document()
    a = document.activity(EX_NS["a5"])
    a.add_attributes([(PROV_LABEL, "activity5")])
    add_types(a)
    roundtrip(document)


def test_activity_6(roundtrip):
    document = new_document()
    a = document.activity(EX_NS["a6"])
    a.add_attributes([(PROV_LABEL, "activity6")])
    add_locations(a)
    roundtrip(document)


def test_activity_7(roundtrip):
    document = new_document()
    a = document.activity(EX_NS["a7"])
    a.add_attributes([(PROV_LABEL, "activity7")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    roundtrip(document)


def test_activity_8(roundtrip):
    document = new_document()
    a = document.activity(
        EX_NS["a8"],
        startTime=datetime.datetime.now(),
        endTime=datetime.datetime.now(),
    )
    a.add_attributes([(PROV_LABEL, "activity8")])
    add_types(a)
    add_types(a)
    add_locations(a)
    add_locations(a)
    add_labels(a)
    add_labels(a)
    roundtrip(document)


def test_activity_9(roundtrip):
    document = new_document()
    a = document.activity(EX_NS["a9"])
    a.add_attributes([(PROV_LABEL, "activity9")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


# AGENTS
def test_agent_1(roundtrip):
    document = new_document()
    document.agent(EX_NS["ag1"])
    roundtrip(document)


def test_agent_2(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag2"])
    a.add_attributes([(PROV_LABEL, "agent2")])
    roundtrip(document)


def test_agent_3(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag3"])
    a.add_attributes(
        [
            (PROV_LABEL, "agent3"),
            (PROV_LABEL, Literal("hello")),
        ]
    )
    roundtrip(document)


def test_agent_4(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag4"])
    a.add_attributes(
        [
            (PROV_LABEL, "agent4"),
            (PROV_LABEL, Literal("hello")),
            (PROV_LABEL, Literal("bye", langtag="en")),
        ]
    )
    roundtrip(document)


def test_agent_5(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag5"])
    a.add_attributes(
        [
            (PROV_LABEL, "agent5"),
            (PROV_LABEL, Literal("hello")),
            (PROV_LABEL, Literal("bye", langtag="en")),
            (PROV_LABEL, Literal("bonjour", langtag="french")),
        ]
    )
    roundtrip(document)


def test_agent_6(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag6"])
    a.add_attributes([(PROV_LABEL, "agent6")])
    add_types(a)
    roundtrip(document)


def test_agent_7(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag7"])
    a.add_attributes([(PROV_LABEL, "agent7")])
    add_locations(a)
    add_labels(a)
    roundtrip(document)


def test_agent_8(roundtrip):
    document = new_document()
    a = document.agent(EX_NS["ag8"])
    a.add_attributes([(PROV_LABEL, "agent8")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


# GENERATIONS
def test_generation_1(roundtrip):
    document = new_document()
    document.generation(EX_NS["e1"], identifier=EX_NS["gen1"])
    roundtrip(document)


def test_generation_2(roundtrip):
    document = new_document()
    document.generation(EX_NS["e1"], identifier=EX_NS["gen2"], activity=EX_NS["a1"])
    roundtrip(document)


def test_generation_3(roundtrip):
    document = new_document()
    a = document.generation(EX_NS["e1"], identifier=EX_NS["gen3"], activity=EX_NS["a1"])
    a.add_attributes(
        [
            (PROV_ROLE, "somerole"),
            (PROV_ROLE, "otherRole"),
        ]
    )
    roundtrip(document)


def test_generation_4(roundtrip):
    document = new_document()
    document.new_record(
        PROV_GENERATION,
        EX_NS["gen4"],
        (
            (PROV_ATTR_ENTITY, EX_NS["e1"]),
            (PROV_ATTR_ACTIVITY, EX_NS["a1"]),
            (PROV_ATTR_TIME, datetime.datetime.now()),
        ),
        {PROV_ROLE: "somerole"},
    )
    roundtrip(document)


def test_generation_5(roundtrip):
    document = new_document()
    a = document.generation(
        EX_NS["e1"],
        identifier=EX_NS["gen5"],
        activity=EX_NS["a1"],
        time=datetime.datetime.now(),
    )
    a.add_attributes(
        [
            (PROV_ROLE, "somerole"),
        ]
    )
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


def test_generation_6(roundtrip):
    document = new_document()
    document.generation(EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now())
    roundtrip(document)


def test_generation_7(roundtrip):
    document = new_document()
    a = document.generation(
        EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now()
    )
    a.add_attributes([(PROV_ROLE, "somerole")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


# USAGE
def test_usage_1(roundtrip):
    document = new_document()
    document.usage(None, entity=EX_NS["e1"], identifier=EX_NS["use1"])
    roundtrip(document)


def test_usage_2(roundtrip):
    document = new_document()
    document.usage(EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use2"])
    roundtrip(document)


def test_usage_3(roundtrip):
    document = new_document()
    use = document.usage(EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use3"])
    use.add_attributes([(PROV_ROLE, "somerole"), (PROV_ROLE, "otherRole")])
    roundtrip(document)


def test_usage_4(roundtrip):
    document = new_document()
    use = document.usage(
        EX_NS["a1"],
        entity=EX_NS["e1"],
        identifier=EX_NS["use4"],
        time=datetime.datetime.now(),
    )
    use.add_attributes([(PROV_ROLE, "somerole")])
    roundtrip(document)


def test_usage_5(roundtrip):
    document = new_document()
    use = document.usage(
        EX_NS["a1"],
        entity=EX_NS["e1"],
        identifier=EX_NS["use5"],
        time=datetime.datetime.now(),
    )
    use.add_attributes([(PROV_ROLE, "somerole")])
    add_types(use)
    add_locations(use)
    add_labels(use)
    add_further_attributes(use)
    roundtrip(document)


def test_usage_6(roundtrip):
    document = new_document()
    document.usage(EX_NS["a1"], entity=EX_NS["e1"])
    roundtrip(document)


def test_usage_7(roundtrip):
    document = new_document()
    use = document.usage(EX_NS["a1"], entity=EX_NS["e1"], time=datetime.datetime.now())
    use.add_attributes([(PROV_ROLE, "somerole")])
    add_types(use)
    add_locations(use)
    add_labels(use)
    add_further_attributes(use)
    roundtrip(document)


# INVALIDATIONS
def test_invalidation_1(roundtrip):
    document = new_document()
    document.invalidation(EX_NS["e1"], identifier=EX_NS["inv1"])
    roundtrip(document)


def test_invalidation_2(roundtrip):
    document = new_document()
    document.invalidation(EX_NS["e1"], identifier=EX_NS["inv2"], activity=EX_NS["a1"])
    roundtrip(document)


def test_invalidation_3(roundtrip):
    document = new_document()
    inv = document.invalidation(
        EX_NS["e1"], identifier=EX_NS["inv3"], activity=EX_NS["a1"]
    )
    inv.add_attributes(
        [
            (PROV_ROLE, "someRole"),
            (PROV_ROLE, "otherRole"),
        ]
    )
    roundtrip(document)


def test_invalidation_4(roundtrip):
    document = new_document()
    inv = document.invalidation(
        EX_NS["e1"],
        identifier=EX_NS["inv4"],
        activity=EX_NS["a1"],
        time=datetime.datetime.now(),
    )
    inv.add_attributes(
        [
            (PROV_ROLE, "someRole"),
        ]
    )
    roundtrip(document)


def test_invalidation_5(roundtrip):
    document = new_document()
    inv = document.invalidation(
        EX_NS["e1"],
        identifier=EX_NS["inv5"],
        activity=EX_NS["a1"],
        time=datetime.datetime.now(),
    )
    inv.add_attributes(
        [
            (PROV_ROLE, "someRole"),
        ]
    )
    add_types(inv)
    add_locations(inv)
    add_labels(inv)
    add_further_attributes(inv)
    roundtrip(document)


def test_invalidation_6(roundtrip):
    document = new_document()
    document.invalidation(EX_NS["e1"], activity=EX_NS["a1"])
    roundtrip(document)


def test_invalidation_7(roundtrip):
    document = new_document()
    inv = document.invalidation(
        EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now()
    )
    inv.add_attributes(
        [
            (PROV_ROLE, "someRole"),
        ]
    )
    add_types(inv)
    add_locations(inv)
    add_labels(inv)
    add_further_attributes(inv)
    roundtrip(document)


# STARTS
def test_start_1(roundtrip):
    document = new_document()
    document.start(None, trigger=EX_NS["e1"], identifier=EX_NS["start1"])
    roundtrip(document)


def test_start_2(roundtrip):
    document = new_document()
    document.start(EX_NS["a1"], trigger=EX_NS["e1"], identifier=EX_NS["start2"])
    roundtrip(document)


def test_start_3(roundtrip):
    document = new_document()
    document.start(EX_NS["a1"], identifier=EX_NS["start3"])
    roundtrip(document)


def test_start_4(roundtrip):
    document = new_document()
    document.start(
        None, trigger=EX_NS["e1"], identifier=EX_NS["start4"], starter=EX_NS["a2"]
    )
    roundtrip(document)


def test_start_5(roundtrip):
    document = new_document()
    document.start(
        EX_NS["a1"],
        trigger=EX_NS["e1"],
        identifier=EX_NS["start5"],
        starter=EX_NS["a2"],
    )
    roundtrip(document)


def test_start_6(roundtrip):
    document = new_document()
    document.start(EX_NS["a1"], identifier=EX_NS["start6"], starter=EX_NS["a2"])
    roundtrip(document)


def test_start_7(roundtrip):
    document = new_document()
    document.start(
        EX_NS["a1"],
        identifier=EX_NS["start7"],
        starter=EX_NS["a2"],
        time=datetime.datetime.now(),
    )
    roundtrip(document)


def test_start_8(roundtrip):
    document = new_document()
    start = document.start(
        EX_NS["a1"],
        identifier=EX_NS["start8"],
        starter=EX_NS["a2"],
        time=datetime.datetime.now(),
    )
    start.add_attributes(
        [
            (PROV_ROLE, "egg-cup"),
            (PROV_ROLE, "boiling-water"),
        ]
    )
    add_types(start)
    add_locations(start)
    add_labels(start)
    add_further_attributes(start)
    roundtrip(document)


def test_start_9(roundtrip):
    document = new_document()
    document.start(EX_NS["a1"], trigger=EX_NS["e1"])
    roundtrip(document)


def test_start_10(roundtrip):
    document = new_document()
    start = document.start(
        EX_NS["a1"], starter=EX_NS["a2"], time=datetime.datetime.now()
    )
    start.add_attributes(
        [
            (PROV_ROLE, "egg-cup"),
            (PROV_ROLE, "boiling-water"),
        ]
    )
    add_types(start)
    add_locations(start)
    add_labels(start)
    add_further_attributes(start)
    roundtrip(document)


# ENDS
def test_end_1(roundtrip):
    document = new_document()
    document.end(None, trigger=EX_NS["e1"], identifier=EX_NS["end1"])
    roundtrip(document)


def test_end_2(roundtrip):
    document = new_document()
    document.end(EX_NS["a1"], trigger=EX_NS["e1"], identifier=EX_NS["end2"])
    roundtrip(document)


def test_end_3(roundtrip):
    document = new_document()
    document.end(EX_NS["a1"], identifier=EX_NS["end3"])
    roundtrip(document)


def test_end_4(roundtrip):
    document = new_document()
    document.end(None, trigger=EX_NS["e1"], identifier=EX_NS["end4"], ender=EX_NS["a2"])
    roundtrip(document)


def test_end_5(roundtrip):
    document = new_document()
    document.end(
        EX_NS["a1"],
        trigger=EX_NS["e1"],
        identifier=EX_NS["end5"],
        ender=EX_NS["a2"],
    )
    roundtrip(document)


def test_end_6(roundtrip):
    document = new_document()
    document.end(EX_NS["a1"], identifier=EX_NS["end6"], ender=EX_NS["a2"])
    roundtrip(document)


def test_end_7(roundtrip):
    document = new_document()
    document.end(
        EX_NS["a1"],
        identifier=EX_NS["end7"],
        ender=EX_NS["a2"],
        time=datetime.datetime.now(),
    )
    roundtrip(document)


def test_end_8(roundtrip):
    document = new_document()
    end = document.end(
        EX_NS["a1"],
        identifier=EX_NS["end8"],
        ender=EX_NS["a2"],
        time=datetime.datetime.now(),
    )
    end.add_attributes(
        [
            (PROV_ROLE, "egg-cup"),
            (PROV_ROLE, "boiling-water"),
        ]
    )
    add_types(end)
    add_locations(end)
    add_labels(end)
    add_further_attributes(end)
    roundtrip(document)


def test_end_9(roundtrip):
    document = new_document()
    document.end(EX_NS["a1"], trigger=EX_NS["e1"])
    roundtrip(document)


def test_end_10(roundtrip):
    document = new_document()
    end = document.end(EX_NS["a1"], ender=EX_NS["a2"], time=datetime.datetime.now())
    end.add_attributes(
        [
            (PROV_ROLE, "yolk"),
            (PROV_ROLE, "white"),
        ]
    )
    add_types(end)
    add_locations(end)
    add_labels(end)
    add_further_attributes(end)
    roundtrip(document)


# DERIVATIONS
def test_derivation_1(roundtrip):
    document = new_document()
    document.derivation(None, usedEntity=EX_NS["e1"], identifier=EX_NS["der1"])
    roundtrip(document)


def test_derivation_2(roundtrip):
    document = new_document()
    document.derivation(EX_NS["e2"], usedEntity=None, identifier=EX_NS["der2"])
    roundtrip(document)


def test_derivation_3(roundtrip):
    document = new_document()
    document.derivation(EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der3"])
    roundtrip(document)


def test_derivation_4(roundtrip):
    document = new_document()
    der = document.derivation(
        EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der4"]
    )
    add_label(der)
    roundtrip(document)


def test_derivation_5(roundtrip):
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["der5"],
        activity=EX_NS["a"],
    )
    roundtrip(document)


def test_derivation_6(roundtrip):
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["der6"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
    )
    roundtrip(document)


def test_derivation_7(roundtrip):
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["der7"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
        generation=EX_NS["g"],
    )
    roundtrip(document)


def test_derivation_8(roundtrip):
    document = new_document()
    der = document.derivation(
        EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der8"]
    )
    add_label(der)
    add_types(der)
    add_further_attributes(der)
    roundtrip(document)


def test_derivation_9(roundtrip):
    document = new_document()
    der = document.derivation(EX_NS["e2"], usedEntity=None)
    add_types(der)
    roundtrip(document)


def test_derivation_10(roundtrip):
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
        generation=EX_NS["g"],
    )
    roundtrip(document)


def test_derivation_11(roundtrip):
    document = new_document()
    document.revision(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["rev1"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
        generation=EX_NS["g"],
    )
    roundtrip(document)


def test_derivation_12(roundtrip):
    document = new_document()
    document.quotation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["quo1"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
        generation=EX_NS["g"],
    )
    roundtrip(document)


def test_derivation_13(roundtrip):
    document = new_document()
    document.primary_source(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["prim1"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
        generation=EX_NS["g"],
    )
    roundtrip(document)


# ASSOCIATIONS
def test_association_1(roundtrip):
    document = new_document()
    document.association(EX_NS["a1"], identifier=EX_NS["assoc1"])
    roundtrip(document)


def test_association_2(roundtrip):
    document = new_document()
    document.association(None, agent=EX_NS["ag1"], identifier=EX_NS["assoc2"])
    roundtrip(document)


def test_association_3(roundtrip):
    document = new_document()
    document.association(EX_NS["a1"], agent=EX_NS["ag1"], identifier=EX_NS["assoc3"])
    roundtrip(document)


def test_association_4(roundtrip):
    document = new_document()
    document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc4"],
        plan=EX_NS["plan1"],
    )
    roundtrip(document)


def test_association_5(roundtrip):
    document = new_document()
    document.association(EX_NS["a1"], agent=EX_NS["ag1"])
    roundtrip(document)


def test_association_6(roundtrip):
    document = new_document()
    assoc = document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc6"],
        plan=EX_NS["plan1"],
    )
    add_labels(assoc)
    roundtrip(document)


def test_association_7(roundtrip):
    document = new_document()
    assoc = document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc7"],
        plan=EX_NS["plan1"],
    )
    add_labels(assoc)
    add_types(assoc)
    roundtrip(document)


def test_association_8(roundtrip):
    document = new_document()
    assoc = document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc8"],
        plan=EX_NS["plan1"],
    )
    assoc.add_attributes(
        [
            (PROV_ROLE, "figroll"),
            (PROV_ROLE, "sausageroll"),
        ]
    )
    roundtrip(document)


def test_association_9(roundtrip):
    document = new_document()
    assoc = document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc9"],
        plan=EX_NS["plan1"],
    )
    add_labels(assoc)
    add_types(assoc)
    add_further_attributes(assoc)
    roundtrip(document)


def test_association_10(roundtrip):
    document = new_document()
    assoc1 = document.association(
        EX_NS["a1"], agent=EX_NS["ag1"], identifier=EX_NS["assoc10a"]
    )
    assoc1.add_attributes(
        [
            (PROV_ROLE, "figroll"),
        ]
    )
    assoc2 = document.association(
        EX_NS["a1"], agent=EX_NS["ag2"], identifier=EX_NS["assoc10b"]
    )
    assoc2.add_attributes(
        [
            (PROV_ROLE, "sausageroll"),
        ]
    )
    roundtrip(document)


# ATTRIBUTIONS
def test_attribution_1(roundtrip):
    document = new_document()
    document.attribution(EX_NS["e1"], None, identifier=EX_NS["attr1"])
    roundtrip(document)


def test_attribution_2(roundtrip):
    document = new_document()
    document.attribution(None, EX_NS["ag1"], identifier=EX_NS["attr2"])
    roundtrip(document)


def test_attribution_3(roundtrip):
    document = new_document()
    document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr3"])
    roundtrip(document)


def test_attribution_4(roundtrip):
    document = new_document()
    document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr4"])
    roundtrip(document)


def test_attribution_5(roundtrip):
    document = new_document()
    document.attribution(EX_NS["e1"], EX_NS["ag1"])
    roundtrip(document)


def test_attribution_6(roundtrip):
    document = new_document()
    attr = document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr6"])
    add_labels(attr)
    roundtrip(document)


def test_attribution_7(roundtrip):
    document = new_document()
    attr = document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr7"])
    add_labels(attr)
    add_types(attr)
    roundtrip(document)


def test_attribution_8(roundtrip):
    document = new_document()
    attr = document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr8"])
    add_labels(attr)
    add_types(attr)
    add_further_attributes(attr)
    roundtrip(document)


# DELEGATIONS
def test_delegation_1(roundtrip):
    document = new_document()
    document.delegation(EX_NS["e1"], None, identifier=EX_NS["dele1"])
    roundtrip(document)


def test_delegation_2(roundtrip):
    document = new_document()
    document.delegation(None, EX_NS["ag1"], identifier=EX_NS["dele2"])
    roundtrip(document)


def test_delegation_3(roundtrip):
    document = new_document()
    document.delegation(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["dele3"])
    roundtrip(document)


def test_delegation_4(roundtrip):
    document = new_document()
    document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele4"]
    )
    roundtrip(document)


def test_delegation_5(roundtrip):
    document = new_document()
    document.delegation(EX_NS["e1"], EX_NS["ag1"])
    roundtrip(document)


def test_delegation_6(roundtrip):
    document = new_document()
    dele = document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele6"]
    )
    add_labels(dele)
    roundtrip(document)


def test_delegation_7(roundtrip):
    document = new_document()
    dele = document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele7"]
    )
    add_labels(dele)
    add_types(dele)
    roundtrip(document)


def test_delegation_8(roundtrip):
    document = new_document()
    dele = document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele8"]
    )
    add_labels(dele)
    add_types(dele)
    add_further_attributes(dele)
    roundtrip(document)


# COMMUNICATIONS
def test_communication_1(roundtrip):
    document = new_document()
    document.communication(EX_NS["a2"], None, identifier=EX_NS["inf1"])
    roundtrip(document)


def test_communication_2(roundtrip):
    document = new_document()
    document.communication(None, EX_NS["a1"], identifier=EX_NS["inf2"])
    roundtrip(document)


def test_communication_3(roundtrip):
    document = new_document()
    document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf3"])
    roundtrip(document)


def test_communication_4(roundtrip):
    document = new_document()
    document.communication(EX_NS["a2"], EX_NS["a1"])
    roundtrip(document)


def test_communication_5(roundtrip):
    document = new_document()
    inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf5"])
    add_labels(inf)
    roundtrip(document)


def test_communication_6(roundtrip):
    document = new_document()
    inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf6"])
    add_labels(inf)
    add_types(inf)
    roundtrip(document)


def test_communication_7(roundtrip):
    document = new_document()
    inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
    add_labels(inf)
    add_types(inf)
    add_further_attributes(inf)
    roundtrip(document)


# INFLUENCES
def test_influence_1(roundtrip):
    document = new_document()
    document.influence(EX_NS["a2"], None, identifier=EX_NS["inf1"])
    roundtrip(document)


def test_influence_2(roundtrip):
    document = new_document()
    document.influence(None, EX_NS["a1"], identifier=EX_NS["inf2"])
    roundtrip(document)


def test_influence_3(roundtrip):
    document = new_document()
    document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf3"])
    roundtrip(document)


def test_influence_4(roundtrip):
    document = new_document()
    document.influence(EX_NS["a2"], EX_NS["a1"])
    roundtrip(document)


def test_influence_5(roundtrip):
    document = new_document()
    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf5"])
    add_labels(inf)
    roundtrip(document)


def test_influence_6(roundtrip):
    document = new_document()
    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf6"])
    add_labels(inf)
    add_types(inf)
    roundtrip(document)


def test_influence_7(roundtrip):
    document = new_document()
    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
    add_labels(inf)
    add_types(inf)
    add_further_attributes(inf)
    roundtrip(document)


# OTHERS
def test_alternate_1(roundtrip):
    document = new_document()
    document.alternate(EX_NS["e2"], EX_NS["e1"])
    roundtrip(document)


def test_specialization_1(roundtrip):
    document = new_document()
    document.specialization(EX_NS["e2"], EX_NS["e1"])
    roundtrip(document)


def test_mention_1(roundtrip):
    document = new_document()
    document.mention(EX_NS["e2"], EX_NS["e1"], None)
    roundtrip(document)


def test_mention_2(roundtrip):
    document = new_document()
    document.mention(EX_NS["e2"], EX_NS["e1"], EX_NS["b"])
    roundtrip(document)


def test_membership_1(roundtrip):
    document = new_document()
    document.membership(EX_NS["c"], EX_NS["e1"])
    roundtrip(document)


def test_membership_2(roundtrip):
    document = new_document()
    document.membership(EX_NS["c"], EX_NS["e1"])
    document.membership(EX_NS["c"], EX_NS["e2"])
    roundtrip(document)


def test_membership_3(roundtrip):
    document = new_document()
    document.membership(EX_NS["c"], EX_NS["e1"])
    document.membership(EX_NS["c"], EX_NS["e2"])
    document.membership(EX_NS["c"], EX_NS["e3"])
    roundtrip(document)


# SCRUFFY
@scruffy_fmt
def test_scruffy_generation_1(roundtrip):
    document = new_document()
    document.generation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    document.generation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_generation_2(roundtrip):
    document = new_document()
    gen1 = document.generation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    gen2 = document.generation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    gen1.add_attributes([(EX_NS["tag2"], "hello-scruff-gen2")])
    gen2.add_attributes([(EX_NS["tag2"], "hi-scruff-gen2")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_invalidation_1(roundtrip):
    document = new_document()
    document.invalidation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    document.invalidation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_invalidation_2(roundtrip):
    document = new_document()
    inv1 = document.invalidation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    inv2 = document.invalidation(
        EX_NS["e1"],
        EX_NS["a1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    inv1.add_attributes([(EX_NS["tag2"], "hello")])
    inv2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_usage_1(roundtrip):
    document = new_document()
    document.usage(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    document.usage(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_usage_2(roundtrip):
    document = new_document()
    use1 = document.usage(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    use2 = document.usage(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    use1.add_attributes([(EX_NS["tag2"], "hello")])
    use2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_start_1(roundtrip):
    document = new_document()
    document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_start_2(roundtrip):
    document = new_document()
    start1 = document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    start2 = document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    start1.add_attributes([(EX_NS["tag2"], "hello")])
    start2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_start_3(roundtrip):
    document = new_document()
    start1 = document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
        starter=EX_NS["a1s"],
    )
    start2 = document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
        starter=EX_NS["a2s"],
    )
    start1.add_attributes([(EX_NS["tag2"], "hello")])
    start2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    document.activity(identifier=EX_NS["a2"])
    document.activity(identifier=EX_NS["a2s"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_start_4(roundtrip):
    document = new_document()
    start1 = document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
        starter=EX_NS["a1s"],
    )
    start2 = document.start(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
        starter=EX_NS["a2s"],
    )
    start1.add_attributes([(EX_NS["tag2"], "hello")])
    start2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    document.activity(identifier=EX_NS["a1s"])
    document.activity(identifier=EX_NS["a2"])
    document.activity(identifier=EX_NS["a2s"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_end_1(roundtrip):
    document = new_document()
    document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_end_2(roundtrip):
    document = new_document()
    end1 = document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
    )
    end2 = document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
    )
    end1.add_attributes([(EX_NS["tag2"], "hello")])
    end2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_end_3(roundtrip):
    document = new_document()
    end1 = document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
        ender=EX_NS["a1s"],
    )
    end2 = document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
        ender=EX_NS["a2s"],
    )
    end1.add_attributes([(EX_NS["tag2"], "hello")])
    end2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    document.activity(identifier=EX_NS["a2"])
    document.activity(identifier=EX_NS["a2s"])
    roundtrip(document)


@scruffy_fmt
def test_scruffy_end_4(roundtrip):
    document = new_document()
    end1 = document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=datetime.datetime.now(),
        ender=EX_NS["a1s"],
    )
    end2 = document.end(
        EX_NS["a1"],
        EX_NS["e1"],
        identifier=EX_NS["gen1"],
        time=_TIME_2012,
        ender=EX_NS["a2s"],
    )
    end1.add_attributes([(EX_NS["tag2"], "hello")])
    end2.add_attributes([(EX_NS["tag2"], "hi")])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    document.activity(identifier=EX_NS["a1s"])
    document.activity(identifier=EX_NS["a2"])
    document.activity(identifier=EX_NS["a2s"])
    roundtrip(document)


def test_bundle_1(roundtrip):
    document = new_document()

    bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
    bundle1.usage(activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"])
    bundle1.entity(identifier=EX_NS["e1"])
    bundle1.activity(identifier=EX_NS["a1"])

    bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
    bundle2.usage(activity=EX_NS["aa1"], entity=EX_NS["ee1"], identifier=EX_NS["use2"])
    bundle2.entity(identifier=EX_NS["ee1"])
    bundle2.activity(identifier=EX_NS["aa1"])

    document.add_bundle(bundle1)
    document.add_bundle(bundle2)

    roundtrip(document)


def test_bundle_2(roundtrip):
    document = new_document()

    bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
    bundle1.usage(activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"])
    bundle1.entity(identifier=EX_NS["e1"])
    bundle1.activity(identifier=EX_NS["a1"])

    bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
    bundle2.usage(activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use2"])
    bundle2.entity(identifier=EX_NS["e1"])
    bundle2.activity(identifier=EX_NS["a1"])

    document.add_bundle(bundle1)
    document.add_bundle(bundle2)

    roundtrip(document)


def test_bundle_3(roundtrip):
    document = new_document()

    bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
    bundle1.usage(activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"])
    bundle1.entity(identifier=EX_NS["e1"])
    bundle1.activity(identifier=EX_NS["a1"])

    bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
    bundle2.usage(activity=EX_NS["aa1"], entity=EX_NS["ee1"], identifier=EX_NS["use2"])
    bundle2.entity(identifier=EX_NS["ee1"])
    bundle2.activity(identifier=EX_NS["aa1"])

    document.add_bundle(bundle1)
    document.add_bundle(bundle2)

    roundtrip(document)


def test_bundle_4(roundtrip):
    document = new_document()

    bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
    bundle1.usage(activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"])
    bundle1.entity(identifier=EX_NS["e1"])
    bundle1.activity(identifier=EX_NS["a1"])

    bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
    bundle2.usage(
        activity=EX2_NS["aa1"], entity=EX2_NS["ee1"], identifier=EX2_NS["use2"]
    )
    bundle2.entity(identifier=EX2_NS["ee1"])
    bundle2.activity(identifier=EX2_NS["aa1"])

    document.add_bundle(bundle1)
    document.add_bundle(bundle2)

    roundtrip(document)

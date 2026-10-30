"""Shared statement round-trip tests.

Each test builds a document and hands it to the ``roundtrip`` fixture
(``conftest.py``), which runs it once per target in ``SHARED_TARGETS``. The
scruffy and mention tests parametrise ``fmt`` themselves to leave out the one
target that cannot represent the document; the comment above their target
tuples says which test asserts that.
"""

import datetime
import json
import warnings

import pytest

import prov
from prov.model import *
from prov.tests.conftest import SHARED_TARGETS

EX_NS = Namespace("ex", "http://example.org/")
EX2_NS = Namespace("ex2", "http://example2.org/")

_TIME_2012 = datetime.datetime(2012, 12, 3, 21, 8, 16, 686000, tzinfo=datetime.UTC)

# The scruffy documents below hold two relations that share one identifier
# but differ in prov:time. PROV-O cannot represent them: both times land on
# the one qualified IRI and reading back raises, a documented limitation
# (docs/reference/conformance.md) that test_rdf.py's
# test_decode_scruffy_relations_raise_documented_limitation asserts, so the
# rdf target is left out here. PROV-JSONLD defines no Mention term, which
# test_jsonld.py's test_serialize_mention_raises asserts, so the jsonld target
# is left out of the mention round trips.
SCRUFFY_TARGETS = tuple(target for target in SHARED_TARGETS if target != "rdf")
MENTION_TARGETS = tuple(target for target in SHARED_TARGETS if target != "jsonld")


def new_document():
    return ProvDocument()


def add_label(record) -> None:
    record.add_attributes([("prov:label", Literal("hello"))])


def add_labels(record) -> None:
    record.add_attributes(
        [
            ("prov:label", Literal("hello")),
            ("prov:label", Literal("bye", langtag="en")),
            ("prov:label", Literal("bonjour", langtag="fr")),
        ]
    )


def add_types(record) -> None:
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


def add_locations(record) -> None:
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


def add_value(record) -> None:
    record.add_attributes([("prov:value", EX_NS["avalue"])])


def add_further_attributes(record) -> None:
    record.add_attributes(
        [
            (EX_NS["tag1"], "hello"),
            (EX_NS["tag2"], "bye"),
            (EX2_NS["tag3"], "hi"),
            (EX_NS["tag1"], "hello\nover\nmore\nlines"),
        ]
    )


def add_further_attributes0(record) -> None:
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


def add_further_attributes_with_qnames(record) -> None:
    record.add_attributes(
        [
            (EX_NS["tag"], EX2_NS["newyork"]),
            (EX_NS["tag"], EX_NS["london"]),
        ]
    )


# TESTS


# ENTITIES
def test_entity_0(roundtrip) -> None:
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


def test_entity_1(roundtrip) -> None:
    document = new_document()
    document.entity(EX_NS["e1"])
    roundtrip(document)


def test_entity_2(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e2"])
    a.add_attributes([(PROV_LABEL, "entity2")])
    roundtrip(document)


def test_entity_3(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e3"])
    a.add_attributes([(PROV_LABEL, "entity3")])
    add_value(a)
    roundtrip(document)


def test_entity_4(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e4"])
    a.add_attributes([(PROV_LABEL, "entity4")])
    add_labels(a)
    roundtrip(document)


def test_entity_5(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e5"])
    a.add_attributes([(PROV_LABEL, "entity5")])
    add_types(a)
    roundtrip(document)


def test_entity_6(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e6"])
    a.add_attributes([(PROV_LABEL, "entity6")])
    add_locations(a)
    roundtrip(document)


def test_entity_7(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e7"])
    a.add_attributes([(PROV_LABEL, "entity7")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    roundtrip(document)


def test_entity_8(roundtrip) -> None:
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


def test_entity_9(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e9"])
    a.add_attributes([(PROV_LABEL, "entity9")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


def test_entity_10(roundtrip) -> None:
    document = new_document()
    a = document.entity(EX_NS["e10"])
    a.add_attributes([(PROV_LABEL, "entity10")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes0(a)
    roundtrip(document)


# ACTIVITIES
def test_activity_1(roundtrip) -> None:
    document = new_document()
    document.activity(EX_NS["a1"])
    roundtrip(document)


def test_activity_2(roundtrip) -> None:
    document = new_document()
    a = document.activity(EX_NS["a2"])
    a.add_attributes([(PROV_LABEL, "activity2")])
    roundtrip(document)


def test_activity_3(roundtrip) -> None:
    document = new_document()
    document.activity(
        EX_NS["a3"],
        startTime=datetime.datetime.now(),
        endTime=datetime.datetime.now(),
    )
    roundtrip(document)


def test_activity_4(roundtrip) -> None:
    document = new_document()
    a = document.activity(EX_NS["a4"])
    a.add_attributes([(PROV_LABEL, "activity4")])
    add_labels(a)
    roundtrip(document)


def test_activity_5(roundtrip) -> None:
    document = new_document()
    a = document.activity(EX_NS["a5"])
    a.add_attributes([(PROV_LABEL, "activity5")])
    add_types(a)
    roundtrip(document)


def test_activity_6(roundtrip) -> None:
    document = new_document()
    a = document.activity(EX_NS["a6"])
    a.add_attributes([(PROV_LABEL, "activity6")])
    add_locations(a)
    roundtrip(document)


def test_activity_7(roundtrip) -> None:
    document = new_document()
    a = document.activity(EX_NS["a7"])
    a.add_attributes([(PROV_LABEL, "activity7")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    roundtrip(document)


def test_activity_8(roundtrip) -> None:
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


def test_activity_9(roundtrip) -> None:
    document = new_document()
    a = document.activity(EX_NS["a9"])
    a.add_attributes([(PROV_LABEL, "activity9")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


# AGENTS
def test_agent_1(roundtrip) -> None:
    document = new_document()
    document.agent(EX_NS["ag1"])
    roundtrip(document)


def test_agent_2(roundtrip) -> None:
    document = new_document()
    a = document.agent(EX_NS["ag2"])
    a.add_attributes([(PROV_LABEL, "agent2")])
    roundtrip(document)


def test_agent_3(roundtrip) -> None:
    document = new_document()
    a = document.agent(EX_NS["ag3"])
    a.add_attributes(
        [
            (PROV_LABEL, "agent3"),
            (PROV_LABEL, Literal("hello")),
        ]
    )
    roundtrip(document)


def test_agent_4(roundtrip) -> None:
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


def test_agent_5(roundtrip) -> None:
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


def test_agent_6(roundtrip) -> None:
    document = new_document()
    a = document.agent(EX_NS["ag6"])
    a.add_attributes([(PROV_LABEL, "agent6")])
    add_types(a)
    roundtrip(document)


def test_agent_7(roundtrip) -> None:
    document = new_document()
    a = document.agent(EX_NS["ag7"])
    a.add_attributes([(PROV_LABEL, "agent7")])
    add_locations(a)
    add_labels(a)
    roundtrip(document)


def test_agent_8(roundtrip) -> None:
    document = new_document()
    a = document.agent(EX_NS["ag8"])
    a.add_attributes([(PROV_LABEL, "agent8")])
    add_types(a)
    add_locations(a)
    add_labels(a)
    add_further_attributes(a)
    roundtrip(document)


# GENERATIONS
def test_generation_1(roundtrip) -> None:
    document = new_document()
    document.generation(EX_NS["e1"], identifier=EX_NS["gen1"])
    roundtrip(document)


def test_generation_2(roundtrip) -> None:
    document = new_document()
    document.generation(EX_NS["e1"], identifier=EX_NS["gen2"], activity=EX_NS["a1"])
    roundtrip(document)


def test_generation_3(roundtrip) -> None:
    document = new_document()
    a = document.generation(EX_NS["e1"], identifier=EX_NS["gen3"], activity=EX_NS["a1"])
    a.add_attributes(
        [
            (PROV_ROLE, "somerole"),
            (PROV_ROLE, "otherRole"),
        ]
    )
    roundtrip(document)


def test_generation_4(roundtrip) -> None:
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


def test_generation_5(roundtrip) -> None:
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


def test_generation_6(roundtrip) -> None:
    document = new_document()
    document.generation(EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now())
    roundtrip(document)


def test_generation_7(roundtrip) -> None:
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
def test_usage_1(roundtrip) -> None:
    document = new_document()
    document.usage(None, entity=EX_NS["e1"], identifier=EX_NS["use1"])
    roundtrip(document)


def test_usage_2(roundtrip) -> None:
    document = new_document()
    document.usage(EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use2"])
    roundtrip(document)


def test_usage_3(roundtrip) -> None:
    document = new_document()
    use = document.usage(EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use3"])
    use.add_attributes([(PROV_ROLE, "somerole"), (PROV_ROLE, "otherRole")])
    roundtrip(document)


def test_usage_4(roundtrip) -> None:
    document = new_document()
    use = document.usage(
        EX_NS["a1"],
        entity=EX_NS["e1"],
        identifier=EX_NS["use4"],
        time=datetime.datetime.now(),
    )
    use.add_attributes([(PROV_ROLE, "somerole")])
    roundtrip(document)


def test_usage_5(roundtrip) -> None:
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


def test_usage_6(roundtrip) -> None:
    document = new_document()
    document.usage(EX_NS["a1"], entity=EX_NS["e1"])
    roundtrip(document)


def test_usage_7(roundtrip) -> None:
    document = new_document()
    use = document.usage(EX_NS["a1"], entity=EX_NS["e1"], time=datetime.datetime.now())
    use.add_attributes([(PROV_ROLE, "somerole")])
    add_types(use)
    add_locations(use)
    add_labels(use)
    add_further_attributes(use)
    roundtrip(document)


# INVALIDATIONS
def test_invalidation_1(roundtrip) -> None:
    document = new_document()
    document.invalidation(EX_NS["e1"], identifier=EX_NS["inv1"])
    roundtrip(document)


def test_invalidation_2(roundtrip) -> None:
    document = new_document()
    document.invalidation(EX_NS["e1"], identifier=EX_NS["inv2"], activity=EX_NS["a1"])
    roundtrip(document)


def test_invalidation_3(roundtrip) -> None:
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


def test_invalidation_4(roundtrip) -> None:
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


def test_invalidation_5(roundtrip) -> None:
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


def test_invalidation_6(roundtrip) -> None:
    document = new_document()
    document.invalidation(EX_NS["e1"], activity=EX_NS["a1"])
    roundtrip(document)


def test_invalidation_7(roundtrip) -> None:
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
def test_start_1(roundtrip) -> None:
    document = new_document()
    document.start(None, trigger=EX_NS["e1"], identifier=EX_NS["start1"])
    roundtrip(document)


def test_start_2(roundtrip) -> None:
    document = new_document()
    document.start(EX_NS["a1"], trigger=EX_NS["e1"], identifier=EX_NS["start2"])
    roundtrip(document)


def test_start_3(roundtrip) -> None:
    document = new_document()
    document.start(EX_NS["a1"], identifier=EX_NS["start3"])
    roundtrip(document)


def test_start_4(roundtrip) -> None:
    document = new_document()
    document.start(
        None, trigger=EX_NS["e1"], identifier=EX_NS["start4"], starter=EX_NS["a2"]
    )
    roundtrip(document)


def test_start_5(roundtrip) -> None:
    document = new_document()
    document.start(
        EX_NS["a1"],
        trigger=EX_NS["e1"],
        identifier=EX_NS["start5"],
        starter=EX_NS["a2"],
    )
    roundtrip(document)


def test_start_6(roundtrip) -> None:
    document = new_document()
    document.start(EX_NS["a1"], identifier=EX_NS["start6"], starter=EX_NS["a2"])
    roundtrip(document)


def test_start_7(roundtrip) -> None:
    document = new_document()
    document.start(
        EX_NS["a1"],
        identifier=EX_NS["start7"],
        starter=EX_NS["a2"],
        time=datetime.datetime.now(),
    )
    roundtrip(document)


def test_start_8(roundtrip) -> None:
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


def test_start_9(roundtrip) -> None:
    document = new_document()
    document.start(EX_NS["a1"], trigger=EX_NS["e1"])
    roundtrip(document)


def test_start_10(roundtrip) -> None:
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
def test_end_1(roundtrip) -> None:
    document = new_document()
    document.end(None, trigger=EX_NS["e1"], identifier=EX_NS["end1"])
    roundtrip(document)


def test_end_2(roundtrip) -> None:
    document = new_document()
    document.end(EX_NS["a1"], trigger=EX_NS["e1"], identifier=EX_NS["end2"])
    roundtrip(document)


def test_end_3(roundtrip) -> None:
    document = new_document()
    document.end(EX_NS["a1"], identifier=EX_NS["end3"])
    roundtrip(document)


def test_end_4(roundtrip) -> None:
    document = new_document()
    document.end(None, trigger=EX_NS["e1"], identifier=EX_NS["end4"], ender=EX_NS["a2"])
    roundtrip(document)


def test_end_5(roundtrip) -> None:
    document = new_document()
    document.end(
        EX_NS["a1"],
        trigger=EX_NS["e1"],
        identifier=EX_NS["end5"],
        ender=EX_NS["a2"],
    )
    roundtrip(document)


def test_end_6(roundtrip) -> None:
    document = new_document()
    document.end(EX_NS["a1"], identifier=EX_NS["end6"], ender=EX_NS["a2"])
    roundtrip(document)


def test_end_7(roundtrip) -> None:
    document = new_document()
    document.end(
        EX_NS["a1"],
        identifier=EX_NS["end7"],
        ender=EX_NS["a2"],
        time=datetime.datetime.now(),
    )
    roundtrip(document)


def test_end_8(roundtrip) -> None:
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


def test_end_9(roundtrip) -> None:
    document = new_document()
    document.end(EX_NS["a1"], trigger=EX_NS["e1"])
    roundtrip(document)


def test_end_10(roundtrip) -> None:
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
def test_derivation_1(roundtrip) -> None:
    document = new_document()
    document.derivation(None, usedEntity=EX_NS["e1"], identifier=EX_NS["der1"])
    roundtrip(document)


def test_derivation_2(roundtrip) -> None:
    document = new_document()
    document.derivation(EX_NS["e2"], usedEntity=None, identifier=EX_NS["der2"])
    roundtrip(document)


def test_derivation_3(roundtrip) -> None:
    document = new_document()
    document.derivation(EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der3"])
    roundtrip(document)


def test_derivation_4(roundtrip) -> None:
    document = new_document()
    der = document.derivation(
        EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der4"]
    )
    add_label(der)
    roundtrip(document)


def test_derivation_5(roundtrip) -> None:
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["der5"],
        activity=EX_NS["a"],
    )
    roundtrip(document)


def test_derivation_6(roundtrip) -> None:
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        identifier=EX_NS["der6"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
    )
    roundtrip(document)


def test_derivation_7(roundtrip) -> None:
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


def test_derivation_8(roundtrip) -> None:
    document = new_document()
    der = document.derivation(
        EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der8"]
    )
    add_label(der)
    add_types(der)
    add_further_attributes(der)
    roundtrip(document)


def test_derivation_9(roundtrip) -> None:
    document = new_document()
    der = document.derivation(EX_NS["e2"], usedEntity=None)
    add_types(der)
    roundtrip(document)


def test_derivation_10(roundtrip) -> None:
    document = new_document()
    document.derivation(
        EX_NS["e2"],
        usedEntity=EX_NS["e1"],
        activity=EX_NS["a"],
        usage=EX_NS["u"],
        generation=EX_NS["g"],
    )
    roundtrip(document)


def test_derivation_11(roundtrip) -> None:
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


def test_derivation_12(roundtrip) -> None:
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


def test_derivation_13(roundtrip) -> None:
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
def test_association_1(roundtrip) -> None:
    document = new_document()
    document.association(EX_NS["a1"], identifier=EX_NS["assoc1"])
    roundtrip(document)


def test_association_2(roundtrip) -> None:
    document = new_document()
    document.association(None, agent=EX_NS["ag1"], identifier=EX_NS["assoc2"])
    roundtrip(document)


def test_association_3(roundtrip) -> None:
    document = new_document()
    document.association(EX_NS["a1"], agent=EX_NS["ag1"], identifier=EX_NS["assoc3"])
    roundtrip(document)


def test_association_4(roundtrip) -> None:
    document = new_document()
    document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc4"],
        plan=EX_NS["plan1"],
    )
    roundtrip(document)


def test_association_5(roundtrip) -> None:
    document = new_document()
    document.association(EX_NS["a1"], agent=EX_NS["ag1"])
    roundtrip(document)


def test_association_6(roundtrip) -> None:
    document = new_document()
    assoc = document.association(
        EX_NS["a1"],
        agent=EX_NS["ag1"],
        identifier=EX_NS["assoc6"],
        plan=EX_NS["plan1"],
    )
    add_labels(assoc)
    roundtrip(document)


def test_association_7(roundtrip) -> None:
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


def test_association_8(roundtrip) -> None:
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


def test_association_9(roundtrip) -> None:
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


def test_association_10(roundtrip) -> None:
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
def test_attribution_1(roundtrip) -> None:
    document = new_document()
    document.attribution(EX_NS["e1"], None, identifier=EX_NS["attr1"])
    roundtrip(document)


def test_attribution_2(roundtrip) -> None:
    document = new_document()
    document.attribution(None, EX_NS["ag1"], identifier=EX_NS["attr2"])
    roundtrip(document)


def test_attribution_3(roundtrip) -> None:
    document = new_document()
    document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr3"])
    roundtrip(document)


def test_attribution_4(roundtrip) -> None:
    document = new_document()
    document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr4"])
    roundtrip(document)


def test_attribution_5(roundtrip) -> None:
    document = new_document()
    document.attribution(EX_NS["e1"], EX_NS["ag1"])
    roundtrip(document)


def test_attribution_6(roundtrip) -> None:
    document = new_document()
    attr = document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr6"])
    add_labels(attr)
    roundtrip(document)


def test_attribution_7(roundtrip) -> None:
    document = new_document()
    attr = document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr7"])
    add_labels(attr)
    add_types(attr)
    roundtrip(document)


def test_attribution_8(roundtrip) -> None:
    document = new_document()
    attr = document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr8"])
    add_labels(attr)
    add_types(attr)
    add_further_attributes(attr)
    roundtrip(document)


# DELEGATIONS
def test_delegation_1(roundtrip) -> None:
    document = new_document()
    document.delegation(EX_NS["e1"], None, identifier=EX_NS["dele1"])
    roundtrip(document)


def test_delegation_2(roundtrip) -> None:
    document = new_document()
    document.delegation(None, EX_NS["ag1"], identifier=EX_NS["dele2"])
    roundtrip(document)


def test_delegation_3(roundtrip) -> None:
    document = new_document()
    document.delegation(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["dele3"])
    roundtrip(document)


def test_delegation_4(roundtrip) -> None:
    document = new_document()
    document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele4"]
    )
    roundtrip(document)


def test_delegation_5(roundtrip) -> None:
    document = new_document()
    document.delegation(EX_NS["e1"], EX_NS["ag1"])
    roundtrip(document)


def test_delegation_6(roundtrip) -> None:
    document = new_document()
    dele = document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele6"]
    )
    add_labels(dele)
    roundtrip(document)


def test_delegation_7(roundtrip) -> None:
    document = new_document()
    dele = document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele7"]
    )
    add_labels(dele)
    add_types(dele)
    roundtrip(document)


def test_delegation_8(roundtrip) -> None:
    document = new_document()
    dele = document.delegation(
        EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele8"]
    )
    add_labels(dele)
    add_types(dele)
    add_further_attributes(dele)
    roundtrip(document)


# COMMUNICATIONS
def test_communication_1(roundtrip) -> None:
    document = new_document()
    document.communication(EX_NS["a2"], None, identifier=EX_NS["inf1"])
    roundtrip(document)


def test_communication_2(roundtrip) -> None:
    document = new_document()
    document.communication(None, EX_NS["a1"], identifier=EX_NS["inf2"])
    roundtrip(document)


def test_communication_3(roundtrip) -> None:
    document = new_document()
    document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf3"])
    roundtrip(document)


def test_communication_4(roundtrip) -> None:
    document = new_document()
    document.communication(EX_NS["a2"], EX_NS["a1"])
    roundtrip(document)


def test_communication_5(roundtrip) -> None:
    document = new_document()
    inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf5"])
    add_labels(inf)
    roundtrip(document)


def test_communication_6(roundtrip) -> None:
    document = new_document()
    inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf6"])
    add_labels(inf)
    add_types(inf)
    roundtrip(document)


def test_communication_7(roundtrip) -> None:
    document = new_document()
    inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
    add_labels(inf)
    add_types(inf)
    add_further_attributes(inf)
    roundtrip(document)


# INFLUENCES
def test_influence_1(roundtrip) -> None:
    document = new_document()
    document.influence(EX_NS["a2"], None, identifier=EX_NS["inf1"])
    roundtrip(document)


def test_influence_2(roundtrip) -> None:
    document = new_document()
    document.influence(None, EX_NS["a1"], identifier=EX_NS["inf2"])
    roundtrip(document)


def test_influence_3(roundtrip) -> None:
    document = new_document()
    document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf3"])
    roundtrip(document)


def test_influence_4(roundtrip) -> None:
    document = new_document()
    document.influence(EX_NS["a2"], EX_NS["a1"])
    roundtrip(document)


def test_influence_5(roundtrip) -> None:
    document = new_document()
    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf5"])
    add_labels(inf)
    roundtrip(document)


def test_influence_6(roundtrip) -> None:
    document = new_document()
    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf6"])
    add_labels(inf)
    add_types(inf)
    roundtrip(document)


def test_influence_7(roundtrip) -> None:
    document = new_document()
    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
    add_labels(inf)
    add_types(inf)
    add_further_attributes(inf)
    roundtrip(document)


# OTHERS
def test_alternate_1(roundtrip) -> None:
    document = new_document()
    document.alternate(EX_NS["e2"], EX_NS["e1"])
    roundtrip(document)


def test_specialization_1(roundtrip) -> None:
    document = new_document()
    document.specialization(EX_NS["e2"], EX_NS["e1"])
    roundtrip(document)


@pytest.mark.parametrize("fmt", MENTION_TARGETS)
def test_mention_1(roundtrip) -> None:
    document = new_document()
    document.mention(EX_NS["e2"], EX_NS["e1"], None)
    roundtrip(document)


@pytest.mark.parametrize("fmt", MENTION_TARGETS)
def test_mention_2(roundtrip) -> None:
    document = new_document()
    document.mention(EX_NS["e2"], EX_NS["e1"], EX_NS["b"])
    roundtrip(document)


_EX_URI = "http://example.org/"
_NO_ENTITY = "hadMember requires a value for prov:entity"
_PROVN_PARTYLESS = (
    "document\nprefix ex <http://example.org/>\n"
    "hadMember(ex:c, -)\nentity(ex:e)\nendDocument"
)
_PROVN_SKIPPED = f"PROV-N statement skipped: line 3, column 1: {_NO_ENTITY}"
_XML_MEMBER = (
    '<prov:document xmlns:prov="http://www.w3.org/ns/prov#"'
    ' xmlns:ex="http://example.org/">\n'
    '<prov:entity prov:id="ex:e"/>\n'
    '<prov:hadMember prov:id="ex:m"><prov:collection prov:ref="ex:c"/><ex:k>v</ex:k>'
    "</prov:hadMember>\n</prov:document>"
)
_TURTLE_MEMBER = (
    "@prefix prov: <http://www.w3.org/ns/prov#> .\n"
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
    "@prefix ex: <http://example.org/> .\n"
    "ex:e a prov:Entity .\n"
    'ex:m a prov:Membership ; prov:collection ex:c ; rdfs:label "m" .\n'
)


def _json_members(*instances: dict) -> str:
    return json.dumps(
        {
            "prefix": {"ex": _EX_URI},
            "entity": {"ex:e": {}},
            "hadMember": {"_:m1": list(instances)},
        }
    )


_MEMBER = {"prov:collection": "ex:c", "prov:entity": "ex:e2"}
_PARTYLESS = {"prov:collection": "ex:c"}


@pytest.mark.parametrize(
    ("fmt", "kwargs", "text", "warning", "extra"),
    [
        pytest.param(
            "provn",
            {"profile": "default"},
            _PROVN_PARTYLESS,
            _PROVN_SKIPPED,
            (),
            id="provn-default",
        ),
        pytest.param(
            "provn",
            {"profile": "lenient"},
            _PROVN_PARTYLESS,
            _PROVN_SKIPPED,
            (),
            id="provn-lenient",
        ),
        pytest.param(
            "provn",
            {},
            "document\nprefix ex <http://example.org/>\nbundle ex:b\nentity(ex:e)\n"
            "hadMember(ex:c, -)\nendBundle\nendDocument",
            f"PROV-N statement skipped: line 5, column 1: {_NO_ENTITY}",
            (),
            id="provn-in-a-bundle",
        ),
        pytest.param(
            None,
            {},
            _PROVN_PARTYLESS,
            _PROVN_SKIPPED,
            (),
            id="provn-read-detected",
        ),
        pytest.param(
            "json",
            {},
            json.dumps(
                {
                    "prefix": {"ex": _EX_URI},
                    "entity": {"ex:e": {}},
                    "hadMember": {"_:m1": _PARTYLESS},
                }
            ),
            f"record '_:m1': {_NO_ENTITY}",
            (),
            id="json",
        ),
        pytest.param(
            "json",
            {},
            _json_members(_MEMBER, _PARTYLESS),
            f"record '_:m1': {_NO_ENTITY}",
            (("ex:c", "ex:e2"),),
            id="json-skipped-instance-last",
        ),
        pytest.param(
            "json",
            {},
            _json_members(_PARTYLESS, _MEMBER),
            f"record '_:m1': {_NO_ENTITY}",
            (("ex:c", "ex:e2"),),
            id="json-skipped-instance-first",
        ),
        pytest.param(
            "jsonld",
            {},
            json.dumps(
                {
                    "@context": [{"ex": _EX_URI}],
                    "@graph": [
                        {"@type": "Entity", "@id": "ex:e"},
                        {"@type": "Membership", "collection": "ex:c"},
                    ],
                }
            ),
            f"an anonymous prov:Membership: {_NO_ENTITY}",
            (),
            id="jsonld",
        ),
        pytest.param(
            "xml",
            {},
            _XML_MEMBER,
            f"line 3, <prov:hadMember> 'ex:m': {_NO_ENTITY}",
            (),
            id="xml",
        ),
        pytest.param(
            "rdf",
            {"rdf_format": "turtle"},
            _TURTLE_MEMBER,
            f"subject 'http://example.org/m': {_NO_ENTITY}",
            (),
            id="rdf",
        ),
    ],
)
def test_a_reader_skips_a_relation_missing_a_party(
    fmt: str | None, kwargs: dict, text: str, warning: str, extra: tuple
) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        document = prov.read(text, format=fmt, **kwargs)
    assert [str(w.message) for w in caught if issubclass(w.category, ProvWarning)] == [
        warning
    ]
    assert not [w for w in caught if w.category is UserWarning]
    # The statement stays in the scope that held it: a bundle's own records, or
    # the document's.
    scope = next(iter(document.bundles), document)
    assert [str(r.identifier) for r in scope.get_records(ProvEntity)] == ["ex:e"]
    assert [
        tuple(str(party) for party in r.args) for r in scope.get_records(ProvMembership)
    ] == list(extra)
    assert len(list(scope.get_records())) == 1 + len(extra)
    if scope is not document:
        assert list(document.get_records()) == []


def test_membership_1(roundtrip) -> None:
    document = new_document()
    document.membership(EX_NS["c"], EX_NS["e1"])
    roundtrip(document)


def test_membership_2(roundtrip) -> None:
    document = new_document()
    document.membership(EX_NS["c"], EX_NS["e1"])
    document.membership(EX_NS["c"], EX_NS["e2"])
    roundtrip(document)


def test_membership_3(roundtrip) -> None:
    document = new_document()
    document.membership(EX_NS["c"], EX_NS["e1"])
    document.membership(EX_NS["c"], EX_NS["e2"])
    document.membership(EX_NS["c"], EX_NS["e3"])
    roundtrip(document)


# The scruffy documents: two relations of one family sharing ex:gen1, the
# first at the current time and the second at _TIME_2012, with the ex:tag2
# values, the starter or ender endpoints and the extra activities each row
# gives. Every row declares ex:e1 and ex:a1.
_SCRUFFY_ARGUMENTS = {
    "generation": ("e1", "a1"),
    "invalidation": ("e1", "a1"),
    "usage": ("a1", "e1"),
    "start": ("a1", "e1"),
    "end": ("a1", "e1"),
}
_SCRUFFY_ENDPOINT = {"start": "starter", "end": "ender"}
_TAGS = ("hello", "hi")
_ENDPOINTS = ("a1s", "a2s")
SCRUFFY_CASES = [
    pytest.param("generation", None, None, (), id="generation_1"),
    pytest.param(
        "generation",
        ("hello-scruff-gen2", "hi-scruff-gen2"),
        None,
        (),
        id="generation_2",
    ),
    pytest.param("invalidation", None, None, (), id="invalidation_1"),
    pytest.param("invalidation", _TAGS, None, (), id="invalidation_2"),
    pytest.param("usage", None, None, (), id="usage_1"),
    pytest.param("usage", _TAGS, None, (), id="usage_2"),
    pytest.param("start", None, None, (), id="start_1"),
    pytest.param("start", _TAGS, None, (), id="start_2"),
    pytest.param("start", _TAGS, _ENDPOINTS, ("a2", "a2s"), id="start_3"),
    pytest.param("start", _TAGS, _ENDPOINTS, ("a1s", "a2", "a2s"), id="start_4"),
    pytest.param("end", None, None, (), id="end_1"),
    pytest.param("end", _TAGS, None, (), id="end_2"),
    pytest.param("end", _TAGS, _ENDPOINTS, ("a2", "a2s"), id="end_3"),
    pytest.param("end", _TAGS, _ENDPOINTS, ("a1s", "a2", "a2s"), id="end_4"),
]


@pytest.mark.parametrize("fmt", SCRUFFY_TARGETS)
@pytest.mark.parametrize(("family", "tags", "endpoints", "activities"), SCRUFFY_CASES)
def test_scruffy_relation(roundtrip, family, tags, endpoints, activities) -> None:
    document = new_document()
    factory = getattr(document, family)
    arguments = [EX_NS[name] for name in _SCRUFFY_ARGUMENTS[family]]
    for i, time in enumerate((datetime.datetime.now(), _TIME_2012)):
        extra = {_SCRUFFY_ENDPOINT[family]: EX_NS[endpoints[i]]} if endpoints else {}
        relation = factory(*arguments, identifier=EX_NS["gen1"], time=time, **extra)
        if tags:
            relation.add_attributes([(EX_NS["tag2"], tags[i])])
    document.entity(identifier=EX_NS["e1"])
    document.activity(identifier=EX_NS["a1"])
    for name in activities:
        document.activity(identifier=EX_NS[name])
    roundtrip(document)


def test_bundle_1(roundtrip) -> None:
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


def test_bundle_2(roundtrip) -> None:
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


def test_bundle_4(roundtrip) -> None:
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

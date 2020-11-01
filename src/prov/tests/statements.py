from prov.model import *

EX_NS = Namespace("ex", "http://example.org/")
EX2_NS = Namespace("ex2", "http://example2.org/")


class TestStatementsBase(object):
    """This is the base class for testing different PROV statements.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    def new_document(self):
        return ProvDocument()

    def add_label(self, record):
        record.add_attributes([("prov:label", Literal("hello"))])

    def add_labels(self, record):
        record.add_attributes(
            [
                ("prov:label", Literal("hello")),
                ("prov:label", Literal("bye", langtag="en")),
                ("prov:label", Literal("bonjour", langtag="fr")),
            ]
        )

    def add_types(self, record):
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

    def add_locations(self, record):
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

    def add_value(self, record):
        record.add_attributes([("prov:value", EX_NS["avalue"])])

    def add_further_attributes(self, record):
        record.add_attributes(
            [
                (EX_NS["tag1"], "hello"),
                (EX_NS["tag2"], "bye"),
                (EX2_NS["tag3"], "hi"),
                (EX_NS["tag1"], "hello\nover\nmore\nlines"),
            ]
        )

    def add_further_attributes0(self, record):
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

        self.add_further_attributes_with_qnames(record)

    def add_further_attributes_with_qnames(self, record):
        record.add_attributes(
            [
                (EX_NS["tag"], EX2_NS["newyork"]),
                (EX_NS["tag"], EX_NS["london"]),
            ]
        )

    # TESTS

    # ENTITIES
    def test_entity_0(self):
        document = self.new_document()
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
        self.do_tests(document)

    def test_entity_1(self):
        document = self.new_document()
        document.entity(EX_NS["e1"])
        self.do_tests(document)

    def test_entity_2(self):
        document = self.new_document()
        a = document.entity(EX_NS["e2"])
        a.add_attributes([(PROV_LABEL, "entity2")])
        self.do_tests(document)

    def test_entity_3(self):
        document = self.new_document()
        a = document.entity(EX_NS["e3"])
        a.add_attributes([(PROV_LABEL, "entity3")])
        self.add_value(a)
        self.do_tests(document)

    def test_entity_4(self):
        document = self.new_document()
        a = document.entity(EX_NS["e4"])
        a.add_attributes([(PROV_LABEL, "entity4")])
        self.add_labels(a)
        self.do_tests(document)

    def test_entity_5(self):
        document = self.new_document()
        a = document.entity(EX_NS["e5"])
        a.add_attributes([(PROV_LABEL, "entity5")])
        self.add_types(a)
        self.do_tests(document)

    def test_entity_6(self):
        document = self.new_document()
        a = document.entity(EX_NS["e6"])
        a.add_attributes([(PROV_LABEL, "entity6")])
        self.add_locations(a)
        self.do_tests(document)

    def test_entity_7(self):
        document = self.new_document()
        a = document.entity(EX_NS["e7"])
        a.add_attributes([(PROV_LABEL, "entity7")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.do_tests(document)

    def test_entity_8(self):
        document = self.new_document()
        a = document.entity(EX_NS["e8"])
        a.add_attributes([(PROV_LABEL, "entity8")])
        self.add_types(a)
        self.add_types(a)
        self.add_locations(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_labels(a)
        self.do_tests(document)

    def test_entity_9(self):
        document = self.new_document()
        a = document.entity(EX_NS["e9"])
        a.add_attributes([(PROV_LABEL, "entity9")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_further_attributes(a)
        self.do_tests(document)

    def test_entity_10(self):
        document = self.new_document()
        a = document.entity(EX_NS["e10"])
        a.add_attributes([(PROV_LABEL, "entity10")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_further_attributes0(a)
        self.do_tests(document)

    # ACTIVITIES
    def test_activity_1(self):
        document = self.new_document()
        document.activity(EX_NS["a1"])
        self.do_tests(document)

    def test_activity_2(self):
        document = self.new_document()
        a = document.activity(EX_NS["a2"])
        a.add_attributes([(PROV_LABEL, "activity2")])
        self.do_tests(document)

    def test_activity_3(self):
        document = self.new_document()
        document.activity(
            EX_NS["a3"],
            startTime=datetime.datetime.now(),
            endTime=datetime.datetime.now(),
        )
        self.do_tests(document)

    def test_activity_4(self):
        document = self.new_document()
        a = document.activity(EX_NS["a4"])
        a.add_attributes([(PROV_LABEL, "activity4")])
        self.add_labels(a)
        self.do_tests(document)

    def test_activity_5(self):
        document = self.new_document()
        a = document.activity(EX_NS["a5"])
        a.add_attributes([(PROV_LABEL, "activity5")])
        self.add_types(a)
        self.do_tests(document)

    def test_activity_6(self):
        document = self.new_document()
        a = document.activity(EX_NS["a6"])
        a.add_attributes([(PROV_LABEL, "activity6")])
        self.add_locations(a)
        self.do_tests(document)

    def test_activity_7(self):
        document = self.new_document()
        a = document.activity(EX_NS["a7"])
        a.add_attributes([(PROV_LABEL, "activity7")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.do_tests(document)

    def test_activity_8(self):
        document = self.new_document()
        a = document.activity(
            EX_NS["a8"],
            startTime=datetime.datetime.now(),
            endTime=datetime.datetime.now(),
        )
        a.add_attributes([(PROV_LABEL, "activity8")])
        self.add_types(a)
        self.add_types(a)
        self.add_locations(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_labels(a)
        self.do_tests(document)

    def test_activity_9(self):
        document = self.new_document()
        a = document.activity(EX_NS["a9"])
        a.add_attributes([(PROV_LABEL, "activity9")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_further_attributes(a)
        self.do_tests(document)

    # AGENTS
    def test_agent_1(self):
        document = self.new_document()
        document.agent(EX_NS["ag1"])
        self.do_tests(document)

    def test_agent_2(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag2"])
        a.add_attributes([(PROV_LABEL, "agent2")])
        self.do_tests(document)

    def test_agent_3(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag3"])
        a.add_attributes(
            [
                (PROV_LABEL, "agent3"),
                (PROV_LABEL, Literal("hello")),
            ]
        )
        self.do_tests(document)

    def test_agent_4(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag4"])
        a.add_attributes(
            [
                (PROV_LABEL, "agent4"),
                (PROV_LABEL, Literal("hello")),
                (PROV_LABEL, Literal("bye", langtag="en")),
            ]
        )
        self.do_tests(document)

    def test_agent_5(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag5"])
        a.add_attributes(
            [
                (PROV_LABEL, "agent5"),
                (PROV_LABEL, Literal("hello")),
                (PROV_LABEL, Literal("bye", langtag="en")),
                (PROV_LABEL, Literal("bonjour", langtag="french")),
            ]
        )
        self.do_tests(document)

    def test_agent_6(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag6"])
        a.add_attributes([(PROV_LABEL, "agent6")])
        self.add_types(a)
        self.do_tests(document)

    def test_agent_7(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag7"])
        a.add_attributes([(PROV_LABEL, "agent7")])
        self.add_locations(a)
        self.add_labels(a)
        self.do_tests(document)

    def test_agent_8(self):
        document = self.new_document()
        a = document.agent(EX_NS["ag8"])
        a.add_attributes([(PROV_LABEL, "agent8")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_further_attributes(a)
        self.do_tests(document)

    # GENERATIONS
    def test_generation_1(self):
        document = self.new_document()
        document.generation(EX_NS["e1"], identifier=EX_NS["gen1"])
        self.do_tests(document)

    def test_generation_2(self):
        document = self.new_document()
        document.generation(EX_NS["e1"], identifier=EX_NS["gen2"], activity=EX_NS["a1"])
        self.do_tests(document)

    def test_generation_3(self):
        document = self.new_document()
        a = document.generation(
            EX_NS["e1"], identifier=EX_NS["gen3"], activity=EX_NS["a1"]
        )
        a.add_attributes(
            [
                (PROV_ROLE, "somerole"),
                (PROV_ROLE, "otherRole"),
            ]
        )
        self.do_tests(document)

    def test_generation_4(self):
        document = self.new_document()
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
        self.do_tests(document)

    def test_generation_5(self):
        document = self.new_document()
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
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_further_attributes(a)
        self.do_tests(document)

    def test_generation_6(self):
        document = self.new_document()
        document.generation(
            EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now()
        )
        self.do_tests(document)

    def test_generation_7(self):
        document = self.new_document()
        a = document.generation(
            EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now()
        )
        a.add_attributes([(PROV_ROLE, "somerole")])
        self.add_types(a)
        self.add_locations(a)
        self.add_labels(a)
        self.add_further_attributes(a)
        self.do_tests(document)

    # USAGE
    def test_usage_1(self):
        document = self.new_document()
        document.usage(None, entity=EX_NS["e1"], identifier=EX_NS["use1"])
        self.do_tests(document)

    def test_usage_2(self):
        document = self.new_document()
        document.usage(EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use2"])
        self.do_tests(document)

    def test_usage_3(self):
        document = self.new_document()
        use = document.usage(EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use3"])
        use.add_attributes([(PROV_ROLE, "somerole"), (PROV_ROLE, "otherRole")])
        self.do_tests(document)

    def test_usage_4(self):
        document = self.new_document()
        use = document.usage(
            EX_NS["a1"],
            entity=EX_NS["e1"],
            identifier=EX_NS["use4"],
            time=datetime.datetime.now(),
        )
        use.add_attributes([(PROV_ROLE, "somerole")])
        self.do_tests(document)

    def test_usage_5(self):
        document = self.new_document()
        use = document.usage(
            EX_NS["a1"],
            entity=EX_NS["e1"],
            identifier=EX_NS["use5"],
            time=datetime.datetime.now(),
        )
        use.add_attributes([(PROV_ROLE, "somerole")])
        self.add_types(use)
        self.add_locations(use)
        self.add_labels(use)
        self.add_further_attributes(use)
        self.do_tests(document)

    def test_usage_6(self):
        document = self.new_document()
        document.usage(EX_NS["a1"], entity=EX_NS["e1"])
        self.do_tests(document)

    def test_usage_7(self):
        document = self.new_document()
        use = document.usage(
            EX_NS["a1"], entity=EX_NS["e1"], time=datetime.datetime.now()
        )
        use.add_attributes([(PROV_ROLE, "somerole")])
        self.add_types(use)
        self.add_locations(use)
        self.add_labels(use)
        self.add_further_attributes(use)
        self.do_tests(document)

    # INVALIDATIONS
    def test_invalidation_1(self):
        document = self.new_document()
        document.invalidation(EX_NS["e1"], identifier=EX_NS["inv1"])
        self.do_tests(document)

    def test_invalidation_2(self):
        document = self.new_document()
        document.invalidation(
            EX_NS["e1"], identifier=EX_NS["inv2"], activity=EX_NS["a1"]
        )
        self.do_tests(document)

    def test_invalidation_3(self):
        document = self.new_document()
        inv = document.invalidation(
            EX_NS["e1"], identifier=EX_NS["inv3"], activity=EX_NS["a1"]
        )
        inv.add_attributes(
            [
                (PROV_ROLE, "someRole"),
                (PROV_ROLE, "otherRole"),
            ]
        )
        self.do_tests(document)

    def test_invalidation_4(self):
        document = self.new_document()
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
        self.do_tests(document)

    def test_invalidation_5(self):
        document = self.new_document()
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
        self.add_types(inv)
        self.add_locations(inv)
        self.add_labels(inv)
        self.add_further_attributes(inv)
        self.do_tests(document)

    def test_invalidation_6(self):
        document = self.new_document()
        document.invalidation(EX_NS["e1"], activity=EX_NS["a1"])
        self.do_tests(document)

    def test_invalidation_7(self):
        document = self.new_document()
        inv = document.invalidation(
            EX_NS["e1"], activity=EX_NS["a1"], time=datetime.datetime.now()
        )
        inv.add_attributes(
            [
                (PROV_ROLE, "someRole"),
            ]
        )
        self.add_types(inv)
        self.add_locations(inv)
        self.add_labels(inv)
        self.add_further_attributes(inv)
        self.do_tests(document)

    # STARTS
    def test_start_1(self):
        document = self.new_document()
        document.start(None, trigger=EX_NS["e1"], identifier=EX_NS["start1"])
        self.do_tests(document)

    def test_start_2(self):
        document = self.new_document()
        document.start(EX_NS["a1"], trigger=EX_NS["e1"], identifier=EX_NS["start2"])
        self.do_tests(document)

    def test_start_3(self):
        document = self.new_document()
        document.start(EX_NS["a1"], identifier=EX_NS["start3"])
        self.do_tests(document)

    def test_start_4(self):
        document = self.new_document()
        document.start(
            None, trigger=EX_NS["e1"], identifier=EX_NS["start4"], starter=EX_NS["a2"]
        )
        self.do_tests(document)

    def test_start_5(self):
        document = self.new_document()
        document.start(
            EX_NS["a1"],
            trigger=EX_NS["e1"],
            identifier=EX_NS["start5"],
            starter=EX_NS["a2"],
        )
        self.do_tests(document)

    def test_start_6(self):
        document = self.new_document()
        document.start(EX_NS["a1"], identifier=EX_NS["start6"], starter=EX_NS["a2"])
        self.do_tests(document)

    def test_start_7(self):
        document = self.new_document()
        document.start(
            EX_NS["a1"],
            identifier=EX_NS["start7"],
            starter=EX_NS["a2"],
            time=datetime.datetime.now(),
        )
        self.do_tests(document)

    def test_start_8(self):
        document = self.new_document()
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
        self.add_types(start)
        self.add_locations(start)
        self.add_labels(start)
        self.add_further_attributes(start)
        self.do_tests(document)

    def test_start_9(self):
        document = self.new_document()
        document.start(EX_NS["a1"], trigger=EX_NS["e1"])
        self.do_tests(document)

    def test_start_10(self):
        document = self.new_document()
        start = document.start(
            EX_NS["a1"], starter=EX_NS["a2"], time=datetime.datetime.now()
        )
        start.add_attributes(
            [
                (PROV_ROLE, "egg-cup"),
                (PROV_ROLE, "boiling-water"),
            ]
        )
        self.add_types(start)
        self.add_locations(start)
        self.add_labels(start)
        self.add_further_attributes(start)
        self.do_tests(document)

    # ENDS
    def test_end_1(self):
        document = self.new_document()
        document.end(None, trigger=EX_NS["e1"], identifier=EX_NS["end1"])
        self.do_tests(document)

    def test_end_2(self):
        document = self.new_document()
        document.end(EX_NS["a1"], trigger=EX_NS["e1"], identifier=EX_NS["end2"])
        self.do_tests(document)

    def test_end_3(self):
        document = self.new_document()
        document.end(EX_NS["a1"], identifier=EX_NS["end3"])
        self.do_tests(document)

    def test_end_4(self):
        document = self.new_document()
        document.end(
            None, trigger=EX_NS["e1"], identifier=EX_NS["end4"], ender=EX_NS["a2"]
        )
        self.do_tests(document)

    def test_end_5(self):
        document = self.new_document()
        document.end(
            EX_NS["a1"],
            trigger=EX_NS["e1"],
            identifier=EX_NS["end5"],
            ender=EX_NS["a2"],
        )
        self.do_tests(document)

    def test_end_6(self):
        document = self.new_document()
        document.end(EX_NS["a1"], identifier=EX_NS["end6"], ender=EX_NS["a2"])
        self.do_tests(document)

    def test_end_7(self):
        document = self.new_document()
        document.end(
            EX_NS["a1"],
            identifier=EX_NS["end7"],
            ender=EX_NS["a2"],
            time=datetime.datetime.now(),
        )
        self.do_tests(document)

    def test_end_8(self):
        document = self.new_document()
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
        self.add_types(end)
        self.add_locations(end)
        self.add_labels(end)
        self.add_further_attributes(end)
        self.do_tests(document)

    def test_end_9(self):
        document = self.new_document()
        document.end(EX_NS["a1"], trigger=EX_NS["e1"])
        self.do_tests(document)

    def test_end_10(self):
        document = self.new_document()
        end = document.end(EX_NS["a1"], ender=EX_NS["a2"], time=datetime.datetime.now())
        end.add_attributes(
            [
                (PROV_ROLE, "yolk"),
                (PROV_ROLE, "white"),
            ]
        )
        self.add_types(end)
        self.add_locations(end)
        self.add_labels(end)
        self.add_further_attributes(end)
        self.do_tests(document)

    # DERIVATIONS
    def test_derivation_1(self):
        document = self.new_document()
        document.derivation(None, usedEntity=EX_NS["e1"], identifier=EX_NS["der1"])
        self.do_tests(document)

    def test_derivation_2(self):
        document = self.new_document()
        document.derivation(EX_NS["e2"], usedEntity=None, identifier=EX_NS["der2"])
        self.do_tests(document)

    def test_derivation_3(self):
        document = self.new_document()
        document.derivation(
            EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der3"]
        )
        self.do_tests(document)

    def test_derivation_4(self):
        document = self.new_document()
        der = document.derivation(
            EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der4"]
        )
        self.add_label(der)
        self.do_tests(document)

    def test_derivation_5(self):
        document = self.new_document()
        document.derivation(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            identifier=EX_NS["der5"],
            activity=EX_NS["a"],
        )
        self.do_tests(document)

    def test_derivation_6(self):
        document = self.new_document()
        document.derivation(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            identifier=EX_NS["der6"],
            activity=EX_NS["a"],
            usage=EX_NS["u"],
        )
        self.do_tests(document)

    def test_derivation_7(self):
        document = self.new_document()
        document.derivation(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            identifier=EX_NS["der7"],
            activity=EX_NS["a"],
            usage=EX_NS["u"],
            generation=EX_NS["g"],
        )
        self.do_tests(document)

    def test_derivation_8(self):
        document = self.new_document()
        der = document.derivation(
            EX_NS["e2"], usedEntity=EX_NS["e1"], identifier=EX_NS["der8"]
        )
        self.add_label(der)
        self.add_types(der)
        self.add_further_attributes(der)
        self.do_tests(document)

    def test_derivation_9(self):
        document = self.new_document()
        der = document.derivation(EX_NS["e2"], usedEntity=None)
        self.add_types(der)
        self.do_tests(document)

    def test_derivation_10(self):
        document = self.new_document()
        document.derivation(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            activity=EX_NS["a"],
            usage=EX_NS["u"],
            generation=EX_NS["g"],
        )
        self.do_tests(document)

    def test_derivation_11(self):
        document = self.new_document()
        document.revision(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            identifier=EX_NS["rev1"],
            activity=EX_NS["a"],
            usage=EX_NS["u"],
            generation=EX_NS["g"],
        )
        self.do_tests(document)

    def test_derivation_12(self):
        document = self.new_document()
        document.quotation(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            identifier=EX_NS["quo1"],
            activity=EX_NS["a"],
            usage=EX_NS["u"],
            generation=EX_NS["g"],
        )
        self.do_tests(document)

    def test_derivation_13(self):
        document = self.new_document()
        document.primary_source(
            EX_NS["e2"],
            usedEntity=EX_NS["e1"],
            identifier=EX_NS["prim1"],
            activity=EX_NS["a"],
            usage=EX_NS["u"],
            generation=EX_NS["g"],
        )
        self.do_tests(document)

    # ASSOCIATIONS
    def test_association_1(self):
        document = self.new_document()
        document.association(EX_NS["a1"], identifier=EX_NS["assoc1"])
        self.do_tests(document)

    def test_association_2(self):
        document = self.new_document()
        document.association(None, agent=EX_NS["ag1"], identifier=EX_NS["assoc2"])
        self.do_tests(document)

    def test_association_3(self):
        document = self.new_document()
        document.association(
            EX_NS["a1"], agent=EX_NS["ag1"], identifier=EX_NS["assoc3"]
        )
        self.do_tests(document)

    def test_association_4(self):
        document = self.new_document()
        document.association(
            EX_NS["a1"],
            agent=EX_NS["ag1"],
            identifier=EX_NS["assoc4"],
            plan=EX_NS["plan1"],
        )
        self.do_tests(document)

    def test_association_5(self):
        document = self.new_document()
        document.association(EX_NS["a1"], agent=EX_NS["ag1"])
        self.do_tests(document)

    def test_association_6(self):
        document = self.new_document()
        assoc = document.association(
            EX_NS["a1"],
            agent=EX_NS["ag1"],
            identifier=EX_NS["assoc6"],
            plan=EX_NS["plan1"],
        )
        self.add_labels(assoc)
        self.do_tests(document)

    def test_association_7(self):
        document = self.new_document()
        assoc = document.association(
            EX_NS["a1"],
            agent=EX_NS["ag1"],
            identifier=EX_NS["assoc7"],
            plan=EX_NS["plan1"],
        )
        self.add_labels(assoc)
        self.add_types(assoc)
        self.do_tests(document)

    def test_association_8(self):
        document = self.new_document()
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
        self.do_tests(document)

    def test_association_9(self):
        document = self.new_document()
        assoc = document.association(
            EX_NS["a1"],
            agent=EX_NS["ag1"],
            identifier=EX_NS["assoc9"],
            plan=EX_NS["plan1"],
        )
        self.add_labels(assoc)
        self.add_types(assoc)
        self.add_further_attributes(assoc)
        self.do_tests(document)

    def test_association_10(self):
        document = self.new_document()
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
        self.do_tests(document)

    # ATTRIBUTIONS
    def test_attribution_1(self):
        document = self.new_document()
        document.attribution(EX_NS["e1"], None, identifier=EX_NS["attr1"])
        self.do_tests(document)

    def test_attribution_2(self):
        document = self.new_document()
        document.attribution(None, EX_NS["ag1"], identifier=EX_NS["attr2"])
        self.do_tests(document)

    def test_attribution_3(self):
        document = self.new_document()
        document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr3"])
        self.do_tests(document)

    def test_attribution_4(self):
        document = self.new_document()
        document.attribution(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr4"])
        self.do_tests(document)

    def test_attribution_5(self):
        document = self.new_document()
        document.attribution(EX_NS["e1"], EX_NS["ag1"])
        self.do_tests(document)

    def test_attribution_6(self):
        document = self.new_document()
        attr = document.attribution(
            EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr6"]
        )
        self.add_labels(attr)
        self.do_tests(document)

    def test_attribution_7(self):
        document = self.new_document()
        attr = document.attribution(
            EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr7"]
        )
        self.add_labels(attr)
        self.add_types(attr)
        self.do_tests(document)

    def test_attribution_8(self):
        document = self.new_document()
        attr = document.attribution(
            EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["attr8"]
        )
        self.add_labels(attr)
        self.add_types(attr)
        self.add_further_attributes(attr)
        self.do_tests(document)

    # DELEGATIONS
    def test_delegation_1(self):
        document = self.new_document()
        document.delegation(EX_NS["e1"], None, identifier=EX_NS["dele1"])
        self.do_tests(document)

    def test_delegation_2(self):
        document = self.new_document()
        document.delegation(None, EX_NS["ag1"], identifier=EX_NS["dele2"])
        self.do_tests(document)

    def test_delegation_3(self):
        document = self.new_document()
        document.delegation(EX_NS["e1"], EX_NS["ag1"], identifier=EX_NS["dele3"])
        self.do_tests(document)

    def test_delegation_4(self):
        document = self.new_document()
        document.delegation(
            EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele4"]
        )
        self.do_tests(document)

    def test_delegation_5(self):
        document = self.new_document()
        document.delegation(EX_NS["e1"], EX_NS["ag1"])
        self.do_tests(document)

    def test_delegation_6(self):
        document = self.new_document()
        dele = document.delegation(
            EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele6"]
        )
        self.add_labels(dele)
        self.do_tests(document)

    def test_delegation_7(self):
        document = self.new_document()
        dele = document.delegation(
            EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele7"]
        )
        self.add_labels(dele)
        self.add_types(dele)
        self.do_tests(document)

    def test_delegation_8(self):
        document = self.new_document()
        dele = document.delegation(
            EX_NS["e1"], EX_NS["ag1"], activity=EX_NS["a1"], identifier=EX_NS["dele8"]
        )
        self.add_labels(dele)
        self.add_types(dele)
        self.add_further_attributes(dele)
        self.do_tests(document)

    # COMMUNICATIONS
    def test_communication_1(self):
        document = self.new_document()
        document.communication(EX_NS["a2"], None, identifier=EX_NS["inf1"])
        self.do_tests(document)

    def test_communication_2(self):
        document = self.new_document()
        document.communication(None, EX_NS["a1"], identifier=EX_NS["inf2"])
        self.do_tests(document)

    def test_communication_3(self):
        document = self.new_document()
        document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf3"])
        self.do_tests(document)

    def test_communication_4(self):
        document = self.new_document()
        document.communication(EX_NS["a2"], EX_NS["a1"])
        self.do_tests(document)

    def test_communication_5(self):
        document = self.new_document()
        inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf5"])
        self.add_labels(inf)
        self.do_tests(document)

    def test_communication_6(self):
        document = self.new_document()
        inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf6"])
        self.add_labels(inf)
        self.add_types(inf)
        self.do_tests(document)

    def test_communication_7(self):
        document = self.new_document()
        inf = document.communication(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
        self.add_labels(inf)
        self.add_types(inf)
        self.add_further_attributes(inf)
        self.do_tests(document)

    # INFLUENCES
    def test_influence_1(self):
        document = self.new_document()
        document.influence(EX_NS["a2"], None, identifier=EX_NS["inf1"])
        self.do_tests(document)

    def test_influence_2(self):
        document = self.new_document()
        document.influence(None, EX_NS["a1"], identifier=EX_NS["inf2"])
        self.do_tests(document)

    def test_influence_3(self):
        document = self.new_document()
        document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf3"])
        self.do_tests(document)

    def test_influence_4(self):
        document = self.new_document()
        document.influence(EX_NS["a2"], EX_NS["a1"])
        self.do_tests(document)

    def test_influence_5(self):
        document = self.new_document()
        inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf5"])
        self.add_labels(inf)
        self.do_tests(document)

    def test_influence_6(self):
        document = self.new_document()
        inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf6"])
        self.add_labels(inf)
        self.add_types(inf)
        self.do_tests(document)

    def test_influence_7(self):
        document = self.new_document()
        inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
        self.add_labels(inf)
        self.add_types(inf)
        self.add_further_attributes(inf)
        self.do_tests(document)

    # OTHERS
    def test_alternate_1(self):
        document = self.new_document()
        document.alternate(EX_NS["e2"], EX_NS["e1"])
        self.do_tests(document)

    def test_specialization_1(self):
        document = self.new_document()
        document.specialization(EX_NS["e2"], EX_NS["e1"])
        self.do_tests(document)

    def test_mention_1(self):
        document = self.new_document()
        document.mention(EX_NS["e2"], EX_NS["e1"], None)
        self.do_tests(document)

    def test_mention_2(self):
        document = self.new_document()
        document.mention(EX_NS["e2"], EX_NS["e1"], EX_NS["b"])
        self.do_tests(document)

    def test_membership_1(self):
        document = self.new_document()
        document.membership(EX_NS["c"], EX_NS["e1"])
        self.do_tests(document)

    def test_membership_2(self):
        document = self.new_document()
        document.membership(EX_NS["c"], EX_NS["e1"])
        document.membership(EX_NS["c"], EX_NS["e2"])
        self.do_tests(document)

    def test_membership_3(self):
        document = self.new_document()
        document.membership(EX_NS["c"], EX_NS["e1"])
        document.membership(EX_NS["c"], EX_NS["e2"])
        document.membership(EX_NS["c"], EX_NS["e3"])
        self.do_tests(document)

    # SCRUFFY
    def test_scruffy_generation_1(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_generation_2(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        gen1.add_attributes([(EX_NS["tag2"], "hello-scruff-gen2")])
        gen2.add_attributes([(EX_NS["tag2"], "hi-scruff-gen2")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_invalidation_1(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_invalidation_2(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        inv1.add_attributes([(EX_NS["tag2"], "hello")])
        inv2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_usage_1(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_usage_2(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        use1.add_attributes([(EX_NS["tag2"], "hello")])
        use2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_start_1(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_start_2(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        start1.add_attributes([(EX_NS["tag2"], "hello")])
        start2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_start_3(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
            starter=EX_NS["a2s"],
        )
        start1.add_attributes([(EX_NS["tag2"], "hello")])
        start2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        document.activity(identifier=EX_NS["a2"])
        document.activity(identifier=EX_NS["a2s"])
        self.do_tests(document)

    def test_scruffy_start_4(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
            starter=EX_NS["a2s"],
        )
        start1.add_attributes([(EX_NS["tag2"], "hello")])
        start2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        document.activity(identifier=EX_NS["a1s"])
        document.activity(identifier=EX_NS["a2"])
        document.activity(identifier=EX_NS["a2s"])
        self.do_tests(document)

    def test_scruffy_end_1(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_end_2(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
        )
        end1.add_attributes([(EX_NS["tag2"], "hello")])
        end2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        self.do_tests(document)

    def test_scruffy_end_3(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
            ender=EX_NS["a2s"],
        )
        end1.add_attributes([(EX_NS["tag2"], "hello")])
        end2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        document.activity(identifier=EX_NS["a2"])
        document.activity(identifier=EX_NS["a2s"])
        self.do_tests(document)

    def test_scruffy_end_4(self):
        document = self.new_document()
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
            time=dateutil.parser.parse("2012-12-03T21:08:16.686Z"),
            ender=EX_NS["a2s"],
        )
        end1.add_attributes([(EX_NS["tag2"], "hello")])
        end2.add_attributes([(EX_NS["tag2"], "hi")])
        document.entity(identifier=EX_NS["e1"])
        document.activity(identifier=EX_NS["a1"])
        document.activity(identifier=EX_NS["a1s"])
        document.activity(identifier=EX_NS["a2"])
        document.activity(identifier=EX_NS["a2s"])
        self.do_tests(document)

    def test_bundle_1(self):
        document = self.new_document()

        bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
        bundle1.usage(
            activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"]
        )
        bundle1.entity(identifier=EX_NS["e1"])
        bundle1.activity(identifier=EX_NS["a1"])

        bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
        bundle2.usage(
            activity=EX_NS["aa1"], entity=EX_NS["ee1"], identifier=EX_NS["use2"]
        )
        bundle2.entity(identifier=EX_NS["ee1"])
        bundle2.activity(identifier=EX_NS["aa1"])

        document.add_bundle(bundle1)
        document.add_bundle(bundle2)

        self.do_tests(document)

    def test_bundle_2(self):
        document = self.new_document()

        bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
        bundle1.usage(
            activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"]
        )
        bundle1.entity(identifier=EX_NS["e1"])
        bundle1.activity(identifier=EX_NS["a1"])

        bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
        bundle2.usage(
            activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use2"]
        )
        bundle2.entity(identifier=EX_NS["e1"])
        bundle2.activity(identifier=EX_NS["a1"])

        document.add_bundle(bundle1)
        document.add_bundle(bundle2)

        self.do_tests(document)

    def test_bundle_3(self):
        document = self.new_document()

        bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
        bundle1.usage(
            activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"]
        )
        bundle1.entity(identifier=EX_NS["e1"])
        bundle1.activity(identifier=EX_NS["a1"])

        bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
        bundle2.usage(
            activity=EX_NS["aa1"], entity=EX_NS["ee1"], identifier=EX_NS["use2"]
        )
        bundle2.entity(identifier=EX_NS["ee1"])
        bundle2.activity(identifier=EX_NS["aa1"])

        document.add_bundle(bundle1)
        document.add_bundle(bundle2)

        self.do_tests(document)

    def test_bundle_4(self):
        document = self.new_document()

        bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
        bundle1.usage(
            activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"]
        )
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

        self.do_tests(document)

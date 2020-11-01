import unittest

from prov.model import *
from prov.dot import prov_to_dot
from prov.serializers import Registry
from prov.tests.examples import primer_example, primer_example_alternate


EX_NS = Namespace("ex", "http://example.org/")
EX2_NS = Namespace("ex2", "http://example2.org/")
EX_OTHER_NS = Namespace("other", "http://exceptions.example.org/")


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


class TestExtras(unittest.TestCase):
    def test_dot(self):
        # This is naive, since we can't programatically check the output is
        # correct
        document = ProvDocument()

        bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
        bundle1.usage(
            activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"]
        )
        bundle1.entity(identifier=EX_NS["e1"], other_attributes={PROV_ROLE: "sausage"})
        bundle1.activity(identifier=EX_NS["a1"])
        document.activity(EX_NS["a2"])

        bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
        bundle2.usage(
            activity=EX_NS["aa1"], entity=EX_NS["ee1"], identifier=EX_NS["use2"]
        )
        bundle2.entity(identifier=EX_NS["ee1"])
        bundle2.activity(identifier=EX_NS["aa1"])

        document.add_bundle(bundle1)
        document.add_bundle(bundle2)
        prov_to_dot(document)

    def test_extra_attributes(self):

        document = ProvDocument()

        inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
        add_labels(inf)
        add_types(inf)
        add_further_attributes(inf)

        self.assertEqual(
            len(inf.attributes), len(list(inf.formal_attributes) + inf.extra_attributes)
        )

    def test_serialize_to_path(self):
        document = ProvDocument()
        document.serialize("output.json")
        os.remove("output.json")

        document.serialize("http://netloc/outputmyprov/submit.php")

    def test_bundle_no_id(self):
        document = ProvDocument()

        def test():
            bundle = ProvBundle()
            document.add_bundle(bundle)

        self.assertRaises(ProvException, test)

    def test_use_set_time_helpers(self):
        dt = datetime.datetime.now()
        document1 = ProvDocument()
        document1.activity(EX_NS["a8"], startTime=dt, endTime=dt)

        document2 = ProvDocument()
        a = document2.activity(EX_NS["a8"])
        a.set_time(startTime=dt, endTime=dt)

        self.assertEqual(document1, document2)
        self.assertEqual(a.get_startTime(), dt)
        self.assertEqual(a.get_endTime(), dt)

    def test_bundle_add_garbage(self):
        document = ProvDocument()

        def test():
            document.add_bundle(document.entity(EX_NS["entity_trying_to_be_a_bundle"]))

        self.assertRaises(ProvException, test)

        def test():
            bundle = ProvBundle()
            document.add_bundle(bundle)

        self.assertRaises(ProvException, test)

    def test_bundle_equality_garbage(self):
        document = ProvBundle()
        self.assertNotEqual(document, 1)

    def test_bundle_is_bundle(self):
        document = ProvBundle()
        self.assertTrue(document.is_bundle())

    def test_bundle_get_record_by_id(self):
        document = ProvDocument()
        self.assertEqual(document.get_record(None), None)

        # record = document.entity(identifier=EX_NS['e1'])
        # self.assertEqual(document.get_record(EX_NS['e1']), record)
        #
        # bundle = document.bundle(EX_NS['b'])
        # self.assertEqual(bundle.get_record(EX_NS['e1']), record)

    def test_bundle_get_records(self):
        document = ProvDocument()

        document.entity(identifier=EX_NS["e1"])
        document.agent(identifier=EX_NS["e1"])
        self.assertEqual(len(list(document.get_records(ProvAgent))), 1)
        self.assertEqual(len(document.get_records()), 2)

    def test_bundle_name_clash(self):
        document = ProvDocument()

        def test():
            document.bundle(EX_NS["indistinct"])
            document.bundle(EX_NS["indistinct"])

        self.assertRaises(ProvException, test)

        document = ProvDocument()

        def test():
            document.bundle(EX_NS["indistinct"])
            bundle = ProvBundle(identifier=EX_NS["indistinct"])
            document.add_bundle(bundle)

        self.assertRaises(ProvException, test)

    def test_document_helper_methods(self):
        document = ProvDocument()
        self.assertFalse(document.is_bundle())
        self.assertFalse(document.has_bundles())
        document.bundle(EX_NS["b"])
        self.assertTrue(document.has_bundles())
        self.assertEqual("<ProvDocument>", str(document))

    def test_reading_and_writing_to_file_like_objects(self):
        """
        Tests reading and writing to and from file like objects.
        """
        # Create some random document.
        document = ProvDocument()
        document.entity(EX2_NS["test"])

        objects = [io.BytesIO, io.StringIO]

        Registry.load_serializers()
        formats = Registry.serializers.keys()

        for obj in objects:
            for format in formats:
                try:
                    buf = obj()
                    document.serialize(destination=buf, format=format)
                    buf.seek(0, 0)
                    new_document = ProvDocument.deserialize(source=buf, format=format)
                    self.assertEqual(document, new_document)
                except NotImplementedError:
                    # Some serializers might not implement serialize or
                    # deserialize method
                    pass  # and this is fine in the context of this test
                finally:
                    buf.close()

    # def test_document_unification(self):
    #     # TODO: Improve testing of this...
    #     document = ProvDocument()
    #     bundle = document.bundle(identifier=EX_NS['b'])
    #     e1 = bundle.entity(EX_NS['e'])
    #     e2 = bundle.entity(EX_NS['e'])
    #     unified = document.unified()
    #
    #     self.assertEqual(len(unified._bundles[0]._records), 1)

    def test_primer_alternate(self):
        g1 = primer_example()
        g2 = primer_example_alternate()
        self.assertEqual(g1, g2)


if __name__ == "__main__":
    unittest.main()

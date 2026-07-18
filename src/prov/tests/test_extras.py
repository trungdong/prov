import datetime
import io

import pytest

pytest.importorskip("pydot", reason="prov.dot requires the dot extra")

from prov.constants import (
    PROV_ROLE,
    XSD,
    XSD_ANYURI,
    XSD_DOUBLE,
    XSD_SHORT,
)
from prov.dot import prov_to_dot
from prov.identifier import Namespace
from prov.model import (
    Literal,
    ProvAgent,
    ProvBundle,
    ProvDocument,
    ProvException,
)
from prov.serializers import DoNotExist, Registry, get as get_serializer
from prov.serializers.provjson import ProvJSONSerializer
from prov.serializers.provn import ProvNSerializer
from prov.serializers.provrdf import ProvRDFSerializer
from prov.serializers.provxml import ProvXMLSerializer
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


def test_dot():
    # This is naive, since we can't programatically check the output is
    # correct
    document = ProvDocument()

    bundle1 = ProvBundle(identifier=EX_NS["bundle1"])
    bundle1.usage(activity=EX_NS["a1"], entity=EX_NS["e1"], identifier=EX_NS["use1"])
    bundle1.entity(identifier=EX_NS["e1"], other_attributes={PROV_ROLE: "sausage"})
    bundle1.activity(identifier=EX_NS["a1"])
    document.activity(EX_NS["a2"])

    bundle2 = ProvBundle(identifier=EX_NS["bundle2"])
    bundle2.usage(activity=EX_NS["aa1"], entity=EX_NS["ee1"], identifier=EX_NS["use2"])
    bundle2.entity(identifier=EX_NS["ee1"])
    bundle2.activity(identifier=EX_NS["aa1"])

    document.add_bundle(bundle1)
    document.add_bundle(bundle2)
    prov_to_dot(document)


def test_extra_attributes():
    document = ProvDocument()

    inf = document.influence(EX_NS["a2"], EX_NS["a1"], identifier=EX_NS["inf7"])
    add_labels(inf)
    add_types(inf)
    add_further_attributes(inf)

    assert len(inf.attributes) == len(
        list(inf.formal_attributes) + list(inf.extra_attributes)
    )


def test_serialize_to_path(tmp_path):
    document = ProvDocument()
    path = tmp_path / "output.json"
    document.serialize(str(path))
    assert path.exists()

    document.serialize("http://netloc/outputmyprov/submit.php")


def test_bundle_no_id():
    document = ProvDocument()

    def test():
        bundle = ProvBundle()
        document.add_bundle(bundle)

    with pytest.raises(ProvException):
        test()


def test_use_set_time_helpers():
    dt = datetime.datetime.now()
    document1 = ProvDocument()
    document1.activity(EX_NS["a8"], startTime=dt, endTime=dt)

    document2 = ProvDocument()
    a = document2.activity(EX_NS["a8"])
    a.set_time(startTime=dt, endTime=dt)

    assert document1 == document2
    assert a.get_startTime() == dt
    assert a.get_endTime() == dt


def test_bundle_add_garbage():
    document = ProvDocument()

    def test1():
        document.add_bundle(document.entity(EX_NS["entity_trying_to_be_a_bundle"]))

    with pytest.raises(ProvException):
        test1()

    def test2():
        bundle = ProvBundle()
        document.add_bundle(bundle)

    with pytest.raises(ProvException):
        test2()


def test_bundle_equality_garbage():
    document = ProvBundle()
    assert document != 1


def test_bundle_is_bundle():
    document = ProvBundle()
    assert document.is_bundle()


def test_bundle_get_record_by_id():
    document = ProvDocument()
    assert len(document.get_record("nonexistentid")) == 0

    record = document.entity(identifier=EX_NS["e1"])
    assert record == document.get_record(EX_NS["e1"])[0]


def test_bundle_get_records():
    document = ProvDocument()

    document.entity(identifier=EX_NS["e1"])
    document.agent(identifier=EX_NS["e1"])
    assert len(list(document.get_records(ProvAgent))) == 1
    assert len(document.get_records()) == 2


def test_bundle_name_clash():
    document = ProvDocument()

    def test1():
        document.bundle(EX_NS["indistinct"])
        document.bundle(EX_NS["indistinct"])

    with pytest.raises(ProvException):
        test1()

    document = ProvDocument()

    def test2():
        document.bundle(EX_NS["indistinct"])
        bundle = ProvBundle(identifier=EX_NS["indistinct"])
        document.add_bundle(bundle)

    with pytest.raises(ProvException):
        test2()


def test_document_helper_methods():
    document = ProvDocument()
    assert not document.is_bundle()
    assert not document.has_bundles()
    document.bundle(EX_NS["b"])
    assert document.has_bundles()
    assert str(document) == "<ProvDocument>"


def test_reading_and_writing_to_file_like_objects():
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
                assert document == new_document
            except NotImplementedError:
                # Some serializers might not implement serialize or
                # deserialize method
                pass  # and this is fine in the context of this test
            finally:
                buf.close()


def test_primer_alternate():
    g1 = primer_example()
    g2 = primer_example_alternate()
    assert g1 == g2


def test_get_serializer_for_unknown_format_chains_key_error():
    with pytest.raises(DoNotExist) as ctx:
        get_serializer("no-such-format")
    assert isinstance(ctx.value.__cause__, KeyError)
    assert "no-such-format" in str(ctx.value)


def test_get_serializer_returns_class_for_each_known_format():
    assert get_serializer("json") is ProvJSONSerializer
    assert get_serializer("rdf") is ProvRDFSerializer
    assert get_serializer("provn") is ProvNSerializer
    assert get_serializer("xml") is ProvXMLSerializer


def test_get_serializer_lazily_populates_registry():
    original = Registry.serializers
    Registry.serializers = None
    try:
        assert Registry.serializers is None
        get_serializer("json")
        assert Registry.serializers is not None
        assert set(Registry.serializers.keys()) == {"json", "rdf", "provn", "xml"}
    finally:
        Registry.serializers = original


def test_plot_without_matplotlib_raises_helpful_error():
    # Deliberately exercises matplotlib's *absence*: builtins.__import__ is
    # patched to fail for matplotlib imports, so this import must stay local
    # to the test rather than move to module scope.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("matplotlib"):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    document = ProvDocument()
    ex = document.add_namespace("ex", "https://example.org/")
    document.entity(ex["e1"])
    builtins.__import__ = fake_import
    try:
        with pytest.raises(ImportError) as ctx:
            document.plot()  # no filename -> interactive path -> needs matplotlib
        assert "prov[plot]" in str(ctx.value)
    finally:
        builtins.__import__ = real_import


def test_serialize_without_a_document_raises():
    """Covers ProvNSerializer.serialize()'s "no document" guard
    (docs/test-gap-checklist.md, T13 item under serializers/provn.py)."""
    serializer = ProvNSerializer(document=None)
    with pytest.raises(Exception) as ctx:
        serializer.serialize(io.StringIO())
    assert "No document to serialize" in str(ctx.value)

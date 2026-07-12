import contextlib
import difflib
import inspect
import io
import os
import warnings

import pytest
from lxml import etree

import prov.model as prov
from prov.constants import PROV
from prov.identifier import Namespace, QualifiedName
from prov.serializers.provxml import (
    ProvXMLException,
    ProvXMLSerializer,
    xml_qname_to_QualifiedName,
)
from prov.tests.conftest import roundtrip_document

EX_NS = ("ex", "http://example.com/ns/ex#")
EX_TR = ("tr", "http://example.com/ns/tr#")

# Most general way to get the path.
DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "xml"
)


def remove_empty_tags(tree):
    if tree.text is not None and tree.text.strip() == "":
        tree.text = None
    for elem in tree:
        if etree.iselement(elem):
            remove_empty_tags(elem)


def compare_xml(doc1, doc2):
    """
    Helper function to compare two XML files. It will parse both once again
    and write them in a canonical fashion.
    """
    with contextlib.suppress(AttributeError):
        doc1.seek(0, 0)
    with contextlib.suppress(AttributeError):
        doc2.seek(0, 0)

    obj1 = etree.parse(doc1)
    obj2 = etree.parse(doc2)

    # Remove comments from both.
    for c in obj1.getroot().xpath("//comment()"):
        p = c.getparent()
        p.remove(c)
    for c in obj2.getroot().xpath("//comment()"):
        p = c.getparent()
        p.remove(c)

    remove_empty_tags(obj1.getroot())
    remove_empty_tags(obj2.getroot())

    buf = io.BytesIO()
    obj1.write_c14n(buf)
    buf.seek(0, 0)
    str1 = buf.read().decode()
    str1 = [_i.strip() for _i in str1.splitlines() if _i.strip()]

    buf = io.BytesIO()
    obj2.write_c14n(buf)
    buf.seek(0, 0)
    str2 = buf.read().decode()
    str2 = [_i.strip() for _i in str2.splitlines() if _i.strip()]

    unified_diff = difflib.unified_diff(str1, str2)

    err_msg = "\n".join(unified_diff)
    if err_msg:
        msg = "Strings are not equal.\n"
        raise AssertionError(msg + err_msg)


def test_serialization_example_6():
    """
    Test the serialization of example 6 which is a simple entity
    description.
    """
    document = prov.ProvDocument()
    ex_ns = document.add_namespace(*EX_NS)
    document.add_namespace(*EX_TR)

    document.entity(
        "tr:WD-prov-dm-20111215",
        ((prov.PROV_TYPE, ex_ns["Document"]), ("ex:version", "2")),
    )

    with io.BytesIO() as actual:
        document.serialize(format="xml", destination=actual)
        compare_xml(os.path.join(DATA_PATH, "example_06.xml"), actual)


def test_serialization_example_7():
    """
    Test the serialization of example 7 which is a basic activity.
    """
    document = prov.ProvDocument()
    document.add_namespace(*EX_NS)

    document.activity(
        "ex:a1",
        "2011-11-16T16:05:00",
        "2011-11-16T16:06:00",
        [
            (prov.PROV_TYPE, prov.Literal("ex:edit", prov.XSD_QNAME)),
            ("ex:host", "server.example.org"),
        ],
    )

    with io.BytesIO() as actual:
        document.serialize(format="xml", destination=actual)
        compare_xml(os.path.join(DATA_PATH, "example_07.xml"), actual)


def test_serialization_example_8():
    """
    Test the serialization of example 8 which deals with generation.
    """
    document = prov.ProvDocument()
    document.add_namespace(*EX_NS)

    e1 = document.entity("ex:e1")
    a1 = document.activity("ex:a1")

    document.wasGeneratedBy(
        entity=e1,
        activity=a1,
        time="2001-10-26T21:32:52",
        other_attributes={"ex:port": "p1"},
    )

    e2 = document.entity("ex:e2")

    document.wasGeneratedBy(
        entity=e2,
        activity=a1,
        time="2001-10-26T10:00:00",
        other_attributes={"ex:port": "p2"},
    )

    with io.BytesIO() as actual:
        document.serialize(format="xml", destination=actual)
        compare_xml(os.path.join(DATA_PATH, "example_08.xml"), actual)


def test_deserialization_example_6():
    """
    Test the deserialization of example 6 which is a simple entity
    description.
    """
    actual_doc = prov.ProvDocument.deserialize(
        source=os.path.join(DATA_PATH, "example_06.xml"), format="xml"
    )

    expected_document = prov.ProvDocument()
    ex_ns = expected_document.add_namespace(*EX_NS)
    expected_document.add_namespace(*EX_TR)

    expected_document.entity(
        "tr:WD-prov-dm-20111215",
        ((prov.PROV_TYPE, ex_ns["Document"]), ("ex:version", "2")),
    )

    assert actual_doc == expected_document


def test_deserialization_example_7():
    """
    Test the deserialization of example 7 which is a simple activity
    description.
    """
    actual_doc = prov.ProvDocument.deserialize(
        source=os.path.join(DATA_PATH, "example_07.xml"), format="xml"
    )

    expected_document = prov.ProvDocument()
    ex_ns = Namespace(*EX_NS)
    expected_document.add_namespace(ex_ns)

    expected_document.activity(
        "ex:a1",
        "2011-11-16T16:05:00",
        "2011-11-16T16:06:00",
        [
            (prov.PROV_TYPE, QualifiedName(ex_ns, "edit")),
            ("ex:host", "server.example.org"),
        ],
    )

    assert actual_doc == expected_document


def test_deserialization_example_04_and_05():
    """
    Example 4 and 5 have a different type specification. They use an
    xsi:type as an attribute on an entity. This can be read but if
    written again it will become an XML child element. This is
    semantically identical but cannot be tested with a round trip.
    """
    # Example 4.
    xml_string = """
    <prov:document
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.com/ns/ex#"
        xmlns:tr="http://example.com/ns/tr#">

      <prov:entity prov:id="tr:WD-prov-dm-20111215" xsi:type="prov:Plan">
        <prov:type xsi:type="xsd:QName">ex:Workflow</prov:type>
      </prov:entity>

    </prov:document>
    """
    with io.StringIO() as xml:
        xml.write(xml_string)
        xml.seek(0, 0)
        actual_document = prov.ProvDocument.deserialize(source=xml, format="xml")

    expected_document = prov.ProvDocument()
    ex_ns = Namespace(*EX_NS)
    expected_document.add_namespace(ex_ns)
    expected_document.add_namespace(*EX_TR)

    # The xsi:type attribute is mapped to a proper PROV attribute.
    expected_document.entity(
        "tr:WD-prov-dm-20111215",
        (
            (prov.PROV_TYPE, QualifiedName(ex_ns, "Workflow")),
            (prov.PROV_TYPE, PROV["Plan"]),
        ),
    )

    assert actual_document == expected_document, "example_04"

    # Example 5.
    xml_string = """
    <prov:document
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xmlns:xsd="http://www.w3.org/2001/XMLSchema"
      xmlns:prov="http://www.w3.org/ns/prov#"
      xmlns:ex="http://example.com/ns/ex#"
      xmlns:tr="http://example.com/ns/tr#">

    <prov:entity prov:id="tr:WD-prov-dm-20111215" xsi:type="prov:Plan">
      <prov:type xsi:type="xsd:QName">ex:Workflow</prov:type>
      <prov:type xsi:type="xsd:QName">prov:Plan</prov:type> <!-- inferred -->
      <prov:type xsi:type="xsd:QName">prov:Entity</prov:type> <!-- inferred -->
    </prov:entity>

    </prov:document>
    """
    with io.StringIO() as xml:
        xml.write(xml_string)
        xml.seek(0, 0)
        actual_document = prov.ProvDocument.deserialize(source=xml, format="xml")

    expected_document = prov.ProvDocument()
    expected_document.add_namespace(*EX_NS)
    expected_document.add_namespace(*EX_TR)

    # The xsi:type attribute is mapped to a proper PROV attribute.
    expected_document.entity(
        "tr:WD-prov-dm-20111215",
        (
            (prov.PROV_TYPE, QualifiedName(ex_ns, "Workflow")),
            (prov.PROV_TYPE, PROV["Entity"]),
            (prov.PROV_TYPE, PROV["Plan"]),
        ),
    )

    assert actual_document == expected_document, "example_05"


def test_other_elements():
    """
    PROV XML uses the <prov:other> element to enable the storage of non
    PROV information in a PROV XML document. It will be ignored by this
    library a warning will be raised informing the user.
    """
    # This is example 42 from the PROV XML documentation.
    xml_string = """
    <prov:document
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.com/ns/ex#">

      <!-- prov statements go here -->

      <prov:other>
        <ex:foo>
          <ex:content>bar</ex:content>
        </ex:foo>
      </prov:other>

      <!-- more prov statements can go here -->

    </prov:document>
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        with io.StringIO() as xml:
            xml.write(xml_string)
            xml.seek(0, 0)
            doc = prov.ProvDocument.deserialize(source=xml, format="xml")

    assert len(w) == 1
    assert (
        "Document contains non-PROV information in <prov:other>. It will "
        "be ignored in this package." in str(w[0].message)
    )

    # This document contains nothing else.
    assert len(doc._records) == 0


def test_nested_default_namespace():
    """
    Tests that a default namespace that is defined in a lower level tag is
    written to a bundle.
    """
    filename = os.path.join(DATA_PATH, "nested_default_namespace.xml")
    doc = prov.ProvDocument.deserialize(source=filename, format="xml")

    ns = Namespace("", "http://example.org/0/")

    assert len(doc._records) == 1
    assert doc.get_default_namespace() == ns
    assert doc._records[0].identifier.namespace == ns
    assert doc._records[0].identifier.localpart == "e001"


def test_redefining_namespaces():
    """
    Test the behaviour when namespaces are redefined at the element level.
    """
    filename = os.path.join(DATA_PATH, "namespace_redefined_but_does_not_change.xml")
    doc = prov.ProvDocument.deserialize(source=filename, format="xml")
    # This has one record part of the original namespace.
    assert len(doc._records) == 1
    ns = Namespace("ex", "http://example.com/ns/ex#")
    assert doc._records[0].attributes[0][1].namespace == ns

    # This also has one record but now in a different namespace.
    filename = os.path.join(DATA_PATH, "namespace_redefined.xml")
    doc = prov.ProvDocument.deserialize(source=filename, format="xml")
    new_ns = doc._records[0].attributes[0][1].namespace
    assert new_ns != ns
    assert new_ns.uri == "http://example.com/ns/new_ex#"


def test_deserialization_with_prov_as_default_namespace():
    # https://github.com/trungdong/prov/issues/155
    xml_string = """<document xmlns="http://www.w3.org/ns/prov#"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:ex="https://example.org/">
      <entity prov:id="ex:e">
        <value xsi:type="xsd:int">1</value>
      </entity>
    </document>"""
    document = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    entity = next(iter(document.get_records(prov.ProvEntity)))
    # the <value> element is in the default (PROV) namespace:
    # it must parse as prov:value, not "None:value"
    values = list(entity.get_attribute(PROV["value"]))
    assert values == [1]
    # and the document must round-trip through XML unchanged
    round_tripped = prov.ProvDocument.deserialize(
        content=document.serialize(format="xml"), format="xml"
    )
    assert round_tripped == document


def test_deserialization_with_xsd_as_default_namespace():
    # An unprefixed xsi:type resolved against an XSD default namespace must
    # map to the canonical xsd namespace (with #); previously it produced a
    # corrupt datatype URI (http://www.w3.org/2001/XMLSchemaint).
    xml_string = """<prov:document xmlns="http://www.w3.org/2001/XMLSchema"
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:ex="https://example.org/">
      <prov:entity prov:id="ex:e">
        <prov:value xsi:type="int">1</prov:value>
      </prov:entity>
    </prov:document>"""
    document = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    entity = next(iter(document.get_records(prov.ProvEntity)))
    values = list(entity.get_attribute(PROV["value"]))
    assert values == [1]


# The following cover ProvXMLSerializer error/warning paths not reached by
# the round-trip fixtures (docs/test-gap-checklist.md, T13 item under
# serializers/provxml.py).


def test_serialize_without_a_document_raises():
    serializer = ProvXMLSerializer(document=None)
    with pytest.raises(ProvXMLException) as ctx:
        serializer.serialize(io.BytesIO())
    assert "No document to serialize" in str(ctx.value)


def test_non_prov_top_level_element_raises():
    xml_string = """<?xml version="1.0" encoding="UTF-8"?>
    <prov:document
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.com/ns/ex#">
      <ex:notAProvElement/>
    </prov:document>
    """
    with (
        pytest.raises(ProvXMLException) as ctx,
        io.StringIO(xml_string) as xml,
    ):
        prov.ProvDocument.deserialize(source=xml, format="xml")
    assert "Non PROV element discovered" in str(ctx.value)


def test_unrepresentable_sub_element_attribute_warns_and_is_ignored():
    # An attribute on a PROV-XML sub-element other than prov:ref,
    # xsi:type, or xml:lang cannot be represented in the internal data
    # model; it is dropped with a warning rather than raising.
    xml_string = """<?xml version="1.0" encoding="UTF-8"?>
    <prov:document
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.com/ns/ex#">
      <prov:entity prov:id="ex:e1">
        <ex:version xsi:type="xsd:string" custom="oops">2</ex:version>
      </prov:entity>
    </prov:document>
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with io.StringIO(xml_string) as xml:
            doc = prov.ProvDocument.deserialize(source=xml, format="xml")

    assert any(
        "not representable in the prov module's internal data model"
        in str(warning.message)
        for warning in w
    )
    e1 = doc.get_record("ex:e1")[0]
    assert list(e1.get_attribute("ex:version")) == ["2"]


def test_unrecognised_only_attribute_on_first_sub_element_raises():
    # #254 mode 1: a child whose only XML attribute is unrecognised used to
    # leak a raw UnboundLocalError when it was the record's first child.
    xml_string = """<?xml version="1.0" encoding="UTF-8"?>
    <prov:document
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.com/ns/ex#">
      <prov:entity prov:id="ex:e1">
        <ex:only ex:junk="x">value</ex:only>
      </prov:entity>
    </prov:document>
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with (
            pytest.raises(ProvXMLException) as ctx,
            io.StringIO(xml_string) as xml,
        ):
            prov.ProvDocument.deserialize(source=xml, format="xml")
    assert "no representable value" in str(ctx.value)


def test_unrecognised_only_attribute_after_sibling_raises_not_reuses_value():
    # #254 mode 2: with a previous sibling, the stale value used to be
    # silently reused ("world" lost, "hello" duplicated).
    xml_string = """<?xml version="1.0" encoding="UTF-8"?>
    <prov:document
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.com/ns/ex#">
      <prov:entity prov:id="ex:e1">
        <ex:first>hello</ex:first>
        <ex:second ex:junk="x">world</ex:second>
      </prov:entity>
    </prov:document>
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with (
            pytest.raises(ProvXMLException) as ctx,
            io.StringIO(xml_string) as xml,
        ):
            prov.ProvDocument.deserialize(source=xml, format="xml")
    assert "no representable value" in str(ctx.value)


def test_xml_qname_to_qualifiedname_without_colon_or_default_ns_raises():
    element = etree.fromstring(
        '<root xmlns:ex="http://example.com/ns/ex#"><child/></root>'
    )
    child = element[0]
    with pytest.raises(ProvXMLException) as ctx:
        xml_qname_to_QualifiedName(child, "noColonNoDefaultNs")
    assert "Could not create a valid QualifiedName" in str(ctx.value)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="#224: the XML serializer drops an attribute whose value is the "
    "empty string; it vanishes on the round trip (JSON and RDF preserve it). "
    "Regression guard from the Hypothesis property tests; remove when #224 is "
    "fixed in 3.0.",
)
def test_empty_string_attribute_survives_xml_roundtrip():
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.agent("ex:g0", {"ex:k0": ""})
    assert roundtrip_document(document, "xml") == document


# Scaffolding for a per-file XML round-trip glob, left disabled.
#
# Deserializing then re-serializing PROV-XML does not maintain XML
# equivalence (e.g. prov:entity elements with type prov:Plan become
# prov:plan elements), so no test function calls this helper.
# Re-enabling it is a possible future coverage chore (2.4.0 window /
# conformance phase), explicitly out of scope for the pytest-matrix
# migration -- see design doc §4 Decision 3
# (docs/superpowers/specs/2026-07-06-test-suite-redesign.md).


def _perform_round_trip(filename, force_types=False):
    document = prov.ProvDocument.deserialize(source=filename, format="xml")

    with io.BytesIO() as new_xml:
        document.serialize(format="xml", destination=new_xml, force_types=force_types)
        compare_xml(filename, new_xml)

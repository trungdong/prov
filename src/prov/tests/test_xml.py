import contextlib
import datetime
import difflib
import inspect
import io
import json
import os
import re
import sys
import warnings

import pytest
from lxml import etree

import prov.model as prov
from prov.constants import (
    PROV,
    PROV_ATTR_ACTIVITY,
    PROV_ATTR_ENTITY,
    PROV_ATTR_TIME,
    PROV_ENTITY,
    PROV_LABEL,
    PROV_TYPE,
    PROV_USAGE,
    XSD_STRING,
)
from prov.identifier import Namespace, QualifiedName
from prov.serializers.provxml import (
    ProvXMLException,
    ProvXMLSerializer,
    _escape_ncname_localpart,
    _unescape_ncname_localpart,
    xml_qname_to_QualifiedName,
)
from prov.tests import examples
from prov.tests.conftest import (
    add_ordered_namespaces,
    default_namespace,
    roundtrip_document,
)

EX_NS = ("ex", "http://example.com/ns/ex#")
EX_TR = ("tr", "http://example.com/ns/tr#")

# Most general way to get the path.
DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "xml"
)


def remove_empty_tags(tree) -> None:
    if tree.text is not None and tree.text.strip() == "":
        tree.text = None
    for elem in tree:
        if etree.iselement(elem):
            remove_empty_tags(elem)


def compare_xml(doc1, doc2) -> None:
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


def test_serialization_example_6() -> None:
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


def test_serialization_example_7() -> None:
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


def test_serialization_example_8() -> None:
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


def test_deserialization_example_6() -> None:
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


def test_deserialization_example_7() -> None:
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


def test_deserialization_example_04_and_05() -> None:
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


def test_other_elements() -> None:
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


def test_nested_default_namespace() -> None:
    """
    An `xmlns` declared on an inner element is not the document's default,
    so a bare name under it is rejected.
    """
    filename = os.path.join(DATA_PATH, "nested_default_namespace.xml")
    with pytest.raises(ProvXMLException, match=r"http://example\.org/0/") as caught:
        prov.ProvDocument.deserialize(source=filename, format="xml")
    assert "e001" in str(caught.value)


def test_xmlns_on_the_document_element_is_the_default_namespace() -> None:
    xml_string = """<prov:document xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns="http://example.org/0/">
      <prov:entity prov:id="e001"/>
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")

    assert doc.get_default_namespace() == default_namespace("http://example.org/0/")
    identifier = doc._records[0].identifier
    assert identifier is not None
    assert identifier.namespace.prefix == ""
    assert identifier.uri == "http://example.org/0/e001"


def test_xmlns_on_bundle_content_is_the_bundle_default_namespace() -> None:
    xml_string = """<prov:document xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.org/ex/" xmlns="http://example.org/0/">
      <prov:bundleContent prov:id="ex:b" xmlns="http://example.org/1/">
        <prov:entity prov:id="e001"/>
      </prov:bundleContent>
      <prov:bundleContent prov:id="ex:c">
        <prov:entity prov:id="e002"/>
      </prov:bundleContent>
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    first_bundle, second_bundle = doc.bundles

    assert doc.get_default_namespace() == default_namespace("http://example.org/0/")
    assert first_bundle.get_default_namespace() == default_namespace(
        "http://example.org/1/"
    )
    assert second_bundle.get_default_namespace() is None
    assert first_bundle.get_records()[0].identifier.uri == "http://example.org/1/e001"
    assert second_bundle.get_records()[0].identifier.uri == "http://example.org/0/e002"


def test_a_bundle_default_namespace_survives_a_round_trip() -> None:
    xml_string = """<prov:document xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.org/ex/" xmlns="http://example.org/0/">
      <prov:bundleContent prov:id="ex:b" xmlns="http://example.org/1/">
        <prov:entity prov:id="e001"/>
      </prov:bundleContent>
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    written = doc.serialize(format="xml")
    again = prov.ProvDocument.deserialize(content=written, format="xml")
    assert again == doc
    (bundle,) = again.bundles
    assert bundle.get_default_namespace() == default_namespace("http://example.org/1/")
    assert bundle.get_records()[0].identifier.uri == "http://example.org/1/e001"


@pytest.mark.parametrize("bundle_first", [True, False], ids=["before", "after"])
def test_a_prefix_declared_on_bundle_content_is_the_bundles_own(
    bundle_first: bool,
) -> None:
    bundle_xml = """<prov:bundleContent prov:id="b" xmlns:ex="http://example.org/two/">
        <prov:entity prov:id="ex:a"/>
      </prov:bundleContent>"""
    entity_xml = '<prov:entity prov:id="ex:d"/>'
    body = bundle_xml + entity_xml if bundle_first else entity_xml + bundle_xml
    xml_string = f"""<prov:document xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.org/one/" xmlns="http://example.org/0/">
      {body}
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (bundle,) = doc.bundles

    assert {ns.prefix: ns.uri for ns in doc.get_registered_namespaces()} == {
        "ex": "http://example.org/one/"
    }
    assert {ns.prefix: ns.uri for ns in bundle.get_registered_namespaces()} == {
        "ex": "http://example.org/two/"
    }
    assert bundle.get_records()[0].identifier.uri == "http://example.org/two/a"


def test_built_in_prefixes_on_bundle_content_are_not_the_bundles_own() -> None:
    xml_string = """<prov:document xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.org/ex/">
      <prov:bundleContent prov:id="ex:b" xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <prov:entity prov:id="ex:e"/>
      </prov:bundleContent>
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (bundle,) = doc.bundles

    assert list(bundle.get_registered_namespaces()) == []


def test_a_bundle_id_under_a_prefix_of_its_own_stays_off_the_document() -> None:
    xml_string = """<prov:document xmlns:prov="http://www.w3.org/ns/prov#">
      <prov:bundleContent prov:id="zz:b" xmlns:zz="http://zz.example/">
        <prov:entity prov:id="zz:a"/>
      </prov:bundleContent>
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (bundle,) = doc.bundles

    assert list(doc.get_registered_namespaces()) == []
    assert [ns.prefix for ns in bundle.get_registered_namespaces()] == ["zz"]
    assert bundle.identifier is not None
    assert bundle.identifier.uri == "http://zz.example/b"
    for fmt in ("provn", "json", "xml"):
        assert (
            prov.ProvDocument.deserialize(content=doc.serialize(format=fmt), format=fmt)
            == doc
        )


def test_a_prefix_redeclared_inside_bundle_content_does_not_shadow_the_document() -> (
    None
):
    xml_string = """<prov:document xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.org/one/">
      <prov:bundleContent prov:id="ex:b">
        <prov:entity prov:id="ex:a"/>
        <prov:entity prov:id="ex:c" xmlns:ex="http://example.org/two/"/>
      </prov:bundleContent>
    </prov:document>"""
    doc = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (bundle,) = doc.bundles
    first, second = (r.identifier for r in bundle.get_records())

    assert first.uri == "http://example.org/one/a"
    assert second.uri == "http://example.org/two/c"
    assert second.namespace.prefix == "ex_1"
    assert [ns.prefix for ns in bundle.get_registered_namespaces()] == ["ex_1"]
    assert [ns.prefix for ns in doc.get_registered_namespaces()] == ["ex"]


def test_redefining_namespaces() -> None:
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


def test_deserialization_with_prov_as_default_namespace() -> None:
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


def test_deserialization_with_xsd_as_default_namespace() -> None:
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
# the round-trip fixtures (planning/test-gap-checklist.md, T13 item under
# serializers/provxml.py).


def test_non_prov_top_level_element_raises() -> None:
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


def test_unrepresentable_sub_element_attribute_warns_and_is_ignored() -> None:
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


def test_unrecognised_only_attribute_on_first_sub_element_raises() -> None:
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


def test_unrecognised_only_attribute_after_sibling_raises_not_reuses_value() -> None:
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


def test_xml_qname_to_qualifiedname_without_colon_or_default_ns_raises() -> None:
    element = etree.fromstring(
        '<root xmlns:ex="http://example.com/ns/ex#"><child/></root>'
    )
    child = element[0]
    with pytest.raises(ProvXMLException) as ctx:
        xml_qname_to_QualifiedName(child, "noColonNoDefaultNs")
    assert "Could not create a valid QualifiedName" in str(ctx.value)


@pytest.mark.parametrize(
    "attributes",
    [
        pytest.param({"ex:k0": ""}, id="plain-attribute"),
        pytest.param({"prov:label": ""}, id="prov-label"),
        pytest.param({"prov:value": ""}, id="prov-value"),
        pytest.param({"ex:lit": prov.Literal("", langtag="en")}, id="literal-langtag"),
    ],
)
def test_empty_string_value_shapes_survive_xml_roundtrip(attributes) -> None:
    # #224: an empty-string value must not vanish on the round trip,
    # regardless of which XML shape it takes (plain text, prov:label,
    # prov:value with an inferred xsd:string type, or a language-tagged
    # Literal). The fix must not special-case just one of these paths.
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.agent("ex:g0", attributes)
    assert roundtrip_document(document, "xml") == document


def test_absent_optional_formal_attribute_stays_none_after_xml_roundtrip() -> None:
    # Regression guard for #224: a genuinely *absent* optional formal
    # attribute (no XML element for it at all) must still deserialize as
    # None, not be coalesced into the empty string.
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1")
    document.activity("ex:a1")
    document.wasGeneratedBy("ex:e1", "ex:a1")
    roundtripped = roundtrip_document(document, "xml")
    assert roundtripped == document
    (generation,) = [
        rec
        for rec in roundtripped.get_records()
        if rec.get_type() == PROV["Generation"]
    ]
    formal = dict(generation.formal_attributes)
    assert formal[PROV["time"]] is None


@pytest.mark.parametrize(
    "local_part",
    [
        pytest.param("weird'key", id="apostrophe"),
        pytest.param("has(parens)", id="parens"),
        pytest.param("has,comma", id="comma"),
        pytest.param("has:colon", id="colon"),
        pytest.param("has;semi", id="semicolon"),
        pytest.param("has[bracket]", id="brackets"),
        pytest.param("has=equals", id="equals"),
        pytest.param("0leadingdigit", id="leading-digit"),
    ],
)
def test_ncname_illegal_attribute_names_roundtrip_xml(local_part) -> None:
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {f"ex:{local_part}": "value"})
    assert roundtrip_document(document, "xml") == document


def test_valid_ncname_attribute_name_serializes_byte_identically() -> None:
    # Names that are already legal NCNames must not gain any _xHHHH_
    # escaping -- existing output stays byte-identical (#289).
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {"ex:plainKey0": "value"})
    with io.BytesIO() as stream:
        document.serialize(destination=stream, format="xml")
        xml_text = stream.getvalue().decode("utf-8")
    assert "_x" not in xml_text
    assert "<ex:plainKey0>" in xml_text


_ORDER_EX = Namespace("ex", "http://example.org/")
_ORDER_E2 = Namespace("e2", "http://example.org/")
_ORDER_PV = Namespace("pv", PROV.uri)
_ORDER_TIME = datetime.datetime(2026, 1, 2, 3, 4, 5)


@pytest.mark.parametrize(
    ("element", "attributes", "expected"),
    [
        pytest.param(
            PROV_ENTITY,
            [
                (_ORDER_EX["z"], 2),
                (PROV_TYPE, "b"),
                (_ORDER_E2["a"], 1),
                (PROV_LABEL, "y"),
                (_ORDER_EX["a"], 3),
                (PROV_TYPE, "a"),
                (PROV_LABEL, "x"),
                (_ORDER_EX["a"], 1),
            ],
            [
                ("prov:label", "x"),
                ("prov:label", "y"),
                ("prov:type", "a"),
                ("prov:type", "b"),
                ("e2:a", 1),
                ("ex:a", 1),
                ("ex:a", 3),
                ("ex:z", 2),
            ],
            id="ranked-then-unranked-by-name-then-value",
        ),
        pytest.param(
            PROV_ENTITY,
            [(_ORDER_PV["type"], "a"), (_ORDER_EX["b"], 1), (PROV_LABEL, "x")],
            [("prov:label", "x"), ("pv:type", "a"), ("ex:b", 1)],
            id="a-prov-name-under-another-prefix-ranks-as-prov",
        ),
        pytest.param(
            PROV_USAGE,
            [
                (PROV_LABEL, "x"),
                (PROV_ATTR_TIME, _ORDER_TIME),
                (PROV_ATTR_ENTITY, _ORDER_EX["e"]),
                (PROV_ATTR_ACTIVITY, _ORDER_EX["a"]),
            ],
            [
                ("prov:activity", _ORDER_EX["a"]),
                ("prov:entity", _ORDER_EX["e"]),
                ("prov:time", _ORDER_TIME),
                ("prov:label", "x"),
            ],
            id="formal-attributes-lead",
        ),
        pytest.param(
            PROV_ENTITY,
            [
                (_ORDER_EX["v"], prov.Literal("b", XSD_STRING)),
                (_ORDER_EX["v"], "a"),
            ],
            [("ex:v", "a"), ("ex:v", prov.Literal("b", XSD_STRING))],
            id="a-literal-sorts-by-its-value-text",
        ),
        pytest.param(
            PROV_ENTITY,
            [(_ORDER_EX["v"], 1), (_ORDER_EX["v"], "1")],
            [("ex:v", 1), ("ex:v", "1")],
            id="equal-keys-keep-input-order",
        ),
    ],
)
def test_sorted_attributes_order(
    element: QualifiedName,
    attributes: list[prov.NameValuePair],
    expected: list[tuple[str, object]],
) -> None:
    # Formal attributes first, then label, location, role, type and value,
    # then the rest by name and value text; equal keys keep input order.
    result = prov.sorted_attributes(element, attributes)
    assert [(str(name), value) for name, value in result] == expected


def test_literal_ncname_escape_shaped_attribute_name_roundtrips_xml() -> None:
    # A literal attribute name that itself already looks like an _xHHHH_
    # escape sequence must still round-trip: the write side self-escapes
    # its introducing underscore (as _x005F_) so the read side's inverse
    # transform recovers the original name exactly (#289).
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {"ex:_x0041_": "value"})
    assert roundtrip_document(document, "xml") == document


@pytest.mark.parametrize(
    "local",
    [
        pytest.param("plainKey0", id="plain"),
        pytest.param("weird'key", id="apostrophe"),
        pytest.param("0leadingdigit", id="leading-digit"),
        pytest.param("a(b)c,d;e:f[g]h=i", id="metacharacters"),
        pytest.param("_x0041_", id="escape-lookalike"),
        pytest.param("_", id="bare-underscore"),
        pytest.param("café", id="legal-non-ascii-letter"),
        pytest.param("a_x005F_x0041_b", id="embedded-escape-lookalike"),
        pytest.param("", id="empty"),
        # Boundary cases from the XML 1.0 5th-edition NameStartChar
        # productions (#289's PUA-vs-CJK-compatibility bug: the range
        # meant to be #xF900-#xFDCF briefly started at U+8C48 instead,
        # which wrongly treated U+D800-U+F8FF -- including the whole
        # Private Use Area -- as legal).
        pytest.param("attr\ue000", id="pua-start-illegal"),
        pytest.param("attr\uf8ff", id="pua-end-illegal"),
        pytest.param("attr\uf900", id="cjk-compat-start-legal"),
        pytest.param("attr\U0001f600", id="astral-legal"),
        pytest.param("attr\U0010ffff", id="astral-above-legal-range"),
    ],
)
def test_escape_unescape_ncname_localpart_is_inverse(local) -> None:
    escaped = _escape_ncname_localpart(local)
    # The pair must be an exact inverse ...
    assert _unescape_ncname_localpart(escaped) == local
    # ... AND, for any non-empty input, the escaped form must actually be an
    # XML name lxml accepts as an element tag. This second assertion is what
    # would have caught the PUA bug above: the escape function trusted a
    # wrong "legal" verdict from _NCNAME_START_RE/_NCNAME_CHAR_RE and left
    # the PUA character unescaped, which the first assertion alone can't
    # detect (unescaping unescaped text is a no-op, so it still looks like a
    # valid inverse). An empty local part has nothing to escape and stays
    # empty either way -- that it cannot form a tag name is a separate,
    # pre-existing "no name at all" limitation, not an NCName-legality bug,
    # so it is exempted from this assertion.
    if local:
        etree.Element(escaped)


# Hardening against XXE / entity expansion (#273).
#
# Three distinct vectors were checked against unmodified pre-fix HEAD
# (e64b794) before writing these tests, and only one reproduces with this
# project's locked lxml (6.1.1):
#
# - External entity, pristine global default parser: does NOT reproduce
#   pre-fix. lxml >= 5.0 changed XMLParser's own default `resolve_entities`
#   from `True` to `'internal'` (no external file/URL access), so pre-fix
#   the SYSTEM entity is left undefined and lxml raises XMLSyntaxError
#   before any file is touched -- but that safety is an accident of the
#   installed lxml version, not anything provxml.py configures: `lxml
#   >=3.3.5` (this package's floor) still admits lxml < 5.0, where the
#   default was `True` and this exact payload leaks the file's contents
#   (verified separately against a parser built with
#   `resolve_entities=True`, matching that old default). Post-fix, the
#   explicit `resolve_entities=False` used by `_XML_PARSER` changes the
#   observable behaviour again: rather than raising, the reference is left
#   unresolved and the attribute value comes back as an empty string --
#   still never containing the file's contents. test_external_entity_
#   does_not_leak_file_contents below pins that actual hardened behaviour.
# - Billion-laughs / entity amplification: does NOT reproduce on any
#   supported lxml, pre- or post-fix. libxml2 itself has carried a hard cap
#   on entity amplification for a long time, independent of any lxml-level
#   flag, so this was never really exploitable through this library
#   specifically. test_billion_laughs_does_not_expand pins libxml2's own
#   protection as a regression guard, not as evidence of a prov-side fix.
# - Global default parser tampering: DOES reproduce, today, through prov's
#   public API. Both `etree.parse` call sites in provxml.py pass no
#   `parser=` argument, so they silently inherit whatever
#   `lxml.etree.set_default_parser()` last installed process-wide -- which
#   any other library sharing the interpreter is free to do, and prov is
#   embedded in other applications. Measured directly:
#
#     pristine global default              -> XMLSyntaxError (safe)
#     after set_default_parser(permissive) -> parsed, file contents leaked
#
#   test_deserialize_ignores_tampered_default_parser exercises exactly this
#   and is the one test in this group that fails against unhardened
#   provxml.py and passes once both `etree.parse` sites pass the explicit
#   `_XML_PARSER`.


@pytest.fixture
def restore_default_xml_parser():
    """Snapshot and restore lxml's process-global default parser.

    Deliberately scoped to the one test that reconfigures the global
    default via ``etree.set_default_parser`` -- leaving a permissive parser
    installed globally would silently weaken entity handling for every
    other test (and every other consumer of lxml) running after it in the
    same process.
    """
    original_parser = etree.get_default_parser()
    try:
        yield
    finally:
        etree.set_default_parser(original_parser)


def _xxe_document(secret_path) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE prov:document [
  <!ENTITY xxe SYSTEM "file://{secret_path}">
]>
<prov:document
    xmlns:prov="http://www.w3.org/ns/prov#"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:ex="http://example.com/ns/ex#">
  <prov:entity prov:id="ex:e1">
    <prov:type xsi:type="xsd:string">&xxe;</prov:type>
  </prov:entity>
</prov:document>
"""


_BILLION_LAUGHS_DOCUMENT = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE prov:document [
 <!ENTITY lol "lol">
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
 <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
 <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
 <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
 <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
 <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
 <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<prov:document
    xmlns:prov="http://www.w3.org/ns/prov#"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:ex="http://example.com/ns/ex#">
  <prov:entity prov:id="ex:e1">
    <prov:type xsi:type="xsd:string">&lol9;</prov:type>
  </prov:entity>
</prov:document>
"""


def test_external_entity_does_not_leak_file_contents(tmp_path) -> None:
    # Actual hardened behaviour observed with `_XML_PARSER`
    # (resolve_entities=False): the document deserializes without raising,
    # but the SYSTEM entity reference is left unresolved rather than
    # expanded, so the attribute that referenced it comes back empty. The
    # file's contents never appear anywhere in the parsed document. This is
    # a behaviour change from pre-fix on this project's locked lxml (6.1.1),
    # where the same payload raised XMLSyntaxError instead (lxml >= 5.0's
    # own `resolve_entities='internal'` default) -- both are safe, but the
    # explicit `False` here is what also protects lxml < 5.0 and a tampered
    # global default parser (see test_deserialize_ignores_tampered_default_
    # parser below), which lxml's own changing defaults do not.
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("TOPSECRET123")

    xml_string = _xxe_document(secret_path.as_posix())
    document = prov.ProvDocument.deserialize(content=xml_string, format="xml")

    assert "TOPSECRET123" not in document.get_provn()
    entity = next(iter(document.get_records(prov.ProvEntity)))
    values = list(entity.get_attribute(PROV["type"]))
    assert values == [""]


def test_billion_laughs_does_not_expand() -> None:
    # Guards against unbounded entity amplification. This is libxml2's own
    # long-standing hard-coded amplification cap doing the work, not
    # anything provxml.py configures -- kept here as a regression guard in
    # case that upstream protection is ever weakened (e.g. via a future
    # `huge_tree=True`, which this module deliberately never sets).
    with pytest.raises(etree.XMLSyntaxError):
        prov.ProvDocument.deserialize(content=_BILLION_LAUGHS_DOCUMENT, format="xml")


def test_deserialize_ignores_tampered_default_parser(
    tmp_path, restore_default_xml_parser
) -> None:
    # The reproducible vector: provxml.py's own `etree.parse` calls pass an
    # explicit, hardened parser, so they are unaffected even when some other
    # code in the same process has repointed lxml's *global* default parser
    # (via `etree.set_default_parser`) to something permissive -- which is
    # exactly what happens, pre-fix, on today's locked lxml (6.1.1):
    # tampering the global default is enough to make the external entity in
    # _xxe_document resolve and leak the file's contents through
    # ProvDocument.deserialize.
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("TOPSECRET123")

    etree.set_default_parser(etree.XMLParser(resolve_entities=True, no_network=True))

    xml_string = _xxe_document(secret_path.as_posix())
    document = prov.ProvDocument.deserialize(content=xml_string, format="xml")

    entity = next(iter(document.get_records(prov.ProvEntity)))
    values = list(entity.get_attribute(PROV["type"]))
    assert "TOPSECRET123" not in str(values)
    assert "TOPSECRET123" not in document.get_provn()


def test_bundle_namespace_order_follows_registration_in_xml() -> None:
    # #337: bundle namespaces are declared in registration order.
    document = prov.ProvDocument()
    document.set_default_namespace("http://example.org/")
    prefixes = add_ordered_namespaces(document.bundle("b1"))

    xml_bytes = document.serialize(format="xml").encode()

    declared = re.findall(rb"xmlns:(ex\d)=", xml_bytes)
    assert [p.decode() for p in declared] == prefixes


# #338: force_types coverage.

XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
PROV_ID = "{http://www.w3.org/ns/prov#}id"
PROV_REF = "{http://www.w3.org/ns/prov#}ref"
FORCE_TYPES_NS = {"ex": "http://example.org/", "prov": "http://www.w3.org/ns/prov#"}


@pytest.mark.parametrize("force_types", [True, False])
def test_force_types_controls_xsi_type_on_non_prov_attributes(force_types) -> None:
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity(
        "ex:e1",
        {
            "ex:text": "plain",
            "ex:count": 7,
            "ex:when": datetime.datetime(2026, 9, 10, 12, 0, 0),
            "prov:type": "a type",
        },
    )

    root = etree.fromstring(
        document.serialize(format="xml", force_types=force_types).encode()
    )

    def xsi_type(path):
        return root.find(path, FORCE_TYPES_NS).get(XSI_TYPE)

    assert xsi_type(".//ex:text") == ("xsd:string" if force_types else None)
    assert xsi_type(".//ex:count") == "xsd:int"
    assert xsi_type(".//ex:when") == "xsd:dateTime"
    assert xsi_type(".//prov:type") == "xsd:string"


def _xsi_type_of(parent: etree._Element, path: str) -> str | None:
    element = parent.find(path, FORCE_TYPES_NS)
    assert element is not None
    return element.get(XSI_TYPE)


@pytest.mark.parametrize(
    ("declared", "prefix"), [(None, "dn"), ("d", "d")], ids=["minted", "reused"]
)
def test_a_default_namespace_name_is_written_as_a_qname(
    declared: str | None, prefix: str
) -> None:
    # a bare local part is a QName under the element's xmlns; one with a colon
    # takes a prefix bound to the IRI, declared on the element when none is in
    # scope, in every position a name is written, as the PROV-JSON writer does
    # (#570, #677)
    document = prov.ProvDocument()
    document.set_default_namespace("http://d.example/")
    document.add_namespace("ex", "http://example.org/")
    if declared is not None:
        document.add_namespace(declared, "http://d.example/")
    default = document.get_default_namespace()
    assert default is not None
    document.entity(
        "ex:e",
        {
            "ex:t": prov.Literal("1", default["t"]),
            "ex:c": prov.Literal("2", default["a:b"]),
            "ex:q": default["a:b"],
            "ex:p": default["e"],
        },
    )
    document.entity(default["a:b"])
    document.entity(default["e"])
    document.used("ex:a", default["a:b"])
    document.bundle(default["c:e"])
    bundle = document.bundle("ex:b")
    bundle.set_default_namespace("http://other.example/")
    other = bundle.get_default_namespace()
    assert other is not None
    bundle.entity("ex:f", {"ex:c": prov.Literal("3", other["c:d"])})

    xml = document.serialize(format="xml")
    root = etree.fromstring(xml.encode())
    assert root.nsmap[prefix] == "http://d.example/"
    assert _xsi_type_of(root, "prov:entity/ex:t") == "t"
    assert _xsi_type_of(root, "prov:entity/ex:c") == f"{prefix}:a:b"
    assert [e.get(PROV_ID) for e in root.findall("prov:entity", FORCE_TYPES_NS)] == [
        "ex:e",
        f"{prefix}:a:b",
        "e",
    ]
    assert root.findtext("prov:entity/ex:q", namespaces=FORCE_TYPES_NS) == (
        f"{prefix}:a:b"
    )
    assert root.findtext("prov:entity/ex:p", namespaces=FORCE_TYPES_NS) == "e"
    used = root.find("prov:used/prov:entity", FORCE_TYPES_NS)
    assert used is not None and used.get(PROV_REF) == f"{prefix}:a:b"
    bundles = root.findall("prov:bundleContent", FORCE_TYPES_NS)
    assert [b.get(PROV_ID) for b in bundles] == [f"{prefix}:c:e", "ex:b"]
    content = bundles[1]
    assert _xsi_type_of(content, "prov:entity/ex:c") == "dn:c:d"
    assert content.nsmap["dn"] == "http://other.example/"
    assert prov.ProvDocument.deserialize(content=xml, format="xml") == document


_XML_NAMESPACES = (
    'xmlns:prov="http://www.w3.org/ns/prov#" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
    'xmlns:ex="http://example.org/"'
)


def _prov_xml(body: str, default: bool) -> str:
    """A document whose root is line 1 and whose body starts at line 2."""
    xmlns = ' xmlns="http://d.example/"' if default else ""
    return f"<prov:document {_XML_NAMESPACES}{xmlns}>\n{body}\n</prov:document>"


def _not_declared(prefix: str) -> str:
    return f"its prefix {prefix!r} is not declared"


_NO_PREFIX = "it has no prefix and no default namespace is declared"
_ENTITY_WITH = '<prov:entity prov:id="ex:e">{}</prov:entity>'
_USED_WITH = "<prov:used>{}</prov:used>"
_AT_ENTITY = "line 2, <prov:entity> 'ex:e': "
_AT_USED = "line 2, <prov:used> with no prov:id: "

# Each row: the body, where the message starts, the text rejected and why.
_REJECTED_UNDER_BOTH = {
    "record id": (
        '<prov:entity prov:id="zz:x"/>',
        "line 2, <prov:entity> 'zz:x': ",
        "zz:x",
        _not_declared("zz"),
    ),
    "bundle id": (
        '<prov:bundleContent prov:id="zz:x"/>',
        "line 2, <prov:bundleContent> 'zz:x': ",
        "zz:x",
        _not_declared("zz"),
    ),
    "prov:ref": (
        _USED_WITH.format('<prov:entity prov:ref="zz:x"/>'),
        _AT_USED,
        "zz:x",
        _not_declared("zz"),
    ),
    "xsd:QName text": (
        _ENTITY_WITH.format('<ex:k xsi:type="xsd:QName">zz:x</ex:k>'),
        _AT_ENTITY,
        "zz:x",
        _not_declared("zz"),
    ),
    "attribute xsi:type": (
        _ENTITY_WITH.format('<ex:k xsi:type="zz:t">v</ex:k>'),
        _AT_ENTITY,
        "zz:t",
        _not_declared("zz"),
    ),
    "record xsi:type": (
        '<prov:entity prov:id="ex:e" xsi:type="zz:t"/>',
        _AT_ENTITY,
        "zz:t",
        _not_declared("zz"),
    ),
    "reference text": (
        _USED_WITH.format("<prov:entity>zz:x</prov:entity>"),
        _AT_USED,
        "zz:x",
        _not_declared("zz"),
    ),
    "reference text, full IRI": (
        _USED_WITH.format("<prov:entity>http://example.org/e1</prov:entity>"),
        _AT_USED,
        "http://example.org/e1",
        _not_declared("http"),
    ),
    "3.2.3 bare id": (
        '<prov:entity prov:id="a:b"/>',
        "line 2, <prov:entity> 'a:b': ",
        "a:b",
        _not_declared("a"),
    ),
    "sibling, B before A": (
        '<prov:entity prov:id="a:e2"/>\n'
        '<prov:entity xmlns:a="http://a.example/" prov:id="a:e1"/>',
        "line 2, <prov:entity> 'a:e2': ",
        "a:e2",
        _not_declared("a"),
    ),
}
_REJECTED_WITH_NO_DEFAULT = {
    "empty prefix": (
        '<prov:entity prov:id=":x"/>',
        "line 2, <prov:entity> ':x': ",
        ":x",
        _not_declared(""),
    ),
    "no colon, record id": (
        '<prov:entity prov:id="e1"/>',
        "line 2, <prov:entity> 'e1': ",
        "e1",
        _NO_PREFIX,
    ),
    "no colon, reference text": (
        _USED_WITH.format("<prov:entity>e1</prov:entity>"),
        _AT_USED,
        "e1",
        _NO_PREFIX,
    ),
    "attribute element in no namespace": (
        _ENTITY_WITH.format("<k>v</k>"),
        _AT_ENTITY,
        "k",
        _NO_PREFIX,
    ),
    "attribute element in no namespace, local part holding a colon": (
        _ENTITY_WITH.format('<a_x003A_b xmlns:a="http://a.example/">v</a_x003A_b>'),
        _AT_ENTITY,
        "a:b",
        _NO_PREFIX,
    ),
    "empty xsd:QName text": (
        _ENTITY_WITH.format('<ex:k xsi:type="xsd:QName"/>'),
        _AT_ENTITY,
        "",
        "it is empty",
    ),
    "blank xsd:QName text": (
        _ENTITY_WITH.format('<ex:k xsi:type="xsd:QName">  </ex:k>'),
        _AT_ENTITY,
        "",
        "it is empty",
    ),
}


@pytest.mark.parametrize(
    ("body", "where", "text", "reason", "default"),
    [
        pytest.param(
            *row, default, id=f"{name}, {'default' if default else 'no xmlns'}"
        )
        for name, row in _REJECTED_UNDER_BOTH.items()
        for default in (True, False)
    ]
    + [
        pytest.param(*row, False, id=f"{name}, no xmlns")
        for name, row in _REJECTED_WITH_NO_DEFAULT.items()
    ],
)
def test_a_name_the_nsmap_does_not_resolve_is_rejected_by_the_model(
    body: str, where: str, text: str, reason: str, default: bool
) -> None:
    # the reader sends every such name to the model's one rejection, positioned
    # at the element, whether or not an xmlns is declared (#677)
    with pytest.raises(ProvXMLException) as ctx:
        prov.ProvDocument.deserialize(content=_prov_xml(body, default), format="xml")
    assert ctx.type is ProvXMLException
    assert str(ctx.value) == (
        f"{where}Invalid Qualified Name: {text}, the qualified name {text!r} "
        f"does not resolve, because {reason}"
    )
    assert isinstance(ctx.value.__cause__, prov.ProvExceptionInvalidQualifiedName)


@pytest.mark.parametrize("default", [True, False], ids=["default", "no xmlns"])
@pytest.mark.parametrize("name", ["e", ":e"])
def test_a_name_with_no_prefix_under_an_elements_own_xmlns_is_refused(
    name: str, default: bool
) -> None:
    # an empty prefix reads as a name with no colon, so `:e` is refused as `e`
    # is, whatever the document's default is (#677)
    body = f'<prov:entity xmlns="http://other/" prov:id="{name}"/>'
    with pytest.raises(ProvXMLException) as ctx:
        prov.ProvDocument.deserialize(content=_prov_xml(body, default), format="xml")
    assert str(ctx.value) == (
        'the name "e" is under an xmlns declaration (http://other/) on an '
        "element, which has no scope in PROV; declare the default on the "
        "document or the bundle, or use a prefix"
    )


def _iris(document: prov.ProvDocument) -> list[str]:
    """The IRI of every name the records spell outside the PROV and XSD namespaces."""
    names: list[object] = []
    for record in document.get_records():
        names.append(record.identifier)
        for attr, value in record.attributes:
            names.extend(
                (attr, value.datatype if isinstance(value, prov.Literal) else value)
            )
    return sorted(
        name.uri
        for name in names
        if isinstance(name, QualifiedName)
        and name.namespace.uri not in (PROV.uri, "http://www.w3.org/2001/XMLSchema#")
    )


@pytest.mark.parametrize(
    ("body", "default", "iris"),
    [
        pytest.param(
            '<prov:entity prov:id=":x"/>', True, ["http://d.example/x"], id=":x"
        ),
        pytest.param(
            _USED_WITH.format("<prov:entity>ex:e1</prov:entity>"),
            False,
            ["http://example.org/e1"],
            id="reference text, prefix on the root",
        ),
        pytest.param(
            _USED_WITH.format(
                '<prov:entity xmlns:a="http://a.example/">a:e</prov:entity>'
            ),
            False,
            ["http://a.example/e"],
            id="reference text, prefix on the reference",
        ),
        pytest.param(
            '<prov:entity xmlns:a="http://a.example/" prov:id="a:e1"/>\n'
            '<prov:entity prov:id="a:e2"/>',
            False,
            ["http://a.example/e1", "http://a.example/e2"],
            id="sibling, A before B",
        ),
        pytest.param(
            _ENTITY_WITH.format("<a_x003A_b>v</a_x003A_b>"),
            True,
            ["http://d.example/a:b", "http://example.org/e"],
            id="attribute element",
        ),
        pytest.param(
            _ENTITY_WITH.format('<ex:k xsi:type="xsd:QName"> ex:v </ex:k>'),
            False,
            ["http://example.org/e", "http://example.org/k", "http://example.org/v"],
            id="xsd:QName text with whitespace",
        ),
        pytest.param(
            _USED_WITH.format("<prov:entity>\n   ex:e1\n  </prov:entity>"),
            False,
            ["http://example.org/e1"],
            id="reference text with whitespace",
        ),
    ],
)
def test_a_name_the_nsmap_or_the_model_resolves_is_read(
    body: str, default: bool, iris: list[str]
) -> None:
    document = prov.ProvDocument.deserialize(
        content=_prov_xml(body, default), format="xml"
    )
    assert _iris(document) == iris


def test_a_3_2_3_default_namespace_datatype_reads_back_equal() -> None:
    # 3.2.3 wrote a default-namespace datatype holding ':' as xsi:type=":a:b"
    expected = prov.ProvDocument()
    expected.set_default_namespace("http://d.example/")
    expected.add_namespace("ex", "http://example.org/")
    default = expected.get_default_namespace()
    assert default is not None
    expected.entity("ex:e", {"prov:type": prov.Literal("v", default["a:b"])})
    body = _ENTITY_WITH.format('<prov:type xsi:type=":a:b">v</prov:type>')
    assert (
        prov.ProvDocument.deserialize(content=_prov_xml(body, True), format="xml")
        == expected
    )


def _membership_xml(entity_element: str) -> str:
    return f"""<document xmlns="http://www.w3.org/ns/prov#"
        xmlns:prov="http://www.w3.org/ns/prov#"
        xmlns:ex="http://example.org/">
      <entity prov:id="ex:c"/>
      <entity prov:id="ex:e1"/>
      <hadMember>
        <collection prov:ref="ex:c"/>
        {entity_element}
      </hadMember>
    </document>"""


_MEMBERSHIP_PREFIX = (
    '<prov:document xmlns:prov="http://www.w3.org/ns/prov#" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:ex="http://example.org/">'
)


def _members_xml(id_attribute: str, entities: tuple[str, ...]) -> str:
    refs = "".join(f'<prov:entity prov:ref="{e}"/>' for e in entities)
    return (
        f"{_MEMBERSHIP_PREFIX}<prov:hadMember{id_attribute}>"
        f'<prov:collection prov:ref="ex:c"/>{refs}<ex:k>v</ex:k>'
        "</prov:hadMember></prov:document>"
    )


@pytest.mark.parametrize(
    ("id_attribute", "entities", "identifiers", "entity_lists"),
    [
        pytest.param(
            ' prov:id="ex:m"',
            ("ex:e1", "ex:e2"),
            ["ex:m", "ex:m"],
            [["ex:e1"], ["ex:e2"]],
            id="identified",
        ),
        pytest.param(
            "",
            ("ex:e1", "ex:e2"),
            [None, None],
            [["ex:e1"], ["ex:e2"]],
            id="anonymous",
        ),
        pytest.param(
            ' prov:id="ex:m"',
            ("ex:e1", "ex:e1"),
            ["ex:m"],
            [["ex:e1"]],
            id="repeated-member",
        ),
        pytest.param(' prov:id="ex:m"', (), ["ex:m"], [[]], id="no-member"),
    ],
)
def test_xml_had_member_with_several_entities_reads_one_record_per_member(
    id_attribute: str,
    entities: tuple[str, ...],
    identifiers: list[str | None],
    entity_lists: list[list[str]],
) -> None:
    document = prov.ProvDocument.deserialize(
        content=_members_xml(f'{id_attribute} xsi:type="ex:T"', entities),
        format="xml",
    )
    records = list(document.get_records(prov.ProvMembership))

    assert [r.identifier and str(r.identifier) for r in records] == identifiers
    assert [
        [str(e) for e in r.get_attribute(PROV_ATTR_ENTITY)] for r in records
    ] == entity_lists
    for record in records:
        assert [str(c) for c in record.get_attribute("prov:collection")] == ["ex:c"]
        assert [str(k) for k in record.get_attribute("ex:k")] == ["v"]
        assert [str(t) for t in record.get_attribute(PROV_TYPE)] == ["ex:T"]


def test_xml_had_member_split_equals_the_prov_json_list_read() -> None:
    # The split record stores prov:collection before prov:entity, as a PROV-JSON
    # read does, so the two documents serialise to the same PROV-JSON text.
    from_xml = prov.ProvDocument.deserialize(
        content=_members_xml(' prov:id="ex:m"', ("ex:e1", "ex:e2")), format="xml"
    )
    json_text = json.dumps(
        {
            "prefix": {"ex": "http://example.org/"},
            "hadMember": {
                "ex:m": [
                    {"prov:collection": "ex:c", "prov:entity": entity, "ex:k": "v"}
                    for entity in ("ex:e1", "ex:e2")
                ]
            },
        }
    )
    from_json = prov.ProvDocument.deserialize(content=json_text, format="json")

    assert from_xml == from_json
    assert from_xml.serialize(format="json") == from_json.serialize(format="json")


def test_xml_example_33_reads_three_memberships_and_writes_three_elements() -> None:
    document = prov.ProvDocument.deserialize(
        source=os.path.join(DATA_PATH, "example_33.xml"), format="xml"
    )
    records = list(document.get_records(prov.ProvMembership))

    assert [str(r.get_attribute(PROV_ATTR_ENTITY).pop()) for r in records] == [
        "ex:e0",
        "ex:e1",
        "ex:e2",
    ]
    assert {str(r.get_attribute("prov:collection").pop()) for r in records} == {"ex:c"}
    written = document.serialize(format="xml")
    assert written.count("<prov:hadMember") == 3


@pytest.mark.parametrize(
    ("body", "position"),
    [
        pytest.param(
            "<prov:wasGeneratedBy>"
            '<prov:entity prov:ref="ex:e"/><prov:activity prov:ref="ex:a1"/>'
            '<prov:activity prov:ref="ex:a2"/></prov:wasGeneratedBy>',
            "<prov:wasGeneratedBy> with no prov:id",
            id="other-record-two-activities",
        ),
        pytest.param(
            '<prov:hadMember><prov:collection prov:ref="ex:c1"/>'
            '<prov:collection prov:ref="ex:c2"/>'
            '<prov:entity prov:ref="ex:e1"/><prov:entity prov:ref="ex:e2"/>'
            "</prov:hadMember>",
            "<prov:hadMember> with no prov:id",
            id="membership-two-collections",
        ),
    ],
)
def test_xml_record_with_a_repeated_formal_child_raises(
    body: str, position: str
) -> None:
    with pytest.raises(ProvXMLException, match=rf"{position}: .*more than one value"):
        prov.ProvDocument.deserialize(
            content=f"{_MEMBERSHIP_PREFIX}{body}</prov:document>", format="xml"
        )


def test_nested_reference_child_is_used_with_a_warning() -> None:
    # ProvToolbox 2.0.4 wraps a hadMember's member in an extra <entity>
    # element; the schema puts prov:ref on the element itself.
    xml_string = _membership_xml(
        '<entity>\n          <entity prov:ref="ex:e1"/>\n        </entity>'
    )
    with pytest.warns(prov.ProvWarning, match="nested"):
        document = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (membership,) = document.get_records(prov.ProvMembership)
    (member,) = membership.get_attribute(PROV["entity"])
    assert str(member) == "ex:e1"


def test_blank_reference_element_without_ref_raises() -> None:
    xml_string = _membership_xml("<entity>   </entity>")
    with pytest.raises(ProvXMLException, match="no prov:ref"):
        prov.ProvDocument.deserialize(content=xml_string, format="xml")


def test_reference_given_as_element_text_still_decodes() -> None:
    xml_string = _membership_xml("<entity>ex:e1</entity>")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        document = prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (membership,) = document.get_records(prov.ProvMembership)
    (member,) = membership.get_attribute(PROV["entity"])
    assert str(member) == "ex:e1"


def test_nested_reference_warning_is_attributed_to_the_caller() -> None:
    xml_string = _membership_xml(
        '<entity>\n          <entity prov:ref="ex:e1"/>\n        </entity>'
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        prov.ProvDocument.deserialize(content=xml_string, format="xml")
    (warning,) = [w for w in caught if issubclass(w.category, prov.ProvWarning)]
    assert warning.filename == __file__


def test_xml_writer_rejects_xsi_bound_to_another_iri() -> None:
    document = prov.ProvDocument()
    document.add_namespace("xsi", "http://other/")
    document.entity("xsi:e")

    with pytest.raises(
        ProvXMLException,
        match=r"prefix 'xsi' to <http://www\.w3\.org/2001/XMLSchema-instance>, "
        r"but the document binds it to <http://other/>",
    ):
        document.serialize(format="xml")


def test_xml_namespace_order_keeps_xsi_last_when_it_is_declared() -> None:
    def prefixes(declare: bool) -> list[str]:
        document = prov.ProvDocument()
        document.add_namespace("ex", "http://example.org/")
        if declare:
            document.add_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
        document.entity("ex:e")
        return re.findall(r"xmlns:(\w+)=", document.serialize(format="xml"))

    assert prefixes(True) == prefixes(False) == ["ex", "prov", "xsd", "xsi"]


def test_reader_builds_one_namespace_per_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Spec 3, 3.4: one Namespace per (prefix, uri) a read meets, so the
    # per-namespace QualifiedName cache hits for repeated names.
    default = etree.fromstring(f'<e xmlns="{PROV.uri}"/>')
    scope = prov.ProvDocument()
    scope.set_default_namespace(PROV.uri)
    assert xml_qname_to_QualifiedName(
        default, "entity", scope=scope
    ).namespace == default_namespace(PROV.uri)
    document = examples.primer_example()
    text = document.serialize(format="xml")
    constructed: list[tuple[str, str]] = []
    real_init = Namespace.__init__

    def counting_init(self: Namespace, prefix: str, uri: str) -> None:
        # Only the reader's constructions count; namespaces.py builds its own
        # copy of each binding the model registers.
        if sys._getframe(1).f_globals["__name__"] == ProvXMLSerializer.__module__:
            constructed.append((prefix, uri))
        real_init(self, prefix, uri)

    monkeypatch.setattr(Namespace, "__init__", counting_init)
    back = prov.ProvDocument.deserialize(content=text, format="xml")
    assert back == document
    assert constructed
    assert len(constructed) == len(set(constructed))

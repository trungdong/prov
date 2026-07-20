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
    _escape_ncname_localpart,
    _unescape_ncname_localpart,
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


def test_empty_string_attribute_survives_xml_roundtrip():
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.agent("ex:g0", {"ex:k0": ""})
    assert roundtrip_document(document, "xml") == document


@pytest.mark.parametrize(
    "attributes",
    [
        pytest.param({"ex:k0": ""}, id="plain-attribute"),
        pytest.param({"prov:label": ""}, id="prov-label"),
        pytest.param({"prov:value": ""}, id="prov-value"),
        pytest.param({"ex:lit": prov.Literal("", langtag="en")}, id="literal-langtag"),
    ],
)
def test_empty_string_value_shapes_survive_xml_roundtrip(attributes):
    # #224: an empty-string value must not vanish on the round trip,
    # regardless of which XML shape it takes (plain text, prov:label,
    # prov:value with an inferred xsd:string type, or a language-tagged
    # Literal). The fix must not special-case just one of these paths.
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.agent("ex:g0", attributes)
    assert roundtrip_document(document, "xml") == document


def test_absent_optional_formal_attribute_stays_none_after_xml_roundtrip():
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


def test_attribute_name_with_ncname_illegal_characters_survives_xml_roundtrip():
    # #289 repro: an attribute name containing characters illegal in an XML
    # NCName must not raise, and must round-trip losslessly.
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {"ex:weird'key": "value"})
    assert roundtrip_document(document, "xml") == document


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
def test_ncname_illegal_attribute_names_roundtrip_xml(local_part):
    document = prov.ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.entity("ex:e1", {f"ex:{local_part}": "value"})
    assert roundtrip_document(document, "xml") == document


def test_valid_ncname_attribute_name_serializes_byte_identically():
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


def test_literal_ncname_escape_shaped_attribute_name_roundtrips_xml():
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
def test_escape_unescape_ncname_localpart_is_inverse(local):
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
#   any other library sharing the interpreter (prov is embedded in
#   ProvStore, among others) is free to do. Measured directly:
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


def _xxe_document(secret_path):
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


def test_external_entity_does_not_leak_file_contents(tmp_path):
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


def test_billion_laughs_does_not_expand():
    # Guards against unbounded entity amplification. This is libxml2's own
    # long-standing hard-coded amplification cap doing the work, not
    # anything provxml.py configures -- kept here as a regression guard in
    # case that upstream protection is ever weakened (e.g. via a future
    # `huge_tree=True`, which this module deliberately never sets).
    with pytest.raises(etree.XMLSyntaxError):
        prov.ProvDocument.deserialize(content=_BILLION_LAUGHS_DOCUMENT, format="xml")


def test_deserialize_ignores_tampered_default_parser(
    tmp_path, restore_default_xml_parser
):
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

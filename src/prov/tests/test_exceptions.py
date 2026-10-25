"""The exception hierarchy of the readers and writers."""

import io
import json
from collections.abc import Mapping

import pytest
from lxml import etree

import prov
from prov.model import (
    ProvDocument,
    ProvElementIdentifierRequired,
    ProvException,
    ProvExceptionInvalidQualifiedName,
    ProvValueError,
)
from prov.serializers import (
    DoNotExist,
    ProvFormatNotDetected,
    ProvSerializationError,
    get as get_serializer,
)
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provjsonld import JSONLD_CONTEXT_URL, ProvJSONLDException
from prov.serializers.provn import ProvNSyntaxError
from prov.serializers.provrdf import ProvRDFException
from prov.serializers.provxml import ProvXMLException, ProvXMLSerializer
from prov.tests.conftest import READER_ERRORS

HIERARCHY = [
    (ProvJSONException, ProvSerializationError, True),
    (ProvJSONLDException, ProvSerializationError, True),
    (ProvNSyntaxError, ProvSerializationError, True),
    (ProvXMLException, ProvSerializationError, True),
    (ProvRDFException, ProvSerializationError, True),
    (ProvFormatNotDetected, ProvSerializationError, True),
    (ProvSerializationError, prov.Error, True),
    (ProvNSyntaxError, ProvException, True),
    (ProvJSONException, ProvException, False),
    (ProvJSONLDException, ProvException, False),
    (ProvXMLException, ProvException, False),
    (ProvRDFException, ProvException, False),
    (ProvFormatNotDetected, ProvException, False),
    (DoNotExist, ProvSerializationError, False),
    (DoNotExist, ProvException, False),
    (ProvFormatNotDetected, TypeError, True),
    (ProvValueError, ValueError, True),
]


@pytest.mark.parametrize(
    ("cls", "base", "expected"),
    HIERARCHY,
    ids=[f"{cls.__name__}-{base.__name__}" for cls, base, _ in HIERARCHY],
)
def test_hierarchy(cls: type, base: type, expected: bool) -> None:
    assert issubclass(cls, base) is expected


# PROV-N and PROV-JSON have no error class of their own for a missing document.
WRITER_ERRORS: dict[str, type[ProvSerializationError]] = READER_ERRORS | {
    "provn": ProvSerializationError,
    "json": ProvSerializationError,
}


@pytest.mark.parametrize("fmt", WRITER_ERRORS)
def test_serialize_without_a_document_raises_the_formats_error(fmt: str) -> None:
    stream = io.BytesIO()
    with pytest.raises(
        ProvSerializationError, match=r"^No document to serialize\.$"
    ) as ctx:
        get_serializer(fmt)(document=None).serialize(stream)
    assert type(ctx.value) is WRITER_ERRORS[fmt]
    assert stream.getvalue() == b""


def test_read_of_undetected_content_raises_format_not_detected() -> None:
    with pytest.raises(TypeError) as ctx:
        prov.read("hello world")
    assert isinstance(ctx.value, ProvFormatNotDetected)
    assert str(ctx.value).startswith("Could not read from the source.")
    assert ctx.value.__cause__ is None


EX = "http://example.org/"
BAD_TIME = "2012-01-01T00:00:00+15:00"


def _jsonld(*statements: Mapping[str, object]) -> str:
    return json.dumps(
        {"@context": [{"ex": EX}, JSONLD_CONTEXT_URL], "@graph": statements}
    )


def _jsonld_bundle(*statements: Mapping[str, object]) -> dict[str, object]:
    return {
        "@type": "Bundle",
        "@id": "ex:b",
        "@context": [],
        "@graph": list(statements),
    }


_JSONLD_ACTIVITY = {"@type": "Activity", "@id": "ex:a1", "startTime": BAD_TIME}
_TRIG_PREFIXES = f"@prefix ex: <{EX}> .\n@prefix prov: <http://www.w3.org/ns/prov#> .\n"
PROV_NS = "http://www.w3.org/ns/prov#"
_XML_ROOT = f'<prov:document xmlns:prov="{PROV_NS}" xmlns:ex="{EX}">'
_XML_ROOT_EX2 = _XML_ROOT[:-1] + f' xmlns:ex2="{EX}">'

# A model rejection from a bundle or an element: the format, the content, the
# reader's error, what starts its message and the class of its cause. A record
# inside a bundle is named by itself, never by the bundle.
WRAPPED = [
    pytest.param(
        "jsonld",
        _jsonld(_jsonld_bundle(_JSONLD_ACTIVITY)),
        ProvJSONLDException,
        "prov:Activity 'ex:a1': ",
        ProvValueError,
        id="jsonld-record-in-bundle",
    ),
    pytest.param(
        "json",
        json.dumps(
            {
                "prefix": {"ex": EX},
                "bundle": {
                    "ex:b": {"activity": {"ex:a1": {"prov:startTime": BAD_TIME}}}
                },
            }
        ),
        ProvJSONException,
        "record 'ex:a1': ",
        ProvValueError,
        id="json-record-in-bundle",
    ),
    pytest.param(
        "xml",
        f"""{_XML_ROOT}
  <prov:bundleContent prov:id="ex:b">
    <prov:activity prov:id="ex:a1">
      <prov:startTime>{BAD_TIME}</prov:startTime>
    </prov:activity>
  </prov:bundleContent>
</prov:document>""",
        ProvXMLException,
        "line 3, <prov:activity> 'ex:a1': ",
        ProvValueError,
        id="xml-record-in-bundle",
    ),
    pytest.param(
        "json",
        json.dumps({"prefix": {"ex": EX}, "bundle": {"ex:a b": {}}}),
        ProvJSONException,
        "bundle 'ex:a b': ",
        ProvExceptionInvalidQualifiedName,
        id="json-bundle-name",
    ),
    pytest.param(
        "json",
        json.dumps(
            {"prefix": {"ex": EX, "ex2": EX}, "bundle": {"ex:b": {}, "ex2:b": {}}}
        ),
        ProvJSONException,
        "bundle 'ex2:b': ",
        ProvException,
        id="json-duplicate-bundle",
    ),
    pytest.param(
        "xml",
        f"""{_XML_ROOT_EX2}
  <prov:bundleContent prov:id="ex:b"/>
  <prov:bundleContent prov:id="ex2:b"/>
</prov:document>""",
        ProvXMLException,
        "line 3, <prov:bundleContent> 'ex2:b': ",
        ProvException,
        id="xml-duplicate-bundle",
    ),
    pytest.param(
        "jsonld",
        json.dumps(
            {
                "@context": [{"ex": EX, "ex2": EX}, JSONLD_CONTEXT_URL],
                "@graph": [_jsonld_bundle(), {**_jsonld_bundle(), "@id": "ex2:b"}],
            }
        ),
        ProvJSONLDException,
        "prov:Bundle 'ex2:b': ",
        ProvException,
        id="jsonld-duplicate-bundle",
    ),
    pytest.param(
        "jsonld",
        _jsonld({"@type": "Usage", "time": BAD_TIME}),
        ProvJSONLDException,
        "an anonymous prov:Usage: ",
        ProvValueError,
        id="jsonld-anonymous-usage",
    ),
    pytest.param(
        "xml",
        f"""{_XML_ROOT}
  <prov:activity prov:id="ex:a1"><prov:startTime>2012-01-01T00:00:00.1234567Z</prov:startTime></prov:activity>
</prov:document>""",
        ProvXMLException,
        "line 2, <prov:activity> 'ex:a1': ",
        ProvException,
        id="xml-fraction-beyond-six-digits",
    ),
    pytest.param(
        "xml",
        f"""{_XML_ROOT}
  <prov:entity/>
</prov:document>""",
        ProvXMLException,
        "line 2, <prov:entity> with no prov:id: ",
        ProvElementIdentifierRequired,
        id="xml-element-without-an-id",
    ),
    pytest.param(
        "rdf",
        _TRIG_PREFIXES + 'ex:e1 a prov:Entity ; prov:wasDerivedFrom "not a name" .\n',
        ProvRDFException,
        "subject 'http://example.org/e1': ",
        ProvExceptionInvalidQualifiedName,
        id="rdf-relation-object",
    ),
    pytest.param(
        "rdf",
        _TRIG_PREFIXES + "<http://example.org/a|b> { ex:e a prov:Entity . }\n",
        ProvRDFException,
        "bundle 'http://example.org/a|b': ",
        ProvExceptionInvalidQualifiedName,
        id="rdf-bundle-name",
    ),
]


@pytest.mark.parametrize(("fmt", "content", "error", "where", "cause"), WRAPPED)
def test_a_reader_names_the_record_it_rejects(
    fmt: str, content: str, error: type[Exception], where: str, cause: type[Exception]
) -> None:
    with pytest.raises(error) as ctx:
        ProvDocument.deserialize(content=content, format=fmt)
    assert type(ctx.value) is error
    assert isinstance(ctx.value.__cause__, cause)
    assert str(ctx.value) == where + str(ctx.value.__cause__)


def test_read_of_a_bad_language_tag_chains_the_reader_and_the_model_errors() -> None:
    content = json.dumps(
        {
            "prefix": {"ex": EX},
            "entity": {"ex:e1": {"ex:a": {"$": "hi", "lang": "en_US"}}},
        }
    )
    with pytest.raises(TypeError) as ctx:
        prov.read(content)
    assert type(ctx.value) is ProvFormatNotDetected
    reader_error = ctx.value.__cause__
    assert type(reader_error) is ProvJSONException
    assert type(reader_error.__cause__) is ProvValueError


def test_a_typed_subject_with_no_separator_raises_the_rdf_error() -> None:
    content = _TRIG_PREFIXES + "<urn:example:e2=> a prov:Entity .\n"
    with pytest.raises(ProvRDFException) as ctx:
        ProvDocument.deserialize(content=content, format="rdf")
    assert type(ctx.value) is ProvRDFException
    assert str(ctx.value) == (
        "Cannot split IRI 'urn:example:e2=' into a namespace and a local part: "
        "it contains no '#' or '/' separator."
    )
    assert ctx.value.__cause__ is None


BAD_XML_ELEMENT = [
    pytest.param(
        f"""{_XML_ROOT}
  <prov:bundleContent/>
</prov:document>""",
        "bundleContent element has no id",
        id="no-id",
    ),
    pytest.param(
        f"""{_XML_ROOT}
  <prov:bundleContent prov:id="ex:b">
    <prov:bundleContent prov:id="ex:c"/>
  </prov:bundleContent>
</prov:document>""",
        "bundleContent found outside a ProvDocument",
        id="inside-a-bundle",
    ),
    pytest.param(
        f"""{_XML_ROOT}
  <prov:frob prov:id="ex:a1"/>
</prov:document>""",
        "line 2, <prov:frob> 'ex:a1': it is not a PROV element",
        id="unknown-prov-element",
    ),
]


@pytest.mark.parametrize(("content", "message"), BAD_XML_ELEMENT)
def test_a_malformed_element_raises_the_xml_error(content: str, message: str) -> None:
    with pytest.raises(ProvXMLException) as ctx:
        ProvDocument.deserialize(content=content, format="xml")
    assert type(ctx.value) is ProvXMLException
    assert str(ctx.value) == message
    assert ctx.value.__cause__ is None


def test_an_element_built_in_code_has_no_line_to_name() -> None:
    root = etree.Element(f"{{{PROV_NS}}}document", nsmap={"prov": PROV_NS, "ex": EX})
    etree.SubElement(root, f"{{{PROV_NS}}}frob").set(f"{{{PROV_NS}}}id", "ex:a1")
    with pytest.raises(ProvXMLException) as ctx:
        ProvXMLSerializer().deserialize_subtree(root, ProvDocument())
    assert str(ctx.value) == "<prov:frob> 'ex:a1': it is not a PROV element"

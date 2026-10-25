"""The exception hierarchy of the readers and writers."""

import io
import json
from collections.abc import Mapping

import pytest

import prov
import prov.serializers
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
from prov.serializers.provxml import ProvXMLException

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
BASE_WRITERS = ["provn", "json"]
OWN_WRITERS = {
    "xml": ProvXMLException,
    "jsonld": ProvJSONLDException,
    "rdf": ProvRDFException,
}


@pytest.mark.parametrize("fmt", BASE_WRITERS)
def test_serialize_without_a_document_raises_the_base(fmt: str) -> None:
    stream = io.BytesIO()
    with pytest.raises(
        ProvSerializationError, match=r"^No document to serialize\.$"
    ) as ctx:
        get_serializer(fmt)(document=None).serialize(stream)
    assert type(ctx.value) is ProvSerializationError
    assert stream.getvalue() == b""


@pytest.mark.parametrize("fmt", OWN_WRITERS)
def test_serialize_without_a_document_raises_the_formats_own_error(fmt: str) -> None:
    stream = io.BytesIO()
    with pytest.raises(OWN_WRITERS[fmt], match=r"^No document to serialize\.$"):
        get_serializer(fmt)(document=None).serialize(stream)
    assert stream.getvalue() == b""


def test_read_of_undetected_content_raises_format_not_detected() -> None:
    with pytest.raises(TypeError) as ctx:
        prov.read("hello world")
    assert isinstance(ctx.value, ProvFormatNotDetected)
    assert str(ctx.value).startswith("Could not read from the source.")
    assert ctx.value.__cause__ is None


def test_serializers_all_holds_both_new_names() -> None:
    assert {"ProvSerializationError", "ProvFormatNotDetected"} <= set(
        prov.serializers.__all__
    )


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
_XML_ROOT = f'<prov:document xmlns:prov="http://www.w3.org/ns/prov#" xmlns:ex="{EX}">'

# A model rejection from a bundle or an element: the format, the content, the
# reader's error, what starts its message and the class of its cause. A record
# inside a bundle is named by itself, never by the bundle.
WRAPPED = [
    pytest.param(
        "jsonld",
        _jsonld(_jsonld_bundle(_JSONLD_ACTIVITY)),
        ProvJSONLDException,
        "Activity 'ex:a1': ",
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


BAD_BUNDLE_CONTENT = [
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
]


@pytest.mark.parametrize(("content", "message"), BAD_BUNDLE_CONTENT)
def test_a_misplaced_bundle_content_raises_the_xml_error(
    content: str, message: str
) -> None:
    with pytest.raises(ProvXMLException) as ctx:
        ProvDocument.deserialize(content=content, format="xml")
    assert str(ctx.value) == message
    assert ctx.value.__cause__ is None

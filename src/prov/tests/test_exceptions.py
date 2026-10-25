"""The exception hierarchy of the readers and writers."""

import io

import pytest

import prov
import prov.serializers
from prov.model import ProvException, ProvValueError
from prov.serializers import (
    DoNotExist,
    ProvFormatNotDetected,
    ProvSerializationError,
    get as get_serializer,
)
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provjsonld import ProvJSONLDException
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

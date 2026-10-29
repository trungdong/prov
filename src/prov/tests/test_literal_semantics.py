"""Literal value-space semantics: the one value key over the XSD 1.1 lexical
table (#527, #593, #594, #595), the spellings a literal keeps and writes back,
the XSD form of a Python value, and the language tags 3.3.0 rejects (#472)."""

import datetime
import decimal
import enum
import io
import math
import re
import uuid
import warnings
from typing import Any

import pytest

from prov.constants import (
    PROV_INTERNATIONALIZEDSTRING,
    PROV_VALUE,
    XSD,
    XSD_BOOLEAN,
    XSD_DATETIME,
    XSD_DECIMAL,
    XSD_DOUBLE,
    XSD_FLOAT,
    XSD_INT,
    XSD_INTEGER,
    XSD_LONG,
    XSD_STRING,
)
from prov.model import Identifier, Literal, ProvDocument, ProvValueError, QualifiedName
from prov.serializers.provjson import ProvJSONException
from prov.tests.conftest import (
    ROUNDTRIP_FORMATS,
    TEXT_FORMATS,
    ex_document,
    roundtrip_document,
)
from prov.tests.format_errors import READER_ERRORS


def test_decimal_literals_compare_in_value_space() -> None:
    # #77: 10, 10.0 and "10.00" denote the same xsd:decimal value.
    assert Literal(10, XSD_DECIMAL) == Literal(10.0, XSD_DECIMAL)
    assert Literal(10, XSD_DECIMAL) == Literal("10.00", XSD_DECIMAL)
    assert hash(Literal(10, XSD_DECIMAL)) == hash(Literal("10.00", XSD_DECIMAL))
    assert Literal(10, XSD_DECIMAL) != Literal("10.01", XSD_DECIMAL)


def test_ill_formed_decimal_literals_compare_lexically() -> None:
    # A text that decimal.Decimal cannot parse compares as text.
    assert Literal("abc", XSD_DECIMAL) == Literal("abc", XSD_DECIMAL)
    assert hash(Literal("abc", XSD_DECIMAL)) == hash(Literal("abc", XSD_DECIMAL))
    assert Literal("abc", XSD_DECIMAL) != Literal("abd", XSD_DECIMAL)


# One value each (XSD 1.1 Part 2, sections 3.3.2 to 3.3.5 and 3.4.x): two texts
# in a datatype's lexical space that denote the same value in its value space
# (#527, #593, #594, #595).
SAME_VALUE: list[tuple[Literal, Literal]] = [
    (Literal("5", XSD_INT), Literal("05", XSD_INT)),
    (Literal("5", XSD_LONG), Literal("+5", XSD_LONG)),
    (Literal("-5", XSD_INTEGER), Literal("-05", XSD_INTEGER)),
    (Literal("255", XSD["unsignedByte"]), Literal("0255", XSD["unsignedByte"])),
    (Literal("1", XSD_INT), Literal("0" * 64 + "1", XSD_INT)),
    (Literal("1e0", XSD_FLOAT), Literal("1.0E0", XSD_FLOAT)),
    (Literal("1.0", XSD_DOUBLE), Literal("1", XSD_DOUBLE)),
    (Literal("INF", XSD_DOUBLE), Literal("+INF", XSD_DOUBLE)),
    (Literal("INF", XSD_DOUBLE), Literal("1e999", XSD_DOUBLE)),
    (Literal("NaN", XSD_DOUBLE), Literal("NaN", XSD_DOUBLE)),
    (Literal("true", XSD_BOOLEAN), Literal("1", XSD_BOOLEAN)),
    (Literal("false", XSD_BOOLEAN), Literal("0", XSD_BOOLEAN)),
    (Literal("1.0", XSD_DECIMAL), Literal("1.00", XSD_DECIMAL)),
    (Literal(".5", XSD_DECIMAL), Literal("0.50", XSD_DECIMAL)),
    (Literal(decimal.Decimal("1E+2"), XSD_DECIMAL), Literal("100", XSD_DECIMAL)),
]

# Two values: a different asserted datatype (#235), a text outside the lexical
# space or the subtype's range, which compares as text, or a different value.
DIFFERENT_VALUE: list[tuple[Literal, Literal]] = [
    (Literal("5", XSD_INT), Literal("5", XSD_LONG)),
    (Literal("5", XSD_INT), Literal("5", XSD_INTEGER)),
    (Literal("1", XSD_INT), Literal("1.0", XSD_DOUBLE)),
    (Literal("256", XSD["unsignedByte"]), Literal("0256", XSD["unsignedByte"])),
    (
        Literal("-1", XSD["nonNegativeInteger"]),
        Literal("-01", XSD["nonNegativeInteger"]),
    ),
    (Literal("TRUE", XSD_BOOLEAN), Literal("true", XSD_BOOLEAN)),
    (Literal("nan", XSD_DOUBLE), Literal("NaN", XSD_DOUBLE)),
    (Literal("1e1", XSD_DECIMAL), Literal("10", XSD_DECIMAL)),
    (Literal("abc", XSD_INT), Literal("abd", XSD_INT)),
    (Literal("1", XSD_INT), Literal("2", XSD_INT)),
]


@pytest.mark.parametrize(("left", "right"), SAME_VALUE, ids=str)
def test_two_spellings_of_one_value_are_equal(left: Literal, right: Literal) -> None:
    assert left == right
    assert right == left
    assert hash(left) == hash(right)


@pytest.mark.parametrize(("left", "right"), DIFFERENT_VALUE, ids=str)
def test_two_values_are_not_equal(left: Literal, right: Literal) -> None:
    assert left != right
    assert right != left


def test_integer_text_beyond_the_digit_limit_compares_as_text() -> None:
    # int() refuses a text longer than sys.get_int_max_str_digits(); the
    # literal has no value and compares as text instead of raising.
    text = "1" * 5000
    assert Literal(text, XSD_INTEGER) == Literal(text, XSD_INTEGER)
    assert Literal(text, XSD_INTEGER) != Literal(text + "1", XSD_INTEGER)


def test_decimal_comparison_ignores_the_callers_context() -> None:
    # #595: only text the grammar admits reaches Decimal(), whose construction
    # from such text is exact in every context; #593: sNaN never reaches it.
    with decimal.localcontext() as context:
        context.prec = 1
        context.traps[decimal.InvalidOperation] = False
        assert Literal("1.0", XSD_DECIMAL) == Literal("1.00", XSD_DECIMAL)
        assert hash(Literal("1.0", XSD_DECIMAL)) == hash(Literal("1.00", XSD_DECIMAL))
        assert Literal("sNaN", XSD_DECIMAL) != Literal("NaN", XSD_DECIMAL)
        assert Literal("sNaN", XSD_DECIMAL) == Literal("sNaN", XSD_DECIMAL)


def test_langtag_comparison_is_case_insensitive() -> None:
    # #259: RDF 1.1 language tags are case-insensitive in the value space.
    assert Literal("hello", langtag="EN") == Literal("hello", langtag="en")
    assert hash(Literal("hello", langtag="EN")) == hash(Literal("hello", langtag="en"))
    assert Literal("hello", langtag="en") != Literal("hello", langtag="fr")


def test_langtag_case_is_preserved_in_output() -> None:
    # #259 non-goal: the stored tag is not normalised -- output stays verbatim.
    document = ex_document()
    document.entity("ex:e1", {"ex:a": Literal("hello", langtag="EN")})
    content = document.serialize(format="json")
    assert content is not None
    assert '"lang": "EN"' in content


def test_rdf_plain_string_emitted_without_xsd_string() -> None:
    # #89: one canonical form for string literals -- the plain literal.
    document = ex_document()
    document.entity("ex:e1", {"ex:a": "hello"})
    buf = io.BytesIO()
    document.serialize(buf, format="rdf", rdf_format="nt11")
    assert b"^^" not in buf.getvalue()


@pytest.mark.parametrize("tag", ["en_US", "1en", "en-", "en--US", "en US", "fr-ç"])
def test_language_tag_not_shaped_like_bcp47_raises(tag: str) -> None:
    # #472: a tag that does not match PROV-N's LANGTAG has no PROV form.
    message = f"the language tag {tag!r} of 'hi' is not a BCP 47 tag"
    with pytest.raises(ProvValueError, match=re.escape(message)):
        Literal("hi", langtag=tag)


def test_empty_language_tag_raises() -> None:
    with pytest.raises(
        ProvValueError, match=re.escape("the language tag of 'hi' is empty")
    ):
        Literal("hi", langtag="")


@pytest.mark.parametrize("tag", ["", "en_US"])
def test_unpickled_literal_is_checked_too(tag: str) -> None:
    # A pickle from an earlier release may hold such a tag; loading it runs
    # the same check, so no document holds a tag the writers cannot spell.
    literal = Literal.__new__(Literal)
    state = {
        "_value": "hi",
        "_datatype": PROV_INTERNATIONALIZEDSTRING,
        "_langtag": tag,
    }
    with pytest.raises(ProvValueError, match="'hi'"):
        literal.__setstate__(state)


@pytest.mark.parametrize(
    "tag", [None, "en", "EN", "en-GB", "zh-Hant-TW", "de-CH-1901", "x-private"]
)
def test_bcp47_language_tag_is_kept(tag: str | None) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert Literal("hi", langtag=tag).langtag == tag


READER_WHERE = {
    "json": r"record 'ex:e1': ",
    "xml": r"line \d+, <prov:entity> 'ex:e1': ",
    "jsonld": r"prov:Entity 'ex:e1': ",
}
READERS = list(READER_WHERE)


def _written_with_tag(fmt: str, tag: str) -> str:
    # PROV-N cannot carry such a tag and PROV-O refuses to write one; the
    # other three write the tag as given, so the text is edited after writing.
    document = ex_document()
    document.entity("ex:e1", {"ex:a": Literal("hi", langtag="en-US")})
    text = document.serialize(format=fmt)
    assert text is not None
    assert text.count("en-US") == 1
    return text.replace("en-US", tag)


@pytest.mark.parametrize("fmt", READERS)
def test_language_tag_raises_when_read(fmt: str) -> None:
    # The readers build the Literal, so each raises its own error for the
    # record, with the model's error as the cause.
    with pytest.raises(
        READER_ERRORS[fmt], match=f"^{READER_WHERE[fmt]}.*'en_US'"
    ) as ctx:
        ProvDocument.deserialize(content=_written_with_tag(fmt, "en_US"), format=fmt)
    assert isinstance(ctx.value.__cause__, ProvValueError)
    assert not isinstance(ctx.value, ValueError)


@pytest.mark.parametrize("fmt", READERS)
def test_bcp47_language_tag_reads_without_warning(fmt: str) -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:a": Literal("hi", langtag="en-US")})
    content = document.serialize(format=fmt)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert ProvDocument.deserialize(content=content, format=fmt) == document


def test_empty_json_lang_raises() -> None:
    # #472's second way in: PROV-JSON passes "lang" to the Literal as written.
    content = (
        '{"prefix": {"ex": "http://example.org/"},'
        ' "entity": {"ex:e1": {"ex:a": {"$": "hi", "lang": ""}}}}'
    )
    message = "record 'ex:e1': the language tag of 'hi' is empty"
    with pytest.raises(
        ProvJSONException,
        match=f"^{re.escape(message)}$",
    ) as ctx:
        ProvDocument.deserialize(content=content, format="json")
    assert isinstance(ctx.value.__cause__, ProvValueError)


# A typed literal whose text is not the canonical spelling of its value keeps
# its Literal and its text through the four text formats; PROV-O cannot keep
# a spelling, so it reads back as the second column. Either way the document
# compares equal, because records compare by value (#527).
KEPT_TEXT: list[tuple[Literal, object]] = [
    (Literal("05", XSD_INT), 5),
    (Literal("+5", XSD_LONG), Literal("5", XSD_LONG)),
    (Literal("1e0", XSD_DOUBLE), 1.0),
    (Literal("1.0", XSD_FLOAT), Literal("1.0", XSD_FLOAT)),
    (Literal("1", XSD_BOOLEAN), True),
    (Literal("1.00", XSD_DECIMAL), Literal("1.00", XSD_DECIMAL)),
]


def _single_value(document: ProvDocument) -> object:
    (record,) = document.get_record("ex:e1")
    (value,) = record.get_attribute("ex:a")
    return value


@pytest.mark.parametrize(("literal", "via_rdf"), KEPT_TEXT, ids=str)
def test_non_canonical_text_is_kept_and_compares_by_value(
    literal: Literal, via_rdf: object
) -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:a": literal})
    stored = _single_value(document)
    assert isinstance(stored, Literal)
    assert stored.value == literal.value
    for fmt in TEXT_FORMATS:
        back = roundtrip_document(document, fmt)
        value = _single_value(back)
        assert isinstance(value, Literal)
        assert value.value == literal.value
        assert back == document
    back = roundtrip_document(document, "rdf")
    assert _single_value(back) == via_rdf
    assert back == document


def test_canonical_text_collapses_to_the_python_value() -> None:
    document = ex_document()
    document.entity(
        "ex:e1",
        [
            ("ex:a", Literal("5", XSD_INT)),
            ("ex:b", Literal("true", XSD_BOOLEAN)),
            ("ex:c", Literal("1.5", XSD_DOUBLE)),
            ("ex:d", Literal("5000000000", XSD_LONG)),
            ("ex:e", Literal("INF", XSD_DOUBLE)),
        ],
    )
    (record,) = document.get_record("ex:e1")
    assert record.get_attribute("ex:a") == {5}
    assert record.get_attribute("ex:b") == {True}
    assert record.get_attribute("ex:c") == {1.5}
    assert record.get_attribute("ex:d") == {5000000000}
    assert record.get_attribute("ex:e") == {float("inf")}


def test_second_spelling_of_a_held_value_is_not_added() -> None:
    # The per-attribute set keys by value, so the first spelling is kept.
    document = ex_document()
    entity = document.entity("ex:e1", {"ex:a": Literal("05", XSD_INT)})
    entity.add_attributes({"ex:a": 5})
    assert len(entity.get_attribute("ex:a")) == 1
    assert _single_value(document) == Literal("05", XSD_INT)


# A typed literal that is not the canonical spelling of a plain value stays a
# Literal: another datatype than the one prov writes for the value (#235), a
# spelling that is not the canonical one (E6), a datatype with no plain form.
STAYS_A_LITERAL: list[Literal] = [
    Literal("5", XSD_LONG),
    Literal("5", XSD["short"]),
    Literal("5", XSD["unsignedByte"]),
    Literal("5", XSD_INTEGER),
    Literal("99999999999", XSD_INT),
    Literal("+5", XSD_INT),
    Literal("1.5", XSD_DECIMAL),
    Literal("5", XSD_DECIMAL),
]


@pytest.mark.parametrize("literal", STAYS_A_LITERAL, ids=str)
def test_typed_literal_that_is_not_a_canonical_plain_value_stays_a_literal(
    literal: Literal,
) -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:a": literal})
    stored = _single_value(document)
    assert isinstance(stored, Literal)
    assert (stored.value, stored.datatype) == (literal.value, literal.datatype)


def test_nan_collapses_and_is_one_value_with_itself() -> None:
    # "NaN" %% xsd:double is the canonical spelling of a float NaN, so it
    # collapses, and a NaN is identical to itself in a key (E5).
    def build() -> ProvDocument:
        document = ex_document()
        document.entity("ex:e1", {"ex:a": Literal("NaN", XSD_DOUBLE)})
        return document

    stored = _single_value(build())
    assert isinstance(stored, float) and math.isnan(stored)
    assert build() == build()


def test_a_literal_keeps_an_ill_formed_decimal_text_the_caller_gave() -> None:
    # A Literal is the caller's text, however it was spelled; the plain value
    # must have a PROV form prov chooses (#482).
    document = ex_document()
    document.entity("ex:e1", {"ex:a": Literal(decimal.Decimal("NaN"), XSD_DECIMAL)})
    stored = _single_value(document)
    assert stored == Literal("NaN", XSD_DECIMAL)
    for fmt in TEXT_FORMATS:
        back = roundtrip_document(document, fmt)
        assert _single_value(back) == stored
        assert back == document
    with pytest.raises(ProvValueError, match="no xsd:decimal form"):
        ex_document().entity("ex:e2", {"ex:a": decimal.Decimal("NaN")})


# An ill-formed text compares as text and is kept by every text format; PROV-O
# reads the value rdflib coerces it to on parse (C10).
ILL_FORMED_VIA_RDF: list[tuple[Literal, object]] = [
    (Literal("True", XSD_BOOLEAN), True),
    (Literal("inf", XSD_DOUBLE), float("inf")),
]


@pytest.mark.parametrize(("literal", "via_rdf"), ILL_FORMED_VIA_RDF, ids=str)
def test_ill_formed_text_reads_as_a_value_through_prov_o(
    literal: Literal, via_rdf: object
) -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:a": literal})
    assert _single_value(document) == literal
    for fmt in TEXT_FORMATS:
        back = roundtrip_document(document, fmt)
        assert _single_value(back) == literal
        assert back == document
    assert _single_value(roundtrip_document(document, "rdf")) == via_rdf


# An (int, Enum) mixin is an int whose str() is its member name, not its digits.
class _Level(int, enum.Enum):
    LOW = 5


class _OddFloat(float):
    def __repr__(self) -> str:
        return "odd"


class _Stamp(datetime.datetime):
    pass


class _Letter(enum.StrEnum):
    A = "a"


# Literal(value) spells a Python value in XSD form (E7).
@pytest.mark.parametrize(
    ("value", "datatype", "text"),
    [
        (True, XSD_BOOLEAN, "true"),
        (False, None, "false"),
        (float("inf"), XSD_DOUBLE, "INF"),
        (float("-inf"), XSD_DOUBLE, "-INF"),
        (float("nan"), None, "NaN"),
        (1.5, XSD_DOUBLE, "1.5"),
        (1e16, XSD_DOUBLE, "1e+16"),
        (1e16, XSD_DECIMAL, "10000000000000000"),
        (1.5, XSD_DECIMAL, "1.5"),
        (decimal.Decimal("1E+2"), XSD_DECIMAL, "100"),
        (decimal.Decimal("NaN"), XSD_DECIMAL, "NaN"),
        (datetime.datetime(2012, 1, 1), XSD_DATETIME, "2012-01-01T00:00:00"),
        (5, XSD_INT, "5"),
        ("x", None, "x"),
        (datetime.timedelta(days=1, seconds=30), XSD["duration"], "P1DT30S"),
        (
            uuid.UUID(int=1),
            XSD["anyURI"],
            "urn:uuid:00000000-0000-0000-0000-000000000001",
        ),
        (b"\x00\x01", XSD["base64Binary"], "AAE="),
        (b"\xab\x01", XSD["hexBinary"], "AB01"),
        (datetime.date(2012, 1, 1), XSD["date"], "2012-01-01"),
        (_Level.LOW, XSD_INT, "5"),
        # No form in the given datatype: prov's spelling, under that datatype (N29).
        (b"\x00", XSD["duration"], "AA=="),
    ],
    ids=str,
)
def test_literal_spells_a_python_value_in_xsd_form(
    value: object, datatype: QualifiedName | None, text: str
) -> None:
    literal = Literal(value, datatype)
    assert literal.value == text
    assert literal.datatype == datatype


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
@pytest.mark.parametrize(
    ("value", "plain"),
    [
        (_Level.LOW, 5),
        (_OddFloat(1.5), 1.5),
        (_Stamp(2012, 1, 1), datetime.datetime(2012, 1, 1)),
        (
            _Stamp(2012, 1, 1, tzinfo=datetime.UTC),
            datetime.datetime(2012, 1, 1, tzinfo=datetime.UTC),
        ),
    ],
    ids=["int", "float", "datetime", "aware-datetime"],
)
def test_a_subclass_of_a_plain_type_is_written_as_the_plain_value(
    fmt: str, value: object, plain: object
) -> None:
    # every writer spells and types the plain value, so a subclass reads back
    # as the plain type (#657) and equals it, the document included (#663)
    document = ex_document()
    document.entity("ex:e1", [("ex:a", value)])
    with io.BytesIO() as stream:
        document.serialize(destination=stream, format=fmt)
        text = stream.getvalue()
    assert type(value).__name__.encode() not in text
    assert b"LOW" not in text and b"odd" not in text
    back = roundtrip_document(document, fmt)
    read = _single_value(back)
    assert read == plain
    assert type(read) is type(plain)
    assert back == document
    # the record's own storage holds one value, where get_attribute() would
    # merge the pair by Python equality whatever the storage did
    both = ex_document().entity("ex:e2", [("ex:a", value), ("ex:a", plain)])
    assert len(both.extra_attributes) == 1


_AWARE_DT = datetime.datetime(2012, 1, 1, tzinfo=datetime.UTC)


_VALUE_SET = type(
    ex_document().entity("ex:e", [(PROV_VALUE, 5)])._attributes[PROV_VALUE]
)


def _only_key(value: object) -> tuple[Any, ...]:
    """The one key the value set of an attribute assigns to ``value``."""
    (key,) = _VALUE_SET([value]).value_keys()
    return key


@pytest.mark.parametrize(
    ("left", "right", "same"),
    [
        pytest.param("x", Literal("x", XSD_STRING), True, id="str"),
        pytest.param(True, Literal("true", XSD_BOOLEAN), True, id="bool"),
        pytest.param(5, Literal("05", XSD_INT), True, id="int"),
        pytest.param(2**40, Literal(str(2**40), XSD_LONG), True, id="long"),
        pytest.param(1.5, Literal("1.5", XSD_DOUBLE), True, id="float"),
        pytest.param(float("nan"), Literal("NaN", XSD_DOUBLE), True, id="nan"),
        pytest.param(_Level.LOW, 5, True, id="int-subclass"),
        pytest.param(_Letter.A, "a", True, id="str-subclass"),
        pytest.param(
            _Stamp(2012, 1, 1),
            datetime.datetime(2012, 1, 1),
            True,
            id="datetime-subclass",
        ),
        pytest.param(5, Literal("5", XSD_LONG), False, id="int-as-long"),
        pytest.param(2, 2.0, False, id="int-vs-float"),
        pytest.param(True, 1, False, id="bool-vs-int"),
        # a record turns a canonical xsd:dateTime literal into a datetime, so the
        # key difference does not show through a record
        pytest.param(
            _AWARE_DT,
            Literal(_AWARE_DT.isoformat(), XSD_DATETIME),
            False,
            id="datetime-vs-literal",
        ),
    ],
)
def test_a_plain_value_keys_as_its_twin(
    left: object, right: object, same: bool
) -> None:
    # a plain value keys as the typed Literal the writers would write it as
    # (#663), and as nothing else (#235, #34)
    left_key, right_key = _only_key(left), _only_key(right)
    assert (left_key == right_key) is same
    # slot 0 is the datatype's URI, an atomic object the collector skips
    assert isinstance(left_key[0], str)
    assert isinstance(right_key[0], str)
    document = ex_document()
    record = document.entity("ex:e1", [("ex:a", left)])
    assert roundtrip_document(document, "json") == document
    if same:
        assert record == ex_document().entity("ex:e1", [("ex:a", right)])


@pytest.mark.parametrize(
    ("value", "slot"),
    [
        (ex_document().valid_qualified_name("ex:q"), QualifiedName),
        (Identifier("http://example.org/i"), Identifier),
        (decimal.Decimal("1.5"), decimal.Decimal),
    ],
    ids=["qualified-name", "identifier", "fallback"],
)
def test_a_value_with_no_plain_form_keys_by_its_type(value: object, slot: type) -> None:
    assert _only_key(value)[0] is slot


def test_float_subclass_with_a_custom_repr_converts_to_decimal() -> None:
    assert Literal(_OddFloat(0.1), XSD_DECIMAL).value == "0.1"

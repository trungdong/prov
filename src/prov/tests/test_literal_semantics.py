"""Literal value-space semantics (3.0): #77 decimal, #259 langtag, #89 string form,
and the language tags 3.3.0 rejects (#472)."""

import decimal
import io
import re
import warnings

import pytest

from prov.constants import (
    PROV_INTERNATIONALIZEDSTRING,
    XSD,
    XSD_BOOLEAN,
    XSD_DECIMAL,
    XSD_DOUBLE,
    XSD_FLOAT,
    XSD_INT,
    XSD_INTEGER,
    XSD_LONG,
)
from prov.model import Literal, ProvDocument, ProvValueError


def _doc() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


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
    document = _doc()
    document.entity("ex:e1", {"ex:a": Literal("hello", langtag="EN")})
    content = document.serialize(format="json")
    assert content is not None
    assert '"lang": "EN"' in content


def test_rdf_plain_string_emitted_without_xsd_string() -> None:
    # #89: one canonical form for string literals -- the plain literal.
    document = _doc()
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


READERS = ["json", "xml", "jsonld"]


def _written_with_tag(fmt: str, tag: str) -> str:
    # PROV-N cannot carry such a tag and PROV-O refuses to write one; the
    # other three write the tag as given, so the text is edited after writing.
    document = _doc()
    document.entity("ex:e1", {"ex:a": Literal("hi", langtag="en-US")})
    text = document.serialize(format=fmt)
    assert text is not None
    assert text.count("en-US") == 1
    return text.replace("en-US", tag)


@pytest.mark.parametrize("fmt", READERS)
def test_language_tag_raises_when_read(fmt: str) -> None:
    # The readers build the Literal, so the model's error reaches their caller.
    with pytest.raises(ProvValueError, match="'en_US'"):
        ProvDocument.deserialize(content=_written_with_tag(fmt, "en_US"), format=fmt)


@pytest.mark.parametrize("fmt", READERS)
def test_bcp47_language_tag_reads_without_warning(fmt: str) -> None:
    document = _doc()
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
    with pytest.raises(ProvValueError, match="is empty"):
        ProvDocument.deserialize(content=content, format="json")

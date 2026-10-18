"""Literal value-space semantics (3.0): #77 decimal, #259 langtag, #89 string form,
and the 3.2.3 warning for a language tag 3.3.0 rejects (#472)."""

import io
import re
import warnings

import pytest

from prov.constants import XSD_DECIMAL, XSD_INT
from prov.model import Literal, ProvDocument, ProvFutureRejectionWarning


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


def test_non_decimal_literals_compare_lexically() -> None:
    # value-space comparison is decimal-only; other datatypes stay lexical.
    assert Literal("1", XSD_INT) != Literal("01", XSD_INT)


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
def test_language_tag_not_shaped_like_bcp47_warns(tag: str) -> None:
    # #472: 3.3.0 rejects a tag that does not match PROV-N's LANGTAG; 3.2.3
    # warns and keeps the tag as given.
    message = f"the language tag {tag!r} of 'hi' is not a BCP 47 tag"
    with pytest.warns(
        ProvFutureRejectionWarning,
        match=re.escape(f"{message}. prov 3.3.0 will reject this (#472)"),
    ) as record:
        literal = Literal("hi", langtag=tag)
    assert literal.langtag == tag
    assert record[0].filename == __file__


def test_empty_language_tag_warns() -> None:
    # #472: 3.3.0 rejects an empty tag too.
    with pytest.warns(
        ProvFutureRejectionWarning,
        match=re.escape(
            "the language tag of 'hi' is empty. prov 3.3.0 will reject this (#472)"
        ),
    ):
        literal = Literal("hi", langtag="")
    assert literal.langtag == ""


@pytest.mark.parametrize(
    "tag", [None, "en", "EN", "en-GB", "zh-Hant-TW", "de-CH-1901", "x-private"]
)
def test_bcp47_language_tag_does_not_warn(tag: str | None) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        assert Literal("hi", langtag=tag).langtag == tag


READERS = ["json", "xml", "jsonld"]


@pytest.mark.parametrize("fmt", READERS)
def test_language_tag_warns_when_read(fmt: str) -> None:
    # The readers build the Literal, so the model's warning reaches their caller.
    # PROV-N cannot carry such a tag and PROV-O refuses to write one.
    document = _doc()
    with pytest.warns(ProvFutureRejectionWarning):
        document.entity("ex:e1", {"ex:a": Literal("hi", langtag="en_US")})
    content = document.serialize(format=fmt)
    with pytest.warns(ProvFutureRejectionWarning, match="'en_US'") as record:
        read = ProvDocument.deserialize(content=content, format=fmt)
    assert read == document
    assert [w.filename for w in record] == [__file__]


@pytest.mark.parametrize("fmt", READERS)
def test_bcp47_language_tag_reads_without_warning(fmt: str) -> None:
    document = _doc()
    document.entity("ex:e1", {"ex:a": Literal("hi", langtag="en-US")})
    content = document.serialize(format=fmt)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        assert ProvDocument.deserialize(content=content, format=fmt) == document


def test_empty_json_lang_warns() -> None:
    # #472's second way in: PROV-JSON passes "lang" to the Literal as written.
    content = (
        '{"prefix": {"ex": "http://example.org/"},'
        ' "entity": {"ex:e1": {"ex:a": {"$": "hi", "lang": ""}}}}'
    )
    with pytest.warns(ProvFutureRejectionWarning, match="is empty"):
        ProvDocument.deserialize(content=content, format="json")

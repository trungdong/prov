"""The remaining 3.2.3 warnings of the PROV-N reader, the statement rules; 3.3.0 turns each into a rejection."""

import pytest

from prov.model import (
    ProvDocument,
    ProvFutureRejectionWarning,
    ProvWarning,
)
from prov.serializers.provn_parser import (
    ProvNParser,
)
from prov.tests.test_provn import (
    STATEMENT_PREFIX,
)

from .conftest import no_future_rejection


def parse_with_warnings(
    text: str, profile: str = "default"
) -> tuple[ProvDocument, list[str]]:
    parser = ProvNParser(text, profile)
    return parser.parse(), parser.warnings


def test_bundle_header_prefix_percent_encoding_warns_once() -> None:
    # The synthesised "dn:" prefix and the percent-encoding of an
    # unrepresentable character in the bundle's own identifier are two
    # separate writer decisions on the same identifier; only one warning
    # should reach the caller, via the same code path
    # provn_bare_representation() uses.
    d = ProvDocument()
    d.set_default_namespace("http://doc.org/")
    with pytest.warns(ProvFutureRejectionWarning):
        b = d.bundle("b 1")
    b.set_default_namespace("http://bundle.org/")
    b.entity("e1")
    with pytest.warns(ProvWarning) as record:
        text = d.get_provn()
    assert "bundle dn:b%201" in text
    assert len(record) == 1


def _reads_back_without_future_warnings(text: str) -> ProvDocument:
    with no_future_rejection():
        return ProvDocument.deserialize(content=text, format="provn")


STRICT_ISSUE = 519


STRICT_CLAUSE = (
    f". prov 3.3.0 will reject this under the strict profile (#{STRICT_ISSUE})"
)


def _read_warning(text: str, match: str, profile: str = "default") -> ProvDocument:
    with pytest.warns(ProvFutureRejectionWarning, match=match) as caught:
        doc = ProvDocument.deserialize(content=text, format="provn", profile=profile)
    assert len(caught) == 1
    return doc


def read_statement(
    statement: str, profile: str = "default"
) -> tuple[ProvDocument, list[str]]:
    return parse_with_warnings(f"{STATEMENT_PREFIX}{statement}\nendDocument", profile)


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
@pytest.mark.parametrize(
    ("statement", "positional", "formal", "keyword"),
    [
        (
            "wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])",
            "wasGeneratedBy(ex:e, ex:a, -)",
            "activity",
            "wasGeneratedBy",
        ),
        (
            "wasGeneratedBy(ex:e, ex:a, -, [prov:activity='ex:a'])",
            "wasGeneratedBy(ex:e, ex:a, -)",
            "activity",
            "wasGeneratedBy",
        ),
        (
            'activity(ex:a, -, -, [prov:startTime="2011-11-16T16:05:00"])',
            "activity(ex:a, 2011-11-16T16:05:00, -)",
            "startTime",
            "activity",
        ),
    ],
)
def test_attribute_named_after_a_formal_warns_and_reads_as_that_formal(
    profile: str, statement: str, positional: str, formal: str, keyword: str
) -> None:
    doc, messages = read_statement(statement, profile)
    column = statement.index("[prov:") + 2
    assert messages == [
        f"line 3, column {column}: 'prov:{formal}' names the '{formal}' argument"
        f" of '{keyword}', which PROV-N gives only by position."
        " prov 3.3.0 will reject this (#523)"
    ]
    positional_doc, positional_messages = read_statement(positional, profile)
    assert positional_messages == []
    assert doc == positional_doc


def test_reserved_attribute_that_is_not_a_formal_does_not_warn() -> None:
    _, messages = read_statement("wasGeneratedBy(ex:e, ex:a, -, [prov:role='ex:r'])")
    assert messages == []


def test_formal_attribute_is_matched_by_name_not_spelling() -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\n"
        "prefix p <http://www.w3.org/ns/prov#>\n"
        "wasGeneratedBy(ex:e, -, -, [p:activity='ex:a'])\nendDocument"
    )
    assert messages == [
        "line 4, column 29: 'p:activity' names the 'activity' argument of"
        " 'wasGeneratedBy', which PROV-N gives only by position."
        " prov 3.3.0 will reject this (#523)"
    ]


def test_formal_attribute_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        f"{STATEMENT_PREFIX}wasGeneratedBy(ex:e, -, -, [prov:activity='ex:a'])\n"
        "endDocument",
        "'prov:activity' names the 'activity' argument of 'wasGeneratedBy'",
    )
    assert doc == read_statement("wasGeneratedBy(ex:e, ex:a, -)")[0]


AFTER_BUNDLE = "a statement follows a bundle, which the strict profile does not allow"


def test_strict_statement_after_a_bundle_warns_once_per_run() -> None:
    _, messages = read_statement(
        "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)\nentity(ex:g)\n"
        "bundle ex:c\nentity(ex:e)\nendBundle\nentity(ex:h)",
        "strict",
    )
    assert messages == [
        f"line 6, column 1: {AFTER_BUNDLE}" + STRICT_CLAUSE,
        f"line 11, column 1: {AFTER_BUNDLE}" + STRICT_CLAUSE,
    ]


def test_strict_statement_before_a_bundle_does_not_warn() -> None:
    _, messages = read_statement(
        "entity(ex:f)\nbundle ex:b\nentity(ex:e)\nendBundle", "strict"
    )
    assert messages == []


@pytest.mark.parametrize("profile", ["default", "lenient"])
def test_statement_after_a_bundle_warns_only_under_strict(profile: str) -> None:
    _, messages = read_statement(
        "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)", profile
    )
    assert messages == []


BARE_RELATION_CASES = [
    ("hadMember(ex:m; ex:c, ex:e)", "an identifier", "ex:m"),
    ("hadMember(-; ex:c, ex:e)", "an identifier", "-"),
    ("alternateOf(ex:a; ex:e2, ex:e1)", "an identifier", "ex:a"),
    ('specializationOf(ex:e2, ex:e1, [ex:k="x"])', "an attribute block", "["),
    ("alternateOf(ex:e2, ex:e1, [])", "an attribute block", "["),
]


@pytest.mark.parametrize(("statement", "what", "marker"), BARE_RELATION_CASES)
def test_strict_identifier_or_attributes_on_a_bare_relation_warns(
    statement: str, what: str, marker: str
) -> None:
    keyword = statement.split("(")[0]
    column = statement.index(marker) + 1
    _, messages = read_statement(statement, "strict")
    assert messages == [
        f"line 3, column {column}: '{keyword}' has {what}, which the strict"
        " profile does not allow" + STRICT_CLAUSE
    ]


def test_strict_identifier_and_attributes_on_a_bare_relation_warn_twice() -> None:
    _, messages = read_statement('hadMember(ex:m; ex:c, ex:e, [ex:k="x"])', "strict")
    assert messages == [
        "line 3, column 11: 'hadMember' has an identifier, which the strict"
        " profile does not allow" + STRICT_CLAUSE,
        "line 3, column 29: 'hadMember' has an attribute block, which the strict"
        " profile does not allow" + STRICT_CLAUSE,
    ]


@pytest.mark.parametrize("profile", ["default", "lenient"])
@pytest.mark.parametrize("statement", [case[0] for case in BARE_RELATION_CASES])
def test_bare_relation_warns_only_under_strict(profile: str, statement: str) -> None:
    _, messages = read_statement(statement, profile)
    assert messages == []


@pytest.mark.parametrize(
    "statement",
    [
        'wasDerivedFrom(ex:d; ex:e2, ex:e1, [ex:k="x"])',
        "prov:mentionOf(ex:m; ex:e2, ex:e1, ex:b)",
    ],
)
def test_strict_identifier_and_attributes_on_other_relations_do_not_warn(
    statement: str,
) -> None:
    _, messages = read_statement(statement, "strict")
    assert messages == []


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (
            "bundle ex:b\nentity(ex:e)\nendBundle\nentity(ex:f)",
            "a statement follows a bundle",
        ),
        ("hadMember(ex:m; ex:c, ex:e)", "'hadMember' has an identifier"),
        (
            'specializationOf(ex:e2, ex:e1, [ex:k="x"])',
            "'specializationOf' has an attribute block",
        ),
    ],
)
def test_strict_statement_warning_reaches_the_caller(body: str, match: str) -> None:
    text = f"{STATEMENT_PREFIX}{body}\nendDocument"
    doc = _read_warning(text, match, "strict")
    assert doc == ProvDocument.deserialize(content=text, format="provn")

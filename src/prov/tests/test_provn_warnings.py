"""The 3.2.3 warnings of the PROV-N reader, moved from test_provn.py; 3.3.0 turns each into a rejection."""

import pytest

from prov.constants import PROV, XSD, XSI
from prov.identifier import Namespace
from prov.model import (
    ProvDocument,
    ProvFutureRejectionWarning,
    ProvWarning,
)
from prov.serializers.provn_parser import (
    ProvNParser,
)
from prov.tests.test_provn import (
    OTHER_XSI,
    STATEMENT_PREFIX,
    XSI_LINE,
    _xsi_document,
    only_record,
)

from .conftest import no_future_rejection


def parse_with_warnings(
    text: str, profile: str = "default"
) -> tuple[ProvDocument, list[str]]:
    parser = ProvNParser(text, profile)
    return parser.parse(), parser.warnings


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
def test_xsi_is_an_ordinary_prefix(profile: str) -> None:
    doc, messages = parse_with_warnings(
        OTHER_XSI + "entity(xsi:e, [xsi:k='xsi:v', ex:t=\"1\" %% xsi:t])\nendDocument",
        profile,
    )
    record = only_record(doc)
    assert record.identifier.uri == "http://other/e"
    attributes = {name.uri: value for name, value in record.extra_attributes}
    assert attributes["http://other/k"].uri == "http://other/v"
    assert attributes["http://example.org/t"].datatype.uri == "http://other/t"
    assert messages == []


def test_xsi_is_an_ordinary_prefix_at_bundle_scope() -> None:
    doc, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\nbundle ex:b\n"
        "prefix xsi <http://other/>\nentity(xsi:e)\nendBundle\nendDocument"
    )
    (bundle,) = doc.bundles
    assert only_record(bundle).identifier.uri == "http://other/e"
    assert messages == []


def test_undeclared_xsi_resolves_to_the_builtin_namespace_and_warns() -> None:
    doc, messages = parse_with_warnings(
        'document\nprefix ex <http://example.org/>\nentity(ex:e, [xsi:type="ex:T"])\n'
        "endDocument"
    )
    ((name, _),) = only_record(doc).extra_attributes
    assert name.uri == XSI.uri + "type"
    assert len(messages) == 1
    assert messages[0].startswith("line 3, column ")
    assert messages[0].endswith(
        f"prefix 'xsi' is not declared; it resolves to <{XSI.uri}>."
        " prov 3.3.0 will reject this (#510)"
    )


def test_undeclared_xsi_value_warns() -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\nentity(ex:e, [ex:p='xsi:v'])\n"
        "endDocument"
    )
    assert len(messages) == 1
    assert "prefix 'xsi' is not declared" in messages[0]


def test_undeclared_xsi_warning_reaches_the_caller() -> None:
    with pytest.warns(ProvFutureRejectionWarning, match="prefix 'xsi' is not declared"):
        ProvDocument.deserialize(
            content="document\nprefix ex <http://example.org/>\n"
            'entity(ex:e, [xsi:type="ex:T"])\nendDocument',
            format="provn",
        )


def test_xsi_qualified_name_literal_resolves_against_the_declared_scope() -> None:
    doc, messages = parse_with_warnings(
        OTHER_XSI + 'entity(ex:e, [ex:p="xsi:v" %% prov:QUALIFIED_NAME])\nendDocument'
    )
    ((_, value),) = only_record(doc).extra_attributes
    assert value.uri == "http://other/v"
    assert messages == []


def test_undeclared_xsi_qualified_name_literal_warns_and_keeps_the_builtin() -> None:
    doc, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\n"
        'entity(ex:e, [ex:p="xsi:v" %% prov:QUALIFIED_NAME])\nendDocument'
    )
    ((_, value),) = only_record(doc).extra_attributes
    assert value.uri == XSI.uri + "v"
    assert len(messages) == 1
    assert messages[0].endswith(
        f"prefix 'xsi' is not declared; it resolves to <{XSI.uri}>."
        " prov 3.3.0 will reject this (#510)"
    )


def test_xsi_bundle_identifier_resolves_against_the_declared_scope() -> None:
    doc, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\nprefix xsi <http://other/>\n"
        "bundle xsi:b\nentity(ex:e)\nendBundle\nendDocument"
    )
    (bundle,) = doc.bundles
    assert bundle.identifier.uri == "http://other/b"  # type: ignore[union-attr]
    assert messages == []


def test_xsi_declared_at_its_standard_iri_does_not_warn() -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix ex <http://example.org/>\nprefix xsi <{XSI.uri}>\n"
        'entity(ex:e, [xsi:type="ex:T"])\nendDocument'
    )
    assert messages == []


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


def test_writer_declares_xsi_when_a_record_uses_it() -> None:
    doc = _xsi_document()
    doc.entity("ex:e", {XSI["type"]: "ex:T"})
    text = doc.get_provn()
    assert XSI_LINE in text
    assert _reads_back_without_future_warnings(text) == doc


def test_writer_declares_xsi_for_an_xsi_identifier() -> None:
    doc = _xsi_document()
    doc.entity(XSI["e"])
    text = doc.get_provn()
    assert XSI_LINE in text
    assert _reads_back_without_future_warnings(text) == doc


def test_writer_declares_xsi_when_another_prefix_holds_its_iri() -> None:
    doc = _xsi_document()
    doc.add_namespace("foo", XSI.uri)
    doc.entity("ex:e", {XSI["type"]: "ex:T"})
    text = doc.get_provn()
    assert XSI_LINE in text
    assert _reads_back_without_future_warnings(text) == doc


def test_writer_declares_xsi_in_the_bundle_that_uses_it() -> None:
    doc = _xsi_document()
    doc.entity("ex:e")
    bundle = doc.bundle("ex:b")
    bundle.entity("ex:f", {XSI["type"]: "ex:T"})
    text = doc.get_provn()
    assert text.count(XSI_LINE) == 1
    assert text.index(XSI_LINE) > text.index("bundle ex:b")
    assert _reads_back_without_future_warnings(text) == doc


STRICT_ISSUE = 519


STRICT_CLAUSE = (
    f". prov 3.3.0 will reject this under the strict profile (#{STRICT_ISSUE})"
)


def test_repeated_default_warns_and_the_last_one_wins() -> None:
    doc, messages = parse_with_warnings(
        "document\ndefault <http://a/>\ndefault <http://b/>\nentity(e)\nendDocument"
    )
    assert only_record(doc).identifier.uri == "http://b/e"
    assert messages == [
        "line 3, column 1: 'default' is declared twice in this scope; the last one"
        " is used. prov 3.3.0 will reject this (#508)"
    ]


def test_single_default_does_not_warn() -> None:
    _, messages = parse_with_warnings(
        "document\ndefault <http://a/>\nentity(e)\nendDocument"
    )
    assert messages == []


@pytest.mark.parametrize("name", ["_", "a/b", "1a"])
def test_prefix_name_that_is_not_a_pn_prefix_warns(name: str) -> None:
    doc, messages = parse_with_warnings(
        f"document\nprefix {name} <http://x/>\nprefix ex <http://example.org/>\n"
        "entity(ex:e)\nendDocument"
    )
    assert only_record(doc).identifier.uri == "http://example.org/e"
    assert messages == [
        f"line 2, column 8: '{name}' is not a PROV-N prefix name, so no qualified"
        " name can use it. prov 3.3.0 will reject this (#511)"
    ]


@pytest.mark.parametrize("name", ["ex", "a.b", "a_b", "a-1"])
def test_pn_prefix_names_do_not_warn(name: str) -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix {name} <http://x/>\nendDocument"
    )
    assert messages == []


def test_strict_default_after_prefix_warns() -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\ndefault <http://d/>\nendDocument",
        "strict",
    )
    assert messages == [
        "line 3, column 1: 'default' follows a 'prefix' declaration, which the"
        " strict profile does not allow" + STRICT_CLAUSE
    ]


@pytest.mark.parametrize("profile", ["default", "lenient"])
def test_default_after_prefix_warns_only_under_strict(profile: str) -> None:
    _, messages = parse_with_warnings(
        "document\nprefix ex <http://example.org/>\ndefault <http://d/>\nendDocument",
        profile,
    )
    assert messages == []


def test_strict_default_before_prefix_does_not_warn() -> None:
    _, messages = parse_with_warnings(
        "document\ndefault <http://d/>\nprefix ex <http://example.org/>\nendDocument",
        "strict",
    )
    assert messages == []


@pytest.mark.parametrize("prefix, namespace", [("prov", PROV), ("xsd", XSD)])
def test_strict_declaring_a_predeclared_prefix_warns(
    prefix: str, namespace: Namespace
) -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix {prefix} <{namespace.uri}>\nendDocument", "strict"
    )
    assert messages == [
        f"line 2, column 8: prefix '{prefix}' is predeclared, and the strict"
        " profile does not allow declaring it" + STRICT_CLAUSE
    ]


@pytest.mark.parametrize("profile", ["default", "lenient"])
@pytest.mark.parametrize("prefix, namespace", [("prov", PROV), ("xsd", XSD)])
def test_declaring_a_predeclared_prefix_warns_only_under_strict(
    profile: str, prefix: str, namespace: Namespace
) -> None:
    _, messages = parse_with_warnings(
        f"document\nprefix {prefix} <{namespace.uri}>\nendDocument", profile
    )
    assert messages == []


def _read_warning(text: str, match: str, profile: str = "default") -> ProvDocument:
    with pytest.warns(ProvFutureRejectionWarning, match=match) as caught:
        doc = ProvDocument.deserialize(content=text, format="provn", profile=profile)
    assert len(caught) == 1
    return doc


def test_repeated_default_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        "document\ndefault <http://a/>\ndefault <http://b/>\nentity(e)\nendDocument",
        "'default' is declared twice in this scope",
    )
    assert only_record(doc).identifier.uri == "http://b/e"


def test_non_pn_prefix_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        "document\nprefix 1a <http://x/>\nprefix ex <http://example.org/>\n"
        "entity(ex:e)\nendDocument",
        "'1a' is not a PROV-N prefix name",
    )
    assert only_record(doc).identifier.uri == "http://example.org/e"


def test_strict_default_after_prefix_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        "document\nprefix ex <http://example.org/>\ndefault <http://d/>\n"
        "entity(e)\nendDocument",
        "'default' follows a 'prefix' declaration",
        "strict",
    )
    assert only_record(doc).identifier.uri == "http://d/e"


def test_strict_predeclared_prefix_warning_reaches_the_caller() -> None:
    doc = _read_warning(
        f"document\nprefix prov <{PROV.uri}>\nprefix ex <http://example.org/>\n"
        "entity(ex:e)\nendDocument",
        "prefix 'prov' is predeclared",
        "strict",
    )
    assert only_record(doc).identifier.uri == "http://example.org/e"


@pytest.mark.parametrize("profile", ["strict", "default", "lenient"])
def test_non_ws_space_warns_and_reads_as_before(profile: str) -> None:
    text = "document\nprefix ex <http://example.org/>\nentity(ex:e)\xa0\nendDocument\n"
    document = _read_warning(
        text,
        (
            r"^line 3, column 13: U\+00A0 is not PROV-N whitespace\."
            r" prov 3\.3\.0 will reject this \(#509\)$"
        ),
        profile,
    )
    with no_future_rejection():
        assert document == ProvDocument.deserialize(
            content=text.replace("\xa0", " "), format="provn", profile=profile
        )


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

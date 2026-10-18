"""The 3.3.0 warning class, its message helper and the PROV-N channel."""

import json
import warnings

import pytest

import prov.model
from prov._warnings import collect_warnings, future_rejection_message, warn
from prov.model import ProvDocument, ProvFutureRejectionWarning, ProvWarning
from prov.serializers.provn_parser import ProvNParser


def test_future_rejection_warning_is_a_prov_warning() -> None:
    assert issubclass(ProvFutureRejectionWarning, ProvWarning)
    assert prov.model.ProvFutureRejectionWarning is ProvFutureRejectionWarning


def test_future_rejection_message_ends_with_the_default_outcome() -> None:
    message = future_rejection_message(
        "line 3, column 1: 'default' is declared twice", issue=508
    )
    assert message == (
        "line 3, column 1: 'default' is declared twice. "
        "prov 3.3.0 will reject this (#508)"
    )


def test_future_rejection_message_takes_another_outcome() -> None:
    message = future_rejection_message(
        "U+1680 between tokens", "read this differently", issue=509
    )
    assert message == (
        "U+1680 between tokens. prov 3.3.0 will read this differently (#509)"
    )


def test_future_rejection_message_ends_with_the_issue_number() -> None:
    message = future_rejection_message("probe", "keep it", issue=529)
    assert message.endswith(" (#529)")
    assert message.count("(#") == 1


def test_ignoring_one_issue_by_message_leaves_the_others_raising() -> None:
    document = {
        "prefix": {"ex": "http://example.org/"},
        "wasGeneratedBy": {"ex:g": {"ex:nothing": None, "prov:entity": ["ex:e1"]}},
    }
    content = json.dumps(document)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        warnings.filterwarnings(
            "ignore", message=r"(?s).*\(#528\)$", category=ProvFutureRejectionWarning
        )
        with pytest.raises(ProvFutureRejectionWarning, match=r"\(#531\)$"):
            ProvDocument.deserialize(content=content, format="json")


def test_ignoring_one_issue_by_message_matches_a_message_with_a_line_break() -> None:
    # Namespace caches the names it builds, so each half needs a fresh one.
    with pytest.warns(ProvFutureRejectionWarning, match=r"\(#524\)$") as caught:
        prov.model.Namespace("ex", "http://example.org/")["a\nb"]
    assert "\n" in str(caught[0].message)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        warnings.filterwarnings(
            "ignore", message=r"(?s).*\(#524\)$", category=ProvFutureRejectionWarning
        )
        name = prov.model.Namespace("ex", "http://example.org/")["a\nb"]
    assert name.localpart == "a\nb"


PROVN = "document\n  prefix ex <http://example.org/>\n  entity(ex:e1)\nendDocument"


def test_provn_parser_warnings_reach_the_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = ProvNParser.parse

    def parse_and_warn(self: ProvNParser) -> ProvDocument:
        document = original(self)
        self.warnings.append(
            future_rejection_message("line 3, column 3: probe", issue=509)
        )
        return document

    monkeypatch.setattr(ProvNParser, "parse", parse_and_warn)
    with pytest.warns(ProvFutureRejectionWarning) as record:
        ProvDocument.deserialize(content=PROVN, format="provn")
    future = [w for w in record if issubclass(w.category, ProvFutureRejectionWarning)]
    assert [str(w.message) for w in future] == [
        "line 3, column 3: probe. prov 3.3.0 will reject this (#509)"
    ]
    assert future[0].filename == __file__


def test_provn_document_without_messages_emits_no_future_rejection() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        ProvDocument.deserialize(content=PROVN, format="provn")


def test_warn_outside_a_collection_warns_at_the_caller() -> None:
    with pytest.warns(ProvFutureRejectionWarning, match="probe") as record:
        warn("probe", ProvFutureRejectionWarning)
    assert record[0].filename == __file__


def test_warn_inside_a_collection_is_collected_not_shown() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with collect_warnings() as collected:
            warn("probe", ProvFutureRejectionWarning)
    assert collected == [("probe", ProvFutureRejectionWarning)]
    assert caught == []


def test_collect_warnings_restores_the_outer_collection() -> None:
    with collect_warnings() as outer:
        with pytest.raises(RuntimeError), collect_warnings() as inner:
            warn("inner")
            raise RuntimeError
        warn("outer")
    assert inner == [("inner", ProvWarning)]
    assert outer == [("outer", ProvWarning)]

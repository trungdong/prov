"""The 3.3.0 warning class, its message helper and the PROV-N channel."""

import warnings

import pytest

import prov.model
from prov._warnings import future_rejection_message
from prov.model import ProvDocument, ProvFutureRejectionWarning, ProvWarning
from prov.serializers.provn_parser import ProvNParser


def test_future_rejection_warning_is_a_prov_warning() -> None:
    assert issubclass(ProvFutureRejectionWarning, ProvWarning)
    assert prov.model.ProvFutureRejectionWarning is ProvFutureRejectionWarning


def test_future_rejection_message_ends_with_the_default_outcome() -> None:
    message = future_rejection_message("line 3, column 1: 'default' is declared twice")
    assert message == (
        "line 3, column 1: 'default' is declared twice. prov 3.3.0 will reject this"
    )


def test_future_rejection_message_takes_another_outcome() -> None:
    message = future_rejection_message("U+1680 between tokens", "read this differently")
    assert message == "U+1680 between tokens. prov 3.3.0 will read this differently"


PROVN = "document\n  prefix ex <http://example.org/>\n  entity(ex:e1)\nendDocument"


def test_provn_parser_warnings_reach_the_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = ProvNParser.parse

    def parse_and_warn(self: ProvNParser) -> ProvDocument:
        document = original(self)
        self.warnings.append(future_rejection_message("line 3, column 3: probe"))
        return document

    monkeypatch.setattr(ProvNParser, "parse", parse_and_warn)
    with pytest.warns(ProvFutureRejectionWarning) as record:
        ProvDocument.deserialize(content=PROVN, format="provn")
    future = [w for w in record if issubclass(w.category, ProvFutureRejectionWarning)]
    assert [str(w.message) for w in future] == [
        "line 3, column 3: probe. prov 3.3.0 will reject this"
    ]
    assert future[0].filename == __file__


def test_provn_document_without_messages_emits_no_future_rejection() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        ProvDocument.deserialize(content=PROVN, format="provn")

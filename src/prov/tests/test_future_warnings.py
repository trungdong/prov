"""The 3.3.0 warning class, its message helper and the PROV-N channel."""

import prov.model
from prov._warnings import future_rejection_message
from prov.model import ProvFutureRejectionWarning, ProvWarning


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

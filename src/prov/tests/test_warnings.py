"""``prov._warnings``: the ``warn`` helper and its collection context."""

import warnings

import pytest

import prov.model
from prov._warnings import collect_warnings, warn
from prov.model import ProvFutureRejectionWarning, ProvWarning


def test_future_rejection_warning_is_a_prov_warning() -> None:
    # Kept for the filters 3.2.3 users wrote; 3.3.0 never raises it.
    assert issubclass(ProvFutureRejectionWarning, ProvWarning)
    assert prov.model.ProvFutureRejectionWarning is ProvFutureRejectionWarning


def test_warn_outside_a_collection_warns_at_the_caller() -> None:
    with pytest.warns(ProvWarning, match="probe") as record:
        warn("probe")
    assert record[0].filename == __file__


def test_warn_inside_a_collection_is_collected_not_shown() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with collect_warnings() as collected:
            warn("probe")
    assert collected == [("probe", ProvWarning)]
    assert caught == []


def test_collect_warnings_restores_the_outer_collection() -> None:
    with collect_warnings() as outer:
        with pytest.raises(RuntimeError), collect_warnings() as inner:
            warn("inner")
            raise RuntimeError
        warn("outer")
    assert inner == [("inner", ProvWarning)]
    assert outer == [("outer", ProvWarning)]

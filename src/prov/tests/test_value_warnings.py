"""When the 3.3.0 warnings about attribute values fire (#513)."""

from __future__ import annotations

import copy
import pickle
import warnings
from collections.abc import Callable

import pytest

from prov.dot import prov_to_dot
from prov.graph import graph_to_prov, prov_to_graph
from prov.model import (
    XSD_DATETIME,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvFutureRejectionWarning,
)


def _document() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def _time(bundle: ProvBundle) -> None:
    bundle.activity("ex:r", startTime="2012-01-01T00:00:00+15:00")


def _typed_datetime(bundle: ProvBundle) -> None:
    bundle.entity("ex:r", {"ex:t": Literal("2011-11-16T16:05:33+15:00", XSD_DATETIME)})


ASSERTIONS: dict[str, Callable[[ProvBundle], None]] = {
    "time": _time,
    "typed datetime": _typed_datetime,
}


def _asserted_twice(assertion: Callable[[ProvBundle], None]) -> ProvDocument:
    # Twice in the document and twice in a bundle, so unified() merges a pair
    # in each scope and flattened() has a bundle to lift.
    document = _document()
    bundle = document.bundle("ex:b")
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        for scope in (document, bundle):
            assertion(scope)
            assertion(scope)
    assert len(caught) == 4
    return document


def _copied(document: ProvDocument) -> None:
    for record in document.get_records():
        record.copy()


def _added(document: ProvDocument) -> None:
    other = ProvDocument()
    for record in document.get_records():
        other.add_record(record)


def _updated(document: ProvDocument) -> None:
    _document().update(document)


REBUILDS: dict[str, Callable[[ProvDocument], object]] = {
    "copy": _copied,
    "add_record": _added,
    "unified": lambda document: document.unified(),
    "flattened": lambda document: document.flattened(),
    "update": _updated,
    "prov_to_dot": prov_to_dot,
    "graph": lambda document: graph_to_prov(prov_to_graph(document)),
    "pickle": lambda document: pickle.loads(pickle.dumps(document)),  # nosec B301 - nosemgrep
    "deepcopy": copy.deepcopy,
}


@pytest.mark.parametrize("assertion", ASSERTIONS.values(), ids=ASSERTIONS.keys())
@pytest.mark.parametrize("rebuild", REBUILDS.values(), ids=REBUILDS.keys())
def test_rebuilt_records_do_not_warn_again(
    assertion: Callable[[ProvBundle], None],
    rebuild: Callable[[ProvDocument], object],
) -> None:
    document = _asserted_twice(assertion)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        rebuild(document)


@pytest.mark.parametrize("assertion", ASSERTIONS.values(), ids=ASSERTIONS.keys())
def test_assertion_after_a_rebuild_warns(
    assertion: Callable[[ProvBundle], None],
) -> None:
    document = _asserted_twice(assertion)
    unified = document.unified()
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        assertion(unified)
    assert len(caught) == 1

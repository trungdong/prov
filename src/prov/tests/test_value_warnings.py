"""3.3.0 warnings about qualified-name values that do not resolve, and when they fire (#516)."""

from __future__ import annotations

import copy
import pickle
from collections.abc import Callable

import pytest

from prov.model import (
    XSD_QNAME,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvFutureRejectionWarning,
)

from .conftest import ex_document, no_future_rejection


def _qualified_name(bundle: ProvBundle) -> None:
    bundle.entity("ex:r", {"ex:q": Literal("zz:x", XSD_QNAME)})


ASSERTIONS: dict[str, Callable[[ProvBundle], None]] = {
    "qualified name": _qualified_name,
}


def _asserted_twice(assertion: Callable[[ProvBundle], None]) -> ProvDocument:
    # Twice in the document and twice in a bundle, so unified() merges a pair
    # in each scope and flattened() has a bundle to lift.
    document = ex_document()
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
    ex_document().update(document)


def _dot(document: ProvDocument) -> object:
    return pytest.importorskip("prov.dot").prov_to_dot(document)


def _graph_round_trip(document: ProvDocument) -> object:
    graph = pytest.importorskip("prov.graph")
    return graph.graph_to_prov(graph.prov_to_graph(document))


REBUILDS: dict[str, Callable[[ProvDocument], object]] = {
    "copy": _copied,
    "add_record": _added,
    "unified": lambda document: document.unified(),
    "flattened": lambda document: document.flattened(),
    "update": _updated,
    "prov_to_dot": _dot,
    "graph": _graph_round_trip,
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
    with no_future_rejection():
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


def test_records_built_while_a_document_is_constructed_warn() -> None:
    source = ex_document()
    records = (
        source.entity(f"ex:e{i}", {"ex:v": Literal("zz:x", XSD_QNAME)})
        for i in range(2)
    )
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        ProvDocument(records=records)
    assert len(caught) == 2

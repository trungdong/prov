"""The 3.3.0 typing stream: the return types mypy sees and the mappings the model accepts.

``uv run mypy src`` checks the ``assert_type`` lines; pytest checks the runtime
behaviour next to them. This module is strict from its first commit and never
joins the override list in ``pyproject.toml``.
"""

from collections.abc import ValuesView
from typing import assert_type

import pytest

from prov.model import (
    ProvAgent,
    ProvBundle,
    ProvDocument,
    ProvEntity,
    ProvException,
    ProvRecord,
)
from prov.tests.examples import primer_example


def test_get_records_returns_a_list_in_both_branches() -> None:
    document = primer_example()
    assert_type(document.get_records(), list[ProvRecord])
    assert_type(document.get_records(ProvEntity), list[ProvEntity])
    assert_type(document.get_records((ProvEntity, ProvAgent)), list[ProvRecord])

    entities = document.get_records(ProvEntity)
    assert entities
    assert all(isinstance(record, ProvEntity) for record in entities)
    # A list, not a one-shot iterator: a second pass sees the same records.
    assert list(entities) == list(entities)
    assert len(document.get_records(ProvEntity)) == len(entities)

    mixed = document.get_records((ProvEntity, ProvAgent))
    assert all(isinstance(record, ProvEntity | ProvAgent) for record in mixed)
    assert len(mixed) > len(entities)


def test_get_records_with_an_empty_tuple_returns_every_record() -> None:
    document = primer_example()
    assert document.get_records(()) == document.get_records()


def test_get_records_returns_a_copy() -> None:
    document = primer_example()
    records = document.get_records()
    records.clear()
    assert document.get_records()


def test_document_bundles_is_a_sized_view() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    document.bundle("ex:b")
    assert_type(document.bundles, ValuesView[ProvBundle])
    assert len(document.bundles) == 1


def test_plain_bundle_has_no_bundles() -> None:
    bundle = ProvBundle()
    with pytest.raises(ProvException):
        _ = bundle.bundles

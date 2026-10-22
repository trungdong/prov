"""The 3.3.0 typing stream: the return types mypy sees and the mappings the model accepts.

``uv run mypy src`` checks the ``assert_type`` lines; pytest checks the runtime
behaviour next to them. This module is strict from its first commit and never
joins the override list in ``pyproject.toml``.
"""

import io
from collections.abc import ValuesView
from pathlib import Path
from types import MappingProxyType
from typing import assert_type

import pytest

from prov.model import (
    NamespaceManager,
    ProvActivity,
    ProvAgent,
    ProvBundle,
    ProvDocument,
    ProvEntity,
    ProvException,
    ProvRecord,
    QualifiedName,
    StreamOrPath,
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


def _no_destination() -> StreamOrPath | None:
    # A call, not an assignment: mypy narrows a variable assigned None to None,
    # which would select the first overload instead of the union one.
    return None


def test_serialize_returns_str_without_a_destination_and_none_with_one(
    tmp_path: Path,
) -> None:
    document = primer_example()
    text = document.serialize(format="provn")
    assert_type(text, str)
    assert "entity(" in text

    stream = io.StringIO()
    assert_type(document.serialize(stream, format="json"), None)
    assert stream.getvalue().startswith("{")

    path = tmp_path / "primer.json"
    assert_type(document.serialize(path), None)
    assert path.read_text().startswith("{")

    result = document.serialize(_no_destination(), format="provn")
    assert_type(result, str | None)
    assert result == text


def test_element_identifier_is_a_qualified_name_and_a_relation_may_lack_one() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    entity = document.entity("ex:e")
    assert_type(entity.identifier, QualifiedName)
    assert entity.identifier.uri == "http://example.org/e"

    generation = document.wasGeneratedBy("ex:e", "ex:a")
    assert_type(generation.identifier, QualifiedName | None)
    assert generation.identifier is None


def test_chaining_methods_keep_the_subclass_type() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    entity = document.entity("ex:e")
    activity = document.activity("ex:a")
    agent = document.agent("ex:ag")

    assert_type(entity.wasGeneratedBy(activity).wasAttributedTo(agent), ProvEntity)
    assert_type(activity.used(entity).wasAssociatedWith(agent), ProvActivity)
    assert_type(agent.actedOnBehalfOf(agent), ProvAgent)

    class Tracked(ProvEntity):
        pass

    tracked = Tracked(document, document.valid_qualified_name("ex:t"))
    assert_type(tracked.wasGeneratedBy(activity), Tracked)
    assert isinstance(tracked.wasGeneratedBy(activity), Tracked)


def test_namespace_arguments_accept_any_mapping() -> None:
    mapping = MappingProxyType({"ex": "http://example.org/"})

    document = ProvDocument(namespaces=mapping)
    assert [ns.prefix for ns in document.get_registered_namespaces()] == ["ex"]

    bundle = ProvBundle(namespaces=mapping)
    assert [ns.prefix for ns in bundle.get_registered_namespaces()] == ["ex"]

    manager = NamespaceManager(mapping)
    manager.add_namespaces(MappingProxyType({"ex2": "http://example.org/2/"}))
    assert {ns.prefix for ns in manager.get_registered_namespaces()} == {"ex", "ex2"}

    manager.add_namespaces({})
    manager.add_namespaces([])
    assert {ns.prefix for ns in manager.get_registered_namespaces()} == {"ex", "ex2"}

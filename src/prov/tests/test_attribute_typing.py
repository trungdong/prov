"""Caller-side typing of the attribute arguments (#474).

mypy checks this module strictly, so every call below is a static assertion
that the argument form is accepted. A `type: ignore[arg-type]` marks a form
that must stay rejected, and `warn_unused_ignores` fails the build if it ever
starts to pass.
"""

from __future__ import annotations

import datetime
import types
from collections.abc import Iterable

from prov.model import (
    PROV,
    PROV_LABEL,
    PROV_TYPE,
    PROV_VALUE,
    ProvDocument,
    ProvEntity,
    QualifiedName,
)


def _document() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def _attribute_names(entity: ProvEntity) -> set[str]:
    return {str(name) for name, _ in entity.attributes}


def test_dict_literals_are_accepted() -> None:
    document = _document()
    number: int | float = 1
    other = document.entity("ex:other")

    labelled = document.entity("ex:a", {PROV_LABEL: "None"})
    valued = document.entity("ex:b", {PROV_VALUE: number})
    mixed = document.entity(
        "ex:c",
        {
            PROV_TYPE: PROV["Collection"],
            "ex:when": datetime.datetime(2026, 1, 1),
            "ex:member": other,
        },
    )

    assert _attribute_names(labelled) == {"prov:label"}
    assert _attribute_names(valued) == {"prov:value"}
    assert _attribute_names(mixed) == {"prov:type", "ex:when", "ex:member"}


def test_prebuilt_dict_with_narrow_types_is_accepted() -> None:
    document = _document()
    attributes = {PROV_LABEL: "x"}

    entity = document.entity("ex:a", attributes)
    activity = document.activity("ex:act", other_attributes=attributes)

    assert _attribute_names(entity) == {"prov:label"}
    assert activity.get_attribute(PROV_LABEL) == {"x"}


def test_non_dict_mapping_is_read_through_items() -> None:
    document = _document()
    read_only = types.MappingProxyType({PROV_LABEL: "x"})

    entity = document.entity("ex:a", read_only)

    assert entity.get_attribute(PROV_LABEL) == {"x"}


def test_pair_collections_are_accepted() -> None:
    document = _document()

    from_list = document.entity("ex:a", [(PROV_LABEL, "x"), ("ex:n", 1)])
    from_tuple = document.entity("ex:b", ((PROV_LABEL, "x"),))
    from_set = document.entity("ex:c", {(PROV_LABEL, "x")})
    from_items = document.entity("ex:d", {PROV_LABEL: "x"}.items())
    from_record = document.entity("ex:e", from_list.attributes)

    assert _attribute_names(from_list) == {"prov:label", "ex:n"}
    for entity in (from_tuple, from_set, from_items):
        assert _attribute_names(entity) == {"prov:label"}
    assert _attribute_names(from_record) == {"prov:label", "ex:n"}


def test_prebuilt_pair_list_with_mixed_values_is_accepted() -> None:
    document = _document()
    pairs = [("ex:a", 1), ("ex:b", "x")]

    entity = document.entity("ex:e", pairs)

    assert _attribute_names(entity) == {"ex:a", "ex:b"}


def test_factory_method_accepts_a_generator() -> None:
    document = _document()
    source = [("ex:a", 1), ("ex:b", "x")]

    entity = document.entity("ex:e", (pair for pair in source))

    assert _attribute_names(entity) == {"ex:a", "ex:b"}


def test_add_attributes_consumes_a_generator_once() -> None:
    document = _document()
    entity = document.entity("ex:a")
    source: list[tuple[QualifiedName | str, str | int]] = [
        (PROV_LABEL, "x"),
        ("ex:n", 1),
    ]

    entity.add_attributes((name, value) for name, value in source)

    assert _attribute_names(entity) == {"prov:label", "ex:n"}


def test_values_without_a_prov_form_are_rejected_statically() -> None:
    document = _document()
    untyped: dict[QualifiedName, object] = {PROV_LABEL: "x"}

    entity = document.entity("ex:a", untyped)  # type: ignore[arg-type]

    assert _attribute_names(entity) == {"prov:label"}


def test_add_attributes_reads_a_non_dict_mapping_through_items() -> None:
    document = _document()
    entity = document.entity("ex:a")
    read_only = types.MappingProxyType({PROV_LABEL: "x"})

    entity.add_attributes(read_only)

    assert entity.get_attribute(PROV_LABEL) == {"x"}


def test_iterable_typed_argument_is_rejected_statically() -> None:
    # `Iterable` in the alias would bring back the literal-inference failure of #474.
    document = _document()

    def pairs() -> Iterable[tuple[str, str]]:
        return [("ex:a", "x")]

    entity = document.entity("ex:e", pairs())  # type: ignore[arg-type]

    assert _attribute_names(entity) == {"ex:a"}

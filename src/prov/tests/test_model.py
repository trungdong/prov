"""
Created on Jan 25, 2012

@author: Trung Dong Huynh
"""

import datetime
import logging
import os
import shutil

import pytest

from prov.constants import PROV_INTERNATIONALIZEDSTRING, XSD
from prov.identifier import Namespace
from prov.model import (
    Literal,
    NamespaceManager,
    ProvBundle,
    ProvDocument,
    ProvElementIdentifierRequired,
    ProvException,
    ProvExceptionInvalidQualifiedName,
    first,
    parse_boolean,
    parse_xsd_datetime,
)
from prov.tests import examples

logger = logging.getLogger(__name__)


EX_URI = "http://www.example.org/"
EX2_URI = "http://www.example2.org/"


def test_loading_all_json():
    json_path = os.path.dirname(os.path.abspath(__file__)) + "/json/"
    fails = []
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            with open(json_path + filename) as json_file:
                try:
                    g1 = ProvDocument.deserialize(json_file)
                    json_str = g1.serialize(indent=4)
                    g2 = ProvDocument.deserialize(content=json_str)
                    assert g1 == g2, (
                        f"Round-trip JSON encoding/decoding failed:  {filename}."
                    )
                except Exception:  # intentionally broad to catch any failure
                    fails.append(filename)

    # Code for debugging the failed tests: reload the failed files so a real
    # failure (not silently swallowed by the broad except above) is reported.
    for filename in fails:
        filepath = json_path + filename
        with open(filepath) as json_file:
            logger.info("Loading %s...", filepath)
            g1 = ProvDocument.deserialize(json_file)
            json_str = g1.serialize(indent=4)
            g2 = ProvDocument.deserialize(content=json_str)
            assert g1 == g2, f"Round-trip JSON encoding/decoding failed:  {filename}."


def test_flattening():
    for name, graph in examples.tests:
        logger.info("Testing flattening of the %s example", name)
        document = graph()
        flattened = document.flattened()
        flattened_records = set(flattened.get_records())
        # counting all the records:
        n_records = 0
        for record in document.get_records():
            n_records += 1
            assert record in flattened_records
        for bundle in document.bundles:
            for record in bundle.get_records():
                n_records += 1
                assert record in flattened_records
        assert n_records == len(flattened.get_records())


def test_unifying():
    # This is a very trivial test just to exercise the unified() function
    # TODO: Create a proper unification test
    json_path = os.path.dirname(os.path.abspath(__file__)) + "/unification/"
    for filename in os.listdir(json_path):
        if not filename.endswith(".json"):
            continue
        filepath = json_path + filename
        with open(filepath) as json_file:
            logger.info("Testing unifying: %s", filename)
            logger.debug("Loading %s...", filepath)
            document = ProvDocument.deserialize(json_file)
            flattened = document.flattened()
            unified = flattened.unified()
            assert len(unified.get_records()) < len(flattened.get_records())


def test_bundle_update_simple():
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)

    b1 = doc.bundle("b1")
    b1.entity("e")

    b2 = doc.bundle("b2")
    b2.entity("e")

    with pytest.raises(ProvException):
        b1.update(1)
    with pytest.raises(ProvException):
        b1.update(doc)

    b1.update(b2)
    assert len(b1.get_records()) == 2


def test_document_update_simple():
    d1 = ProvDocument()
    d1.set_default_namespace(EX_URI)
    d1.entity("e")

    b1 = d1.bundle("b1")
    b1.entity("e")

    d2 = ProvDocument()
    d2.set_default_namespace(EX_URI)
    d2.entity("e")

    b1 = d2.bundle("b1")
    b1.entity("e")
    b2 = d2.bundle("b2")
    b2.entity("e")

    with pytest.raises(ProvException):
        d1.update(1)

    d1.update(d2)
    assert len(d1.get_records()) == 2
    assert len(d1.bundles) == 2


def test_document_update_merges_bundles_with_same_identifier():
    # When both documents already have a bundle with the same identifier,
    # update() must merge the records of the other's bundle into the
    # existing one rather than raising/duplicating (model.py ~2664).
    d1 = ProvDocument()
    d1.set_default_namespace(EX_URI)
    b1 = d1.bundle("b1")
    b1.entity("e1")

    d2 = ProvDocument()
    d2.set_default_namespace(EX_URI)
    b1_other = d2.bundle("b1")
    b1_other.entity("e2")

    d1.update(d2)

    assert len(d1.bundles) == 1
    (merged_bundle,) = d1.bundles
    assert len(merged_bundle.get_records()) == 2


def test_document_update_from_other_with_no_bundles():
    # ProvDocument.update()'s bundle-merging block is only entered when
    # `other.has_bundles()`; a document with only top-level records must
    # skip it cleanly (model.py ~2629).
    d1 = ProvDocument()
    d1.set_default_namespace(EX_URI)
    d1.entity("e1")

    d2 = ProvDocument()
    d2.set_default_namespace(EX_URI)
    d2.entity("e2")

    d1.update(d2)

    assert len(d1.get_records()) == 2
    assert list(d1.bundles) == []


def _document_1():
    d1 = ProvDocument()
    ns_ex = d1.add_namespace("ex", EX_URI)
    d1.entity(ns_ex["e1"])
    return d1


def _document_2():
    d2 = ProvDocument()
    ns_ex = d2.add_namespace("ex", EX2_URI)
    d2.activity(ns_ex["a1"])
    return d2


def _bundle_0():
    return ProvBundle(namespaces={"ex": EX2_URI})


def test_add_bundle_simple():
    d1 = _document_1()
    b0 = _bundle_0()

    with pytest.raises(ProvException):
        d1.add_bundle(b0)
    assert not d1.has_bundles()

    d1.add_bundle(b0, "ex:b0")
    assert d1.has_bundles()
    assert b0 in d1.bundles

    with pytest.raises(ProvException):
        ex2_b0 = b0.identifier
        d1.add_bundle(ProvBundle(identifier=ex2_b0))

    d1.add_bundle(ProvBundle(), "ex:b0")
    assert len(d1.bundles) == 2


def test_add_bundle_document():
    d1 = _document_1()
    d2 = _document_2()

    with pytest.raises(ProvException):
        d1.add_bundle(d2)

    ex2_b2 = d2.valid_qualified_name("ex:b2")
    d1.add_bundle(d2, "ex:b2")
    assert ex2_b2 == first(d1.bundles).identifier
    assert d2 not in d1.bundles
    b2 = ProvBundle()
    b2.update(d2)
    assert b2 in d1.bundles


def test_bundle_requires_an_identifier():
    d1 = _document_1()
    with pytest.raises(ProvException):
        d1.bundle(None)


def test_bundle_rejects_unresolvable_identifier():
    # No default namespace and an unregistered prefix: valid_qualified_name()
    # returns None, which bundle() must turn into a ProvException.
    d1 = _document_1()
    with pytest.raises(ProvException):
        d1.bundle("bogus:x")


def test_bundle_rejects_duplicate_identifier():
    d1 = _document_1()
    d1.bundle("ex:b1")
    with pytest.raises(ProvException):
        d1.bundle("ex:b1")


def test_add_bundle_rejects_document_with_nested_bundles():
    # A ProvDocument that itself already contains bundles cannot be
    # folded into another document as a single bundle (model.py ~2664).
    d1 = _document_1()
    d2 = _document_2()
    d2.bundle("ex:nested").entity("ex:nested-e1")

    with pytest.raises(ProvException):
        d1.add_bundle(d2)


def test_literal_provn_with_single_quotes():
    literal = Literal('{"foo": "bar"}')
    string_rep = literal.provn_representation()
    assert '{\\"f' in string_rep


def test_literal_provn_with_triple_quotes():
    literal = Literal('"""foo\\nbar"""')
    string_rep = literal.provn_representation()
    assert '\\"\\"\\"f' in string_rep


# The following cover the Literal/datatype-parsing helpers
# (docs/test-gap-checklist.md, T13 item under model.py: parse_xsd_datetime,
# parse_boolean, Literal __eq__/__ne__/__hash__, and the langtag-forces-
# InternationalizedString warning).


def test_parse_xsd_datetime_returns_none_on_unparseable_input():
    assert parse_xsd_datetime("not a date at all!!") is None


def test_parse_boolean_variants():
    assert parse_boolean("true")
    assert parse_boolean("1")
    assert not parse_boolean("false")
    assert not parse_boolean("0")
    assert parse_boolean("neither") is None


def test_literal_equality_and_hash():
    l1 = Literal("hello", datatype=XSD["string"])
    l2 = Literal("hello", datatype=XSD["string"])
    l3 = Literal("bye", datatype=XSD["string"])

    assert l1 == l2
    assert l1 != l3
    assert hash(l1) == hash(l2)


def test_literal_not_equal_to_non_literal():
    literal = Literal("hello")
    assert literal != "hello"


def test_langtag_forces_internationalizedstring_datatype_with_warning(caplog):
    with caplog.at_level("WARNING", logger="prov.model"):
        literal = Literal("bonjour", datatype=XSD["string"], langtag="fr")
    assert literal.datatype == PROV_INTERNATIONALIZEDSTRING
    assert any("overridden as" in message for message in caplog.messages), (
        caplog.messages
    )


def test_langtag_without_datatype_defaults_to_internationalizedstring():
    literal = Literal("bonjour", langtag="fr")
    assert literal.datatype == PROV_INTERNATIONALIZEDSTRING


# The following cover ProvException paths in ProvRecord.add_attributes()
# (docs/test-gap-checklist.md, T13 item under model.py).


@pytest.fixture
def doc():
    d = ProvDocument()
    d.add_namespace("ex", "http://example.org/")
    return d


def test_identifierless_record_as_qname_attribute_value_raises(doc):
    e1 = doc.entity("ex:e1")
    a1 = doc.activity("ex:a1")
    # An anonymous (identifier-less) relation used as the value of an
    # attribute expecting a qualified name (here: attribution's agent).
    anonymous_usage = doc.usage(a1, e1)
    assert anonymous_usage.identifier is None

    with pytest.raises(ProvException):
        doc.attribution(e1, anonymous_usage)


def test_identifierless_record_as_generic_attribute_value_raises(doc):
    # Same anonymous-relation value, but through the generic (non-formal)
    # attribute path: _auto_literal_conversion() reduces a ProvRecord to
    # its identifier, which is None here, tripping the "value is None"
    # guard rather than a formal-attribute check.
    e1 = doc.entity("ex:e1b")
    a1 = doc.activity("ex:a1b")
    anonymous_usage = doc.usage(a1, e1)
    assert anonymous_usage.identifier is None

    e2 = doc.entity("ex:e2b")
    with pytest.raises(ProvException):
        e2.add_attributes({"ex:ref": anonymous_usage})


def test_unparseable_datetime_formal_attribute_raises(doc):
    activity = doc.activity("ex:a2")
    with pytest.raises(ProvException):
        activity.add_attributes({"prov:startTime": "not a date"})


def test_conflicting_duplicate_value_raises(doc):
    activity = doc.activity("ex:a3", startTime=datetime.datetime(2020, 1, 1))
    with pytest.raises(ProvException):
        activity.add_attributes({"prov:startTime": datetime.datetime(2020, 1, 2)})


def test_conflicting_duplicate_value_with_naive_vs_aware_datetime(doc):
    # Naive and timezone-aware datetimes for the same single-valued
    # formal attribute still compare as "different" (Python's `!=`
    # between them returns True rather than raising -- confirmed
    # separately: no PROV_ATTRIBUTES value type raises TypeError on
    # `!=`, so the `except TypeError` branch at model.py:521-523 is
    # dead code for any value this library can construct; left
    # deferred per docs/test-gap-checklist.md). This still exercises
    # the duplicate-value ProvException with two "different" datetimes.
    activity = doc.activity("ex:a4", startTime=datetime.datetime(2020, 1, 1))
    aware_time = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    with pytest.raises(ProvException):
        activity.add_attributes({"prov:startTime": aware_time})


def test_record_not_equal_to_non_record(doc):
    e1 = doc.entity("ex:e1")
    assert e1 != "not a record"
    assert e1 != object()


def test_record_value_converted_from_provrecord_for_generic_attribute(doc):
    # A ProvRecord used as the value of a *generic* (non-formal) attribute
    # is converted to a QualifiedName via its identifier
    # (_auto_literal_conversion's ProvRecord branch, model.py:415-417).
    e1 = doc.entity("ex:e1")
    e2 = doc.entity("ex:e2")
    e2.add_attributes({"ex:ref": e1})
    assert e2.get_attribute("ex:ref") == {e1.identifier}


def test_entity_without_identifier_raises():
    d = ProvDocument()
    with pytest.raises(ProvElementIdentifierRequired):
        d.entity(None)


def test_activity_without_identifier_raises():
    d = ProvDocument()
    with pytest.raises(ProvElementIdentifierRequired):
        d.activity(None)


def test_provelementidentifierrequired_str():
    assert (
        str(ProvElementIdentifierRequired())
        == "An identifier is missing. All PROV elements require a valid identifier."
    )


def test_provexceptioninvalidqualifiedname_str():
    exc = ProvExceptionInvalidQualifiedName("bogus")
    assert str(exc) == "Invalid Qualified Name: bogus"


# The following cover small ProvRecord accessors not otherwise exercised
# (docs/test-gap-checklist.md, T13 item under model.py).


def test_get_asserted_types_default_empty(doc):
    e1 = doc.entity("ex:e1")
    assert e1.get_asserted_types() == set()


def test_label_falls_back_to_identifier(doc):
    e1 = doc.entity("ex:e1")
    assert e1.label == str(e1.identifier)


def test_value_property_default_empty(doc):
    e1 = doc.entity("ex:e1")
    assert e1.value == set()


# The following exercise the fluent convenience wrappers on
# ProvEntity/ProvActivity that examples.py does not otherwise reach
# (docs/test-gap-checklist.md, T13 item under model.py).


@pytest.fixture
def ns_doc():
    d = ProvDocument()
    d.set_default_namespace("http://example.org/")
    return d


def test_entity_was_invalidated_by(ns_doc):
    e1 = ns_doc.entity("e1")
    a1 = ns_doc.activity("a1")
    result = e1.wasInvalidatedBy(a1)
    assert result is e1
    assert any(r.get_type().localpart == "Invalidation" for r in ns_doc.get_records())


def test_entity_had_member(ns_doc):
    collection = ns_doc.entity("collection1")
    member = ns_doc.entity("member1")
    result = collection.hadMember(member)
    assert result is collection
    assert any(r.get_type().localpart == "Membership" for r in ns_doc.get_records())


def test_activity_was_started_by(ns_doc):
    a1 = ns_doc.activity("a1")
    trigger = ns_doc.entity("trigger1")
    result = a1.wasStartedBy(trigger)
    assert result is a1
    assert any(r.get_type().localpart == "Start" for r in ns_doc.get_records())


def test_activity_was_ended_by(ns_doc):
    a1 = ns_doc.activity("a1")
    trigger = ns_doc.entity("trigger1")
    result = a1.wasEndedBy(trigger)
    assert result is a1
    assert any(r.get_type().localpart == "End" for r in ns_doc.get_records())


def test_activity_was_informed_by(ns_doc):
    a1 = ns_doc.activity("a1")
    a2 = ns_doc.activity("a2")
    result = a1.wasInformedBy(a2)
    assert result is a1
    assert any(r.get_type().localpart == "Communication" for r in ns_doc.get_records())


def test_activity_set_time_both(ns_doc):
    a1 = ns_doc.activity("a1")
    start = datetime.datetime(2020, 1, 1)
    end = datetime.datetime(2020, 1, 2)
    a1.set_time(startTime=start, endTime=end)
    assert a1.get_startTime() == start
    assert a1.get_endTime() == end


def test_activity_set_time_start_only(ns_doc):
    a1 = ns_doc.activity("a1")
    start = datetime.datetime(2020, 1, 1)
    a1.set_time(startTime=start)
    assert a1.get_startTime() == start
    assert a1.get_endTime() is None


def test_activity_set_time_end_only(ns_doc):
    a1 = ns_doc.activity("a1")
    end = datetime.datetime(2020, 1, 2)
    a1.set_time(endTime=end)
    assert a1.get_startTime() is None
    assert a1.get_endTime() == end


# The following cover NamespaceManager branches not exercised by round-trip
# serialization (docs/test-gap-checklist.md, T13 item under model.py).


def test_construction_without_default_namespace():
    nm = NamespaceManager()
    assert nm.get_default_namespace() is None


def test_get_namespace_miss_and_hit():
    nm = NamespaceManager()
    assert nm.get_namespace("http://example.org/") is None
    ns = Namespace("ex", "http://example.org/")
    nm.add_namespace(ns)
    assert nm.get_namespace("http://example.org/") == ns


def test_add_namespace_reuses_renamed_namespace_from_cache():
    nm = NamespaceManager()
    nm.add_namespace(Namespace("ex", "http://a.example.org/"))
    conflicting = Namespace("ex", "http://b.example.org/")
    first_add = nm.add_namespace(conflicting)
    # Prefix conflict: the second namespace is registered under a new
    # ("ex_1") prefix and cached in the rename map.
    assert first_add.prefix == "ex_1"
    # Adding the *same* conflicting namespace object again should reuse
    # the cached renamed namespace (the `namespace in self._rename_map`
    # branch) rather than renaming it again.
    second_add = nm.add_namespace(conflicting)
    assert second_add is first_add


def test_valid_qualified_name_rejects_blank_node_and_bad_types():
    nm = NamespaceManager()
    assert nm.valid_qualified_name("_:blank1") is None
    assert nm.valid_qualified_name(12345) is None


def test_get_anonymous_identifier_increments_and_uses_prefix():
    nm = NamespaceManager()
    first_id = nm.get_anonymous_identifier()
    second_id = nm.get_anonymous_identifier("custom")
    assert str(first_id) != str(second_id)
    assert str(second_id).startswith("_:custom")


def test_get_unused_prefix_counts_up():
    nm = NamespaceManager()
    nm.add_namespace(Namespace("ex", "http://a.example.org/"))
    # Force two successive conflicts on the same prefix so
    # _get_unused_prefix must count past "ex_1".
    second = nm.add_namespace(Namespace("ex", "http://b.example.org/"))
    third = nm.add_namespace(Namespace("ex", "http://c.example.org/"))
    assert second.prefix == "ex_1"
    assert third.prefix == "ex_2"


def test_construction_with_default_namespace():
    nm = NamespaceManager(default="http://example.org/")
    default_ns = nm.get_default_namespace()
    assert default_ns is not None
    assert default_ns.uri == "http://example.org/"


def test_add_namespaces_with_empty_collection_is_a_no_op():
    nm = NamespaceManager()
    nm.add_namespaces([])
    assert list(nm.get_registered_namespaces()) == []


def test_get_unused_prefix_returns_original_when_available():
    # _get_unused_prefix() is only ever called internally once its
    # caller (add_namespace) has already confirmed a conflict, so this
    # "prefix is actually free" branch is otherwise unreachable; call
    # the helper directly to cover it.
    nm = NamespaceManager()
    assert nm._get_unused_prefix("neverused") == "neverused"


# The following cover ProvBundle API edges not reached by round-trip
# serialization (docs/test-gap-checklist.md, T13 item under model.py).


def test_bundles_property_raises_on_a_plain_bundle():
    b = ProvBundle()
    with pytest.raises(ProvException):
        list(b.bundles)


def test_standalone_bundle_properties():
    b = ProvBundle()
    assert b.records == []
    assert b.identifier is None
    assert b.document is None


def test_add_namespace_without_uri_raises():
    b = ProvBundle()
    with pytest.raises(ProvException):
        b.add_namespace("ex")


def test_mandatory_valid_qname_failure():
    b = ProvBundle()
    with pytest.raises(ProvExceptionInvalidQualifiedName):
        b.mandatory_valid_qname(None)


def test_eq_early_out_for_non_bundle():
    b = ProvBundle()
    assert b != "not a bundle"
    assert b != 42


def test_default_ns_uri_present_and_absent():
    b = ProvBundle()
    assert b.default_ns_uri is None
    b.set_default_namespace("http://example.org/")
    assert b.default_ns_uri == "http://example.org/"


def test_get_registered_namespaces():
    b = ProvBundle()
    b.add_namespace("ex", "http://example.org/")
    uris = {ns.uri for ns in b.get_registered_namespaces()}
    assert "http://example.org/" in uris


def test_has_bundles_false_for_plain_bundle():
    b = ProvBundle()
    assert not b.has_bundles()


# The following cover ProvDocument.serialize()'s file-path save path and
# .deserialize()'s argument-validation error (docs/test-gap-checklist.md, T13
# item under model.py, natural neighbours of the T12 read() tests).


def test_serialize_to_file_path_uses_tempfile_and_move(tmp_path):
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    path = tmp_path / "out.json"
    result = doc.serialize(destination=str(path), format="json")
    assert result is None
    assert path.exists()
    reloaded = ProvDocument.deserialize(str(path), format="json")
    assert reloaded == doc


def test_deserialize_without_source_or_content_raises_type_error():
    with pytest.raises(TypeError):
        ProvDocument.deserialize()


# The following cover ProvDocument.__eq__'s bundle-comparison early-outs and
# unified()'s no-bundles loop (docs/test-gap-checklist.md, T13 item under
# model.py).


def test_not_equal_when_other_is_missing_a_bundle():
    d1 = ProvDocument()
    d1.set_default_namespace("http://example.org/")
    d1.bundle("b1").entity("e1")

    d2 = ProvDocument()
    d2.set_default_namespace("http://example.org/")

    assert d1 != d2


def test_not_equal_when_matching_bundle_content_differs():
    d1 = ProvDocument()
    d1.set_default_namespace("http://example.org/")
    d1.bundle("b1").entity("e1")

    d2 = ProvDocument()
    d2.set_default_namespace("http://example.org/")
    d2.bundle("b1").entity("e2")

    assert d1 != d2


def test_unified_with_no_bundles():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    unified = doc.unified()

    assert list(unified.bundles) == []
    assert unified == doc


# The following cover ProvDocument.plot()'s filename-based save path and its
# unknown-format ValueError (docs/test-gap-checklist.md, T13 item under
# model.py; the matplotlib/interactive-display path remains deferred, see
# checklist).


@pytest.fixture
def plot_doc():
    d = ProvDocument()
    d.add_namespace("ex", "http://example.org/")
    d.entity("ex:e1")
    return d


@pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not available"
)
def test_plot_to_filename_infers_format_and_saves(plot_doc, tmp_path):
    path = tmp_path / "out.png"
    plot_doc.plot(filename=str(path))
    assert path.exists()
    assert path.stat().st_size > 0


@pytest.mark.skipif(
    not shutil.which("dot"), reason="graphviz 'dot' binary not available"
)
def test_plot_unknown_format_raises_value_error(plot_doc, tmp_path):
    path = tmp_path / "out.not-a-real-format"
    with pytest.raises(ValueError):
        plot_doc.plot(filename=str(path))

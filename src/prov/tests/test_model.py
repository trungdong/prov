"""
Created on Jan 25, 2012

@author: Trung Dong Huynh
"""

import datetime
import logging
import os
import shutil
import tempfile
import unittest

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
from prov.tests.attributes import TestAttributesBase
from prov.tests.qnames import TestQualifiedNamesBase
from prov.tests.statements import TestStatementsBase
from prov.tests.utility import RoundTripTestCase

logger = logging.getLogger(__name__)


EX_URI = "http://www.example.org/"
EX2_URI = "http://www.example2.org/"


class TestExamplesBase:
    """This is the base class for testing support for all the examples provided
    in prov.tests.examples.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    def test_all_examples(self):
        for counter, (name, graph) in enumerate(examples.tests, start=1):
            logger.info("%d. Testing the %s example", counter, name)
            g = graph()
            self.do_tests(g)


class TestLoadingProvToolboxJSON(unittest.TestCase):
    def setUp(self):
        self.json_path = os.path.dirname(os.path.abspath(__file__)) + "/json/"
        filenames = os.listdir(self.json_path)
        self.fails = []
        for filename in filenames:
            if filename.endswith(".json"):
                with open(self.json_path + filename) as json_file:
                    try:
                        g1 = ProvDocument.deserialize(json_file)
                        json_str = g1.serialize(indent=4)
                        g2 = ProvDocument.deserialize(content=json_str)
                        self.assertEqual(
                            g1,
                            g2,
                            f"Round-trip JSON encoding/decoding failed:  {filename}.",
                        )
                    except:  # noqa: E722 -- intentionally broad to catch any failure
                        self.fails.append(filename)

    def test_loading_all_json(self):
        # self.assertFalse(fails, 'Failed to load/round-trip %d JSON files (%s)' % (len(fails), ', '.join(fails)))

        # Code for debugging the failed tests
        for filename in self.fails:
            # Reload the failed files
            filepath = self.json_path + filename
            #             os.rename(json_path + filename, json_path + filename + '-fail')
            with open(filepath) as json_file:
                logger.info("Loading %s...", filepath)
                g1 = ProvDocument.deserialize(json_file)
                json_str = g1.serialize(indent=4)
                g2 = ProvDocument.deserialize(content=json_str)
                self.assertEqual(
                    g1,
                    g2,
                    f"Round-trip JSON encoding/decoding failed:  {filename}.",
                )


class TestFlattening(unittest.TestCase):
    def test_flattening(self):
        for name, graph in examples.tests:
            logger.info("Testing flattening of the %s example", name)
            document = graph()
            flattened = document.flattened()
            flattened_records = set(flattened.get_records())
            # counting all the records:
            n_records = 0
            for record in document.get_records():
                n_records += 1
                self.assertIn(record, flattened_records)
            for bundle in document.bundles:
                for record in bundle.get_records():
                    n_records += 1
                    self.assertIn(record, flattened_records)
            self.assertEqual(n_records, len(flattened.get_records()))


class TestUnification(unittest.TestCase):
    def test_unifying(self):
        # This is a very trivial test just to exercise the unified() function
        # TODO: Create a proper unification test
        json_path = os.path.dirname(os.path.abspath(__file__)) + "/unification/"
        filenames = os.listdir(json_path)
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            filepath = json_path + filename
            with open(filepath) as json_file:
                logger.info("Testing unifying: %s", filename)
                logger.debug("Loading %s...", filepath)
                document = ProvDocument.deserialize(json_file)
                flattened = document.flattened()
                unified = flattened.unified()
                self.assertLess(
                    len(unified.get_records()), len(flattened.get_records())
                )


class TestBundleUpdate(unittest.TestCase):
    def test_bundle_update_simple(self):
        doc = ProvDocument()
        doc.set_default_namespace(EX_URI)

        b1 = doc.bundle("b1")
        b1.entity("e")

        b2 = doc.bundle("b2")
        b2.entity("e")

        self.assertRaises(ProvException, lambda: b1.update(1))
        self.assertRaises(ProvException, lambda: b1.update(doc))

        b1.update(b2)
        self.assertEqual(len(b1.get_records()), 2)

    def test_document_update_simple(self):
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

        self.assertRaises(ProvException, lambda: d1.update(1))

        d1.update(d2)
        self.assertEqual(len(d1.get_records()), 2)
        self.assertEqual(len(d1.bundles), 2)

    def test_document_update_merges_bundles_with_same_identifier(self):
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

        self.assertEqual(len(d1.bundles), 1)
        (merged_bundle,) = d1.bundles
        self.assertEqual(len(merged_bundle.get_records()), 2)

    def test_document_update_from_other_with_no_bundles(self):
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

        self.assertEqual(len(d1.get_records()), 2)
        self.assertEqual(list(d1.bundles), [])


class TestAddBundle(unittest.TestCase):
    def document_1(self):
        d1 = ProvDocument()
        ns_ex = d1.add_namespace("ex", EX_URI)
        d1.entity(ns_ex["e1"])
        return d1

    def document_2(self):
        d2 = ProvDocument()
        ns_ex = d2.add_namespace("ex", EX2_URI)
        d2.activity(ns_ex["a1"])
        return d2

    def bundle_0(self):
        b = ProvBundle(namespaces={"ex": EX2_URI})
        return b

    def test_add_bundle_simple(self):
        d1 = self.document_1()
        b0 = self.bundle_0()

        def sub_test_1():
            d1.add_bundle(b0)

        self.assertRaises(ProvException, sub_test_1)
        self.assertFalse(d1.has_bundles())

        d1.add_bundle(b0, "ex:b0")
        self.assertTrue(d1.has_bundles())
        self.assertIn(b0, d1.bundles)

        def sub_test_2():
            ex2_b0 = b0.identifier
            d1.add_bundle(ProvBundle(identifier=ex2_b0))

        self.assertRaises(ProvException, sub_test_2)

        d1.add_bundle(ProvBundle(), "ex:b0")
        self.assertEqual(len(d1.bundles), 2)

    def test_add_bundle_document(self):
        d1 = self.document_1()
        d2 = self.document_2()

        def sub_test_1():
            d1.add_bundle(d2)

        self.assertRaises(ProvException, sub_test_1)

        ex2_b2 = d2.valid_qualified_name("ex:b2")
        d1.add_bundle(d2, "ex:b2")
        self.assertEqual(ex2_b2, first(d1.bundles).identifier)
        self.assertNotIn(d2, d1.bundles)
        b2 = ProvBundle()
        b2.update(d2)
        self.assertIn(b2, d1.bundles)

    def test_bundle_requires_an_identifier(self):
        d1 = self.document_1()
        self.assertRaises(ProvException, d1.bundle, None)

    def test_bundle_rejects_unresolvable_identifier(self):
        # No default namespace and an unregistered prefix: valid_qualified_name()
        # returns None, which bundle() must turn into a ProvException.
        d1 = self.document_1()
        self.assertRaises(ProvException, d1.bundle, "bogus:x")

    def test_bundle_rejects_duplicate_identifier(self):
        d1 = self.document_1()
        d1.bundle("ex:b1")
        self.assertRaises(ProvException, d1.bundle, "ex:b1")

    def test_add_bundle_rejects_document_with_nested_bundles(self):
        # A ProvDocument that itself already contains bundles cannot be
        # folded into another document as a single bundle (model.py ~2664).
        d1 = self.document_1()
        d2 = self.document_2()
        d2.bundle("ex:nested").entity("ex:nested-e1")

        self.assertRaises(ProvException, d1.add_bundle, d2)


class TestLiteralRepresentation(unittest.TestCase):
    def test_literal_provn_with_single_quotes(self):
        literal = Literal('{"foo": "bar"}')
        string_rep = literal.provn_representation()
        self.assertTrue('{\\"f' in string_rep)

    def test_literal_provn_with_triple_quotes(self):
        literal = Literal('"""foo\\nbar"""')
        string_rep = literal.provn_representation()
        self.assertTrue('\\"\\"\\"f' in string_rep)


class TestLiteralHandling(unittest.TestCase):
    """Covers the Literal/datatype-parsing helpers (docs/test-gap-checklist.md,
    T13 item under model.py: parse_xsd_datetime, parse_boolean, Literal
    __eq__/__ne__/__hash__, and the langtag-forces-InternationalizedString
    warning)."""

    def test_parse_xsd_datetime_returns_none_on_unparseable_input(self):
        self.assertIsNone(parse_xsd_datetime("not a date at all!!"))

    def test_parse_boolean_variants(self):
        self.assertTrue(parse_boolean("true"))
        self.assertTrue(parse_boolean("1"))
        self.assertFalse(parse_boolean("false"))
        self.assertFalse(parse_boolean("0"))
        self.assertIsNone(parse_boolean("neither"))

    def test_literal_equality_and_hash(self):
        l1 = Literal("hello", datatype=XSD["string"])
        l2 = Literal("hello", datatype=XSD["string"])
        l3 = Literal("bye", datatype=XSD["string"])

        self.assertEqual(l1, l2)
        self.assertNotEqual(l1, l3)
        self.assertEqual(hash(l1), hash(l2))

    def test_literal_not_equal_to_non_literal(self):
        literal = Literal("hello")
        self.assertFalse(literal == "hello")
        self.assertTrue(literal != "hello")

    def test_langtag_forces_internationalizedstring_datatype_with_warning(self):
        with self.assertLogs("prov.model", level="WARNING") as ctx:
            literal = Literal("bonjour", datatype=XSD["string"], langtag="fr")
        self.assertEqual(literal.datatype, PROV_INTERNATIONALIZEDSTRING)
        self.assertTrue(
            any("overridden as" in message for message in ctx.output),
            ctx.output,
        )

    def test_langtag_without_datatype_defaults_to_internationalizedstring(self):
        literal = Literal("bonjour", langtag="fr")
        self.assertEqual(literal.datatype, PROV_INTERNATIONALIZEDSTRING)


class TestAttributeValidationErrors(unittest.TestCase):
    """Covers ProvException paths in ProvRecord.add_attributes()
    (docs/test-gap-checklist.md, T13 item under model.py)."""

    def setUp(self):
        self.doc = ProvDocument()
        self.doc.add_namespace("ex", "http://example.org/")

    def test_identifierless_record_as_qname_attribute_value_raises(self):
        e1 = self.doc.entity("ex:e1")
        a1 = self.doc.activity("ex:a1")
        # An anonymous (identifier-less) relation used as the value of an
        # attribute expecting a qualified name (here: attribution's agent).
        anonymous_usage = self.doc.usage(a1, e1)
        self.assertIsNone(anonymous_usage.identifier)

        self.assertRaises(ProvException, self.doc.attribution, e1, anonymous_usage)

    def test_identifierless_record_as_generic_attribute_value_raises(self):
        # Same anonymous-relation value, but through the generic (non-formal)
        # attribute path: _auto_literal_conversion() reduces a ProvRecord to
        # its identifier, which is None here, tripping the "value is None"
        # guard rather than a formal-attribute check.
        e1 = self.doc.entity("ex:e1b")
        a1 = self.doc.activity("ex:a1b")
        anonymous_usage = self.doc.usage(a1, e1)
        self.assertIsNone(anonymous_usage.identifier)

        e2 = self.doc.entity("ex:e2b")
        self.assertRaises(ProvException, e2.add_attributes, {"ex:ref": anonymous_usage})

    def test_unparseable_datetime_formal_attribute_raises(self):
        activity = self.doc.activity("ex:a2")
        self.assertRaises(
            ProvException,
            activity.add_attributes,
            {"prov:startTime": "not a date"},
        )

    def test_conflicting_duplicate_value_raises(self):
        activity = self.doc.activity("ex:a3", startTime=datetime.datetime(2020, 1, 1))
        self.assertRaises(
            ProvException,
            activity.add_attributes,
            {"prov:startTime": datetime.datetime(2020, 1, 2)},
        )

    def test_conflicting_duplicate_value_with_naive_vs_aware_datetime(self):
        # Naive and timezone-aware datetimes for the same single-valued
        # formal attribute still compare as "different" (Python's `!=`
        # between them returns True rather than raising -- confirmed
        # separately: no PROV_ATTRIBUTES value type raises TypeError on
        # `!=`, so the `except TypeError` branch at model.py:521-523 is
        # dead code for any value this library can construct; left
        # deferred per docs/test-gap-checklist.md). This still exercises
        # the duplicate-value ProvException with two "different" datetimes.
        activity = self.doc.activity("ex:a4", startTime=datetime.datetime(2020, 1, 1))
        aware_time = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertRaises(
            ProvException, activity.add_attributes, {"prov:startTime": aware_time}
        )

    def test_record_not_equal_to_non_record(self):
        e1 = self.doc.entity("ex:e1")
        self.assertFalse(e1 == "not a record")
        self.assertNotEqual(e1, object())

    def test_record_value_converted_from_provrecord_for_generic_attribute(self):
        # A ProvRecord used as the value of a *generic* (non-formal) attribute
        # is converted to a QualifiedName via its identifier
        # (_auto_literal_conversion's ProvRecord branch, model.py:415-417).
        e1 = self.doc.entity("ex:e1")
        e2 = self.doc.entity("ex:e2")
        e2.add_attributes({"ex:ref": e1})
        self.assertEqual(e2.get_attribute("ex:ref"), {e1.identifier})


class TestElementIdentifierRequired(unittest.TestCase):
    def test_entity_without_identifier_raises(self):
        doc = ProvDocument()
        self.assertRaises(ProvElementIdentifierRequired, doc.entity, None)

    def test_activity_without_identifier_raises(self):
        doc = ProvDocument()
        self.assertRaises(ProvElementIdentifierRequired, doc.activity, None)

    def test_provelementidentifierrequired_str(self):
        self.assertEqual(
            str(ProvElementIdentifierRequired()),
            "An identifier is missing. All PROV elements require a valid identifier.",
        )

    def test_provexceptioninvalidqualifiedname_str(self):
        exc = ProvExceptionInvalidQualifiedName("bogus")
        self.assertEqual(str(exc), "Invalid Qualified Name: bogus")


class TestRecordMiscProperties(unittest.TestCase):
    """Covers small ProvRecord accessors not otherwise exercised
    (docs/test-gap-checklist.md, T13 item under model.py)."""

    def setUp(self):
        self.doc = ProvDocument()
        self.doc.add_namespace("ex", "http://example.org/")

    def test_get_asserted_types_default_empty(self):
        e1 = self.doc.entity("ex:e1")
        self.assertEqual(e1.get_asserted_types(), set())

    def test_label_falls_back_to_identifier(self):
        e1 = self.doc.entity("ex:e1")
        self.assertEqual(e1.label, str(e1.identifier))

    def test_value_property_default_empty(self):
        e1 = self.doc.entity("ex:e1")
        self.assertEqual(e1.value, set())


class TestElementConvenienceMethods(unittest.TestCase):
    """Exercises the fluent convenience wrappers on ProvEntity/ProvActivity
    that examples.py does not otherwise reach (docs/test-gap-checklist.md,
    T13 item under model.py)."""

    def setUp(self):
        self.doc = ProvDocument()
        self.doc.set_default_namespace("http://example.org/")

    def test_entity_was_invalidated_by(self):
        e1 = self.doc.entity("e1")
        a1 = self.doc.activity("a1")
        result = e1.wasInvalidatedBy(a1)
        self.assertIs(result, e1)
        self.assertTrue(
            any(
                r.get_type().localpart == "Invalidation" for r in self.doc.get_records()
            )
        )

    def test_entity_had_member(self):
        collection = self.doc.entity("collection1")
        member = self.doc.entity("member1")
        result = collection.hadMember(member)
        self.assertIs(result, collection)
        self.assertTrue(
            any(r.get_type().localpart == "Membership" for r in self.doc.get_records())
        )

    def test_activity_was_started_by(self):
        a1 = self.doc.activity("a1")
        trigger = self.doc.entity("trigger1")
        result = a1.wasStartedBy(trigger)
        self.assertIs(result, a1)
        self.assertTrue(
            any(r.get_type().localpart == "Start" for r in self.doc.get_records())
        )

    def test_activity_was_ended_by(self):
        a1 = self.doc.activity("a1")
        trigger = self.doc.entity("trigger1")
        result = a1.wasEndedBy(trigger)
        self.assertIs(result, a1)
        self.assertTrue(
            any(r.get_type().localpart == "End" for r in self.doc.get_records())
        )

    def test_activity_was_informed_by(self):
        a1 = self.doc.activity("a1")
        a2 = self.doc.activity("a2")
        result = a1.wasInformedBy(a2)
        self.assertIs(result, a1)
        self.assertTrue(
            any(
                r.get_type().localpart == "Communication"
                for r in self.doc.get_records()
            )
        )

    def test_activity_set_time_both(self):
        a1 = self.doc.activity("a1")
        start = datetime.datetime(2020, 1, 1)
        end = datetime.datetime(2020, 1, 2)
        a1.set_time(startTime=start, endTime=end)
        self.assertEqual(a1.get_startTime(), start)
        self.assertEqual(a1.get_endTime(), end)

    def test_activity_set_time_start_only(self):
        a1 = self.doc.activity("a1")
        start = datetime.datetime(2020, 1, 1)
        a1.set_time(startTime=start)
        self.assertEqual(a1.get_startTime(), start)
        self.assertIsNone(a1.get_endTime())

    def test_activity_set_time_end_only(self):
        a1 = self.doc.activity("a1")
        end = datetime.datetime(2020, 1, 2)
        a1.set_time(endTime=end)
        self.assertIsNone(a1.get_startTime())
        self.assertEqual(a1.get_endTime(), end)


class TestNamespaceManagerEdges(unittest.TestCase):
    """Covers NamespaceManager branches not exercised by round-trip
    serialization (docs/test-gap-checklist.md, T13 item under model.py)."""

    def test_construction_without_default_namespace(self):
        nm = NamespaceManager()
        self.assertIsNone(nm.get_default_namespace())

    def test_get_namespace_miss_and_hit(self):
        nm = NamespaceManager()
        self.assertIsNone(nm.get_namespace("http://example.org/"))
        ns = Namespace("ex", "http://example.org/")
        nm.add_namespace(ns)
        self.assertEqual(nm.get_namespace("http://example.org/"), ns)

    def test_add_namespace_reuses_renamed_namespace_from_cache(self):
        nm = NamespaceManager()
        nm.add_namespace(Namespace("ex", "http://a.example.org/"))
        conflicting = Namespace("ex", "http://b.example.org/")
        first_add = nm.add_namespace(conflicting)
        # Prefix conflict: the second namespace is registered under a new
        # ("ex_1") prefix and cached in the rename map.
        self.assertEqual(first_add.prefix, "ex_1")
        # Adding the *same* conflicting namespace object again should reuse
        # the cached renamed namespace (the `namespace in self._rename_map`
        # branch) rather than renaming it again.
        second_add = nm.add_namespace(conflicting)
        self.assertIs(second_add, first_add)

    def test_valid_qualified_name_rejects_blank_node_and_bad_types(self):
        nm = NamespaceManager()
        self.assertIsNone(nm.valid_qualified_name("_:blank1"))
        self.assertIsNone(nm.valid_qualified_name(12345))

    def test_get_anonymous_identifier_increments_and_uses_prefix(self):
        nm = NamespaceManager()
        first_id = nm.get_anonymous_identifier()
        second_id = nm.get_anonymous_identifier("custom")
        self.assertNotEqual(str(first_id), str(second_id))
        self.assertTrue(str(second_id).startswith("_:custom"))

    def test_get_unused_prefix_counts_up(self):
        nm = NamespaceManager()
        nm.add_namespace(Namespace("ex", "http://a.example.org/"))
        # Force two successive conflicts on the same prefix so
        # _get_unused_prefix must count past "ex_1".
        second = nm.add_namespace(Namespace("ex", "http://b.example.org/"))
        third = nm.add_namespace(Namespace("ex", "http://c.example.org/"))
        self.assertEqual(second.prefix, "ex_1")
        self.assertEqual(third.prefix, "ex_2")

    def test_construction_with_default_namespace(self):
        nm = NamespaceManager(default="http://example.org/")
        default_ns = nm.get_default_namespace()
        self.assertIsNotNone(default_ns)
        self.assertEqual(default_ns.uri, "http://example.org/")

    def test_add_namespaces_with_empty_collection_is_a_no_op(self):
        nm = NamespaceManager()
        nm.add_namespaces([])
        self.assertEqual(list(nm.get_registered_namespaces()), [])

    def test_get_unused_prefix_returns_original_when_available(self):
        # _get_unused_prefix() is only ever called internally once its
        # caller (add_namespace) has already confirmed a conflict, so this
        # "prefix is actually free" branch is otherwise unreachable; call
        # the helper directly to cover it.
        nm = NamespaceManager()
        self.assertEqual(nm._get_unused_prefix("neverused"), "neverused")


class TestProvBundleEdges(unittest.TestCase):
    """Covers ProvBundle API edges not reached by round-trip serialization
    (docs/test-gap-checklist.md, T13 item under model.py)."""

    def test_bundles_property_raises_on_a_plain_bundle(self):
        b = ProvBundle()
        with self.assertRaises(ProvException):
            list(b.bundles)

    def test_standalone_bundle_properties(self):
        b = ProvBundle()
        self.assertEqual(b.records, [])
        self.assertIsNone(b.identifier)
        self.assertIsNone(b.document)

    def test_add_namespace_without_uri_raises(self):
        b = ProvBundle()
        self.assertRaises(ProvException, b.add_namespace, "ex")

    def test_mandatory_valid_qname_failure(self):
        b = ProvBundle()
        self.assertRaises(
            ProvExceptionInvalidQualifiedName, b.mandatory_valid_qname, None
        )

    def test_eq_early_out_for_non_bundle(self):
        b = ProvBundle()
        self.assertFalse(b == "not a bundle")
        self.assertNotEqual(b, 42)

    def test_default_ns_uri_present_and_absent(self):
        b = ProvBundle()
        self.assertIsNone(b.default_ns_uri)
        b.set_default_namespace("http://example.org/")
        self.assertEqual(b.default_ns_uri, "http://example.org/")

    def test_get_registered_namespaces(self):
        b = ProvBundle()
        b.add_namespace("ex", "http://example.org/")
        uris = {ns.uri for ns in b.get_registered_namespaces()}
        self.assertIn("http://example.org/", uris)

    def test_has_bundles_false_for_plain_bundle(self):
        b = ProvBundle()
        self.assertFalse(b.has_bundles())


class TestSerializeDeserializeEdgeCases(unittest.TestCase):
    """Covers ProvDocument.serialize()'s file-path save path and
    .deserialize()'s argument-validation error (docs/test-gap-checklist.md,
    T13 item under model.py, natural neighbours of the T12 read() tests)."""

    def test_serialize_to_file_path_uses_tempfile_and_move(self):
        doc = ProvDocument()
        doc.add_namespace("ex", "http://example.org/")
        doc.entity("ex:e1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.json")
            result = doc.serialize(destination=path, format="json")
            self.assertIsNone(result)
            self.assertTrue(os.path.exists(path))
            reloaded = ProvDocument.deserialize(path, format="json")
            self.assertEqual(reloaded, doc)

    def test_deserialize_without_source_or_content_raises_type_error(self):
        self.assertRaises(TypeError, ProvDocument.deserialize)


class TestDocumentEqualityAndUnification(unittest.TestCase):
    """Covers ProvDocument.__eq__'s bundle-comparison early-outs and
    unified()'s no-bundles loop (docs/test-gap-checklist.md, T13 item under
    model.py)."""

    def test_not_equal_when_other_is_missing_a_bundle(self):
        d1 = ProvDocument()
        d1.set_default_namespace("http://example.org/")
        d1.bundle("b1").entity("e1")

        d2 = ProvDocument()
        d2.set_default_namespace("http://example.org/")

        self.assertNotEqual(d1, d2)

    def test_not_equal_when_matching_bundle_content_differs(self):
        d1 = ProvDocument()
        d1.set_default_namespace("http://example.org/")
        d1.bundle("b1").entity("e1")

        d2 = ProvDocument()
        d2.set_default_namespace("http://example.org/")
        d2.bundle("b1").entity("e2")

        self.assertNotEqual(d1, d2)

    def test_unified_with_no_bundles(self):
        doc = ProvDocument()
        doc.add_namespace("ex", "http://example.org/")
        doc.entity("ex:e1")

        unified = doc.unified()

        self.assertEqual(list(unified.bundles), [])
        self.assertEqual(unified, doc)


@unittest.skipUnless(shutil.which("dot"), "graphviz 'dot' binary not available")
class TestPlot(unittest.TestCase):
    """Covers ProvDocument.plot()'s filename-based save path and its
    unknown-format ValueError (docs/test-gap-checklist.md, T13 item under
    model.py; the matplotlib/interactive-display path remains deferred, see
    checklist)."""

    def setUp(self):
        self.doc = ProvDocument()
        self.doc.add_namespace("ex", "http://example.org/")
        self.doc.entity("ex:e1")

    def test_plot_to_filename_infers_format_and_saves(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.png")
            self.doc.plot(filename=path)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 0)

    def test_plot_unknown_format_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.not-a-real-format")
            self.assertRaises(ValueError, self.doc.plot, filename=path)


class AllTestsBase(
    TestExamplesBase, TestStatementsBase, TestAttributesBase, TestQualifiedNamesBase
):
    """This is a test to include all available tests."""

    pass


class RoundTripModelTest(RoundTripTestCase, AllTestsBase):
    def assertRoundTripEquivalence(self, prov_doc, msg=None):
        """Exercises prov.model without the actual serialization and PROV-N
        generation.
        """
        provn_content = prov_doc.get_provn()
        # Checking for self-equality
        self.assertEqual(
            prov_doc, prov_doc, "The document is not self-equal:\n" + provn_content
        )


if __name__ == "__main__":
    unittest.main()

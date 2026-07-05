import unittest

from prov.identifier import Identifier, Namespace


class TestNamespace(unittest.TestCase):
    """Exercises prov.identifier.Namespace edges not otherwise covered by the
    serializer round-trip tests (docs/test-gap-checklist.md, T13)."""

    def test_namespace_rejects_empty_uri(self):
        with self.assertRaises(ValueError):
            Namespace("ex", "")

    def test_namespace_rejects_whitespace_only_uri(self):
        with self.assertRaises(ValueError):
            Namespace("ex", "   ")

    def test_contains_with_matching_str(self):
        ns = Namespace("ex", "http://example.org/")
        self.assertTrue(ns.contains("http://example.org/thing"))

    def test_contains_with_matching_identifier(self):
        ns = Namespace("ex", "http://example.org/")
        self.assertTrue(ns.contains(Identifier("http://example.org/thing")))

    def test_contains_with_non_matching_uri(self):
        ns = Namespace("ex", "http://example.org/")
        self.assertFalse(ns.contains("http://other.org/thing"))

    def test_contains_with_non_str_non_identifier_returns_false(self):
        ns = Namespace("ex", "http://example.org/")
        self.assertFalse(ns.contains(12345))

    def test_qname_for_contained_str(self):
        ns = Namespace("ex", "http://example.org/")
        qname = ns.qname("http://example.org/thing")
        self.assertEqual(str(qname), "ex:thing")

    def test_qname_for_contained_identifier(self):
        ns = Namespace("ex", "http://example.org/")
        qname = ns.qname(Identifier("http://example.org/thing"))
        self.assertEqual(str(qname), "ex:thing")

    def test_qname_for_non_contained_uri_returns_none(self):
        ns = Namespace("ex", "http://example.org/")
        self.assertIsNone(ns.qname("http://other.org/thing"))

    def test_qname_for_non_str_non_identifier_returns_none(self):
        ns = Namespace("ex", "http://example.org/")
        self.assertIsNone(ns.qname(12345))


if __name__ == "__main__":
    unittest.main()

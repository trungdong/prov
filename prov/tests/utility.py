import logging
import unittest

from prov.model import ProvDocument

try:
    from cStringIO import StringIO
    assert StringIO
except ImportError:
    from StringIO import StringIO
    assert StringIO


logger = logging.getLogger(__name__)


class BaseTestCase(unittest.TestCase):
    def assertIsInstance(self, obj, cls, msg=None):
        """Python < v2.7 compatibility.  Assert isinstance(obj, cls)"""
        try:
            f = super(BaseTestCase, self).assertIsInstance
        except AttributeError:
            self.assertTrue(isinstance(obj, cls), msg)
        else:
            f(obj, cls, msg)

    def assertIsNotNone(self, obj, *args, **kwargs):
        """Python < v2.7 compatibility.  Assert 'a' in 'b'"""
        try:
            f = super(BaseTestCase, self).assertIsNotNone
        except AttributeError:
            self.assertTrue(obj is not None, *args, **kwargs)
        else:
            f(obj, *args, **kwargs)

    def assertIn(self, a, b, *args, **kwargs):
        """Python < v2.7 compatibility.  Assert 'a' in 'b'"""
        try:
            f = super(BaseTestCase, self).assertIn
        except AttributeError:
            self.assertTrue(a in b, *args, **kwargs)
        else:
            f(a, b, *args, **kwargs)

    def assertNotIn(self, a, b, *args, **kwargs):
        """Python < v2.7 compatibility.  Assert 'a' NOT in 'b'"""
        try:
            f = super(BaseTestCase, self).assertNotIn
        except AttributeError:
            self.assertFalse(a in b, *args, **kwargs)
        else:
            f(a, b, *args, **kwargs)

    def assertLess(self, a, b, *args, **kwargs):
        """Python < v2.7 compatibility.  Assert a < b"""
        try:
            f = super(BaseTestCase, self).assertLess
        except AttributeError:
            self.assertTrue(a < b, *args, **kwargs)
        else:
            f(a, b, *args, **kwargs)


class RoundTripTestCase(BaseTestCase):
    FORMAT = 'json'  # default to PROV-JSON

    def assertRoundTripEquivalence(self, prov_doc, msg=None):
        json_str = prov_doc.serialize(format=self.FORMAT, indent=4)
        prov_doc_new = ProvDocument.deserialize(content=json_str, format=self.FORMAT)
        self.assertEqual(prov_doc, prov_doc_new, msg)

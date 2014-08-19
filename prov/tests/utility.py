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
    """A serializer test should subclass this class and set the class property FORMAT to the correct value (e.g.
    'json', 'xml', 'rdf').
    """
    FORMAT = None  # a subclass should change this

    def assertRoundTripEquivalence(self, prov_doc, msg=None):
        if self.FORMAT is None:
            # This is a dummy test, just return
            return

        serialized_content = prov_doc.serialize(format=self.FORMAT, indent=4)
        prov_doc_new = ProvDocument.deserialize(content=serialized_content, format=self.FORMAT)
        msg_extra = u"'%s' serialization content:\n%s" % (self.FORMAT, serialized_content)
        msg = u'\n'.join((msg, msg_extra)) if msg else msg_extra
        self.assertEqual(prov_doc, prov_doc_new, msg)

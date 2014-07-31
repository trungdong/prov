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


class BaseRoundTripTest(unittest.TestCase):
    def setUp(self):
        # a dictionary to hold test documents
        self._documents = dict()

    def write(self, document, fp):
        pass

    def read(self, fp):
        return None

    def compare_documents(self, doc_1, doc_2):
        # Self equality check
        self.assertEqual(doc_1, doc_1)
        self.assertEqual(doc_2, doc_2)
        # PROV-N output
        logger.debug(doc_1.get_provn())
        # Equality check
        try:
            self.assertEqual(doc_1, doc_2)
        except AssertionError, e:
            logger.info(u'---- Document 1 ----\n' + doc_1.get_provn())
            logger.info(u'---- Document 2 ----\n' + doc_2.get_provn())
            # Re-raise the exception
            raise e

    def run_roundtrip_test_document(self, document):
        stream = StringIO()
        self.write(document, stream)
        stream.seek(0)
        doc_2 = self.read(stream)
        self.compare_documents(document, doc_2)


class ProvJSONRoundTripTest(BaseRoundTripTest):
    def write(self, document, fp):
        document.serialize(fp)

    def read(self, fp):
        return ProvDocument.deserialize(fp)


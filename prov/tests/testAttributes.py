import unittest
import logging
from prov.model import *

logger = logging.getLogger(__name__)


class RoundTripTest(unittest.TestCase):
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


EX_NS = Namespace('ex', 'http://example.org/')
EX_OTHER_NS = Namespace('other', 'http://example.org/')
EX2_NS = Namespace('ex2', 'http://example2.org/')
EX3_URI = 'http://example3.org/'


class TestAttributes(RoundTripTest):
    attribute_values_small = [
        "un lieu",
        Literal("un lieu", langtag='fr'),
        Literal("a place", datatype=XSD_STRING, langtag='en')
    ]

    attribute_values_long = [
        "un lieu",
        Literal("un lieu", langtag='fr'),
        Literal("a place", datatype=XSD_STRING, langtag='en'),
        Literal(1, XSD_INT),
        Literal(1, XSD_LONG),
        Literal(1, XSD_SHORT),
        Literal(2.0, XSD_DOUBLE),
        Literal(1.0, XSD_FLOAT),
        Literal(10, XSD_DECIMAL),
        True,
        False,
        Literal(10, XSD_BYTE),
        Literal(10, XSD_UNSIGNEDINT),
        Literal(10, XSD_UNSIGNEDLONG),
        Literal(10, XSD_INTEGER),
        Literal(10, XSD_UNSIGNEDSHORT),
        Literal(10, XSD_NONNEGATIVEINTEGER),
        Literal(-10, XSD_NONPOSITIVEINTEGER),
        Literal(10, XSD_POSITIVEINTEGER),
        Literal(10, XSD_UNSIGNEDBYTE),
        Identifier('http://example.org'),
        Literal('http://example.org', XSD_ANYURI),
        EX_NS['abc'],
        EX_OTHER_NS['abcd'],
        Namespace('ex', 'http://example4.org/')['zabc'],
        Namespace('other', 'http://example4.org/')['zabcd'],

        datetime.datetime.now(),
        Literal(datetime.datetime.now().isoformat(), XSD_DATETIME)
    ]

    def write(self, document, fp):
        document.serialize(fp)

    def read(self, fp):
        return ProvDocument.deserialize(fp)

    def new_document(self):
        return ProvDocument()

    def run_entity_with_one_type_attribute(self, n):
        document = self.new_document()
        document.entity(EX_NS['et%d' % n], {'prov:type': self.attribute_values_long[n]})
        self.run_roundtrip_test_document(document)

    def test_entity_with_one_type_attribute_0(self):
        self.run_entity_with_one_type_attribute(0)

    def test_entity_with_one_type_attribute_1(self):
        self.run_entity_with_one_type_attribute(1)

    def test_entity_with_one_type_attribute_2(self):
        self.run_entity_with_one_type_attribute(2)

    def test_entity_with_one_type_attribute_3(self):
        self.run_entity_with_one_type_attribute(3)

    def test_entity_with_one_type_attribute_4(self):
        self.run_entity_with_one_type_attribute(4)

    def test_entity_with_one_type_attribute_5(self):
        self.run_entity_with_one_type_attribute(5)

    def test_entity_with_one_type_attribute_6(self):
        self.run_entity_with_one_type_attribute(6)

    def test_entity_with_one_type_attribute_7(self):
        self.run_entity_with_one_type_attribute(7)

    def test_entity_with_one_type_attribute_8(self):
        self.run_entity_with_one_type_attribute(8)

    def test_entity_with_one_type_attribute_9(self):
        self.run_entity_with_one_type_attribute(9)

    def test_entity_with_one_type_attribute_10(self):
        self.run_entity_with_one_type_attribute(10)

    def test_entity_with_one_type_attribute_11(self):
        self.run_entity_with_one_type_attribute(11)

    def test_entity_with_one_type_attribute_12(self):
        self.run_entity_with_one_type_attribute(12)

    def test_entity_with_one_type_attribute_13(self):
        self.run_entity_with_one_type_attribute(13)

    def test_entity_with_one_type_attribute_14(self):
        self.run_entity_with_one_type_attribute(14)

    def test_entity_with_one_type_attribute_15(self):
        self.run_entity_with_one_type_attribute(15)

    def test_entity_with_one_type_attribute_16(self):
        self.run_entity_with_one_type_attribute(16)

    def test_entity_with_one_type_attribute_17(self):
        self.run_entity_with_one_type_attribute(17)

    def test_entity_with_one_type_attribute_18(self):
        self.run_entity_with_one_type_attribute(18)

    def test_entity_with_one_type_attribute_19(self):
        self.run_entity_with_one_type_attribute(19)

    def test_entity_with_one_type_attribute_20(self):
        self.run_entity_with_one_type_attribute(20)

    def test_entity_with_one_type_attribute_21(self):
        self.run_entity_with_one_type_attribute(21)

    def test_entity_with_one_type_attribute_22(self):
        self.run_entity_with_one_type_attribute(22)

    def test_entity_with_one_type_attribute_23(self):
        self.run_entity_with_one_type_attribute(23)

    def test_entity_with_one_type_attribute_24(self):
        self.run_entity_with_one_type_attribute(24)

    def test_entity_with_one_type_attribute_25(self):
        self.run_entity_with_one_type_attribute(25)

    def test_entity_with_one_type_attribute_26(self):
        self.run_entity_with_one_type_attribute(26)

    def test_entity_with_one_type_attribute_27(self):
        self.run_entity_with_one_type_attribute(27)


if __name__ == '__main__':
    unittest.main()
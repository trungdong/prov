from prov.model import *


EX_NS = Namespace("ex", "http://example.org/")
EX_OTHER_NS = Namespace("other", "http://example.org/")


class TestAttributesBase(object):
    """This is the base class for testing support for various datatypes.
    It is not runnable and needs to be included in a subclass of
    RoundTripTestCase.
    """

    attribute_values = [
        "un lieu",
        Literal("un lieu", langtag="fr"),
        Literal("a place", langtag="en"),
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
        Identifier("http://example.org"),
        Literal("http://example.org", XSD_ANYURI),
        EX_NS["abc"],
        EX_OTHER_NS["abcd"],
        Namespace("ex", "http://example4.org/")["zabc"],
        Namespace("other", "http://example4.org/")["zabcd"],
        datetime.datetime.now(),
        Literal(datetime.datetime.now().isoformat(), XSD_DATETIME),
    ]

    def new_document(self):
        """
        Creates a new document. document.

        Args:
            self: (todo): write your description
        """
        return ProvDocument()

    def run_entity_with_one_type_attribute(self, n):
        """
        Runs a new entity with a new entity type.

        Args:
            self: (todo): write your description
            n: (todo): write your description
        """
        document = self.new_document()
        document.entity(EX_NS["et%d" % n], {"prov:type": self.attribute_values[n]})
        self.do_tests(document)

    def test_entity_with_one_type_attribute_0(self):
        """
        Sets the test test_attribute_entity.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(0)

    def test_entity_with_one_type_attribute_1(self):
        """
        Sets a test type of the test type.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(1)

    def test_entity_with_one_type_attribute_2(self):
        """
        : param test_entity_2.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(2)

    def test_entity_with_one_type_attribute_3(self):
        """
        : param test_entity_type : str

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(3)

    def test_entity_with_one_type_attribute_4(self):
        """
        : param test_entity_type_type_attribute_type : int

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(4)

    def test_entity_with_one_type_attribute_5(self):
        """
        : param test_entity_type_attribute_entity.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(5)

    def test_entity_with_one_type_attribute_6(self):
        """
        : parameter_entity_type_attribute_type :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(6)

    def test_entity_with_one_type_attribute_7(self):
        """
        : param test_entity_type : : return :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(7)

    def test_entity_with_one_type_attribute_8(self):
        """
        Assigns_entity type : class : ~.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(8)

    def test_entity_with_one_type_attribute_9(self):
        """
        : param test_entity_9.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(9)

    def test_entity_with_one_type_attribute_10(self):
        """
        : parameter_entity_type_type : int

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(10)

    def test_entity_with_one_type_attribute_11(self):
        """
        Sets the : attrtype_attribute_entity_type_attribute.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(11)

    def test_entity_with_one_type_attribute_12(self):
        """
        Sets : attr : parameter with_entity.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(12)

    def test_entity_with_one_type_attribute_13(self):
        """
        : param test_entity_type : param test_type :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(13)

    def test_entity_with_one_type_attribute_14(self):
        """
        : param entity_type_attribute_type : none

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(14)

    def test_entity_with_one_type_attribute_15(self):
        """
        : param test_entity_15.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(15)

    def test_entity_with_one_type_attribute_16(self):
        """
        : parameter_entity_16_type.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(16)

    def test_entity_with_one_type_attribute_17(self):
        """
        : param test_type_attribute : : type.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(17)

    def test_entity_with_one_type_attribute_18(self):
        """
        : param test_type_attribute : none

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(18)

    def test_entity_with_one_type_attribute_19(self):
        """
        : param test_entity_19.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(19)

    def test_entity_with_one_type_attribute_20(self):
        """
        : param test_entity_type_attribute : : return :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(20)

    def test_entity_with_one_type_attribute_21(self):
        """
        : param test_type_attribute : none.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(21)

    def test_entity_with_one_type_attribute_22(self):
        """
        : param test_entity_type : : return :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(22)

    def test_entity_with_one_type_attribute_23(self):
        """
        : param test_type : attr : return :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(23)

    def test_entity_with_one_type_attribute_24(self):
        """
        : param entity type with the given type : param : attr_type.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(24)

    def test_entity_with_one_type_attribute_25(self):
        """
        : param test_entity_type_type.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(25)

    def test_entity_with_one_type_attribute_26(self):
        """
        : param test_entity_type_attribute : : return :

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(26)

    def test_entity_with_one_type_attribute_27(self):
        """
        Sets the test type : attr : testentity /. entity_with_type.

        Args:
            self: (todo): write your description
        """
        self.run_entity_with_one_type_attribute(27)

    def test_entity_with_multiple_attribute(self):
        """
        Test for multiple entities in the document.

        Args:
            self: (todo): write your description
        """
        document = self.new_document()
        attributes = [
            (EX_NS["v_%d" % i], value) for i, value in enumerate(self.attribute_values)
        ]
        document.entity(EX_NS["emov"], attributes)
        self.do_tests(document)

    def test_entity_with_multiple_value_attribute(self):
        """
        Test if the document with the given entity.

        Args:
            self: (todo): write your description
        """
        document = self.new_document()
        attributes = [
            ("prov:value", value) for i, value in enumerate(self.attribute_values)
        ]
        document.entity(EX_NS["emv"], attributes)
        self.do_tests(document)

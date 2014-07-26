import inspect
import os
import unittest

import prov.model as prov


EX_NS = ('ex', 'http://example.org/ns/ex#')
EX_TR = ('tr', 'http://example.org/ns/tr#')
EX_XSI = ('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

# Most general way to get the path.
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(
    inspect.currentframe()))), "xml")


class ProvXMLSerializationTestCase(unittest.TestCase):
    def test_serialization_example_6(self):
        """
        Test the serialization of example 6 which is a simple entity
        description.
        """
        document = prov.ProvDocument()
        document.add_namespace(*EX_NS)
        document.add_namespace(*EX_TR)
        document.add_namespace(*EX_XSI)

        document.entity("tr:WD-prov-dm-20111215", (
            (prov.PROV_TYPE, prov.Literal("document", prov.XSD_QNAME)),
            ("ex:version", "2")
        ))

        document.serialize(format='xml')

    def test_serialization_example_7(self):
        """
        Test the serialization of example 7 which is a basic activity.
        """
        document = prov.ProvDocument()
        document.add_namespace(*EX_NS)
        document.add_namespace(*EX_XSI)

        document.activity(
            "ex:a1",
            "2011-11-16T16:05:00",
            "2011-11-16T16:06:00", [
            (prov.PROV_TYPE, prov.Literal("ex:edit", prov.XSD_QNAME)),
            ("ex:host", "server.example.org")])

        document.serialize(format='xml')



if __name__ == '__main__':
    unittest.main()
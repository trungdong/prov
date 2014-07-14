"""
Created on July 14, 2014

@author: Trung Dong Huynh
"""
import logging
from prov.tests.utility import BaseTestCase

from prov.model import ProvDocument


logger = logging.getLogger(__name__)


class TestDefaultSerializer(BaseTestCase):
    def test_decoding_unicode_value(self):
        unicode_char = u'\u2019'
        json_content = u'''{
    "prefix": {
        "ex": "http://www.example.org"
    },
    "entity": {
        "ex:unicode_char": {
            "prov:label": "%s"
        }
    }
}''' % unicode_char

        prov_doc = ProvDocument.deserialize(content=json_content)
        e1 = prov_doc.get_record('ex:unicode_char')[0]
        self.assertIn(unicode_char, e1.get_attribute('prov:label'))

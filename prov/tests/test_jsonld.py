from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.tests.utility import RoundTripTestCase
from prov.tests.test_model import AllTestsBase


class RoundTripJSONLDTests(RoundTripTestCase, AllTestsBase):
    FORMAT = 'jsonld'

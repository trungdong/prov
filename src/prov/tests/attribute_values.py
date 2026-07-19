"""Shared attribute-value corpus for the attribute round-trip tests.

`ATTRIBUTE_VALUES` is the canonical list of datatypes exercised by
``test_attributes.py`` (pytest-native) and by the legacy
``TestAttributesBase`` mixin (still consumed by the not-yet-migrated
xml/rdf/dot modules). Keep the entries and their order stable: some tests
(e.g. ``test_attributes.py``, ``test_xml_schema.py``) reference individual
values by index (e.g. index 8 is the ``xsd:decimal`` case).
"""

import datetime

from prov.identifier import Identifier, Namespace
from prov.model import (
    XSD_ANYURI,
    XSD_BYTE,
    XSD_DATETIME,
    XSD_DECIMAL,
    XSD_DOUBLE,
    XSD_FLOAT,
    XSD_INT,
    XSD_INTEGER,
    XSD_LONG,
    XSD_NONNEGATIVEINTEGER,
    XSD_NONPOSITIVEINTEGER,
    XSD_POSITIVEINTEGER,
    XSD_SHORT,
    XSD_UNSIGNEDBYTE,
    XSD_UNSIGNEDINT,
    XSD_UNSIGNEDLONG,
    XSD_UNSIGNEDSHORT,
    Literal,
)

EX_NS = Namespace("ex", "http://example.org/")
EX_OTHER_NS = Namespace("other", "http://example.org/")

ATTRIBUTE_VALUES = [
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

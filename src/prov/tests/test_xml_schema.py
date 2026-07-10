"""Validate PROV-XML output against the W3C PROV-XML schema (roadmap step 30).

Serializes each of the 8 canonical `examples.tests` documents and one document
per entry of the `ATTRIBUTE_VALUES` datatype corpus, then validates the
resulting XML against the vendored `prov.xsd` schema closure
(`src/prov/tests/schemas/`, see that directory's README.md for provenance).

Audit authority: docs/superpowers/specs/2026-07-10-conformance-audit-findings.md
section 3.1.
"""

from io import BytesIO
from pathlib import Path

import pytest

etree = pytest.importorskip("lxml.etree")

from prov.model import ProvDocument  # noqa: E402
from prov.tests import examples  # noqa: E402
from prov.tests.attribute_values import ATTRIBUTE_VALUES, EX_NS  # noqa: E402

SCHEMA_DIR = Path(__file__).parent / "schemas"

# --- Triage: schema/spec limitations (documented skips, not prov bugs) ------
#
# PROV-XML's `prov:id`/`prov:ref` attributes are typed `xsd:QName`, whose
# local part must be a valid NCName -- stricter than PROV-N's QualifiedName,
# which allows arbitrary local-name characters (e.g. "/"). The spec itself
# acknowledges this gap ("valid identifier values in PROV-N serializations
# have [the] potential to not be valid identifier values in PROV-XML",
# https://www.w3.org/TR/prov-xml/) and recommends identifier schemes that
# avoid it -- it does not require implementations to work around it. The
# "W3C Publication 1" example (ported verbatim from the ProvToolbox test
# corpus) uses the real-world identifier `chairs:2011OctDec/0004`, whose
# local part contains "/" and is therefore not representable as PROV-XML at
# all, by design of the format -- not a defect in this library's serializer.
QNAME_LOCAL_PART_SKIP = pytest.mark.skip(
    reason="PROV-XML spec limitation: xsd:QName local names are stricter than "
    "PROV-N QualifiedNames (e.g. no '/'); 'chairs:2011OctDec/0004' has no valid "
    "PROV-XML representation -- see https://www.w3.org/TR/prov-xml/"
)

# The PROV-XML schema (prov-core.xsd) only gives `prov:label` the
# `prov:InternationalizedString` complex type (a string plus optional
# `xml:lang`); `prov:type`, `prov:role`, `prov:location`, and `prov:value`
# are all plain `xs:anySimpleType`, which does not permit an `xml:lang`
# attribute. A language-tagged `prov:type` value (PROV-DM permits language
# tags on any attribute) therefore has no valid PROV-XML representation --
# a schema limitation, not something this library's serializer could fix by
# changing how it writes `prov:type`.
LANG_TAG_ON_NON_LABEL_SKIP = pytest.mark.skip(
    reason="PROV-XML schema limitation: only prov:label is typed "
    "prov:InternationalizedString (xml:lang-capable); prov:type/role/location/value "
    "are xs:anySimpleType, which disallows xml:lang"
)

# --- Triage: filed defects (strict xfails) -----------------------------------

INT_MAGNITUDE_XFAIL = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="#244: PROV-XML conformance -- plain Python ints are always typed "
    "xsd:int regardless of magnitude, so values outside the int32 range "
    "serialize as schema-invalid PROV-XML",
)

_EXAMPLE_MARKS = {
    "W3C Publication 1": QNAME_LOCAL_PART_SKIP,
    "datatypes": INT_MAGNITUDE_XFAIL,
}

_ATTRIBUTE_VALUE_MARKS = {
    1: LANG_TAG_ON_NON_LABEL_SKIP,  # Literal("un lieu", langtag="fr")
    2: LANG_TAG_ON_NON_LABEL_SKIP,  # Literal("a place", langtag="en")
}


@pytest.fixture(scope="module")
def prov_xml_schema():
    return etree.XMLSchema(etree.parse(str(SCHEMA_DIR / "prov.xsd")))


def _validate(schema, document):
    xml_bytes = document.serialize(format="xml").encode("utf-8")
    schema.assert_(etree.parse(BytesIO(xml_bytes)))


@pytest.mark.parametrize(
    "make_document",
    [
        pytest.param(fn, id=name, marks=_EXAMPLE_MARKS.get(name, ()))
        for name, fn in examples.tests
    ],
)
def test_example_documents_validate_against_prov_xsd(prov_xml_schema, make_document):
    _validate(prov_xml_schema, make_document())


@pytest.mark.parametrize(
    "index",
    [
        pytest.param(i, marks=_ATTRIBUTE_VALUE_MARKS.get(i, ()))
        for i in range(len(ATTRIBUTE_VALUES))
    ],
)
def test_attribute_values_validate_against_prov_xsd(prov_xml_schema, index):
    document = ProvDocument()
    document.entity(EX_NS["et"], {"prov:type": ATTRIBUTE_VALUES[index]})
    _validate(prov_xml_schema, document)

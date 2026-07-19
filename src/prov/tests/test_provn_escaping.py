"""PROV-N local-part metacharacter escaping (#223, PROV-N [53]/[55])."""

import pytest

from prov.model import ProvDocument

METACHARS = "='(),:;[]"


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


@pytest.mark.parametrize("ch", list(METACHARS))
def test_metachar_local_parts_are_escaped(ch):
    document = _doc()
    document.entity(f"ex:na{ch}me")
    provn = document.get_provn()
    assert f"ex:na\\{ch}me" in provn


def test_issue_repro_escaped_end_to_end():
    document = _doc()
    document.entity("ex:weird'name)x,y")
    assert "entity(ex:weird\\'name\\)x\\,y)" in document.get_provn()


def test_plain_local_parts_unchanged():
    document = _doc()
    document.entity("ex:plain-name_1.x")
    assert "entity(ex:plain-name_1.x)" in document.get_provn()


def test_string_literal_backslash_escaped_before_quotes():
    document = _doc()
    document.entity("ex:e1", {"ex:note": 'back\\slash and "quote"'})
    provn = document.get_provn()
    # backslash must be escaped first, giving an unambiguous \\ followed by \"
    assert '\\\\slash and \\"quote\\"' in provn

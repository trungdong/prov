"""PROV-N output correctness: local-part metacharacter escaping (#223, PROV-N
[53]/[55]) and Mention keyword rendering (#248)."""

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


def test_bundle_identifier_metachar_is_escaped():
    document = _doc()
    bundle = document.bundle("ex:weird'bundle")
    bundle.entity("ex:e1")
    assert "bundle ex:weird\\'bundle" in document.get_provn()


def test_bundle_identifier_plain_unchanged():
    document = _doc()
    bundle = document.bundle("ex:plain-bundle")
    bundle.entity("ex:e1")
    assert "bundle ex:plain-bundle" in document.get_provn()


def test_attribute_name_metachar_is_escaped():
    document = _doc()
    document.entity("ex:e1", {"ex:weird'key": "value"})
    assert '[ex:weird\\\'key="value"]' in document.get_provn()


def test_attribute_name_plain_unchanged():
    document = _doc()
    document.entity("ex:e1", {"ex:plain_key": "value"})
    assert '[ex:plain_key="value"]' in document.get_provn()


def test_mention_bare_keyword_no_prefix():
    """PROV-N Mention emits bare mentionOf(...) without prov: prefix (decision 2026-07-20).

    The PROV-Links specification grammar requires prov:mentionOf, but the bare keyword has
    been the de-facto output of reference implementations for the last decade and matches
    ProvToolbox's ANTLR grammar (PROV_N.g:338), so provconvert keeps parsing prov's output.
    This test locks in the current syntax to prevent silent regressions.
    """
    document = _doc()
    bundle = document.bundle("ex:bundle1")
    bundle.entity("ex:report1bis")
    bundle.mentionOf("ex:report1bis", "ex:report1", "ex:bundle2")
    provn = document.get_provn()

    assert "mentionOf(ex:report1bis, ex:report1, ex:bundle2)" in provn

    # This negative assertion is the one that actually guards the decision, and
    # it is not the redundant twin of the line above: ``mentionOf(`` is a
    # substring of ``prov:mentionOf(``, so a regression to the spec-exact form
    # would still satisfy the positive assertion. Do not remove this as dead
    # weight.
    assert "prov:mentionOf" not in provn

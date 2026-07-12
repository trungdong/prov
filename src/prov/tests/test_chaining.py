"""Record-level chaining convenience methods added by #154.

Each method must (a) produce a document equal to the one built via the
corresponding ProvBundle factory and (b) return self for chaining.
"""

from prov.model import ProvDocument

EX = "http://example.org/"


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", EX)
    return document


def test_entity_wasRevisionOf():
    document = _doc()
    e2 = document.entity("ex:e2")
    assert e2.wasRevisionOf("ex:e1") is e2
    expected = _doc()
    expected.entity("ex:e2")
    expected.revision("ex:e2", "ex:e1")
    assert document == expected


def test_entity_wasQuotedFrom():
    document = _doc()
    e2 = document.entity("ex:e2")
    assert e2.wasQuotedFrom("ex:e1") is e2
    expected = _doc()
    expected.entity("ex:e2")
    expected.quotation("ex:e2", "ex:e1")
    assert document == expected


def test_entity_hadPrimarySource():
    document = _doc()
    e2 = document.entity("ex:e2")
    assert e2.hadPrimarySource("ex:e1") is e2
    expected = _doc()
    expected.entity("ex:e2")
    expected.primary_source("ex:e2", "ex:e1")
    assert document == expected


def test_entity_mentionOf():
    document = _doc()
    e2 = document.entity("ex:e2")
    assert e2.mentionOf("ex:e1", "ex:b") is e2
    expected = _doc()
    expected.entity("ex:e2")
    expected.mention("ex:e2", "ex:e1", "ex:b")
    assert document == expected


def test_entity_wasInfluencedBy():
    document = _doc()
    e2 = document.entity("ex:e2")
    assert e2.wasInfluencedBy("ex:e1") is e2
    expected = _doc()
    expected.entity("ex:e2")
    expected.influence("ex:e2", "ex:e1")
    assert document == expected


def test_activity_wasInfluencedBy():
    document = _doc()
    a2 = document.activity("ex:a2")
    assert a2.wasInfluencedBy("ex:a1") is a2
    expected = _doc()
    expected.activity("ex:a2")
    expected.influence("ex:a2", "ex:a1")
    assert document == expected


def test_agent_wasInfluencedBy():
    document = _doc()
    ag2 = document.agent("ex:ag2")
    assert ag2.wasInfluencedBy("ex:ag1") is ag2
    expected = _doc()
    expected.agent("ex:ag2")
    expected.influence("ex:ag2", "ex:ag1")
    assert document == expected

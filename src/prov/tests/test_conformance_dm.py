"""PROV-DM §5 conformance tests (Phase 3.5 audit, roadmap step 29).

Strict-xfail tests reproduce defects filed by the audit (each reason cites its
issue); characterization tests pin the current permissive behaviour that the
audit recorded for 3.0 triage (findings doc §2.8) without endorsing it.

Audit authority: docs/superpowers/specs/2026-07-10-conformance-audit-findings.md
section 2.
"""

import os
import tempfile

import pytest
from dateutil.parser import ParserError

import prov
from prov.model import (
    PROV_QUALIFIEDNAME,
    PROV_VALUE,
    XSD_LONG,
    Literal,
    ProvDocument,
    ProvException,
)


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


# --- Filed defects (strict xfails) -------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="#235: PROV-DM §5.7.3 — xsd:long literals are silently re-typed as xsd:int",
)
def test_xsd_long_literal_datatype_preserved():
    document = _doc()
    entity = document.entity("ex:e1", {"ex:attr": Literal("42", XSD_LONG)})
    ((_, value),) = entity.extra_attributes
    assert value == Literal("42", XSD_LONG)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "#238: PROV-DM §5.7.3 — prov:QUALIFIED_NAME literals are not resolved to "
        "QualifiedNames, so the JSON round trip mutates the value"
    ),
)
def test_qualified_name_literal_roundtrip_equality():
    document = _doc()
    document.entity("ex:e1", {"ex:a": Literal("ex:v", PROV_QUALIFIEDNAME)})
    content = document.serialize(format="json")
    assert ProvDocument.deserialize(content=content, format="json") == document


@pytest.mark.xfail(
    strict=True,
    raises=ParserError,
    reason=(
        "#237: PROV-DM §5.7.3 — factory time parameters leak raw dateutil "
        "ParserError instead of ProvException"
    ),
)
def test_factory_time_parse_error_raises_prov_exception():
    document = _doc()
    with pytest.raises(ProvException):
        document.activity("ex:a1", startTime="not a date")


@pytest.mark.xfail(
    strict=True,
    raises=ParserError,
    reason=(
        "#237: PROV-DM §5.7.3 — the valid xsd:dateTime hour-24 lexical form is "
        "rejected (dateutil ParserError)"
    ),
)
def test_factory_time_accepts_hour24_datetime():
    document = _doc()
    activity = document.activity("ex:a1", startTime="2011-11-16T24:00:00")
    assert activity.get_startTime() is not None


@pytest.mark.xfail(
    strict=True,
    reason=(
        "#239: prov.read() cannot auto-detect valid PROV-XML (RDF deserializer's "
        "BadSyntax propagates before the XML deserializer is tried)"
    ),
)
def test_read_autodetects_prov_xml(tmp_path):
    document = _doc()
    document.entity("ex:e1")
    path = tmp_path / "doc.xml"
    path.write_text(document.serialize(format="xml"))
    assert prov.read(str(path)) == document


def test_serialize_writes_to_named_temporary_file(tmp_path, monkeypatch):
    # #240 regression: non-io.IOBase writables (e.g. NamedTemporaryFile's
    # _TemporaryFileWrapper proxy) must be treated as streams, not paths.
    monkeypatch.chdir(tmp_path)  # any junk repr-named file would land here
    document = _doc()
    document.entity("ex:e1")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=tmp_path, delete=False
    ) as stream:
        document.serialize(stream, format="json")
        name = stream.name
    assert ProvDocument.deserialize(name, format="json") == document
    junk = [p for p in os.listdir(tmp_path) if p.startswith("<")]
    assert junk == []


def test_deserialize_reads_from_named_temporary_file(tmp_path):
    # #240 (read side): deserialize() had the same isinstance(…, IOBase)
    # test; any object with read() must be accepted as a stream.
    document = _doc()
    document.entity("ex:e1")
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", dir=tmp_path) as stream:
        stream.write(document.serialize(format="json"))
        stream.flush()
        stream.seek(0)
        assert ProvDocument.deserialize(stream, format="json") == document


def test_serialize_xml_to_text_mode_named_temporary_file(tmp_path):
    # #240 as originally filed: text-mode NamedTemporaryFile + format="xml".
    # Beyond the stream-vs-path routing in serialize(), the serializers'
    # text/binary detection (isinstance(stream, io.TextIOBase)) also had to
    # recognise such wrapper objects as text streams.
    pytest.importorskip("lxml")
    document = _doc()
    document.entity("ex:e1")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", dir=tmp_path) as stream:
        document.serialize(stream, format="xml")
        stream.flush()
        assert ProvDocument.deserialize(stream.name, format="xml") == document


# --- Characterization of permissive behaviour (findings doc section 2.8) -----
# These pin the current behaviour; PROV-DM marks it non-conformant but whether
# 3.0 validates, warns, or keeps the status quo is a maintainer decision
# (step 31 triage). No issues filed.


def test_multiple_prov_value_attributes_accepted():
    # 3.0 triage (findings §2.8): PROV-DM §5.7.2.5 allows prov:value at most once
    document = _doc()
    entity = document.entity("ex:e1", {PROV_VALUE: 1})
    entity.add_attributes({PROV_VALUE: 2})
    assert entity.value == {1, 2}


def test_non_string_prov_label_accepted():
    # 3.0 triage (findings §2.8): PROV-DM §5.7.2.1 requires prov:label be a string
    document = _doc()
    entity = document.entity("ex:e1", {"prov:label": 42})
    assert entity.label == "42"


def test_mandatory_formal_attribute_none_silently_dropped():
    # 3.0 triage (findings §2.8): PROV-DM §5.1.3 requires a generated entity;
    # None values are skipped, producing wasGeneratedBy(-, -, -)
    document = _doc()
    record = document.generation(None)  # type: ignore[arg-type]
    assert record.get_provn() == "wasGeneratedBy(-, -, -)"


def test_at_least_one_of_rule_not_enforced():
    # 3.0 triage (findings §2.8): PROV-DM §5.1.3 — at least one of id, activity,
    # time, attributes MUST be present alongside the entity
    document = _doc()
    record = document.generation("ex:e1")
    assert record.get_provn() == "wasGeneratedBy(ex:e1, -, -)"

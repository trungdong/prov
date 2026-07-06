"""Pytest-native shared scaffolding for the round-trip test matrix.

This replaces the ``RoundTripTestCase``/``do_tests`` inheritance machinery for
the migrated shared modules (``test_statements.py``, ``test_attributes.py``,
``test_qnames.py``, ``test_examples.py``). Each shared test builds a document
and hands it to the ``roundtrip`` fixture, which is parametrized over
``SHARED_TARGETS`` so every case runs once per serialization format AND once
under the non-serializing ``model`` target.

The legacy ``utility.py``/``statements.py``/``attributes.py``/``qnames.py``
mixins remain in place for the not-yet-migrated xml/rdf/dot modules; they are
retired in a later migration step.
"""

import io

import pytest

from prov.model import ProvDocument

# Formats that support a full serialize -> deserialize -> compare round trip.
# xml and rdf join in the next migration step.
ROUNDTRIP_FORMATS = ("json",)
# The full target axis: the round-trip formats PLUS a "model" target that
# constructs the document, exercises PROV-N generation, and checks the
# self-equality invariant WITHOUT serialization. The model axis preserves the
# coverage the old RoundTripModelTest provided.
SHARED_TARGETS = ("model", *ROUNDTRIP_FORMATS)


def roundtrip_document(doc: ProvDocument, fmt: str) -> ProvDocument:
    """Serialize ``doc`` to ``fmt`` and read it back."""
    with io.BytesIO() as stream:
        doc.serialize(destination=stream, format=fmt, indent=4)
        stream.seek(0)
        return ProvDocument.deserialize(source=stream, format=fmt)


@pytest.fixture(params=SHARED_TARGETS)
def fmt(request):
    """The target under test — "model" or a serialization format.

    Parametrizes every shared statement/attribute/qname/example case, so each
    runs once per round-trip format AND once under the non-serializing model
    target.
    """
    return request.param


@pytest.fixture
def roundtrip(fmt):
    """Return a ``_check(doc)`` callable that asserts ``doc`` survives its target.

    For a serialization format: serialize -> deserialize -> ``doc == reloaded``.
    For the "model" target: no serialization — force PROV-N generation (proving
    model support for the statement) and assert self-equality. On inequality the
    ``pytest_assertrepr_compare`` hook below renders which records differ.
    """

    def _check(doc: ProvDocument) -> ProvDocument:
        if fmt == "model":
            doc.get_provn()  # exercises PROV-N generation
            assert doc == doc  # self-equality invariant, no serialization
            return doc
        reloaded = roundtrip_document(doc, fmt)
        assert doc == reloaded  # readable diff via the hook below
        return reloaded

    return _check


def pytest_assertrepr_compare(config, op, left, right):
    """Readable diff for ``assert doc == reloaded`` on two ProvDocuments."""
    if op != "==" or not (
        isinstance(left, ProvDocument) and isinstance(right, ProvDocument)
    ):
        return None
    left_recs = {str(r) for r in left.get_records()}
    right_recs = {str(r) for r in right.get_records()}
    only_left = sorted(left_recs - right_recs)
    only_right = sorted(right_recs - left_recs)
    return [
        "ProvDocument == ProvDocument failed:",
        f"  records: {len(left_recs)} left, {len(right_recs)} right",
        f"  in left only  ({len(only_left)}):",
        *(f"    - {r}" for r in only_left),
        f"  in right only ({len(only_right)}):",
        *(f"    + {r}" for r in only_right),
    ]

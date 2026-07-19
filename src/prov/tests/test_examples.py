"""Pytest-native shared example round-trip test.

Migrated from the ``TestExamplesBase`` mixin (in ``test_model.py``): a single
function loops over the canonical ``examples.tests`` documents and round-trips
each, run once per target in ``SHARED_TARGETS``. It is kept as one looping node
per target (not expanded per example) to preserve the collected-count parity
baseline; per-example isolation is a deferred improvement. The legacy mixin
remains for the not-yet-migrated ``test_dot.py``.
"""

from prov.tests import examples


def test_all_examples(roundtrip, fmt):
    for name, build in examples.tests:
        if name == "datatypes" and fmt == "rdf":
            # The "datatypes" example packs a mixed-XSD-datatype attribute set
            # onto one entity -- issue #218's general shape. Its two
            # test_attributes.py reproductions were fixed by #77/#89 (the
            # xsd:decimal literal was their only surviving cause), but this
            # example still loses fidelity for a different reason: its
            # xsd:double value is canonicalised to fewer significant digits
            # by the RDF serializer (100.123456 -> 100.1235). The
            # pre-migration test_rdf.py loop skipped this example outright
            # (`if name in ["datatypes"]: continue`); preserved here, scoped
            # to the rdf target only, pending a dedicated issue.
            continue
        roundtrip(build())

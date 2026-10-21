# Documents written by prov 3.2.3

Each file is a canonical example from `examples.py`, or the attribute corpus
from `attribute_values.py`, serialised by the published `prov==3.2.3` wheel.
`test_written_by_3_2_3.py` reads every file and asserts that the document
equals the one the current release builds from the same source. That is the
compatibility promise of the 3.3.0 release: a document 3.2.3 wrote reads the
same under 3.3.0.

The files are not edited by hand. To regenerate them, run `generate.py` as its
docstring says. The one example that holds `mentionOf` (Bundle2) has no PROV-JSONLD file,
because the submission defines no Mention term. The `.trig` files carry
blank-node labels that differ between runs; the test compares documents, not
bytes.

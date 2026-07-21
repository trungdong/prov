.. :changelog:

History
-------

3.0.0 (unreleased)
^^^^^^^^^^^^^^^^^^
* PROV-XML round trip preserves attributes whose value is the empty string;
  previously they were silently dropped on deserialization (#224)
* PROV-XML serializes attribute names containing characters illegal in an
  XML NCName using the reversible ``_xHHHH_`` escaping convention instead
  of raising ``ValueError``; the deserializer applies the inverse, so such
  names round-trip (#289)
* PROV-O: documents containing multiple same-identifier relations with
  differing formal attributes ("scruffy" statements) are documented as a
  PROV-O representational limitation — they serialize but do not round-trip
  through RDF, and deserializing such RDF now raises an error naming the
  limitation; all other formats are unaffected (#217)
* The PROV-JSON deserializer raises ``ProvJSONException`` on structurally
  malformed input instead of leaking raw ``KeyError``/``AttributeError``
  (#228)
* BREAKING: ``pydot`` and ``networkx`` are no longer unconditional runtime
  dependencies. ``import prov.dot`` now requires the ``dot`` extra
  (``pip install "prov[dot]"``) and ``import prov.graph`` the ``graph``
  extra; without them the import raises ``ModuleNotFoundError`` naming the
  extra to install. The ``plot`` extra now pulls in ``pydot``/``networkx``
  as well, since ``plot()`` renders through ``prov.dot``. Signposted by the
  2.4.0 ``DeprecationWarning`` (now removed); see ``docs/upgrading-3.0.md``.
* BREAKING: the ``rdf`` extra now requires ``rdflib>=7.0.0`` (previously
  ``>=6.0.0``); internally the RDF serializer migrated from the deprecated
  ``ConjunctiveGraph`` to ``Dataset``, with unchanged round-trip behaviour
* BREAKING: ``python-dateutil`` dropped — ``prov`` now has no unconditional
  runtime dependencies. Datetime strings are parsed as ``xsd:dateTime``
  (ISO 8601 plus the hour-24 end-of-day form) via the standard library;
  factory ``time=``/``startTime=``/``endTime=`` parameters raise
  ``ProvException`` on invalid input instead of leaking a raw dateutil
  error, and non-ISO forms previously tolerated by dateutil (e.g.
  ``"Nov 7, 2011"``) are no longer accepted (#237)
* Numeric datatype fidelity: ``Literal`` values typed ``xsd:long`` (and the
  rest of the XSD integer family) keep their asserted datatype instead of
  being silently re-typed ``xsd:int`` (#235); PROV-N output types plain
  integers by magnitude (``xsd:int``/``xsd:long``/``xsd:integer``) so
  out-of-int32 values are no longer emitted as invalid bare int literals
  (#249), and plain floats as full-precision ``xsd:double`` instead of
  ``%g``-truncated ``xsd:float`` (#251)
* PROV-JSON typed literals always encode ``$`` as a string, and plain
  integers are typed by magnitude across PROV-JSON/PROV-XML/PROV-O output
  (``xsd:int``/``xsd:long``/``xsd:integer``), fixing schema-invalid output
  for out-of-int32 values (#244, #246, #256)
* PROV-JSON encodes QualifiedName attribute values as ``xsd:QName`` typed
  literals per the PROV-JSON submission (previously the non-standard
  ``prov:QUALIFIED_NAME``, which remains accepted on input) (#168), and
  ``prov:QUALIFIED_NAME``-typed ``Literal`` values are resolved to
  QualifiedNames at assertion time, restoring round-trip equality (#238)
* Literal semantics: string literals have one canonical serialized form (RDF
  output no longer decorates plain strings with ``^^xsd:string``) (#89);
  ``xsd:decimal`` literals compare and hash in value space (#77); language
  tags compare case-insensitively per RDF 1.1 while preserving their
  original case in output (#259)
* PROV-O (RDF) round-trip fidelity: mixed XSD-datatype attribute sets
  survive deserialization with their asserted datatypes intact (#218), and
  ``xsd:double`` values are emitted at full precision instead of rdflib's
  6-significant-digit canonical form (#225)
* PROV-N output escapes qualified-name local parts per the grammar's
  ``PN_CHARS_ESC`` production, so identifiers containing ``' ( ) , : ; [ ]
  =`` no longer produce invalid PROV-N (#223)
* Internal: the PROV-O (RDF) serializer's encode/decode container functions
  were decomposed into per-record-type dispatch (cyclomatic complexity 81/66
  → under 15 per function), with byte-identical output (#274)
* PROV-O output: anonymous qualified Communication/Attribution/Delegation/
  Influence nodes now carry their influencer property (``prov:activity``/
  ``prov:agent``/``prov:agent``/``prov:influencer``) as the PROV-O
  qualification tables require, and the RDF round trip no longer collapses
  distinct anonymous delegations sharing a (delegate, activity) pair
  (#250, #226)
* PROV-O output emits ``alternateOf`` with the PROV-DM argument order
  (``alt1 prov:alternateOf alt2``); previously subject and object were
  transposed on both write and read (#258)
* PROV-O (RDF) deserialization returns ``xsd:base64Binary`` literals as
  their base64 text; previously the value was wrapped in a Python bytes
  repr (``b'…'``), corrupting the round trip (#288)
* Bundle-local and default namespace prefixes are now bound into RDF
  serialization alongside document-level ones, so turtle/TriG output uses
  the declared prefixes instead of auto-minted ``ns1:``-style fallbacks
  (#96)
* Security: PROV-XML parsing no longer resolves DTD entities and never
  touches the network (``resolve_entities=False``, ``no_network=True``),
  closing an XXE surface on untrusted input (#273)
* PROV-N continues to emit Mention as bare ``mentionOf(...)`` — the
  de-facto syntax of the reference implementations for the last decade —
  rather than the ``prov:mentionOf`` form derivable from the PROV-Links
  note; now documented as a deliberate deviation (#248)
* Test infrastructure: the RDF fixture-comparison helper ``find_diff()`` now
  correctly detects single-triple differences in test assertions (previously
  a one-triple difference was invisible, masking potential regressions in
  fixture expectations) (#304)
* PROV-O (RDF) deserialization now recognizes ``prov:startedAtTime``/
  ``prov:endedAtTime`` asserted directly on a qualified ``prov:Start``/
  ``prov:End`` node and reconciles the value into the relation's formal
  ``prov:time`` attribute; previously it was misfiled as an extra attribute
  named ``prov:startTime``/``prov:endTime`` and the formal attribute was
  left ``None`` (#299)
* PROV-O (RDF) round trip: an anonymous Communication/Attribution/Influence
  relation carrying extra attributes now deserializes back into a single
  record instead of two; the binary triple is reconciled onto the same
  ``prov:qualified*`` node used for the extra attributes, generalising the
  mechanism Delegation/Association already used (#303)
* PROV-O (RDF) round trip: a qualified name whose local part ends in a PROV-N
  metacharacter (``= ' , : ; [ ]``) now deserializes instead of raising
  ``ValueError: Can't split ...``; the decoder resolves the IRI against the
  document's registered namespaces (or splits at the last ``#``/``/`` when the
  namespace is unknown) rather than relying on rdflib's ``compute_qname``,
  which refuses such splits. Encode output is unchanged (#294)

2.5.1 (2026-07-13)
^^^^^^^^^^^^^^^^^^
* ``prov.read()`` polish following 2.5.0's #239: seekable streams are now
  rewound between auto-detection attempts (so e.g. a PROV-XML stream
  auto-detects instead of being consumed by the first candidate); rdflib's
  "does not look like a valid URI" logger noise from swallowed candidate
  attempts is suppressed during auto-detection; and when a ``str``/``bytes``
  source that is not an existing file path fails to parse, the error now
  carries a hint that it was treated as raw content
* Documentation: the PROV-XML and PROV-JSON how-to pages no longer describe
  the pre-2.5.0 ``read()`` auto-detection behaviour (exception whitelist,
  "XML never auto-detects")

2.5.0 (2026-07-13)
^^^^^^^^^^^^^^^^^^
* New record-level chaining convenience methods (#154):
  ``ProvEntity.wasRevisionOf()``, ``.wasQuotedFrom()``, ``.hadPrimarySource()``,
  ``.mentionOf()``, and ``.wasInfluencedBy()`` on ``ProvEntity``,
  ``ProvActivity`` and ``ProvAgent`` — mirroring the existing
  ``e1.wasDerivedFrom(e2)`` style for the remaining relation types
* The PROV-XML deserializer now raises ``ProvXMLException`` when a record's
  child element carries only unrecognised XML attributes, instead of leaking a
  raw ``UnboundLocalError`` or silently reusing the previous attribute's value
  (#254)
* ``ProvDocument.serialize()`` and ``deserialize()`` now accept any writable/
  readable file-like object (e.g. ``tempfile.NamedTemporaryFile``), instead of
  only ``io.IOBase`` instances; previously such destinations were silently
  treated as file paths, writing to a repr-named file in the working
  directory. The serializers' text/binary stream detection now also
  recognises such wrapper objects as text streams (#240)
* ``prov.read()`` fixes (#239): valid PROV-XML is now auto-detected (the RDF
  parser's ``BadSyntax`` no longer aborts detection); a ``str``/``bytes``
  source that is not an existing file path is parsed as raw content, as the
  documentation always advertised; and input that no deserializer can
  meaningfully parse (e.g. an empty file) now raises ``TypeError`` instead of
  silently returning an empty document
* Documentation: the agent-subtype idiom now correctly uses qualified names
  (``PROV["Person"]``) for ``prov:type`` values; the previously documented
  string form asserted a plain string, which does not denote the pre-defined
  PROV type (#236)

2.4.0 (2026-07-06)
^^^^^^^^^^^^^^^^^^
* **Documentation overhaul**: the documentation has been reorganised along the
  Diátaxis framework (tutorials, how-to guides, reference, explanations), with
  new furo/MyST/napoleon/intersphinx tooling behind the Sphinx build. Closes
  #141 (graphics export how-to) and #83 (``prov-convert``/``prov-compare`` CLI
  tools how-to). (#210, #211, #212, #213, #214, #215, #216)
* **Test suite redesigned as pytest-native**: shared statement/attribute/qname
  coverage is now expressed once and parametrized across a document x format
  matrix (json/xml/rdf/model) instead of being copy-pasted per serializer;
  Hypothesis property-based round-trip tests generate documents across the
  full feature set; a malformed-input corpus exercises each deserializer's
  error handling. (#219, #220, #221, #222, #227, #229)
* **``prov.model`` split into a package** (``prov.model.records``,
  ``prov.model.namespaces``, ``prov.model.bundle``) for maintainability, with
  no import-path changes: every historic ``from prov.model import X`` still
  works identically. (#231)
* Minor Makefile/CLAUDE.md cleanup for contributors. (#209)
* The serializer registry now degrades gracefully when the optional ``rdf``
  (``rdflib``) or ``xml`` (``lxml``) extra is not installed: ``import prov``
  and the JSON/PROV-N serializers work in a minimal install, and requesting
  the ``rdf``/``xml`` format raises an informative ``DoNotExist`` naming the
  missing extra instead of a bare ``ModuleNotFoundError``. (#230)
* Deprecation warnings signposting planned 3.0 changes: importing
  ``prov.dot``/``prov.graph`` now emits a ``DeprecationWarning`` naming the
  future ``prov[dot]``/``prov[graph]`` extras those modules will require, and
  ``ProvBundle.unified()``/``ProvDocument.unified()`` emit a ``FutureWarning``
  about the upcoming PROV-CONSTRAINTS unification rework. Both warnings are
  hidden by default (standard ``DeprecationWarning``/``FutureWarning``
  semantics) and link to the new `Upgrading to 3.0
  <https://github.com/trungdong/prov/blob/master/docs/upgrading-3.0.md>`_
  guide, which tables every planned 3.0 change and what to do about it.

2.3.0 (2026-07-05)
^^^^^^^^^^^^^^^^^^
* **Dropped Python 3.9 support; minimum is now Python 3.10** (security fixes
  in transitive dependencies are only released for Python 3.10+) (#189)
* **Widened ``rdflib`` to ``>=6.0.0,<8``** (was ``>=4.2.1,<7``): rdflib 7 now
  supported; the floor rose because 4.2.1 no longer installs on supported
  Pythons (#207)
* Diagnostic improvement: ``DoNotExist`` (serializer lookup) and the CLI's
  ``CLIError`` now set ``__cause__`` via exception chaining, so tracebacks
  show the original error; exception types and messages are unchanged, so
  existing ``except`` blocks are unaffected (#200)
* Whole package passes ``mypy --strict``; ships a ``py.typed`` marker
  (PEP 561) so downstream type-checkers see inline types (#192, #193, #194)
* Coverage raised to 97%, enforced in CI; new tests for the CLI scripts,
  ``prov.read()`` auto-detection, graph interop, and the serializer
  registry (#201, #202, #203, #204)
* Internal code quality: ruff rule families I/C4/SIM/RUF/UP045/UP031 enabled
  and long-standing lint suppressions resolved (#195, #196, #197, #198,
  #199, #200); dependency audit documented in ``docs/dependencies.md``; tox
  removed (use ``uv run --python 3.X pytest`` for local multi-version
  testing) (#205)
* Security hygiene: ``SECURITY.md``, Dependabot version updates, and a
  documented support policy (#190)
* Fixed ReadTheDocs build (Sphinx pinned ``<9``) (#187)

2.2.0 (2026-07-03)
^^^^^^^^^^^^^^^^^^
* Fixed graphical output when a filename is supplied (#164)
* Fixed PROV-XML deserialization when prov is the default namespace (#155)
* New ``plot`` extra: ``pip install prov[plot]`` for matplotlib support (#166)
* Marked as Production/Stable; added Python 3.14 to the test matrix
* Tooling: ruff (lint+format), pytest runner, uv-based CI, automated PyPI
  releases via Trusted Publishing. No public API changes.

2.1.1 (2025-06-24)
^^^^^^^^^^^^^^^^^^
* No change - fixing the previous botched release

2.1.0 (2025-06-24)
^^^^^^^^^^^^^^^^^^
* Added type annotations and mypy checks
* Added support for Python 3.13

2.0.2 (2025-06-07)
^^^^^^^^^^^^^^^^^^
* Removed support for EOL Python 3.8
* Using pyproject.toml for project configurations (instead of setup.py)

2.0.1 (2024-06-10)
^^^^^^^^^^^^^^^^^^
* Removed support for EOL Python 3.6 and 3.7
* Minor documentation update (#153)
* Stopped using deepcopy when duplicating Namespace (#158)
* Restricting rdflib package version to "<7" (#156)
* Raise an exception when an empty URI is registered as a namespace (#142)
* Ensure rdflib 6+ returns bytes when serializing tests (fixed #151)
* Removed fancy label output for bundle

2.0.0 (2020-11-01)
^^^^^^^^^^^^^^^^^^
* Removed support for EOL Python 2
* Testing against Python 3.6+ and Pypy3

1.5.3 (2018-11-20)
^^^^^^^^^^^^^^^^^^
* Reorganised source code to /src
* Added Python 3.7 support
* Removed Python 3.3 support due to end-of-life
* plus minor improvements and bug fixes

1.5.2 (2018-02-06)
^^^^^^^^^^^^^^^^^^
* Fixed association relation in RDF serialisation
* Fixed compatibility with networkx 2.0+

1.5.1 (2017-07-18)
^^^^^^^^^^^^^^^^^^
* Replaced pydotplus with pydot (see #111)
* Fixed datetime and bundle error in RDF serialisation
* Tested against Python 3.6
* Improved documentation

1.5.0 (2016-10-19)
^^^^^^^^^^^^^^^^^^
* Added: Support for `PROV-O <http://www.w3.org/TR/prov-o/>`_ (RDF) serialization and deserialization
* Added: `direction` option for :py:meth:`prov.dot.prov_to_dot`
* Added: :py:meth:`prov.graph.graph_to_prov` to convert a `MultiDiGraph <https://networkx.readthedocs.io/en/stable/reference/classes.multigraph.html>`_ back to a :py:class:`~prov.model.ProvDocument`
* Testing with Python 3.5
* Various minor bug fixes and improvements

1.4.0 (2015-08-13)
^^^^^^^^^^^^^^^^^^
* Changed the type of qualified names to prov:QUALIFIED_NAME (fixed #68)
* Removed XSDQName class and stopped supporting parsing xsd:QName as qualified names
* Replaced pydot dependency with pydotplus
* Removed support for Python 2.6
* Various minor bug fixes and improvements

1.3.2 (2015-06-17)
^^^^^^^^^^^^^^^^^^
* Added: prov-compare script to check equivalence of two PROV files (currently supporting JSON and XML)
* Fixed: deserialising Python 3's bytes objects (issue #67)

1.3.1 (2015-02-27)
^^^^^^^^^^^^^^^^^^
* Fixed unicode issue with deserialising text contents
* Set the correct version requirement for six
* Fixed format selection in prov-convert script

1.3.0 (2015-02-03)
^^^^^^^^^^^^^^^^^^
* Python 3.3 and 3.4 supported
* Updated prov-convert script to support XML output
* Added missing test JSON and XML files in distributions


1.2.0 (2014-12-19)
^^^^^^^^^^^^^^^^^^
* Added: :py:meth:`prov.graph.prov_to_graph` to convert a :py:class:`~prov.model.ProvDocument` to a `MultiDiGraph <https://networkx.readthedocs.io/en/stable/reference/classes.multigraph.html>`_
* Added: PROV-N serializer
* Fixed: None values for empty formal attributes in PROV-N output (issue #60)
* Fixed: PROV-N representation for xsd:dateTime (issue #58)
* Fixed: Unintended merging of Identifier and QualifiedName values
* Fixed: Cloning the records when creating a new document from them
* Fixed: incorrect SoftwareAgent records in XML serialization

1.1.0 (2014-08-21)
^^^^^^^^^^^^^^^^^^
* Added: Support for `PROV-XML <http://www.w3.org/TR/prov-xml/>`_ serialization and deserialization
* A :py:class:`~prov.model.ProvRecord` instance can now be used as the value of an attributes
* Added: convenient assertions methods for :py:class:`~prov.model.ProvEntity`, :py:class:`~prov.model.ProvActivity`, and :py:class:`~prov.model.ProvAgent`
* Added: :py:meth:`prov.model.ProvDocument.update` and :py:meth:`prov.model.ProvBundle.update`
* Fixed: Handling default namespaces of bundles when flattened

1.0.1 (2014-08-18)
^^^^^^^^^^^^^^^^^^
* Added: Default namespace inheritance for bundles
* Fixed: :py:meth:`prov.model.NamespaceManager.valid_qualified_name` did not support :py:class:`~prov.model.XSDQName`
* Added: Convenience :py:func:`prov.read` method with a lazy format detection
* Added: Convenience :py:meth:`~prov.model.ProvBundle.plot` method on the :py:class:`~prov.model.ProvBundle` class (requiring matplotlib).
* Changed: The previous :py:meth:`!add_record` method renamed to :py:meth:`~prov.model.ProvBundle.new_record`
* Added: :py:meth:`~prov.model.ProvBundle.add_record` function which takes one argument, a :py:class:`~prov.model.ProvRecord`, has been added
* Fixed: Document flattening (see :py:meth:`~prov.model.ProvDocument.flattened`)
* Added: :py:meth:`~prov.model.ProvRecord.__hash__` function added to :py:class:`~prov.model.ProvRecord` (**at risk**: to be removed as :py:class:`~prov.model.ProvRecord` is expected to be mutable)
* Added: :py:attr:`~prov.model.ProvRecord.extra_attributes` added to mirror existing :py:attr:`~prov.model.ProvRecord.formal_attributes`

1.0.0 (2014-07-15)
^^^^^^^^^^^^^^^^^^

* The underlying data model has been rewritten and is **incompatible** with pre-1.0 versions.
* References to PROV elements (i.e. entities, activities, agents) in relation records are now QualifiedName instances.
* A document or bundle can have multiple records with the same identifier.
* PROV-JSON serializer and deserializer are now separated from the data model.
* Many tests added, including round-trip PROV-JSON encoding/decoding.
* For changes pre-1.0, see the "Pre-1.0 change log" section below.

Pre-1.0 change log
------------------

0.5.3 (2013-12-13)
^^^^^^^^^^^^^^^^^^
- Changed: Allowed namespaces at bundle level
- Fixed: Only check equality of ProvBundles on asserted records
- Fixed: Some string literals are wrongly converted to QNames
- Updated test cases from ProvToolbox (v4.1)
- Added text explanations for some ProvException subclasses
- Added support for langtag in prov.persistence.LiteralAttribute
- Fixed: Support for prov:InternationalizedString literals
- Fixed: Keep timezone information when parsing xsd:dateTime

0.5.2 (2013-10-18)
^^^^^^^^^^^^^^^^^^
- Added South migrations for prov.persistence
- Fixed: Support for unlimited-length record identifier
- Fixed: Support for unlimited-length URI in namespace
- Fixed: Support for long literals (i.e. longer than 255 characters)
- Fixed: (JSON) Support for membership with multiple members
- Fixed: UnicodeEncodeError error
- Fixed: Support for JSON having records sharing the same identifier
- Fixed: Refactor the flattening code
- Fixed: Parsing XSD dateTime
- Fixed: Triple quoted multi-line string literals in PROV-N
- Added: Support initialising namespaces when creating a ProvBundle

0.5.1 (2013-09-13)
^^^^^^^^^^^^^^^^^^
- Added: JSON membership relation with a single entity (in a list)
- Fixed: Not generating inferred records in JSON encoding.
- Fixed: Generating JSON arrays for multi-value attributes
- Fixed: Comparing unicode literal values (fixed #12)
- Fixed: Returning the identifier of a record if the required attribute type is Identifier
- Fixed: No longer trying to find the actual generalEntity record when creating a Mention record
- Added informative arguments to ProvException classes
- Fixed: Attribute validation does not fail if the attribute is already a ProvRecord

0.5.0 (2013-09-02)
^^^^^^^^^^^^^^^^^^
- Allow inferred records to be retyped when flattening
- prov.model.graph: check if a node of a relation already drawn
- Add get_flattened() function to ProvBundle
- Added: hash functions for Literal and Namespace
- Changed: Add new bundle's namespaces to parent document
- Fixed: prov.persistence only saves namespaces at document level
- Added: is_document() and is_bundle() for ProvBundle
- Fixed: Stop outputting prefix in an bundle's PROV-JSON
- Changed: Removed namespace declarations in example bundles
- Better handling of ids when generating PROV-JSON
- Changed: Bundles cannot have their own namespace prefixes
- When exporting a bundle as a document add namespaces from parent
- Return pdbundle when calling add_prov_bundle
- Fixed support for the default namespace
- Fixed minor bugs.

0.4.9 (2013-08-09)
^^^^^^^^^^^^^^^^^^
- Fixed: Cannot get_label() when self._extra_attributes is None

0.4.8 (2013-08-06)
^^^^^^^^^^^^^^^^^^
- Added: Option to show attributes of relations in DOT graph generation
- Added: option to show attributes of nodes in DOT graph representation
- Added: Convenient methods for (de)serialising PROV-JSON (closes #17)
- Fixed: No longer output inferred records in PROV-N and PROV-JSON
- Fixed: Bundles now can have own namespaces
- Fixed: missing return Literal(...)
- Fixed: Error getting the value and datatype of Literal

0.4.7 (2013-07-10)
^^^^^^^^^^^^^^^^^^
- Changed: Removed out-dated example_graph()
- Changed: Improved mappings between default Python and XSD data types
- Changed: Removed ProvElement as the inferred record for influence
- Changed: Updated examples (primer, bundles1, bundles2)
- Fixed: Removed the duplicated Bundle definition in PROV_RECORD_TYPES
- Added JSON test files from ProvToolbox and a test for loading these
- Changed: Improved Literal equality test
- Added langtag getter to Literal

0.4.6 (2013-04-24)
^^^^^^^^^^^^^^^^^^
- Fixed: Removed the 'activity' attribute from Influence expression
- Fixed: Inferred records couldn't be created when the expected types provided as a list

0.4.5 (2013-03-13)
^^^^^^^^^^^^^^^^^^
- Changed: ProvActivity.set_time() can now accept just one argument. It previously sets the time of the missing argument to None.
- Changed: ProvAgent is now eligible for entity arguments and ProvEntity for agent ones
- Fixed: Producing the right PROV-N representation for float values

0.4.4
^^^^^
- Added float data type support for prov.persistence
- Removed ProvCollection class since collections should be instantiated as entities
- Added get_attribute() and get_value() to ProvRecord
- Changed: Check if an attribute's value is a valid QName and return the QName
- Fixed exception rendering graphs with empty records

0.4.3
^^^^^
- Fixed: PROV-N export - top-level bundle -> document
- Fixed: Bug when renaming prefixes

0.4.2
^^^^^
- Updated graph colors to the PROV style

0.4.1
^^^^^
- Restructured package folder
- Moved to a new repo.
- Fixed: 'memberof' -> 'hadMember'

0.4.0 (2012-10-31)
^^^^^^^^^^^^^^^^^^
- Initial release.

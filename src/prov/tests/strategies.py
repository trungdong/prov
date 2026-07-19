"""Hypothesis strategies that generate valid PROV documents.

These feed ``test_property_roundtrip.py``: the composite ``prov_documents``
strategy builds a :class:`~prov.model.ProvDocument` containing multiple
namespaces, elements (entities/activities/agents) with mixed attribute types,
the full relation set drawn over the generated identifiers, and — optionally —
one named sub-bundle populated the same way.

Every construct generated here is expected to survive a
serialize -> deserialize round trip through *all* deserializable formats
(json, xml, rdf). Known-lossy constructs are deliberately excluded, each with a
comment linking the tracking issue, so that a property failure signals a *new*
bug rather than a documented one. See the exclusions inline below.
"""

import string
from datetime import datetime, timezone

from hypothesis import strategies as st

from prov.identifier import Namespace
from prov.model import ProvBundle, ProvDocument

# A small fixed set of namespaces registered on every generated document, so
# documents exercise multi-namespace prefix handling (criterion 1).
NAMESPACES = {
    "ex": "http://example.org/",
    "ex2": "http://example.com/ns2/",
    "ex3": "http://example.net/ns3#",
}
# Reused to build QualifiedName *attribute values* below; equal (prefix + uri)
# to the "ex" namespace registered on each document, so it resolves cleanly.
EX_NS = Namespace("ex", NAMESPACES["ex"])

# Local parts used for identifiers and prefixes are kept to a simple ascii
# alphabet. #223: PROV-N does not escape qname metacharacters (' ) , ( : ; [ ] =)
# in local parts. PROV-N is write-only and therefore out of the round-trip
# property, but keeping identifier local parts simple avoids depending on that
# behaviour at all. Non-ASCII deliberately lives in the string attribute
# *values* below (criterion 1), never in identifiers.
local_part = st.text(
    alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=8
)

# Text attribute values may contain non-ASCII. Surrogates (Cs) cannot be encoded
# to UTF-8, and control characters (Cc) make the XML writer raise
# ``ValueError: All strings must be XML compatible...`` (an uncaught exception,
# not a serializer behaviour we could round-trip; RDF handles every Cc codepoint
# unchanged). Excluding both is a generation-validity narrowing (not a serializer
# behaviour change) — the values that remain still cover the full non-ASCII range.
# min_size=1: an *empty*-string attribute value is dropped entirely by the XML
# serializer (the attribute vanishes on round trip), while JSON and RDF preserve
# it — #224, a genuine XML round-trip bug deferred to 3.0, excluded here rather
# than fixed under the 2.x output freeze.
text_values = st.text(
    alphabet=st.characters(exclude_categories=("Cs", "Cc")),
    min_size=1,
    max_size=30,
)

attr_values = st.one_of(
    text_values,  # str, including non-ASCII
    # xsd:int range (PROV-DM's canonical datatype for a plain Python int,
    # #249): magnitudes beyond it are excluded because the serializers still
    # tag every plain int xsd:int regardless of magnitude until their
    # magnitude-aware reverse maps land (roadmap step 37), so a generated
    # int outside int32 would round-trip back as a kept xsd:int Literal
    # instead of the original bare int (#235's lossless-collapse rule).
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.booleans(),
    # Floats. PROV types a Python ``float`` as xsd:float (single precision), and
    # RDF canonicalises xsd:float to a short decimal, so an arbitrary float does
    # NOT survive the RDF round trip (e.g. 0.1 and large-magnitude values come
    # back changed) even with width=32 — #225, a genuine RDF float-precision loss
    # deferred to 3.0. JSON/XML keep the full repr and are unaffected. We
    # therefore restrict generation to eighth-step dyadic rationals of modest
    # magnitude (|v| <= 8192): exactly representable in float32 with a short
    # exact decimal, empirically round-tripping cleanly through all three
    # formats while still exercising the xsd:float datatype with fractional
    # values. #77 (no Decimal values are generated) is covered for the same
    # reason: xsd:decimal fidelity is lost through RDF.
    st.integers(min_value=-(8192 * 8), max_value=8192 * 8).map(lambda n: n / 8.0),
    # Timezone-aware UTC datetimes; PROV serialises these as xsd:dateTime.
    st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(2100, 1, 1)).map(
        lambda dt: dt.replace(tzinfo=timezone.utc)
    ),
    # QualifiedName values, drawn from the registered "ex" namespace.
    local_part.map(lambda s: EX_NS[s]),
)


def _attribute_dict(draw) -> dict:
    """Draw a dict of ``ex:<key> -> value`` other-attributes.

    #218: multiple values / mixed datatypes on a *single* attribute key lose
    datatype fidelity through RDF. Using a dict guarantees unique keys, so no
    key is ever emitted twice with differing datatypes.
    """
    keys = draw(st.lists(local_part, min_size=0, max_size=4, unique=True))
    return {f"ex:k{key}": draw(attr_values) for key in keys}


def _draw_ids(draw, tag: str) -> list[str]:
    """Draw a list of unique element identifiers with a role-specific prefix.

    Prefixing by role (``e``/``a``/``g``) keeps entity, activity and agent
    identifiers disjoint even when their local parts collide, so no two
    elements of different kinds ever share an identifier.
    """
    names = draw(st.lists(local_part, min_size=1, max_size=3, unique=True))
    return [f"ex:{tag}{name}" for name in names]


# Optional formal time on time-bearing relations, mirroring the datetime values.
_rel_time = st.one_of(
    st.none(),
    st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(2100, 1, 1)).map(
        lambda dt: dt.replace(tzinfo=timezone.utc)
    ),
)


def _populate(draw, container: ProvBundle) -> list[str]:
    """Add elements and relations to ``container`` (a document or a bundle).

    Returns the entity identifiers drawn for ``container`` so the caller can
    wire up cross-bundle relations (mentionOf) that reference them.
    """
    entities = _draw_ids(draw, "e")
    activities = _draw_ids(draw, "a")
    agents = _draw_ids(draw, "g")
    all_ids = entities + activities + agents

    for eid in entities:
        container.entity(eid, _attribute_dict(draw))
    for aid in activities:
        # Optional start/end times on the activity itself.
        start = draw(_rel_time)
        end = draw(_rel_time)
        container.activity(aid, start, end, _attribute_dict(draw))
    for gid in agents:
        container.agent(gid, _attribute_dict(draw))

    def pick(pool: list[str]) -> str:
        return draw(st.sampled_from(pool))

    def times() -> int:
        return draw(st.integers(min_value=0, max_value=2))

    # The full relation set, drawn over the generated identifiers, all created
    # *without* an explicit relation identifier (anonymous). mentionOf is the one
    # relation not created here: it is inherently cross-bundle (it references
    # another bundle's identifier), so `prov_documents` emits it separately once
    # a sub-bundle has been drawn.
    #
    # #217: PROV-O cannot represent two relations of the same kind between the
    # same primary endpoints that differ only in a *qualifying* formal attribute
    # (e.g. prov:time) — one collapses or loses an attribute on the RDF round
    # trip. Anonymity alone does NOT avoid this. We therefore keep at most one
    # relation of each kind per (endpoint1, endpoint2) pair (the `fresh` guard
    # below), which is exactly the construct #217 tracks; excluding it is a
    # generation-validity narrowing, not a serializer change. The guard is
    # deliberately conservative — broader than #217's exact same-identifier
    # shape — because it also forecloses #226-style collapse: it suppresses e.g.
    # two `association`s sharing (activity, agent) but differing by `plan`.
    # Those non-delegation qualified variants (association `plan`, start/end
    # `starter`/`ender`) were verified to round-trip cleanly, so the guard
    # forecloses #217/#226-style loss without masking any other known bug.
    seen: set[tuple[str, str, str]] = set()

    def fresh(kind: str, e1: str, e2: str) -> bool:
        key = (kind, e1, e2)
        if key in seen:
            return False
        seen.add(key)
        return True

    for _ in range(times()):
        e, a = pick(entities), pick(activities)
        if fresh("gen", e, a):
            container.generation(e, a, time=draw(_rel_time))
    for _ in range(times()):
        a, e = pick(activities), pick(entities)
        if fresh("use", a, e):
            container.usage(a, e, time=draw(_rel_time))
    for _ in range(times()):
        a1, a2 = pick(activities), pick(activities)
        if fresh("com", a1, a2):
            container.communication(a1, a2)
    for _ in range(times()):
        a, e = pick(activities), pick(entities)
        if fresh("start", a, e):
            container.start(a, e, pick(activities), time=draw(_rel_time))
    for _ in range(times()):
        a, e = pick(activities), pick(entities)
        if fresh("end", a, e):
            container.end(a, e, pick(activities), time=draw(_rel_time))
    for _ in range(times()):
        e, a = pick(entities), pick(activities)
        if fresh("inv", e, a):
            container.invalidation(e, a, time=draw(_rel_time))
    for _ in range(times()):
        e1, e2 = pick(entities), pick(entities)
        if fresh("der", e1, e2):
            container.derivation(e1, e2)
    for _ in range(times()):
        e, g = pick(entities), pick(agents)
        if fresh("attr", e, g):
            container.attribution(e, g)
    for _ in range(times()):
        a, g = pick(activities), pick(agents)
        if fresh("assoc", a, g):
            container.association(a, g, pick(entities))
    for _ in range(times()):
        g1, g2 = pick(agents), pick(agents)
        if fresh("deleg", g1, g2):
            # No qualifying activity: #226. Qualified delegation is lost through
            # RDF when two anonymous delegations share the same delegate AND
            # qualifying activity but differ in responsible — the
            # qualifiedDelegation blank nodes are keyed on (delegate, activity),
            # which the endpoint-pair `fresh` guard cannot prevent (distinct from
            # #217, which is about relations sharing an explicit identifier).
            # Every other relation qualifier (relation prov:time,
            # association plan, start/end starter/ender) round-trips fine and is
            # kept. Omitting only delegation's activity keeps the relation type
            # in the corpus without depending on that RDF-lossy construct.
            container.delegation(g1, g2)
    for _ in range(times()):
        x1, x2 = pick(all_ids), pick(all_ids)
        if fresh("infl", x1, x2):
            container.influence(x1, x2)
    for _ in range(times()):
        e1, e2 = pick(entities), pick(entities)
        if fresh("spec", e1, e2):
            container.specialization(e1, e2)
    for _ in range(times()):
        e1, e2 = pick(entities), pick(entities)
        if fresh("alt", e1, e2):
            container.alternate(e1, e2)
    for _ in range(times()):
        e1, e2 = pick(entities), pick(entities)
        if fresh("mem", e1, e2):
            container.membership(e1, e2)

    return entities


@st.composite
def prov_documents(draw) -> ProvDocument:
    """Generate a valid PROV document for round-trip property testing."""
    doc = ProvDocument()
    for prefix, uri in NAMESPACES.items():
        doc.add_namespace(prefix, uri)

    doc_entities = _populate(draw, doc)

    # Optionally one named sub-bundle, populated the same way. When a bundle is
    # drawn, also emit anonymous cross-bundle mentionOf relations completing the
    # 14-relation set: mention(specific, general, bundle) references a
    # document-level entity as the general entity described in the sub-bundle.
    # Guarded on the document having drawn at least one entity.
    if draw(st.booleans()):
        bundle_id = f"ex:b{draw(local_part)}"
        bundle = doc.bundle(bundle_id)
        _populate(draw, bundle)
        if doc_entities:
            for _ in range(draw(st.integers(min_value=0, max_value=2))):
                specific = draw(st.sampled_from(doc_entities))
                general = draw(st.sampled_from(doc_entities))
                doc.mention(specific, general, bundle_id)

    return doc

"""__slots__ and precomputed hashes on Identifier, QualifiedName, Namespace
and Literal: no __dict__, unchanged equality, copy and pickle intact."""

import copy
import os
import pickle
import subprocess
import sys
import weakref

import pytest

from prov.constants import XSD_INT
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import Literal

NS = Namespace("ex", "http://example.org/")
OBJECTS = [
    Identifier("http://example.org/id"),
    NS,
    NS["e1"],
    Literal("1", XSD_INT),
    Literal("un lieu", langtag="fr"),
]


@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_no_instance_dict(obj):
    assert not hasattr(obj, "__dict__")
    with pytest.raises(AttributeError):
        obj.undeclared = 1


@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_copy_preserves_equality(obj):
    assert copy.copy(obj) == obj
    assert copy.deepcopy(obj) == obj


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_pickle_round_trips_under_every_protocol(obj, protocol):
    # Round-trips a value created immediately above, not external input.
    loaded = pickle.loads(pickle.dumps(obj, protocol=protocol))  # nosec B301 - nosemgrep
    assert loaded == obj
    assert hash(loaded) == hash(obj)


def test_unpickled_qualified_name_recomputes_its_hash_in_the_loading_process(tmp_path):
    # The hash is process-specific (str hashing is seeded), so a pickle must
    # not carry it. Produce the pickle under a different seed and look the
    # object up in a dict keyed by a fresh, equal qualified name. The script
    # is a file rather than a "-c" argument, so it is a static string.
    script = tmp_path / "produce_pickle.py"
    script.write_text(
        "import pickle, sys\n"
        "from prov.identifier import Namespace\n"
        "sys.stdout.buffer.write(pickle.dumps(Namespace('ex', 'http://example.org/')['e1']))\n"
    )
    for seed in ("12345", "54321"):
        # The command is the running interpreter plus a script this test
        # just wrote, not untrusted input.
        produced = subprocess.run(  # nosec B603 - nosemgrep
            [sys.executable, str(script)],
            capture_output=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        ).stdout
        loaded = pickle.loads(produced)  # nosec B301 - nosemgrep
        fresh = Namespace("ex", "http://example.org/")["e1"]
        assert loaded == fresh
        assert hash(loaded) == hash(fresh)
        assert {fresh: 1}.get(loaded) == 1


def test_setstate_accepts_a_pre_3_2_dict_state():
    # prov <= 3.1.1 pickled these classes through __dict__; that state has no
    # _hash and Namespace's carries its cache.
    ns = Namespace.__new__(Namespace)
    ns.__setstate__({"_prefix": "ex", "_uri": "http://example.org/", "_cache": {}})
    assert ns == Namespace("ex", "http://example.org/")
    qn = QualifiedName.__new__(QualifiedName)
    qn.__setstate__(
        {
            "_uri": "http://example.org/e1",
            "_namespace": ns,
            "_localpart": "e1",
            "_str": "ex:e1",
        }
    )
    assert qn == ns["e1"]
    assert hash(qn) == hash(ns["e1"])
    lit = Literal.__new__(Literal)
    lit.__setstate__({"_value": "1", "_datatype": XSD_INT, "_langtag": None})
    assert lit == Literal("1", XSD_INT)


@pytest.mark.parametrize(
    ("cls", "slots"),
    [
        (Identifier, {"_hash": 1, "_uri": "http://example.org/e1"}),
        (
            QualifiedName,
            {
                "_hash": 1,
                "_uri": "http://example.org/e1",
                "_namespace": NS,
                "_localpart": "e1",
                "_str": "ex:e1",
            },
        ),
        (Namespace, {"_prefix": "ex", "_uri": "http://example.org/", "_cache": {}}),
        (Literal, {"_value": "1", "_datatype": XSD_INT, "_langtag": None}),
    ],
    ids=lambda v: getattr(v, "__name__", ""),
)
def test_setstate_accepts_the_3_2_0_slotted_state(cls, slots):
    # 3.2.0 had __slots__ without __getstate__, so its pickles carry the
    # (dict_state, slot_state) tuple Python builds for slotted objects.
    obj = cls.__new__(cls)
    obj.__setstate__((None, slots))
    expected = {
        Identifier: Identifier("http://example.org/e1"),
        QualifiedName: NS["e1"],
        Namespace: Namespace("ex", "http://example.org/"),
        Literal: Literal("1", XSD_INT),
    }[cls]
    assert obj == expected
    assert hash(obj) == hash(expected)


@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_weak_references_are_supported(obj):
    assert weakref.ref(obj)() is obj


def test_equal_identifiers_hash_equal_across_classes():
    ident = Identifier("http://example.org/e1")
    qname = NS["e1"]
    assert ident == qname
    assert hash(ident) == hash(qname) == hash("http://example.org/e1")


def test_namespace_cache_still_interns_qualified_names():
    assert NS["e1"] is NS["e1"]

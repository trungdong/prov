"""__slots__ and precomputed hashes on Identifier, QualifiedName, Namespace
and Literal: no __dict__, unchanged equality, copy and pickle intact."""

import copy
import os
import pickle
import subprocess
import sys
import weakref
from pathlib import Path
from typing import Any

import pytest

from prov.constants import XSD_INT
from prov.identifier import Identifier, Namespace, QualifiedName
from prov.model import Literal, ProvDocument

NS = Namespace("ex", "http://example.org/")
OBJECTS = [
    Identifier("http://example.org/id"),
    NS,
    NS["e1"],
    Literal("1", XSD_INT),
    Literal("un lieu", langtag="fr"),
]


@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_no_instance_dict(obj: Any) -> None:
    assert not hasattr(obj, "__dict__")
    with pytest.raises(AttributeError):
        obj.undeclared = 1


@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_copy_preserves_equality(obj: object) -> None:
    assert copy.copy(obj) == obj
    assert copy.deepcopy(obj) == obj


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
@pytest.mark.parametrize("obj", OBJECTS, ids=lambda o: type(o).__name__)
def test_pickle_round_trips_under_every_protocol(obj: object, protocol: int) -> None:
    # Round-trips a value created immediately above, not external input.
    loaded = pickle.loads(pickle.dumps(obj, protocol=protocol))  # nosec B301 - nosemgrep
    assert loaded == obj
    assert hash(loaded) == hash(obj)


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_a_pickled_default_namespace_loads_without_running_init(protocol: int) -> None:
    document = ProvDocument()
    document.set_default_namespace("http://d.example/")
    document.entity("e")
    # Round-trips a value created immediately above, not external input.
    loaded = pickle.loads(pickle.dumps(document, protocol=protocol))  # nosec B301 - nosemgrep
    default = loaded.get_default_namespace()
    assert default is not None
    assert (default.prefix, default.uri) == ("", "http://d.example/")
    assert default == document.get_default_namespace()
    assert loaded == document


def test_unpickled_qualified_name_recomputes_its_hash_in_the_loading_process(
    tmp_path: Path,
) -> None:
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


def test_setstate_accepts_a_pre_3_2_dict_state() -> None:
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
def test_setstate_accepts_the_3_2_0_slotted_state(
    cls: Any, slots: dict[str, object]
) -> None:
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
def test_weak_references_are_supported(obj: object) -> None:
    assert weakref.ref(obj)() is obj


def test_equal_identifiers_hash_equal_across_classes() -> None:
    ident = Identifier("http://example.org/e1")
    qname = NS["e1"]
    assert ident == qname
    assert hash(ident) == hash(qname) == hash("http://example.org/e1")


def test_namespace_cache_still_interns_qualified_names() -> None:
    assert NS["e1"] is NS["e1"]


GUARDED = {
    Identifier: {"_hash", "_uri"},
    QualifiedName: {"_hash", "_uri", "_localpart", "_namespace", "_str"},
    Namespace: {"_cache", "_prefix", "_uri"},
    Literal: {"_datatype", "_langtag", "_value"},
}
GUARDED_PAIRS = [(obj, name) for obj in OBJECTS for name in sorted(GUARDED[type(obj)])]


@pytest.mark.parametrize(
    ("obj", "name"),
    GUARDED_PAIRS,
    ids=lambda v: v if isinstance(v, str) else type(v).__name__,
)
def test_a_guarded_field_refuses_assignment_and_deletion(obj: Any, name: str) -> None:
    message = f"^{type(obj).__name__}\\.{name} is read-only$"
    before, digest, text = getattr(obj, name), hash(obj), str(obj)
    with pytest.raises(AttributeError, match=message):
        setattr(obj, name, before)
    with pytest.raises(AttributeError, match=message):
        delattr(obj, name)
    assert getattr(obj, name) is before
    assert (hash(obj), str(obj)) == (digest, text)


def _slots_across_the_mro(cls: type) -> set[str]:
    declared: set[str] = set()
    for klass in cls.__mro__:
        slots = klass.__dict__.get("__slots__", ())
        declared.update([slots] if isinstance(slots, str) else slots)
    return declared - {"__weakref__"}


@pytest.mark.parametrize("cls", list(GUARDED), ids=lambda c: c.__name__)
def test_read_only_names_are_every_slot(cls: Any) -> None:
    assert _slots_across_the_mro(cls) == cls._READ_ONLY
    assert GUARDED[cls] == cls._READ_ONLY


class _SubIdentifier(Identifier):
    def __init__(self, uri: str) -> None:
        super().__init__(uri)
        self.extra = "i"


class _SubQualifiedName(QualifiedName):
    def __init__(self, namespace: Namespace, localpart: str) -> None:
        super().__init__(namespace, localpart)
        self.extra = "q"


class _SubNamespace(Namespace):
    def __init__(self, prefix: str, uri: str) -> None:
        super().__init__(prefix, uri)
        self.extra = "n"


class _SubLiteral(Literal):
    def __init__(self, value: Any) -> None:
        super().__init__(value)
        self.extra = "l"


@pytest.mark.parametrize(
    ("subclass", "obj", "name"),
    [
        (_SubIdentifier, _SubIdentifier("http://example.org/s"), "_uri"),
        (_SubQualifiedName, _SubQualifiedName(NS, "s"), "_uri"),
        (_SubNamespace, _SubNamespace("sx", "http://s.example/"), "_uri"),
        (_SubLiteral, _SubLiteral("s"), "_value"),
    ],
    ids=lambda v: v if isinstance(v, str) else getattr(v, "__name__", ""),
)
def test_a_subclass_sets_its_own_attributes_and_keeps_the_guard(
    subclass: type, obj: Any, name: str
) -> None:
    assert obj.extra in {"i", "q", "n", "l"}
    obj.extra = "changed"
    assert obj.extra == "changed"
    del obj.extra
    assert not hasattr(obj, "extra")
    message = f"^{subclass.__name__}\\.{name} is read-only$"
    with pytest.raises(AttributeError, match=message):
        setattr(obj, name, "x")
    with pytest.raises(AttributeError, match=message):
        delattr(obj, name)


@pytest.mark.parametrize("name", ["_prefix", "_uri", "_cache"])
def test_a_default_namespace_is_guarded_too(name: str) -> None:
    default = Namespace._default("http://d.example/")
    before = getattr(default, name)
    message = f"^Namespace\\.{name} is read-only$"
    with pytest.raises(AttributeError, match=message):
        setattr(default, name, before)
    with pytest.raises(AttributeError, match=message):
        delattr(default, name)
    assert getattr(default, name) == before


def test_mypy_still_rejects_a_final_write_and_an_undeclared_name() -> None:
    qn: QualifiedName = NS["e1"]
    with pytest.raises(AttributeError):
        qn._uri = "x"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        qn.undeclared = 1  # type: ignore[attr-defined]
    ns: Namespace = NS
    with pytest.raises(AttributeError):
        ns.undeclared = 1  # type: ignore[attr-defined]
    lit: Literal = Literal("1", XSD_INT)
    with pytest.raises(AttributeError):
        lit.undeclared = 1  # type: ignore[attr-defined]

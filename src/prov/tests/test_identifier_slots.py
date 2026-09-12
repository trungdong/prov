"""__slots__ and precomputed hashes on Identifier, QualifiedName, Namespace
and Literal: no __dict__, unchanged equality, copy and pickle intact."""

import copy
import pickle

import pytest

from prov.constants import XSD_INT
from prov.identifier import Identifier, Namespace
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
def test_copy_and_pickle_preserve_equality(obj):
    assert copy.copy(obj) == obj
    assert copy.deepcopy(obj) == obj

    # Round-trips a value created immediately above, not external input.
    assert pickle.loads(pickle.dumps(obj)) == obj  # nosec B301 - nosemgrep


def test_qualified_name_hash_is_stored_and_uri_based():
    qname = NS["e1"]
    assert hash(qname) == hash(qname.uri)
    assert qname._hash == hash(qname)


def test_identifier_hash_unchanged():
    ident = Identifier("http://example.org/e1")
    assert hash(ident) == hash((ident.uri, Identifier))
    assert hash(ident) != hash(NS["e1"])  # class-distinguished, as before


def test_namespace_cache_still_interns_qualified_names():
    assert NS["e1"] is NS["e1"]

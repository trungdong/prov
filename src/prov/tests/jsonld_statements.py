"""Builders for the one-statement PROV-JSONLD documents the reader tests feed in."""

import json
from typing import Any

from prov.serializers.provjsonld import JSONLD_CONTEXT_URL

from .conftest import EX_URI


def statement_dict(kind: str, ident: Any = None, **terms: Any) -> dict[str, Any]:
    """A document under the ``ex`` context holding one statement of type
    ``kind``, with ``"@id"`` ``ident`` unless ``None`` and the keys ``terms``."""
    statement = {"@type": kind, **({} if ident is None else {"@id": ident}), **terms}
    return {"@context": [{"ex": EX_URI}, JSONLD_CONTEXT_URL], "@graph": [statement]}


def statement_of(kind: str, ident: Any = None, **terms: Any) -> str:
    """The document of :func:`statement_dict` as JSON-LD text."""
    return json.dumps(statement_dict(kind, ident, **terms))


def usage_with(ident: str | None = "ex:u1", **terms: Any) -> str:
    """A ``Usage`` of ``ex:e`` by ``ex:a`` whose keys ``terms`` replace or extend
    the formal ones."""
    return statement_of(
        "Usage", ident, **{"activity": "ex:a", "entity": "ex:e"} | terms
    )

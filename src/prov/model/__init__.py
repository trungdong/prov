"""Python implementation of the W3C Provenance Data Model (PROV-DM), including
support for PROV-JSON import/export

References:

PROV-DM: http://www.w3.org/TR/prov-dm/
PROV-JSON: https://openprovenance.org/prov-json/
"""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

import datetime as datetime
import io as io
import itertools as itertools
import logging
import os as os
import shutil as shutil
import tempfile as tempfile
import typing as typing
from collections import defaultdict as defaultdict
from collections.abc import Callable as Callable, Iterable as Iterable
from io import IOBase as IOBase
from typing import Any as Any, Union as Union
from urllib.parse import urlparse as urlparse

import dateutil as dateutil

from prov import Error as Error, serializers as serializers
from prov.constants import *
from prov.identifier import (
    Identifier as Identifier,
    Namespace as Namespace,
    QualifiedName as QualifiedName,
)
from prov.model.bundle import (
    ProvBundle as ProvBundle,
    ProvDocument as ProvDocument,
    sorted_attributes as sorted_attributes,
)
from prov.model.namespaces import (
    DEFAULT_NAMESPACES as DEFAULT_NAMESPACES,
    NamespaceManager as NamespaceManager,
)
from prov.model.records import (
    DATATYPE_PARSERS as DATATYPE_PARSERS,
    PROV_REC_CLS as PROV_REC_CLS,
    XSD_DATATYPE_PARSERS as XSD_DATATYPE_PARSERS,
    ActivityRef as ActivityRef,
    AgentRef as AgentRef,
    DatetimeOrStr as DatetimeOrStr,
    EntityRef as EntityRef,
    GenrationRef as GenrationRef,
    Literal as Literal,
    NameValuePair as NameValuePair,
    NSCollection as NSCollection,
    OptionalID as OptionalID,
    PathLike as PathLike,
    ProvActivity as ProvActivity,
    ProvAgent as ProvAgent,
    ProvAlternate as ProvAlternate,
    ProvAssociation as ProvAssociation,
    ProvAttribution as ProvAttribution,
    ProvCommunication as ProvCommunication,
    ProvDelegation as ProvDelegation,
    ProvDerivation as ProvDerivation,
    ProvElement as ProvElement,
    ProvElementIdentifierRequired as ProvElementIdentifierRequired,
    ProvEnd as ProvEnd,
    ProvEntity as ProvEntity,
    ProvException as ProvException,
    ProvExceptionInvalidQualifiedName as ProvExceptionInvalidQualifiedName,
    ProvGeneration as ProvGeneration,
    ProvInfluence as ProvInfluence,
    ProvInvalidation as ProvInvalidation,
    ProvMembership as ProvMembership,
    ProvMention as ProvMention,
    ProvRecord as ProvRecord,
    ProvRelation as ProvRelation,
    ProvSpecialization as ProvSpecialization,
    ProvStart as ProvStart,
    ProvUsage as ProvUsage,
    ProvWarning as ProvWarning,
    QualifiedNameCandidate as QualifiedNameCandidate,
    RecordAttributesArg as RecordAttributesArg,
    SupportedXSDParsedTypes as SupportedXSDParsedTypes,
    UsageRef as UsageRef,
    encoding_provn_value as encoding_provn_value,
    first as first,
    parse_boolean as parse_boolean,
    parse_xsd_datetime as parse_xsd_datetime,
    parse_xsd_types as parse_xsd_types,
)

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


logger = logging.getLogger(__name__)

# The split into submodules is an implementation detail of the 2.4 refactor:
# remove the submodule attributes that the import system bound on this package
# so that the public namespace (dir(prov.model)) stays identical to the
# pre-split prov/model.py module. `from prov.model.records import ...` (and
# `.namespaces`/`.bundle`) still works via sys.modules; only attribute access
# like `prov.model.records` is hidden, which no historic code could have used.
for _submodule_name in ("bundle", "namespaces", "records"):
    globals().pop(_submodule_name, None)
del _submodule_name

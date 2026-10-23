"""Sphinx configuration for the prov documentation."""

import os
import sys

# Make the src-layout package importable so autodoc and `prov.__version__` work.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import prov

project = "prov"
copyright = "2026, Trung Dong Huynh"
author = "Trung Dong Huynh"
version = prov.__version__
release = prov.__version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
exclude_patterns = [
    "_build",
    # Internal working docs (dependency notes, the release runbook) live under
    # docs/ for convenience but are not part of the published documentation.
    # Design specs and plans live in the top-level planning/ directory.
    "dependencies.md",
    "releasing.md",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
}

autodoc_member_order = "bysource"
# Signatures name these prov.model aliases instead of expanding their unions; model.md
# documents each. Sphinx 9.1 unwraps an alias placeholder only when it is the whole
# annotation; inside ``Alias | None`` the placeholder prints as "TypeAliasForwardRef".
# Giving the placeholder the alias's module and name makes the stringifier print the
# alias.
autodoc_type_aliases = {
    name: name
    for name in (
        "AttributeValue",
        "RecordAttributesArg",
        "OptionalID",
        "EntityRef",
        "ActivityRef",
        "AgentRef",
        "InfluencerRef",
        "GenerationRef",
        "UsageRef",
        "StreamOrPath",
        "QualifiedNameCandidate",
        "DatetimeOrStr",
        "NSCollection",
    )
}
# Defaults render as written in the source (``PROV_ENTITY``), not as a repr.
autodoc_preserve_defaults = True

from sphinx.util.inspect import TypeAliasForwardRef  # noqa: E402

_forward_ref_init = TypeAliasForwardRef.__init__


def _forward_ref_with_names(self: TypeAliasForwardRef, name: str) -> None:
    _forward_ref_init(self, name)
    self.__module__ = "prov.model"
    self.__qualname__ = self.__name__ = name


TypeAliasForwardRef.__init__ = _forward_ref_with_names  # type: ignore[method-assign]

# Every cross-reference must resolve; CI builds with -W -n.
nitpicky = True
nitpick_ignore = [
    # Private protocol behind RecordAttributesArg; a public annotation exposes it.
    ("py:class", "prov.model.records._SupportsItems"),
    # Type variable of ProvBundle.get_records(); not a public name.
    ("py:class", "prov.model.bundle._R"),
    # Module table in prov.graph that the prov_to_graph docstring cites; graph.md
    # documents the two functions only.
    ("py:data", "INFERRED_ELEMENT_CLASS"),
    # prov.graph annotates with the `nx` import alias, which intersphinx cannot map.
    ("py:class", "nx.MultiDiGraph"),
    # pydot publishes no Sphinx inventory.
    ("py:class", "pydot.Dot"),
    ("py:class", "pydot.core.Dot"),
]
napoleon_google_docstring = True
napoleon_numpy_docstring = False

myst_enable_extensions = ["colon_fence", "deflist"]

html_theme = "furo"
htmlhelp_basename = "provdoc"

latex_documents = [
    (
        "index",
        "prov.tex",
        "PROV Python Package Documentation",
        "Trung Dong Huynh",
        "manual",
    ),
]
man_pages = [
    ("index", "prov", "PROV Python Package Documentation", ["Trung Dong Huynh"], 1)
]
texinfo_documents = [
    (
        "index",
        "prov",
        "PROV Python Package Documentation",
        "Trung Dong Huynh",
        "prov",
        "A Python library for the W3C PROV Data Model",
        "Documentation",
    ),
]

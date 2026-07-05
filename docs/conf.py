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
    # Internal working docs (roadmap plans/specs, dependency notes, gap
    # checklists) live under docs/ for convenience but are not part of the
    # published documentation.
    "superpowers",
    "dependencies.md",
    "test-gap-checklist.md",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
}

autodoc_member_order = "bysource"
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

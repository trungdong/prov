#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / "README.rst").read_text(encoding="utf-8")

requirements = ["python-dateutil>=2.2", "networkx>=2.0", "lxml>=3.3.5", "rdflib>=4.2.1"]

test_requirements = ["pydot>=1.2.0"]

setup(
    name="prov",
    version="2.0.0",
    description="A library for W3C Provenance Data Model supporting PROV-JSON, "
    "PROV-XML and PROV-O (RDF)",
    long_description=long_description,
    author="Trung Dong Huynh",
    author_email="trungdong@donggiang.com",
    url="https://github.com/trungdong/prov",
    project_urls={
        "Bug Reports": "https://github.com/trungdong/prov/issues",
        "Source": "https://github.com/trungdong/prov",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.6, <4",
    scripts=["scripts/prov-convert", "scripts/prov-compare"],
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dot": ["pydot>=1.2.0"],
    },
    license="MIT",
    zip_safe=False,
    keywords=[
        "provenance",
        "graph",
        "model",
        "PROV",
        "PROV-DM",
        "PROV-JSON",
        "W3C",
        "PROV-XML",
        "PROV-N",
        "PROV-O",
        "RDF",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Security",
        "Topic :: System :: Logging",
    ],
    test_suite="prov.tests",
    tests_require=test_requirements,
)

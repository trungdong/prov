#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()

with open(path.join(here, 'HISTORY.rst'), encoding='utf-8') as f:
    history = f.read().replace('.. :changelog:', '')

requirements = [
    'python-dateutil',
    'networkx',
    'lxml',
    'six>=1.9.0',
    'rdflib>=4.2.1'
]

test_requirements = [
    'pydot>=1.2.0'
]

setup(
    name='prov',
    version='1.5.1.dev1',
    description='A library for W3C Provenance Data Model supporting PROV-JSON, '
                'PROV-XML and PROV-O (RDF)',
    long_description=readme + '\n\n' + history,
    author='Trung Dong Huynh',
    author_email='trungdong@donggiang.com',
    url='https://github.com/trungdong/prov',
    packages=find_packages(exclude=['dev', 'docs']),
    package_dir={
        'prov': 'prov'
    },
    scripts=['scripts/prov-convert', 'scripts/prov-compare'],
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'dot': ['pydot>=1.2.0'],
    },
    license="MIT",
    zip_safe=False,
    keywords=[
        'provenance', 'graph', 'model', 'PROV', 'PROV-DM', 'PROV-JSON', 'JSON',
        'PROV-XML', 'PROV-N', 'PROV-O', 'RDF'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Security',
        'Topic :: System :: Logging',
    ],
    test_suite='prov.tests',
    tests_require=test_requirements
)

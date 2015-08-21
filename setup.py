#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

requirements = [
    'python-dateutil',
    'networkx>=1.10',
    'lxml',
    'six>=1.9.0'
]

test_requirements = [
    'pydotplus'
]

setup(
    name='prov',
    version='1.4.1.dev1',
    description='A library for W3C Provenance Data Model supporting PROV-JSON '
                'and PROV-XML',
    long_description=readme + '\n\n' + history,
    author='Trung Dong Huynh',
    author_email='trungdong@donggiang.com',
    url='https://github.com/trungdong/prov',
    packages=find_packages(),
    package_dir={
        'prov': 'prov'
    },
    scripts=['scripts/prov-convert', 'scripts/prov-compare'],
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'dot': ['pydotplus'],
    },
    license="MIT",
    zip_safe=False,
    keywords=[
        'provenance', 'graph', 'model', 'PROV', 'PROV-DM', 'PROV-JSON', 'JSON',
        'PROV-XML', 'PROV-N'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Security',
        'Topic :: System :: Logging',
    ],
    test_suite='prov.tests',
    tests_require=test_requirements
)

from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

with open('LICENCE.txt') as f:
    licence = f.read()

setup(
    name='prov',
    version='0.6.0',
    author='Trung Dong Huynh',
    author_email='trungdong@donggiang.com',
    packages=['prov', 'prov.serializers'],
    scripts=[],
    url='https://github.com/trungdong/prov',
    license=licence,
    description='A Python implementation of PROV data model.',
    long_description=long_description,
    extras_require={
        'graph-export': ['pydot'],
    },
    install_requires=['python-dateutil'], 
    provides=['prov'],
    keywords=['provenance', 'graph', 'model', 'PROV', 'PROV-DM', 'PROV-JSON', 'JSON'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Security',
        'Topic :: System :: Logging',
    ]
)

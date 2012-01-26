from setuptools import setup

setup(
    name='provdm',
    version='1.0.2',
    author='Huanjia Yang',
    author_email='huanjiayang@hotmail.com',
    packages=['provdm', 'test','examples'],
    scripts=[],
    url='http://github.com/trungdong/w3-prov/tree/master/provpy/provdm',
    license='LICENSE.txt',
    description='A Python implementation of PROV-DM data model.',
    long_description=open('README.txt').read(),
    install_requires=[],
)
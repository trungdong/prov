from setuptools import setup

setup(
    name='provpy',
    version='1.0.0',
    author='Huanjia Yang',
    author_email='huanjiayang@hotmail.com',
    packages=['provpy', 'provpy.model','provpy.model.examples','provpy.model.test'],
    scripts=[],
    url='http://github.com/trungdong/w3-prov/tree/master/provpy',
    license='LICENSE.txt',
    description='A Python implementation of PROV-DM data model.',
    long_description=open('README').read(),
    install_requires=[],
)
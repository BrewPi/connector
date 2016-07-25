from os import path
from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='brewpi-connector',
    version='0.1',
    author='Matthew McGowan',
    install_requires=[
    ],

    packages=[
        'brewpi.connector',
        'brewpi.datalog',
        'brewpi.protocol',
    ],

    extras_require={
        'test': ['coverage'],
    },

    namespace_packages=[
        'brewpi',
        'brewpi.connector',
        'brewpi.datalog',
        'brewpi.protocol',
    ],
)

#!/usr/bin/env python

from setuptools import setup, find_packages

long_description = '''A wrapper for Rdio's web service API.

This also includes a command-line tool rdio-call for making API calls.'''

setup(
    name='Rdio',
    version='0.3.0',

    description='A Python wrapper library for the Rdio web services API',
    long_description=long_description,

    author='Rdio',
    author_email='developersupport@rd.io',

    url='http://www.rdio.com/developers/',

    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    license='MIT',
    platforms='any',

    install_requires=['oauth2'],

    packages=find_packages(),

    scripts=['rdio-call'],
)

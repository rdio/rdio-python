#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='Rdio',
      version='0.1',
      description='A Python wrapper library for the Rdio web services API',
      long_description='''A wrapper for Rdio's web service API.
This includes versions of the httplib2 and oauth2 libraries that work well with the Rdio service.
This also includes a command-line tool rdio-call for making API calls.''',
      author='Rdio',
      author_email='api@rd.io',
      platforms='any',
      license='MIT',
      url='http://developer.rdio.com/',
      packages=find_packages(),
      scripts=['rdio-call'],
)


#!/usr/bin/env python3
import os

from setuptools import setup, find_packages

VERSION = 'v0.1.0'
PACKAGE_NAME = 'wardreport'
HERE = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_URL = ('https://github.com/lrnselfreliance/wardreport/archive/'
                '{}.zip'.format(VERSION))

PACKAGES = find_packages(exclude=['tests', 'tests.*'])

REQUIRES = [
    'requests>=2,<3',
    'python-dotenv>=0.19.2',
    'selenium>=4.0.0',
]

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    license='GNU General Public License v3.0',
    download_url=DOWNLOAD_URL,
    author='Roland',
    author_email='roland@learningselfreliance.com',
    description='A tool to generate PDF reports from the LDS churches Leader and Clerk Resources (LCR)',
    url='https://github.com/lrnselfreliance/wardreport',
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=REQUIRES,
    test_suite='tests',
)

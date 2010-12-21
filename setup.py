from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
from downpour.core import VERSION
import sys, os

setup(name="Downpour",
    version=VERSION,
    license="GPLv2",
    description="Downpour is a web-based BitTorrent client",
    long_description="""\
    Downpour was designed with home media servers in mind.  It supports
    auto-downloading from RSS feeds and automatic importing and renaming
    of downloads into a media library.
    """,
    author="Jeremy Jongsma",
    author_email="jeremy@jongsma.org",
    url="http://home.jongsma.org/software/downpour/",
    packages=find_packages(exclude='tests'),
    include_package_data=True,
    # Not zip-safe until /media/ handler is rewritten
    zip_safe=False,
    scripts=['bin/downpourd', 'bin/downpour-remote'],
    install_requires=['Twisted-Core>=8.2.0', 'Twisted-Web>=8.2.0', 'jinja2>=2.5.0', 'storm>=0.14', 'FeedParser>=4.1', 'python-dateutil>=1.4.1']
)

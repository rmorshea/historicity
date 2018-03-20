import os
import sys
from distutils.core import setup
from setuptools import find_packages

#-------------------------------------------------------------------------------
# Project
#-------------------------------------------------------------------------------

url = "https://github.com/rmorshea/historicity"
project = "historicity"
version = "0.1.0"
author = "Ryan Morshead"
email = "ryan.morshead@gmail.com"
summary = "historical authenticity"

description = """
Historicity
-----------

Historical authenticity.
"""

#-------------------------------------------------------------------------------
# Packages
#-------------------------------------------------------------------------------

packages = find_packages(project)

#-------------------------------------------------------------------------------
# Base Paths
#-------------------------------------------------------------------------------

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.join(here, project)

#-------------------------------------------------------------------------------
# Finalize Parameters
#-------------------------------------------------------------------------------

if sys.version_info < (3, 5):
    requires = ["funcsigs"]
else:
    requires = []

parameters = dict(
    url=url,
    name=project,
    version=version,
    author=author,
    author_email=email,
    description=summary,
    long_description=description,
    packages=find_packages(),
    python_requires = ">=2.7",
    install_requries=requires,
    classifiers = [
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)

#-------------------------------------------------------------------------------
# Setup
#-------------------------------------------------------------------------------

if __name__ == "__main__":
    setup(**parameters)

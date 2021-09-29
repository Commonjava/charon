"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# !/usr/bin/env python

import re

from setuptools import setup, find_packages

version = "1.0.0"

# f = open('README.md')
# long_description = f.read().strip()
# long_description = long_description.split('split here', 1)[1]
# f.close()
long_description = """
This mrrc-uploader is a tool to synchronize several types of
artifacts repository data to RedHat MRRC service (maven.repository.redhat.com).
These repositories including types of maven, npm or some others like python
in future. And MRRC service will be hosted in AWS S3.
"""


def _get_requirements(path):
    try:
        with open(path, encoding="utf-8") as f:
            packages = f.read().splitlines()
    except (IOError, OSError) as ex:
        raise RuntimeError(f"Can't open file with requirements: {ex}") from ex
    packages = (p.strip() for p in packages if not re.match(r'^\s*#', p))
    packages = list(filter(None, packages))
    return packages


setup(
    zip_safe=True,
    name="mrrc-uploader",
    version=version,
    long_description=long_description,
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
    ],
    keywords="mrrc maven npm build java",
    author="RedHat EXD SPMM",
    license="APLv2",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    install_requires=_get_requirements('requirements.txt'),
    test_suite="tests",
    entry_points={
      'console_scripts': ['mrrc = mrrc.cli.main:run'],
    }
)

"""
Copyright (C) 2022 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
from setuptools import setup, find_packages

version = "1.4.0"

long_description = """
This charon is a tool to synchronize several types of
artifacts repository data to RedHat Ronda service (maven.repository.redhat.com).
These repositories including types of maven, npm or some others like python
in future. And Ronda service will be hosted in AWS S3.
"""

setup(
    zip_safe=True,
    name="charon",
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
    keywords="charon mrrc maven npm build java",
    author="RedHat EXD SPMM",
    license="APLv2",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    package_data={'charon': ['schemas/*.json']},
    test_suite="tests",
    entry_points={
        "console_scripts": ["charon = charon.cmd:cli"],
    },
    install_requires=[
        "Jinja2>=3.1.3",
        "boto3>=1.18.35",
        "botocore>=1.21.35",
        "click>=8.1.3",
        "requests>=2.25.0",
        "PyYAML>=5.4.1",
        "defusedxml>=0.7.1",
        "subresource-integrity>=0.2",
        "jsonschema>=4.9.1",
        "urllib3>=1.25.10",
        "semantic-version>=2.10.0",
        "oras<=0.2.31",
        "python-qpid-proton>=0.39.0"
    ],
)

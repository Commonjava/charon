#!/usr/bin/env python

from setuptools import setup, find_packages
import sys

# handle python 3
if sys.version_info >= (3,):
    use_2to3 = True
else:
    use_2to3 = False

version = "1.0.0"

# f = open('README.md')
# long_description = f.read().strip()
# long_description = long_description.split('split here', 1)[1]
# f.close()
long_description = '''
This mrrc-uploader is a tool to synchronize several types of artifacts repository data to RedHat MRRC service (maven.repository.redhat.com). These repositories including types of maven, npm or some others like python in future. And MRRC service will be hosted in AWS S3.
'''

test_deps = [
    "Mock",
    "nose",
    "responses",
  ]

extras = {
  'test': test_deps,
  'build': ['tox'],
  'ci': ['coverage']
}

setup(
    zip_safe=True,
    use_2to3=use_2to3,
    name='mrrc-uploader',
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
    keywords='mrrc maven npm build java',
    author='RedHat EXD SPMM',
    license='APLv2',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    install_requires=[
      "requests",
      "click",
      "boto3",
      "botocore",
      "marshmallow-dataclass",
    ],
    tests_require=test_deps,
    extras_require=extras,
    test_suite="tests",
    entry_points={
      'console_scripts': [
        'mrrc = mrrc:cli'
      ],
    }
)

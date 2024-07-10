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

from __future__ import absolute_import

import json
import os

import jsonschema
import pytest
import yaml
from flexmock import flexmock

from charon.utils.yaml import (read_yaml,
                               read_yaml_from_file_path,
                               load_schema,
                               validate_with_schema)


def test_read_yaml_file_ioerrors(tmpdir):
    config_path = os.path.join(str(tmpdir), 'nosuchfile.yaml')
    with pytest.raises(IOError):
        read_yaml_from_file_path(config_path, 'schemas/nosuchfile.json')


@pytest.mark.parametrize('from_file', [True, False])
@pytest.mark.parametrize('config', [
    ("""\
      targets:
          ga:
          - bucket: test_bucket
    """),
])
def test_read_yaml_file_or_yaml(tmpdir, from_file, config):
    expected = yaml.safe_load(config)

    if from_file:
        config_path = os.path.join(str(tmpdir), 'config.yaml')
        with open(config_path, 'w') as fp:
            fp.write(config)
        output = read_yaml_from_file_path(config_path, 'schemas/charon.json')
    else:
        output = read_yaml(config, 'schemas/charon.json')

    assert output == expected


def test_read_yaml_bad_package(caplog):
    with pytest.raises(ImportError):
        read_yaml("", 'schemas/charon.json', package='bad_package')
    assert 'Unable to find package bad_package' in caplog.text


@pytest.mark.skip(reason="removed pkg_resources, use importlib instead")
def test_read_yaml_file_bad_extract(tmpdir, caplog):
    class FakeProvider(object):
        def get_resource_stream(self, pkg, rsc):
            raise IOError

    # pkg_resources.resource_stream() cannot be mocked directly
    # Instead mock the module-level function it calls.
    # (flexmock(pkg_resources)
    #  .should_receive('get_provider')
    #  .and_return(FakeProvider()))

    config_path = os.path.join(str(tmpdir), 'config.yaml')
    with open(config_path, 'w'):
        pass

    with pytest.raises(IOError):
        read_yaml_from_file_path(config_path, 'schemas/charon.json')
    assert "unable to extract JSON schema, cannot validate" in caplog.text


def test_read_yaml_file_bad_decode(tmpdir, caplog):
    (flexmock(json)
     .should_receive('load')
     .and_raise(ValueError))

    config_path = os.path.join(str(tmpdir), 'config.yaml')
    with open(config_path, 'w'):
        pass

    with pytest.raises(ValueError):
        read_yaml_from_file_path(config_path, 'schemas/charon.json')
    assert "unable to decode JSON schema, cannot validate" in caplog.text


@pytest.mark.parametrize(('config', 'expected'), [
    ("""\
        ignore_patterns:
            - test """,
     "'targets' is a required property"),
    ("""\
        tests: ga """,
     "Additional properties are not allowed ('tests' was unexpected)"),
])
def test_read_yaml_validation_error(config, expected, caplog):
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        read_yaml(config, 'schemas/charon.json')

    assert "schema validation error" in caplog.text
    assert expected in str(exc_info.value)


@pytest.mark.parametrize(('package', 'package_pass'), [
    ('charon', True),
    ('FOO', False)
])
def test_load_schema_package(package, package_pass, caplog):
    schema = 'schemas/charon.json'
    if not package_pass:
        with pytest.raises(ImportError):
            load_schema(package, schema)
        assert "Unable to find package FOO" in caplog.text
    else:
        assert isinstance(load_schema(package, schema), dict)


@pytest.mark.parametrize(('schema', 'schema_pass'), [
    ('schemas/charon.json', True),
    ('schemas/charon.json', False)
])
def test_load_schema_schema(schema, schema_pass, caplog):
    package = 'charon'
    if not schema_pass:
        (flexmock(json)
         .should_receive('load')
         .and_raise(ValueError))
        with pytest.raises(ValueError):
            load_schema(package, schema)
        assert "unable to decode JSON schema, cannot validate" in caplog.text
    else:
        assert isinstance(load_schema(package, schema), dict)


@pytest.mark.parametrize(('config', 'validation_pass', 'expected'), [
    ({
         'name': 1
     }, False,
     "1 is not of type 'string"
     ),
    (
            {
                'name': 'foo',
                'module': 'bar'
            },
            False,
            "'module' was unexpected",
    ), ({
            'name': 'foo'
        }, True, '')
])
def test_validate_with_schema_validation(config, validation_pass, expected, caplog):
    schema = {
        'type': 'object',
        'required': ['name'],
        'properties': {
            'name': {
                'type': 'string'
            }
        },
        'additionalProperties': False
    }
    if not validation_pass:
        with pytest.raises(jsonschema.ValidationError) as exc_info:
            validate_with_schema(config, schema)
        assert 'schema validation error' in caplog.text
        assert expected in str(exc_info.value)
    else:
        validate_with_schema(config, schema)
        assert expected == ''


def test_validate_with_schema_bad_schema(caplog):
    config = {
        'name': 'foo'
    }
    schema = {
        'type': 'bakagaki',  # Nonexistent type
        'properties': {
            'name': {
                'type': 'string'
            }
        }
    }
    with pytest.raises(jsonschema.SchemaError):
        validate_with_schema(config, schema)
    assert 'invalid schema, cannot validate' in caplog.text

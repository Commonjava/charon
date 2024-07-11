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
import codecs
import json
import logging

import jsonschema
import yaml
import importlib

logger = logging.getLogger(__name__)


def read_yaml_from_file_path(file_path, schema, package='charon'):
    """
    :param file_path: string, yaml file to read
    :param schema: string, file path to the JSON schema
    :param package: string, package name containing the schema
    """
    with open(file_path) as f:
        yaml_data = f.read()
    return read_yaml(yaml_data, schema, package)


def read_yaml(yaml_data, schema, package=None):
    """
    :param yaml_data: string, yaml content
    :param schema: string, file path to the JSON schema
    :param package: string, package name containing the schema
    """
    package = package or 'charon'
    data = yaml.safe_load(yaml_data)
    schema = load_schema(package, schema)
    validate_with_schema(data, schema)
    return data


def load_schema(package, schema):
    """
    :param package: string, package name containing the schema
    :param schema: string, file path to the JSON schema
    """
    # Read schema from file
    try:
        resource = importlib.resources.files(package).joinpath(schema).open("rb")
        # resource = resource_stream(package, schema)
        schema = codecs.getreader('utf-8')(resource)
    except ImportError:
        logger.error('Unable to find package %s', package)
        raise
    except (IOError, TypeError):
        logger.error('unable to extract JSON schema, cannot validate')
        raise

    # Load schema into Dict
    try:
        schema = json.load(schema)
    except ValueError:
        logger.error('unable to decode JSON schema, cannot validate')
        raise
    return schema


def validate_with_schema(data, schema):
    """
    :param data: dict, data to be validated
    :param schema: dict, schema to validate with
    """
    validator = jsonschema.Draft7Validator(schema=schema)
    try:
        jsonschema.Draft7Validator.check_schema(schema)
        validator.validate(data)
    except jsonschema.SchemaError:
        logger.error('invalid schema, cannot validate')
        raise
    except jsonschema.ValidationError as exc:
        logger.error("schema validation error: %s", exc)
        raise

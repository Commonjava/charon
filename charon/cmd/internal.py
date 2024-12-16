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
from typing import List, Optional

from charon.config import CharonConfig
from charon.constants import DEFAULT_REGISTRY
from charon.types import TARGET_TYPE
from charon.utils.logs import set_logging
from charon.utils.archive import download_archive
from json import loads
from shutil import rmtree

import logging
import os

logger = logging.getLogger(__name__)


def _get_targets(
    target_names: List[str], conf: CharonConfig
) -> List[TARGET_TYPE]:
    targets: List[TARGET_TYPE] = []
    for target in target_names:
        for bucket in conf.get_target(target):
            aws_bucket = bucket.get('bucket', '')
            prefix = bucket.get('prefix', '')
            registry = bucket.get('registry', DEFAULT_REGISTRY)
            cf_domain = bucket.get('domain', None)
            targets.append((target, aws_bucket, prefix, registry, cf_domain))
    return targets


def _safe_delete(tmp_dir: str):
    if tmp_dir and os.path.exists(tmp_dir):
        logger.info("Cleaning up work directory: %s", tmp_dir)
        try:
            rmtree(tmp_dir)
        except Exception as e:
            logger.error("Failed to clear work directory. %s", e)


def _get_ignore_patterns(conf: CharonConfig) -> Optional[List[str]]:
    ignore_patterns = os.getenv("CHARON_IGNORE_PATTERNS")
    if ignore_patterns:
        try:
            return loads(ignore_patterns)
        except (ValueError, TypeError):
            logger.warning("Warning: ignore_patterns %s specified in "
                           "system environment, but not a valid json "
                           "style array. Will skip it.", ignore_patterns)
    if conf:
        return conf.get_ignore_patterns()
    return None


def _get_local_repo(url: str) -> str:
    archive_path = url
    if url.startswith("http://") or url.startswith("https://"):
        logger.info("Start downloading tarball %s", url)
        archive_path = download_archive(url)
        logger.info("Tarball downloaded at: %s", archive_path)
    return archive_path


def _validate_prod_key(product: str, version: str) -> bool:
    if not product or product.strip() == "":
        logger.error("Error: product can not be empty!")
        return False
    if not version or version.strip() == "":
        logger.error("Error: version can not be empty!")
        return False
    if "," in product:
        logger.error("Error: there are invalid characters in product!")
        return False
    if "," in version:
        logger.error("Error: there are invalid characters in version!")
        return False
    return True


def _decide_mode(
    product: str, version: str, is_quiet: bool,
    is_debug: bool, use_log_file=True
):
    if is_quiet:
        logger.info("Quiet mode enabled, "
                    "will only give warning and error logs.")
        set_logging(
            product, version, level=logging.WARNING, use_log_file=use_log_file
        )
    elif is_debug:
        logger.info("Debug mode enabled, "
                    "will give all debug logs for tracing.")
        set_logging(
            product, version, level=logging.DEBUG, use_log_file=use_log_file
        )
    else:
        set_logging(
            product, version, level=logging.INFO, use_log_file=use_log_file
        )

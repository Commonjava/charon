from typing import List
import sys
import logging

logger = logging.getLogger(__name__)


def is_metadata(file: str) -> bool:
    return is_mvn_metadata(file) or is_npm_metadata(file) or file.endswith("index.html")


def is_mvn_metadata(file: str) -> bool:
    return "maven-metadata.xml" in file or "archetype-catalog.xml" in file


def is_npm_metadata(file: str) -> bool:
    return "package.json" in file


def upload_post_process(failed_files: List[str], failed_metas: List[str], product_key):
    __post_process(failed_files, failed_metas, product_key, "uploaded to")


def rollback_post_process(
    failed_files: List[str], failed_metas: List[str], product_key
):
    __post_process(failed_files, failed_metas, product_key, "rolled back from")


def __post_process(
    failed_files: List[str], failed_metas: List[str], product_key: str, operation: str
):
    if len(failed_files) == 0 and len(failed_metas) == 0:
        logger.info(
            "Product release %s is successfully" "%s Ronda service.",
            operation,
            product_key,
        )
    else:
        logger.error(
            "Product release %s is %s Ronda "
            "service, but has some failures as below:",
            product_key,
            operation,
        )
        if len(failed_files) > 0:
            logger.error("Failed files: \n%s", failed_files)
        if len(failed_metas) > 0:
            logger.error("Failed metadata files: \n%s", failed_metas)
        sys.exit(1)

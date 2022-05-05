from typing import List
import logging

logger = logging.getLogger(__name__)


def is_metadata(file: str) -> bool:
    return is_mvn_metadata(file) or is_npm_metadata(file) or file.endswith("index.html")


def is_mvn_metadata(file: str) -> bool:
    return "maven-metadata.xml" in file or "archetype-catalog.xml" in file


def is_npm_metadata(file: str) -> bool:
    return "package.json" in file


def upload_post_process(
    failed_files: List[str], failed_metas: List[str], product_key, bucket=None
):
    __post_process(failed_files, failed_metas, product_key, "uploaded to", bucket)


def rollback_post_process(
    failed_files: List[str], failed_metas: List[str], product_key, bucket=None
):
    __post_process(failed_files, failed_metas, product_key, "rolled back from", bucket)


def __post_process(
    failed_files: List[str],
    failed_metas: List[str],
    product_key: str,
    operation: str,
    bucket: str = None,
):
    if len(failed_files) == 0 and len(failed_metas) == 0:
        logger.info(
            "Product release %s is successfully %s " "Ronda service in bucket %s\n",
            product_key,
            operation,
            bucket,
        )
    else:
        total = len(failed_files) + len(failed_metas)
        logger.error(
            "%d file(s) occur errors/warnings in bucket %s, "
            "please see errors.log for details.\n",
            bucket,
            total,
        )
        logger.error(
            "Product release %s is %s Ronda service in bucket %s, "
            "but has some failures as below:",
            product_key,
            operation,
            bucket,
        )
        if len(failed_files) > 0:
            logger.error("Failed files: \n%s\n", failed_files)
        if len(failed_metas) > 0:
            logger.error("Failed metadata files: \n%s\n", failed_metas)

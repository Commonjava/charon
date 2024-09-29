from typing import List, Optional, Dict
from charon.cache import (
    CFClient,
    INVALIDATION_BATCH_DEFAULT,
    INVALIDATION_BATCH_WILDCARD,
    INVALIDATION_STATUS_COMPLETED
)
from charon.types import TARGET_TYPE
import logging
import os

logger = logging.getLogger(__name__)


def is_metadata(file: str) -> bool:
    return is_mvn_metadata(file) or \
           is_npm_metadata(file) or \
           file.endswith("index.html")


def is_mvn_metadata(file: str) -> bool:
    return "maven-metadata.xml" in file or \
           "archetype-catalog.xml" in file


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
    bucket: str = None
):
    if len(failed_files) == 0 and len(failed_metas) == 0:
        logger.info("Product release %s is successfully %s "
                    "Ronda service in bucket %s\n",
                    product_key, operation, bucket)
    else:
        total = len(failed_files) + len(failed_metas)
        logger.error(
            "%d file(s) occur errors/warnings in bucket %s, "
            "please see errors.log for details.\n",
            bucket, total
        )
        logger.error(
            "Product release %s is %s Ronda service in bucket %s, "
            "but has some failures as below:",
            product_key, operation, bucket
        )
        if len(failed_files) > 0:
            logger.error("Failed files: \n%s\n", failed_files)
        if len(failed_metas) > 0:
            logger.error("Failed metadata files: \n%s\n", failed_metas)


def invalidate_cf_paths(
    cf_client: CFClient,
    target: TARGET_TYPE,
    invalidate_paths: List[str],
    root="/",
    batch_size=INVALIDATION_BATCH_DEFAULT
):
    logger.info("Invalidating CF cache for %s", target[1])
    bucket_name = target[1]
    prefix = target[2]
    prefix = "/" + prefix if not prefix.startswith("/") else prefix
    domain: Optional[str] = target[4]
    slash_root = root
    if not root.endswith("/"):
        slash_root = slash_root + "/"
    final_paths = []
    for full_path in invalidate_paths:
        path = full_path
        if path.startswith(slash_root):
            path = path[len(slash_root):]
        if prefix:
            path = os.path.join(prefix, path)
        final_paths.append(path)
    logger.debug("Invalidating paths: %s, size: %s", final_paths, len(final_paths))
    if not domain:
        domain = cf_client.get_domain_by_bucket(bucket_name)
    if domain:
        distr_id = cf_client.get_dist_id_by_domain(domain)
        if distr_id:
            real_batch_size = batch_size
            for path in final_paths:
                if path.endswith('*'):
                    real_batch_size = INVALIDATION_BATCH_WILDCARD
                    break
            result = cf_client.invalidate_paths(
                distr_id, final_paths, real_batch_size
            )
            if result:
                output: Dict[str, List[str]] = {}
                for invalidation in result:
                    status = invalidation.get('Status', '')
                    if status and status not in output:
                        output[status] = []
                    output[status].append(invalidation["Id"])
                non_completed = {}
                for status, ids in output.items():
                    if status != INVALIDATION_STATUS_COMPLETED:
                        non_completed[status] = ids
                logger.info(
                    "The CF invalidating requests done, following requests "
                    "are not completed yet:\n %s\nPlease use 'cf check' command to "
                    "check its details.", non_completed
                )
                logger.debug(
                    "All invalidations requested in this process:\n %s", output
                )
    else:
        logger.error(
            "CF invalidating will not be performed because domain not found for"
            " bucket %s. ", bucket_name
        )

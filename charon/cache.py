from boto3 import session
from botocore.exceptions import ClientError
from typing import Dict, List, Optional
import os
import logging
import uuid
import time

logger = logging.getLogger(__name__)

ENDPOINT_ENV = "aws_endpoint_url"
INVALIDATION_BATCH_DEFAULT = 3000
INVALIDATION_BATCH_WILDCARD = 15

INVALIDATION_STATUS_COMPLETED = "Completed"
INVALIDATION_STATUS_INPROGRESS = "InProgress"

DEFAULT_BUCKET_TO_DOMAIN = {
    "prod-ga": "maven.repository.redhat.com",
    "prod-maven-ga": "maven.repository.redhat.com",
    "prod-ea": "maven.repository.redhat.com",
    "prod-maven-ea": "maven.repository.redhat.com",
    "stage-ga": "maven.stage.repository.redhat.com",
    "stage-maven-ga": "maven.stage.repository.redhat.com",
    "stage-ea": "maven.stage.repository.redhat.com",
    "stage-maven-ea": "maven.stage.repository.redhat.com",
    "prod-npm": "npm.registry.redhat.com",
    "prod-npm-npmjs": "npm.registry.redhat.com",
    "stage-npm": "npm.stage.registry.redhat.com",
    "stage-npm-npmjs": "npm.stage.registry.redhat.com"
}


class CFClient(object):
    """The CFClient is a wrapper of the original boto3 clouldfrong client,
    which will provide CloudFront functions to be used in the charon.
    """

    def __init__(
        self,
        aws_profile=None,
        extra_conf=None
    ) -> None:
        self.__client = self.__init_aws_client(aws_profile, extra_conf)

    def __init_aws_client(
        self, aws_profile=None, extra_conf=None
    ):
        if aws_profile:
            logger.debug("[CloudFront] Using aws profile: %s", aws_profile)
            cf_session = session.Session(profile_name=aws_profile)
        else:
            cf_session = session.Session()
        endpoint_url = self.__get_endpoint(extra_conf)
        return cf_session.client(
            'cloudfront',
            endpoint_url=endpoint_url
        )

    def __get_endpoint(self, extra_conf) -> Optional[str]:
        endpoint_url = os.getenv(ENDPOINT_ENV)
        if not endpoint_url or not endpoint_url.strip():
            if isinstance(extra_conf, Dict):
                endpoint_url = extra_conf.get(ENDPOINT_ENV, None)
        if endpoint_url:
            logger.info(
                "[CloudFront] Using endpoint url for aws CF client: %s",
                endpoint_url
            )
        else:
            logger.debug("[CloudFront] No user-specified endpoint url is used.")
        return endpoint_url

    def invalidate_paths(
        self, distr_id: str, paths: List[str],
        batch_size=INVALIDATION_BATCH_DEFAULT
    ) -> List[Dict[str, str]]:
        """Send a invalidating requests for the paths in distribution to CloudFront.
        This will invalidate the paths in the distribution to enforce the refreshment
        from backend S3 bucket for these paths. For details see:
        https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html
            * The distr_id is the id for the distribution. This id can be get through
            get_dist_id_by_domain(domain) function
            * Can specify the invalidating paths through paths param.
            * Batch size is the number of paths to be invalidated in one request.
            The default value is 3000 which is the maximum number in official doc:
            https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html#InvalidationLimits
        """
        INPRO_W_SECS = 10
        NEXT_W_SECS = 2
        real_paths = [paths]
        # Split paths into batches by batch_size
        if batch_size:
            real_paths = [paths[i:i + batch_size] for i in range(0, len(paths), batch_size)]
        total_time_approx = len(real_paths) * (INPRO_W_SECS * 2 + NEXT_W_SECS)
        logger.info("There will be %d invalidating requests in total,"
                    " will take more than %d seconds",
                    len(real_paths), total_time_approx)
        results = []
        current_invalidation: Dict[str, str] = {}
        processed_count = 0
        for batch_paths in real_paths:
            while (current_invalidation and
                    INVALIDATION_STATUS_INPROGRESS == current_invalidation.get('Status', '')):
                time.sleep(INPRO_W_SECS)
                try:
                    result = self.check_invalidation(distr_id, current_invalidation.get('Id', ''))
                    if result:
                        current_invalidation = {
                            'Id': result.get('Id', None),
                            'Status': result.get('Status', None)
                        }
                        logger.debug("Check invalidation: %s", current_invalidation)
                except Exception as err:
                    logger.warning(
                        "[CloudFront] Error occurred while checking invalidation status during"
                        " creating invalidation, invalidation: %s, error: %s",
                        current_invalidation, err
                    )
                    break
            if current_invalidation:
                results.append(current_invalidation)
                processed_count += 1
                if processed_count % 10 == 0:
                    logger.info(
                        "[CloudFront] ######### %d/%d requests finished",
                        processed_count, len(real_paths))
                # To avoid conflict rushing request, we can wait 1s here
                # for next invalidation request sending.
                time.sleep(NEXT_W_SECS)
            caller_ref = str(uuid.uuid4())
            logger.debug(
                "Processing invalidation for batch with ref %s, size: %s",
                caller_ref, len(batch_paths)
            )
            try:
                response = self.__client.create_invalidation(
                    DistributionId=distr_id,
                    InvalidationBatch={
                        'CallerReference': caller_ref,
                        'Paths': {
                            'Quantity': len(batch_paths),
                            'Items': batch_paths
                        }
                    }
                )
                if response:
                    invalidation = response.get('Invalidation', {})
                    current_invalidation = {
                        'Id': invalidation.get('Id', None),
                        'Status': invalidation.get('Status', None)
                    }
            except Exception as err:
                logger.error(
                    "[CloudFront] Error occurred while creating invalidation"
                    " for paths %s, error: %s", batch_paths, err
                )
        if current_invalidation:
            results.append(current_invalidation)
        return results

    def check_invalidation(self, distr_id: str, invalidation_id: str) -> Optional[dict]:
        try:
            response = self.__client.get_invalidation(
                DistributionId=distr_id,
                Id=invalidation_id
            )
            if response:
                invalidation = response.get('Invalidation', {})
                return {
                    'Id': invalidation.get('Id', None),
                    'CreateTime': str(invalidation.get('CreateTime', None)),
                    'Status': invalidation.get('Status', None)
                }
        except Exception as err:
            logger.error(
                "[CloudFront] Error occurred while check invalidation of id %s, "
                "error: %s", invalidation_id, err
            )
        return None

    def get_dist_id_by_domain(self, domain: str) -> Optional[str]:
        """Get distribution id by a domain name. The id can be used to send invalidating
        request through #invalidate_paths function
           * Domain are Ronda domains, like "maven.repository.redhat.com"
           or "npm.registry.redhat.com"
        """
        try:
            response = self.__client.list_distributions()
            if response:
                dist_list_items = response.get("DistributionList", {}).get("Items", [])
                for distr in dist_list_items:
                    aliases_items = distr.get('Aliases', {}).get('Items', [])
                    if aliases_items and domain in aliases_items:
                        return distr['Id']
            logger.error("[CloudFront]: Distribution not found for domain %s", domain)
        except ClientError as err:
            logger.error(
                "[CloudFront]: Error occurred while get distribution for domain %s: %s",
                domain, err
            )
        return None

    def get_domain_by_bucket(self, bucket: str) -> Optional[str]:
        return DEFAULT_BUCKET_TO_DOMAIN.get(bucket, None)

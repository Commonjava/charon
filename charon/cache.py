from boto3 import session
from botocore.exceptions import ClientError
from typing import Dict, List
import os
import logging
import uuid

logger = logging.getLogger(__name__)

ENDPOINT_ENV = "aws_endpoint_url"

DEFAULT_BUCKET_TO_DOMAIN = {
    "prod-maven-ga": "maven.repository.redhat.com",
    "prod-maven-ea": "maven.repository.redhat.com",
    "stage-maven-ga": "maven.strage.repository.redhat.com",
    "stage-maven-ea": "maven.strage.repository.redhat.com",
    "prod-npm": "npm.repository.redhat.com",
    "stage-npm": "npm.stage.repository.redhat.com"
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

    def __get_endpoint(self, extra_conf) -> str:
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

    def invalidate_paths(self, distr_id: str, paths: List[str]) -> Dict[str, str]:
        """Send a invalidating requests for the paths in distribution to CloudFront.
        This will invalidate the paths in the distribution to enforce the refreshment
        from backend S3 bucket for these paths. For details see:
        https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html
            * The distr_id is the id for the distribution. This id can be get through
            get_dist_id_by_domain(domain) function
            * Can specify the invalidating paths through paths param.
        """
        caller_ref = str(uuid.uuid4())
        logger.debug("[CloudFront] Creating invalidation for paths: %s", paths)
        try:
            response = self.__client.create_invalidation(
                DistributionId=distr_id,
                InvalidationBatch={
                    'CallerReference': caller_ref,
                    'Paths': {
                        'Quantity': len(paths),
                        'Items': paths
                    }
                }
            )
            if response:
                invalidation = response.get('Invalidation', {})
                return {
                    'Id': invalidation.get('Id', None),
                    'Status': invalidation.get('Status', None)
                }
        except Exception as err:
            logger.error(
                "[CloudFront] Error occurred while creating invalidation, error: %s", err
            )

    def check_invalidation(self, distr_id: str, invalidation_id: str) -> dict:
        try:
            response = self.__client.get_invalidation(
                DistributionId=distr_id,
                Id=invalidation_id
            )
            if response:
                invalidation = response.get('Invalidation', {})
                return {
                    'Id': invalidation.get('Id', None),
                    'CreateTime': invalidation.get('CreateTime', None),
                    'Status': invalidation.get('Status', None)
                }
        except Exception as err:
            logger.error(
                "[CloudFront] Error occurred while check invalidation of id %s, "
                "error: %s", invalidation_id, err
            )

    def get_dist_id_by_domain(self, domain: str) -> str:
        """Get distribution id by a domain name. The id can be used to send invalidating
        request through #invalidate_paths function
           * Domain are Ronda domains, like "maven.repository.redhat.com"
           or "npm.repository.redhat.com"
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

    def get_domain_by_bucket(self, bucket: str) -> str:
        return DEFAULT_BUCKET_TO_DOMAIN.get(bucket, None)

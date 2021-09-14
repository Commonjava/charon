from mrrc.config import mrrc_config, AWS_ENDPOINT, AWS_BUCKET, AWS_RETRY_MAX, AWS_RETRY_MODE
import boto3
from botocore.config import Config
from typing import List

class S3Client(object):
    def __init__(self, extra_conf=None) -> None:
        mrrc_conf = mrrc_config()
        aws_configs = mrrc_conf.get_aws_configs()
        s3_extra_conf = Config(
            retries = {
                'max_attempts': int(aws_configs.get(AWS_RETRY_MAX, '10')),
                'mode': aws_configs.get(AWS_RETRY_MODE, 'standard')
            }
        )
        self.client = boto3.resource(
            's3',
            config=s3_extra_conf,
            aws_access_key_id=mrrc_conf.get_aws_key_id(),
            aws_secret_access_key=mrrc_conf.get_aws_key(),
            region_name=mrrc_conf.get_aws_region(),
            endpoint_url=aws_configs[AWS_ENDPOINT] if AWS_ENDPOINT in aws_configs else None
        )
    
    def get_files(self, bucket_name=None, prefix=None, suffix=None)-> List[str]:
        b_name = bucket_name
        if not bucket_name or bucket_name.strip() == "":
            mrrc_conf = mrrc_config()
            b_name = mrrc_conf.get_aws_configs()[AWS_BUCKET]
        bucket = self.client.Bucket(b_name)
        objs = []
        if prefix and prefix.strip() != "":
            objs = list(bucket.objects.filter(Prefix=prefix))
        else:
            objs = list(bucket.objects.all())
        files = []
        if suffix and suffix.strip() != "":
            files = [i.key for i in objs if i.key.endswith(suffix)]
        else:
            files = [i.key for i in objs]    
        return files
        
        
    
# # Init config
# def boto3_config():
#     aws_configs = mrrc_config().get_aws_configs()
#     return Config(
#         region_name = aws_configs[AWS_REGION],
#         retries = {
#             'max_attempts': int(aws_configs.get(AWS_RETRY_MAX, '10')),
#             'mode': aws_configs.get(AWS_RETRY_MODE, 'standard')
#         }
#     )


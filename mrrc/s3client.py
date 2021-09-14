from mrrc.config import mrrc_config, AWS_ENDPOINT, AWS_BUCKET, AWS_RETRY_MAX, AWS_RETRY_MODE
import boto3
from botocore.config import Config
from typing import List

class S3Client(object):
    """The S3Client is a wrapper of the original boto3 s3 client, which will provide
       some convenient methods to be used in the mrrc uploader. 
    """
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
    
    def upload_files(self, file_paths: List[str], bucket_name=None, root="/"):
        """ Upload a list of files to s3 bucket. Use the cut down file path as s3 key.
            The cut down way is move root from the file path.
            Example: if file_path is /tmp/maven-repo/org/apache/.... and root is /tmp/maven-repo
            Then the key will be org/apache/.....
        """
        bucket = self.__get_bucket(bucket_name)
        slash_root = root
        if not root.endswith("/"):
            slash_root = slash_root + '/'
        for full_path in file_paths:
            path = full_path
            if path.startswith(slash_root):
                path = path[len(slash_root):]
            bucket.upload_file(full_path, path)
    
    def get_files(self, bucket_name=None, prefix=None, suffix=None)-> List[str]:
        """Get the file names from s3 bucket. Can use prefix and suffix to filter the
           files wanted.
        """
        bucket = self.__get_bucket(bucket_name)
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
    
    def __get_bucket(self, bucket_name=None):
        b_name = bucket_name
        if not bucket_name or bucket_name.strip() == "":
            mrrc_conf = mrrc_config()
            b_name = mrrc_conf.get_aws_configs()[AWS_BUCKET]
        return self.client.Bucket(b_name)
        
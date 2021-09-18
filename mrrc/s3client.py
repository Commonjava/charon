from mrrc.config import mrrc_config, AWS_ENDPOINT, AWS_BUCKET, AWS_RETRY_MAX, AWS_RETRY_MODE
import boto3
from botocore.config import Config
from botocore.errorfactory import ClientError
from typing import Callable, Dict, List

PRODUCT_META_KEY = "rh-products"
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
    
    def upload_files(self, file_paths: List[str], bucket_name=None, product=None, root="/"):
        """ Upload a list of files to s3 bucket. 
            * Use the cut down file path as s3 key. The cut down way is move root from the file path if it starts with root.
            Example: if file_path is /tmp/maven-repo/org/apache/.... and root is /tmp/maven-repo
            Then the key will be org/apache/.....  
            
            * The product will be added as the extra metadata with key "rh-products". For example, if the product for a file 
            is "apache-commons", the metadata of that file will contain "rh-products":"apache-commons"
            
            * For existed files, the upload will not override them, as the metadata of "rh-products" will be updated to add
            the new product. For example, if an exited file with new product "commons-lang3" is uploaded based on existed 
            metadata "apache-commons", the file will not be overrided, but the metadata will be changed to 
            "rh-products": "apache-commons,commons-lang3"
        """
        bucket = self.__get_bucket(bucket_name)
        slash_root = root
        if not root.endswith("/"):
            slash_root = slash_root + '/'
        for full_path in file_paths:
            path = full_path
            if path.startswith(slash_root):
                path = path[len(slash_root):]
                
        def path_handler(full_path: str, path: str):
            fileObject = bucket.Object(path)
            existed = self.__file_exists(fileObject)
            if not existed:
                if product:
                    fileObject.put(Body=full_path, Metadata={PRODUCT_META_KEY: product})
                else:
                    fileObject.upload_file(full_path)
            else:
                prods = []
                try:
                    prods = fileObject.metadata[PRODUCT_META_KEY].split(",")
                except KeyError:
                    pass
                if product not in prods:
                    prods.append(product)
                    self.__update_file_metadata(fileObject, bucket_name, path,{PRODUCT_META_KEY:",".join(prods)}) 
                
        self.__do_path_cut_and(
            file_paths=file_paths,
            fn=path_handler,
            root=root)   
            
    def delete_files(self, file_paths: List[str], bucket_name=None, product=None, root="/"):
        """ Deletes a list of files to s3 bucket. 
            * Use the cut down file path as s3 key. The cut down way is move root from the file path if it starts with root.
            Example: if file_path is /tmp/maven-repo/org/apache/.... and root is /tmp/maven-repo
            Then the key will be org/apache/.....  
            
            * The removing will happen with conditions of product checking. First the deletion will remove
            The product from the file metadata "rh-products". After the metadata removing, if there still are extra
            products left in that metadata, the file will not really be removed from the bucket. Only when 
            the metadata is all cleared, the file will be finally removed from bucket.
        """
        bucket = self.__get_bucket(bucket_name)
        def path_handler(full_path: str, path: str):
            fileObject = bucket.Object(path)
            existed = self.__file_exists(fileObject)
            if existed:
                prods = []
                try:
                    prods = fileObject.metadata[PRODUCT_META_KEY].split(",")
                except KeyError:
                    pass
                if product and product in prods:
                    prods.remove(product)
                    if len(prods)>0:
                        self.__update_file_metadata(fileObject, bucket_name, path,{PRODUCT_META_KEY:",".join(prods)}) 
            if len(prods)==0:
                bucket.delete_objects(Delete={'Objects':[{'Key':path}]})

        self.__do_path_cut_and(
            file_paths=file_paths,
            fn=path_handler,
            root=root)   
    
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
    
    def __file_exists(self, fileObject):
        try:
            fileObject.load() 
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else: 
                raise e
    
    def __update_file_metadata(self, fileObject, bucket_name: str, key: str, metadata: Dict):
        fileObject.metadata.update(metadata)
        fileObject.copy_from(
            CopySource={'Bucket':bucket_name, 'Key': key}, 
            Metadata=fileObject.metadata, 
            MetadataDirective='REPLACE'
        )
    
    def __do_path_cut_and(self, file_paths: List[str], fn: Callable[[str,str], None], root="/"):
        slash_root = root
        if not root.endswith("/"):
            slash_root = slash_root + '/'
        for full_path in file_paths:
            path = full_path
            if path.startswith(slash_root):
                path = path[len(slash_root):]
            fn(full_path, path)


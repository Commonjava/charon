"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/hermes)

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
from hermes.utils.files import read_sha1

from boto3 import session
from botocore.errorfactory import ClientError
from botocore.exceptions import HTTPClientError
from typing import Callable, Dict, List, Tuple
import os
import logging

logger = logging.getLogger(__name__)

PRODUCT_META_KEY = "rh-products"
CHECKSUM_META_KEY = "checksum"

ENDPOINT_ENV = "aws_endpoint_url"


class S3Client(object):
    """The S3Client is a wrapper of the original boto3 s3 client, which will provide
    some convenient methods to be used in the hermes.
    """

    def __init__(self, extra_conf=None) -> None:
        self.client = self.__init_aws_client(extra_conf)

    def __init_aws_client(self, extra_conf=None):
        aws_profile = os.getenv("AWS_PROFILE", None)
        if aws_profile:
            logger.debug("Using aws profile: %s", aws_profile)
            s3_session = session.Session(profile_name=aws_profile)
        else:
            s3_session = session.Session()
        endpoint_url = self.__get_endpoint(extra_conf)
        return s3_session.resource(
            's3',
            endpoint_url=endpoint_url
        )

    def __get_endpoint(self, extra_conf) -> str:
        endpoint_url = os.getenv(ENDPOINT_ENV)
        if not endpoint_url or endpoint_url.strip() == "":
            if isinstance(extra_conf, Dict):
                endpoint_url = extra_conf.get(ENDPOINT_ENV, None)
        if endpoint_url:
            logger.debug("Using endpoint url for aws client: %s", endpoint_url)
        else:
            logger.debug("Not using any endpoint url, will use default s3 endpoint")
        return endpoint_url

    def upload_files(
        self, file_paths: List[str], bucket_name: str,
        product: str, root="/"
    ) -> Tuple[List[str], List[str]]:
        """ Upload a list of files to s3 bucket. * Use the cut down file path as s3 key. The cut
        down way is move root from the file path if it starts with root. Example: if file_path is
        /tmp/maven-repo/org/apache/.... and root is /tmp/maven-repo Then the key will be
        org/apache/.....
            * The product will be added as the extra metadata with key "rh-products". For
            example, if the product for a file is "apache-commons", the metadata of that file
            will contain "rh-products":"apache-commons"
            * For existed files, the upload will not override them, as the metadata of
            "rh-products" will be updated to add the new product. For example, if an exited file
            with new product "commons-lang3" is uploaded based on existed metadata
            "apache-commons", the file will not be overridden, but the metadata will be changed to
            "rh-products": "apache-commons,commons-lang3"
            * Every file has sha1 checksum in "checksum" metadata. When uploading existed files,
            if the checksum does not match the existed one, will not upload it and report error.
            Note that if file name match
            * Return all failed to upload files due to any exceptions.
        """
        bucket = self.get_bucket(bucket_name)

        uploaded_files = []

        def path_upload_handler(full_file_path: str, path: str) -> bool:
            if not os.path.isfile(full_file_path):
                logger.warning('Warning: file %s does not exist during uploading. Product: %s',
                               full_file_path, product)
                return False
            logger.info('Uploading %s to bucket %s', full_file_path, bucket_name)
            fileObject = bucket.Object(path)
            existed = self.file_exists(fileObject)
            sha1 = read_sha1(full_file_path)
            if not existed:
                f_meta = {}
                if sha1.strip() != "":
                    f_meta[CHECKSUM_META_KEY] = sha1
                if product:
                    f_meta[PRODUCT_META_KEY] = product
                try:
                    if len(f_meta) > 0:
                        fileObject.put(Body=open(full_file_path, "rb"), Metadata=f_meta)
                    else:
                        fileObject.upload_file(full_file_path)
                    logger.info('Uploaded %s to bucket %s', full_file_path, bucket_name)
                    uploaded_files.append(path)
                except (ClientError, HTTPClientError) as e:
                    logger.error("ERROR: file %s not uploaded to bucket"
                                 " %s due to error: %s ", full_file_path,
                                 bucket_name, e)
                    return False
            else:
                logger.info(
                    "File %s already exists, check if need to update product.",
                    full_file_path,
                )
                f_meta = fileObject.metadata
                checksum = (
                    f_meta[CHECKSUM_META_KEY] if CHECKSUM_META_KEY in f_meta else ""
                )
                if checksum != "" and checksum.strip() != sha1:
                    logger.error('Error: checksum check failed. The file %s is different from the '
                                 'one in S3. Product: %s', path, product)
                    return False

                prods = []
                try:
                    prods = f_meta[PRODUCT_META_KEY].split(",")
                except KeyError:
                    pass
                if product not in prods:
                    logger.info(
                        "File %s has new product, updating the product %s",
                        full_file_path,
                        product,
                    )
                    prods.append(product)
                    self.__update_file_metadata(fileObject, bucket_name, path,
                                                {PRODUCT_META_KEY: ",".join(prods)})
            return True

        return (uploaded_files, self.__do_path_cut_and(
            file_paths=file_paths, fn=path_upload_handler, root=root
        ))

    def upload_metadatas(
        self, meta_file_paths: List[str], bucket_name: str,
        product: str, root="/"
    ) -> Tuple[List[str], List[str]]:
        """ Upload a list of metadata files to s3 bucket. This function is very similar to
        upload_files, except:
            * The metadata files will always be overwritten for each uploading
            * The metadata files' checksum will also be overwritten each time
            * Return all failed to upload metadata files due to exceptions
        """
        bucket = self.get_bucket(bucket_name)

        uploaded_files = []

        def path_upload_handler(full_file_path: str, path: str):
            if not os.path.isfile(full_file_path):
                logger.warning('Warning: file %s does not exist during uploading. Product: %s',
                               full_file_path, product)
                return False
            logger.info('Updating metadata %s to bucket %s', path, bucket_name)
            fileObject = bucket.Object(path)
            existed = self.file_exists(fileObject)
            f_meta = {}
            need_overwritten = True
            sha1 = read_sha1(full_file_path)
            if existed:
                f_meta = fileObject.metadata
                need_overwritten = (
                    CHECKSUM_META_KEY not in f_meta or sha1 != f_meta[CHECKSUM_META_KEY]
                )

            f_meta[CHECKSUM_META_KEY] = sha1
            prods = (
                f_meta[PRODUCT_META_KEY].split(",")
                if PRODUCT_META_KEY in f_meta
                else []
            )
            if product and product not in prods:
                prods.append(product)
                f_meta[PRODUCT_META_KEY] = ",".join(prods)
            try:
                if need_overwritten:
                    fileObject.put(Body=open(full_file_path, "rb"), Metadata=f_meta)
                else:
                    self.__update_file_metadata(fileObject, bucket_name, path, f_meta)
                logger.info('Updated metadata %s to bucket %s', path, bucket_name)
                uploaded_files.append(path)
            except (ClientError, HTTPClientError) as e:
                logger.error("ERROR: file %s not uploaded to bucket"
                             " %s due to error: %s ", full_file_path,
                             bucket_name, e)
                return False
            return True

        return (uploaded_files, self.__do_path_cut_and(
            file_paths=meta_file_paths, fn=path_upload_handler, root=root
        ))

    def delete_files(
        self, file_paths: List[str], bucket_name: str, product: str, root="/"
    ) -> Tuple[List[str], List[str]]:
        """ Deletes a list of files to s3 bucket. * Use the cut down file path as s3 key. The cut
        down way is move root from the file path if it starts with root. Example: if file_path is
        /tmp/maven-repo/org/apache/.... and root is /tmp/maven-repo Then the key will be
        org/apache/.....
            * The removing will happen with conditions of product checking. First the deletion
            will remove The product from the file metadata "rh-products". After the metadata
            removing, if there still are extra products left in that metadata, the file will not
            really be removed from the bucket. Only when the metadata is all cleared, the file
            will be finally removed from bucket.
        """
        bucket = self.get_bucket(bucket_name)

        deleted_files = []

        def path_delete_handler(full_file_path: str, path: str):
            logger.info('Deleting %s from bucket %s', path, bucket_name)
            fileObject = bucket.Object(path)
            existed = self.file_exists(fileObject)
            if existed:
                prods = []
                try:
                    prods = fileObject.metadata[PRODUCT_META_KEY].split(",")
                except KeyError:
                    pass
                if product and product in prods:
                    prods.remove(product)
                if len(prods) > 0:
                    try:
                        logger.info(
                            "File %s has other products overlapping,"
                            " will remove %s from its metadata",
                            path, product
                        )
                        self.__update_file_metadata(
                            fileObject,
                            bucket_name,
                            path,
                            {PRODUCT_META_KEY: ",".join(prods)},
                        )
                        logger.info(
                            "Removed product %s from metadata of file %s",
                            product, path
                        )
                        return True
                    except (ClientError, HTTPClientError) as e:
                        logger.error(
                            "ERROR: Failed to update metadata of file"
                            " %s due to error: %s ", path, e
                        )
                        return False
                elif len(prods) == 0:
                    try:
                        bucket.delete_objects(Delete={"Objects": [{"Key": path}]})
                        logger.info("Deleted %s from bucket %s", path, bucket_name)
                        deleted_files.append(path)
                        return True
                    except (ClientError, HTTPClientError) as e:
                        logger.error("ERROR: file %s failed to delete from bucket"
                                     " %s due to error: %s ", full_file_path,
                                     bucket_name, e)
                        return False
            else:
                logger.info("File %s does not exist in s3 bucket %s, skip deletion.",
                            path, bucket_name)
                return True

        failed_files = self.__do_path_cut_and(
            file_paths=file_paths, fn=path_delete_handler, root=root)

        return (deleted_files, failed_files)

    def get_files(self, bucket_name: str, prefix=None, suffix=None) -> List[str]:
        """Get the file names from s3 bucket. Can use prefix and suffix to filter the
        files wanted.
        """
        bucket = self.get_bucket(bucket_name)
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

    def read_file_content(self, bucket_name=None, key=None):
        bucket = self.get_bucket(bucket_name)
        fileObject = bucket.Object(key)
        return str(fileObject.get()['Body'].read(), 'utf-8')

    def get_bucket(self, bucket_name: str):
        return self.client.Bucket(bucket_name)

    def file_exists(self, fileObject) -> bool:
        try:
            fileObject.load()
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise e

    def file_exists_in_bucket(
        self, bucket_name: str, path: str
    ) -> bool:
        bucket = self.get_bucket(bucket_name)
        fileObject = bucket.Object(path)
        return self.file_exists(fileObject)

    def __update_file_metadata(
        self, fileObject, bucket_name: str, key: str, metadata: Dict
    ):
        fileObject.metadata.update(metadata)
        fileObject.copy_from(
            CopySource={"Bucket": bucket_name, "Key": key},
            Metadata=fileObject.metadata,
            MetadataDirective="REPLACE",
        )

    def __do_path_cut_and(
        self, file_paths: List[str], fn: Callable[[str, str], bool], root="/"
    ) -> List[str]:
        slash_root = root
        if not root.endswith("/"):
            slash_root = slash_root + "/"
        failed_paths = []
        for full_path in file_paths:
            path = full_path
            if path.startswith(slash_root):
                path = path[len(slash_root):]
            if not fn(full_path, path):
                failed_paths.append(path)
        return failed_paths

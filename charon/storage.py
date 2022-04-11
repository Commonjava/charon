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
import asyncio
import threading
from boto3_type_annotations.s3.service_resource import Object
from charon.utils.files import read_sha1
from charon.constants import PROD_INFO_SUFFIX, MANIFEST_SUFFIX

from boto3 import session
from botocore.errorfactory import ClientError
from botocore.exceptions import HTTPClientError
from boto3.exceptions import S3UploadFailedError
from botocore.config import Config
from boto3_type_annotations import s3
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
import os
import logging
import mimetypes
import functools
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(10)

logger = logging.getLogger(__name__)

PRODUCT_META_KEY = "rh-products"
CHECKSUM_META_KEY = "checksum"

ENDPOINT_ENV = "aws_endpoint_url"
ACCELERATION_ENABLE_ENV = "aws_enable_acceleration"

DEFAULT_MIME_TYPE = "application/octet-stream"

FILE_REPORT_LIMIT = 1000


class S3Client(object):
    """The S3Client is a wrapper of the original boto3 s3 client, which will provide
    some convenient methods to be used in the charon.
    """

    def __init__(
        self,
        aws_profile=None, extra_conf=None,
        con_limit=25, dry_run=False
    ) -> None:
        self.__client: s3.ServiceResource = self.__init_aws_client(aws_profile, extra_conf)
        self.__buckets: Dict[str, s3.Bucket] = {}
        self.__dry_run = dry_run
        self.__con_sem = asyncio.BoundedSemaphore(con_limit)
        self.__lock = threading.Lock()

    def __init_aws_client(
        self, aws_profile=None, extra_conf=None
    ) -> s3.ServiceResource:
        if aws_profile:
            logger.debug("Using aws profile: %s", aws_profile)
            s3_session = session.Session(profile_name=aws_profile)
        else:
            s3_session = session.Session()
        endpoint_url = self.__get_endpoint(extra_conf)
        config = None
        if self.__enable_acceleration(extra_conf):
            logger.info("S3 acceleration config enabled, "
                        "will enable s3 use_accelerate_endpoint config")
            config = Config(s3={"use_accelerate_endpoint": True})
        return s3_session.resource(
            's3',
            endpoint_url=endpoint_url,
            config=config
        )

    def __get_endpoint(self, extra_conf) -> str:
        endpoint_url = os.getenv(ENDPOINT_ENV)
        if not endpoint_url or endpoint_url.strip() == "":
            if isinstance(extra_conf, Dict):
                endpoint_url = extra_conf.get(ENDPOINT_ENV, None)
        if endpoint_url:
            logger.info("Using endpoint url for aws client: %s", endpoint_url)
        else:
            logger.debug("No user-specified endpoint url is used.")
        return endpoint_url

    def __enable_acceleration(self, extra_conf) -> bool:
        enable_acc = os.getenv(ACCELERATION_ENABLE_ENV)
        if not enable_acc or enable_acc.strip() == "":
            if isinstance(extra_conf, Dict):
                enable_acc = extra_conf.get(ACCELERATION_ENABLE_ENV, "False")
        if enable_acc and enable_acc.strip().lower() == "true":
            return True
        return False

    def upload_files(
        self, file_paths: List[str],
        targets: List[Tuple[str, str]],
        product: str, root="/"
    ) -> List[str]:
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
        main_target = targets[0]
        main_bucket_name = main_target[0]
        main_bucket = self.__get_bucket(main_bucket_name)
        key_prefix = main_target[1]
        extra_targets = targets[1:] if len(targets) > 1 else []
        extra_prefixed_buckets: List[Tuple[s3.Bucket, str]] = []
        if len(extra_targets) > 0:
            for target in extra_targets:
                extra_prefixed_buckets.append((self.__get_bucket(target[0]), target[1]))

        async def path_upload_handler(
            full_file_path: str, path: str, index: int,
            total: int, failed: List[str]
        ):
            async with self.__con_sem:
                if not os.path.isfile(full_file_path):
                    logger.warning(
                        'Warning: file %s does not exist during uploading. Product: %s',
                        full_file_path, product
                    )
                    failed.append(full_file_path)
                    return

                logger.debug(
                    '(%d/%d) Uploading %s to bucket %s',
                    index, total, full_file_path, main_bucket_name
                )
                main_path_key = os.path.join(key_prefix, path) if key_prefix else path
                main_file_object: s3.Object = main_bucket.Object(main_path_key)
                existed = False
                try:
                    existed = await self.__run_async(self.__file_exists, main_file_object)
                except (ClientError, HTTPClientError) as e:
                    logger.error(
                        "Error: file existence check failed due to error: %s", e
                    )
                    failed.append(full_file_path)
                    return
                sha1 = read_sha1(full_file_path)
                (content_type, _) = mimetypes.guess_type(full_file_path)
                if not content_type:
                    content_type = DEFAULT_MIME_TYPE
                if not existed:
                    f_meta = {}
                    if sha1.strip() != "":
                        f_meta[CHECKSUM_META_KEY] = sha1
                    try:
                        if not self.__dry_run:
                            if len(f_meta) > 0:
                                await self.__run_async(
                                    functools.partial(
                                        main_file_object.put,
                                        Body=open(full_file_path, "rb"),
                                        Metadata=f_meta,
                                        ContentType=content_type
                                    )
                                )
                            else:
                                await self.__run_async(
                                    functools.partial(
                                        main_file_object.upload_file,
                                        Filename=full_file_path,
                                        ExtraArgs={'ContentType': content_type}
                                    )
                                )
                            if product:
                                await self.__update_prod_info(
                                    main_path_key, main_bucket_name, [product]
                                )

                        logger.debug('Uploaded %s to bucket %s', path, main_bucket_name)
                    except (ClientError, HTTPClientError) as e:
                        logger.error("ERROR: file %s not uploaded to bucket"
                                     " %s due to error: %s ", full_file_path,
                                     main_bucket_name, e)
                        failed.append(full_file_path)
                        return
                else:
                    await handle_existed(
                        full_file_path, sha1, main_path_key,
                        main_bucket_name, main_file_object
                    )

                # do copy:
                for target_ in extra_prefixed_buckets:
                    extra_bucket = target_[0]
                    extra_bucket_name = extra_bucket.name
                    extra_prefix = target_[1]
                    extra_path_key = os.path.join(extra_prefix, path) if extra_prefix else path
                    logger.debug(
                        'Copyinging %s from bucket %s to bucket %s',
                        full_file_path, main_bucket_name, extra_bucket
                    )
                    file_object: s3.Object = extra_bucket.Object(extra_path_key)
                    existed = await self.__run_async(self.__file_exists, file_object)
                    if not existed:
                        if not self.__dry_run:
                            try:
                                await self.__copy_between_bucket(
                                    main_bucket_name, main_path_key,
                                    extra_bucket, extra_path_key
                                )
                                if product:
                                    await self.__update_prod_info(
                                        extra_path_key, extra_bucket_name, [product]
                                    )
                            except (ClientError, HTTPClientError) as e:
                                logger.error("ERROR: copying failure happend for file %s to bucket"
                                             " %s due to error: %s ", full_file_path,
                                             extra_bucket_name, e)
                                failed.append(full_file_path)
                    else:
                        await handle_existed(
                            full_file_path, sha1, extra_path_key,
                            extra_bucket_name, file_object
                        )

        async def handle_existed(
            file_path, file_sha1, path_key,
            bucket_name, file_object
        ) -> bool:
            logger.debug(
                "File %s already exists in bucket %s, check if need to update product.",
                path_key, bucket_name
            )
            f_meta = file_object.metadata
            checksum = (
                f_meta[CHECKSUM_META_KEY] if CHECKSUM_META_KEY in f_meta else ""
            )
            if checksum != "" and checksum.strip() != file_sha1:
                logger.warning('Warning: checksum check failed. The file %s is '
                               'different from the one in S3 bucket %s. Product: %s',
                               path_key, bucket_name, product)
                return False
            (prods, no_error) = await self.__run_async(
                self.__get_prod_info,
                path_key, bucket_name
            )
            if not self.__dry_run and no_error and product not in prods:
                logger.debug(
                    "File %s has new product, updating the product %s",
                    file_path,
                    product,
                )
                prods.append(product)
                result = await self.__update_prod_info(
                    path_key, bucket_name, prods
                )
                if not result:
                    return False
                return True

        return self.__do_path_cut_and(
            file_paths=file_paths,
            path_handler=self.__path_handler_count_wrapper(path_upload_handler),
            root=root
        )

    async def __copy_between_bucket(
        self, source: str, source_key: str,
        target: s3.Bucket, target_key: str
    ) -> bool:
        logger.debug(
            "Copying file %s from bucket %s to target %s as %s",
            source_key, source, target.name, target_key)
        copy_source = {
            'Bucket': source,
            'Key': source_key
        }
        try:
            await self.__run_async(
                functools.partial(
                    target.copy,
                    CopySource=copy_source,
                    Key=target_key
                )
            )
            logger.debug('Copy done')
            return True
        except (ClientError, HTTPClientError) as e:
            logger.error(
                "ERROR: Can not copy file %s to bucket %s due to error: %s",
                source_key, target.name, e
            )
            return False

    def upload_metadatas(
        self, meta_file_paths: List[str],
        target: Tuple[str, str],
        product: Optional[str] = None, root="/"
    ) -> List[str]:
        """ Upload a list of metadata files to s3 bucket. This function is very similar to
        upload_files, except:
            * The metadata files will always be overwritten for each uploading
            * The metadata files' checksum will also be overwritten each time
            * Return all failed to upload metadata files due to exceptions
        """
        bucket_name = target[0]
        bucket = self.__get_bucket(bucket_name)

        async def path_upload_handler(
            full_file_path: str, path: str, index: int,
            total: int, failed: List[str]
        ):
            async with self.__con_sem:
                if not os.path.isfile(full_file_path):
                    logger.warning(
                        'Warning: file %s does not exist during uploading. Product: %s',
                        full_file_path, product
                    )
                    failed.append(full_file_path)
                    return

                logger.debug(
                    '(%d/%d) Updating metadata %s to bucket %s',
                    index, total, path, bucket_name
                )

                key_prefix = target[1]
                path_key = os.path.join(key_prefix, path) if key_prefix else path
                file_object: s3.Object = bucket.Object(path_key)
                existed = False
                try:
                    existed = await self.__run_async(self.__file_exists, file_object)
                except (ClientError, HTTPClientError) as e:
                    logger.error(
                        "Error: file existence check failed due to error: %s", e
                    )
                    failed.append(full_file_path)
                    return
                f_meta = {}
                need_overwritten = True
                sha1 = read_sha1(full_file_path)
                (content_type, _) = mimetypes.guess_type(full_file_path)
                if not content_type:
                    content_type = DEFAULT_MIME_TYPE
                if existed:
                    f_meta = file_object.metadata
                    need_overwritten = (
                        CHECKSUM_META_KEY not in f_meta or sha1 != f_meta[CHECKSUM_META_KEY]
                    )

                f_meta[CHECKSUM_META_KEY] = sha1
                try:
                    if not self.__dry_run:
                        if need_overwritten:
                            await self.__run_async(
                                functools.partial(
                                    file_object.put,
                                    Body=open(full_file_path, "rb"),
                                    Metadata=f_meta,
                                    ContentType=content_type
                                )
                            )
                        if product:
                            # NOTE: This should not happen for most cases, as most
                            # of the metadata file does not have product info. Just
                            # leave for requirement change in future
                            # This is now used for npm version-level package.json
                            prods = [product]
                            if existed:
                                (prods, no_error) = await self.__run_async(
                                    self.__get_prod_info,
                                    path_key, bucket_name
                                )
                                if not no_error:
                                    failed.append(full_file_path)
                                    return
                                if no_error and product not in prods:
                                    prods.append(product)
                            updated = await self.__update_prod_info(
                                path_key, bucket_name, prods
                            )
                            if not updated:
                                failed.append(full_file_path)
                                return
                    logger.debug('Updated metadata %s to bucket %s', path, bucket_name)
                except (ClientError, HTTPClientError) as e:
                    logger.error(
                        "ERROR: file %s not uploaded to bucket"
                        " %s due to error: %s ",
                        full_file_path, bucket_name, e
                    )
                    failed.append(full_file_path)

        return self.__do_path_cut_and(
            file_paths=meta_file_paths,
            path_handler=self.__path_handler_count_wrapper(path_upload_handler),
            root=root
        )

    def upload_manifest(
            self, manifest_name: str, manifest_full_path: str, target: str,
            manifest_bucket_name: str
    ):
        target = target if target else "default"
        path_key = os.path.join(target, manifest_name)
        manifest_bucket = self.__get_bucket(manifest_bucket_name)
        try:
            file_object: s3.Object = manifest_bucket.Object(path_key)
            file_object.upload_file(
                Filename=manifest_full_path,
                ExtraArgs={'ContentType': DEFAULT_MIME_TYPE}
            )
        except S3UploadFailedError:
            logger.warning(
                'Warning: Manifest bucket %s does not exist in S3, will ignore uploading of '
                'manifest file %s', manifest_bucket_name, manifest_name)

    def delete_files(
        self, file_paths: List[str], target: Tuple[str, str],
        product: Optional[str], root="/"
    ) -> List[str]:
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
        bucket_name = target[0]
        bucket = self.__get_bucket(bucket_name)

        async def path_delete_handler(
            full_file_path: str, path: str, index: int,
            total: int, failed: List[str]
        ):
            async with self.__con_sem:
                key_prefix = target[1]
                logger.debug('(%d/%d) Deleting %s from bucket %s', index, total, path, bucket_name)
                path_key = os.path.join(key_prefix, path) if key_prefix else path
                file_object = bucket.Object(path_key)
                existed = False
                try:
                    existed = await self.__run_async(self.__file_exists, file_object)
                except (ClientError, HTTPClientError) as e:
                    logger.error(
                        "Error: file existence check failed due to error: %s", e
                    )
                    failed.append(full_file_path)
                    return
                if existed:
                    # NOTE: If we're NOT using the product key to track collisions
                    # (in the case of metadata), then this prods array will remain
                    # empty, and we will just delete the file, below. Otherwise,
                    # the product reference counts will be used (from object metadata).
                    prods = []
                    if product:
                        (prods, no_error) = await self.__run_async(
                            self.__get_prod_info,
                            path_key, bucket_name
                        )
                        if not no_error:
                            return False
                        if product in prods:
                            prods.remove(product)

                    if len(prods) > 0:
                        try:
                            logger.debug(
                                "File %s has other products overlapping,"
                                " will remove %s from its metadata",
                                path, product
                            )
                            await self.__update_prod_info(path_key, bucket_name, prods)
                            logger.debug(
                                "Removed product %s from metadata of file %s",
                                product, path
                            )
                            return
                        except (ClientError, HTTPClientError) as e:
                            logger.error(
                                "ERROR: Failed to update metadata of file"
                                " %s due to error: %s ", path, e
                            )
                            failed.append(full_file_path)
                            return
                    elif len(prods) == 0:
                        try:
                            if not self.__dry_run:
                                await self.__run_async(
                                    functools.partial(
                                        bucket.delete_objects,
                                        Delete={"Objects": [{"Key": path_key}]}
                                    )
                                )
                                updated = await self.__update_prod_info(
                                    path_key, bucket_name, prods
                                )
                                if not updated:
                                    failed.append(full_file_path)
                                    return
                            logger.info("Deleted %s from bucket %s", path, bucket_name)
                            return
                        except (ClientError, HTTPClientError) as e:
                            logger.error(
                                "ERROR: file %s failed to delete from bucket"
                                " %s due to error: %s ",
                                full_file_path, bucket_name, e
                            )
                            failed.append(full_file_path)
                            return
                else:
                    logger.debug(
                        "File %s does not exist in s3 bucket %s, skip deletion.",
                        path, bucket_name
                    )
                    return

        failed_files = self.__do_path_cut_and(
            file_paths=file_paths,
            path_handler=self.__path_handler_count_wrapper(path_delete_handler),
            root=root
        )

        return failed_files

    def delete_manifest(self, product_key: str, target: str, manifest_bucket_name: str):
        if not manifest_bucket_name:
            logger.warning(
                'Warning: No manifest bucket is provided, will ignore the process of manifest '
                'deleting')
            return
        manifest_name = product_key + MANIFEST_SUFFIX
        target = target if target else "default"
        path_key = os.path.join(target, manifest_name)

        manifest_bucket = self.__get_bucket(manifest_bucket_name)
        file_object: s3.Object = manifest_bucket.Object(path_key)
        existed = False
        try:
            existed = self.__file_exists(file_object)
        except (ClientError, HTTPClientError) as e:
            logger.error(
                "Error: file existence check failed due to error: %s", e
            )
            return
        if existed:
            manifest_bucket.delete_objects(Delete={"Objects": [{"Key": path_key}]})
        else:
            logger.warning(
                'Warning: Manifest %s does not exist in S3 bucket %s, will ignore its deleting',
                manifest_name, manifest_bucket_name)

    def get_files(self, bucket_name: str, prefix=None, suffix=None) -> Tuple[List[str], bool]:
        """Get the file names from s3 bucket. Can use prefix and suffix to filter the
        files wanted. If some error happend, will return an empty file list and false result
        """
        bucket = self.__get_bucket(bucket_name)
        objs = []
        if prefix and prefix.strip() != "":
            try:
                objs = list(bucket.objects.filter(Prefix=prefix))
            except (ClientError, HTTPClientError) as e:
                logger.error("ERROR: Can not get files under %s in bucket"
                             " %s due to error: %s ", prefix,
                             bucket_name, e)
                return ([], False)
        else:
            objs = list(bucket.objects.all())
        files = []
        if suffix and suffix.strip() != "":
            files = [i.key for i in objs if i.key.endswith(suffix)]
        else:
            files = [i.key for i in objs]
        return (files, True)

    def read_file_content(self, bucket_name: str, key: str) -> str:
        bucket = self.__get_bucket(bucket_name)
        file_object = bucket.Object(key)
        return str(file_object.get()['Body'].read(), 'utf-8')

    def list_folder_content(self, bucket_name: str, folder: str) -> List[str]:
        """List the content in folder in an s3 bucket. Note it's not recursive,
           which means the content only contains the items in that folder, but
           not in its subfolders.
        """
        bucket = self.__get_bucket(bucket_name)
        try:
            if not folder or folder.strip() == "/" or folder.strip() == "":
                result = bucket.meta.client.list_objects(
                    Bucket=bucket.name,
                    Delimiter='/'
                )
            else:
                prefix = folder if folder.endswith("/") else folder+"/"
                result = bucket.meta.client.list_objects(
                    Bucket=bucket.name,
                    Prefix=prefix,
                    Delimiter='/'
                )
        except (ClientError, HTTPClientError) as e:
            logger.error("ERROR: Can not get contents of %s from bucket"
                         " %s due to error: %s ", folder,
                         bucket_name, e)
            return []

        contents = []
        folders = result.get("CommonPrefixes")
        if folders:
            contents.extend([f.get("Prefix") for f in folders])
        files = result.get("Contents")
        if files:
            contents.extend([f.get("Key") for f in files])
        return contents

    def file_exists_in_bucket(
        self, bucket_name: str, path: str
    ) -> bool:
        bucket = self.__get_bucket(bucket_name)
        file_object = bucket.Object(path)
        return self.__file_exists(file_object)

    def __get_bucket(self, bucket_name: str) -> s3.Bucket:
        self.__lock.acquire()
        try:
            bucket = self.__buckets.get(bucket_name)
            if bucket:
                return bucket
            logger.debug("Cache aws bucket %s", bucket_name)
            bucket = self.__client.Bucket(bucket_name)
            self.__buckets[bucket_name] = bucket
            return bucket
        finally:
            self.__lock.release()

    def __file_exists(self, file_object: Object) -> bool:
        try:
            file_object.load()
            return True
        except (ClientError, HTTPClientError) as e:
            if isinstance(e, ClientError) and e.response["Error"]["Code"] == "404":
                return False
            else:
                raise e

    def __get_prod_info(
        self, file: str, bucket_name: str
    ) -> Tuple[List[str], bool]:
        logger.debug("Getting product infomation for file %s", file)
        prod_info_file = file + PROD_INFO_SUFFIX
        try:
            info_file_content = self.read_file_content(bucket_name, prod_info_file)
            prods = [p.strip() for p in info_file_content.split("\n")]
            logger.debug("Got product information as below %s", prods)
            return (prods, True)
        except (ClientError, HTTPClientError) as e:
            logger.warning("WARN: Can not get product info for file %s "
                           "due to error: %s", file, e)
            return ([], False)

    async def __update_prod_info(
        self, file: str, bucket_name: str, prods: List[str]
    ) -> bool:
        prod_info_file = file + PROD_INFO_SUFFIX
        bucket = self.__get_bucket(bucket_name)
        file_obj = bucket.Object(prod_info_file)
        content_type = "text/plain"
        if len(prods) > 0:
            logger.debug("Updating product infomation for file %s "
                         "with products: %s", file, prods)
            try:
                await self.__run_async(
                    functools.partial(
                        file_obj.put,
                        Body="\n".join(prods).encode("utf-8"),
                        ContentType=content_type
                    )
                )
                logger.debug("Updated product infomation for file %s", file)
                return True
            except (ClientError, HTTPClientError) as e:
                logger.warning("WARNING: Can not update product info for file %s "
                               "due to error: %s", file, e)
                return False
        else:
            logger.debug("Removing product infomation file for file %s "
                         "because no products left", file)
            try:
                result = await self.__run_async(
                    self.__file_exists,
                    file_obj
                )
                if result:
                    await self.__run_async(
                        functools.partial(
                            bucket.delete_objects,
                            Delete={"Objects": [{"Key": prod_info_file}]}
                        )
                    )
                    logger.debug("Removed product infomation file for file %s", file)
                return True
            except (ClientError, HTTPClientError) as e:
                logger.warning("WARNING: Can not delete product info file for file %s "
                               "due to error: %s", file, e)
                return False

    def __path_handler_count_wrapper(
        self,
        path_handler: Callable[[str, str, int, int, List[str], asyncio.Semaphore], Awaitable[bool]]
    ) -> Callable[[str, str, int, int, List[str], asyncio.Semaphore], Awaitable[bool]]:
        async def wrapper(
            full_file_path: str, path: str, index: int,
            total: int, failed: List[str]
        ):
            try:
                await path_handler(full_file_path, path, index, total, failed)
            finally:
                if index % FILE_REPORT_LIMIT == 0:
                    logger.info("######### %d/%d files finished", index, total)
        return wrapper

    def __do_path_cut_and(
        self, file_paths: List[str],
        path_handler: Callable[[str, str, int, int, List[str], asyncio.Semaphore], Awaitable[bool]],
        root="/"
    ) -> List[str]:
        slash_root = root
        if not root.endswith("/"):
            slash_root = slash_root + "/"
        failed_paths = []
        index = 1
        file_paths_count = len(file_paths)
        tasks = []
        for full_path in file_paths:
            path = full_path
            if path.startswith(slash_root):
                path = path[len(slash_root):]
            tasks.append(
                asyncio.ensure_future(
                    path_handler(full_path, path, index, file_paths_count, failed_paths)
                )
            )
            index += 1

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))
        return failed_paths

    async def __run_async(self, fn: Callable, *args) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, fn, *args)

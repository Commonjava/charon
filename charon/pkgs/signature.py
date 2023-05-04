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

import os
import subprocess
import asyncio
import logging
import gnupg
from typing import Awaitable, Callable, List, Tuple
from charon.storage import S3Client

logger = logging.getLogger(__name__)


def generate_sign(
    package_type: str,
    artifact_path: List[str],
    top_level: str,
    prefix: str,
    s3_client: S3Client,
    bucket: str,
    key_id: str = None,
    key_file: str = None,
    passphrase: str = None
) -> Tuple[List[str], List[str]]:
    """ This Python function generates a digital signature for a list of metadata files using
    the GPG library for uploads to an Amazon S3 bucket.

        * Does not regenerate the existing metadata files when existing
        * Returning all failed to generate signature files due to exceptions
        * key_id: A string representing the ID of the RSA key to use for signing,
        GPG command line tool is required when this parameter is not None.
        * key_file: A string representing the location of the private key file.
        * passphrase: A string containing the passphrase for the RSA key for key_id or key_file.

    It returns a tuple containing two lists: one with the successfully generated files
    and another with the failed to generate files due to exceptions.
    """

    if key_file is not None:
        gpg = gnupg.GPG(gnupghome='~/.gnupg')
        gpg.import_keys_file(key_file)

    async def sign_file(
        filename: str, failed_paths: List[str], generated_signs: List[str]
    ):
        async with asyncio.BoundedSemaphore(10):
            signature_file = filename + ".asc"
            if prefix:
                remote = os.path.join(prefix, signature_file)
            else:
                remote = signature_file
            local = os.path.join(top_level, signature_file)
            artifact = os.path.join(top_level, filename)

            if not os.path.isfile(os.path.join(prefix, artifact)):
                logger.warning("Artifact needs signature is missing, please check again")
                return

            # skip sign if file already exist locally
            if os.path.isfile(local):
                logger.debug(".asc file %s existed, skipping", local)
                return
            # skip sign if file already exist in bucket
            try:
                existed = s3_client.file_exists_in_bucket(bucket, remote)
            except ValueError as e:
                logger.error(
                    "Error: Can not check signature file status due to: %s", e
                )
                return
            if existed:
                logger.debug(".asc file %s existed, skipping", remote)
                return

            command = [
                'gpg',
                '--batch',
                '--armor',
                '-u', key_id,
                '--passphrase', passphrase,
                '--sign', artifact
            ]

            if key_file is None:
                # use GPG command line tool to sign artifact if key_id is passed
                try:
                    # result = await __run_cmd_async(command)
                    result = subprocess.run(command, capture_output=True, text=True, check=True)
                except subprocess.CalledProcessError as e:
                    logger.error(
                            "Error: signature generation failed due to error: %s", e
                        )
                    failed_paths.append(local)
                    return
                if result.returncode == 0:
                    generated_signs.append(local)
                else:
                    logger.info(
                        "signature failed with exit code %s, message %s",
                        result.returncode, result.stderr.decode()
                    )
            else:
                try:
                    with open(artifact, "rb") as f:
                        gpg.sign_file(f, passphrase=passphrase, output=local, detach=True)
                        generated_signs.append(local)
                except ValueError as e:
                    logger.error(
                            "Error: signature generation failed due to error: %s", e
                        )
                    failed_paths.append(local)

            return

    return __do_path_cut_and(
            file_paths=artifact_path,
            path_handler=sign_file,
            root=top_level
        )


def __do_path_cut_and(
    file_paths: List[str],
    path_handler: Callable[[str, List[str], List[str], asyncio.Semaphore], Awaitable[bool]],
    root="/"
) -> List[str]:
    slash_root = root
    if not root.endswith("/"):
        slash_root = slash_root + "/"
    failed_paths = []
    generated_signs = []
    tasks = []
    for full_path in file_paths:
        path = full_path
        if path.startswith(slash_root):
            path = path[len(slash_root):]
        tasks.append(
            asyncio.ensure_future(
                path_handler(path, failed_paths, generated_signs)
            )
        )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))
    return (failed_paths, generated_signs)


async def __run_cmd_async(cmd):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, subprocess.run, cmd)
    return result

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
from jinja2 import Template
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
    key: str = None,
    command: str = None
) -> Tuple[List[str], List[str]]:
    """ This Python function generates a digital signature for a list of metadata files using
    the GPG library for uploads to an Amazon S3 bucket.

        * Does not regenerate the existing metadata files when existing
        * Returning all failed to generate signature files due to exceptions
        * key: name of the sign key, using inside template to render correct command,
        replace {{ key }} field in command string.
        * command: A string representing the subprocess command to run.

    It returns a tuple containing two lists: one with the successfully generated files
    and another with the failed to generate files due to exceptions.
    """

    async def sign_file(
        filename: str, failed_paths: List[str], generated_signs: List[str],
        sem: asyncio.BoundedSemaphore
    ):
        async with sem:
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

            run_command = Template(command)
            result = await __run_cmd_async(run_command.render(key=key, file=artifact).split())

            if result.returncode == 0:
                generated_signs.append(local)
                logger.debug("Generated signature file: %s", local)
            else:
                failed_paths.append(local)

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
    sem = asyncio.BoundedSemaphore(10)
    for full_path in file_paths:
        path = full_path
        if path.startswith(slash_root):
            path = path[len(slash_root):]
        tasks.append(
            asyncio.ensure_future(
                path_handler(path, failed_paths, generated_signs, sem)
            )
        )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))
    return (failed_paths, generated_signs)


async def __run_cmd_async(cmd):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, subprocess.run, cmd)
    return result

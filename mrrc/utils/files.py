"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/mrrc-uploader)

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
import errno
import hashlib
import os
from enum import Enum


class HashType(Enum):
    """Possible types of hash"""
    MD5 = 0
    SHA1 = 1
    SHA256 = 2


def write_file(file_path: str, content: str):
    if not os.path.isfile(file_path):
        with open(file_path, mode='a'):
            pass
    with open(file_path, mode='w') as f:
        f.write(content)


def read_sha1(file: str) -> str:
    """ This function will read sha1 hash of a file from a ${file}.sha1 file first, which should
    contain the sha1 has of the file. This is a maven repository rule which contains .sha1 files
    for artifact files. We can use this to avoid the digestion of big files which will improve
    performance. BTW, for some files like .md5, .sha1 and .sha256, they don't have .sha1 files as
    they are used for hashing, so we will directly calculate its sha1 hash through digesting.
    """
    if os.path.isfile(file):
        non_search_suffix = [".md5", ".sha1", ".sha256"]
        _, suffix = os.path.splitext(file)
        if suffix not in non_search_suffix:
            sha1_file = file + ".sha1"
            if os.path.isfile(sha1_file):
                with open(sha1_file) as f:
                    return f.read().strip()
        return digest(file)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file)


def digest(file: str, hash_type=HashType.SHA1) -> str:
    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    hash_obj = None
    if hash_type == HashType.MD5:
        hash_obj = hashlib.md5()
    elif hash_type == HashType.SHA1:
        hash_obj = hashlib.sha1()
    elif hash_type == HashType.SHA256:
        hash_obj = hashlib.sha256()
    else:
        raise Exception("Error: Unknown hash type for digesting.")

    with open(file, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            hash_obj.update(data)

    return hash_obj.hexdigest()

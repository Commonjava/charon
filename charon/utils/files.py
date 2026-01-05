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
from enum import Enum
import os
import hashlib
import errno
import tempfile
import shutil
from typing import List, Tuple, Optional
from charon.constants import MANIFEST_SUFFIX


class HashType(Enum):
    """Possible types of hash"""

    MD5 = 0
    SHA1 = 1
    SHA256 = 2
    SHA512 = 3


def get_hash_type(type_str: str) -> HashType:
    """Get hash type from string"""
    type_str_low = type_str.lower()
    if type_str_low == "md5":
        return HashType.MD5
    elif type_str_low == "sha1":
        return HashType.SHA1
    elif type_str_low == "sha256":
        return HashType.SHA256
    elif type_str_low == "sha512":
        return HashType.SHA512
    else:
        raise ValueError("Unsupported hash type: {}".format(type_str))


def overwrite_file(file_path: str, content: str) -> None:
    parent_dir: Optional[str] = os.path.dirname(file_path)
    if parent_dir:
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
    else:
        parent_dir = None  # None explicitly means current directory for tempfile

    # Write to temporary file first, then atomically rename
    fd, temp_path = tempfile.mkstemp(dir=parent_dir, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        shutil.move(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def read_sha1(file: str) -> str:
    """This function will read sha1 hash of a file from a ${file}.sha1 file first, which should
    contain the sha1 has of the file. This is a maven repository rule which contains .sha1 files
    for artifact files. We can use this to avoid the digestion of big files which will improve
    performance. BTW, for some files like .md5, .sha1 and .sha256, they don't have .sha1 files as
    they are used for hashing, so we will directly calculate its sha1 hash through digesting.
    """
    if os.path.isfile(file):
        non_search_suffix = [".md5", ".sha1", ".sha256", ".sha512"]
        _, suffix = os.path.splitext(file)
        if suffix not in non_search_suffix:
            sha1_file = file + ".sha1"
            if os.path.isfile(sha1_file):
                with open(sha1_file, encoding="utf-8") as f:
                    return f.read().strip()
        return digest(file)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file)


def digest(file: str, hash_type=HashType.SHA1) -> str:
    hash_obj = _hash_object(hash_type)

    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
    with open(file, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            hash_obj.update(data)

    return hash_obj.hexdigest()


def digest_content(content: str, hash_type=HashType.SHA1) -> str:
    """This function will caculate the hash value for the string content with the specified
       hash type
    """
    hash_obj = _hash_object(hash_type)
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def _hash_object(hash_type: HashType):
    if hash_type == HashType.SHA1:
        hash_obj = hashlib.sha1()
    elif hash_type == HashType.SHA256:
        hash_obj = hashlib.sha256()
    elif hash_type == HashType.MD5:
        hash_obj = hashlib.md5()
    elif hash_type == HashType.SHA512:
        hash_obj = hashlib.sha512()
    else:
        raise ValueError("Error: Unknown hash type for digesting.")
    return hash_obj


def write_manifest(paths: List[str], root: str, product_key: str) -> Tuple[str, str]:
    manifest_name = product_key + MANIFEST_SUFFIX
    manifest_path = os.path.join(root, manifest_name)
    artifacts = []
    for path in paths:
        rel_path = os.path.relpath(path, root)
        artifacts.append(rel_path)

    overwrite_file(manifest_path, '\n'.join(artifacts))
    return manifest_name, manifest_path

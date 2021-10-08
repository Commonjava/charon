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
import logging
import sys

MRRC_INFO_LOGGER_FORMAT = "%(message)s"
MRRC_DEBUG_LOGGER_FORMAT = "%(asctime)s : %(levelname)s - %(message)s"
DEFAULT_LOGGER = "mrrc-uploader"


def set_logging(name=DEFAULT_LOGGER, level=logging.DEBUG, handler=None):
    # create logger
    logger = logging.getLogger(name)
    for hdlr in list(logger.handlers):  # make a copy so it doesn't change
        logger.removeHandler(hdlr)

    logger.setLevel(level)

    if not handler:
        # create console handler and set level to debug
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # create formatter
        formatter = logging.Formatter(MRRC_INFO_LOGGER_FORMAT)
        if level <= logging.DEBUG:
            formatter = logging.Formatter(MRRC_DEBUG_LOGGER_FORMAT)

        # add formatter to ch
        handler.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(handler)

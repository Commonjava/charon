"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
from locale import nl_langinfo, CODESET
from os import fdopen, dup

from charon.constants import CHARON_LOGGING_FMT


class EncodedStream(object):
    # The point of this class is to force python to encode UTF-8
    # over stderr.  Normal techniques were not working, so we dup
    # the file handler and force it UTF-8.  :-(
    def __init__(self, fileno, encoding):
        self.binarystream = fdopen(dup(fileno), 'wb')
        self.encoding = encoding

    def write(self, text):
        if not isinstance(text, bytes):
            self.binarystream.write(text.encode(self.encoding))
        else:
            self.binarystream.write(text)
        # We need to flush regularly, because launching plugins or running
        # subprocess calls breaks serialization of logging output otherwise
        self.binarystream.flush()

    def __del__(self):
        try:
            self.binarystream.close()
        except AttributeError:
            pass


def set_logging(name="charon", level=logging.DEBUG, handler=None):
    # create logger
    logger = logging.getLogger(name)
    for hdlr in list(logger.handlers):  # make a copy so it doesn't change
        logger.removeHandler(hdlr)

    logger.setLevel(level)

    # create formatter
    formatter = logging.Formatter(fmt=CHARON_LOGGING_FMT)

    if not handler:
        # create console handler and set level to debug
        log_encoding = nl_langinfo(CODESET)
        encoded_stream = EncodedStream(sys.stderr.fileno(), log_encoding)
        handler = logging.StreamHandler(encoded_stream)
        handler.setLevel(logging.DEBUG)

        # add formatter to ch
        handler.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(handler)

    logger = logging.getLogger('charon')
    for hdlr in list(logger.handlers):  # make a copy so it doesn't change
        hdlr.setFormatter(formatter)


def getLogger(name: str) -> logging:
    error_log = "./errors.log"
    handler = logging.FileHandler(error_log)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.WARN)

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger

from locale import nl_langinfo, CODESET
from os import fdopen, dup
import logging
import sys

MRRC_INFO_LOGGER_FORMAT='%(asctime)s : %(message)s'
MRRC_DEBUG_LOGGER_FORMAT='%(asctime)s : %(levelname)s - %(message)s'
DEFAULT_LOGGER = "mrrc-uploader"

class EncodedStream(object):
    # The point of this class is to force python to enocde UTF-8
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

def set_logging(name=DEFAULT_LOGGER, level=logging.DEBUG, handler=None):
    # create logger
    logger = logging.getLogger(name)
    for hdlr in list(logger.handlers):  # make a copy so it doesn't change
        logger.removeHandler(hdlr)

    logger.setLevel(level)

    if not handler:
        # create console handler and set level to debug
        log_encoding = nl_langinfo(CODESET)
        encoded_stream = EncodedStream(sys.stderr.fileno(), log_encoding)
        handler = logging.StreamHandler(encoded_stream)
        handler.setLevel(level)
        
        # create formatter
        formatter = logging.Formatter(MRRC_INFO_LOGGER_FORMAT)
        if level<=logging.DEBUG:
            formatter = logging.Formatter(MRRC_DEBUG_LOGGER_FORMAT)

        # add formatter to ch
        handler.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(handler)
from locale import nl_langinfo, CODESET
from os import fdopen, dup
import logging
import sys

MRRC_INFO_LOGGER_FORMAT='%(message)s'
MRRC_DEBUG_LOGGER_FORMAT='%(asctime)s : %(levelname)s - %(message)s'
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
        if level<=logging.DEBUG:
            formatter = logging.Formatter(MRRC_DEBUG_LOGGER_FORMAT)

        # add formatter to ch
        handler.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(handler)
import logging
from decouple import config

LOGLEVEL = config("LOGLEVEL", default=logging.DEBUG)
LOGFORMAT = config(
    "LOGFORMAT",
    default="::::%(asctime)s::::%(levelname)s::::%(filename)s:%(funcName)s():%(lineno)d::::%(message)s::::",
)
LOGFILE = config("LOGFILE", default="log.log")


def get_logger():
    fmt = logging.Formatter(LOGFORMAT)

    # init logger
    logger = logging.getLogger(__name__)
    logger.setLevel(LOGLEVEL)

    # add filehandler:
    fh = logging.FileHandler(LOGFILE)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # add streamhandler
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


logger = get_logger()

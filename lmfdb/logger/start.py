from logging import (FileHandler, getLogger, StreamHandler, Formatter,
                     INFO, WARNING, DEBUG,
                     info, warning)

from sage.version import version as sage_version

from .utils import LmfdbFormatter

# logfocus
logfocus = None
def get_logfocus():
    # set by start_logging
    return logfocus

file_handler = None
def logger_file_handler():
    # set by start_logging
    return file_handler

LMFDB_SAGE_VERSION = '7.1'
def check_sage_version():
    if [int(c) for c in sage_version.split(".")[:2]] < [int(c) for c in LMFDB_SAGE_VERSION.split(".")[:2]]:
        warning("*** WARNING: SAGE VERSION %s IS OLDER THAN %s ***"%(sage_version,LMFDB_SAGE_VERSION))

def start_logging():
    global logfocus, file_handler
    from lmfdb.utils.config import Configuration
    config = Configuration()
    logging_options = config.get_logging()

    file_handler = FileHandler(logging_options['logfile'])
    file_handler.setLevel(WARNING)

    if 'logfocus' in logging_options:
        logfocus = logging_options['logfocus']
        getLogger(logfocus).setLevel(DEBUG)

    root_logger = getLogger()
    root_logger.setLevel(INFO)
    root_logger.name = "LMFDB"

    formatter = Formatter(LmfdbFormatter.fmtString.split(r'[')[0])
    ch = StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    cfg = config.get_all()
    if "postgresql_options" and "password" in cfg["postgresql_options"]:
        cfg["postgresql_options"]["password"] = "****"
    info("Configuration = {}".format(cfg) )
    check_sage_version()



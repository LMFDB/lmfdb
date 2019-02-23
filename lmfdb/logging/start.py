from logging import (FileHandler, getLogger, StreamHandler, Formatter,
                     WARNING, DEBUG, INFO,
                     info)

from sage.version import version as sage_version

from .utils import LmfdbFormatter

# logfocus
logfocus = None
def set_logfocus(lf):
    global logfocus
    logfocus = lf

def get_logfocus():
    return logfocus

LMFDB_SAGE_VERSION = '7.1'
def check_sage_version():
    if [int(c) for c in sage_version.split(".")[:2]] < [int(c) for c in LMFDB_SAGE_VERSION.split(".")[:2]]:
        warning("*** WARNING: SAGE VERSION %s IS OLDER THAN %s ***"%(sage_version,LMFDB_SAGE_VERSION))

def start_logging():
    from lmfdb.utils.config import Configuration
    config = Configuration()
    logging_options = config.get_logging()
    file_handler = FileHandler(logging_options['logfile'])

    file_handler.setLevel(WARNING)
    if 'logfocus' in logging_options:
        set_logfocus(logging_options['logfocus'])
        getLogger(get_logfocus()).setLevel(DEBUG)

    root_logger = getLogger()
    root_logger.setLevel(INFO)
    root_logger.name = "LMFDB"

    formatter = Formatter(LmfdbFormatter.fmtString.split(r'[')[0])
    ch = StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    app.logger.addHandler(file_handler)
    info("Configuration = %s" % config.get_all())
    check_sage_version()



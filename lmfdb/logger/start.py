from logging import (FileHandler, getLogger, StreamHandler, Formatter,
                     INFO, WARNING,
                     info, warning)

from sage.version import version as sage_version

from .utils import LmfdbFormatter

LMFDB_SAGE_VERSION = '9.3'
def check_sage_version():
    if [int(c) for c in sage_version.split(".")[:2]] < [int(c) for c in LMFDB_SAGE_VERSION.split(".")[:2]]:
        warning("*** WARNING: SAGE VERSION %s IS OLDER THAN %s ***" % (sage_version,LMFDB_SAGE_VERSION))

def start_logging():
    from lmfdb.utils.config import Configuration
    config = Configuration()
    logging_options = config.get_logging()

    root_logger = getLogger()
    root_logger.name = "LMFDB"
    root_logger.setLevel(logging_options.get('loglevel', INFO))

    file_handler = FileHandler(logging_options['logfile'])
    file_handler.setLevel(WARNING)

    stream_handler = StreamHandler()
    formatter = Formatter(LmfdbFormatter.fmtString.split('[')[0])
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    cfg = config.get_all()
    if "postgresql_options" and "password" in cfg["postgresql_options"]:
        cfg["postgresql_options"]["password"] = "****"
    info("Configuration = {}".format(cfg) )
    check_sage_version()

################################################################################
#  logging utilities
################################################################################
import logging
import os


class LmfdbFormatter(logging.Formatter):
    """
    This Formatter adds some colors, in the future it might do even more ;)

    TODO: the _hl highlighting condition could be a function
          evaluating to true or false
    """
    fmtString = '%(levelname)s:%(name)s@%(asctime)s: %(message)s [%(pathname)s]'

    def __init__(self, *args, **kwargs):
        self._hl = kwargs.pop('hl', None)
        self._fmt_orig = kwargs.pop('fmt', None)
        logging.Formatter.__init__(self, self._fmt_orig, *args, **kwargs)

    def format(self, record):
        """modify the _mft string, call superclasses format method"""
        # reset fmt string
        self._fmt = self._fmt_orig or LmfdbFormatter.fmtString
        fn = os.path.split(record.pathname)[-1]
        record.pathname = "%s:%s" % (fn, record.lineno)

        # some colors for severity level
        if record.levelno >= logging.CRITICAL:
            self._fmt = '\033[31m' + self._fmt
        elif record.levelno >= logging.ERROR:
            self._fmt = '\033[35m' + self._fmt
        elif record.levelno >= logging.WARNING:
            self._fmt = '\033[33m' + self._fmt
        elif record.levelno <= logging.DEBUG:
            self._fmt = '\033[34m' + self._fmt
        elif record.levelno <= logging.INFO:
            self._fmt = '\033[32m' + self._fmt

        # bold, if module name matches
        if record.name == self._hl:
            self._fmt = "\033[1m" + self._fmt

        # reset, to unaffect the next line
        self._fmt += '\033[0m'

        return logging.Formatter.format(self, record)



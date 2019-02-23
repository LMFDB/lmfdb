################################################################################
#  logging utilities
################################################################################

import logging, os

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


def make_logger(bp_or_name, hl = False, extraHandlers = [] ):
    """
    creates a logger for the given blueprint. if hl is set
    to true, the corresponding lines will be bold.
    """
    import flask
    from .start import get_logfocus
    logfocus = get_logfocus()
    if type(bp_or_name) == flask.Blueprint:
        name = bp_or_name.name
    else:
        assert isinstance(bp_or_name, basestring)
        name = bp_or_name
    l = logging.getLogger(name)
    l.propagate = False
    if logfocus is None:
        l.setLevel(logging.INFO)
    elif logfocus == name:
        # this will NEVER BE TRUE, because logfocus is set AFTER
        # we have created all of the loggers. This is ok for now,
        # because we are setting the log level later when we set
        # the logfocus variable.
        #
        # Maybe someday someone will rewrite this so that it makes
        # sense...
        l.setLevel(logging.DEBUG)
    else:
        l.setLevel(logging.WARNING)
    if len(l.handlers) == 0:
        formatter = LmfdbFormatter(hl=name if hl else None)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        l.addHandler(ch)
        for elt in extraHandlers:
            l.addHandler(elt)
    return l

# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.utils import comma, make_logger

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("hmf")

the_HMFstats = None

def get_stats():
    global the_HMFstats
    if the_HMFstats is None:
        the_HMFstats = HMFstats()
    return the_HMFstats

class HMFstats(object):
    """
    Class for creating and displaying statistics for Hilbert modular forms
    """

    def __init__(self):
        logger.debug("Constructing an instance of HMFstats")
        self.fields = lmfdb.base.getDBConnection().hmfs.fields
        self.forms = lmfdb.base.getDBConnection().hmfs.forms
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_hmf_count()
        return self._counts

    def stats(self):
        self.init_hmf_count()
        self.init_hmf_stats()
        return self._stats

    def init_hmf_count(self):
        if self._counts:
            return
        logger.debug("Computing HMF counts...")
        forms = self.forms
        fields = self.fields
        counts = {}
        nforms = forms.count()
        counts['nforms']  = nforms
        counts['nforms_c']  = comma(nforms)
        nfields = fields.count()
        counts['nfields']  = nfields
        counts['nfields_c']  = comma(nfields)
        max_deg = fields.find().sort('degree', DESCENDING).limit(1)[0]['degree']
        counts['max_deg'] = max_deg
        counts['max_deg_c'] = comma(max_deg)
        self._counts  = counts
        logger.debug("... finished computing HMF counts.")
        #logger.debug("%s" % self._counts)



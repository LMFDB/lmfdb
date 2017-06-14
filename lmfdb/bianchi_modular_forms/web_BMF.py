# -*- coding: utf-8 -*-
from lmfdb.base import getDBConnection
from lmfdb.utils import make_logger
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField, field_pretty
from lmfdb.ecnf.WebEllipticCurve import make_field
from lmfdb.nfutils.psort import primes_iter, ideal_from_label
from lmfdb.utils import web_latex
from flask import url_for

from sage.all import QQ, polygen

logger = make_logger("bmf")

bmf_dims = None
bmf_forms = None

def db_dims():
    global bmf_dims
    if bmf_dims is None:
        bmf_dims = getDBConnection().bmfs.dimensions
    return bmf_dims

def db_forms():
    global bmf_forms
    if bmf_forms is None:
        bmf_forms = getDBConnection().bmfs.forms
    return bmf_forms

nf_fields = None

def db_nf_fields():
    global nf_fields
    if nf_fields is None:
        nf_fields = getDBConnection().numberfields.fields
    return nf_fields

from lmfdb.hilbert_modular_forms.web_HMF import construct_full_label

class WebBMF(object):
    """
    Class for an Bianchi Newform
    """
    def __init__(self, dbdata):
        """Arguments:

            - dbdata: the data from the database

        dbdata is expected to be a database entry from which the class
        is initialised.

        """
        logger.debug("Constructing an instance of WebBMF class from database")
        self.__dict__.update(dbdata)
        # All other fields are handled here
        self.make_form()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific Hilbert newform in the forms
        collection by its label.
        """
        data = db_forms().find_one({"label" : label})

        if data:
            return WebBMF(data)
        raise ValueError("Bianchi newform %s not found" % label)
        # caller must catch this and raise an error


    def make_form(self):
        # To start with the data fields of self are just those from
        # the database.  We need to reformat these and compute some
        # further (easy) data about it.
        #
        self.field = make_field(self.field_label)
        pretty_field = field_pretty(self.field_label)
        print self.label
        self.field_knowl = nf_display_knowl(self.field_label, getDBConnection(), pretty_field)
        dims = db_dims().find_one({'field_label':self.field_label})['dimension_data']
        self.newspace_dimension = dims['2']['new_dim']
        K = self.field.K()
        self.hecke_table = [[web_latex(p.norm()),
                             web_latex(p.gens_reduced()[0]),
                             web_latex(ap)] for p,ap in zip(primes_iter(K), self.hecke_eigs)]
        level = ideal_from_label(K,self.level_label)
        badp = level.prime_factors()
        self.AL_table = [[web_latex(p.norm()),
                          web_latex(p.gens_reduced()[0]),
                          web_latex(ap)] for p,ap in zip(badp, self.AL_eigs)]
        self.properties2 = [('Base field', pretty_field),
                            ('Weight', str(self.weight)),
                            ('Level norm', str(self.level_norm)),
                            ('Level', self.level_ideal),
                            ('Label', self.label)
                            ]
        if self.is_base_change == '?':
            self.bc = 'not determined'
        else:
            self.bc = 'Yes' if self.is_base_change else "No"
            self.properties2.append(('Base-change', self.bc))
        if self.is_CM == '?':
            self.cm = 'not determined'
        else:
            self.cm = 'Yes' if self.is_CM else "No"
            self.properties2.append(('CM', self.cm))
        self.friends = [('Elliptic curve isogeny class {}'.format(self.label),url_for("ecnf.show_ecnf_isoclass", nf=self.field_label, conductor_label=self.level_label, class_label=self.label_suffix))]

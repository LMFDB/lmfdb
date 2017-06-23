# -*- coding: utf-8 -*-
from lmfdb.base import getDBConnection
from lmfdb.utils import make_logger
from lmfdb.WebNumberField import nf_display_knowl, field_pretty
from lmfdb.ecnf.WebEllipticCurve import make_field
from lmfdb.nfutils.psort import primes_iter, ideal_from_label
from lmfdb.utils import web_latex
from flask import url_for
from sage.all import QQ, PolynomialRing, NumberField

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

nfcurves = None
def db_ecnf():
    global nfcurves
    if nfcurves is None:
        nfcurves = getDBConnection().elliptic_curves.nfcurves
    return nfcurves

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
        self.field_knowl = nf_display_knowl(self.field_label, getDBConnection(), pretty_field)
        dims = db_dims().find_one({'field_label':self.field_label})['gl2_dims']
        self.newspace_dimension = dims[str(self.weight)]['new_dim']
        self.newspace_label = "-".join([self.field_label,self.level_label])
        self.newspace_url = url_for(".render_bmf_space_webpage", field_label=self.field_label, level_label=self.level_label)
        K = self.field.K()

        if self.dimension>1:
            Qx = PolynomialRing(QQ,'x')
            self.hecke_poly = Qx(str(self.hecke_poly))
            F = NumberField(self.hecke_poly,'z')
            self.hecke_poly = web_latex(self.hecke_poly)
            def conv(ap):
                if '?' in ap:
                    return '?'
                else:
                    return F(str(ap))

            self.hecke_eigs = [conv(ap) for ap in self.hecke_eigs]
        self.nap = len(self.hecke_eigs)
        self.nap0 = min(25, self.nap)
        self.hecke_table = [[web_latex(p.norm()),
                             web_latex(p.gens_reduced()[0]),
                             web_latex(ap)] for p,ap in zip(primes_iter(K), self.hecke_eigs[:self.nap0])]
        level = ideal_from_label(K,self.level_label)
        self.level_ideal2 = web_latex(level)
        badp = level.prime_factors()
        self.have_AL = self.AL_eigs[0]!='?'
        if self.have_AL:
            self.AL_table = [[web_latex(p.norm()),
                              web_latex(p.gens_reduced()[0]),
                              web_latex(ap)] for p,ap in zip(badp, self.AL_eigs)]
        self.sign = 'not determined'
        if self.sfe == 1:
            self.sign = "+1"
        elif self.sfe == -1:
            self.sign = "-1"

        if self.Lratio == '?':
            self.Lratio = "not determined"
            self.anrank = "not determined"
        else:
            self.Lratio = QQ(self.Lratio)
            self.anrank = "\(0\)" if self.Lratio!=0 else "\(\ge1\), odd" if self.sfe==-1 else "\(\ge2\), even"

        self.properties2 = [('base field', pretty_field),
                            ('label', self.label),
                            ('level', self.level_ideal2),
                            ('level norm', str(self.level_norm)),
                            ('weight', str(self.weight)),
                            ('dimension', str(self.dimension))
                            ]
        if self.is_base_change == '?':
            self.bc = 'not determined'
        else:
            self.bc = 'yes' if self.is_base_change else "no"
            self.properties2.append(('base-change', self.bc))
        if self.is_CM == '?':
            self.cm = 'not determined'
        else:
            self.cm = 'Yes' if self.is_CM else "No"
        self.properties2.append(('CM', self.cm))
        self.properties2.append(('Sign', self.sign))
        self.properties2.append(('Analytic rank', self.anrank))
        self.friends = []
        if self.dimension==1:
            if db_ecnf().find_one({'class_label':self.label}):
                self.friends += [('Elliptic curve isogeny class {}'.format(self.label),url_for("ecnf.show_ecnf_isoclass", nf=self.field_label, conductor_label=self.level_label, class_label=self.label_suffix))]
            else:
                self.friends += [('Elliptic curve {} not available'.format(self.label),"")]

        self.friends += [ ('Newspace {}'.format(self.newspace_label),self.newspace_url)]
        self.friends += [ ('L-function not available','')]

# -*- coding: utf-8 -*-
from lmfdb import db
from lmfdb.logger import make_logger
from lmfdb.number_fields.web_number_field import nf_display_knowl, field_pretty
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label
from lmfdb.nfutils.psort import primes_iter, ideal_from_label, ideal_label, prime_key
from lmfdb.utils import web_latex, names_and_urls, prop_int_pretty
from lmfdb.lfunctions.LfunctionDatabase import (get_lfunction_by_url,
        get_instances_by_Lhash_and_trace_hash)
from flask import url_for
from sage.all import QQ, PolynomialRing, NumberField

logger = make_logger("bmf")

# Labels of BMFs which have no elliptic curve but are not twists of
# base change.  Those which have no curve but are twists of base
# change are detectable automatically in the code below, but these are
# not.  Up to Galois conjugacy and quadratic twist there are only four
# of these known; each is associated to the Jacobian of a genus 2
# curve over the base field; these curves were found by Ciaran
# Schembri.  At some point we will want to list these abelian surfaces
# as friends when there is no curve.

# TO (after adding 31 more for 2.0.43.1): make this list into a table,
# OR add a column to the bmf_forms table to indicate whether or not a
# curve exists (which could be because we have not foud one, but is
# normally because there really is not curve).

bmfs_with_no_curve = ['2.0.4.1-34225.7-b',
                      '2.0.4.1-34225.7-a',
                      '2.0.4.1-34225.3-b',
                      '2.0.4.1-34225.3-a',
                      '2.0.3.1-67081.3-a',
                      '2.0.3.1-67081.3-b',
                      '2.0.3.1-67081.7-b',
                      '2.0.3.1-67081.7-a',
                      '2.0.3.1-61009.1-a',
                      '2.0.3.1-61009.1-b',
                      '2.0.3.1-61009.9-a',
                      '2.0.3.1-61009.9-b',
                      '2.0.3.1-123201.1-b',
                      '2.0.3.1-123201.1-c',
                      '2.0.3.1-123201.3-b',
                      '2.0.3.1-123201.3-c',
                      '2.0.19.1-1849.1-a',
                      '2.0.19.1-1849.3-a',
                      '2.0.43.1-121.1-a',
                      '2.0.43.1-121.3-a',
                      '2.0.43.1-256.1-c',
                      '2.0.43.1-256.1-d',
                      '2.0.43.1-256.1-e',
                      '2.0.43.1-256.1-f',
                      '2.0.43.1-529.1-a',
                      '2.0.43.1-529.3-a',
                      '2.0.43.1-961.1-a',
                      '2.0.43.1-961.3-a',
                      '2.0.43.1-1849.1-b',
                      '2.0.43.1-1936.1-a',
                      '2.0.43.1-1936.3-a',
                      '2.0.43.1-2209.1-a',
                      '2.0.43.1-2209.3-a',
                      '2.0.43.1-3481.1-a',
                      '2.0.43.1-3481.3-a',
                      '2.0.43.1-4096.1-d',
                      '2.0.43.1-4096.1-e',
                      '2.0.43.1-4096.1-f',
                      '2.0.43.1-4096.1-g',
                      '2.0.43.1-4489.1-a',
                      '2.0.43.1-4489.3-a',
                      '2.0.43.1-6241.1-a',
                      '2.0.43.1-6241.3-a',
                      '2.0.43.1-6889.1-a',
                      '2.0.43.1-6889.3-a',
                      '2.0.43.1-8464.1-a',
                      '2.0.43.1-8464.3-a',
                      '2.0.43.1-9801.1-a',
                      '2.0.43.1-9801.3-a',
                      '2.0.43.1-10609.1-a',
                      '2.0.43.1-10609.3-a',
                      '2.0.43.1-11449.1-a',
                      '2.0.43.1-11449.3-a']

def cremona_label_to_lmfdb_label(lab):
    if "." in lab:
        return lab
    return db.ec_curvedata.lucky({"Clabel":lab}, projection='lmfdb_label')

class WebBMF():
    """
    Class for a Bianchi Newform
    """
    def __init__(self, dbdata, max_eigs=50):
        """Arguments:

            - dbdata: the data from the database

        dbdata is expected to be a database entry from which the class
        is initialised.

        """
        logger.debug("Constructing an instance of WebBMF class from database")
        self.__dict__.update(dbdata)
        # All other fields are handled here
        self.make_form(max_eigs)

    @staticmethod
    def by_label(label, max_eigs=50):
        """
        Searches for a specific Bianchi newform in the forms
        collection by its label.
        """
        data = db.bmf_forms.lookup(label)

        if data:
            return WebBMF(data, max_eigs)
        raise ValueError("Bianchi newform %s not found" % label)
        # caller must catch this and raise an error


    def make_form(self,nap0=50):
        # To start with the data fields of self are just those from
        # the database.  We need to reformat these and compute some
        # further (easy) data about it.
        #
        from lmfdb.ecnf.WebEllipticCurve import FIELD
        self.field = FIELD(self.field_label)
        pretty_field = field_pretty(self.field_label)
        self.field_knowl = nf_display_knowl(self.field_label, pretty_field)
        try:
            dims = db.bmf_dims.lucky({'field_label':self.field_label, 'level_label':self.level_label}, projection='gl2_dims')
            self.newspace_dimension = dims[str(self.weight)]['new_dim']
        except TypeError:
            self.newspace_dimension = 'not available'
        self.newspace_label = "-".join([self.field_label,self.level_label])
        self.newspace_url = url_for(".render_bmf_space_webpage", field_label=self.field_label, level_label=self.level_label)
        K = self.field.K()

        # 'hecke_poly_obj' is the non-LaTeX version of hecke_poly
        self.hecke_poly_obj = self.hecke_poly

        if self.dimension>1:
            Qx = PolynomialRing(QQ,'x')
            self.hecke_poly = Qx(str(self.hecke_poly))
            F = NumberField(self.hecke_poly,'z')
            self.hecke_poly = web_latex(self.hecke_poly)
            def conv(ap):
                if '?' in ap:
                    return 'not known'
                else:
                    return F(str(ap))
            self.hecke_eigs = [conv(str(ap)) for ap in self.hecke_eigs]

        self.level = ideal_from_label(K,self.level_label)
        self.level_ideal2 = web_latex(self.level)
        badp = self.level.prime_factors()
        badp.sort(key=prime_key)

        self.nap = len(self.hecke_eigs)
        self.nap0 = min(nap0, self.nap)
        self.neigs = self.nap0 + len(badp)
        self.hecke_table = [[web_latex(p.norm()),
                             ideal_label(p),
                             web_latex(p.gens_reduced()),
                             web_latex(ap)] for p,ap in zip(primes_iter(K), self.hecke_eigs[:self.neigs]) if p not in badp]
        self.have_AL = self.AL_eigs[0]!='?'
        if self.have_AL:
            self.AL_table = [[web_latex(p.norm()),
                             ideal_label(p),
                              web_latex(p.gens_reduced()),
                              web_latex(ap)] for p,ap in zip(badp, self.AL_eigs)]
            # The following helps to create Sage download data
            self.AL_table_data = [[p.gens_reduced(),ap] for p,ap in zip(badp, self.AL_eigs)]
        self.sign = 'not determined'

        try:
            if self.sfe == 1:
                self.sign = "$+1$"
            elif self.sfe == -1:
                self.sign = "$-1$"
        except AttributeError:
            self.sfe = '?'

        if self.Lratio == '?':
            self.Lratio = "not determined"
            self.anrank = "not determined"
        else:
            self.Lratio = QQ(self.Lratio)
            self.anrank = r"\(0\)" if self.Lratio!=0 else "odd" if self.sfe==-1 else r"\(\ge2\), even"

        self.properties = [('Label', self.label),
                            ('Base field', pretty_field),
                            ('Weight', prop_int_pretty(self.weight)),
                            ('Level norm', prop_int_pretty(self.level_norm)),
                            ('Level', self.level_ideal2),
                            ('Dimension', prop_int_pretty(self.dimension))
        ]

        try:
            if self.CM == '?':
                self.CM = 'not determined'
            elif self.CM == 0:
                self.CM = 'no'
            else:
                if int(self.CM)%4 in [2,3]:
                    self.CM = 4*int(self.CM)
                self.CM = "$%s$" % self.CM
        except AttributeError:
            self.CM = 'not determined'
        self.properties.append(('CM', str(self.CM)))

        self.bc_extra = ''
        self.bcd = 0
        self.bct = self.bc!='?' and self.bc!=0
        if self.bc == '?':
            self.bc = 'not determined'
        elif self.bc == 0:
            self.bc = 'no'
        elif self.bc == 1:
            self.bcd = self.bc
            self.bc = 'yes'
        elif self.bc >1:
            self.bcd = self.bc
            self.bc = 'yes'
            self.bc_extra = r', of a form over \(\mathbb{Q}\) with coefficients in \(\mathbb{Q}(\sqrt{' + str(self.bcd) + r'})\)'
        elif self.bc == -1:
            self.bc = 'no'
            self.bc_extra = r', but is a twist of the base change of a form over \(\mathbb{Q}\)'
        elif self.bc < -1:
            self.bcd = -self.bc
            self.bc = 'no'
            self.bc_extra = r', but is a twist of the base change of a form over \(\mathbb{Q}\) with coefficients in \(\mathbb{Q}(\sqrt{'+str(self.bcd)+r'})\)'
        self.properties.append(('Base change', str(self.bc)))

        curve_bc = db.ec_nfcurves.lucky({'class_label':self.label}, projection="base_change")
        if curve_bc is not None:
            curve_bc = [lab for lab in curve_bc if '?' not in lab]
            if curve_bc and "." not in curve_bc[0]:
                curve_bc = [cremona_label_to_lmfdb_label(lab) for lab in curve_bc]
            self.ec_status = 'exists'
            self.ec_url = url_for("ecnf.show_ecnf_isoclass", nf=self.field_label, conductor_label=self.level_label, class_label=self.label_suffix)
            curve_bc_parts = [split_lmfdb_label(lab) for lab in curve_bc]
            bc_urls = [url_for("cmf.by_url_newform_label", level=cond, weight=2, char_orbit_label='a', hecke_orbit=iso) for cond, iso, num in curve_bc_parts]
            bc_labels = [".".join( [str(cond), str(2), 'a', iso] ) for cond,iso,_ in curve_bc_parts]
            bc_exists = [db.mf_newforms.label_exists(lab) for lab in bc_labels]
            self.bc_forms = [{'exists':ex, 'label':lab, 'url':url} for ex,lab,url in zip(bc_exists, bc_labels, bc_urls)]
        else:
            self.bc_forms = []
            if self.bct or self.label in bmfs_with_no_curve:
                self.ec_status = 'none'
            else:
                self.ec_status = 'missing'

        self.properties.append(('Sign', self.sign))
        self.properties.append(('Analytic rank', self.anrank))

        self.friends = []
        self.friends += [('Newspace {}'.format(self.newspace_label),self.newspace_url)]
        url = 'ModularForm/GL2/ImaginaryQuadratic/{}'.format(
                self.label.replace('-', '/'))
        Lfun = get_lfunction_by_url(url)
        if Lfun:
            instances = get_instances_by_Lhash_and_trace_hash(Lfun['Lhash'], Lfun['degree'], Lfun['trace_hash'])

            # This will also add the EC/G2C, as this how the Lfun was computed
            # and not add itself
            self.friends = names_and_urls(instances, exclude = {url})
            self.friends.append(('L-function', '/L/'+url))
        else:
            # old code
            if self.dimension == 1:
                if self.ec_status == 'exists':
                    self.friends += [('Isogeny class {}'.format(self.label), self.ec_url)]
                elif self.ec_status == 'missing':
                    self.friends += [('Isogeny class {} missing'.format(self.label), "")]
                else:
                    self.friends += [('No elliptic curve', "")]

            self.friends += [ ('L-function not available','')]

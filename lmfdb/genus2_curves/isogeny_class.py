# -*- coding: utf-8 -*-
from pymongo import ASCENDING, DESCENDING
from flask import url_for
from lmfdb.genus2_curves.web_g2c import g2cdb, list_to_min_eqn, end_alg_name, st0_group_name, st_group_name, st_group_href
from lmfdb.genus2_curves.web_g2c import gl2_statement_base, factorsRR_raw_to_pretty, fod_statement, intlist_to_poly
from sage.all import QQ, PolynomialRing, factor,ZZ, NumberField, expand, var
from lmfdb.WebNumberField import field_pretty

###############################################################################
# Pretty print functions
###############################################################################

def list_to_poly(s):
    return str(PolynomialRing(QQ, 'x')(s)).replace('*','')

def list_to_factored_poly(s):
    return str(factor(PolynomialRing(ZZ, 't')(s))).replace('*','')

def list_to_factored_poly_otherorder(s, galois=False):
    """ Either return the polynomial in a nice factored form,
        or return a pair, with first entry the factored polynomial
        and the second entry a list describing the Galois groups
        of the factors.
    """
    gal_list=[]
    if len(s) == 1:
        if galois:
            return [str(s[0]), [[0,0]]]
        return str(s[0])
    sfacts = factor(PolynomialRing(ZZ, 'T')(s))
    sfacts_fc = [[v[0],v[1]] for v in sfacts]
    if sfacts.unit() == -1:
        sfacts_fc[0][0] *= -1
    outstr = ''
    x = var('x')
    for v in sfacts_fc:
        this_poly = v[0]
        # if the factor is -1+T^2, replace it by 1-T^2
        # this should happen an even number of times, mod powers
        if this_poly.substitute(T=0) == -1:
            this_poly = -1*this_poly
            v[0] = this_poly
        if galois:
            this_degree = this_poly.degree()
                # hack because currently sage only handles monic polynomials:
            this_poly = expand(x**this_degree*this_poly.substitute(T=1/x))
            this_number_field = NumberField(this_poly, "a")
            this_gal = this_number_field.galois_group(type='pari')
            this_t_number = this_gal.group()._pari_()[2]._sage_()
            gal_list.append([this_degree, this_t_number])
        vcf = v[0].list()
        started = False
        if len(sfacts) > 1 or v[1] > 1:
            outstr += '('
        for i in range(len(vcf)):
            if vcf[i] != 0:
                if started and vcf[i] > 0:
                    outstr += '+'
                started = True
                if i == 0:
                    outstr += str(vcf[i])
                else:
                    if abs(vcf[i]) != 1:
                        outstr += str(vcf[i])
                    elif vcf[i] == -1:
                        outstr += '-'
                    if i == 1:
                        outstr += 'T'
                    elif i > 1:
                        outstr += 'T^{' + str(i) + '}'
        if len(sfacts) > 1 or v[1] > 1:
            outstr += ')'
        if v[1] > 1:
            outstr += '^{' + str(v[1]) + '}'
    if galois:
        if galois and len(sfacts_fc)==2:
            if sfacts[0][0].degree()==2 and sfacts[1][0].degree()==2:
                troubletest = sfacts[0][0].disc()*sfacts[1][0].disc()
                if troubletest.is_square():
                    gal_list=[[2,1]]
        return [outstr, gal_list]
    return outstr

###############################################################################
# Statement functions for endomorphism functionality
###############################################################################

# We could also import from web_g2c.py, but this seems more maintainable if we
# ever want to give some individual style to the isogeny class pages.
def endo_statement_isog(factorsQQ, factorsRR, fieldstring):
    statement = """<table class="g2">"""
    factorsQQ_number = len(factorsQQ)
    factorsQQ_pretty = [ field_pretty(fac[0]) for fac in factorsQQ if
        fac[0] ]

    # First row: description of endomorphism algebra factors
    statement += """<tr><td>\(\End (J_{%s}) \otimes \Q \)</td><td>\(\simeq\)</td><td>"""\
        % fieldstring
    # In the case of only one factor we either get a number field or a
    # quaternion algebra:
    if factorsQQ_number == 1:
        # First we deal with the number field case,
        # in which we have set the discriminant to be -1
        if factorsQQ[0][2] == -1:
            # Prettify if labels available, otherwise return defining polynomial:
            if factorsQQ_pretty:
                statement += """<a href=%s>%s</a>"""\
                    % (url_for("number_fields.by_label",
                       label=factorsQQ[0][0]), factorsQQ_pretty[0])
            else:
                statement += """number field with defining polynomial \(%s\)"""\
                    % intlist_to_poly(factorsQQ[0][1])
            # Detect CM by presence of a quartic polynomial:
            # TODO: Add knowl link
            if len(factorsQQ[0][1]) == 5:
                statement += """(CM)"""
        # Up next is the case of a matrix ring (trivial disciminant), with
        # labels and full prettification always available:
        elif factorsQQ[0][2] == 1:
            statement += """\(\mathrm{M}_2(\)<a href=%s>%s</a>\()\)"""\
                % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                    factorsQQ_pretty[0])
        # And finally we deal with quaternion algebras over the rationals:
        else:
            statement += """quaternion algebra over <a href=%s>%s</a> of discriminant %s"""\
                % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                    factorsQQ_pretty[0], factorsQQ[0][2])
    # If there are two factors, then we get two at most quadratic fields:
    else:
        statement += """<a href=%s>%s</a> \(\\times\) <a href=%s>%s</a>"""\
            % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                factorsQQ_pretty[0], url_for("number_fields.by_label",
                label=factorsQQ[1][0]), factorsQQ_pretty[1])
    # End of first row:
    statement += """</td></tr>"""

    # Second row: description of algebra tensored with RR
    statement += """<tr><td>\(\End (J_{%s}) \otimes \R\)</td><td>\(\simeq\)</td> <td>\(%s\)</td></tr>"""\
        % (fieldstring, factorsRR_raw_to_pretty(factorsRR))

    # End of statement:
    statement += """</table>"""
    return statement

###############################################################################
# The actual class definition
###############################################################################

class G2Cisogeny_class(object):
    """
    Class for an isogeny class of genus 2 curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        self.__dict__.update(dbdata)
        self.make_class()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific genus 2 curve isogeny class in the
        curves collection by its label.
        """
        try:
            data = g2cdb().isogeny_classes.find_one({"label" : label})
        except AttributeError:
            return "Invalid isogeny class label" # caller must catch this and raise an error
        if data:
            return G2Cisogeny_class(data)
        return "No isogeny class with this label currently in the database" # caller must catch this and raise an error

    ###########################################################################
    # Main data creation for individual isogeny classes
    ###########################################################################


    def make_class(self):
        from lmfdb.genus2_curves.genus2_curve import url_for_curve_label

        # Data
        curves_data = g2cdb().curves.find({"class" : self.label},{'_id':int(0),'label':int(1),'min_eqn':int(1),'disc_key':int(1)}).sort([("disc_key", ASCENDING), ("label", ASCENDING)])
        assert curves_data
        self.curves = [ {"label" : c['label'], "equation_formatted" : list_to_min_eqn(c['min_eqn']),
            "url": url_for_curve_label(c['label'])} for c in curves_data ]
        self.ncurves = curves_data.count()
        self.bad_lfactors = [ [c[0], list_to_factored_poly_otherorder(c[1])]
            for c in self.bad_lfactors]

        # Data derived from Sato-Tate group
        self.st_group_name = st_group_name(self.st_group)
        self.st_group_href = st_group_href(self.st_group)
        self.st0_group_name = st0_group_name(self.real_geom_end_alg)
        # Later used in Lady Gaga box:
        self.real_geom_end_alg_disp = [r'\End(J_{\overline{\Q}}) \otimes \R',
                end_alg_name(self.real_geom_end_alg)]
        if self.is_gl2_type:
            self.is_gl2_type_name = 'yes'
        else:
            self.is_gl2_type_name = 'no'

        # Endomorphism data
        endodata = g2cdb().endomorphisms.find_one({"label" :
            self.curves[0]['label']})
        self.gl2_statement_base = \
            gl2_statement_base(endodata['factorsRR_base'], r'\(\Q\)')
        self.endo_statement_base = \
            """Endomorphism algebra over \(\Q\):<br>""" + \
            endo_statement_isog(endodata['factorsQQ_base'],
                endodata['factorsRR_base'], r'')
        endodata['fod_poly'] = intlist_to_poly(endodata['fod_coeffs'])
        self.fod_statement = fod_statement(endodata['fod_label'],
            endodata['fod_poly'])
        if endodata['fod_label'] != '1.1.1.1':
            self.endo_statement_geom = \
                """Endomorphism algebra over \(\overline{\Q}\):<br>""" + \
                endo_statement_isog(endodata['factorsQQ_geom'],
                    endodata['factorsRR_geom'], r'\overline{\Q}')
        else:
            self.endo_statement_geom = ''

        # Title
        self.title = "Genus 2 Isogeny Class %s" % (self.label)

        # Lady Gaga box
        self.properties = (
                ('Label', self.label),
                ('Number of curves', str(self.ncurves)),
                ('Conductor','%s' % self.cond),
                ('Sato-Tate group', self.st_group_href),
                ('\(%s\)' % self.real_geom_end_alg_disp[0],
                 '\(%s\)' % self.real_geom_end_alg_disp[1]),
                ('\(\mathrm{GL}_2\)-type','%s' % self.is_gl2_type_name)
                )
        x = self.label.split('.')[1]
        self.friends = [('L-function', url_for("l_functions.l_function_genus2_page", cond=self.cond,x=x))]
        #self.downloads = [('Download Euler factors', ".")]
        #self.downloads = [
        #        ('Download Euler factors', "."),
        #            url_for(".download_g2c_eulerfactors", label=self.label)),
        #        ('Download stored data for all curves',
        #            url_for(".download_g2c_all", label=self.label))
        #        ]

        # Breadcrumbs
        self.bread = (
                       ('Genus 2 Curves', url_for(".index")),
                       ('$\Q$', url_for(".index_Q")),
                       ('%s' % self.cond, url_for(".by_conductor", cond=self.cond)),
                       ('%s' % self.label, ' ')
                     )

        # More friends (NOTE: to be improved)
        self.ecproduct_wurl = []
        if hasattr(self, 'ecproduct'):
            for i in range(2):
                curve_label = self.ecproduct[i]
                crv_url = url_for("ec.by_ec_label", label=curve_label)
                if i == 1 or len(set(self.ecproduct)) != 1:
                    self.friends.append(('Elliptic curve ' + curve_label,
                        crv_url))
                self.ecproduct_wurl.append({'label' : curve_label, 'url' :
                    crv_url})

        self.ecquadratic_wurl = []
        if hasattr(self, 'ecquadratic'):
            for i in range(len(self.ecquadratic)):
                curve_label = self.ecquadratic[i]
                crv_spl = curve_label.split('-')
                crv_url = url_for("ecnf.show_ecnf_isoclass", nf = crv_spl[0],
                        conductor_label = crv_spl[1], class_label = crv_spl[2])
                self.friends.append(('Elliptic curve ' + curve_label, crv_url))
                self.ecquadratic_wurl.append({'label' : curve_label, 'url' :
                    crv_url, 'nf' : crv_spl[0]})

        if hasattr(self, 'mfproduct'):
            for i in range(len(self.mfproduct)):
                mf_label = self.mfproduct[i]
                mf_spl = mf_label.split('.')
                mf_spl.append(mf_spl[2][-1])
                mf_spl[2] = mf_spl[2][:-1] # Need a splitting function
                mf_url = url_for("emf.render_elliptic_modular_forms",
                        level=mf_spl[0], weight=mf_spl[1], character=mf_spl[2],
                        label=mf_spl[3])
                self.friends.append(('Modular form ' + mf_label, mf_url))

        if hasattr(self, 'mfhilbert'):
            for i in range(len(self.mfhilbert)):
                mf_label = self.mfhilbert[i]
                mf_spl = mf_label.split('-')
                mf_url = url_for("hmf.render_hmf_webpage",
                        field_label=mf_spl[0], label=mf_label)
                self.friends.append(('Hilbert modular form ' + mf_label, mf_url))

# -*- coding: utf-8 -*-

from pymongo import ASCENDING
from ast import literal_eval
from lmfdb.base import getDBConnection
from lmfdb.utils import web_latex, encode_plot
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField
from lmfdb.transitive_group import group_display_knowl
from sage.all import latex, ZZ, QQ, CC, NumberField, PolynomialRing, factor, implicit_plot, point, real, sqrt, var, expand, nth_prime
from sage.plot.text import text
from flask import url_for

###############################################################################
# Database connection -- all access to mongo db should happen here
###############################################################################

def belyi_db_galmaps():
    return getDBConnection().belyi.galmaps

def belyi_db_passports():
    return getDBConnection().belyi.passports


###############################################################################
# Pretty print functions
###############################################################################

geomtypelet_to_geomtypename_dict = {'H':'hyperbolic','E':'Euclidean','S':'spherical'}

def make_curve_latex(crv_str):
    from sage.all import PolynomialRing, FractionField
    # FIXME: Get rid of nu when map is defined over QQ
    R0 = PolynomialRing(QQ,'nu')
    R = PolynomialRing(R0,2,'x,y')
    F = FractionField(R)
    sides = crv_str.split("=")
    lhs = latex(F(sides[0]))
    rhs = latex(F(sides[1]))
    eqn_str = lhs + '=' + rhs
    return eqn_str

def make_map_latex(map_str):
    from sage.all import PolynomialRing, FractionField, gcd
    # FIXME: Get rid of nu when map is defined over QQ
    R0 = PolynomialRing(QQ,'nu')
    R = PolynomialRing(R0,2,'x,y')
    F = FractionField(R)
    phi = F(map_str)
    num = phi.numerator()
    den = phi.denominator()
    c_num = num.denominator()
    c_den = den.denominator()
    lc = c_den/c_num
    # rescale coeffs to make them integral. then try to factor out gcds
    # numerator
    num_new = c_num*num
    num_cs = num_new.coefficients()
    num_cs_ZZ = []
    for el in num_cs:
        num_cs_ZZ = num_cs_ZZ + el.coefficients()
    num_gcd = gcd(num_cs_ZZ)
    # denominator
    den_new = c_den*den
    den_cs = den_new.coefficients()
    den_cs_ZZ = []
    for el in den_cs:
        den_cs_ZZ = den_cs_ZZ + el.coefficients()
    den_gcd = gcd(den_cs_ZZ)
    lc = lc*(num_gcd/den_gcd)
    num_new = num_new/num_gcd
    den_new = den_new/den_gcd
    # make strings for lc, num, and den
    num_str = latex(num_new)
    den_str = latex(den_new)
    if lc==1:
        lc_str=""
    else:
        lc_str = latex(lc)
    if den_new==1:
        if lc ==1:
            phi_str = num_str
        else:
            phi_str = lc_str+"("+num_str+")"
    else:
        phi_str = lc_str+"\\frac{"+num_str+"}"+"{"+den_str+"}"
    return phi_str

###############################################################################
# Belyi map class definitions
###############################################################################

def belyi_base_field(galmap):
    fld_coeffs = galmap['base_field']
    if fld_coeffs==[-1,1]:
        fld_coeffs = [0,1]
    F = WebNumberField.from_coeffs(fld_coeffs)
    return F

class WebBelyiGalmap(object):
    """
    Class for a Belyi map.  Attributes include:
        data -- information about the map to be displayed
        plot -- currently empty
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels of related objects
        code -- code snippets for relevant attributes in data
        bread -- bread crumbs for home page
        title -- title to display on home page
    """
    def __init__(self, galmap):
        self.make_galmap_object(galmap)

    @staticmethod
    def by_label(label):
        """
        Searches for a specific Belyi map in the galmaps collection by its label.
        If label is for a passport, constructs an object for an arbitrarily chosen galmap in the passport
        Constructs the WebBelyiGalmap object if found, raises an error otherwise
        """
        try:
            slabel = label.split("-")
            if len(slabel) == 6:
                galmap = belyi_db_galmaps().find_one({"plabel" : label})
            elif len(slabel) == 7:
                galmap = belyi_db_galmaps().find_one({"label" : label})
            else:
                raise ValueError("Invalid Belyi map label %s." % label)
        except AttributeError:
            raise ValueError("Invalid Belyi map label %s." % label)
        if not galmap:
            if len(slabel) == 6:
                raise KeyError("Belyi map passport label %s not found in the database." % label)
            else:
                raise KeyError("Belyi map %s not found in database." % label)
        return WebBelyiGalmap(galmap)


    def make_galmap_object(self, galmap):
        from lmfdb.belyi.main import url_for_belyi_galmap_label
        from lmfdb.belyi.main import url_for_belyi_passport_label

        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}
        # the stuff that does not need to be polished
        for elt in ('label', 'plabel', 'triples', 'orbit_size', 'g', 'abc', 'embeddings'):
            data[elt] = galmap[elt]
        slabel = data['label'].split("-")
        data['isogeny_label'] = slabel[-1];
        data['isQQ'] = False
        F = belyi_base_field(galmap)
        if F.poly().degree()==1:
            data['isQQ'] = True 
        F.latex_poly = web_latex(F.poly())
        data['base_field'] = F
        crv_str = galmap['curve']
        if crv_str=='PP1':
            data['curve'] = '\mathbb{P}^1'
        else:
            data['curve'] = make_curve_latex(crv_str)

        data['map'] = make_map_latex(galmap['map'])
        data['lambdas'] = [str(c)[1:-1] for c in galmap['lambdas']]

        # Properties
        self.properties = properties = [('Label', data['label'])]
        properties += [
            ]

        # Friends
        self.friends = friends = [('Passport', url_for_belyi_passport_label(galmap['plabel']))]

        # Breadcrumbs
        groupstr, abcstr, sigma0, sigma1, sigmaoo, gstr = data['plabel'].split("-");
        lambdasstr = '%s-%s-%s' % (sigma0, sigma1, sigmaoo);
        lambdasgstr = lambdasstr + "-" + gstr;
        self.bread = bread = [
                ('Belyi Maps', url_for(".index")),
                (groupstr,
                    url_for(".by_url_belyi_search_group",
                        group=groupstr
                        )
                    ),
                (abcstr,
                    url_for(".by_url_belyi_search_group_triple",
                        group=groupstr,
                        abc=abcstr
                        )
                    ),
                (lambdasgstr,
                    url_for(".by_url_belyi_passport_label",
                        group=groupstr,
                        abc=abcstr,
                        sigma0=sigma0,
                        sigma1=sigma1,
                        sigmaoo=sigmaoo,
                        g = gstr )
                    ),
                (data['isogeny_label'],
                    url_for(".by_url_belyi_galmap_label",
                        group=groupstr,
                        abc=abcstr,
                        sigma0=sigma0,
                        sigma1=sigma1,
                        sigmaoo=sigmaoo,
                        g = gstr,
                        letnum = data['isogeny_label'])
                    ),
                ];

        # Title
        self.title = "Belyi map " + data['label']

        # Code snippets (only for curves)
        self.code = code = {}
        return

class WebBelyiPassport(object):
    """
    Class for a Belyi passport.  Attributes include:
        data -- information about the map to be displayed
        plot -- currently empty
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels of related objects
        code -- code snippets for relevant attributes in data, currently empty
        bread -- bread crumbs for home page
        title -- title to display on home page
    """
    def __init__(self, passport):
        self.make_passport_object(passport)

    @staticmethod
    def by_label(label):
        """
        Searches for a specific passport in the passports collection by its label.
        Constructs the WebBelyiPassport object if found, raises an error otherwise
        """
        try:
            slabel = label.split("-")
            if len(slabel) == 6:
                passport = belyi_db_passports().find_one({"plabel" : label})
            else:
                raise ValueError("Invalid Belyi passport label %s." % label)
        except AttributeError:
            raise ValueError("Invalid passport label %s." % label)
        if not passport:
            raise KeyError("Passport %s not found in database." % label)
        return WebBelyiPassport(passport)

    def make_passport_object(self, passport):
        from lmfdb.belyi.main import url_for_belyi_galmap_label
        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}

        for elt in ('plabel', 'abc', 'num_orbits', 'g', 'abc', 'deg', 'maxdegbf'):
            data[elt] = passport[elt]

        slabel = data['plabel'].split("-")

        nt = passport['group'].split('T')
        data['group'] = group_display_knowl(nt[0],nt[1],getDBConnection())

        data['geomtype'] = geomtypelet_to_geomtypename_dict[passport['geomtype']]
        data['lambdas'] = [str(c)[1:-1] for c in passport['lambdas']]

        # Permutation triples
        galmaps_for_plabel = belyi_db_galmaps().find({"plabel" : passport['plabel']}).sort([('label_index', ASCENDING)])
        galmapdata = [] 
        for galmap in galmaps_for_plabel:
            F = WebNumberField.from_coeffs(galmap['base_field'])
            galmapdatum = [galmap['label'].split('-')[-1], 
                           url_for_belyi_galmap_label(galmap['label']), 
                           galmap['orbit_size'], 
                           belyi_base_field(galmap),
                           galmap['triples'][0]]
            galmapdata.append(galmapdatum)
        data['galmapdata'] = galmapdata

        # Properties
        properties = [('Label', passport['plabel']),
            ('Group', str(passport['group'])),
            ('Orders', str(passport['abc'])), 
            ('Genus', str(passport['g'])),
            ('Size', str(passport['pass_size'])),
            ('Galois orbits', str(passport['num_orbits']))
            ]
        self.properties = properties

        # Friends
        self.friends = friends = []

        # Breadcrumbs

        groupstr, abcstr, sigma0, sigma1, sigmaoo, gstr = data['plabel'].split("-");
        lambdasstr = '%s-%s-%s' % (sigma0, sigma1, sigmaoo);
        lambdasgstr = lambdasstr + "-" + gstr;
        self.bread = bread = [
                ('Belyi Maps', url_for(".index")),
                (groupstr,
                    url_for(".by_url_belyi_search_group",
                        group=groupstr
                        )
                    ),
                (abcstr,
                    url_for(".by_url_belyi_search_group_triple",
                        group=groupstr,
                        abc=abcstr
                        )
                    ),
                (lambdasgstr,
                    url_for(".by_url_belyi_passport_label",
                        group=groupstr,
                        abc=abcstr,
                        sigma0=sigma0,
                        sigma1=sigma1,
                        sigmaoo=sigmaoo,
                        g = gstr )
                    )
                ];

        # Title
        self.title = "Passport " + data['plabel']

        # Code snippets (only for curves)
        self.code = code = {}
        return

# -*- coding: utf-8 -*-

from lmfdb.utils import web_latex
from lmfdb.WebNumberField import  WebNumberField
from lmfdb.transitive_group import group_display_knowl
from sage.all import gcd, latex, QQ, FractionField, PolynomialRing
from flask import url_for

from lmfdb.db_backend import db




###############################################################################
# Pretty print functions
###############################################################################

geomtypelet_to_geomtypename_dict = {'H':'hyperbolic','E':'Euclidean','S':'spherical'}

def make_curve_latex(crv_str):
    # FIXME: Get rid of nu when map is defined over QQ
    if "nu" not in crv_str:
        R0 = QQ
    else:
        R0 = PolynomialRing(QQ,'nu')
    R = PolynomialRing(R0,2,'x,y')
    F = FractionField(R)
    sides = crv_str.split("=")
    lhs = latex(F(sides[0]))
    rhs = latex(F(sides[1]))
    eqn_str = lhs + '=' + rhs
    return eqn_str

def make_map_latex(map_str):
    # FIXME: Get rid of nu when map is defined over QQ
    if "nu" not in map_str:
        R0 = QQ
    else:
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
    if R0 == QQ:
        num_cs_ZZ = num_cs
    else:
        num_cs_ZZ = []
        for el in num_cs:
            num_cs_ZZ = num_cs_ZZ + el.coefficients()
    num_gcd = gcd(num_cs_ZZ)
    # denominator
    den_new = c_den*den
    den_cs = den_new.coefficients()
    if R0 == QQ:
        den_cs_ZZ = den_cs
    else:
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
                galmap = db.belyi_galmaps.lucky({"plabel" : label})
            elif len(slabel) == 7:
                galmap = db.belyi_galmaps.lucky({"label" : label})
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
        from lmfdb.belyi.main import url_for_belyi_passport_label

        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}
        # the stuff that does not need to be polished
        for elt in ('label', 'plabel', 'triples_cyc', 'orbit_size', 'g', 'abc', 'deg'):
            data[elt] = galmap[elt]
        nt = galmap['group'].split('T')
        data['group'] = group_display_knowl(int(nt[0]),int(nt[1]))

        data['geomtype'] = geomtypelet_to_geomtypename_dict[galmap['geomtype']]
        data['lambdas'] = [str(c)[1:-1] for c in galmap['lambdas']]

        data['isQQ'] = False
        data['in_LMFDB'] = False
        F = belyi_base_field(galmap)
        if F._data == None:
            fld_coeffs = galmap['base_field']
            pol = PolynomialRing(QQ, 'x')(fld_coeffs)
            data['base_field'] = latex(pol)
        else:
            data['in_LMFDB'] = True 
            if F.poly().degree()==1:
                data['isQQ'] = True 
            F.latex_poly = web_latex(F.poly())
            data['base_field'] = F
        crv_str = galmap['curve']
        if crv_str=='PP1':
            data['curve'] = '\mathbb{P}^1'
        else:
            data['curve'] = make_curve_latex(crv_str)

        # change pairs of floats to complex numbers
        embeds = galmap['embeddings']
        embed_strs = []
        for el in embeds:
            if el[1] < 0:
                el_str = str(el[0]) + str(el[1]) + "\sqrt{-1}"
            else:
                el_str = str(el[0]) + "+" + str(el[1]) + "\sqrt{-1}"
            embed_strs.append(el_str)

        data['map'] = make_map_latex(galmap['map'])
        data['embeddings_and_triples'] = []
        if data['isQQ']:
            for i in range(0,len(data['triples_cyc'])):
                triple_cyc = data['triples_cyc'][i]
                data['embeddings_and_triples'].append(["\\text{not applicable (over $\mathbb{Q}$)}", triple_cyc[0], triple_cyc[1], triple_cyc[2]])
        else:
            for i in range(0,len(data['triples_cyc'])):
                triple_cyc = data['triples_cyc'][i]
                data['embeddings_and_triples'].append([embed_strs[i], triple_cyc[0], triple_cyc[1], triple_cyc[2]])

        data['lambdas'] = [str(c)[1:-1] for c in galmap['lambdas']]

        # Properties
        properties = [('Label', galmap['label']),
            ('Group', str(galmap['group'])),
            ('Orders', str(galmap['abc'])), 
            ('Genus', str(galmap['g'])),
            ('Size', str(galmap['orbit_size'])),
        ]
        self.properties = properties

        # Friends
        self.friends = [('Passport', url_for_belyi_passport_label(galmap['plabel']))]

        # Breadcrumbs
        groupstr, abcstr, sigma0, sigma1, sigmaoo, gstr, letnum = data['label'].split("-");
        lambdasstr = '%s-%s-%s' % (sigma0, sigma1, sigmaoo);
        lambdasgstr = lambdasstr + "-" + gstr;
        self.bread = [
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
                (letnum,
                    url_for(".by_url_belyi_galmap_label",
                        group=groupstr,
                        abc=abcstr,
                        sigma0=sigma0,
                        sigma1=sigma1,
                        sigmaoo=sigmaoo,
                        g = gstr,
                        letnum = letnum)
                    ),
                ];

        # Title
        self.title = "Belyi map " + data['label']

        # Code snippets (only for curves)
        self.code = {}
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
                passport = db.belyi_passports.lucky({"plabel" : label})
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

        nt = passport['group'].split('T')
        data['group'] = group_display_knowl(int(nt[0]),int(nt[1]))

        data['geomtype'] = geomtypelet_to_geomtypename_dict[passport['geomtype']]
        data['lambdas'] = [str(c)[1:-1] for c in passport['lambdas']]
        data['pass_size'] = passport['pass_size']

        # Permutation triples
        galmaps_for_plabel = db.belyi_galmaps.search( {"plabel" : passport['plabel']})#, sort = ['label_index'])
        galmapdata = []
        for galmap in galmaps_for_plabel:
            # wrap number field nonsense
            F = belyi_base_field(galmap)
            # inLMFDB = False;
            field = {};
            if F._data == None:
                field['in_LMFDB'] = False;
                fld_coeffs = galmap['base_field']
                pol = PolynomialRing(QQ, 'x')(fld_coeffs)
                field['base_field'] = latex(pol)
                field['isQQ'] = False;
            else:
                field['in_LMFDB'] = True;
                if F.poly().degree()==1:
                    field['isQQ'] = True
                F.latex_poly = web_latex(F.poly())
                field['base_field'] = F

            galmapdatum = [galmap['label'].split('-')[-1],
                           url_for_belyi_galmap_label(galmap['label']),
                           galmap['orbit_size'],
                           field,
                           galmap['triples_cyc'][0][0],
                           galmap['triples_cyc'][0][1],
                           galmap['triples_cyc'][0][2],
                           ]
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
        self.friends = []

        # Breadcrumbs

        groupstr, abcstr, sigma0, sigma1, sigmaoo, gstr = data['plabel'].split("-");
        lambdasstr = '%s-%s-%s' % (sigma0, sigma1, sigmaoo);
        lambdasgstr = lambdasstr + "-" + gstr;
        self.bread = [
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
        self.code = {}
        return

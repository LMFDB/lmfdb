# -*- coding: utf-8 -*-

from lmfdb.utils import web_latex
from lmfdb.number_fields.web_number_field import WebNumberField
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl
from sage.all import gcd, latex, CC, QQ, FractionField, PolynomialRing
from lmfdb.utils import names_and_urls, prop_int_pretty
from flask import url_for

from lmfdb import db


###############################################################################
# Pretty print functions
###############################################################################

geomtypelet_to_geomtypename_dict = {
    "H": "hyperbolic",
    "E": "Euclidean",
    "S": "spherical",
}


def make_curve_latex(crv_str, nu=None):
    if "nu" not in crv_str:
        R0 = QQ
    else:
        R0 = PolynomialRing(QQ, "nu")
    R = PolynomialRing(R0, 2, "x,y")
    #F = FractionField(R)
    sides = crv_str.split("=")
    lhs = R(sides[0])
    rhs = R(sides[1])
    if nu and ("nu" in crv_str):
        S = PolynomialRing(CC, 2, 'x,y')
        # evaluate at nu, if given
        new_lhs = dict()
        new_rhs = dict()
        for m, c in lhs.dict().items():
            new_lhs[m] = c.subs(nu=nu)
        for m, c in rhs.dict().items():
            new_rhs[m] = c.subs(nu=nu)
        lhs = S(new_lhs) # R, or something else, like CC[]?
        rhs = S(new_rhs)
    eqn_str = latex(lhs) + "=" + latex(rhs)
    return eqn_str


def make_map_latex(map_str, nu = None):
    if "nu" not in map_str:
        R0 = QQ
    else:
        R0 = PolynomialRing(QQ, "nu")
    R = PolynomialRing(R0, 2, "x,y")
    F = FractionField(R)
    phi = F(map_str)
    num = phi.numerator()
    den = phi.denominator()
    c_num = num.denominator()
    c_den = den.denominator()
    lc = c_den / c_num
    # rescale coeffs to make them integral. then try to factor out gcds
    # numerator
    num_new = c_num * num
    num_cs = num_new.coefficients()
    if R0 == QQ:
        num_cs_ZZ = num_cs
    else:
        num_cs_ZZ = []
        for el in num_cs:
            num_cs_ZZ = num_cs_ZZ + el.coefficients()
    num_gcd = gcd(num_cs_ZZ)
    # denominator
    den_new = c_den * den
    den_cs = den_new.coefficients()
    if R0 == QQ:
        den_cs_ZZ = den_cs
    else:
        den_cs_ZZ = []
        for el in den_cs:
            den_cs_ZZ = den_cs_ZZ + el.coefficients()
    den_gcd = gcd(den_cs_ZZ)
    lc = lc * (num_gcd / den_gcd)
    num_new = num_new / num_gcd
    den_new = den_new / den_gcd
    # evaluate at nu, if given
    if nu and ("nu" in map_str):
        S = PolynomialRing(CC, 2, 'x,y')
        lc = lc.subs(nu=nu)
        num_dict = dict()
        den_dict = dict()
        for m, c in num_new.dict().items():
            num_dict[m] = c.subs(nu=nu)
        for m, c in den_new.dict().items():
            den_dict[m] = c.subs(nu=nu)
        num_new = S(num_dict)
        den_new = S(den_dict)
    # make strings for lc, num, and den
    num_str = latex(num_new)
    den_str = latex(den_new)

    if lc == 1:
        lc_str = ""
    else:
        lc_str = latex(lc)
    if den_new == 1:
        if lc == 1:
            phi_str = num_str
        else:
            phi_str = lc_str + "(" + num_str + ")"
    else:
        phi_str = lc_str + "\\frac{%s}{%s}" % (num_str, den_str)
    return phi_str


###############################################################################
# Belyi map class definitions
###############################################################################


def belyi_base_field(galmap):
    fld_coeffs = galmap["base_field"]
    if fld_coeffs == [-1, 1]:
        fld_coeffs = [0, 1]
    F = WebNumberField.from_coeffs(fld_coeffs)
    return F


class WebBelyiGalmap():
    """
    Class for a Belyi map.  Attributes include:
        data -- information about the map to be displayed
        plot -- currently empty
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels or URLs of related objects
        code -- code snippets for relevant attributes in data
        bread -- bread crumbs for home page
        title -- title to display on home page
    """

    @staticmethod
    def by_label(label, triple=None):
        """
        Searches for a specific Belyi map in the galmaps collection by its label.
        If label is for a passport, constructs an object for an arbitrarily chosen galmap in the passport
        Constructs the WebBelyiGalmap object if found, raises an error otherwise
        """
        try:
            slabel = label.split("-")
            if len(slabel) == 2: # passport label length
                galmap = db.belyi_galmaps_fixed.lucky({"plabel": label})
            elif len(slabel) == 3: # galmap label length
                galmap = db.belyi_galmaps_fixed.lucky({"label": label})
            else:
                raise ValueError("Invalid Belyi map label %s." % label)
        except AttributeError:
            raise ValueError("Invalid Belyi map label %s." % label)
        if not galmap:
            if len(slabel) == 2:
                raise KeyError(
                    "Belyi map passport label %s not found in the database." % label
                )
            else:
                raise KeyError("Belyi map %s not found in database." % label)
        return WebBelyiGalmap(galmap, triple=triple)

    def __init__(self, galmap, triple=None):
        from lmfdb.belyi.main import url_for_belyi_passport_label, url_for_belyi_galmap_label

        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}
        # the stuff that does not need to be polished
        for elt in ("label", "plabel", "triples_cyc", "orbit_size", "g", "abc", "deg", "primitivization", "is_primitive"):
            data[elt] = galmap[elt]
        if triple:
            data["label"] += '-' + (triple).replace(' ', '')
            data["triple"] = triple
        data["group"] = transitive_group_display_knowl(galmap["group"])

        data["geomtype"] = geomtypelet_to_geomtypename_dict[galmap["geomtype"]]
        data["lambdas"] = [str(c)[1:-1] for c in galmap["lambdas"]]
        data["primitivization_url"] = url_for_belyi_galmap_label(data['primitivization'])

        data["isQQ"] = False
        data["in_LMFDB"] = False
        F = belyi_base_field(galmap)
        if F._data is None:
            fld_coeffs = galmap["base_field"]
            pol = PolynomialRing(QQ, "t")(fld_coeffs)
            data["base_field"] = latex(pol)
        else:
            data["in_LMFDB"] = True
            if F.poly().degree() == 1:
                data["isQQ"] = True
            F.latex_poly = web_latex(F.poly(var="t"))
            data["base_field"] = F

        data['embeddings'] = galmap['embeddings']
        # change pairs of floats to complex numbers
        embed_strs = []
        for el in galmap["embeddings"]:
            if el[1] < 0:
                el_str = str(el[0]) + str(el[1]) + r"\sqrt{-1}"
            else:
                el_str = str(el[0]) + "+" + str(el[1]) + r"\sqrt{-1}"
            embed_strs.append(el_str)
        data["embeddings_and_triples"] = []
        self.triple = None
        self.embedding = None
        for i in range(0, len(data["triples_cyc"])):
            my_dict = {}
            triple_str = ', '.join(data['triples_cyc'][i])
            triple_link = triple_str.replace(' ','')
            if triple_link == triple:
                self.triple = data['triples_cyc'][i]
                self.embedding = CC(data['embeddings'][i])
            my_dict['triple'] = triple_str
            my_dict['triple_link'] = triple_link
            if data["isQQ"]:
                my_dict['embedding'] = r"\text{not applicable (over $\mathbb{Q}$)}"
            else:
                my_dict['embedding'] = embed_strs[i]
            data['embeddings_and_triples'].append(my_dict)

        crv_str = galmap["curve"]
        if crv_str == "PP1":
            data["curve"] = r"\mathbb{P}^1"
        else:
            data["curve"] = make_curve_latex(crv_str, nu = self.embedding)

        data["map"] = make_map_latex(galmap["map"], nu = self.embedding)
        data["lambdas"] = [str(c)[1:-1] for c in galmap["lambdas"]]

        # Properties
        self.plot = db.belyi_galmap_portraits.lucky({"label": galmap['label']},projection="portrait")
        plot_link = '<a href="{0}"><img src="{0}" width="200" height="200" style="background-color: white;"/></a>'.format(self.plot)
        properties = [("Label", galmap["label"])]
        if triple:
            properties += [("Triple", "$%s$" % triple)]
        if self.plot:
            properties += [(None, plot_link)]
        properties += [
            ("Group", str(galmap["group"])),
            ("Orders", "$%s$" % (data["abc"])),
            ("Genus", prop_int_pretty(data["g"])),
            ("Size", prop_int_pretty(data["orbit_size"])),
        ]
        self.properties = properties

        # Friends
        self.friends = [("Passport", url_for_belyi_passport_label(galmap["plabel"]))]
        if galmap['label'] != galmap['primitivization']:
            self.friends.append(("Primitivization", url_for_belyi_galmap_label(galmap["primitivization"])))
        self.friends.extend(names_and_urls(galmap['friends']))

        #add curve link, if in LMFDB
        if 'curve_label' in galmap.keys():
            data['curve_label'] = galmap['curve_label']
            for name, url in self.friends:
                if "curve" in name.lower() and data['curve_label'] in name:
                    data["curve_url"] = url

        # Downloads
        data_label = data["label"]
        if galmap["g"] <= 2:
            if triple:
                spl = data_label.split("-")
                data_label = "-".join(spl[0:-1])
            self.downloads = [
                (
                    "Code to Magma",
                    url_for(".belyi_galmap_magma_download", label=data_label),
                ),
                (
                    "Code to SageMath",
                    url_for(".belyi_galmap_sage_download", label=data_label),
                ),
                (
                    "All data to text",
                    url_for(".belyi_galmap_text_download", label=data_label),
                ),

            ]
        else:
            self.downloads = []
        self.downloads.append(("Underlying data", url_for(".belyi_data", label=data_label)))

        # Breadcrumbs
        label_spl = data["label"].split("-")
        groupstr = label_spl[0]
        letnum = label_spl[2]
        gstr = str(data['g'])
        sigmas = label_spl[1]
        sigma0, sigma1, sigmaoo = sigmas.split("_")
        abcstr = str(data['abc']).replace(' ', '')
        # does lambdasstr need to be updated?
        lambdasstr = "%s-%s-%s" % (sigma0, sigma1, sigmaoo)
        lambdasgstr = lambdasstr + "-" + gstr
        self.bread = [
            ("Belyi Maps", url_for(".index")),
            (groupstr, url_for(".by_url_belyi_search_group", group=groupstr)),
            (
                abcstr,
                url_for(
                    ".by_url_belyi_search_group_triple", group=groupstr, abc=abcstr
                ),
            ),
            (
                lambdasgstr,
                url_for(
                    ".by_url_belyi_passport_label",
                    group=groupstr,
                    abc=abcstr,
                    sigma0=sigma0,
                    sigma1=sigma1,
                    sigmaoo=sigmaoo,
                    g=gstr,
                ),
            ),
            (
                letnum,
                url_for(
                    ".by_url_belyi_galmap_label",
                    group=groupstr,
                    abc=abcstr,
                    sigma0=sigma0,
                    sigma1=sigma1,
                    sigmaoo=sigmaoo,
                    g=gstr,
                    letnum=letnum,
                ),
            ),
        ]

        # Title
        if self.triple:
            self.title = "Embedded Belyi map " + data["label"]
        else:
            self.title = "Belyi map orbit " + data["label"]

        # Code snippets (only for curves)
        self.code = {}
        self.__dict__.update(data)
        return


class WebBelyiPassport():
    """
    Class for a Belyi passport.  Attributes include:
        data -- information about the map to be displayed
        plot -- currently empty
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels or URLs of related objects
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
            if len(slabel) == 2:
                passport = db.belyi_passports_fixed.lucky({"plabel": label})
            else:
                raise ValueError("Invalid Belyi passport label %s." % label)
        except AttributeError:
            raise ValueError("Invalid passport label %s." % label)
        if not passport:
            raise KeyError("Passport %s not found in database." % label)
        return WebBelyiPassport(passport)

    def make_passport_object(self, passport):
        from lmfdb.belyi.main import url_for_belyi_galmap_label, url_for_belyi_passport_label

        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}

        for elt in ("plabel", "abc", "num_orbits", "g", "abc", "deg", "maxdegbf", "is_primitive", "primitivization"):
            data[elt] = passport[elt]

        data["group"] = transitive_group_display_knowl(passport["group"])

        data["geomtype"] = geomtypelet_to_geomtypename_dict[passport["geomtype"]]
        data["lambdas"] = [str(c)[1:-1] for c in passport["lambdas"]]
        data["pass_size"] = passport["pass_size"]
        data["primitivization_url"] = url_for_belyi_passport_label(data['primitivization'])

        # Permutation triples
        galmaps_for_plabel = db.belyi_galmaps_fixed.search(
            {"plabel": passport["plabel"]}
        )  # , sort = ['label_index'])
        galmapdata = []
        for galmap in galmaps_for_plabel:
            # wrap number field nonsense
            F = belyi_base_field(galmap)
            # inLMFDB = False
            field = {}
            if F._data is None:
                field["in_LMFDB"] = False
                fld_coeffs = galmap["base_field"]
                pol = PolynomialRing(QQ, "x")(fld_coeffs)
                field["base_field"] = latex(pol)
                field["isQQ"] = False
            else:
                field["in_LMFDB"] = True
                if F.poly().degree() == 1:
                    field["isQQ"] = True
                F.latex_poly = web_latex(F.poly(var="t"))
                field["base_field"] = F

            galmapdatum = [
                galmap["label"].split("-")[-1],
                url_for_belyi_galmap_label(galmap["label"]),
                galmap["orbit_size"],
                field,
                galmap["triples_cyc"][0][0],
                galmap["triples_cyc"][0][1],
                galmap["triples_cyc"][0][2],
            ]
            galmapdata.append(galmapdatum)
        data["galmapdata"] = galmapdata

        # Properties
        properties = [
            ("Label", passport["plabel"]),
            ("Group", str(passport["group"])),
            ("Orders", str(passport["abc"])),
            ("Genus", str(passport["g"])),
            ("Size", str(passport["pass_size"])),
            ("Galois orbits", str(passport["num_orbits"])),
        ]
        self.properties = properties

        # Friends
        self.friends = []

        # Breadcrumbs
        label_spl = data["plabel"].split("-")
        groupstr = label_spl[0]
        gstr = str(data['g'])
        sigmas = label_spl[1]
        sigma0, sigma1, sigmaoo = sigmas.split("_")
        abcstr = str(data['abc']).replace(' ', '')
        # does lambdasstr need to be updated?
        lambdasstr = "%s-%s-%s" % (sigma0, sigma1, sigmaoo)
        lambdasgstr = lambdasstr + "-" + gstr
        self.bread = [
            ("Belyi Maps", url_for(".index")),
            (groupstr, url_for(".by_url_belyi_search_group", group=groupstr)),
            (
                abcstr,
                url_for(
                    ".by_url_belyi_search_group_triple", group=groupstr, abc=abcstr
                ),
            ),
            (
                lambdasgstr,
                url_for(
                    ".by_url_belyi_passport_label",
                    group=groupstr,
                    abc=abcstr,
                    sigma0=sigma0,
                    sigma1=sigma1,
                    sigmaoo=sigmaoo,
                    g=gstr,
                ),
            ),
        ]

        # Title
        self.title = "Passport " + data["plabel"]

        # Code snippets (only for curves)
        self.code = {}
        self.__dict__.update(data)
        return

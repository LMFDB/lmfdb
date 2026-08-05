
from lmfdb.number_fields.web_number_field import WebNumberField
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl
from sage.all import gcd, latex, CC, QQ, FractionField, PolynomialRing
from lmfdb.utils import (names_and_urls, prop_int_pretty, raw_typeset,
        web_latex, compress_expression)
from flask import url_for
import re
import os

from lmfdb import db


###############################################################################
# Belyi dessin images from belyi_images.txt
###############################################################################

_belyi_images = None

def _load_belyi_images():
    global _belyi_images
    if _belyi_images is not None:
        return _belyi_images
    _belyi_images = {}
    txt_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'belyi_images.txt')
    txt_path = os.path.abspath(txt_path)
    if not os.path.exists(txt_path):
        return _belyi_images
    with open(txt_path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < 2:  # skip header rows
                continue
            line = line.rstrip('\n')
            parts = line.split('|', 2)
            if len(parts) != 3:
                continue
            belyidb_label = parts[1]
            svg_field = parts[2]
            lmfdb_plabel = _belyidb_to_lmfdb_plabel(belyidb_label)
            if lmfdb_plabel is None:
                continue
            # svg_field is a PostgreSQL text[] like {svg1,svg2,...}; split into list
            svg_field = svg_field.strip()
            if svg_field.startswith('{') and svg_field.endswith('}'):
                svg_field = svg_field[1:-1]
            # Each element is a complete <svg>...</svg>; split on the boundary between them
            raw_svgs = re.split(r'(?<=</svg>),', svg_field)
            svgs = [_crop_svg_bottom(s.replace('\\"', '"').strip()) for s in raw_svgs if s.strip()]
            _belyi_images[lmfdb_plabel] = svgs
    return _belyi_images


def _crop_svg_bottom(svg, crop_height=660):
    # The page number sits at y≈702 in a 792-unit-tall viewBox.
    # Fix: shrink the viewBox height AND the SVG height attribute proportionally,
    # and set overflow="hidden" so nothing outside the viewBox leaks through.
    # 1. Update viewBox height
    svg = re.sub(
        r'(viewBox=")(\S+\s+\S+\s+\S+\s+)\S+(")',
        lambda m: m.group(1) + m.group(2) + str(crop_height) + m.group(3),
        svg
    )
    # 2. Update the SVG height attribute proportionally (original viewBox height = 792)

    def _new_height(m):
        try:
            orig = float(m.group(1))
            new_h = round(orig * crop_height / 792)
            return 'height="{}"'.format(new_h)
        except ValueError:
            return m.group(0)
    svg = re.sub(r'height="([\d.]+)"', _new_height, svg, count=1)
    # 3. Ensure the outermost <svg> tag has overflow="hidden" to clip below the viewBox
    svg = re.sub(r'(<svg\b)(?![^>]*overflow)', r'\1 overflow="hidden"', svg, count=1)
    return svg


def _belyidb_to_lmfdb_plabel(belyidb_label):
    # "4T2-[2,2,2]-22-22-22-g0" -> "4T2-2.2_2.2_2.2"
    parts = belyidb_label.split('-')
    if len(parts) < 5:
        return None
    group = parts[0]
    # parts[1] is abc like [2,2,2] — skip it; parts[2-4] are cycle types
    sigma0 = '.'.join(list(parts[2]))
    sigma1 = '.'.join(list(parts[3]))
    sigmaoo = '.'.join(list(parts[4]))
    return '{}-{}_{}_{}'.format(group, sigma0, sigma1, sigmaoo)


def get_belyi_images(plabel):
    """Return list of SVG strings for the given LMFDB passport label, or []."""
    return _load_belyi_images().get(plabel, [])


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
    # F = FractionField(R)
    sides = crv_str.split("=")
    lhs = R(sides[0])
    rhs = R(sides[1])
    if nu and ("nu" in crv_str):
        S = PolynomialRing(CC, 2, 'x,y')
        # evaluate at nu, if given
        new_lhs = {}
        new_rhs = {}
        for m, c in lhs.dict().items():
            new_lhs[m] = c.subs(nu=nu)
        for m, c in rhs.dict().items():
            new_rhs[m] = c.subs(nu=nu)
        lhs = S(new_lhs)  # R, or something else, like CC[]?
        rhs = S(new_rhs)
    eqn_str = latex(lhs) + "=" + latex(rhs)
    return eqn_str

def make_map_latex(map_str, nu=None):
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
        num_dict = {}
        den_dict = {}
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

#def make_plane_model_latex(crv_str, nu=None):
#    if "nu" not in crv_str:
#        R0 = QQ
#    else:
#        R0 = PolynomialRing(QQ, "nu")
#    R = PolynomialRing(R0, 2, "t,x")
#    f = R(crv_str)
#    #return teXify_pol(f)
#    return latex(f)+"=0"
#
#def make_plane_model_latex_factored(crv_str, numfld_cs, nu=None):
#    R0 = PolynomialRing(QQ,"T")
#    K = NumberField(R0(numfld_cs), "nu") # sage factors out constants, ruining integrality
#    S0 = PolynomialRing(K,"x")
#    S = PolynomialRing(S0,"t")
#    t = S.gens()[0]
#    f = S(crv_str)
#    cs = f.coefficients()
#    cs.reverse()
#    mons = f.monomials()
#    L = len(cs)
#    f_str = ""
#    for i in range(0,L-1):
#        f_str += "%s%s" % (latex(factor(cs[i])), latex(t**(L-i-1)))
#        if i != L-2:
#            f_str += "+"
#    if mons[-1] == 1:
#        f_str += latex(factor(cs[-1]))
#    else:
#        f_str += latex(factor(cs[-1])) + latex(mons[-1])
#    return f_str

def belyi_latex(s):
    str = s.replace('*',' ')
    str = str.replace('(',r'\left(')
    str = str.replace(')',r'\right)')
    str = str.replace('nu',r'\nu')
    # multidigit exponents
    str = re.sub(r'\^\s*(\d+)', r'^{\1}',str)
    return str

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
                galmap = db.belyi_galmaps.lucky({"plabel": label})
            elif len(slabel) == 3: # galmap label length
                galmap = db.belyi_galmaps.lucky({"label": label})
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
            pol = PolynomialRing(QQ, "T")(fld_coeffs)
            data["base_field"] = latex(pol)
        else:
            data["in_LMFDB"] = True
            if F.poly().degree() == 1:
                data["isQQ"] = True
            F.latex_poly = web_latex(F.poly(var="T"))
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
        for i in range(len(data["triples_cyc"])):
            my_dict = {}
            triple_str = ', '.join(data['triples_cyc'][i])
            triple_link = triple_str.replace(' ', '')
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

        # Friends
        self.friends = [("Passport", url_for_belyi_passport_label(galmap["plabel"]))]
        if galmap['label'] != galmap['primitivization']:
            self.friends.append(("Primitivization", url_for_belyi_galmap_label(galmap["primitivization"])))
        self.friends.extend(names_and_urls(galmap['friends']))

        curve_ref = ''
        # add curve link, if in LMFDB
        if 'curve_label' in galmap:
            data['curve_label'] = galmap['curve_label']
            for name, url in self.friends:
                if "curve" in name.lower() and data['curve_label'] in name:
                    data["curve_url"] = url

            # curve reference
            curve_ref = ', isomorphic to '
            if galmap['g'] == 1:
                curve_ref += 'elliptic'
            if galmap['g'] == 2:
                curve_ref += 'genus 2'
            curve_ref += rf' curve with label <a href="{url}">{data["curve_label"]}</a>'

        # curve equations
        crv_str = galmap["curve"]
        if crv_str == "PP1":
            data["curve"] = r"$\mathbb{P}^1$"
        else:
            data["curve"] = raw_typeset(crv_str, r'$\displaystyle '+compress_expression(make_curve_latex(crv_str, nu=self.embedding))+'$', extra=curve_ref)

        data["map"] = raw_typeset(galmap["map"], r'$\displaystyle '+compress_expression(make_map_latex(galmap["map"], nu=self.embedding))+'$')
        data["lambdas"] = [str(c)[1:-1] for c in galmap["lambdas"]]
        # plane model
        if galmap.get("plane_model"):
            data["plane_model"] = raw_typeset(galmap["plane_model"]+'=0', r'$\displaystyle '+compress_expression(belyi_latex(galmap["plane_model"]))+'=0$', extra=curve_ref)

        if galmap.get('plane_map_constant_factored'):
            data['plane_map_constant_factored'] = galmap['plane_map_constant_factored']

        # Dessin images (one per embedding, or a single shared one)
        data['dessin_svgs'] = get_belyi_images(galmap['plabel'])

        # Properties
        self.plot = db.belyi_galmap_portraits.lucky({"label": galmap['label']},
                                                    projection="portrait")
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
                passport = db.belyi_passports.lucky({"plabel": label})
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
        galmaps_for_plabel = db.belyi_galmaps.search(
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
                F.latex_poly = web_latex(F.poly(var="T"))
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

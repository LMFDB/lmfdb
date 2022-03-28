# -*- coding: utf-8 -*-

from collections import Counter
from flask import url_for

from sage.all import lazy_attribute, prod, euler_phi, ZZ, QQ, latex, PolynomialRing, lcm, NumberField, FractionField
from lmfdb.utils import WebObj, integer_prime_divisors, teXify_pol, web_latex
from lmfdb import db
from lmfdb.classical_modular_forms.main import url_for_label as url_for_mf_label
from lmfdb.elliptic_curves.web_ec import latex_equation as EC_equation
from lmfdb.elliptic_curves.elliptic_curve import url_for_label as url_for_EC_label
from lmfdb.ecnf.main import url_for_label as url_for_ECNF_label
from lmfdb.number_fields.number_field import url_for_label as url_for_NF_label


def get_bread(tail=[]):
    base = [("Modular curves", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def showexp(c, wrap=True):
    if c == 1:
        return ""
    elif wrap:
        return f"$^{{{c}}}$"
    else:
        return f"^{{{c}}}"

def showj(j):
    if j[0] == 0:
        return rf"$0$"
    elif j[1] == 1:
        return rf"${j[0]}$"
    else:
        return r"$\tfrac{%s}{%s}$" % tuple(j)

def showj_fac(j):
    if j[0] == 0 or j[1] == 1 and ZZ(j[0]).is_prime():
        return ""
    else:
        return "$= %s$" % latex((ZZ(j[0]) / ZZ(j[1])).factor())

def showj_nf(j, nflabel):
    Ra = PolynomialRing(QQ, 'a')
    if "," in j:
        f = Ra([QQ(c) for c in j.split(",")])
        if nflabel.startswith("2."):
            D = ZZ(nflabel.split(".")[2])
            if nflabel.split(".")[1] == "0":
                D = -D
            x = Ra.gen()
            if D % 4 == 1:
                K = NumberField(x**2 - x - (D - 1)//4, 'a')
            else:
                K = NumberField(x**2 - D//4, 'a')
            if K.class_number() == 1:
                jj = K((f).padded_list(K.degree()))
                jfac = latex(jj.factor())
                if D % 4 == 0:
                    jfac = jfac.replace("a", r"\sqrt{%s}" % (D // 4))
                return f"${jfac}$"
        d = f.denominator()
        if d == 1:
            return web_latex(f)
        else:
            return fr"$\tfrac{{1}}{{{latex(d.factor())}}} \left({latex(d*f)}\right)$"
    if "/" in j:
        fac = f" = {latex(QQ(j).factor())}"
        a, b = j.split("/")
        j = r"\tfrac{%s}{%s}" % (a, b)
    elif j != "0":
        fac = f" = {latex(ZZ(j).factor())}"
    else:
        fac = ""
    return f"${j}{fac}$"

def canonicalize_name(name):
    cname = "X" + name[1:].lower().replace("_", "").replace("^", "")
    if cname[:4] == "Xs4(":
        cname = cname.upper()
    return cname

def name_to_latex(name):
    if not name:
        return ""
    name = canonicalize_name(name)
    if "+" in name:
        name = name.replace("+", "^+")
    if "ns" in name:
        name = name.replace("ns", "{\mathrm{ns}}")
    elif "sp" in name:
        name = name.replace("sp", "{\mathrm{sp}}")
    elif "S4" in name:
        name = name.replace("S4", "{S_4}")
    if name[1] != "(":
        name = "X_" + name[1:]
    return f"${name}$"

def factored_conductor(conductor):
    return "\\cdot".join(f"{p}{showexp(e, wrap=False)}" for (p, e) in conductor) if conductor else "1"

def remove_leading_coeff(jfac):
    if "(%s)" % jfac.unit() == (str(jfac).split("*")[0]).replace(' ',''):
        return "*".join(str(jfac).split("*")[1:])
    else:
        return str(jfac)

def jmap_factored(j_str):
    if 't' in j_str:
        R = PolynomialRing(QQ, 't')
        t = R.gens()[0]
        F = FractionField(R)
    else:
        #assert ('x' in j_str or 'z' in j_str)
        R = PolynomialRing(QQ,2,'x,z')
        x = R.gens()[0]
        z = R.gens()[1]
        F = FractionField(R)
    j = F(j_str)
    # deal with leading coefficient
    j_lc = j.factor().unit()
    j_no_lc = j/j_lc
    jmap_parts = [j_no_lc.numerator(), j_no_lc.denominator()]
    j_lc_1728 = (j-1728).factor().unit()
    j_no_lc_1728 = (j-1728)/j_lc_1728
    jmap_parts_1728 = [j_no_lc_1728.numerator(), j_no_lc_1728.denominator()]
    js_tex = [teXify_pol(remove_leading_coeff(el.factor())) for el in jmap_parts]
    js_tex_1728 = [teXify_pol(remove_leading_coeff(el.factor())) for el in jmap_parts_1728]
    if j_lc != 1:
        lc_str = "%s" % latex(j_lc)
        #if lc_str[0] == "-": # parens if minus sign
            #lc_str = "(%s)" % lc_str
        if "+" in lc_str[1:] or "-" in lc_str[1:]:
            lc_str = "\\left(%s\\right)" % lc_str
    else:
        lc_str = ""
    if j_lc_1728 != 1:
        lc_str_1728 = "%s" % latex(j_lc_1728)
        if "+" in lc_str_1728 or "-" in lc_str_1728:
            lc_str_1728 = "\\left(%s\\right)" % lc_str_1728
    else:
        lc_str_1728 = ""
    # good test case for lc stuff: 8.96.1.183
    # also 4.8.0.2
    if j.denominator() == 1: # no denom, so polynomial
        js_tex_frac = []
        js_tex_frac.append(r"%s%s" % (lc_str, js_tex[0]))
        js_tex_frac.append(r"1728 + %s%s" % (lc_str_1728, js_tex[1]))
    else: # has denom
        js_tex_frac = []
        js_tex_frac.append(r"%s\frac{%s}{%s}" % (lc_str, js_tex[0], js_tex[1]))
        js_tex_frac.append(r"1728 + %s\frac{%s}{%s}" % (lc_str_1728, js_tex_1728[0], js_tex_1728[1]))
    return js_tex_frac

def j_table(j_str):
    js_tex = jmap_factored(j_str)
    s = "<table class='coeff_ring_basis'>\n"
    s += r'<tr><td class="LHS">\( j \)</td><td class="eq">\(=\)</td><td class="RHS">\( %s \)</td></tr>' % js_tex[0] + '\n'
    s += r'<tr><td class="LHS"> </td><td class="eq">\(=\)</td><td class="RHS">\( %s \)</td></tr>' % js_tex[1]
    return s + "</table>"

def formatted_dims(dims):
    if not dims:
        return ""
    C = Counter(dims)
    return "$" + ",".join(f"{d}{showexp(c, wrap=False)}" for (d, c) in sorted(C.items())) + "$"

def formatted_newforms(newforms):
    if not newforms:
        return ""
    C = Counter(newforms)
    # Make sure that the Counter doesn't break the ordering
    return ",&nbsp;".join(f'<a href="{url_for_mf_label(label)}">{label}</a>{showexp(c)}' for (label, c) in C.items())

def difference(A,B):
    C = A.copy()
    for f in B:
        if f in C:
            C.pop(C.index(f))
    return C

def modcurve_link(label):
    return '<a href="%s">%s</a>'%(url_for(".by_label",label=label),label)

class WebModCurve(WebObj):
    table = db.gps_gl2zhat_test

    @lazy_attribute
    def properties(self):
        props = [
            ("Label", self.label),
            ("Level", str(self.level)),
            ("Index", str(self.index)),
            ("Genus", str(self.genus)),
        ]
        if hasattr(self,"rank"):
            props.append(("Rank", str(self.rank)))
        props.extend([("Cusps", str(self.cusps)),
                      (r"$\Q$-cusps", str(self.rational_cusps))])
        return props

    @lazy_attribute
    def friends(self):
        friends = []
        if self.genus > 0:
            for r in self.table.search({'trace_hash':self.trace_hash},['label','name','newforms']):
                if r['newforms'] == self.newforms and r['label'] != self.label:
                    friends.append(("Modular curve " + (r['name'] if r['name'] else r['label']),url_for("modcurve.by_label", label=r['label'])))
        if self.simple:
            friends.append(("Modular form " + self.newforms[0], url_for_mf_label(self.newforms[0])))
            if self.genus == 1:
                s = self.newforms[0].split(".")
                label = s[0] + "." + s[2]
                friends.append(("Isogeny class " + label, url_for("ec.by_ec_label", label=label)))
            if self.genus == 2:
                g2c_url = db.lfunc_instances.lucky({'Lhash':str(self.trace_hash), 'type' : 'G2Q'}, 'url')
                if g2c_url:
                    s = g2c_url.split("/")
                    label = s[2] + "." + s[3]
                    friends.append(("Isogeny class " + label, url_for("g2c.by_label", label=label)))
            friends.append(("L-function", "/L" + url_for_mf_label(self.newforms[0])))
        else:
            friends.append(("L-function not available",""))
        return friends

    @lazy_attribute
    def bread(self):
        tail = []
        A = ["level", "index", "genus"]
        D = {}
        for a in A:
            D[a] = getattr(self, a)
            tail.append(
                (str(D[a]), url_for(".index_Q", **D))
            )
        tail.append((self.label, " "))
        return get_bread(tail)

    @lazy_attribute
    def title(self):
        if self.name:
            return f"Modular curve {name_to_latex(self.name)}"
        else:
            return f"Modular curve {self.label}"

    @lazy_attribute
    def formatted_dims(self):
        return formatted_dims(self.dims)

    @lazy_attribute
    def formatted_newforms(self):
        return formatted_newforms(self.newforms)

    @lazy_attribute
    def latexed_plane_model(self):
        return teXify_pol(self.plane_model)

    @lazy_attribute
    def obstruction_primes(self):
        return ",".join(str(p) for p in self.obstructions[:3] if p != 0) + r"\ldots"

    @lazy_attribute
    def qtwist_description(self):
        if self.contains_negative_one:
            if len(self.qtwists) > 1:
                return r"$\textsf{yes}\quad$ (see %s for level structures without $-I$)"%(', '.join([modcurve_link(label) for label in self.qtwists[1:]]))
            else:
                return ""
        else:
            return r"$\textsf{no}\quad$ (see %s for the level structure with $-I$)"%(modcurve_link(self.qtwists[0]))

    @lazy_attribute
    def cusp_display(self):
        if self.cusps == 1:
            return "$1$ (which is rational)"
        elif self.rational_cusps == 0:
            return f"${self.cusps}$ (none of which are rational)"
        elif self.rational_cusps == 1:
            return f"${self.cusps}$ (of which $1$ is rational)"
        elif self.cusps == self.rational_cusps:
            return f"${self.cusps}$ (all of which are rational)"
        else:
            return f"${self.cusps}$ (of which ${self.rational_cusps}$ are rational)"

    @lazy_attribute
    def cm_discriminant_list(self):
        return ",".join(str(D) for D in self.cm_discriminants)

    @lazy_attribute
    def factored_conductor(self):
        return factored_conductor(self.conductor)

    @lazy_attribute
    def jmap_factored(self):
        if self.jmap:
            return jmap_factored(self.jmap)
        else:
            return ""

    @lazy_attribute
    def j_table(self):
        if self.jmap:
            return j_table(self.jmap)
        else:
            return ""

    def cyclic_isogeny_field_degree(self):
        return min(r[1] for r in self.isogeny_orbits if r[0] == self.level)

    def cyclic_torsion_field_degree(self):
        return min(r[1] for r in self.orbits if r[0] == self.level)

    def full_torsion_field_degree(self):
        N = self.level
        P = integer_prime_divisors(N)
        GL2size = euler_phi(N) * N * (N // prod(P))**2 * prod(p**2 - 1 for p in P)
        return GL2size // self.index

    def show_generators(self):
        return ", ".join(r"$\begin{bmatrix}%s&%s\\%s&%s\end{bmatrix}$" % tuple(g) for g in self.generators)

    def modular_covers(self):
        curves = self.table.search({"label":{"$in": self.parents}, "contains_negative_one": self.contains_negative_one}, ["label", "name", "rank", "dims"])
        return [(C["label"], name_to_latex(C["name"]) if C.get("name") else C["label"], C["label"].split(".")[0], self.index // int(C["label"].split(".")[1]), C["label"].split(".")[2], C["rank"] if C.get("rank") is not None else "", formatted_dims(difference(self.dims,C.get("dims",[])))) for C in curves]

    def modular_covered_by(self):
        curves = self.table.search({"parents":{"$contains": self.label},"contains_negative_one": self.contains_negative_one}, ["label", "name", "rank", "dims"])
        return [(C["label"], name_to_latex(C["name"]) if C.get("name") else C["label"], C["label"].split(".")[0], int(C["label"].split(".")[1]) // self.index, C["label"].split(".")[2], C["rank"] if C.get("rank") is not None else "", formatted_dims(difference(C.get("dims",[]),self.dims))) for C in curves]

    @lazy_attribute
    def newform_level(self):
        return lcm([int(f.split('.')[0]) for f in self.newforms])

    @lazy_attribute
    def downloads(self):
        self.downloads = [
            (
                "Code to Magma",
                url_for(".modcurve_magma_download", label=self.label),
            ),
            (
                "Code to SageMath",
                url_for(".modcurve_sage_download", label=self.label),
            ),
            (
                "All data to text",
                url_for(".modcurve_text_download", label=self.label),
            ),
            (
                'Underlying data',
                url_for(".modcurve_data", label=self.label),
            )

        ]
        #self.downloads.append(("Underlying data", url_for(".belyi_data", label=self.label)))
        return self.downloads

    @lazy_attribute
    def known_degree1_points(self):
        return db.modcurve_points.count({"curve_label": self.label, "degree": 1})

    @lazy_attribute
    def known_degree1_noncm_points(self):
        return db.modcurve_points.count({"curve_label": self.label, "degree": 1, "cm": 0})

    @lazy_attribute
    def known_low_degree_points(self):
        return db.modcurve_points.count({"curve_label": self.label, "degree": {"$gt": 1}})

    @lazy_attribute
    def db_rational_points(self):
        # Use the db.ec_curvedata table to automatically find rational points
        limit = None if (self.genus > 1 or self.genus == 1 and self.rank == 0) else 10
        if ZZ(self.level).is_prime_power():
            curves = (list(db.ec_curvedata.search(
                {"elladic_images": {"$contains": self.label}, "cm": 0},
                sort=["conductor", "iso_nlabel", "lmfdb_number"],
                one_per=["jinv"],
                limit=limit,
                projection=["lmfdb_label", "ainvs", "jinv", "cm"])) +
                      list(db.ec_curvedata.search(
                {"elladic_images": {"$contains": self.label}, "cm": {"$ne": 0}},
                sort=["conductor", "iso_nlabel", "lmfdb_number"],
                one_per=["jinv"],
                limit=None,
                projection=["lmfdb_label", "ainvs", "jinv", "cm", "conductor", "iso_nlabel", "lmfdb_number"])))
            curves.sort(key=lambda x: (x["conductor"], x["iso_nlabel"], x["lmfdb_number"]))
            return [(rec["lmfdb_label"], url_for_EC_label(rec["lmfdb_label"]), EC_equation(rec["ainvs"]), r'$\textsf{no}$' if rec["cm"] == 0 else f'${rec["cm"]}$', showj(rec["jinv"]), showj_fac(rec["jinv"]))
                    for rec in curves]
        else:
            return []

    @lazy_attribute
    def db_nf_points(self):
        pts = []
        for rec in db.modcurve_points.search({"curve_label": self.label, "degree": {"$gt": 1}}, sort=["degree"]):
            pts.append(
                (rec["Elabel"],
                 url_for_ECNF_label(rec["Elabel"]) if rec["Elabel"] else "",
                 r"$\textsf{no}$" if rec["cm"] == 0 else f'${rec["cm"]}$',
                 r"$\textsf{yes}$" if rec["isolated"] is True else (r"$\textsf{no}$" if rec["isolated"] is False else r"$\textsf{maybe}$"),
                 showj_nf(rec["jinv"], rec["j_field"]),
                 rec["residue_field"],
                 url_for_NF_label(rec["residue_field"]),
                 rec["j_field"],
                 url_for_NF_label(rec["j_field"]),
                 rec["degree"]))
        return pts

    @lazy_attribute
    def old_db_nf_points(self):
        # Use the db.ec_curvedata table to automatically find rational points
        #limit = None if (self.genus > 1 or self.genus == 1 and self.rank == 0) else 10
        if ZZ(self.level).is_prime():
            curves = list(db.ec_nfcurves.search(
                {"galois_images": {"$contains": self.Slabel},
                 "degree": {"$lte": self.genus}},
                one_per=["jinv"],
                projection=["label", "degree", "equation", "jinv", "cm"]))
            Ra = PolynomialRing(QQ,'a')
            return [(rec["label"],
                     url_for_ECNF_label(rec["label"]),
                     rec["equation"],
                     r"$\textsf{no}$" if rec["cm"] == 0 else f'${rec["cm"]}$',
                     r"$\textsf{yes}$" if (rec["degree"] < ZZ(self.gonality_bounds[0]) / 2 or rec["degree"] < self.gonality_bounds[0] and (self.rank == 0 or self.simple and rec["degree"] < self.genus)) else r"$\textsf{maybe}$",
                     web_latex(Ra([QQ(s) for s in rec["jinv"].split(',')]))) for rec in curves]
        else:
            return []


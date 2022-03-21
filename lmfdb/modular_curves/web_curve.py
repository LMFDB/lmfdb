# -*- coding: utf-8 -*-

from collections import Counter
from flask import url_for

from sage.all import lazy_attribute, prod, euler_phi, ZZ
from lmfdb.utils import WebObj, integer_prime_divisors, teXify_pol
from lmfdb import db
from lmfdb.classical_modular_forms.main import url_for_label as url_for_mf_label
from lmfdb.elliptic_curves.web_ec import latex_equation as EC_equation
from lmfdb.elliptic_curves.elliptic_curve import url_for_label as url_for_EC_label

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
        curves = db.gps_gl2zhat_test.search({"label":{"$in": self.parents}}, ["label", "name", "rank", "dims"])
        return [(C["label"], name_to_latex(C["name"]) if C.get("name") else C["label"], C["label"].split(".")[0], self.index // int(C["label"].split(".")[1]), C["label"].split(".")[2], C["rank"] if C.get("rank") is not None else "", formatted_dims(difference(self.dims,C.get("dims",[])))) for C in curves]

    def modular_covered_by(self):
        curves = db.gps_gl2zhat_test.search({"parents":{"$contains": self.label}}, ["label", "name", "rank", "dims"])
        return [(C["label"], name_to_latex(C["name"]) if C.get("name") else C["label"], C["label"].split(".")[0], int(C["label"].split(".")[1]) // self.index, C["label"].split(".")[2], C["rank"] if C.get("rank") is not None else "", formatted_dims(difference(C.get("dims",[]),self.dims))) for C in curves]

    @lazy_attribute
    def db_rational_points(self):
        # Use the db.ec_curvedata table to automatically find rational points
        limit = None if self.genus > 1 else 10
        if ZZ(self.level).is_prime_power():
            return [(rec["lmfdb_label"], url_for_EC_label(rec["lmfdb_label"]), EC_equation(rec["ainvs"]), r"$\tfrac{%s}{%s}$" % tuple(rec["jinv"]))
                    for rec in db.ec_curvedata.search(
                            {"elladic_images": {"$contains": self.label}},
                            sort=["conductor", "iso_nlabel", "lmfdb_number"],
                            one_per=["conductor", "iso_nlabel"],
                            limit=limit,
                            projection=["lmfdb_label", "ainvs", "jinv"])]
        else:
            return []

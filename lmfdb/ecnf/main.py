# -*- coding: utf-8 -*-
# This Blueprint is about Elliptic Curves over Number Fields
# Authors: Harald Schilly and John Cremona

#import re
import pymongo
ASC = pymongo.ASCENDING
#import flask
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, redirect
from lmfdb.utils import image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ, GCD
from lmfdb.ecnf import ecnf_page, logger
from lmfdb.number_fields.number_field import parse_field_string, field_pretty

credit = "John Cremona, Paul Gunnells, Dan Yasaki, Alyson Deines, John Voight"

ecnf = None
nfdb = None

def db_ecnf():
    global ecnf
    if ecnf is None:
        ecnf = getDBConnection().elliptic_curves.nfcurves
    return ecnf

def db_nfdb():
    global nfdb
    if nfdb is None:
        nfdb = getDBConnection().numberfields.fields
    return nfdb

class FIELD(object):
    """
    Number Field wrapper
    """
    names = {'2.0.4.1': 'i',
             '2.2.5.1': 'phi',
             '4.0.125.1': 'zeta5',
             }

    def __init__(self, label):
        dbdata = db_nfdb().find_one({'label': label})
        self.__dict__.update(dbdata)
        self.make_K()

    def make_K(self):
        coeffs = map(int, self.coeffs.split(","))
        poly = PolynomialRing(QQ,'x')(coeffs)
        name = FIELD.names.get(self.label, 'a')
        from sage.rings.all import NumberField
        self.K = NumberField(poly, name)
        self.pretty_label = field_pretty(self.label)
        self.poly = web_latex(self.K.defining_polynomial())
        self.generator = web_latex(self.K.gen())
        self.disc = web_latex(self.K.discriminant())
        self.funits = ",".join([web_latex(u) for u in self.K.units()])
        self.real_quadratic = (self.signature=='2,0')
        self.imag_quadratic = (self.signature=='0,1')
        self.class_number = self.K.class_number()

    def parse_NFelt(self,s):
        """
        convert a list of d strings (rationals) to a field element
        """
        return self.K([QQ(str(c)) for c in s])

class ECNF(object):
    """
    ECNF Wrapper
    """

    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        #del dbdata["_id"]
        self.__dict__.update(dbdata)
        self.field = FIELD(self.field_label)
        self.make_E()

    @staticmethod
    def by_label(label):
        """
        searches for a specific elliptic curve in the ecnf collection by its label
        """
        data = db_ecnf().find_one({"label" : label})
        if data:
            return ECNF(data)
        print "No such curve in the database: %s" % label

    def make_E(self):
        coeffs = self.ainvs # list of 5 lists of d strings
        self.ainvs = [self.field.parse_NFelt(x) for x in coeffs]
        from sage.schemes.elliptic_curves.all import EllipticCurve
        self.E = E = EllipticCurve(self.ainvs)
        self.equn = web_latex(E)

        # Conductor, discriminant, j-invariant
        N = E.conductor()
        self.cond = web_latex(N)
        self.cond_norm = web_latex(N.norm())
        if N.norm()==1:  # since the factorization of (1) displays as "1"
            self.fact_cond = self.cond
        else:
            self.fact_cond = web_latex(N.factor())
        self.fact_cond_norm = web_latex(N.norm().factor())
        D = E.discriminant()
        self.disc = web_latex(D)
        try:
            self.fact_disc = web_latex(D.factor())
        except ValueError: # if not all prime ideal factors principal
            pass
            #self.fact_disc = web_latex(self.field.K.ideal(D).factor())
        j = E.j_invariant()
        d = j.denominator()
        n = d*j # numerator exists for quadratic fields only!
        g = GCD(list(n))
        n1 = n/g
        self.j = web_latex(n1)
        if d!=1:
            self.j = "("+self.j+")\(/\)"+web_latex(d)
        if g>1: self.j = web_latex(g) + self.j
        try:
            self.fact_j = web_latex(j.factor())
        except ValueError: # if not all prime ideal factors principal
            pass
            #self.fact_j = self.j

        # CM and End(E)
        self.cm_bool = "no"
        self.End = "\(\Z\)"
        if self.cm:
            self.cm_bool = "yes (\(%s\))" % self.cm
            if self.cm%4==0:
                d4 = ZZ(self.cm)//4
                self.End = "\(\Z[\sqrt{%s}]\)"%(d4)
            else:
                self.End = "\(\Z[(1+\sqrt{%s})/2]\)" % self.cm

        # Base change
        self.bc = "no"
        if self.base_change: self.bc = "yes"

        # Torsion
        self.ntors = web_latex(self.torsion_order)
        self.tr = len(self.torsion_structure)
        if self.tr==0:
            self.tor_struct_pretty = "Trivial"
        if self.tr==1:
            self.tor_struct_pretty = "\(\Z/%s\Z\)" % self.torsion_structure[0]
        if self.tr==2:
            self.tor_struct_pretty = "\(\Z/%s\Z\times\Z/%s\Z\)" % self.torsion_structure
        torsion_gens = [E([self.field.parse_NFelt(x) for x in P])
                        for P in self.torsion_gens]
        self.torsion_gens = ",".join([web_latex(P) for P in torsion_gens])


        # Rank etc
        try:
            self.rk = web_latex(self.rank)
        except AttributeError:
            self.rk = "not known"
#       if rank in self:
#            self.r = web_latex(self.rank)

        # Local data
        self.local_data = []
        for p in N.prime_factors():
            self.local_info = E.local_data(p, algorithm="generic")
            self.local_data.append({'p': web_latex(p),
                               'tamagawa_number': self.local_info.tamagawa_number(),
                               'kodaira_symbol': web_latex(self.local_info.kodaira_symbol()).replace('$', ''),
                               'reduction_type': self.local_info.bad_reduction_type()
                               })

        if self.field.real_quadratic:
            self.hmf_label = self.field.label+"-"+self.conductor_label+"-"+self.iso_label
        if self.field.imag_quadratic:
            self.bmf_label = self.field.label+"-"+self.conductor_label+"-"+self.iso_label

def get_bread(*breads):
    bc = [("ECNF", url_for(".index"))]
    map(bc.append, breads)
    return bc

@ecnf_page.route("/")
def index():
    bread = get_bread()
    return render_template("ecnf-index.html",
        title="Elliptic Curve Number Field",
        bread=bread)


@ecnf_page.route("/<nf>/<label>")
def show_ecnf(nf, label):
    nf_label = parse_field_string(nf)
    bread = get_bread((label, url_for(".show_ecnf", label = label, nf = nf_label)))
    label = nf_label + "-" + label
    print label
    ec = ECNF.by_label(label)
    title = "Elliptic Curve %s over Number Field %s" % (label, ec.field.pretty_label)
    info = {}
    properties = [
('Base field', ec.field.pretty_label),
('Class number', str(ec.field.class_number)),
('Label' , ec.label),
('Conductor' , ec.cond),
('Conductor norm' , ec.cond_norm),
('j-invariant' , ec.j),
('CM' , ec.cm_bool),
('Base change' , ec.bc),
('Torsion order' , ec.ntors),
('Rank' , ec.rk),
]

    return render_template("show-ecnf.html",
        credit=credit,
        title=title,
        bread=bread,
        ec=ec,
        properties = properties,
        properties2 = properties,
        info=info)


@ecnf_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("ecnf-index.html", title="Elliptic Curve Search", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return redirect(404)


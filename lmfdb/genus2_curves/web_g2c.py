# -*- coding: utf-8 -*-
import re
import tempfile
import os
from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.genus2_curves import g2c_page, g2c_logger

import sage.all
from sage.all import EllipticCurve, latex, matrix, ZZ, QQ, PolynomialRing

logger = make_logger("g2c")

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves.curves
    return g2cdb

def list_to_min_eqn(L):
    xpoly_rng = PolynomialRing(QQ,'x')
    ypoly_rng = PolynomialRing(xpoly_rng,'y')
    poly_tup = [xpoly_rng(tup) for tup in L]
    lhs = ypoly_rng([0,poly_tup[1],1])
    return str(lhs).replace("*","") + " = " + str(poly_tup[0]).replace("*","")

class WebG2C(object):
    """
    Class for a genus 2 curve over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        #logger.debug("Constructing an instance of G2Cisog_class")
        self.__dict__.update(dbdata)
        self.make_curve()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific elliptic curve in the curves
        collection by its label, which can be either in LMFDB or
        Cremona format.
        label is string separated by "."
        """
        try:
            print label
            data = db_g2c().find_one({"label" : label})
            
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error

        if data:
            return WebG2C(data)
        return "Curve not found" # caller must catch this and raise an error

    def make_curve(self):
        # To start with the data fields of self are just those from
        # the database.  We need to reformat these, construct the
        # actual elliptic curve E, and compute some further (easy)
        # data about it.
        #

        # Weierstrass equation

        data = self.data = {}
        data['label'] = self.label
        data['disc'] = self.disc
        data['igusa_clebsch'] = web_latex(self.igusa_clebsch)
        data['min_eqn'] = list_to_min_eqn(self.min_eqn)
        # TODO: once aut group info in database, uncomment
        #data['aut_grp'] = web_latex(self.aut_grp)
        #data['geom_aut_grp'] = web_latex(self.geom_aut_grp)
        self.friends = []
        self.downloads = []


        self.properties = [('Label', self.label), ('Minimal discriminant', '\( %s \)' % self.disc)]
        self.title = "Genus 2 Curve %s" % (self.label)
        self.bread = [
# ('Elliptic Curves', url_for("ecnf.index")),
#                           ('$\Q$', url_for(".rational_genus2_curves")),
#                           ('%s' % N, url_for(".by_conductor", conductor=N)),
#                           ('%s' % iso, url_for(".by_double_iso_label", conductor=N, iso_label=iso)),
#                           ('%s' % num,' ')
        ]

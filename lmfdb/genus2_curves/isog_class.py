# -*- coding: utf-8 -*-
import re
import os

from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.genus2_curves.web_g2c import g2c_page, g2c_logger, list_to_min_eqn
from sage.all import QQ

logger = make_logger("g2c")

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves.isogeny_classes
    return g2cdb

def list_to_poly(s):
    return str(PolynomialRing(QQ, 'x')(s)).replace('*','')

class G2Cisog_class(object):
    """
    Class for an isogeny class of genus 2 curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        logger.debug("Constructing an instance of G2Cisog_class")
        self.__dict__.update(dbdata)
        self.make_class()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific genus 2 curve isogeny class in the
        curves collection by its label.
        """
        try:
            data = db_g2c().find_one({"label" : label})
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error

        if data:
            return G2Cisog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        curves_data = db_g2c().find({"isog_class" : self.label})
        self.curves = [ {"label" : c.label, "equation_formatted" : list_to_min_eqn(c.equation)} for c in curves_data ]
        self.ncurves = curves_data.count()
        self.friends = [
#        ('L-function', self.lfunction_link),
#        ('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', label=self.lmfdb_iso)),
#        ('Symmetric 4th power L-function', url_for("l_functions.l_function_ec_sym_page", power='4', label=self.lmfdb_iso)),
#        ('Modular form ' + self.newform_label, self.newform_link)]
         ]

        self.properties = [('Label', self.label),
                           ('Number of curves', str(self.ncurves)),
                           ('Conductor', '\(%s\)' % self.cond),
                           ]

        self.title = "Genus 2 Isogeny Class %s" % (self.label)
        self.downloads = []
#                         ('Download coeffients of newform', url_for(".download_EC_qexp", label=self.lmfdb_iso, limit=100)),
#                         ('Download stored data for all curves', url_for(".download_EC_all", label=self.lmfdb_iso))]
        
        self.bread = [
#('Elliptic Curves', url_for("ecnf.index")),
#                      ('$\Q$', url_for(".rational_genus2_curves")),
#                      ('%s' % N, url_for(".by_conductor", conductor=N)),
#                      ('%s' % iso, ' ')
                     ]

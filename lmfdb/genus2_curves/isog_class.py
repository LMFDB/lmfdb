
# -*- coding: utf-8 -*-
import re
import os

from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.genus2_curves.web_g2c import g2c_page, g2c_logger, list_to_min_eqn
from sage.all import QQ, PolynomialRing

logger = make_logger("g2c")

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves
    return g2cdb

def list_to_poly(s):
    return str(PolynomialRing(QQ, 'x')(s)).replace('*','')

def url_for_label(label):
    # returns the url for label
    L = label.split(".")
    return url_for(".by_full_label", conductor=L[0], iso_label=L[1], disc=L[2], number=L[3])

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
            data = db_g2c().isogeny_classes.find_one({"label" : label})
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error

        if data:
            return G2Cisog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        curves_data = db_g2c().curves.find({"class" : self.label})
        self.curves = [ {"label" : c['label'], "equation_formatted" : list_to_min_eqn(c['min_eqn']), "url": url_for_label(c['label'])} for c in curves_data ]
        self.ncurves = curves_data.count()
        self.bad_lfactors = [ [c[0], list_to_poly(c[1])] for c in self.bad_lfactors]
        self.real_end_alg_name = self.real_end_alg

        # TODO:  When these cells are in the database, uncomment below
        #self.end_alg_name = self.end_alg
        #self.rat_end_alg_name = self.rat_end_alg
        #self.geom_end_alg_name = self.geom_end_alg
        #self.fullrat_end_alg_name = self.full_rat_end_alg
        
        self.friends = [
         ('L-function', ".")]  # self.lfunction_link)
#         ('Siegel modular form ' + self.newform_label, self.newform_link),
#         ('Modular form ' + self.newform_label, self.newform_link)]

        self.properties = [('Label', self.label),
                           ('Number of curves', str(self.ncurves)),
                           ('Conductor', '\(%s\)' % self.cond),
                           ]

        self.title = "Genus 2 Isogeny Class %s" % (self.label)
        self.downloads = [
                          ('Download Euler factors', ".")] # url_for(".download_g2c_eulerfactors", label=self.label)),
#                          ('Download stored data for all curves', url_for(".download_g2c_all", label=self.label))]
        
        self.bread = [
                       ('Genus 2 Curves', url_for(".index")),
                       ('$\Q$', url_for(".index_Q")),
                       ('%s' % self.cond, url_for(".by_conductor", conductor=self.cond)),
                       ('%s' % self.label, ' ')
                     ]

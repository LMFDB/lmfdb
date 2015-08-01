# -*- coding: utf-8 -*-
import re
import os
import pymongo
from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.genus2_curves.web_g2c import g2c_page, g2c_logger, list_to_min_eqn, end_alg_name, st_group_name, st0_group_name
from sage.all import QQ, PolynomialRing, factor,ZZ
from lmfdb.WebNumberField import field_pretty

logger = make_logger("g2c")

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves
    return g2cdb

def list_to_poly(s):
    return str(PolynomialRing(QQ, 'x')(s)).replace('*','')

def list_to_factored_poly(s):
    return str(factor(PolynomialRing(ZZ, 't')(s))).replace('*','')

def list_to_factored_poly_otherorder(s):
    if len(s) == 1:
        return str(s[0])
    sfacts = factor(PolynomialRing(ZZ, 'T')(s))
    sfacts_fc = [[v[0],v[1]] for v in sfacts]
    if sfacts.unit() == -1:
        sfacts_fc[0][0] *= -1
    outstr = ''
    for v in sfacts_fc:
        vcf = v[0].list()
        started = False
        if len(sfacts) > 1 or v[1] > 1:
            outstr += '('
        for i in range(len(vcf)):
            if vcf[i] <> 0:
                if started and vcf[i] > 0:
                    outstr += '+'
                started = True
                if i == 0:
                    outstr += str(vcf[i])
                else:
                    if abs(vcf[i]) <> 1:
                        outstr += str(vcf[i])
                    elif vcf[i] == -1:
                        outstr += '-'
                    if i == 1:
                        outstr += 'T'
                    elif i > 1:
                        outstr += 'T^{' + str(i) + '}'
        if len(sfacts) > 1 or v[1] > 1:
            outstr += ')'
        if v[1] > 1:
            outstr += '^{' + str(v[1]) + '}'        
    return outstr

def url_for_label(label):
    # returns the url for label
    L = label.split(".")
    return url_for(".by_full_label", conductor=L[0], iso_label=L[1], disc=L[2], number=L[3])

def isog_url_for_label(label):
    # returns the isogeny class url for curve label
    # TODO FIX: replace by full label line by approporiate
    L = label.split(".")
    return url_for(".by_double_iso_label", conductor=L[0], iso_label=L[1])

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
        curves_data = db_g2c().curves.find({"class" : self.label}).sort([("disc_key", pymongo.ASCENDING), ("label", pymongo.ASCENDING)])
        self.curves = [ {"label" : c['label'], "equation_formatted" : list_to_min_eqn(c['min_eqn']), "url": url_for_label(c['label'])} for c in curves_data ]
        self.ncurves = curves_data.count()
        self.bad_lfactors = [ [c[0], list_to_factored_poly_otherorder(c[1])] for c in self.bad_lfactors]
        for endalgtype in ['end_alg', 'rat_end_alg', 'real_end_alg', 'geom_end_alg', 'rat_geom_end_alg', 'real_geom_end_alg']:
            if hasattr(self, endalgtype):
                setattr(self,endalgtype + '_name',end_alg_name(getattr(self,endalgtype)))
            else:
                setattr(self,endalgtype + '_name','')

        self.st_group_name = st_group_name(self.st_group)
        self.st0_group_name = st0_group_name(self.st_group)

        if hasattr(self, 'geom_end_field') and self.geom_end_field <> '':
            self.geom_end_field_name = field_pretty(self.geom_end_field)
        else:
            self.geom_end_field_name = ''

        if self.is_gl2_type:
            self.is_gl2_type_name = 'yes'
            gl2_statement = 'of \(\GL_2\)-type'
        else:
            self.is_gl2_type_name = 'no'
            gl2_statement = 'not of \(\GL_2\)-type'
            
        if hasattr(self, 'is_simple') and hasattr(self, 'is_geom_simple'):
            if self.is_geom_simple:
                simple_statement = "simple over \(\overline{\Q}\), "
            elif self.is_simple:
                simple_statement = "simple over \(\Q\) but not simple over \(\overline{\Q}\), "
            else:
                simple_statement = "not simple over \(\Q\), "
        else:
            simple_statement = ""  # leave empty since not computed.
        self.endomorphism_statement = simple_statement + gl2_statement
            #if self.is_simple:
            #    self.is_simple_name = 'yes'
            #else:
            #    self.is_simple_name = 'no'
        #else:
         #   self.is_simple_name = '?'
        #if 
        #    if self.is_geom_simple:
        #        self.is_geom_simple_name = 'yes'
        #    else:
        #        self.is_geom_simple_name = 'no'
        #else:
        #    self.is_geom_simple_name = '?'

        x = self.label.split('.')[1]
        
        self.friends = [
          ('L-function', url_for("l_functions.l_function_genus2_page", cond=self.cond,x=x))
]

        self.ecproduct_wurl = []
        if hasattr(self, 'ecproduct'):
            for i in range(2):
                curve_label = self.ecproduct[i]
                crv_url = url_for("ec.by_ec_label", label=curve_label)
                if i == 1 or len(set(self.ecproduct)) <> 1:
                    self.friends.append(('Elliptic curve ' + curve_label, crv_url))
                self.ecproduct_wurl.append({'label' : curve_label, 'url' : crv_url})

        self.ecquadratic_wurl = []
        if hasattr(self, 'ecquadratic'):
            for i in range(len(self.ecquadratic)):
                curve_label = self.ecquadratic[i]
                crv_spl = curve_label.split('-')
                crv_url = url_for("ecnf.show_ecnf_isoclass", nf = crv_spl[0], conductor_label = crv_spl[1], class_label = crv_spl[2])
                self.friends.append(('Elliptic curve ' + curve_label, crv_url))
                self.ecquadratic_wurl.append({'label' : curve_label, 'url' : crv_url, 'nf' : crv_spl[0]})

        if hasattr(self, 'mfproduct'):
            for i in range(len(self.mfproduct)):
                mf_label = self.mfproduct[i]
                mf_spl = mf_label.split('.')
                mf_spl.append(mf_spl[2][-1])
                mf_spl[2] = mf_spl[2][:-1] # Need a splitting function
                mf_url = url_for("emf.render_elliptic_modular_forms", level=mf_spl[0], weight=mf_spl[1], character=mf_spl[2], label=mf_spl[3])
                self.friends.append(('Modular form ' + mf_label, mf_url))

        if hasattr(self, 'mfhilbert'):
            for i in range(len(self.mfhilbert)):
                mf_label = self.mfhilbert[i]
                mf_spl = mf_label.split('-')
                mf_url = url_for("hmf.render_hmf_webpage", field_label=mf_spl[0], label=mf_label)
                self.friends.append(('Hilbert modular form ' + mf_label, mf_url))

        self.properties = [('Label', self.label),
                           ('Number of curves', str(self.ncurves)),
                           ('Conductor','%s' % self.cond),
                           ('Sato-Tate group', '\(%s\)' % self.st_group_name),
                           ('\(\mathrm{End}(J_{\overline{\Q}}) \otimes \R\)','\(%s\)' % self.real_geom_end_alg_name),
                           ('\(\mathrm{GL}_2\)-type','%s' % self.is_gl2_type_name)]

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

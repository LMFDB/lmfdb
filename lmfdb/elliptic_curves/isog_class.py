# -*- coding: utf-8 -*-
import re
import tempfile
import os
from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.elliptic_curves import ec_page, ec_logger

import sage.all
from sage.all import EllipticCurve, latex, matrix

cremona_label_regex = re.compile(r'(\d+)([a-z]+)(\d*)')
lmfdb_label_regex = re.compile(r'(\d+)\.([a-z]+)(\d*)')
sw_label_regex = re.compile(r'sw(\d+)(\.)(\d+)(\.*)(\d*)')

logger = make_logger("ec")

ecdb = None

def db_ec():
    global ecdb
    if ecdb is None:
        ecdb = lmfdb.base.getDBConnection().elliptic_curves.curves
    return ecdb

class ECisog_class(object):
    """
    Class for an isogeny class of elliptic curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        logger.info("Constructing an instance of ECisog_class")
        self.__dict__.update(dbdata)
        self.make_class()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific elliptic curve isogeny class in the
        curves collection by its label, which can be either a curve
        label (e.g. "11.a1") or a class label (e.g. "11.a") in either
        LMFDB or Cremona format.
        """
        print "label = %s" % label
        try:
            N, iso, number = lmfdb_label_regex.match(label).groups()
            if number:
                data = db_ec().find_one({"lmfdb_label" : label})
            else:
                data = db_ec().find_one({"lmfdb_label" : label+"1"})
        except AttributeError:
            try:
                N, iso, number = cremona_label_regex.match(label).groups()
                if number:
                    data = db_ec().find_one({"label" : label})
                else:
                    data = db_ec().find_one({"label" : label+"1"})
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error

        if data:
            return ECisog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        self.ainvs_str = self.ainvs
        self.ainvs = [int(a) for a in self.ainvs_str]
        self.E = EllipticCurve(self.ainvs)

        # Sage's isogeny class function changed in version 6.2:
        ver = sage.version.version.split('.') # e.g. "6.1.beta2"
        ma = int(ver[0])
        mi = int(ver[1])
        if ma>6 or ma==6 and mi>1:
            # Code for Sage 6.2 and later:
            isogeny_class = self.E.isogeny_class()
            self.curves = isogeny_class.curves
            self.mat = isogeny_class.matrix()
            self.graph = isogeny_class.graph()
        else:
            # Code for Sage 6.1 and before:
            self.curves, self.mat = self.E.isogeny_class()
            self.graph = self.E.isogeny_graph()
        size = len(self.curves)

        # Create isogeny graph url:

        n = self.graph.num_verts()
        P = self.graph.plot(edge_labels=True, layout='spring')
        self.graph_img = encode_plot(P)

        # Create a list of the curves in the class from the database, so
        # they are in the correct order!

        self.db_curves = [self.E]
        self.optimal_flags = [False] * size
        self.degrees = [0] * size
        if self.degree:
            self.degrees[0] = self.degree
        else:
            try:
                self.degrees[0] = self.E.modular_degree()
            except RuntimeError:
                pass

        # Fill in the curves in the class by looking each one up in the db:

        self.cremona_labels = [self.label] + [0] * (size - 1)
        if self.number == 1:
            self.optimal_flags[0] = True
        for i in range(2, size + 1):
            Edata = db_ec().find_one({'lmfdb_label': self.lmfdb_iso + str(i)})
            Ei = EllipticCurve([int(a) for a in Edata['ainvs']])
            self.cremona_labels[i - 1] = Edata['label']
            if Edata['number'] == 1:
                self.optimal_flags[i - 1] = True
            if 'degree' in Edata:
                self.degrees[i - 1] = Edata['degree']
            else:
                try:
                    self.degrees[i - 1] = Ei.modular_degree()
                except RuntimeError:
                    pass
            self.db_curves.append(Ei)

        if self.iso == '990h':  # this isogeny class is labeled wrong in Cremona's tables
            self.optimal_flags = [False, False, True, False]

        # Now work out the permutation needed to match the two lists of curves:
        perm = [self.db_curves.index(Ei) for Ei in self.curves]
        # Apply the same permutation to the isogeny matrix:
        self.mat = [[self.mat[perm[i], perm[j]] for j in range(size)]
                                                for i in range(size)]

        self.isogeny_matrix = latex(matrix(self.mat))
        self.newform = web_latex(self.E.q_eigenform(10))
        self.curves = [[self.lmfdb_iso + str(i + 1), self.cremona_labels[i],
                        str(list(c.ainvs())), c.torsion_order(), self.degrees[i],
                        self.optimal_flags[i]]
                       for i, c in enumerate(self.db_curves)]


        N, iso, number = lmfdb_label_regex.match(self.lmfdb_iso).groups()
        self.friends = [
        ('L-function', url_for("l_functions.l_function_ec_page", label=self.lmfdb_iso)),
        ('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', label=self.lmfdb_iso)),
        ('Symmetric 4th power L-function', url_for("l_functions.l_function_ec_sym_page", power='4', label=self.lmfdb_iso)),
        ('Modular form ' + self.lmfdb_iso.replace('.', '.2'), url_for("emf.render_elliptic_modular_forms", level=N, weight=2, character=0, label=iso))]

        self.downloads = [('Download coeffients of q-expansion', url_for(".download_EC_qexp", label=self.lmfdb_iso, limit=100)),
                         ('Download stored data for curves in this class', url_for(".download_EC_all", label=self.lmfdb_iso))]

        if self.lmfdb_iso == self.iso:
            self.title = "Elliptic Curve Isogeny Class %s" % self.lmfdb_iso
        else:
            self.title = "Elliptic Curve Isogeny Class %s (Cremona label %s)" % (self.lmfdb_iso, self.iso)

        self.bread = [('Elliptic Curves ', url_for(".rational_elliptic_curves")), ('isogeny class %s' % self.lmfdb_iso, ' ')]

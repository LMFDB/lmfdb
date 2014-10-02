# -*- coding: utf-8 -*-
import re
import tempfile
import os
from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.elliptic_curves import ec_page, ec_logger
from lmfdb.elliptic_curves.isog_class import make_graph
from lmfdb.ecnf.WebEllipticCurve import ECNF

import sage.all
from sage.all import EllipticCurve, latex, matrix

logger = make_logger("ecnf")

ecdb = None

def db_ec():
    global ecdb
    if ecdb is None:
        ecdb = lmfdb.base.getDBConnection().elliptic_curves.nfcurves
    return ecdb

class ECNF_isoclass(object):
    """
    Class for an isogeny class of elliptic curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        logger.info("Constructing an instance of ECNF_isoclass")
        self.__dict__.update(dbdata)
        self.make_class()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific elliptic curve isogeny class in the
        curves collection by its label, which can be either a full
        curve label (including the field_label component) or a full
        class label.  In either case the data will be obtained from
        the curve in the database with number 1 in the class.
        """
        print "label = %s" % label
        try:
            if label[-1].isdigit():
                data = db_ec().find_one({"label" : label})
            else:
                data = db_ec().find_one({"label" : label+"1"})
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error

        if data:
            if 'isogeny_matrix' in data:
                return ECNF_isoclass(data)
            else:
                return "No isogeny matrix found" # caller must catch these
        return "Class not found"                 # and raise an error

    def make_class(self):
        self.ECNF = ECNF.by_label(self.label)

        # Extract the isogeny degree matrix from the database
        size = len(self.isogeny_matrix)
        from sage.matrix.all import Matrix
        self.isogeny_matrix = Matrix(self.isogeny_matrix)

        # Create isogeny graph:
        self.graph = make_graph(self.isogeny_matrix)
        P = self.graph.plot(edge_labels=True)
        self.graph_img = encode_plot(P)
        self.graph_link = '<img src="%s" width="200" height="150"/>' % self.graph_img
        self.isogeny_matrix_str = latex(matrix(self.isogeny_matrix))

        # Create a list of the curves in the class from the database
        self.db_curves = [self.ECNF] + [ECNF.by_label(self.class_label + str(i))
                                          for i in range(2, size + 1)]

        self.curves = [[c.short_label, c.latex_ainvs]
                       for i, c in enumerate(self.db_curves)]

        self.friends = []

        self.properties = [('Label', self.ECNF.label),
                           (None, self.graph_link),
                           ('Conductor', '%s' % self.ECNF.cond)
                           ]

        self.bread = [('Elliptic Curves ', url_for(".index")),
                      (self.ECNF.field_label, url_for('.show_ecnf1', nf=self.ECNF.field_label)),
                      ('isogeny class %s' % self.ECNF.short_label, ' ')]


def make_graph(M):
    """
    Code extracted from Sage's elliptic curve isogeny class (reshaped
    in the case maxdegree==12)
    """
    from sage.schemes.elliptic_curves.ell_curve_isogeny import fill_isogeny_matrix, unfill_isogeny_matrix
    from sage.graphs.graph import Graph
    n = M.nrows() # = M.ncols()
    G = Graph(unfill_isogeny_matrix(M), format='weighted_adjacency_matrix')
    MM = fill_isogeny_matrix(M)
    # The maximum degree classifies the shape of the isogeny
    # graph, though the number of vertices is often enough.
    # This only holds over Q, so this code will need to change
    # once other isogeny classes are implemented.
    if n == 1:
        # one vertex
        pass
    elif n == 2:
        # one edge, two vertices.  We align horizontally and put
        # the lower number on the left vertex.
        G.set_pos(pos={0:[-0.5,0],1:[0.5,0]})
    else:
        maxdegree = max(max(MM))
        if n == 3:
            # o--o--o
            centervert = [i for i in range(3) if max(MM.row(i)) < maxdegree][0]
            other = [i for i in range(3) if i != centervert]
            G.set_pos(pos={centervert:[0,0],other[0]:[-1,0],other[1]:[1,0]})
        elif maxdegree == 4:
            # o--o<8
            centervert = [i for i in range(4) if max(MM.row(i)) < maxdegree][0]
            other = [i for i in range(4) if i != centervert]
            G.set_pos(pos={centervert:[0,0],other[0]:[0,1],other[1]:[-0.8660254,-0.5],other[2]:[0.8660254,-0.5]})
        elif maxdegree == 27:
            # o--o--o--o
            centers = [i for i in range(4) if list(MM.row(i)).count(3) == 2]
            left = [j for j in range(4) if MM[centers[0],j] == 3 and j not in centers][0]
            right = [j for j in range(4) if MM[centers[1],j] == 3 and j not in centers][0]
            G.set_pos(pos={left:[-1.5,0],centers[0]:[-0.5,0],centers[1]:[0.5,0],right:[1.5,0]})
        elif n == 4:
            # square
            opp = [i for i in range(1,4) if not MM[0,i].is_prime()][0]
            other = [i for i in range(1,4) if i != opp]
            G.set_pos(pos={0:[1,1],other[0]:[-1,1],opp:[-1,-1],other[1]:[1,-1]})
        elif maxdegree == 8:
            # 8>o--o<8
            centers = [i for i in range(6) if list(MM.row(i)).count(2) == 3]
            left = [j for j in range(6) if MM[centers[0],j] == 2 and j not in centers]
            right = [j for j in range(6) if MM[centers[1],j] == 2 and j not in centers]
            G.set_pos(pos={centers[0]:[-0.5,0],left[0]:[-1,0.8660254],left[1]:[-1,-0.8660254],centers[1]:[0.5,0],right[0]:[1,0.8660254],right[1]:[1,-0.8660254]})
        elif maxdegree == 18:
            # two squares joined on an edge
            centers = [i for i in range(6) if list(MM.row(i)).count(3) == 2]
            top = [j for j in range(6) if MM[centers[0],j] == 3]
            bl = [j for j in range(6) if MM[top[0],j] == 2][0]
            br = [j for j in range(6) if MM[top[1],j] == 2][0]
            G.set_pos(pos={centers[0]:[0,0.5],centers[1]:[0,-0.5],top[0]:[-1,0.5],top[1]:[1,0.5],bl:[-1,-0.5],br:[1,-0.5]})
        elif maxdegree == 16:
            # tree from bottom, 3 regular except for the leaves.
            centers = [i for i in range(8) if list(MM.row(i)).count(2) == 3]
            center = [i for i in centers if len([j for j in centers if MM[i,j] == 2]) == 2][0]
            centers.remove(center)
            bottom = [j for j in range(8) if MM[center,j] == 2 and j not in centers][0]
            left = [j for j in range(8) if MM[centers[0],j] == 2 and j != center]
            right = [j for j in range(8) if MM[centers[1],j] == 2 and j != center]
            G.set_pos(pos={center:[0,0],bottom:[0,-1],centers[0]:[-0.8660254,0.5],centers[1]:[0.8660254,0.5],left[0]:[-0.8660254,1.5],right[0]:[0.8660254,1.5],left[1]:[-1.7320508,0],right[1]:[1.7320508,0]})
        elif maxdegree == 12:
            # tent
            centers = [i for i in range(8) if list(MM.row(i)).count(2) == 3]
            left = [j for j in range(8) if MM[centers[0],j] == 2]
            right = []
            for i in range(3):
                right.append([j for j in range(8) if MM[centers[1],j] == 2 and MM[left[i],j] == 3][0])
            G.set_pos(pos={centers[0]:[-0.3,0],centers[1]:[0.3,0],
                           left[0]:[-0.14,0.15], right[0]:[0.14,0.15],
                           left[1]:[-0.14,-0.15],right[1]:[0.14,-0.15],
                           left[2]:[-0.14,-0.3],right[2]:[0.14,-0.3]})

    G.relabel(range(1,n+1))
    return G

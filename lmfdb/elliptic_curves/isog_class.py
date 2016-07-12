# -*- coding: utf-8 -*-
from flask import url_for
import lmfdb.base
from lmfdb.utils import make_logger, web_latex, encode_plot
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label, split_cremona_label
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import newform_label, is_newform_in_db

from sage.all import EllipticCurve, latex, matrix

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
        logger.debug("Constructing an instance of ECisog_class")
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
        #print "label = %s" % label
        try:
            N, iso, number = split_lmfdb_label(label)
            if number:
                data = db_ec().find_one({"lmfdb_label" : label})
            else:
                data = db_ec().find_one({"lmfdb_label" : label+"1"})
        except AttributeError:
            try:
                N, iso, number = split_cremona_label(label)
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
        self.CM = self.E.has_cm()

        try:
            # Extract the isogeny degree matrix from the database
            size = len(self.isogeny_matrix)
            from sage.matrix.all import Matrix
            self.isogeny_matrix = Matrix(self.isogeny_matrix)
        except AttributeError:
            # Failsafe: construct it from scratch
            self.isogeny_matrix = self.E.isogeny_class(order="lmfdb").matrix()
            size = self.isogeny_matrix.nrows()
        self.ncurves = size

        # Create isogeny graph:
        self.graph = make_graph(self.isogeny_matrix)
        P = self.graph.plot(edge_labels=True)
        self.graph_img = encode_plot(P)
        self.graph_link = '<img src="%s" width="200" height="150"/>' % self.graph_img

        # Create a list of the curves in the class from the database
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

        self.isogeny_matrix_str = latex(matrix(self.isogeny_matrix))

        N, iso, number = split_lmfdb_label(self.lmfdb_iso)

        self.newform = web_latex(self.E.q_eigenform(10))
        self.newform_label = newform_label(N,2,1,iso)
        self.newform_link = url_for("emf.render_elliptic_modular_forms", level=N, weight=2, character=1, label=iso)
        self.newform_exists_in_db = is_newform_in_db(self.newform_label)

        self.lfunction_link = url_for("l_functions.l_function_ec_page", label=self.lmfdb_iso)

        self.curves = [dict([('label',self.lmfdb_iso + str(i + 1)),
                             ('url',url_for(".by_triple_label", conductor=N, iso_label=iso, number=i+1)),
                             ('cremona_label',self.cremona_labels[i]),
                             ('ainvs',str(list(c.ainvs()))),
                             ('torsion',c.torsion_order()),
                             ('degree',self.degrees[i]),
                             ('optimal',self.optimal_flags[i])])
                       for i, c in enumerate(self.db_curves)]

        self.friends =  [('L-function', self.lfunction_link)]
        if not self.CM:
            if int(N)<=300:
                self.friends += [('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', label=self.lmfdb_iso))]
            if int(N)<=50:
                self.friends += [('Symmetric cube L-function', url_for("l_functions.l_function_ec_sym_page", power='3', label=self.lmfdb_iso))]
        if self.newform_exists_in_db:
            self.friends +=  [('Modular form ' + self.newform_label, self.newform_link)]

        self.properties = [('Label', self.lmfdb_iso),
                           ('Number of curves', str(self.ncurves)),
                           ('Conductor', '\(%s\)' % N),
                           ('CM', '%s' % self.CM),
                           ('Rank', '\(%s\)' % self.rank),
                           ('Graph', ''),(None, self.graph_link)
                           ]


        self.downloads = [('Download coefficients of newform', url_for(".download_EC_qexp", label=self.lmfdb_iso, limit=1000)),
                         ('Download stored data for all curves', url_for(".download_EC_all", label=self.lmfdb_iso))]

        if self.lmfdb_iso == self.iso:
            self.title = "Elliptic Curve Isogeny Class %s" % self.lmfdb_iso
        else:
            self.title = "Elliptic Curve Isogeny Class %s (Cremona label %s)" % (self.lmfdb_iso, self.iso)

        self.bread = [('Elliptic Curves', url_for("ecnf.index")),
                      ('$\Q$', url_for(".rational_elliptic_curves")),
                      ('%s' % N, url_for(".by_conductor", conductor=N)),
                      ('%s' % iso, ' ')]
        self.code = {}
        self.code['show'] = {'sage':''} # use default show names
        self.code['class'] = {'sage':'E = EllipticCurve("%s1")\n'%(self.lmfdb_iso) + 'E.isogeny_class()\n'}
        self.code['curves'] = {'sage':'E.isogeny_class().curves'}
        self.code['rank'] = {'sage':'E.rank()'}
        self.code['q_eigenform'] = {'sage':'E.q_eigenform(10)'}
        self.code['matrix'] = {'sage':'E.isogeny_class().matrix()'}
        self.code['plot'] = {'sage':'E.isogeny_graph().plot(edge_labels=True)'}

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

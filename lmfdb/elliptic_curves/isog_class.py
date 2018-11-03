# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb.utils import web_latex, encode_plot
from lmfdb.elliptic_curves import ec_logger
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label, split_cremona_label
from lmfdb.db_backend import db

from sage.all import latex, matrix, PowerSeriesRing, QQ

class ECisog_class(object):
    """
    Class for an isogeny class of elliptic curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        ec_logger.debug("Constructing an instance of ECisog_class")
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
        try:
            N, iso, number = split_lmfdb_label(label)
            if number:
                label = ".".join([N,iso])
            data = db.ec_curves.lucky({"lmfdb_iso" : label, 'number':1})
        except AttributeError:
            try:
                N, iso, number = split_cremona_label(label)
                if number:
                    label = "".join([N,iso])
                data = db.ec_curves.lucky({"iso" : label, 'number':1})
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error

        if data:
            return ECisog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        self.CM = self.cm
        N, iso, number = split_lmfdb_label(self.lmfdb_iso)

        # Extract the size of the isogeny class from the database
        ncurves = self.class_size
        # Create a list of the curves in the class from the database
        self.curves = [db.ec_curves.lucky({'iso':self.iso, 'lmfdb_number': i+1})
                          for i in range(ncurves)]

        # Set optimality flags.  The optimal curve is number 1 except
        # in one case which is labeled differently in the Cremona tables
        for c in self.curves:
            c['optimal'] = (c['number']==(3 if self.label == '990h' else 1))
            c['ai'] = c['ainvs']
            c['url'] = url_for(".by_triple_label", conductor=N, iso_label=iso, number=c['lmfdb_number'])

        from sage.matrix.all import Matrix
        self.isogeny_matrix = Matrix(self.isogeny_matrix)
        self.isogeny_matrix_str = latex(matrix(self.isogeny_matrix))

        # Create isogeny graph:
        self.graph = make_graph(self.isogeny_matrix)
        P = self.graph.plot(edge_labels=True)
        self.graph_img = encode_plot(P)
        self.graph_link = '<img src="%s" width="200" height="150"/>' % self.graph_img


        self.newform =  web_latex(PowerSeriesRing(QQ, 'q')(self.anlist, 20, check=True))
        self.newform_label = db.mf_newforms.lucky({'level':N, 'weight':2, 'related_objects':{'$contains':'EllipticCurve/Q/%s/%s' % (N, iso)}},'label')
        self.newform_exists_in_db = self.newform_label is not None
        if self.newform_label is not None:
            char_orbit, hecke_orbit = self.newform_label.split('.')[2:]
            self.newform_link = url_for("cmf.by_url_newform_label", level=N, weight=2, char_orbit_label=char_orbit, hecke_orbit=hecke_orbit)

        self.lfunction_link = url_for("l_functions.l_function_ec_page", conductor_label = N, isogeny_class_label = iso)

        self.friends =  [('L-function', self.lfunction_link)]
        if not self.CM:
            self.CM = "no"
            if int(N)<=300:
                self.friends += [('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', conductor = N, isogeny = iso))]
            if int(N)<=50:
                self.friends += [('Symmetric cube L-function', url_for("l_functions.l_function_ec_sym_page", power='3', conductor = N, isogeny = iso))]
        if self.newform_exists_in_db:
            self.friends +=  [('Modular form ' + self.newform_label, self.newform_link)]

        self.properties = [('Label', self.lmfdb_iso),
                           ('Number of curves', str(ncurves)),
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

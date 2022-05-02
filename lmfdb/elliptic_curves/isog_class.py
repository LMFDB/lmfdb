# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb.utils import encode_plot, prop_int_pretty, raw_typeset, integer_squarefree_part
from lmfdb.elliptic_curves import ec_logger
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label, split_cremona_label, OPTIMALITY_BOUND, CREMONA_BOUND
from lmfdb.number_fields.web_number_field import field_pretty
from lmfdb import db

from sage.all import latex, PowerSeriesRing, QQ, ZZ, RealField

class ECisog_class():
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
                return "Invalid label"
            data = db.ec_curvedata.lucky({"lmfdb_iso": label, 'lmfdb_number':1})
            if data is None:
                return "Class not found"
            data['label_type'] = 'LMFDB'
            data['iso_label'] = iso
            data['class_label'] = label
        except AttributeError:
            try:
                N, iso, number = split_cremona_label(label)
                if number:
                    label = "".join([N,iso])
                data = db.ec_curvedata.lucky({"Ciso": label, 'Cnumber':1})
                data['label_type'] = 'Cremona'
                data['iso_label'] = iso
                data['class_label'] = label
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error

        if data:
            return ECisog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        # Extract the size of the isogeny class from the database
        classdata = db.ec_classdata.lucky({'lmfdb_iso': self.lmfdb_iso})
        self.class_size = ncurves = classdata['class_size']

        # Create a list of the curves in the class from the database
        number_key = 'Cnumber' if self.label_type=='Cremona' else 'lmfdb_number'
        self.curves = [db.ec_curvedata.lucky({'lmfdb_iso':self.lmfdb_iso, number_key: i+1})
                          for i in range(ncurves)]

        # Set optimality flags.  The optimal curve is conditionally
        # number 1 except in one case which is labeled differently in
        # the Cremona tables.  We know which curve is optimal iff the
        # optimality code for curve #1 is 1 (except for class 990h).

        # Note that self is actually an elliptic curve, with number=1.

        # The code here allows us to update the display correctly by
        # changing one line in this file (defining OPTIMALITY_BOUND)
        # without changing the data.

        self.cremona_bound    = CREMONA_BOUND
        self.optimality_bound = OPTIMALITY_BOUND
        self.optimality_known = (self.conductor < OPTIMALITY_BOUND) or ((self.conductor < CREMONA_BOUND) and ((self.optimality==1) or (self.Ciso=='990h')))
        self.optimal_label = self.Clabel if self.label_type == 'Cremona' else self.lmfdb_label

        if self.conductor < OPTIMALITY_BOUND:
            for c in self.curves:
                c['optimal'] = (c['Cnumber'] == (3 if self.Ciso=='990h' else 1))
                c['optimality_known'] = True
        elif self.conductor < CREMONA_BOUND:
            for c in self.curves:
                c['optimal'] = (c['optimality']>0) # this curve possibly optimal
                c['optimality_known'] = (c['optimality']==1) # this curve certainly optimal
        else:
            for c in self.curves:
                c['optimal'] = None
                c['optimality_known'] = False
        for c in self.curves:
            c['ai'] = c['ainvs']
            c['curve_url_lmfdb'] = url_for(".by_ec_label", label=c['lmfdb_label'])
            c['curve_url_cremona'] = url_for(".by_ec_label", label=c['Clabel']) if self.conductor < CREMONA_BOUND else "N/A"
            if self.label_type == 'Cremona':
                c['curve_label'] = c['Clabel']
                _, c_iso, c_number = split_cremona_label(c['Clabel'])
            else:
                c['curve_label'] = c['lmfdb_label']
                _, c_iso, c_number = split_lmfdb_label(c['lmfdb_label'])
            c['short_label'] = "{}{}".format(c_iso,c_number)
            c['FH'] = RealField(20)(c['faltings_height'])
            c['j_inv'] = QQ(tuple(c['jinv'])) # convert [num,den] to rational for display
            c['disc'] = c['signD'] * c['absD']

        from sage.matrix.all import Matrix
        M = classdata['isogeny_matrix']

        # permute rows/cols to match labelling: the rows/cols in the
        # ec_classdata table are with respect to LMFDB ordering.
        if self.label_type == 'Cremona':
            perm = lambda i: next(c for c in self.curves if c['Cnumber']==i+1)['lmfdb_number']-1
            M = [[M[perm(i)][perm(j)] for i in range(ncurves)] for j in range(ncurves)]

        M = Matrix(M)

        self.isogeny_matrix_str = latex(M)

        # Create isogeny graph with appropriate vertex labels:

        self.graph = make_graph(M, [c['short_label'] for c in self.curves])
        P = self.graph.plot(edge_labels=True, vertex_size=1000)
        self.graph_img = encode_plot(P)
        self.graph_link = '<img src="%s" width="200" height="150"/>' % self.graph_img


        self.newform =  raw_typeset(PowerSeriesRing(QQ, 'q')(classdata['anlist'], 20, check=True))
        self.newform_label = ".".join([str(self.conductor), str(2), 'a', self.iso_label])
        self.newform_exists_in_db = db.mf_newforms.label_exists(self.newform_label)
        if self.newform_exists_in_db:
            char_orbit, hecke_orbit = self.newform_label.split('.')[2:]
            self.newform_link = url_for("cmf.by_url_newform_label", level=self.conductor, weight=2, char_orbit_label=char_orbit, hecke_orbit=hecke_orbit)

        self.lfunction_link = url_for("l_functions.l_function_ec_page", conductor_label = self.conductor, isogeny_class_label = self.iso_label)

        self.friends =  [('L-function', self.lfunction_link)]

        if self.cm:
            # set CM field for Properties box.
            D = integer_squarefree_part(ZZ(self.cm))
            coeffs = [(1-D)//4,-1,1] if D%4==1 else [-D,0,1]
            lab = db.nf_fields.lucky({'coeffs': coeffs}, projection='label')
            self.CMfield = field_pretty(lab)
        else:
            self.CMfield = "no"
            if self.conductor <= 300:
                self.friends += [('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', conductor = self.conductor, isogeny = self.iso_label))]
            if self.conductor <= 50:
                self.friends += [('Symmetric cube L-function', url_for("l_functions.l_function_ec_sym_page", power='3', conductor = self.conductor, isogeny = self.iso_label))]
        if self.newform_exists_in_db:
            self.friends +=  [('Modular form ' + self.newform_label, self.newform_link)]

        if self.label_type == 'Cremona':
            self.title = "Elliptic curve isogeny class with Cremona label {} (LMFDB label {})".format(self.Ciso, self.lmfdb_iso)
        elif self.conductor < CREMONA_BOUND:
            self.title = "Elliptic curve isogeny class with LMFDB label {} (Cremona label {})".format(self.lmfdb_iso, self.Ciso)
        else:
            self.title = "Elliptic curve isogeny class with LMFDB label {}".format(self.lmfdb_iso)

        self.properties = [('Label', self.Ciso if self.label_type=='Cremona' else self.lmfdb_iso),
                           ('Number of curves', prop_int_pretty(ncurves)),
                           ('Conductor', prop_int_pretty(self.conductor)),
                           ('CM', '%s' % self.CMfield),
                           ('Rank', prop_int_pretty(self.rank))
                           ]
        if ncurves>1:
            self.properties += [('Graph', ''),(None, self.graph_link)]

        self.downloads = [('q-expansion to text', url_for(".download_EC_qexp", label=self.iso_label, limit=1000)),
                         ('All stored data to text', url_for(".download_EC_all", label=self.iso_label))]


        self.bread = [('Elliptic curves', url_for("ecnf.index")),
                      (r'$\Q$', url_for(".rational_elliptic_curves")),
                      ('%s' % self.conductor, url_for(".by_conductor", conductor=self.conductor)),
                      ('%s' % self.iso_label, ' ')]
        self.code = {}
        self.code['show'] = {'sage':''} # use default show names
        self.code['class'] = {'sage':'E = EllipticCurve("%s1")\n'%(self.iso_label) + 'E.isogeny_class()\n'}
        self.code['curves'] = {'sage':'E.isogeny_class().curves'}
        self.code['rank'] = {'sage':'E.rank()'}
        self.code['q_eigenform'] = {'sage':'E.q_eigenform(10)'}
        self.code['matrix'] = {'sage':'E.isogeny_class().matrix()'}
        self.code['plot'] = {'sage':'E.isogeny_graph().plot(edge_labels=True)'}

def make_graph(M, vertex_labels=None):
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


    if vertex_labels:
        G.relabel(vertex_labels)
    else:
        G.relabel(list(range(1, n + 1)))
    return G

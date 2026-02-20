from flask import url_for
from lmfdb.utils import make_graph, setup_isogeny_graph, prop_int_pretty, raw_typeset, integer_squarefree_part, list_to_factored_poly_otherorder
from lmfdb.elliptic_curves import ec_logger
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label, split_cremona_label, OPTIMALITY_BOUND, CREMONA_BOUND
from lmfdb.number_fields.web_number_field import field_pretty
from lmfdb.lfunctions.Lfunctionutilities import Lfactor_to_label, AbvarExists
from lmfdb.abvar.fq.main import url_for_label
from lmfdb import db

from sage.all import latex, PowerSeriesRing, QQ, ZZ, RealField, nth_prime


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
        number_key = 'Cnumber' if self.label_type == 'Cremona' else 'lmfdb_number'
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

        self.cremona_bound = CREMONA_BOUND
        self.optimality_bound = OPTIMALITY_BOUND
        self.optimality_known = (self.conductor < OPTIMALITY_BOUND) or ((self.conductor < CREMONA_BOUND) and ((self.optimality == 1) or (self.Ciso == '990h')))
        self.optimal_label = self.Clabel if self.label_type == 'Cremona' else self.lmfdb_label

        if self.conductor < OPTIMALITY_BOUND:
            for c in self.curves:
                c['optimal'] = (c['Cnumber'] == (3 if self.Ciso == '990h' else 1))
                c['optimality_known'] = True
        elif self.conductor < CREMONA_BOUND:
            for c in self.curves:
                c['optimal'] = (c['optimality'] > 0) # this curve possibly optimal
                c['optimality_known'] = (c['optimality'] == 1) # this curve certainly optimal
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
            def perm(i): return next(c for c in self.curves if c['Cnumber'] == i+1)['lmfdb_number']-1
            M = [[M[perm(i)][perm(j)] for i in range(ncurves)] for j in range(ncurves)]

        M = Matrix(M)

        self.isogeny_matrix_str = latex(M)

        # Create isogeny graph with appropriate vertex labels:

        self.graph = make_graph(M, [c['short_label'] for c in self.curves])
        self.graph_data, self.graph_link, self.graph_layouts, self.graph_default_layout = setup_isogeny_graph(self.graph)
        # Attach curve metadata to nodes for tooltip display
        curve_by_label = {c['short_label']: c for c in self.curves}
        for el in self.graph_data:
            if el['group'] == 'nodes':
                label = el['data']['label']
                c = curve_by_label.get(label)
                if c:
                    el['data']['url'] = c['curve_url_lmfdb']
                    el['data']['torsion'] = ' x '.join('Z/%dZ' % t for t in c['torsion_structure']) if c['torsion_structure'] else 'Trivial'
                    el['data']['degree'] = c['degree']
                    el['data']['faltings_height'] = str(c['FH'])
                    el['data']['optimal'] = bool(c.get('optimal'))
                    el['data']['j_inv'] = str(c['j_inv'])

        self.newform = raw_typeset(PowerSeriesRing(QQ, 'q')(classdata['anlist'], 20, check=True))
        self.newform_label = ".".join([str(self.conductor), str(2), 'a', self.iso_label])
        self.newform_exists_in_db = db.mf_newforms.label_exists(self.newform_label)
        if self.newform_exists_in_db:
            char_orbit, hecke_orbit = self.newform_label.split('.')[2:]
            self.newform_link = url_for("cmf.by_url_newform_label", level=self.conductor, weight=2, char_orbit_label=char_orbit, hecke_orbit=hecke_orbit)

        self.lfunction_link = url_for("l_functions.l_function_ec_page", conductor_label=self.conductor, isogeny_class_label=self.iso_label)

        self.friends = [('L-function', self.lfunction_link)]

        if self.cm:
            # set CM field for Properties box.
            D = integer_squarefree_part(ZZ(self.cm))
            coeffs = [(1-D)//4,-1,1] if D % 4 == 1 else [-D,0,1]
            lab = db.nf_fields.lucky({'coeffs': coeffs}, projection='label')
            self.CMfield = field_pretty(lab)
        else:
            self.CMfield = "no"
            #if self.conductor <= 300:
            #    self.friends += [('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', conductor=self.conductor, isogeny=self.iso_label))]
            #if self.conductor <= 50:
            #    self.friends += [('Symmetric cube L-function', url_for("l_functions.l_function_ec_sym_page", power='3', conductor=self.conductor, isogeny=self.iso_label))]
        if self.newform_exists_in_db:
            self.friends += [('Modular form ' + self.newform_label, self.newform_link)]

        if self.label_type == 'Cremona':
            self.title = "Elliptic curve isogeny class with Cremona label {} (LMFDB label {})".format(self.Ciso, self.lmfdb_iso)
        elif self.conductor < CREMONA_BOUND:
            self.title = "Elliptic curve isogeny class with LMFDB label {} (Cremona label {})".format(self.lmfdb_iso, self.Ciso)
        else:
            self.title = "Elliptic curve isogeny class with LMFDB label {}".format(self.lmfdb_iso)

        self.properties = [('Label', self.Ciso if self.label_type == 'Cremona' else self.lmfdb_iso),
                           ('Number of curves', prop_int_pretty(ncurves)),
                           ('Conductor', prop_int_pretty(self.conductor)),
                           ('CM', '%s' % self.CMfield),
                           ('Rank', prop_int_pretty(self.rank))
                           ]
        self.properties += [('Graph', ''), (None, self.graph_link)]

        self.downloads = [('q-expansion to text', url_for(".download_EC_qexp", label=self.lmfdb_iso, limit=1000)),
                          ('All stored data to text', url_for(".download_EC_all", label=self.lmfdb_iso)),
                          ('Underlying data', url_for(".EC_data", label=self.lmfdb_iso))]

        self.bread = [('Elliptic curves', url_for("ecnf.index")),
                      (r'$\Q$', url_for(".rational_elliptic_curves")),
                      ('%s' % self.conductor, url_for(".by_conductor", conductor=self.conductor)),
                      ('%s' % self.iso_label, ' ')]
        self.code = {}
        self.code['show'] = {'sage':''} # use default show names
        self.code['class'] = {'sage':'E = EllipticCurve(%s)\n' % (self.ainvs) + 'E.isogeny_class()\n'}
        self.code['curves'] = {'sage':'E.isogeny_class().curves'}
        self.code['rank'] = {'sage':'E.rank()'}
        self.code['q_eigenform'] = {'sage':'E.q_eigenform(10)'}
        self.code['matrix'] = {'sage':'E.isogeny_class().matrix()'}
        self.code['plot'] = {'sage':'E.isogeny_graph().plot(edge_labels=True)'}

        lfunc_url = self.lfunction_link
        origin_url = lfunc_url.lstrip('/L/').rstrip('/')
        self.lfunc_label = db.lfunc_instances.lucky({'url':origin_url}, "label")
        if self.lfunc_label:
            self.lfunc_entry = db.lfunc_search.lookup(self.lfunc_label)
            if self.lfunc_entry:
                self.has_lfunction = True
                self.euler_factors = self.lfunc_entry["euler_factors"]
                self.good_lfactors = [[nth_prime(n+1), self.euler_factors[n]] for n in range(len(self.euler_factors)) if nth_prime(n+1) < 30 and self.conductor % nth_prime(n+1)]
                self.good_lfactors_pretty_with_label = [(c[0], list_to_factored_poly_otherorder(c[1]), (Lfactor_to_label(c[1])), url_for_label(Lfactor_to_label(c[1])) if AbvarExists(1,c[0]) else '') for c in self.good_lfactors]
                self.bad_lfactors = db.lfunc_lfunctions.lucky({"label": self.lfunc_label})["bad_lfactors"]
                self.bad_lfactors_pretty = [(c[0], list_to_factored_poly_otherorder(c[1])) for c in self.bad_lfactors]
            else:
                self.has_lfunction = False
        else:
            self.has_lfunction = False


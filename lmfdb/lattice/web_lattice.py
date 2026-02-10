
from collections import defaultdict
from lmfdb import db
from flask import url_for
from sage.all import lazy_attribute, matrix, ZZ, sqrt, round, Graph, latex, Factorization, PolynomialRing
from lmfdb.utils import WebObj, raw_typeset_qexp, prop_int_pretty, encode_plot, pos_int_and_factor
from lmfdb.groups.abstract.web_groups import abelian_gp_display, abstract_group_display_knowl

#####################################
# Utilitary functions for displays  #
#####################################

def vect_to_matrix(v):
    """
    Converts a list of vectors of ints into a latex-formatted string which renders a latex pmatrix, ready for display
    """
    return str(latex(matrix(v)))

def vect_to_sym(v):
    """
    Converts an upper triangular vector of ints, to a full 2d list of ints
    """
    n = ZZ(round(sqrt(len(v))))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(n):
            M[i, j] = v[k]
            k += 1
    return [[int(M[i, j]) for i in range(n)] for j in range(n)]

def vect_to_sym2(v):
    """
    Converts a list of n^2 ints, to a 2D n x n array
    """
    n = ZZ(round(sqrt(len(v))))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(n):
            M[i, j] = v[k]
            k += 1
    return [[int(M[i, j]) for i in range(n)] for j in range(n)]

def format_conway_symbol(s):
    # Format Conway symbol so Roman numerals appear as text (upright) in LaTeX
    return "$" + s.replace('II_', r'\text{II}_').replace('I_', r'\text{I}_') + "$"

class WebLat(WebObj):
    def _mathwrap(self, fac, nofac):
        for col in fac + nofac:
            val = getattr(self, col, None)
            dcol = col + "_display"
            if val is None:
                setattr(self, dcol, "not computed")
            elif col in fac:
                setattr(self, dcol, pos_int_and_factor(val))
            else:
                setattr(self, dcol, f"${val}$")

    @lazy_attribute
    def nminus(self):
        return self.rank - self.nplus

    @lazy_attribute
    def signature(self):
        return (self.nplus, self.nminus)

    @lazy_attribute
    def is_positive_definite(self):
        return self.nminus == 0

    @lazy_attribute
    def conway_display(self):
        return format_conway_symbol(self.conway_symbol)

    @lazy_attribute
    def dual_conway_display(self):
        return format_conway_symbol(self.dual_conway_symbol)

    @lazy_attribute
    def even_odd(self):
        return "Even" if self.is_even else "Odd"

    @lazy_attribute
    def discriminant_group_display(self):
        if self.discriminant_group_invs is None:
            return "not computed"
        # TODO: this should be a knowl
        return "$" + abelian_gp_display(self.discriminant_group_invs) + "$"

    @lazy_attribute
    def discriminant_gram_display(self):
        if self.discriminant_form is None:
            return "not computed"
        return "$" + vect_to_matrix(vect_to_sym2(self.discriminant_form)) + "$"

    @lazy_attribute
    def properties(self):
        return [
            ('Label', self.label),
            ('Rank', prop_int_pretty(self.rank)),
            ('Signature', f'${self.signature}$'),
            ('Determinant', prop_int_pretty(self.det)),
            ('Discriminant', prop_int_pretty(self.disc)),
            ('Level', prop_int_pretty(self.level)),
            ('Class Number', f'${self.class_number}$'),
            ('Parity', f'{self.even_odd}'),
        ]

    # TODO: Switch this to using code snippets
    #info['download_gram'] = [
    #(i, url_for(".render_genus_webpage_download", label=info['label'], lang=i, obj='gram')) for i in ['gp', 'magma', 'sage']]

class WebGenus(WebLat):
    table = db.lat_genera

    def __init__(self, label, data=None):
        super().__init__(label, data)
        self._mathwrap(["det", "disc", "level"], ["class_number"])
        X = self.adjacency_display

    @lazy_attribute
    def gram_display(self):
        if self.rep is None:
            return "not computed"
        return f"${vect_to_matrix(vect_to_sym2(self.rep))}$"

    @lazy_attribute
    def mass_display(self):
        if self.mass is None:
            return "not computed"
        a, b = self.mass
        if b == 1:
            return f"${a}$"
        return f"${a}/{b}$"

    @lazy_attribute
    def adjacency_display(self):
        display = defaultdict(dict)
        R = PolynomialRing(ZZ, "x")
        for p, M in self.adjacency_matrix.items():
            adj_mat = matrix(ZZ, self.class_number, self.class_number, M)
            display[p]["matrix"] = f"${latex(adj_mat)}$"
            G = Graph(adj_mat, format='weighted_adjacency_matrix') # can also do format='adjacency_matrix'
            # TODO: improve layout
            img = encode_plot(G.plot(), transparent=True)
            display[p]["graph_link"] = f'<img src="{img}" width="400" height="300"/>'
            F = Factorization([(R(f), e) for f,e in self.adjacency_polynomials[p]])
            display[p]["poly"] = f"${latex(F)}$"
        return display

    @lazy_attribute
    def start_p(self):
        ps = sorted(self.adjacency_matrix)
        if ps:
            for p in ps:
                if any(c != 0 for c in self.adjacency_matrix[p]):
                    return p
            return ps[0]

    @lazy_attribute
    def lattices_stored(self):
        return db.lat_lattices_new.exists({"genus_label": self.label})

    @lazy_attribute
    def friends(self):
        # Should add things like modular forms spaces
        return []

    @lazy_attribute
    def downloads(self):
        return [("Underlying data", url_for(".genus_data", label=self.label))]

class WebLattice(WebLat):
    table = db.lat_lattices_new

    def __init__(self, label, data=None):
        super().__init__(label, data)
        self._mathwrap(["det", "dual_det", "disc", "level", "aut_size"], ["density", "dual_density", "hermite", "dual_hermite", "minimum", "kissing", "festi_veniani", "class_number"])

    @lazy_attribute
    def dual_display(self):
        if self.dual_label is None:
            return "not in database"
        return f'<a href="{url_for(".render_lattice_webpage", label=self.dual_label)}">{self.dual_label}</a>'

    @lazy_attribute
    def aut_display(self):
        return abstract_group_display_knowl(self.aut_label)

    @lazy_attribute
    def genus(self):
        return WebGenus(self.genus_label)

    @lazy_attribute
    def gram_display(self):
        if self.gram is None:
            return "not computed"
        return f"${vect_to_matrix(vect_to_sym2(self.gram))}$"

    @lazy_attribute
    def theta_display(self):
        if self.theta_series:
            return raw_typeset_qexp(self.theta_series)
        return "not computed"

    @lazy_attribute
    def dual_theta_display(self):
        if self.dual_theta_series:
            return raw_typeset_qexp(self.dual_theta_series)
        return "not computed"

    @lazy_attribute
    def friends(self):
        return [("Genus of this lattice", f"/Lattice/Genus/{self.genus_label}")]

    @lazy_attribute
    def downloads(self):
        return [("Underlying data", url_for(".lattice_data", label=self.label))]


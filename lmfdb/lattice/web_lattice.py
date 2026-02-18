
import os
import yaml
from collections import defaultdict
from lmfdb import db
from flask import url_for
from sage.all import lazy_attribute, matrix, ZZ, sqrt, round, Graph, latex, Factorization, PolynomialRing, flatten
from lmfdb.utils import WebObj, raw_typeset_qexp, prop_int_pretty, encode_plot, pos_int_and_factor, raw_typeset_poly_factor, raw_typeset_matrix
from lmfdb.groups.abstract.web_groups import abelian_gp_display, abstract_group_display_knowl

#####################################
# Utilitary functions for displays  #
#####################################

def vect_to_matrix(v, **kwargs):
    """
    Converts a list of vectors of ints into a latex-formatted string which renders a latex pmatrix, ready for display
    """
    return raw_typeset_matrix(matrix(v), **kwargs)

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
        return vect_to_matrix(vect_to_sym2(self.discriminant_form))

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

    def _mat_in(self, mat, lang):
        if lang == "pari":
            return "[" + ";".join(",".join(str(c) for c in row) for row in mat) + "]"
        return str(flatten(mat)).replace(" ", "")

    # TODO: Switch this to using code snippets
    #info['download_gram'] = [
    #(i, url_for(".render_genus_webpage_download", label=info['label'], lang=i, obj='gram')) for i in ['gp', 'magma', 'sage']]

class WebGenus(WebLat):
    table = db.lat_genera

    def __init__(self, label, data=None):
        super().__init__(label, data)
        self._mathwrap(["det", "disc", "level"], ["class_number"])
        if self.adjacency_matrix is None:
            self.adjacency_matrix = {}
        if self.adjacency_polynomials is None:
            self.adjacency_polynomials = {}
        X = self.adjacency_display

    @lazy_attribute
    def gram_display(self):
        if self.rep is None:
            return "not computed"
        return vect_to_matrix(vect_to_sym2(self.rep))

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
            display[p]["matrix"] = raw_typeset_matrix(adj_mat)
            G = Graph(adj_mat, format='weighted_adjacency_matrix') # can also do format='adjacency_matrix'
            # TODO: improve layout
            img = encode_plot(G.plot(), transparent=True)
            display[p]["graph_link"] = f'<img src="{img}" width="400" height="300"/>'
            F = [(R(f), e) for f,e in self.adjacency_polynomials[p]]
            display[p]["poly"] = raw_typeset_poly_factor(F)
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
        downloads = []
        for lang in [("Magma", "magma"), ("Oscar", "oscar"), ("PariGP", "pari"), ("SageMath", "sage")]:
            downloads.append(('{} commands'.format(lang[0]), url_for(".genus_code_download", label=self.label, download_type=lang[1])))
        downloads.append(("Underlying data", url_for(".genus_data", label=self.label)))
        return downloads

   
    @lazy_attribute
    def code(self):
        # read in code.yaml from lattice directory:
        _curdir = os.path.dirname(os.path.abspath(__file__))
        code = yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)

        # Get a representative gram matrix
        if self.rep is not None:
            gram = self.rep
        elif self.canonical_gram is not None:
            gram = self.canonical_gram
        elif self.gram is not None and len(self.gram) > 0:
            gram = self.gram[0] if isinstance(self.gram[0], list) else self.gram
        else:
            gram = None

        code["genus_definition"] = dict()
        if gram is not None:
            for lang, s in code["lattice_definition"].items():
                if lang != "comment":
                    code["genus_definition"][lang] = s.format(n=self.rank, gram=self._mat_in(vect_to_sym2(gram), lang))
                    if code["genus"][lang] is not None:
                        code["genus_definition"][lang] += "\n"+code["genus"][lang]
        else:
            for lang in code["lattice_definition"]:
                if lang != "comment":
                    code["genus_definition"][lang] = code["not-implemented"][lang]
        code["genus_definition"]["comment"] = "Define a representative lattice in the genus"
        code['show'] = {lang: '' for lang in code['prompt']}
        return code


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
        gram = self.canonical_gram if self.canonical_gram is not None else self.gram[0] if self.gram is not None and len(self.gram) > 0 else None
        if gram is None:
            return "not computed"
        return vect_to_matrix(vect_to_sym2(gram))

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
    def quadratic_form_display(self):
        """
        Return a latex-formatted quadratic form associated to the Gram matrix of this lattice.
        If rank at most 7, uses variables x, y, z, t, u, v, w
        Otherwise uses variables x_1, x_2, x_3, etc.
        """

        gram = self.canonical_gram if self.canonical_gram is not None else self.gram[0] if self.gram is not None and len(self.gram) > 0 else None
        gram = vect_to_sym2(gram)

        default_vars = ["x", "y", "z", "t", "u", "v", "w"]
        if self.rank <= len(default_vars):
            var_names = default_vars[:self.rank]
        else:
            var_names = [f"x_{{{i+1}}}" for i in range(self.rank)]
    
        terms = []
    
        # Diagonal terms
        for i in range(self.rank):
            coeff = gram[i][i]//2 if self.is_even else gram[i][i]
            if coeff != 0:
                var = var_names[i]
                if coeff == 1:
                    terms.append(f"{var}^2")
                elif coeff == -1:
                    terms.append(f"-{var}^2")
                else:
                    terms.append(f"{coeff}{var}^2")
    
        # Off-diagonal terms
        for i in range(self.rank):
            for j in range(i+1, self.rank):
                coeff = gram[i][j] if self.is_even else 2*gram[i][j]
                if coeff != 0:
                    vi, vj = var_names[i], var_names[j]
                    if coeff == 1:
                        terms.append(f"{vi}{vj}")
                    elif coeff == -1:
                        terms.append(f"-{vi}{vj}")
                    else:
                        terms.append(f"{coeff}{vi}{vj}")
    
        result = " + ".join(terms)
        result = result.replace("+ -", "- ")
        return "$"+result+"$"

    @lazy_attribute
    def friends(self):
        return [("Genus of this lattice", f"/Lattice/Genus/{self.genus_label}")]

    @lazy_attribute
    def downloads(self):
        downloads = []
        for lang in [("Magma", "magma"), ("Oscar", "oscar"), ("PariGP", "pari"), ("SageMath", "sage")]:
            downloads.append(('{} commands'.format(lang[0]), url_for(".lattice_code_download", label=self.label, download_type=lang[1])))
        downloads.append(("Underlying data", url_for(".lattice_data", label=self.label)))
        return downloads

    @lazy_attribute
    def code(self):
        # read in code.yaml from lattice directory:
        _curdir = os.path.dirname(os.path.abspath(__file__))
        code = yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)
        if self.canonical_gram is not None:
            gram = self.canonical_gram
        elif self.gram is not None and len(self.gram) > 0:
            gram = self.gram[0] if isinstance(self.gram[0], list) else self.gram
        else:
            gram = None
        if gram is not None:
            for lang, s in code["lattice_definition"].items():
                if lang != "comment":
                    code["lattice_definition"][lang] = s.format(n=self.rank, gram=self._mat_in(vect_to_sym2(gram), lang))
        else:
            for lang in code["lattice_definition"]:
                if lang != "comment":
                    code["lattice_definition"][lang] = code["not-implemented"][lang]
        code['show'] = {lang: '' for lang in code['prompt']}
        return code

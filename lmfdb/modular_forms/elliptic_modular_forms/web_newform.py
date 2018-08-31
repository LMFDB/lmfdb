# See genus2_curves/web_g2c.py
# See templates/newform.html for how functions are called

from sage.all import prime_range, latex, PolynomialRing, QQ, PowerSeriesRing
from lmfdb.db_backend import db
from lmfdb.WebNumberField import nf_display_knowl
from lmfdb.number_fields.number_field import field_pretty
from flask import url_for
from lmfdb.utils import coeff_to_poly, coeff_to_power_series, web_latex, web_latex_split_on_pm
from lmfdb.characters.utils import url_character
import re
from sage.databases.cremona import cremona_letter_code, class_to_int
from web_space import convert_spacelabel_from_conrey

LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[a-z]+\.[a-z]+$")
def valid_label(label):
    return bool(LABEL_RE.match(label))


def convert_newformlabel_from_conrey(newformlabel_conrey):
    """
    Returns the label for the newform using the orbit index
    eg:
        N.k.c.x --> N.k.i.x
    return None if N.k.i is not on the db
    """
    N, k, chi, x = newformlabel_conrey.split('.')
    newspace_label = convert_spacelabel_from_conrey('.'.join([N,k,chi]))
    if newspace_label is not None:
        return newspace_label + '.' + x
    else:
        return None

def newform_conrey_exists(newformlabel_conrey):
    return db.mf_newforms.label_exists(convert_newformlabel_from_conrey(newformlabel_conrey))

def eigs_as_seqseq_to_qexp(eigseq):
    # Takes a sequence of sequence of integers and returns a string for the corresponding q expansion
    # For example, eigs_as_seqseq_to_qexp([[0,0],[1,3]]) returns "\((1+3\beta_{1})q\)\(+O(q^2)\)"
    prec = len(eigseq)
    if prec == 0:
        return 'O(1)'
    d = len(eigseq[0])
    R = PolynomialRing(QQ, ['beta%s' % i for i in range(1,d)])
    Rgens = [1] + [g for g in R.gens()]
    Rq = PowerSeriesRing(R, 'q')
    q = Rq.gens()[0]
    s = ''
    for j in range(prec):
        term = sum([Rgens[i]*eigseq[j][i] for i in range(d)])
        if term != 0:
             latexterm = latex(term*(q**j))
             if s <> '' and latexterm[0] <> '-':
                  latexterm = '+' + latexterm
             s += '\(' + latexterm + '\)'
    return s + '\(+O(q^{%s})\)' % prec

class WebNewform(object):
    def __init__(self, data, space=None):
        #TODO validate data
        # Need to set level, weight, character, num_characters, degree, has_exact_qexp, has_complex_qexp, hecke_index, is_twist_minimal
        self.__dict__.update(data)
        self._data = data
        self.char_orbit_code = cremona_letter_code(self.char_orbit - 1)

        if space is None:
            # Need character info from spaces table
            chardata = db.mf_newspaces.lookup(self.space_label,['conrey_labels','cyc_degree'])
            self.__dict__.update(chardata)
        else:
            self.conrey_labels, self.cyc_degree = space.conrey_labels, space.cyc_degree
        eigenvals = db.mf_hecke_nf.search({'hecke_orbit_code':self.hecke_orbit_code}, ['n','an'], sort=['n'])
        if eigenvals:  # this will always be true
            self.has_exact_qexp = True
            zero = [0] * self.dim
            self.qexp = [zero]
            for i, ev in enumerate(eigenvals):
                if ev['n'] != i+1:
                    raise ValueError("Missing eigenvalue")
                if not ev.get('an'):
                    # only had traces
                    self.has_exact_qexp = False
                    break
                self.qexp.append(ev['an'])
            self.qexp_prec = len(self.qexp)-1
        else:
            self.has_exact_qexp = False
#        angles = db.mf_hecke_cc.search({'orbit':self.orbit_code}, ['embedding','angles'], sort=[])
#        self.angles = {data['embedding']:data['angles'] for data in angles}

        self.char_conrey = db.mf_newspaces.lookup(self.space_label, 'conrey_labels')[0]
                     # label is the distinguished column in mf_newspaces,
                     # and the space label is called "label" in mf_newspaces
        self.char_conrey_str = '\chi_{%s}(%s,\cdot)' % (self.level, self.char_conrey)
        self.char_conrey_link = url_character(type='Dirichlet', modulus=self.level, number=self.char_conrey)
        self.inner_twist = [(chi,url_character(type='Dirichlet', modulus=self.level, number=chi)) for chi in self.inner_twist]
        self.char_orbit_label = "\(" + str(self.level) + "\)." + self.char_orbit_code

        self.properties = [('Label', self.label),
                           ('Weight', '%s' % self.weight),
                           ('Character Orbit', '%s' % self.char_orbit),
                           ('Representative Character', '\(%s\)' % self.char_conrey_str),
                           ('Dimension', '%s' % self.dim)]
        if self.__dict__.get('is_CM'):
            self.properties += [('CM', '%s' % self.is_CM)] # properties box

        # Breadcrumbs
        self.bread = bread = [
             ('Classical newforms', url_for(".index")),
             ('%s' % self.level, url_for(".by_url_level", level=self.level)),
             ('%s' % self.weight, url_for(".by_url_full_gammma1_space_label", level=self.level, weight=self.weight)),
             ('%s' % self.char_orbit_code, url_for(".by_url_space_label", level=self.level, weight=self.weight, char_orbit=self.char_orbit_code)),
             ('%s' % cremona_letter_code(self.hecke_orbit - 1), url_for(".by_url_newform_label", level=self.level, weight=self.weight, char_orbit=self.char_orbit_code, hecke_orbit=cremona_letter_code(self.hecke_orbit - 1))),
             ]

        self.title = "Newform %s"%(self.label)
        #self.friends += [ ('Newspace {}'.format(sum(self.label.split('.')[:-1])),self.newspace_url)]

    @property
    def friends(self):
        res = []
        base_label =  map(str, [self.level, self.weight])
        hecke_letter = cremona_letter_code(self.hecke_orbit - 1)
        i = 0
        for i, character in enumerate(self.conrey_labels):
            for j in range(self.dim/self.cyc_degree):
                label = base_label + [str(character), hecke_letter, str(j + 1)]
                lfun_label = '.'.join(label)
                lfun_url =  "/L/ModularForm/GL2/Q/holomorphic/" + '/'.join(label)
                res.append(('L-function ' + lfun_label, lfun_url))
        return res

    @staticmethod
    def by_label(label):
        if not valid_label(label):
            raise ValueError("Invalid newform label %s." % label)
        data = db.mf_newforms.lookup(label)
        if data is None:
            raise ValueError("Newform %s not found" % label)
        return WebNewform(data)

    def field_display(self):
        # display the coefficient field
        label = self.__dict__.get("nf_label")
        if label is None:
            return r"\(\Q(\nu)\)"
        elif label == u'1.1.1.1':  # rationals, special case
            return nf_display_knowl(self.nf_label, name=r"\(\Q\)")
        else:
            return r"\(\Q(\nu)\) = " + self.field_knowl()

    def cm_field_knowl(self):
        # The knowl for the CM field, with appropriate title
        if self.cm_disc == 0:
            raise ValueError("Not CM")
        cm_label = "2.0.%s.1"%(-self.cm_disc)
        return nf_display_knowl(cm_label, field_pretty(cm_label))

    def field_knowl(self):
        label = self.__dict__.get("nf_label")
        if label:
            return nf_display_knowl(label, field_pretty(label))
        else:
            return "Not in LMFDB"

    def defining_polynomial(self):
        if self.__dict__.get('field_poly'):
            return r"\( %s \)"%(coeff_to_poly(self.field_poly)._latex_())
        return None

    def order_basis(self):
        # display the Hecke order, defining the variables used in the exact q-expansion display
        numerators = [coeff_to_poly(num, 'nu')._latex_() for num in self.hecke_ring_numerators]
        basis = [num if den == 1 else r"\frac{%s}{%s}"%(num, den) for num, den in zip(numerators, self.hecke_ring_denominators)]
        return ", ".join(r"\(\beta_{%s} = %s\)"%(i, x) for i, x in enumerate(basis))

    def q_expansion(self, format, prec_max=10):
        # options for format: 'oneline', 'short', 'all'
        # Display the q-expansion.  If all is False, truncate to a low precision (e.g. 10).  Will be inside \( \).
        # For now we ignore the format and just print on one line
        if self.has_exact_qexp:
            if format == 'all':
               prec = self.qexp_prec
            else:
               prec = min(self.qexp_prec, prec_max)
            zero = [0] * self.dim
            if self.dim == 1:
                s = web_latex_split_on_pm(web_latex(coeff_to_power_series([self.qexp[n][0] for n in range(prec+1)],prec=prec),enclose=False))
            else:
                s = eigs_as_seqseq_to_qexp(self.qexp[:prec])
            return s
        else:
            return coeff_to_power_series([0,1], prec=2)._latex_()

    def conrey_from_embedding(self, m):
        # Given an embedding number, return the Conrey label for the restriction of that embedding to the cyclotomic field
        return self.conrey_labels[(m-1) // self.cyc_degree]

    def embedding(self, m, n=None, prec=6, format='embed'):
        """
        Return the value of the ``m``th embedding on a specified input.

        INPUT:

        - ``m`` -- an integer, specifying which embedding to use.
        - ``n`` -- an integer, specifying which a_n.  If None, returns the image of
            the generator of the field (i.e. the root corresponding to this embedding).
        - ``prec`` -- the precision to display floating point values
        - ``format`` -- either ``embed`` or ``analytic_embed``.  In the second case, divide by n^((k-1)/2).
        """
        pass

    def satake(self, m, p, prec=6, format='satake'):
        """
        Return a Satake parameter.

        INPUT:

        - ``m`` -- an integer, specifying which embedding to use.
        - ``p`` -- a prime, specifying which a_p.
        - ``prec`` -- the precision to display floating point values
        - ``format`` -- either ``satake`` or ``satake_angle``.  In the second case, give the argument of the Satake parameter
        """
        pass

    def embed_range(self, a, b, format='embed'):
        if format in ['embed', 'analytic_embed']:
            return range(a, b)
        else:
            return prime_range(a, b)

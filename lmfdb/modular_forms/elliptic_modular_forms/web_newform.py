# See genus2_curves/web_g2c.py
# See templates/newform.html for how functions are called

from sage.all import prime_range
from lmfdb.db_backend import db
from lmfdb.WebNumberField import nf_display_knowl
from lmfdb.utils import coeff_to_poly

class WebNewform(object):
    def __init__(self, data):
        # Need to set level, weight, character, num_characters, degree, has_exact_qexp, has_complex_qexp, hecke_index, is_twist_minimal
        self.__dict__.update(data)
        eigenvals = db.mf_hecke_nf.search({'orbit':self.orbit_code}, ['n','an'], sort=['n'])
        if eigenvals:
            self.has_exact_qexp = True
            self.qexp = [0,1] # so that qexp[n] lines up
            for i, ev in enumerate(eigenvals):
                if ev['n'] != i+2:
                    raise ValueError("Missing eigenvalue")
                self.qexp.append(ev['an'])
        else:
            self.has_exact_qexp = False
        angles = db.mf_hecke_cc.search({'orbit':self.orbit_code}, ['embedding','angles'], sort=[])

    @staticmethod
    def by_label(label):
        return WebNewform(db.mf_newforms.lookup(label))

    def field_display(self):
        # display the coefficient field
        if self.nf_label is None:
            return r"\(\Q(w)\)"
        else:
            return nf_display_knowl(self.nf_label, name=r"\(\Q(w)\)")

    def defining_polynomial(self):
        return r"\( %s \)"%(coeff_to_poly(self.field_poly)._latex_())

    def order_basis(self):
        # display the Hecke order, defining the variables used in the exact q-expansion display
        numerators = [coeff_to_poly(num, 'w')._latex_() for num in self.hecke_ring_numerators]
        basis = [num if den == 1 else r"\frac{%s}{%s}"%(num, den) for num, den in zip(self.hecke_ring_numerators, self.hecke_ring_denominators)]
        return ", ".join(r"\(\beta_%s = %s\)"%(i+1, x) for i, x in enumerate(basis))

    def q_expansion(self, format):
        # options for format: oneline, short, all
        # Display the q-expansion.  If all is False, truncate to a low precision (e.g. 10).  Will be inside \( \).
        # For now we ignore the format and just print on one line
        if self.has_exact_qexp:
            prec = self.qexp_prec if all else min(self.qexp_prec, 10)
            s = r"q \)"
            zero = [0] * self.dim
            for n in range(2,prec):
                term = self.qexp[n]
                if term != zero:
                    coeff = " + ".join(r"%s \beta_{%s}"%(c,i+1) for i,c in enumerate(term) if c != 0)
                    s += r" + \((%s) q^{%s}\)"%(coeff, n)
            s += r" + \(O(q^{%s})"%(self.qexp_prec)
            return s
        else:
            return coeff_to_power_series([0,1], prec=2)._latex_()

    def conrey_from_embedding(self, m):
        # Given an embedding number, return the Conrey label for the restriction of that embedding to the cyclotomic field
        pass

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

    def cm_field_knowl(self):
        # The knowl for the CM field, with appropriate title
        pass

    def atkinlehner_data(self):
        # A list of triples (Q, c, ev).  I'm not sure what these are exactly...
        pass

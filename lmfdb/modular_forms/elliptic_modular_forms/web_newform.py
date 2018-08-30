# See genus2_curves/web_g2c.py
# See templates/newform.html for how functions are called

from sage.all import prime_range
from lmfdb.db_backend import db
from lmfdb.WebNumberField import nf_display_knowl
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.utils import coeff_to_poly, coeff_to_power_series, web_latex
import re
LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.[a-z]+$") # not putting in o currently
def valid_label(label):
    return bool(LABEL_RE.match(label))

class WebNewform(object):
    def __init__(self, data, space=None):
        # Need to set level, weight, character, num_characters, degree, has_exact_qexp, has_complex_qexp, hecke_index, is_twist_minimal
        self.__dict__.update(data)

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

        self.properties = [('Label', self.label), 
                           ('Weight', '%s' % self.weight),
                           ('Character Orbit', '%s' % self.char_orbit),
                           ('Representative Character', '\(%s\)' % self.char_conrey_str),
                           ('Dimension', '%s' % self.dim)]
        if self.__dict__.get('is_CM'):
            self.properties += [('CM', '%s' % self.is_CM)] # properties box
        
        self.bread = [] # bread
        self.title = "Newform %s"%(self.label)
        self.friends = []

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
            return r"\(\Q(w)\)"
        elif label == u'1.1.1.1':  # rationals, special case
            return nf_display_knowl(label, name=r"\(\Q\)")
        else:
            return nf_display_knowl(label, name=r"\(\Q(w)\)")

    def defining_polynomial(self):
        return r"\( %s \)"%(coeff_to_poly(self.field_poly)._latex_())

    def order_basis(self):
        # display the Hecke order, defining the variables used in the exact q-expansion display
        numerators = [coeff_to_poly(num, 'w')._latex_() for num in self.hecke_ring_numerators]
        basis = [num if den == 1 else r"\frac{%s}{%s}"%(num, den) for num, den in zip(self.hecke_ring_numerators, self.hecke_ring_denominators)]
        return ", ".join(r"\(\beta_%s = %s\)"%(i+1, x) for i, x in enumerate(basis))

    def q_expansion(self, format):
        # options for format: 'oneline', 'short', 'all'
        # Display the q-expansion.  If all is False, truncate to a low precision (e.g. 10).  Will be inside \( \).
        # For now we ignore the format and just print on one line
        if self.has_exact_qexp:
            if format == 'all':
               prec = self.qexp_prec 
            else:
               prec = min(self.qexp_prec, 10)
            zero = [0] * self.dim
            if self.dim == 1:
                s = web_latex(coeff_to_power_series([self.qexp[n][0] for n in range(prec+1)],prec=prec),enclose=True)
            else:
                s = r"q \)"
                for n in range(2,prec):
                    term = self.qexp[n]
                    if term != zero:
                        coeff = " + ".join(r"%s \beta_{%s}"%(c,i+1) for i,c in enumerate(term) if c != 0)
                        s += r" + \((%s) q^{%s}\)"%(coeff, n)
                s += r" + \(O(q^{%s})"%(self.qexp_prec)
                s.replace('\beta_{1}','')
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

    def cm_field_knowl(self):
        # The knowl for the CM field, with appropriate title
        if self.cm_disc == 0:
            raise ValueError("Not CM")
        cm_label = "2.0.%s.1"%(-self.cm_disc)
        return nf_display_knowl(cm_label, field_pretty(cm_label))

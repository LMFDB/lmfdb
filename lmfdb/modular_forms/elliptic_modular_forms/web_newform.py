# See genus2_curves/web_g2c.py
# See templates/newform.html for how functions are called

from sage.all import prime_range, latex, PolynomialRing, QQ, PowerSeriesRing, CDF, ZZ
from lmfdb.db_backend import db
from lmfdb.WebNumberField import nf_display_knowl, cyclolookup
from lmfdb.number_fields.number_field import field_pretty
from flask import url_for
from lmfdb.utils import coeff_to_poly, coeff_to_power_series, web_latex, web_latex_split_on_pm
from lmfdb.characters.utils import url_character
import re
from collections import defaultdict
from sage.databases.cremona import cremona_letter_code, class_to_int
from web_space import convert_spacelabel_from_conrey
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey

LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[a-z]+\.[a-z]+$")
def valid_label(label):
    return bool(LABEL_RE.match(label))
EPLUS_RE = re.compile(r"e\+0*([1-9][0-9]*)")
EMINUS_RE = re.compile(r"e\-0*([1-9][0-9]*)")

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
        if eigenvals:  # this should always be true
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
        cc_data = list(db.mf_hecke_cc.search({'hecke_orbit_code':self.hecke_orbit_code},
                                             projection=['embedding','an','angles'],
                                             sort=['embedding']))
        if cc_data:
            self.has_complex_qexp = True
            self.cqexp_prec = 10000
        else:
            self.has_complex_qexp = False
        self.cc_data = []
        self.rel_dim = self.dim // self.cyc_degree
        for m, embedded_mf in enumerate(cc_data):
            embedded_mf['conrey_label'] = self.conrey_labels[m // self.rel_dim]
            embedded_mf['embedding_num'] = (m % self.rel_dim) + 1
            embedded_mf['real'] = all(z[1] == 0 for z in embedded_mf['an'])
            embedded_mf['angles'] = {p:theta for p,theta in embedded_mf['angles']}
            self.cc_data.append(embedded_mf)
            self.cqexp_prec = min(self.cqexp_prec, len(embedded_mf['an']))
        if cc_data:
            self.analytic_shift = [None]
            for n in range(1,self.cqexp_prec):
                self.analytic_shift.append(float(n)**((1-ZZ(self.weight))/2))

        self.character_values = defaultdict(list)
        G = DirichletGroup_conrey(self.level)
        chars = [DirichletCharacter_conrey(G, char) for char in self.conrey_labels]
        for p in prime_range(2, self.cqexp_prec):
            if p.divides(self.level):
                continue
            for chi in chars:
                c = chi.logvalue(p) * self.char_order
        #for p, L in self.char_values:
        #    for c in L:
                angle = float(c / self.char_order)
                value = CDF(0,2*CDF.pi()*angle).exp()
                self.character_values[p].append((angle, value))

        self.char_conrey = db.mf_newspaces.lookup(self.space_label, 'conrey_labels')[0]
                     # label is the distinguished column in mf_newspaces,
                     # and the space label is called "label" in mf_newspaces
        self.char_conrey_str = '\chi_{%s}(%s,\cdot)' % (self.level, self.char_conrey)
        self.char_conrey_link = url_character(type='Dirichlet', modulus=self.level, number=self.char_conrey)
        self.inner_twist = [(chi,url_character(type='Dirichlet', modulus=self.level, number=chi)) for chi in self.inner_twist]
        self.char_orbit_label = "\(" + str(self.level) + "\)." + self.char_orbit_code

        # properties box
        self.properties = [('Label', self.label),
                           ('Weight', '%s' % self.weight),
                           ('Character Orbit', '%s' % self.char_orbit_code),
                           ('Representative Character', '\(%s\)' % self.char_conrey_str),
                           ('Dimension', '%s' % self.dim)]
        if self.is_cm:
            self.properties += [('CM discriminant', '%s' % self.cm_disc)]
        else:
            self.properties += [('CM', 'No')]

        # Breadcrumbs
        self.bread = bread = [
             ('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Classical newforms', url_for(".index")),
             ('Level %s' % self.level, url_for(".by_url_level", level=self.level)),
             ('Weight %s' % self.weight, url_for(".by_url_full_gammma1_space_label", level=self.level, weight=self.weight)),
             ('Character orbit %s' % self.char_orbit_code, url_for(".by_url_space_label", level=self.level, weight=self.weight, char_orbit=self.char_orbit_code)),
             ('Hecke orbit %s' % cremona_letter_code(self.hecke_orbit - 1), url_for(".by_url_newform_label", level=self.level, weight=self.weight, char_orbit=self.char_orbit_code, hecke_orbit=cremona_letter_code(self.hecke_orbit - 1))),
             ]

        self.title = "Newform %s"%(self.label)
        #self.friends += [ ('Newspace {}'.format(sum(self.label.split('.')[:-1])),self.newspace_url)]

    @property
    def friends(self):
        res = []
        base_label = [str(self.level)]
        #if self.weight == 2 and self.dim == 1:
        #    label = base_label + [self.isogeny_class_label]
        #    ec_label = '.'.join(label)
        #    ec_url = '/EllipticCurve/Q/' + '/'.join(label)
        #    res.append(('Elliptic curve isogeny class ' + ec_label, ec_url))
        base_label.append(str(self.weight))
        cmf_base = '/ModularForm/GL2/Q/holomorphic/'
        base_label =  map(str, [self.level, self.weight])
        ns1_label = '.'.join(base_label)
        ns1_url = cmf_base + '/'.join(base_label)
        res.append(('Newspace ' + ns1_label, ns1_url))
        char_letter = cremona_letter_code(self.char_orbit - 1)
        ns_label = '.'.join(base_label + [char_letter])
        ns_url = cmf_base + '/'.join(base_label + [char_letter])
        res.append(('Newspace ' + ns_label, ns_url))
        hecke_letter = cremona_letter_code(self.hecke_orbit - 1)
        for character in self.conrey_labels:
            for j in range(self.dim/self.cyc_degree):
                label = base_label + [str(character), hecke_letter, str(j + 1)]
                lfun_label = '.'.join(label)
                lfun_url =  '/L' + cmf_base + '/'.join(label)
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
        if self.rel_dim == 1:
            return self.cyc_display()
        label = self.__dict__.get("nf_label")
        if label:
            return nf_display_knowl(label, field_pretty(label))
        else:
            return "Not in LMFDB"

    def cyc_display(self):
        if self.cyc_degree == 1:
            name = r'\(\Q\)'
        else:
            name = r'\(\Q(\zeta_{%s})\)' % self.char_order
        if self.cyc_degree < 24:
            return nf_display_knowl(cyclolookup[self.char_order], name=name)
        else:
            return name

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

    def embed_header(self, n, format='embed'):
        if format == 'embed':
            return 'a_{%s}'%n
        elif format == 'analytic_embed':
            if self.weight == 1:
                return 'a_{%s}' % n
            elif self.weight == 3:
                return 'a_{%s}/%s' % (n, n)
            else:
                return r'\frac{a_{%s}}{%s^{%s}}'%(n, n, (ZZ(self.weight)-1)/2)
        elif format == 'satake':
            return r'\alpha_{%s}' % n
        else:
            return r'\theta_{%s}' % n

    def conrey_from_embedding(self, m):
        # Given an embedding number, return the Conrey label for the restriction of that embedding to the cyclotomic field
        return "{c}.{e}".format(c=self.cc_data[m]['conrey_label'], e=(m%self.rel_dim)+1)

    @staticmethod
    def _display_float(x, prec):
        if abs(x) < 10**(-prec):
            return "0"
        s = "%.{}f".format(prec) % float(x)
        s = EPLUS_RE.sub(r" \cdot 10^{\1}", s)
        s = EMINUS_RE.sub(r" \cdot 10^{-\1}", s)
        return s

    def _display_complex(self, x, y, prec):
        if abs(y) < 10**(-prec):
            return self._display_float(x, prec)
        if abs(x) < 10**(-prec):
            return self._display_float(y, prec) + "i"
        x = self._display_float(x, prec)
        if y < 0:
            sign = " - "
            y = -y
        else:
            sign = " + "
        y = self._display_float(y, prec)
        return x + sign + y + r"i"

    def embedding(self, m, n=None, prec=6, format='embed'):
        """
        Return the value of the ``m``th embedding on a specified input.

        INPUT:

        - ``m`` -- an integer, specifying which embedding to use.
        - ``n`` -- a positive integer, specifying which a_n.  If None, returns the image of
            the generator of the field (i.e. the root corresponding to this embedding).
        - ``prec`` -- the precision to display floating point values
        - ``format`` -- either ``embed`` or ``analytic_embed``.  In the second case, divide by n^((k-1)/2).
        """
        if n is None:
            return '?' # FIXME
        x, y = self.cc_data[m]['an'][n]
        if format == 'analytic_embed':
            x *= self.analytic_shift[n]
            y *= self.analytic_shift[n]
        if self.cc_data[m]['real']:
            return self._display_float(x, prec)
        else:
            return self._display_complex(x, y, prec)

    def satake(self, m, p, i, prec=6, format='satake'):
        """
        Return a Satake parameter.

        INPUT:

        - ``m`` -- an integer, specifying which embedding to use.
        - ``p`` -- a prime, specifying which a_p.
        - ``i`` -- either 0 or 1, indicating which root of the quadratic.
        - ``prec`` -- the precision to display floating point values
        - ``format`` -- either ``satake`` or ``satake_angle``.  In the second case, give the argument of the Satake parameter
        """
        theta = self.cc_data[m]['angles'][p]
        chiang, chival = self.character_values[p][m // self.rel_dim]
        if format == 'satake':
            ppow = CDF(p)**((ZZ(self.weight)-1)/2)
            unit = CDF(0,2*CDF.pi()*theta).exp()
            if i == 0:
                alpha = ppow * unit
            else:
                alpha = ppow * chival / unit
            return self._display_complex(alpha.real(), alpha.imag(), prec)
        else:
            if i == 1:
                theta = chiang - theta
                if theta > 0.5:
                    theta -= 1
                elif theta <= -0.5:
                    theta += 1
            s = self._display_float(2*theta, prec)
            if s != "0":
                s += r'\pi'
            return s

    def an_range(self, L, format='embed'):
        if format in ['embed', 'analytic_embed']:
            return [n for n in L if n >= 2 and n < self.cqexp_prec]
        else:
            return [p for p in L if p >= 2 and p < self.cqexp_prec and ZZ(p).is_prime() and not ZZ(p).divides(self.level)]

    def m_range(self, L):
        return [m-1 for m in L if m >= 1 and m <= self.dim]

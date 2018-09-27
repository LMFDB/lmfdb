# See genus2_curves/web_g2c.py
# See templates/newform.html for how functions are called

from sage.all import complex_plot, exp, prime_range, latex, PolynomialRing, QQ, PowerSeriesRing, CDF, Infinity, ZZ
from lmfdb.db_backend import db
from lmfdb.WebNumberField import nf_display_knowl, cyclolookup
from lmfdb.number_fields.number_field import field_pretty
from flask import url_for
from lmfdb.utils import coeff_to_poly, coeff_to_power_series, encode_plot, web_latex, web_latex_split_on_pm, web_latex_bigint_poly, bigint_knowl, display_float, display_complex
from lmfdb.characters.utils import url_character
import re
from collections import defaultdict
from sage.databases.cremona import cremona_letter_code, class_to_int
from web_space import convert_spacelabel_from_conrey, get_bread
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey

LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[a-z]+\.[a-z]+$")
def valid_label(label):
    return bool(LABEL_RE.match(label))
EPLUS_RE = re.compile(r"e\+0*([1-9][0-9]*)")
EMINUS_RE = re.compile(r"e\-0*([1-9][0-9]*)")

def decode_hecke_orbit(code):
    level = str(code % 2**24)
    weight = str((code >> 24) % 2**12)
    char_orbit_label = cremona_letter_code((code >> 36) % 2**16)
    hecke_orbit_label = cremona_letter_code(code >> 52)
    return '.'.join([level, weight, char_orbit_label, hecke_orbit_label])
def encode_hecke_orbit(label):
    level, weight, char_orbit_label, hecke_orbit_label = label.split('.')
    level = int(level)
    weight = int(weight)
    char_orbit = class_to_int(char_orbit_label)
    hecke_orbit = class_to_int(hecke_orbit_label)
    return level + (weight << 24) + (char_orbit << 36) + (hecke_orbit << 52)

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

        if self.level == 1 or ZZ(self.level).is_prime():
            self.factored_level = ''
        else:
            self.factored_level = ' = ' + ZZ(self.level).factor()._latex_()

        if self.has_inner_twist != 0:
            if self.inner_twist_proved:
                if len(self.inner_twist == 1):
                    self.star_twist = 'inner twist'
                else:
                    self.star_twist = 'inner twists'
            elif len(self.inner_twist) == 1:
                self.star_twist = 'inner twist*'
            else:
                self.star_twist = 'inner twists*'

        eigenvals = db.mf_hecke_nf.search({'hecke_orbit_code':self.hecke_orbit_code}, ['n','an','trace_an'], sort=['n'])
        if eigenvals:  # this should always be true
            self.has_exact_qexp = True
            zero = [0] * self.dim
            self.qexp = [zero]
            self.texp = [0]
            for i, ev in enumerate(eigenvals):
                if ev['n'] != i+1:
                    raise ValueError("Missing eigenvalue")
                self.texp.append(ev['trace_an'])
                if ev.get('an'):
                    self.qexp.append(ev['an'])
                else:
                    # only had traces
                    self.has_exact_qexp = False
            self.qexp_prec = len(self.qexp)-1
            self.texp_prec = len(self.texp)-1
        else:
            self.has_exact_qexp = False
        self.character_values = defaultdict(list)
        cc_data = list(db.mf_hecke_cc.search({'hecke_orbit_code':self.hecke_orbit_code},
                                             projection=['embedding_index','an','angles','embedding_root_real','embedding_root_imag'],
                                             sort=['embedding_index']))
        self.rel_dim = self.dim // self.char_degree
        if not cc_data:
            self.has_complex_qexp = False
        else:
            self.has_complex_qexp = True
            self.cqexp_prec = 10000
            self.cc_data = []
            for m, embedded_mf in enumerate(cc_data):
                embedded_mf['conrey_label'] = self.char_labels[m // self.rel_dim]
                embedded_mf['embedding_num'] = (m % self.rel_dim) + 1
                embedded_mf['real'] = all(z[1] == 0 for z in embedded_mf['an'])
                embedded_mf['angles'] = {p:theta for p,theta in embedded_mf['angles']}

                self.cc_data.append(embedded_mf)
                self.cqexp_prec = min(self.cqexp_prec, len(embedded_mf['an']))
            self.analytic_shift = [None]
            for n in range(1,self.cqexp_prec):
                self.analytic_shift.append(float(n)**((1-ZZ(self.weight))/2))


            G = DirichletGroup_conrey(self.level)
            chars = [DirichletCharacter_conrey(G, char) for char in self.char_labels]
            for p in prime_range(2, self.cqexp_prec):
                if p.divides(self.level):
                    continue
                for chi in chars:
                    c = chi.logvalue(p) * self.char_order
                    angle = float(c / self.char_order)
                    value = CDF(0,2*CDF.pi()*angle).exp()
                    self.character_values[p].append((angle, value))

        self.char_conrey = self.char_labels[0]
        self.char_conrey_str = '\chi_{%s}(%s,\cdot)' % (self.level, self.char_conrey)
        self.char_conrey_link = url_character(type='Dirichlet', modulus=self.level, number=self.char_conrey)
        if self.has_inner_twist:
            self.inner_twist = [(chi,url_character(type='Dirichlet', modulus=self.level, number=chi)) for chi in self.inner_twist]
        self.character_label = "\(" + str(self.level) + "\)." + self.char_orbit_label

        self.has_further_properties = (self.is_cm != 0 or self.__dict__.get('is_twist_minimal') or self.has_inner_twist != 0 or self.char_orbit_index == 1 and self.level != 1)

        # properties box
        self.properties = [('Label', self.label)]
        if cc_data:
            self.properties += [(None, '<a href="{0}"><img src="{0}" width="200" height="200"/></a>'.format(self.plot))]

        self.properties += [('Level', str(self.level)),
                            ('Weight', str(self.weight)),
                            ('Analytic Conductor', str(self.Nk2)),
                            ('Character orbit label', '%s.%s' % (self.level, self.char_orbit_label)),
                            ('Representative character', '\(%s\)' % self.char_conrey_str),
                            ('Dimension', str(self.dim))]
        if self.is_cm == 1:
            self.properties += [('CM discriminant', str(self.__dict__.get('cm_disc')))]
        elif self.is_cm == -1:
            self.properties += [('CM', 'No')]

        # Breadcrumbs
        self.bread = get_bread(level=self.level, weight=self.weight, char_orbit_label=self.char_orbit_label, hecke_orbit=cremona_letter_code(self.hecke_orbit - 1))

        # Downloads
        self.downloads = []
        if self.has_exact_qexp:
            self.downloads.append(('Download coefficients of q-expansion', url_for('.download_qexp', label=self.label)))
            # self.downloads.append(('Download coefficient ring basis', url_for('.download_hecke_ring', label=self.label))) FIXME
        if self.has_complex_qexp:
            self.downloads.append(('Download complex embeddings', url_for('.download_cc_data', label=self.label)))
        self.downloads.append(('Download all stored data', url_for('.download_newform', label=self.label)))

        self.title = "Newform %s"%(self.label)

    @property
    def friends(self):
        res = []
        base_label = [str(self.level)]
        if self.weight == 2 and self.dim == 1:
            label = self.isogeny_class_label.split('.')
            ec_label = '.'.join(label)
            ec_url = '/EllipticCurve/Q/' + '/'.join(label)
            res.append(('Elliptic curve isogeny class ' + ec_label, ec_url))
        base_label.append(str(self.weight))
        cmf_base = '/ModularForm/GL2/Q/holomorphic/'
        base_label =  map(str, [self.level, self.weight])
        ns1_label = '.'.join(base_label)
        ns1_url = cmf_base + '/'.join(base_label)
        res.append(('Newspace ' + ns1_label, ns1_url))
        char_letter = self.char_orbit_label
        ns_label = '.'.join(base_label + [char_letter])
        ns_url = cmf_base + '/'.join(base_label + [char_letter])
        res.append(('Newspace ' + ns_label, ns_url))
        hecke_letter = cremona_letter_code(self.hecke_orbit - 1)
        nf_url = ns_url + '/' + hecke_letter
        # without the leading /
        if db.lfunc_instances.exists({'url': nf_url[1:]}):
            res.append(('L-function ' + self.label, '/L' + nf_url))
        if self.dim > 1:
            for character in self.char_labels:
                for j in range(self.dim/self.char_degree):
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
        if self.__dict__.get('cm_disc', 0) == 0:
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
        if self.char_degree == 1:
            name = r'\(\Q\)'
        else:
            name = r'\(\Q(\zeta_{%s})\)' % self.char_order
        if self.char_degree < 24:
            return nf_display_knowl(cyclolookup[self.char_order], name=name)
        else:
            return name

    def defining_polynomial(self):
        if self.__dict__.get('field_poly'):
            return web_latex_split_on_pm(web_latex(coeff_to_poly(self.field_poly), enclose=False))
        return None

    def order_basis(self):
        # display the Hecke order, defining the variables used in the exact q-expansion display
        basis = []
        for num, den in zip(self.hecke_ring_numerators, self.hecke_ring_denominators):
            numsize = sum(len(str(c)) for c in num if c)
            if numsize > 80:
                num = web_latex_bigint_poly(num, r'\nu')
                if den == 1:
                    basis.append(num)
                elif den < 10**8:
                    basis.append(r"\((\)%s\()/%s\)"%(num, den))
                else:
                    basis.append(r"\((\)%s\()/\)%s"%(num, bigint_knowl(den)))
            else:
                num = web_latex(coeff_to_poly(num, 'nu'), enclose=(den == 1))
                if den == 1:
                    basis.append(num)
                elif den < 10**8:
                    basis.append(r"\((%s)/%s\)"%(num, den))
                else:
                    basis.append(r"\((%s)/\)%s"%(num, bigint_knowl(den)))
        basis = [r"\(\beta_{%s}%s =\mathstrut \)%s"%(i, r"\ " if (len(basis) > 10 and i < 10) else "", x) for i, x in enumerate(basis)]
        if len(basis) > 3 or any(d > 1 for d in self.hecke_ring_denominators):
            return '</p>\n<p class="short">'.join([""]+basis)
        else:
            return ', '.join(basis)

    def order_basis_table(self):
        s = '<table class="ntdata">\n  <tr>\n'
        for i in range(self.dim):
            s += r'    <td>\(\nu^{%s}\)</td>\n'%i
        s += '    <td>Denominator</td>\n  </tr>\n'
        for num, den in zip(self.hecke_ring_numerators, self.hecke_ring_denominators):
            s += '  <tr>\n'
            for coeff in num:
                s += '    <td>%s</td>\n' % (bigint_knowl(coeff))
            s += '    <td>%s</td>\n' % (bigint_knowl(den))
            s += '  </tr>\n'
        s += '</table>'
        return s

    def q_expansion(self, prec_max=10):
        # Display the q-expansion, truncating to precision prec_max.  Will be inside \( \).
        if self.has_exact_qexp:
            prec = min(self.qexp_prec, prec_max)
            zero = [0] * self.dim
            if self.dim == 1:
                s = web_latex_split_on_pm(web_latex(coeff_to_power_series([self.qexp[n][0] for n in range(prec+1)],prec=prec),enclose=False))
            else:
                s = eigs_as_seqseq_to_qexp(self.qexp[:prec])
            return s
        else:
            return coeff_to_power_series([0,1], prec=2)._latex_()

    def trace_expansion(self, prec_max=10):
        prec = min(self.texp_prec, prec_max)
        return web_latex_split_on_pm(web_latex(coeff_to_power_series(self.texp[:prec], prec=prec), enclose=False))

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
            x = self.cc_data[m].get('embedding_root_real', None)
            y = self.cc_data[m].get('embedding_root_imag', None)
            if x is None or y is None:
                return '?' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an'][n]
            if format == 'analytic_embed':
                x *= self.analytic_shift[n]
                y *= self.analytic_shift[n]
        if self.cc_data[m]['real']:
            return display_float(x, prec)
        else:
            return display_complex(x, y, prec)

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
            return display_complex(alpha.real(), alpha.imag(), prec)
        else:
            if i == 1:
                theta = chiang - theta
                if theta > 0.5:
                    theta -= 1
                elif theta <= -0.5:
                    theta += 1
            s = display_float(2*theta, prec)
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

    @property
    def plot(self):
        # perhaps this should be read directly from "Plot/ModularForm/GL2/Q/holomorphic/1/12/a/a/"
        # same idea in genus 2 would save 0.5 s
        I = CDF(0,1)
        DtoH = lambda x: (-I *x + 1)/(x - I)
        Htoq = lambda x: exp(2*CDF.pi()*I*x)
        Dtoq = lambda x: Htoq(DtoH(CDF(x)))
        absasphase = lambda x: Htoq(x.abs() + 0.6)
        R = PolynomialRing(CDF, "q");
        #FIXME increase precision and points
        f = R([CDF(tuple(elt)) for elt in self.cc_data[0]['an'][:30] ])
        plot = complex_plot(lambda x: +Infinity if abs(x) >= 0.99 else 16*absasphase(f(Dtoq(x))), (-1,1),(-1,1), plot_points=200, aspect_ratio = 1, axes=False)
        return encode_plot(plot, pad_inches=0, bbox_inches = 'tight', remove_axes = True)

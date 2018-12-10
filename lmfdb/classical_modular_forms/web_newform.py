# See templates/newform.html for how functions are called

from sage.all import prime_range, latex, QQ, PolynomialRing,\
    CDF, ZZ, CBF, cached_method, vector, lcm
from lmfdb.db_backend import db
from lmfdb.WebNumberField import nf_display_knowl, cyclolookup,\
    factor_base_factorization_latex

from lmfdb.number_fields.number_field import field_pretty
from flask import url_for
from lmfdb.utils import coeff_to_poly, coeff_to_power_series, web_latex,\
    web_latex_split_on_pm, web_latex_poly, bigint_knowl,\
    display_float, display_complex, round_CBF_to_half_int, polyquo_knowl,\
    display_knowl
from lmfdb.characters.utils import url_character
from lmfdb.lfunctions.Lfunctionutilities import names_and_urls
from lmfdb.search_parsing import integer_options
import re
from collections import defaultdict
from sage.databases.cremona import cremona_letter_code, class_to_int
from web_space import convert_spacelabel_from_conrey, get_bread
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey
import bisect

LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[a-z]+\.[a-z]+$")
INTEGER_RANGE_RE = re.compile(r"^([0-9]+)-([0-9]+)$")


# we store a_n with n \in [1, an_storage_bound]
an_storage_bound = 1000
# we store alpha_p with p <= an_storage_bound
primes_for_angles = prime_range(an_storage_bound)

def valid_label(label):
    return bool(LABEL_RE.match(label))

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

def quad_field_knowl(disc):
    r = 2 if disc > 0 else 0
    field_label = "2.%d.%d.1" % (r, abs(disc))
    field_name = field_pretty(field_label)
    return nf_display_knowl(field_label, field_name)

class WebNewform(object):
    def __init__(self, data, space=None, all_m = False, all_n = False):
        #TODO validate data
        # Need to set level, weight, character, num_characters, degree, has_exact_qexp, has_complex_qexp, hecke_ring_index, is_twist_minimal

        # Make up for db_backend currently deleting Nones
        for elt in db.mf_newforms.col_type:
            if elt not in data:
                data[elt] = None
        self.__dict__.update(data)
        self._data = data

        self.hecke_orbit_label = cremona_letter_code(self.hecke_orbit - 1)

        if self.level == 1 or ZZ(self.level).is_prime():
            self.factored_level = ''
        else:
            self.factored_level = ' = ' + ZZ(self.level).factor()._latex_()
        # We always print analytic conductor with 1 decimal digit
        self.analytic_conductor = '%.1f'%(self.analytic_conductor)
        self.single_generator = self.hecke_ring_power_basis or (self.dim == 2)


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
        self.has_analytic_rank = data.get('analytic_rank') is not None

        eigenvals = db.mf_hecke_nf.search({'hecke_orbit_code':self.hecke_orbit_code,  'n':{'$lt':100}}, ['n','an','trace_an'], sort=['n'])
        if eigenvals:  # this should always be true
            self.has_exact_qexp = True
            zero = [0] * self.dim
            self.qexp = [zero]
            self.texp = [0]
            for i, ev in enumerate(eigenvals, 1):
                if ev['n'] != i:
                    raise ValueError("Missing eigenvalue")
                self.texp.append(ev['trace_an'])
                if ev.get('an'):
                    self.qexp.append(ev['an'])
                else:
                    # only had traces
                    self.has_exact_qexp = False
            self.qexp_prec = len(self.qexp)
            self.texp_prec = len(self.texp)
        else:
            self.has_exact_qexp = False
        self.rel_dim = self.dim // self.char_degree


        ## CC_DATA
        self.cqexp_prec = 1001 # Initial estimate for error messages in render_newform_webpage.
                               # Should get updated in setup_cc_data.
        self.has_complex_qexp = False # stub, overwritten by setup_cc_data.

        self.char_conrey = self.char_labels[0]
        self.char_conrey_str = '\chi_{%s}(%s,\cdot)' % (self.level, self.char_conrey)
        self.char_conrey_link = url_character(type='Dirichlet', modulus=self.level, number=self.char_conrey)
        if self.has_inner_twist:
            self.inner_twist = [(chi,url_character(type='Dirichlet', modulus=self.level, number=chi)) for chi in self.inner_twist]
        self.character_label = "\(" + str(self.level) + "\)." + self.char_orbit_label

        self.has_further_properties = (self.is_cm != 0 or self.__dict__.get('is_twist_minimal') or self.has_inner_twist != 0 or self.char_orbit_index == 1 and self.level != 1 or self.hecke_cutters)

        self.plot =  db.mf_newform_portraits.lookup(self.label, projection = "portrait")

        # properties box
        self.properties = [('Label', self.label)]
        if self.plot is not None:
            self.properties += [(None, '<a href="{0}"><img src="{0}" width="200" height="200"/></a>'.format(self.plot))]

        self.properties += [('Level', str(self.level)),
                            ('Weight', str(self.weight)),
                            ('Character orbit', '%s.%s' % (self.level, self.char_orbit_label))]

        if self.is_self_dual != 0:
                self.properties += [('Self dual', 'Yes' if self.is_self_dual == 1 else 'No')]
        self.properties += [('Analytic conductor', self.analytic_conductor)]

        if self.analytic_rank is not None:
            self.properties += [('Analytic rank', str(int(self.analytic_rank)))]

        self.properties += [('Dimension', str(self.dim))]

        if self.projective_image:
            self.properties += [('Projective image', '\(%s\)' % self.projective_image_latex)]
        if self.artin_degree: # artin_degree > 0
            self.properties += [('Artin image size', str(self.artin_degree))]
        if self.artin_image:
            self.properties += [('Artin image', '\(%s\)' %  self.artin_image_display)]

        if self.is_self_twist ==1:
            if self.is_cm == 1:
                disc = ' and '.join([ str(d) for d in self.self_twist_discs if d < 0 ])
                self.properties += [('CM discriminant', disc)]
            elif self.is_cm == -1:
                self.properties += [('CM', 'No')]

            if self.weight == 1:
                if self.is_rm == 1:
                    disc = ' and '.join([ str(d) for d in self.self_twist_discs if d > 0 ])
                    self.properties += [('RM discriminant', disc)]
                elif self.is_rm == -1:
                    self.properties += [('RM', 'No')]

        # Breadcrumbs
        self.bread = get_bread(level=self.level, weight=self.weight, char_orbit_label=self.char_orbit_label, hecke_orbit=cremona_letter_code(self.hecke_orbit - 1))

        self.title = "Newform %s"%(self.label)

    @property
    def lfunction_labels(self):
        base_label = self.label.split('.')
        res = []
        for character in self.char_labels:
            for j in range(self.dim/self.char_degree):
                label = base_label + [str(character), str(j + 1)]
                lfun_label = '.'.join(label)
                res.append(lfun_label)
        return res
    @property
    def friends(self):
        res = names_and_urls(self.related_objects)
        base_label = map(str, [self.level, self.weight])
        cmf_base = '/ModularForm/GL2/Q/holomorphic/'
        ns1_label = '.'.join(base_label)
        ns1_url = cmf_base + '/'.join(base_label)
        res.append(('Newspace ' + ns1_label, ns1_url))
        char_letter = self.char_orbit_label
        ns_label = '.'.join(base_label + [char_letter])
        ns_url = cmf_base + '/'.join(base_label + [char_letter])
        res.append(('Newspace ' + ns_label, ns_url))
        nf_url = ns_url + '/' + self.hecke_orbit_label

        # fake it until you make it
        # display L-functions from Artin
        if self.weight == 1:
            res += [ ('L-function ' + name.split(' ')[-1], '/L' + url) for name, url in res if url.startswith('/ArtinRepresentation/') ]
        else:
            if db.lfunc_instances.exists({'url': nf_url[1:]}):
                res.append(('L-function ' + self.label, '/L' + nf_url))
            if len(self.char_labels)*self.rel_dim > 50:
                res = map(lambda elt : list(map(str, elt)), res)
                # properties_lfun(initialFriends, label, nf_url, char_labels, rel_dim)
                return '<script id="properties_script">$( document ).ready(function() {properties_lfun(%r, %r, %r, %r, %r)}); </script>' %  (res, str(self.label), str(nf_url), self.char_labels, self.rel_dim)
            if self.dim > 1:
                for lfun_label in self.lfunction_labels:
                    lfun_url =  '/L' + cmf_base + lfun_label.replace('.','/')
                    res.append(('L-function ' + lfun_label, lfun_url))

        return res


    @property
    def downloads(self):
        downloads = []
        if self.has_exact_qexp:
            downloads.append(('Download coefficients of q-expansion', url_for('.download_qexp', label=self.label)))
        downloads.append(('Download trace form', url_for('.download_traces', label=self.label)))
        if self.has_complex_qexp:
            downloads.append(('Download complex embeddings', url_for('.download_cc_data', label=self.label)))
            downloads.append(('Download Satake angles', url_for('.download_satake_angles', label=self.label)))
        downloads.append(('Download all stored data', url_for('.download_newform', label=self.label)))
        return downloads

    def setup_cc_data(self, info):
        """
        INPUT:

        - ``info`` -- a dictionary with keys
          - ``m`` -- a string describing the embedding indexes desired
          - ``n`` -- a string describing the a_n desired
          - ``CC_m`` -- a list of embedding indexes
          - ``CC_n`` -- a list of desired a_n
          - ``format`` -- one of 'embed', 'analytic_embed', 'satake', or 'satake_angle'
        """
        an_formats = ['embed','analytic_embed',None]
        angles_formats = ['satake','satake_angle',None]
        m = info.get('m','1-%s'%(min(self.dim,20)))
        n = info.get('n','1-10')
        CC_m = info.get('CC_m', integer_options(m))
        CC_n = info.get('CC_n', integer_options(n))
        # convert CC_n to an interval in [1,an_storage_bound]
        CC_n = ( max(1, min(CC_n)), min(an_storage_bound, max(CC_n)) )
        an_keys = (CC_n[0]-1, CC_n[1])
        # extra 5 primes in case we hit too many bad primes
        angles_keys = (bisect.bisect_left(primes_for_angles, CC_n[0]), bisect.bisect_right(primes_for_angles, CC_n[1]) + 5)
        format = info.get('format')
        cc_proj = ['conrey_label','embedding_index','embedding_m','embedding_root_real','embedding_root_imag']
        an_projection = 'an[%d:%d]' % an_keys
        angles_projection = 'angles[%d:%d]' % angles_keys
        if format in an_formats:
            cc_proj.append(an_projection)
        if format in angles_formats:
            cc_proj.append(angles_projection)
        query = {'hecke_orbit_code':self.hecke_orbit_code}
        range_match = INTEGER_RANGE_RE.match(m)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            query['embedding_m'] = {'$gte':low, '$lte':high}
        else:
            query['embedding_m'] = {'$in': CC_m}

        cc_data= list(db.mf_hecke_cc.search(query, projection = cc_proj))
        if not cc_data:
            self.has_complex_qexp = False
            self.cqexp_prec = 0
        else:
            self.has_complex_qexp = True
            self.cqexp_prec = an_keys[1] + 1
            self.cc_data = {}
            for embedded_mf in cc_data:
                #as they are stored as a jsonb, large enough elements might be recognized as an integer
                if format in an_formats:
                    # we don't store a_0, thus the +1
                    embedded_mf['an'] = {i: [float(x), float(y)] for i, (x, y) in enumerate(embedded_mf.pop(an_projection), an_keys[0] + 1)}
                if format in angles_formats:
                    embedded_mf['angles'] = {primes_for_angles[i]: theta for i, theta in enumerate(embedded_mf.pop(angles_projection), angles_keys[0])}
                self.cc_data[embedded_mf.pop('embedding_m')] = embedded_mf
            if format in ['analytic_embed',None]:
                self.analytic_shift = {i : float(i)**((1-ZZ(self.weight))/2) for i in self.cc_data.values()[0]['an'].keys()}
            if format in angles_formats:
                self.character_values = defaultdict(list)
                G = DirichletGroup_conrey(self.level)
                chars = [DirichletCharacter_conrey(G, char) for char in self.char_labels]
                for p in self.cc_data.values()[0]['angles'].keys():
                    if p.divides(self.level):
                        continue
                    for chi in chars:
                        c = chi.logvalue(p) * self.char_order
                        angle = float(c / self.char_order)
                        value = CDF(0,2*CDF.pi()*angle).exp()
                        self.character_values[p].append((angle, value))


    @staticmethod
    def by_label(label):
        if not valid_label(label):
            raise ValueError("Invalid newform label %s." % label)

        data = db.mf_newforms.lookup(label)
        if data is None:
            # Display a different error if Nk^2 is too large
            N, k, a, x = label.split('.')
            Nk2 = int(N) * int(k) * int(k)
            max_Nk2 = db.mf_newforms.max('Nk2')
            if Nk2 > max_Nk2:
                raise ValueError(r"Level and weight too large.  The product \(Nk^2 = %s\) is larger than the currently computed threshold of \(%s\)."%(Nk2, max_Nk2))
            raise ValueError("Newform %s not found" % label)
        return WebNewform(data)

    @property
    def hecke_ring_index_factored(self):
        if self.hecke_ring_index_factorization is not None:
            return "\( %s \)" % factor_base_factorization_latex(self.hecke_ring_index_factorization)
        return None

    @property
    def projective_image_latex(self):
        if self.projective_image:
            return '%s_{%s}' % (self.projective_image[:1], self.projective_image[1:])
        return None

    def field_display(self):
        # display the coefficient field
        if self.rel_dim == 1:
            return self.cyc_display()
        else:
            return self.field_display_gen(self.nf_label, self.field_poly)

    def field_display_gen(self, label, poly):
        if label is None:
            if poly:
                return polyquo_knowl(poly)
            else:
                return 'Unknown'
        elif label == u'1.1.1.1':  # rationals, special case
            return nf_display_knowl(label, name=r"\(\Q\)")
        else:
            return nf_display_knowl(label, field_pretty(label))

    @property
    def artin_field_display(self):
        label, poly = self.artin_field_label, self.artin_field
        return self.field_display_gen(label, poly)

    @property
    def projective_field_display(self):
        label, poly = self.projective_field_label, self.projective_field
        return self.field_display_gen(label, poly)

    @property
    def artin_image_display(self):
        if self.artin_image:
            pretty = db.gps_small.lookup(self.artin_image, projection = 'pretty')
            return pretty if pretty else self.artin_image
        return None



    def rm_and_cm_field_knowl(self, sign  = 1):
        if self.self_twist_discs:
            disc = [ d for d in self.self_twist_discs if sign*d > 0 ]
            return ' and '.join( map(quad_field_knowl, disc) )
        else:
            return ''

    def cyc_display(self):
        if self.char_degree == 1:
            name = r'\(\Q\)'
        else:
            m = self.char_order
            if self.dim == self.char_degree and self.field_poly_root_of_unity:
                # the relative dimension is 1 and the coefficient field is cyclotomic
                # We want to display it using the appropriate root of unity
                m = self.field_poly_root_of_unity
            if m == 4:
                name = r'\(\Q(i)\)'
            else:
                name = r'\(\Q(\zeta_{%s})\)' % m
        if self.char_degree < 24:
            return nf_display_knowl(cyclolookup[self.char_order], name=name)
        else:
            return name

    def display_newspace(self):
        s = r'\(S_{%s}^{\mathrm{new}}('
        if self.char_order == 1:
            s += r'\Gamma_0(%s))\)'
        else:
            s += r'%s, \chi)\)'
        return s%(self.weight, self.level)

    def display_hecke_cutters(self):
        polynomials = []
        truncated = False
        for p,F in self.hecke_cutters:
            cut = len(F) - 1
            count = 0
            while cut >= 0 and count < 8:
                if F[cut]:
                    count += 1
                cut -= 1
            if count < 8 or cut == 0 and abs(F[0]) < 100:
                F = latex(coeff_to_poly(F, 'T%s'%p))
            else:
                # truncate to the first 8 nonzero coefficients
                F = [0]*(cut+1) + F[cut+1:]
                F = latex(coeff_to_poly(F, 'T%s'%p)) + r' + \cdots'
                truncated = True
            polynomials.append(web_latex_split_on_pm(F))
        title = 'linear operator'
        if len(polynomials) > 1:
            title += 's'
        knowl = display_knowl('mf.elliptic.hecke_cutter', title=title)
        desc = "<p>This newform can be constructed as the "
        if truncated or len(polynomials) > 1:
            if len(polynomials) > 1:
                desc += "intersection of the kernels "
            else:
                desc += "kernel "
            desc += "of the following %s acting on %s:</p>\n<table>"
            desc = desc % (knowl, self.display_newspace())
            desc += "\n".join("<tr><td>%s</td></tr>" % F for F in polynomials) + "\n</table>"
        elif len(polynomials) == 1:
            desc += "kernel of the %s %s acting on %s."
            desc = desc % (knowl, polynomials[0], self.display_newspace())
        else:
            desc = r"<p>There are no other newforms in %s.</p>"%(self.display_newspace())
        return desc

    def defining_polynomial(self):
        if self.field_poly:
            return web_latex_split_on_pm(web_latex(coeff_to_poly(self.field_poly), enclose=False))
        return None

    def Qnu(self):
        if self.field_poly_root_of_unity != 0 or self.single_generator:
            return ""
        else:
            return r"\(\Q(\nu)\)"

    def Qeq(self):
        if self.field_poly_root_of_unity != 0 or self.single_generator:
            return ""
        else:
            return r"\(=\)"

    def _make_frac(self, num, den):
        if den == 1:
            return num
        elif den < 10**8:
            return r"\((\)%s\()/%s\)"%(num, den)
        else:
            return r"\((\)%s\()/\)%s"%(num, bigint_knowl(den))

    @property
    def _nu_latex(self):
        if self.field_poly_root_of_unity != 0:
            if self.field_poly_root_of_unity == 4:
                return 'i'
            else:
                return r"\zeta_{%s}" % self.field_poly_root_of_unity
        else:
            return r"\nu"

    @property
    def _nu_var(self):
        if self.field_poly_root_of_unity != 0:
            if self.field_poly_root_of_unity == 4:
                return 'i'
            else:
                return r"zeta%s" % self.field_poly_root_of_unity
        else:
            return r"nu"

    def _make_table(self, basis):
        s = '<table class="coeff_ring_basis">\n'
        for LHS, RHS in basis:
            s += r'<tr><td class="LHS">%s</td><td class="eq">\(=\)</td><td class="RHS">%s</td></tr>'%(LHS, RHS) + '\n'
        return s + "</table>"

    def _order_basis_forward(self):
        basis = []
        for i, (num, den) in enumerate(zip(self.hecke_ring_numerators, self.hecke_ring_denominators)):
            numsize = sum(len(str(c)) for c in num if c)
            if numsize > 80:
                num = web_latex_poly(num, self._nu_latex, superscript=True, cutoff=8)
            else:
                num = web_latex(coeff_to_poly(num, self._nu_var))
            betai = r'\(\beta_{%s}\)'%i
            basis.append((betai, self._make_frac(num, den)))
        return self._make_table(basis)

    def _order_basis_inverse(self):
        basis = [('\(1\)', r'\(\beta_0\)')]
        for i, (num, den) in enumerate(zip(self.hecke_ring_inverse_numerators[1:], self.hecke_ring_inverse_denominators[1:])):
            num = web_latex_poly(num, r'\beta', superscript=False, cutoff=40)
            if i == 0:
                nupow = r'\(%s\)' % self._nu_latex
            else:
                nupow = r'\(%s^{%s}\)' % (self._nu_latex, i+1)
            basis.append((nupow, self._make_frac(num, den)))
        return self._make_table(basis)

    def order_basis(self):
        # display the Hecke order, defining the variables used in the exact q-expansion display
        html = r"""
<script>
function switch_basis(btype) {
    $('.forward-basis').hide();
    $('.inverse-basis').hide();
    $('.'+btype).show();
}
</script>
<div class="forward-basis%s">
%s
<div class="toggle">
  <a onclick="switch_basis('inverse-basis'); return false" href='#'>Display \(%s^j\) in terms of \(\beta_i\)</a>
</div>
</div>
<div class="inverse-basis%s">
%s
<div class="toggle">
  <a onclick="switch_basis('forward-basis'); return false" href='#'>Display \(\beta_i\) in terms of \(%s^j\)</a>
</div>
</div>"""
        forward_size = inverse_size = 0
        for num, den in zip(self.hecke_ring_numerators, self.hecke_ring_denominators):
            forward_size += sum(len(str(c)) for c in num if c) + len(str(den))
        for num, den in zip(self.hecke_ring_inverse_numerators, self.hecke_ring_inverse_denominators):
            inverse_size += sum(len(str(c)) for c in num if c) + len(str(den))
        if len(self.hecke_ring_numerators) > 3 and forward_size > 240 and 2*inverse_size < forward_size:
            return html % (" nodisplay", self._order_basis_forward(), self._nu_latex, "", self._order_basis_inverse(), self._nu_latex)
        else:
            return html % ("", self._order_basis_forward(), self._nu_latex, " nodisplay", self._order_basis_inverse(), self._nu_latex)

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

    def order_gen(self):
        if self.field_poly_root_of_unity == 4:
            return r'\(i = \sqrt{-1}\)'
        elif self.hecke_ring_power_basis and self.field_poly_root_of_unity != 0:
            return r'a primitive root of unity \(\zeta_{%s}\)' % self.field_poly_root_of_unity
        elif self.dim == 2:
            c, b, a = map(ZZ, self.field_poly)
            D = b**2 - 4*a*c
            d = D.squarefree_part()
            s = (D//d).isqrt()
            k, l = map(ZZ, self.hecke_ring_numerators[1])
            k = k / self.hecke_ring_denominators[1]
            l = l / self.hecke_ring_denominators[1]
            beta = vector((k - (b*l)/(2*a), ((s*l)/(2*a)).abs()))
            den = lcm(beta[0].denom(), beta[1].denom())
            beta *= den
            if d == -1:
                Sqrt = 'i'
            else:
                Sqrt = r'\sqrt{%s}' % d
            if beta[1] != 1:
                Sqrt = r'%s%s' % (beta[1], Sqrt)
            if beta[0] == 0:
                Num = Sqrt
            else:
                Num = r'%s + %s' % (beta[0], Sqrt)
            if den == 1:
                Frac = Num
            else:
                Frac = r'\frac{1}{%s}(%s)' % (den, Num)
            return r'\(\beta = %s\)' % Frac
        elif self.hecke_ring_power_basis:
            return r'a root \(\beta\) of the polynomial %s' % (self.defining_polynomial())
        else:
            if self.dim <= 5:
                betas = ",".join(r"\beta_%s" % (i) for i in range(1, self.dim))
            else:
                betas = r"\beta_1,\ldots,\beta_{%s}" % (self.dim - 1)
            return r'a basis \(1,%s\) for the coefficient ring described below' % (betas)

    def _get_Rgens(self):
        d = self.dim
        if self.single_generator:
            if self.hecke_ring_power_basis and self.field_poly_root_of_unity != 0:
                R = PolynomialRing(QQ, self._nu_var)
            else:
                R = PolynomialRing(QQ, 'beta')
            beta = R.gen()
            return [beta**i for i in range(d)]
        else:
            R = PolynomialRing(QQ, ['beta%s' % i for i in range(1,d)])
            return [1] + [g for g in R.gens()]

    def display_character_values(self):
        Rgens = self._get_Rgens()
        d = self.dim
        gens = [r'      <td class="dark border-right border-bottom">\(n\)</td>']
        vals = [r'      <td class="dark border-right">\(\chi(n)\)</td>']
        for j, (g, chi_g) in enumerate(self.hecke_ring_character_values):
            term = sum(Rgens[i]*chi_g[i] for i in range(d))
            latexterm = latex(term)
            color = "dark" if j%2 else "light"
            gens.append(r'      <td class="%s border-bottom">\(%s\)</td>'%(color, g))
            vals.append(r'      <td class="%s">\(%s\)</td>'%(color, latexterm))
        return '    <tr>\n%s    </tr>\n    <tr>\n%s    </tr>'%('\n'.join(gens), '\n'.join(vals))

    def eigs_as_seqseq_to_qexp(self, prec_max):
        # Takes a sequence of sequence of integers and returns a string for the corresponding q expansion
        # For example, eigs_as_seqseq_to_qexp([[0,0],[1,3]]) returns "\((1+3\beta_{1})q\)\(+O(q^2)\)"
        prec = min(self.qexp_prec, prec_max)
        if prec == 0:
            return 'O(1)'
        eigseq = self.qexp[:prec]
        d = self.dim
        Rgens = self._get_Rgens()
        s = ''
        for j in range(len(eigseq)):
            term = sum([Rgens[i]*eigseq[j][i] for i in range(d)])
            if term != 0:
                latexterm = latex(term)
                if term.number_of_terms() > 1:
                    latexterm = r"\left(" +  latexterm + r"\right)"

                if j > 0:
                    if term == 1:
                        latexterm = ''
                    elif term == -1:
                        latexterm = '-'
                    if j == 1:
                        latexterm += ' q'
                    else:
                        latexterm += ' q^{%d}' % j
                #print latexterm
                if s != '' and latexterm[0] != '-':
                    latexterm = '+' + latexterm
                s += '\(' + latexterm + '\) '
        # Work around bug in Sage's latex
        s = s.replace('betaq', 'beta q')
        return s + '\(+O(q^{%d})\)' % prec

    def q_expansion(self, prec_max=10):
        # Display the q-expansion, truncating to precision prec_max.  Will be inside \( \).
        if self.has_exact_qexp:
            prec = min(self.qexp_prec, prec_max)
            if self.dim == 1:
                s = web_latex_split_on_pm(web_latex(coeff_to_power_series([self.qexp[n][0] for n in range(prec)],prec=prec),enclose=False))
            else:
                s = self.eigs_as_seqseq_to_qexp(prec)
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
        return "{c}.{e}".format(c=self.cc_data[m]['conrey_label'], e=((m-1)%self.rel_dim)+1)


    def embedding(self, m, n=None, prec=6, format='embed'):
        """
        Return the value of the ``m``th embedding on a specified input.
        Should only be used when all of the entries in this column are either real
        or imaginary.

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

    def _display_re(self, x, prec):
        if abs(x) < 10**(-prec):
            return ""
        return r"%s"%(display_float(x, prec).replace('-','&minus;'))

    def _display_im(self, y, prec):
        if abs(y) < 10**(-prec):
            return ""
        res = display_float(y, prec)
        if res == '1':
            res = ''
        return r"%s<em>i</em>"%(res)

    def _display_op(self, x, y, prec):
        xiszero = abs(x) < 10**(-prec)
        yiszero = abs(y) < 10**(-prec)
        if xiszero and yiszero:
            return r"0"
        elif yiszero or (xiszero and y > 0):
            return ""
        elif y > 0:
            return r"+"
        elif y < 0:
            return r"&minus;"

    def embedding_re(self, m, n=None, prec=6, format='embed'):
        if n is None:
            x = self.cc_data[m].get('embedding_root_real', None)
            if x is None:
                return '' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an'][n]
            if format == 'analytic_embed':
                x *= self.analytic_shift[n]
        return self._display_re(x, prec)

    def embedding_im(self, m, n=None, prec=6, format='embed'):
        if n is None:
            y = self.cc_data[m].get('embedding_root_imag', None)
            if y is None:
                return '' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an'][n]
            if format == 'analytic_embed':
                y *= self.analytic_shift[n]
        return self._display_im(abs(y), prec) # sign is handled in embedding_op

    def embedding_op(self, m, n=None, prec=6):
        if n is None:
            x = self.cc_data[m].get('embedding_root_real', None)
            y = self.cc_data[m].get('embedding_root_imag', None)
            if x is None or y is None:
                return '?' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an'][n]
        return self._display_op(x, y, prec)

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
        if format == 'satake':
            alpha = self._get_alpha(m, p, i)
            return display_complex(alpha.real(), alpha.imag(), prec)
        else:
            return self.satake_angle(m, p, i, prec)

    @cached_method
    def satake_angle(self, m, p, i, prec=6):
        theta = self._get_theta(m, p, i)
        s = display_float(2*theta, prec)
        if s == "1":
            s =  r'\pi'
        elif s== "-1":
            s =  r'-\pi'
        elif s != "0":
            s += r'\pi'
        return r'\(%s\)'%s

    @cached_method
    def _get_alpha(self, m, p, i):
        theta = CBF(self.cc_data[m]['angles'][p])
        unit = (2 * theta).exppii()
        if i == 0:
            res =  unit
        else:
            # it is very likely that the real or imag part are a half integer
            # as it returns a CDF, we need to convert it to CBF again
            chival = CBF(round_CBF_to_half_int(CBF(self.character_values[p][(m-1) // self.rel_dim][1])))
            res =  chival / unit
        return round_CBF_to_half_int(res)

    @cached_method
    def _get_theta(self, m, p, i):
        theta = self.cc_data[m]['angles'][p]
        chiang, chival = self.character_values[p][(m-1) // self.rel_dim]
        if i == 1:
            theta = chiang - theta
            if theta > 0.5:
                theta -= 1
            elif theta <= -0.5:
                theta += 1
        return theta

    def satake_re(self, m, p, i, prec=6):
        return self._display_re(self._get_alpha(m, p, i).real(), prec)

    def satake_im(self, m, p, i, prec=6):
        return self._display_im(abs(self._get_alpha(m, p, i).imag()), prec)

    def satake_op(self, m, p, i, prec=6):
        alpha = self._get_alpha(m, p, i)
        return self._display_op(alpha.real(), alpha.imag(), prec)

    def an_range(self, L, format='embed'):
        if format in ['embed', 'analytic_embed']:
            return [n for n in L if n >= 2 and n < self.cqexp_prec]
        else:
            return [p for p in L if p >= 2 and p < self.cqexp_prec and ZZ(p).is_prime() and not ZZ(p).divides(self.level)]

    def m_range(self, L):
        return [m for m in L if m >= 1 and m <= self.dim]


# -*- coding: utf-8 -*-
# See templates/newform.html for how functions are called
from __future__ import absolute_import
from six import string_types
from collections import defaultdict
import bisect, re

from flask import url_for
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey
from sage.all import (prime_range, latex, QQ, PolynomialRing, prime_pi, gcd,
                      CDF, ZZ, CBF, cached_method, vector, lcm, RR, lazy_attribute)
from sage.databases.cremona import cremona_letter_code, class_to_int

from lmfdb import db
from lmfdb.utils import (
    coeff_to_poly, coeff_to_power_series, web_latex,
    web_latex_poly, bigint_knowl, bigpoly_knowl, too_big, make_bigint,
    display_float, display_complex, round_CBF_to_half_int, polyquo_knowl,
    display_knowl, factor_base_factorization_latex,
    integer_options, names_and_urls)
from lmfdb.number_fields.web_number_field import nf_display_knowl
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.galois_groups.transitive_group import small_group_label_display_knowl
from lmfdb.sato_tate_groups.main import st_link, get_name
from .web_space import convert_spacelabel_from_conrey, get_bread, cyc_display, display_hecke_polys

LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[a-z]+\.[a-z]+$")
EMB_LABEL_RE = re.compile(r"^[0-9]+\.[0-9]+\.[a-z]+\.[a-z]+\.[0-9]+\.[0-9]+$")
INTEGER_RANGE_RE = re.compile(r"^([0-9]+)-([0-9]+)$")


# we may store alpha_p with p <= 3000
primes_for_angles = prime_range(3000)

def valid_label(label):
    return bool(LABEL_RE.match(label))

def valid_emb_label(label):
    return bool(EMB_LABEL_RE.match(label))

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

def field_display_gen(label, poly, disc=None, self_dual=None, truncate=0):
    """
    This function is used to display a number field knowl.  When the field
    is not in the LMFDB, it uses a dynamic knowl displaying the polynomial
    and discriminant.  Otherwise, it uses the standard LMFDB number field knowl.

    INPUT:

    - ``label`` -- the LMFDB label for the field (``None`` if not in the LMFDB)
    - ``poly`` -- the defining polynomial for the field as a list
    - ``disc`` -- the discriminant of the field, as a list of (p, e) pairs
    - ``truncate`` -- an integer, the maximum length of the field label before truncation.
        If 0, no truncation will occur.
    """
    if label is None:
        if poly:
            if self_dual:
                unit = ZZ(1)
            else:
                unit = ZZ(-1)**((len(poly)-1)//2)
            return polyquo_knowl(poly, disc, unit, 12)
        else:
            return ''
    else:
        name = field_pretty(label)
        if truncate and name == label and len(name) > truncate:
            parts = label.split('.')
            parts[2] = r'\(\cdots\)'
            name = '.'.join(parts)
        return nf_display_knowl(label, name)

def th_wrap(kwl, title):
    return '    <th>%s</th>' % display_knowl(kwl, title=title)
def td_wrapl(val):
    return '    <td align="left">%s</td>' % val
def td_wrapc(val):
    return '    <td align="center">%s</td>' % val
def td_wrapr(val):
    return '    <td align="right">%s</td>' % val

def parity_text(val):
    return 'odd' if val == -1 else 'even'

class WebNewform(object):
    def __init__(self, data, space=None, all_m = False, all_n = False, embedding_label = None):
        #TODO validate data
        # Need to set level, weight, character, num_characters, degree, has_exact_qexp, has_complex_qexp, hecke_ring_index, is_twist_minimal

        # Make up for db_backend currently deleting Nones
        for elt in db.mf_newforms.col_type:
            if elt not in data:
                data[elt] = None
        self.__dict__.update(data)
        self._data = data
        self.embedding_label = embedding_label
        self.embedded_minimal_twist = None # stub filled in below when embedding_label is set

        self.hecke_orbit_label = cremona_letter_code(self.hecke_orbit - 1)

        if self.level == 1 or ZZ(self.level).is_prime():
            self.factored_level = ''
        else:
            self.factored_level = ' = ' + ZZ(self.level).factor()._latex_()
        if 'field_disc_factorization' not in data: # Until we have search results include nulls
            self.field_disc_factorization = None
        elif self.field_disc_factorization:
            self.field_disc_factorization = [(ZZ(p), ZZ(e)) for p, e in self.field_disc_factorization]
        self.rel_dim = self.dim // self.char_degree

        self.has_analytic_rank = data.get('analytic_rank') is not None

        self.texp = [0] + self.traces
        self.texp_prec = len(self.texp)

        #self.char_conrey = self.conrey_indexes[0]
        #self.char_conrey_str = '\chi_{%s}(%s,\cdot)' % (self.level, self.char_conrey)
        self.character_label = r"\(" + str(self.level) + r"\)." + self.char_orbit_label

        self.hecke_ring_character_values = None
        self.single_generator = None
        self.has_exact_qexp = False
        if self.embedding_label is None:
            hecke_cols = ['hecke_ring_numerators', 'hecke_ring_denominators', 'hecke_ring_inverse_numerators', 'hecke_ring_inverse_denominators', 'hecke_ring_cyclotomic_generator', 'hecke_ring_character_values', 'hecke_ring_power_basis', 'maxp']
            eigenvals = db.mf_hecke_nf.lucky({'hecke_orbit_code':self.hecke_orbit_code}, ['an'] + hecke_cols)
            if eigenvals and eigenvals.get('an'):
                self.has_exact_qexp = True
                for attr in hecke_cols:
                    setattr(self, attr, eigenvals.get(attr))
                m = self.hecke_ring_cyclotomic_generator
                if m is None or m == 0:
                    zero = [0] * self.dim
                else:
                    zero = []
                self.qexp = [zero] + eigenvals['an']
                self.qexp_prec = len(self.qexp)
                m = self.field_poly_root_of_unity
                self.single_generator = self.hecke_ring_power_basis or (self.dim == 2)
                # This is not enough, for some reason
                #if (m != 0) and (not self.single_generator):
                # This is the only thing I could make work:
                if (m != 0) and (self.hecke_ring_numerators is not None):
                    self.convert_qexp_to_cyclotomic(m)
        else:
            hecke_cols = ['hecke_ring_cyclotomic_generator', 'hecke_ring_power_basis']
            hecke_data = db.mf_hecke_nf.lucky({'hecke_orbit_code':self.hecke_orbit_code}, hecke_cols)
            if hecke_data:
                for attr in hecke_cols:
                    setattr(self, attr, hecke_data.get(attr))
                self.single_generator = self.hecke_ring_power_basis or (self.dim == 2)
            # get data from char_dir_values
            self.char_conrey = self.embedding_label.split('.')[0]
            char_values = db.char_dir_values.lucky({'label': '%s.%s' % (self.level, self.char_conrey)},['order','values_gens'])
            if char_values is None:
                raise ValueError("Invalid Conrey label")
            self.hecke_ring_character_values = char_values['values_gens'] # [[i,[[1, m]]] for i, m in char_values['values_gens']]
            self.hecke_ring_cyclotomic_generator = char_values['order']
        # sort by the generators
        if self.hecke_ring_character_values:
            self.hecke_ring_character_values.sort(key = lambda elt: elt[0])

        ## CC_DATA
        self.has_complex_qexp = False # stub, overwritten by setup_cc_data.

        # lookup twists (of newform orbits or embedded newforms as appropriate)
        if self.embedding_label is None:
            self.twists = [r for r in db.mf_twists_nf.search({'source_label':self.label})]
        else:
            self.embedded_twists = [r for r in db.mf_twists_cc.search({'source_label':self.label + '.' + self.embedding_label})]
            if self.embedded_twists:
                self.embedded_minimal_twist = self.embedded_twists[0]["twist_class_label"]

        self.plot =  db.mf_newform_portraits.lookup(self.label, projection = "portrait")

        # properties box
        if embedding_label is None:
            self.properties = [('Label', self.label)]
        else:
            self.properties = [('Label', '%s.%s' % (self.label, self.embedding_label))]
        if self.plot is not None:
            self.properties += [(None, '<img src="{0}" width="200" height="200"/>'.format(self.plot))]

        self.properties += [('Level', str(self.level)),
                            ('Weight', str(self.weight))]
        if self.embedding_label is None:
            self.properties.append(('Character orbit', '%s.%s' % (self.level, self.char_orbit_label)))
        else:
            self.properties.append(('Character', '%s.%s' % (self.level, self.char_conrey)))

        if self.is_self_dual != 0:
            self.properties += [('Self dual', 'yes' if self.is_self_dual == 1 else 'no')]
        self.properties += [('Analytic conductor', '%.3f'%(self.analytic_conductor))]

        if self.analytic_rank is not None:
            self.properties += [('Analytic rank', str(int(self.analytic_rank)))]

        self.properties += [('Dimension', str(self.dim))]

        if self.projective_image:
            self.properties += [('Projective image', r'\(%s\)' % self.projective_image_latex)]
        # Artin data would make the property box scroll
        #if self.artin_degree: # artin_degree > 0
        #    self.properties += [('Artin image size', str(self.artin_degree))]
        #if self.artin_image:
        #    self.properties += [('Artin image', r'\(%s\)' %  self.artin_image_display)]

        if self.is_cm and self.is_rm:
            disc = ', '.join([ str(d) for d in self.self_twist_discs ])
            self.properties += [('CM/RM discs', disc)]
        elif self.is_cm:
            disc = ' and '.join([ str(d) for d in self.self_twist_discs if d < 0 ])
            self.properties += [('CM discriminant', disc)]
        elif self.is_rm:
            disc = ' and '.join([ str(d) for d in self.self_twist_discs if d > 0 ])
            self.properties += [('RM discriminant', disc)]
        elif self.weight == 1:
            self.properties += [('CM/RM', 'no')]
        else:
            self.properties += [('CM', 'no')]
        if self.inner_twist_count >= 1:
            self.properties += [('Inner twists', str(self.inner_twist_count))]
        self.title = "Newform orbit %s"%(self.label)

    # Breadcrumbs
    @property
    def bread(self):
        kwds = dict(level=self.level, weight=self.weight, char_orbit_label=self.char_orbit_label,
                    hecke_orbit=cremona_letter_code(self.hecke_orbit - 1))
        if self.embedding_label is not None:
            kwds['embedding_label'] = self.embedding_label
        return get_bread(**kwds)

    def convert_qexp_to_cyclotomic(self,  m):
        from sage.all import CyclotomicField
        F = CyclotomicField(m)
        zeta = F.gens()[0]
        ret = []
        l = len(self.hecke_ring_numerators)
        betas = [F(self.hecke_ring_numerators[i]) /
                 self.hecke_ring_denominators[i] for i in range(l)]
        write_in_powers = zeta.coordinates_in_terms_of_powers()
        for coeffs in self.qexp:
            elt = sum([coeffs[i] * betas[i] for i in range(l)])
            ret.append(write_in_powers(elt))
        self.single_generator = True
        self.hecke_ring_power_basis = True
        self.qexp = ret
        return ret
    
    @lazy_attribute
    def embedding_labels(self):
        base_label = self.label.split('.')
        def make_label(character, j):
            label = base_label + [str(character), str(j + 1)]
            return '.'.join(label)
        if self.embedding_label is None:
            return [make_label(character, j)
                    for character in self.conrey_indexes
                    for j in range(self.dim//self.char_degree)]
        else:
            character, j = map(int, self.embedding_label.split('.'))
            return [make_label(character, j-1)]

    @property
    def friends(self):
        # first newspaces
        res = []
        base_label = [str(s) for s in [self.level, self.weight]]
        cmf_base = '/ModularForm/GL2/Q/holomorphic/'
        ns1_label = '.'.join(base_label)
        ns1_url = cmf_base + '/'.join(base_label)
        res.append(('Newspace ' + ns1_label, ns1_url))
        char_letter = self.char_orbit_label
        ns_label = '.'.join(base_label + [char_letter])
        ns_url = cmf_base + '/'.join(base_label + [char_letter])
        res.append(('Newspace ' + ns_label, ns_url))
        nf_url = ns_url + '/' + self.hecke_orbit_label
        if self.sato_tate_group:
            res.append((r'Sato-Tate group \({}\)'.format(get_name(self.sato_tate_group)[0]),
                        '/SatoTateGroup/' + self.sato_tate_group))
        if self.embedding_label is not None:
            res.append(('Newform orbit ' + self.label, nf_url))
            if (self.dual_label is not None and
                    self.dual_label != self.embedding_label):
                dlabel = self.label + '.' + self.dual_label
                d_url = nf_url + '/' + self.dual_label.replace('.','/') + '/'
                res.append(('Dual form ' + dlabel, d_url))
            if self.embedded_minimal_twist is not None and self.embedded_minimal_twist != self.label + '.' + self.embedding_label:
                minimal_twist_url = cmf_base + self.embedded_minimal_twist.replace('.','/') + '/'
                res.append(('Minimal twist ' + self.embedded_minimal_twist, minimal_twist_url))
            if self.dim == 1:
                # use the Galois orbits friends for the unique embedding
                related_objects = self.related_objects
            else:
                m = self.embedding_from_embedding_label(self.embedding_label)
                try:
                    if self.embedded_related_objects:
                        related_objects = self.embedded_related_objects[int(m) - 1]
                    else:
                        related_objects = []
                except TypeError:
                    related_objects = self.related_objects
        else:
            if self.minimal_twist is not None and self.minimal_twist != self.label:
                minimal_twist_url = cmf_base + self.minimal_twist.replace('.','/') + '/'
                res.append(('Minimal twist ' + self.minimal_twist, minimal_twist_url))
            related_objects = self.related_objects
        res += names_and_urls(related_objects)

        # finally L-functions
        if self.weight <= 200:
            if (self.dim==1 or not self.embedding_label) and db.lfunc_instances.exists({'url': nf_url[1:]}):
                res.append(('L-function ' + self.label, '/L' + nf_url))
            if self.embedding_label is None and len(self.conrey_indexes)*self.rel_dim > 50:
                res = [list(map(str, elt)) for elt in res]
                # properties_lfun(initialFriends, label, nf_url, conrey_indexes, rel_dim)
                return '<script id="properties_script">$( document ).ready(function() {properties_lfun(%r, %r, %r, %r, %r)}); </script>' %  (res, str(self.label), str(nf_url), self.conrey_indexes, self.rel_dim)
            if self.dim > 1:
                for lfun_label in self.embedding_labels:
                    lfun_url =  '/L' + cmf_base + lfun_label.replace('.','/')
                    res.append(('L-function ' + lfun_label, lfun_url))

        return res


    @property
    def downloads(self):
        downloads = []
        if self.embedding_label is None:
            if self.hecke_cutters or self.has_exact_qexp:
                downloads.append(('Modular form to Magma', url_for('.download_newform_to_magma', label=self.label)))
            if self.has_exact_qexp:
                downloads.append(('q-expansion to Sage', url_for('.download_qexp', label=self.label)))
            downloads.append(('Trace form to text', url_for('.download_traces', label=self.label)))
            if self.has_complex_qexp:
                downloads.append(('Embeddings to text', url_for('.download_cc_data', label=self.label)))
                downloads.append(('Satake angles to text', url_for('.download_satake_angles', label=self.label)))
            downloads.append(('All stored data to text', url_for('.download_newform', label=self.label)))
        else:
            downloads.append(('Coefficient data to text', url_for('.download_embedded_newform', label='%s.%s'%(self.label, self.embedding_label))))
        return downloads

    @lazy_attribute
    def an_cc_bound(self):
        if self.level <= 1000:
            return 1000
        elif self.level <= 4000:
            return 2000
        else:
            return 3000

    @lazy_attribute
    def primes_cc_bound(self):
        return prime_pi(self.an_cc_bound)


    @lazy_attribute
    def one_column_display(self):
        if self.embedding_m:
            an = self.cc_data[self.embedding_m]['an_normalized'].values()
            return all([x == 0 or y == 0 for x, y in an])


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
        an_formats = ['embed','analytic_embed', None]
        angles_formats = ['satake','satake_angle', None]
        analytic_shift_formats = ['embed', None]
        cc_proj = ['conrey_index','embedding_index','embedding_m','embedding_root_real','embedding_root_imag']
        format = info.get('format')
        query = {'hecke_orbit_code':self.hecke_orbit_code}


        # deal with m
        if self.embedding_label is None:
            m = info.get('m','1-%s'%(min(self.dim,20)))
            if '.' in m:
                m = re.sub(r'\d+\.\d+', self.embedding_from_embedding_label, m)
            CC_m = info['CC_m'] if 'CC_m' in info else integer_options(m)
            CC_m = sorted(set(CC_m))
            # if it is a range
            if len(CC_m) - 1 == CC_m[-1] - CC_m[0]:
                query['embedding_m'] = {'$gte':CC_m[0], '$lte':CC_m[-1]}
            else:
                query['embedding_m'] = {'$in': CC_m}
            self.embedding_m = None
        else:
            self.embedding_m = int(info['CC_m'][0])
            cc_proj.extend(['dual_conrey_index', 'dual_embedding_index'])
            query = {'label' : self.label + '.' + self.embedding_label}

        if format is None and 'CC_n' not in info:
            # for download
            CC_n = (1, self.an_cc_bound)
        else:
            n = info.get('n','1-10')
            CC_n = info['CC_n'] if 'CC_n' in info else integer_options(n)
            # convert CC_n to an interval in [1,an_bound]
            CC_n = ( max(1, min(CC_n)), min(self.an_cc_bound, max(CC_n)) )
        an_keys = (CC_n[0]-1, CC_n[1])
        # extra 5 primes in case we hit too many bad primes
        angles_keys = (
                bisect.bisect_left(primes_for_angles, CC_n[0]),
                min(bisect.bisect_right(primes_for_angles, CC_n[1]) + 5,
                    self.primes_cc_bound)
                )
        an_projection = 'an_normalized[%d:%d]' % an_keys
        angles_projection = 'angles[%d:%d]' % angles_keys
        if format in an_formats:
            cc_proj.append(an_projection)
        if format in angles_formats:
            cc_proj.append(angles_projection)

        cc_data= list(db.mf_hecke_cc.search(query, projection = cc_proj))
        if not cc_data:
            self.has_complex_qexp = False
        else:
            self.has_complex_qexp = True
            self.cc_data = {}
            for embedded_mf in cc_data:
                if format in an_formats:
                    an_normalized = embedded_mf.pop(an_projection)
                    # we don't store a_0, thus the +1
                    embedded_mf['an_normalized'] = {i: [float(x), float(y)] for i, (x, y) in enumerate(an_normalized, an_keys[0] + 1)}
                if format in angles_formats:
                    embedded_mf['angles'] = {primes_for_angles[i]: theta for i, theta in enumerate(embedded_mf.pop(angles_projection), angles_keys[0])}
                self.cc_data[embedded_mf.pop('embedding_m')] = embedded_mf
            if format in analytic_shift_formats:
                self.analytic_shift = {i: RR(i)**((ZZ(self.weight)-1)/2) for i in list(self.cc_data.values())[0]['an_normalized']}
            if format in angles_formats:
                self.character_values = defaultdict(list)
                G = DirichletGroup_conrey(self.level)
                chars = [DirichletCharacter_conrey(G, char) for char in self.conrey_indexes]
                for p in list(self.cc_data.values())[0]['angles']:
                    if p.divides(self.level):
                        self.character_values[p] = None
                        continue
                    for chi in chars:
                        c = chi.logvalue(p) * self.char_order
                        angle = float(c / self.char_order)
                        value = CDF(0,2*CDF.pi()*angle).exp()
                        self.character_values[p].append((angle, value))

        if self.embedding_m is not None:
            m = self.embedding_m
            dci = self.cc_data[m].get('dual_conrey_index')
            dei = self.cc_data[m].get('dual_embedding_index')
            self.dual_label = "%s.%s" % (dci, dei)
            x = self.cc_data[m].get('embedding_root_real')
            y = self.cc_data[m].get('embedding_root_imag')
            if x is None or y is None:
                self.embedding_root = None
            else:
                self.embedding_root = display_complex(x, y, 6, method='round', try_halfinteger=False)

    @staticmethod
    def by_label(label, embedding_label = None):
        if not valid_label(label):
            raise ValueError("Invalid newform label %s." % label)

        data = db.mf_newforms.lookup(label)
        if data is None:
            # Display a different error if Nk^2 is too large
            N, k, a, x = label.split('.')
            Nk2 = int(N) * int(k) * int(k)
            nontriv = not (a == 'a')
            from .main import Nk2_bound
            if Nk2 > Nk2_bound(nontriv = nontriv):
                nontriv_text = "non trivial" if nontriv else "trivial"
                raise ValueError(r"Level and weight too large.  The product \(Nk^2 = %s\) is larger than the currently computed threshold of \(%s\) for %s character."%(Nk2, Nk2_bound(nontriv = nontriv), nontriv_text) )
            raise ValueError("Newform %s not found" % label)
        return WebNewform(data, embedding_label = embedding_label)


    @property
    def projective_image_latex(self):
        if self.projective_image:
            return '%s_{%s}' % (self.projective_image[:1], self.projective_image[1:])

    def projective_image_knowl(self):
        if self.projective_image:
            gp_name = "C2^2" if self.projective_image == "D2" else ( "S3" if self.projective_image == "D3" else self.projective_image )
            gp_label = db.gps_small.lucky({'name':gp_name},'label')
            gp_display = '\\(' + self.projective_image_latex + '\\)'
            return gp_display if gp_label is None else small_group_label_display_knowl(gp_label,gp_display)

    def field_display(self):
        """
        This function is used to display the coefficient field.

        When the relative dimension is 1 (and dimension larger than 2),
        it displays the coefficient field as a cyclotomic field.  Otherwise,
        if the field is in the lmfdb it displays it using the standard number
        field knowl; if not it uses a dynamic knowl showing the coefficient field.
        """
        # display the coefficient field
        m = self.field_poly_root_of_unity
        d = self.dim
        if m and (d != 2 or self.hecke_ring_cyclotomic_generator):
            return cyc_display(m, d, self.field_poly_is_real_cyclotomic)
        else:
            return field_display_gen(self.nf_label, self.field_poly, self.field_disc_factorization)

    @property
    def artin_field_display(self):
        """
        For weight 1 forms, displays the Artin field.
        """
        label, poly = self.artin_field_label, self.artin_field
        return field_display_gen(label, poly)

    @property
    def projective_field_display(self):
        """
        For weight 1 forms, displays the kernel of the projective Galois rep.
        """
        label, poly = self.projective_field_label, self.projective_field
        return field_display_gen(label, poly)

    @property
    def artin_image_display(self):
        if self.artin_image:
            pretty = db.gps_small.lookup(self.artin_image, projection = 'pretty')
            return pretty if pretty else self.artin_image
        return None

    def artin_image_knowl(self):
        return small_group_label_display_knowl(self.artin_image)

    def rm_and_cm_field_knowl(self, sign=1):
        if self.self_twist_discs:
            disc = [ d for d in self.self_twist_discs if sign*d > 0 ]
            return ' and '.join( map(quad_field_knowl, disc) )
        else:
            return ''

    def cyc_display(self, m=None, real_sub=False):
        r"""
        Used to display cyclotomic fields and their real subfields.

        INPUT:

        - ``m`` -- if ``None``, m is set to the order of the character
        (or the order of the field generator when the defining polynomial
        is cyclotomic and the relative dimension is 1).
        - ``real_sub`` -- If ``True``, will display the real subfield instead.

        OUTPUT:

        A string or knowl showing the cyclotomic field Q(\zeta_m) or Q(\zeta_m)^+.
        """
        if m is None:
            m = self.char_order
            d = self.char_degree
            if self.dim == self.char_degree and self.field_poly_root_of_unity:
                # the relative dimension is 1 and the coefficient field is cyclotomic
                # We want to display it using the appropriate root of unity
                m = self.field_poly_root_of_unity
        else:
            d = self.dim
        return cyc_display(m, d, real_sub)

    def ring_display(self):
        if self.dim == 1:
            return r'\(\Z\)'
        nbound = self.hecke_ring_generator_nbound
        if nbound == 2:
            return r'\(\Z[a_1, a_2]\)'
        elif nbound == 3:
            return r'\(\Z[a_1, a_2, a_3]\)'
        else:
            return r'\(\Z[a_1, \ldots, a_{%s}]\)' % nbound

    @property
    def hecke_ring_index_factored(self):
        if self.hecke_ring_index_factorization is not None:
            return r"\( %s \)" % factor_base_factorization_latex(self.hecke_ring_index_factorization)
        return None

    def ring_index_display(self):
        fac = self.hecke_ring_index_factored
        if self.hecke_ring_index_proved:
            return fac
        else:
            return r'multiple of %s' % fac

    def twist_minimal_display(self):
        if self.is_twist_minimal is None:
            return 'unknown'
        if self.is_twist_minimal:
            return r'yes'
        else:
            return r'no (minimal twist has level %s)'%(self.minimal_twist.split('.')[0]) if self.minimal_twist else r'no'

    def display_newspace(self):
        s = r'\(S_{%s}^{\mathrm{new}}('
        if self.char_order == 1:
            s += r'\Gamma_0(%s))\)'
        else:
            s += r'%s, [\chi])\)'
        return s%(self.weight, self.level)

    def display_hecke_cutters(self):
        polynomials = [bigpoly_knowl(F, var='T%s'%p) for p,F in self.hecke_cutters]
        title = 'linear operator'
        if len(polynomials) > 1:
            title += 's'
        knowl = display_knowl('cmf.hecke_cutter', title=title)
        desc = "<p>This %s can be constructed as the "%(display_knowl('cmf.newform_subspace','newform subspace'))
        if len(polynomials) > 1:
            desc += "intersection of the kernels of the following %s acting on %s:</p>\n<table>"
            desc = desc % (knowl, self.display_newspace())
            desc += "\n".join("<tr><td>%s</td></tr>" % F for F in polynomials) + "\n</table>"
        elif len(polynomials) == 1:
            desc += "kernel of the %s %s acting on %s."
            desc = desc % (knowl, polynomials[0], self.display_newspace())
        else:
            desc = r"<p>This %s is the entire %s %s.</p> "%(display_knowl('cmf.newform_subspace','newform subspace'),
                                                          display_knowl('cmf.newspace','newspace'),self.display_newspace())
        return desc

    def defining_polynomial(self):
        if self.field_poly:
            return web_latex_poly(self.field_poly, superscript=True)
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
        paren = ('+' in num or '-' in num)
        if den == 1:
            return num
        elif den < 10**8:
            if paren:
                return r"\((\)%s\()/%s\)" % (num, den)
            else:
                return r"%s\(/%s\)" % (num, den)
        else:
            if paren:
                return r"\((\)%s\()/%s\)" % (num, make_bigint(web_latex(den, enclose=False)))
            else:
                return r"%s\(/%s\)" % (num, make_bigint(web_latex(den, enclose=False)))

    @property
    def _nu_latex(self):
        if self.field_poly_is_cyclotomic:
            if self.field_poly_root_of_unity == 4:
                return 'i'
            else:
                return r"\zeta_{%s}" % self.field_poly_root_of_unity
        else:
            return r"\nu"

    @property
    def _nu_var(self):
        if self.field_poly_is_cyclotomic:
            if self.field_poly_root_of_unity == 4:
                return 'i'
            else:
                return r"zeta%s" % self.field_poly_root_of_unity
        else:
            return r"nu"

    @property
    def _zeta_print(self):
        # This will often be the same as _nu_var, since self.hecke_ring_cyclotomic_generator
        # is often the same as field_poly_root_of_unity
        m = self.hecke_ring_cyclotomic_generator
        if m == 4:
            return 'i'
        elif m is None or m == 0:
            raise ValueError
        else:
            return r"zeta%s" % m

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
                num = web_latex_poly(num, self._nu_latex, superscript=True)
            else:
                num = web_latex(coeff_to_poly(num, self._nu_var))
            betai = r'\(\beta_{%s}\)'%i
            basis.append((betai, self._make_frac(num, den)))
        return self._make_table(basis)

    def _order_basis_inverse(self):
        basis = [(r'\(1\)', r'\(\beta_0\)')]
        for i, (num, den) in enumerate(zip(self.hecke_ring_inverse_numerators[1:], self.hecke_ring_inverse_denominators[1:])):
            num = web_latex_poly(num, r'\beta', superscript=False)
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
        elif self.hecke_ring_power_basis and self.field_poly_is_cyclotomic:
            return r'a primitive root of unity \(\zeta_{%s}\)' % self.field_poly_root_of_unity
        elif self.dim == 2:
            c, b, a = map(ZZ, self.field_poly)
            D = b**2 - 4*a*c
            d = D.squarefree_part()
            s = (D//d).isqrt()
            if self.hecke_ring_power_basis:
                k, l = ZZ(0), ZZ(1)
            else:
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

    def order_gen_below(self):
        m = self.field_poly_root_of_unity
        if m == 0:
            return r" in terms of a root \(\nu\) of %s" % self.defining_polynomial()
        elif self.field_poly_is_real_cyclotomic:
            return r" in terms of \(\nu = \zeta_{%s} + \zeta_{%s}^{-1}\)" % (m, m)
        else:
            return ""

    @property
    def _PrintRing(self):
        # the order='negdeglex' assures constant terms come first
        # univariate polynomial rings don't support order,
        # we work around it by introducing a dummy variable
        m = self.hecke_ring_cyclotomic_generator
        if m is not None and m != 0:
            return PolynomialRing(QQ, [self._zeta_print, 'dummy'], order = 'negdeglex')
        elif self.single_generator:
            if self.hecke_ring_power_basis and self.field_poly_is_cyclotomic:
                return PolynomialRing(QQ, [self._nu_var, 'dummy'], order = 'negdeglex')
            else:
                return PolynomialRing(QQ, ['beta', 'dummy'], order = 'negdeglex')
        else:
            return PolynomialRing(QQ, ['beta%s' % i for i in range(1, self.dim)], order = 'negdeglex')

    @property
    def _Rgens(self):
        R = self._PrintRing
        if self.single_generator:
            beta = R.gen(0)
            return [beta**i for i in range(0, self.dim)]
        else:
            return [1] + list(R.gens())

    def _elt(self, data):
        """
        Returns an element of a polynomial ring whose print representation
        agrees with the specified data
        """
        m = self.hecke_ring_cyclotomic_generator
        if m is None or m == 0:
            # normal representation: as a list of coefficients
            return sum(c * gen for c, gen in zip(data, self._Rgens))
        else:
            # sum of powers of zeta_m
            zeta = self._PrintRing.gen(0)
            return sum(c * zeta**e for c,e in data)

    @property
    def dual_link(self):
        dlabel = self.label + '.' + self.dual_label
        d_url = '/ModularForm/GL2/Q/holomorphic/' + dlabel.replace('.','/') + '/'
        return '<a href="%s">%s</a>'%(d_url, dlabel)

    @property
    def char_orbit_link(self):
        label = '%s.%s' % (self.level, self.char_orbit_label)
        return display_knowl('character.dirichlet.orbit_data', title=label, kwargs={'label':label})

    @property
    def char_conrey_link(self):
        if self.embedding_label is None:
            raise ValueError
        label = '%s.%s' % (self.level, self.embedding_label.split('.')[0])
        return display_knowl('character.dirichlet.data', title=label, kwargs={'label':label})

    def display_character(self):
        if self.char_order == 1:
            ord_deg_min = " (trivial)"
        else:
            ord_knowl = display_knowl('character.dirichlet.order', title='order')
            deg_knowl = display_knowl('character.dirichlet.degree', title='degree')
            min_knowl = ('not ' if not self.char_is_minimal else '') + display_knowl('character.dirichlet.minimal', title='minimal')
            ord_deg_min = r" (of %s \(%d\), %s \(%d\), %s)" % (ord_knowl, self.char_order, deg_knowl, self.char_degree, min_knowl)
        return self.char_orbit_link + ord_deg_min

    def display_character_values(self):
        gens = [r'      <td class="dark border-right border-bottom">\(n\)</td>']
        vals = [r'      <td class="dark border-right">\(\chi(n)\)</td>']
        for j, (g, chi_g) in enumerate(self.hecke_ring_character_values):
            if self.embedding_label is None:
                term = self._elt(chi_g)
                latexterm = latex(term)
            else:
                order = self.hecke_ring_cyclotomic_generator
                d = gcd(order, chi_g)
                order = order // d
                chi_g = chi_g // d
                if order == 1:
                    latexterm = '1'
                elif order == 2:
                    latexterm = '-1'
                else:
                    latexterm = r'e\left(\frac{%s}{%s}\right)'%(chi_g, order)
            color = "dark" if j%2 else "light"
            gens.append(r'      <td class="%s border-bottom">\(%s\)</td>'%(color, g))
            vals.append(r'      <td class="%s">\(%s\)</td>'%(color, latexterm))
        return '    <tr>\n%s    </tr>\n    <tr>\n%s    </tr>'%('\n'.join(gens), '\n'.join(vals))

    def display_inner_twists(self):
        twists = ['<table class="ntdata">', '<thead>', '  <tr>',
                  th_wrap('character.dirichlet.galois_orbit_label', 'Char'),
                  th_wrap('character.dirichlet.parity', 'Parity'),
                  th_wrap('character.dirichlet.order', 'Ord'),
                  th_wrap('cmf.inner_twist_multiplicity', 'Mult'),
                  th_wrap('cmf.self_twist_field', 'Type'),
                  '  </tr>', '</thead>', '<tbody>']
        self_twists = sorted([r for r in self.twists if r['self_twist_disc']], key = lambda r: r['conductor'])
        other_inner_twists = sorted([r for r in self.twists if r['target_label'] == self.label and not r['self_twist_disc']], key = lambda r: r['conductor'])
        inner_twists = self_twists + other_inner_twists
        for r in inner_twists:
            char_link = display_knowl('character.dirichlet.orbit_data', title=r['twisting_char_label'], kwargs={'label':r['twisting_char_label']})
            d = r['self_twist_disc']
            stdisc = 'inner' if not d else ('trivial' if d==1 else ('CM by ' if d < 0 else 'RM by ') + quad_field_knowl(d))
            twists.append('  <tr>')
            twists.extend([td_wrapl(char_link), td_wrapl(parity_text(r['parity'])), td_wrapr(r['order']), td_wrapr(r['multiplicity']), td_wrapl(stdisc)])
            twists.append('  </tr>')
        twists.extend(['</tbody>', '</table>'])
        return '\n'.join(twists)

    def display_hecke_char_polys(self, num_disp = 5):
        return display_hecke_polys([self.label], num_disp)
      
    def display_twists(self):
        if not self.twists:
            return '<p>Twists of this newform have not been computed.</p>'
        def twist_type(r):
            d = r['self_twist_disc']
            return '' if r['target_label'] != self.label else ('inner' if not d else ('trivial' if d == 1 else ('CM' if d < 0 else 'RM')))

        twists1 = ['<table class="ntdata" style="float: left">', '<thead>',
                   '<tr><th colspan=8>&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;By %s</th></tr>'% display_knowl('cmf.twist','twisting character orbit'), '<tr>',
                  th_wrap('character.dirichlet.galois_orbit_label', 'Char'),
                  th_wrap('character.dirichlet.parity', 'Parity'),
                  th_wrap('character.dirichlet.order', 'Ord'),
                  th_wrap('cmf.twist_multiplicity', 'Mult'),
                  th_wrap('cmf.self_twist_field', 'Type'),
                  th_wrap('cmf.twist', 'Twist'),
                  th_wrap('cmf.twist_minimal', 'Min'),
                  th_wrap('cmf.dimension', 'Dim'),
                  '</tr>', '</thead>', '<tbody>']

        for r in  sorted(self.twists, key = lambda x : [x['conductor'],x['twisting_char_orbit'],x['target_level'],x['target_char_orbit'],x['target_hecke_orbit']]):
            minimality = '&check;' if r['target_label'] == self.minimal_twist else 'yes' if r['target_is_minimal'] else ''
            char_link = display_knowl('character.dirichlet.orbit_data', title=r['twisting_char_label'], kwargs={'label':r['twisting_char_label']})
            target_link = '<a href="%s">%s</a>'%('/ModularForm/GL2/Q/holomorphic/' + r['target_label'].replace('.','/'),r['target_label'])
            twists1.append('<tr>')
            twists1.extend([td_wrapl(char_link), td_wrapl(parity_text(r['parity'])), td_wrapr(r['order']), td_wrapr(r['multiplicity']), td_wrapl(twist_type(r)),
                            td_wrapl(target_link), td_wrapc(minimality), td_wrapr(r['target_dim'])])
            twists1.append('</tr>')
        twists1.extend(['</tbody>', '</table>'])

        twists2 = ['<table class="ntdata" style="float: left">', '<thead>',
                   '<tr><th colspan=8>&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;By %s</th></tr>'% display_knowl('cmf.twist','twisted newform orbit'), '<tr>',
                  th_wrap('cmf.twist', 'Twist'),
                  th_wrap('cmf.twist_minimal', 'Min'),
                  th_wrap('cmf.dimension', 'Dim'),
                  th_wrap('character.dirichlet.galois_orbit_label', 'Char'),
                  th_wrap('character.dirichlet.parity', 'Parity'),
                  th_wrap('character.dirichlet.order', 'Ord'),
                  th_wrap('cmf.twist_multiplicity', 'Mult'),
                  th_wrap('cmf.self_twist_field', 'Type'),
                  '</tr>', '</thead>', '<tbody>']
        for r in sorted(self.twists, key = lambda x : [x['target_level'],x['target_char_orbit'],x['target_hecke_orbit'],x['conductor'],x['twisting_char_orbit']]):
            minimality = '&check;' if r['target_label'] == self.minimal_twist else 'yes' if r['target_is_minimal'] else ''
            char_link = display_knowl('character.dirichlet.orbit_data', title=r['twisting_char_label'], kwargs={'label':r['twisting_char_label']})
            target_link = '<a href="%s">%s</a>'%('/ModularForm/GL2/Q/holomorphic/' + r['target_label'].replace('.','/'),r['target_label'])
            twists2.append('<tr>')
            twists2.extend([td_wrapl(target_link), td_wrapc(minimality), td_wrapr(r['target_dim']),
                            td_wrapl(char_link), td_wrapl(parity_text(r['parity'])), td_wrapr(r['order']), td_wrapr(r['multiplicity']), td_wrapl(twist_type(r))])
            twists2.append('</tr>')
        twists2.extend(['</tbody>', '</table>'])

        return '\n'.join(twists1) + '\n<div style="float: left">&emsp;&emsp;&emsp;&emsp;</div>\n' + '\n'.join(twists2) + '\n<br clear="all" />\n'

    def display_embedded_twists(self):
        if not self.embedded_twists:
            return '<p>Twists of this newform have not been computed.</p>'
        if not self.embedding_label:
            return '' # we should only be called when embedding_label is set
        def twist_type(r):
            if r['target_hecke_orbit_code'] != self.hecke_orbit_code:
                return ''
            if r['twisting_char_label'] == '1.1':
                return 'trivial'
            if r['target_label'] != self.label + '.' + self.embedding_label:
                return 'inner'
            else:
                return 'CM' if r['parity'] < 0 else 'RM'
        def revcode(x):    # reverse encoding of newform orbit N.k.o.i for sorting (so N is in the high 24 bits not the low 24 bits)
            return ((x&((1<<24)-1))<<40) | (((x>>24)&((1<<12)-1))<<28) | (((x>>36)&((1<<16)-1))<<12) | (x>>52)

        twists1 = ['<table class="ntdata" style="float: left">', '<thead>',
                   '<tr><th colspan=8>&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;By %s</th></tr>'% display_knowl('cmf.twist','twisting character'), '<tr>',
                  th_wrap('character.dirichlet.conrey', 'Char'),
                  th_wrap('character.dirichlet.parity', 'Parity'),
                  th_wrap('character.dirichlet.order', 'Ord'),
                  th_wrap('cmf.self_twist_field', 'Type'),
                  th_wrap('cmf.twist', 'Twist'),
                  th_wrap('cmf.twist_minimality', 'Min'),
                  th_wrap('cmf.dimension', 'Dim'),
                  '</tr>', '</thead>', '<tbody>']

        for r in sorted(self.embedded_twists, key = lambda x : [x['conductor'],x['twisting_conrey_index'],revcode(x['target_hecke_orbit_code']),x['target_conrey_index'],x['target_embedding_index']]):
            minimality = '&check;' if r['target_label'] == self.embedded_minimal_twist else 'yes' if r['target_is_minimal'] else ''
            char_link = display_knowl('character.dirichlet.data', title=r['twisting_char_label'], kwargs={'label':r['twisting_char_label']})
            target_link = '<a href="%s">%s</a>'%('/ModularForm/GL2/Q/holomorphic/' + r['target_label'].replace('.','/'),r['target_label'])
            twists1.append('<tr>')
            twists1.extend([td_wrapl(char_link), td_wrapl(parity_text(r['parity'])), td_wrapr(r['order']), td_wrapl(twist_type(r)),
                            td_wrapl(target_link), td_wrapc(minimality), td_wrapr(r['target_dim'])])
            twists1.append('</tr>')
        twists1.extend(['</tbody>', '</table>'])

        twists2 = ['<table class="ntdata" style="float: left">', '<thead>',
                   '<tr><th colspan=8>&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;By %s</th></tr>'% display_knowl('cmf.twist','twisted newform'), '<tr>',
                  th_wrap('cmf.twist', 'Twist'),
                  th_wrap('cmf.twist_minimality', 'Min'),
                  th_wrap('cmf.dimension', 'Dim'),
                  th_wrap('character.dirichlet.conrey', 'Char'),
                  th_wrap('character.dirichlet.parity', 'Parity'),
                  th_wrap('character.dirichlet.order', 'Ord'),
                  th_wrap('cmf.self_twist_field', 'Type'),
                  '</tr>', '</thead>', '<tbody>']

        for r in sorted(self.embedded_twists, key = lambda x : [revcode(x['target_hecke_orbit_code']),x['target_conrey_index'],x['target_embedding_index'],x['conductor'],x['twisting_conrey_index']]):
            minimality = '&check;' if r['target_label'] == self.embedded_minimal_twist else 'yes' if r['target_is_minimal'] else ''
            char_link = display_knowl('character.dirichlet.orbit_data', title=r['twisting_char_label'], kwargs={'label':r['twisting_char_label']})
            target_link = '<a href="%s">%s</a>'%('/ModularForm/GL2/Q/holomorphic/' + r['target_label'].replace('.','/'),r['target_label'])
            twists2.append('<tr>')
            twists2.extend([td_wrapl(target_link), td_wrapc(minimality), td_wrapr(r['target_dim']),
                            td_wrapl(char_link), td_wrapl(parity_text(r['parity'])), td_wrapr(r['order']), td_wrapl(twist_type(r))])
            twists2.append('</tr>')
        twists2.extend(['</tbody>', '</table>'])

        return '\n'.join(twists1) + '\n<div style="float: left">&emsp;&emsp;&emsp;&emsp;</div>\n' + '\n'.join(twists2) + '\n<br clear="all" />\n'

    def sato_tate_display(self):
        if self.sato_tate_group:
            return st_link(self.sato_tate_group)
        else:
            return ''

    def eigs_as_seqseq_to_qexp(self, prec_max):
        # Takes a sequence of sequence of integers (or pairs of integers in the hecke_ring_cyclotomic_generator != 0 case) and returns a string for the corresponding q expansion
        # For example, eigs_as_seqseq_to_qexp([[0,0],[1,3]]) returns "\((1+3\beta_{1})q\)\(+O(q^2)\)"
        prec = min(self.qexp_prec, prec_max)
        if prec == 0:
            return 'O(1)'
        eigseq = self.qexp[:prec]
        use_knowl = too_big(eigseq, 10**24)
        s = ''
        for j in range(len(eigseq)):
            term = self._elt(eigseq[j])
            if term != 0:
                latexterm = latex(term)
                if use_knowl:
                    latexterm = make_bigint(latexterm)
                if term.number_of_terms() > 1:
                    latexterm = r"(" +  latexterm + r")"
                if j > 0:
                    if term == 1:
                        latexterm = ''
                    elif term == -1:
                        latexterm = '-'
                    if j == 1:
                        latexterm += ' q'
                    else:
                        latexterm += ' q^{%d}' % j
                if s != '' and latexterm[0] != '-':
                    latexterm = '+' + latexterm
                s += '' + latexterm + ' '
        # Work around bug in Sage's latex
        s = s.replace('betaq', 'beta q')
        return r'\(' + s + r'+O(q^{%d})\)' % prec

    def q_expansion_cc(self, prec_max):
        eigseq = self.cc_data[self.embedding_m]['an_normalized']
        prec = min(max(eigseq.keys()) + 1, prec_max)
        if prec == 0:
            return r'\(O(1)\)'
        s = r'\(q'
        for j in range(2, prec):
            term = eigseq[j]
            latexterm = display_complex(term[0]*self.analytic_shift[j], term[1]*self.analytic_shift[j], 6, method = "round", parenthesis = True, try_halfinteger=False)
            if latexterm != '0':
                if latexterm == '1':
                    latexterm = ''
                elif latexterm == '-1':
                    latexterm = '-'
                latexterm += ' q^{%d}' % j
                if s != '' and latexterm[0] != '-':
                    latexterm = '+' + latexterm
                s += '' + latexterm + ' '
        # Work around bug in Sage's latex
        s = s.replace('betaq', 'beta q')
        return s + r'+O(q^{%d})\)' % prec


    def q_expansion(self, prec_max=10):
        # Display the q-expansion, truncating to precision prec_max.  Will be inside \( \).
        if self.embedding_label:
            return self.q_expansion_cc(prec_max)
        elif self.has_exact_qexp:
            prec = min(self.qexp_prec, prec_max)
            if self.dim == 1:
                s = web_latex(coeff_to_power_series([self.qexp[n][0] for n in range(prec)],prec=prec),enclose=True)
            else:
                s = self.eigs_as_seqseq_to_qexp(prec)
            return s
        else:
            return coeff_to_power_series([0,1], prec=2)._latex_()

    def trace_expansion(self, prec_max=10):
        prec = min(self.texp_prec, prec_max)
        s = web_latex(coeff_to_power_series(self.texp[:prec], prec=prec), enclose=True)
        if too_big(self.texp[:prec], 10**24):
            s = make_bigint(s)
        return s

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
        return "{c}.{e}".format(c=self.cc_data[m]['conrey_index'], e=((m-1)%self.rel_dim)+1)
    def embedded_mf_link(self, m):
        # Given an embedding number, return the Conrey label for the restriction of that embedding to the cyclotomic field
        return '/ModularForm/GL2/Q/holomorphic/' + self.label.replace('.','/') + "/{c}/{e}/".format(c=self.cc_data[m]['conrey_index'], e=((m-1)%self.rel_dim)+1)

    def embedding_from_embedding_label(self, elabel):
        if not isinstance(elabel, string_types): # match object
            elabel = elabel.group(0)
        c, e = map(int, elabel.split('.'))
        if e <= 0 or e > self.rel_dim:
            raise ValueError("Invalid embedding")
        return str(self.rel_dim * self.conrey_indexes.index(c) + e)

    def embedded_title(self, m):
        return "Embedded newform %s.%s"%(self.label, self.conrey_from_embedding(m))

    def _display_re(self, x, prec, method='round', extra_truncation_digits=3):
        res = display_float(x, prec,
                method=method,
                extra_truncation_digits=extra_truncation_digits,
                try_halfinteger=False)
        if res == "0":
            return ""
        else:
            return res.replace('-','&minus;')

    def _display_im(self, y, prec, method='round', extra_truncation_digits=3):
        res = display_float(y, prec,
                method=method,
                extra_truncation_digits=extra_truncation_digits,
                try_halfinteger=False)
        if res == "0":
            return ""
        elif res == "1":
            res = ""
        return r"%s<em>i</em>"%(res)

    def _display_op(self, x, y, prec, extra_truncation_digits=3):
        xiszero = abs(x) < 10**(-prec + extra_truncation_digits)
        yiszero = abs(y) < 10**(-prec + extra_truncation_digits)
        if xiszero and yiszero:
            return r"0"
        elif yiszero or (xiszero and y > 0):
            return ""
        elif y > 0:
            return r"+"
        elif y < 0:
            return r"&minus;"

    #    Return the value of the ``m``th embedding on a specified input.
    #    Should only be used when all of the entries in this column are either real
    #    or imaginary.

    #    INPUT:

    #    - ``m`` -- an integer, specifying which embedding to use.
    #    - ``n`` -- a positive integer, specifying which a_n.  If None, returns the image of
    #        the generator of the field (i.e. the root corresponding to this embedding).
    #    - ``prec`` -- the precision to display floating point values
    #    - ``format`` -- either ``embed`` or ``analytic_embed``.  In the second case, divide by n^((k-1)/2).

    def embedding_re(self, m, n=None, prec=6, format='embed'):
        if n is None:
            x = self.cc_data[m].get('embedding_root_real', None)
            if x is None:
                return '' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an_normalized'][n]
            if format == 'embed':
                x *= self.analytic_shift[n]
        return self._display_re(x, prec, method='round')

    def embedding_im(self, m, n=None, prec=6, format='embed'):
        if n is None:
            y = self.cc_data[m].get('embedding_root_imag', None)
            if y is None:
                return '' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an_normalized'][n]
            if format == 'embed':
                y *= self.analytic_shift[n]
        return self._display_im(abs(y), prec, method='round') # sign is handled in embedding_op

    def embedding_op(self, m, n=None, prec=6, format='embed'):
        if n is None:
            x = self.cc_data[m].get('embedding_root_real', None)
            y = self.cc_data[m].get('embedding_root_imag', None)
            if x is None or y is None:
                return '?' # we should never see this if we have an exact qexp
        else:
            x, y = self.cc_data[m]['an_normalized'][n]
            # we might decide to not display an operator if normalized value is too small
            if format == 'embed':
                x *= self.analytic_shift[n]
                y *= self.analytic_shift[n]
        return self._display_op(x, y, prec)

    def embedding(self,  m, n=None, prec=6, format='embed'):
        return " ".join([ elt(m, n, prec, format)
            for elt in [self.embedding_re, self.embedding_op, self.embedding_im]
            ])


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
            return " ".join([ elt(m, p, i, prec)
                for elt in [self.satake_re, self.satake_op, self.satake_im]
                ])

        else:
            return self.satake_angle(m, p, i, prec)

    @cached_method
    def satake_angle(self, m, p, i, prec=6):
        if not self.character_values[p]:
            # bad prime
            return ''
        theta = self._get_theta(m, p, i)
        s = display_float(2*theta, prec, method='round')
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
        if not self.character_values[p]:
            # bad prime
            return ''
        return self._display_re(self._get_alpha(m, p, i).real(), prec)

    def satake_im(self, m, p, i, prec=6):
        if not self.character_values[p]:
            # bad prime
            return ''
        return self._display_im(abs(self._get_alpha(m, p, i).imag()), prec)

    def satake_op(self, m, p, i, prec=6):
        if not self.character_values[p]:
            # bad prime
            return ''
        alpha = self._get_alpha(m, p, i)
        return self._display_op(alpha.real(), alpha.imag(), prec)

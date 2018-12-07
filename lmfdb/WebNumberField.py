# -*- coding: utf-8 -*-
import sage
from sage.all import gcd, Set, ZZ, is_even, is_odd, euler_phi, CyclotomicField, gap, AbelianGroup, QQ, gp, NumberField, PolynomialRing, latex, pari, valuation
import yaml, os
from sage.misc.cachefunc import cached_function
from lmfdb.utils import make_logger, web_latex, coeff_to_poly, pol_to_html, display_multiset
from flask import url_for
from collections import Counter
from lmfdb.transitive_group import group_display_short, WebGaloisGroup, group_display_knowl, galois_module_knowl
from lmfdb.db_backend import db
wnflog = make_logger("WNF")

dir_group_size_bound = 10000
dnc = 'data not computed'

# Dictionary of field label: n for abs(disc(Q(zeta_n)))
# Does all cyclotomic fields of degree n s.t. 2<n<24
cycloinfo = {'4.0.125.1': 5, '6.0.16807.1': 7, '4.0.256.1': 8,
  '6.0.19683.1': 9, '10.0.2357947691.1': 11, '4.0.144.1': 12,
  '12.0.1792160394037.1': 13, '8.0.1265625.1': 15, '8.0.16777216.1': 16,
  '16.0.2862423051509815793.1': 17, '18.0.5480386857784802185939.1': 19,
  '8.0.4000000.1': 20, '12.0.205924456521.1': 21,
  '22.0.39471584120695485887249589623.1': 23, '8.0.5308416.1': 24,
  '20.0.2910383045673370361328125.1': 25,
  '18.0.2954312706550833698643.1': 27, '12.0.1157018619904.1': 28,
  '16.0.18446744073709551616.1': 32, '20.0.328307557444402776721569.1': 33,
  '24.0.304383340063522342681884765625.1': 35,
  '12.0.1586874322944.1': 36,
  '24.0.1706902865139206151939937338729.1': 39,
  '16.0.1048576000000000000.1': 40,
  '20.0.5829995856912430117421056.1': 44,
  '24.0.572565594852444156646728515625.1': 45,
  '16.0.1846757322198614016.1': 48,
  '24.0.53885714612646242347927893704704.1': 52,
  '24.0.22459526297810799636782730182656.1': 56,
  '16.0.104976000000000000.1': 60,
  '24.0.42247883974617233597120303333376.1': 72,
  '24.0.711435861303500483618465120256.1': 84}
# Reverse lookup for newforms
cyclolookup = {n:label for label,n in cycloinfo.items()}
cyclolookup[1] = '1.1.1.1'
cyclolookup[3] = '2.0.3.1'
cyclolookup[4] = '2.0.4.1'
for n, label in cyclolookup.items():
    if label.split('.')[0] == '24':
        # LMFDB doesn't actually include fields of dimension 24
        cyclolookup.pop(n)
    elif n % 2 == 1:
        cyclolookup[2*n] = label

def na_text():
    return "Not computed"

## Turn a list into a string (without brackets)

def list2string(li):
    li2 = [str(x) for x in li]
    return ','.join(li2)

def string2list(s):
    s = str(s)
    if s == '':
        return []
    return [int(a) for a in s.split(',')]

def is_fundamental_discriminant(d):
    if d in [0, 1]:
        return False
    if d.is_squarefree():
        return d % 4 == 1
    else:
        return d % 16 in [8, 12] and (d // 4).is_squarefree()

def factor_base_factor(n, fb):
    return [[p, valuation(n,p)] for p in fb]

def factor_base_factorization_latex(fbf):
    ans = ''
    if len(fbf)==0:
        return '1'
    for pm in fbf:
        if pm[1]==1:
            ans += r'\cdot %d'%(pm[0])
        elif pm[1]>1:
            ans += r'\cdot %d^{%d}'%(pm[0],pm[1])
    return ans[6:]

@cached_function
def field_pretty(label):
    d, r, D, i = label.split('.')
    if d == '1':  # Q
        return '\(\Q\)'
    if d == '2':  # quadratic field
        D = ZZ(int(D))
        if r == '0':
            D = -D
        # Don't prettify invalid quadratic field labels
        if not is_fundamental_discriminant(D):
            return label
        return '\(\Q(\sqrt{' + str(D if D%4 else D/4) + '}) \)'
    if label in cycloinfo:
        return '\(\Q(\zeta_{%d})\)' % cycloinfo[label]
    if d == '4':
        wnf = WebNumberField(label)
        subs = wnf.subfields()
        if len(subs)==3: # only for V_4 fields
            subs = [wnf.from_coeffs(string2list(str(z[0]))) for z in subs]
            # Abort if we don't know one of these fields
            if [z for z in subs if z._data is None] == []:
                labels = [str(z.get_label()) for z in subs]
                labels = [z.split('.') for z in labels]
                # extract abs disc and signature to be good for sorting
                labels = [[ZZ(z[2]).squarefree_part(), - int(z[1])] for z in labels]
                labels.sort()
                # put in +/- sign
                labels = [z[0]*(-1)**(1+z[1]/2) for z in labels]
                labels = ['i' if z == -1 else '\sqrt{%d}'% z for z in labels]
                return '\(\Q(%s, %s)\)'%(labels[0],labels[1])
    return label

def psum(val, li):
    tot=0
    for j in range(len(li)):
        tot += li[j]*val**j
    return tot

def decodedisc(ads, s):
    return ZZ(ads[3:]) * s

def formatfield(coef):
    coef = string2list(coef)
    thefield = WebNumberField.from_coeffs(coef)
    if thefield._data is None:
        deg = len(coef) - 1
        mypol = sage.all.latex(coeff_to_poly(coef))
        mypol = mypol.replace(' ','').replace('+','%2B').replace('{', '%7B').replace('}','%7d')
        mypol = '<a title = "Field missing" knowl="nf.field.missing" kwargs="poly=%s">Deg %d</a>' % (mypol,deg)
        return mypol
    return nf_display_knowl(thefield.get_label(),thefield.field_pretty())

# input is a list of pairs, module and multiplicity
def modules2string(n, t, modlist):
    modlist = [[galois_module_knowl(n, t, z[0]), int(z[1])] for z in modlist]
    ans = modlist[0][0]
    modlist[0][1] -= 1
    for j in range(len(modlist)):
        while modlist[j][1]>0:
            ans += r' $\oplus$ '+modlist[j][0]
            modlist[j][1] -= 1
    return ans

def nf_display_knowl(label, name=None):
    if not name:
        name = "Global Number Field %s" % label
    return '<a title = "%s [nf.field.data]" knowl="nf.field.data" kwargs="label=%s">%s</a>' % (name, label, name)

def nf_knowl_guts(label):
    out = ''
    wnf = WebNumberField(label)
    if wnf.is_null():
        return 'Cannot find global number field %s' % label
    out += "Global number field %s" % label
    out += '<div>'
    out += 'Defining polynomial: '
    out += "\(%s\)" % latex(wnf.poly())
    D = wnf.disc()
    Dfact = wnf.disc_factored_latex()
    if D.abs().is_prime() or D == 1:
        Dfact = "\(%s\)" % str(D)
    else:
        Dfact = '%s = \(%s\)' % (str(D),Dfact)
    out += '<br>Discriminant: '
    out += Dfact
    out += '<br>Signature: '
    out += str(wnf.signature())
    out += '<br>Galois group: '+group_display_knowl(wnf.degree(),wnf.galois_t())
    out += '<br>Class number: %s ' % str(wnf.class_number_latex())
    if wnf.can_class_number():
        out += wnf.short_grh_string()
    out += '</div>'
    out += '<div align="right">'
    out += '<a href="%s">%s home page</a>' % (str(url_for("number_fields.number_field_render_webpage", natural=label)),label)
    out += '</div>'
    return out

class WebNumberField:
    """
     Class for retrieving number field information from the database
    """
    def __init__(self, label, data=None, gen_name='a'):
        self.label = label
        self.gen_name = gen_name
        if data is None:
            self._data = self._get_dbdata()
        else:
            self._data = data

    # works with a string, or a list of coefficients
    @classmethod
    def from_coeffs(cls, coeffs):
        if isinstance(coeffs, str):
            coeffs = string2list(coeffs)
        if isinstance(coeffs, list):
            f = db.nf_fields.lucky({'coeffs': coeffs})
            if f is None:
                return cls('a')  # will initialize data to None
            return cls(f['label'], f)
        else:
            raise Exception('wrong type')

    # Just a shell which should be used in a limited way since we don't
    # initialize much
    @classmethod
    def fakenf(cls, coeffs):
        if isinstance(coeffs, list):
            coeffs = list2string(coeffs)
        coefstr = string2list(coeffs)
        n = len(coefstr)-1
        data = {'coeffs': coeffs, 'degree': n}
        return cls('Degree %d field'%n, data)

    @classmethod
    def from_polredabs(cls, pol):
        return cls.from_coeffs([int(c) for c in pol.coefficients(sparse=False)])

    @classmethod
    def from_polynomial(cls, pol):
        pol = PolynomialRing(QQ, 'x')(str(pol))
        pol *= pol.denominator()
        R = pol.parent()
        pol = R(pari(pol).polredbest().polredabs())
        return cls.from_coeffs([int(c) for c in pol.coefficients(sparse=False)])

    # If we already have the database entry
    @classmethod
    def from_data(cls, data):
        return cls(data['label'], data)

    # For cyclotomic fields
    @classmethod
    def from_cyclo(cls, n):
        if euler_phi(n) > 23:
            return cls('none')  # Forced to fail
        pol = pari.polcyclo(n)
        R = PolynomialRing(ZZ, 'x')
        coeffs = R(pol.polredabs()).coefficients(sparse=False)
        return cls.from_coeffs(coeffs)

    def _get_dbdata(self):
        return db.nf_fields.lookup(self.label)

    def get_label(self):
        if self.label == 'a':
            return None
        return self.label

    def field_pretty(self):
        return field_pretty(self.get_label())

    def knowl(self):
        return nf_display_knowl(self.get_label(), self.field_pretty())

    # Is the polynomial polredabs'ed
    def is_reduced(self):
        if not self.haskey('reduced'):
            return True
        if self._data['reduced'] == 0:
            return False
        return True

    # Return discriminant as a sage int
    def disc(self):
        return ZZ(self._data['disc_abs']) * self._data['disc_sign']

    def ramified_primes(self):
        return [int(str(j)) for j in self._data['ramps']]

    # Return a nice string for the Galois group
    def galois_string(self):
        if not self.haskey('galt'):
            return 'Not computed'
        n = self._data['degree']
        t = self._data['galt']
        return group_display_short(n, t)

    # Just return the t-number of the Galois group
    def galois_t(self):
        return self._data['galt']

    # return the Galois group
    def gg(self):
        if not self.haskey('gg'):
            self._data['gg'] = WebGaloisGroup.from_nt(self.degree(), self.galois_t())
        return self._data['gg']

    def is_galois(self):
        return self.gg().order() == self.degree()

    def is_abelian(self):
        return self.gg().is_abelian()

    def coeffs(self):
        coeffs = self._data['coeffs']
        if isinstance(coeffs, list):
            return coeffs
        elif isinstance(coeffs, str):
            return string2list(coeffs)
        else:
            raise RuntimeError

    def signature(self):
        r2 = self._data['r2']
        n = self._data['degree']
        return [n-2*r2, r2]

    def degree(self):
        return self._data['degree']

    def is_real_quadratic(self):
        return self.signature()==[2,0]

    def is_imag_quadratic(self):
        return self.signature()==[0,1]

    def poly(self):
        return coeff_to_poly(self._data['coeffs'])

    def haskey(self, key):
        return self._data.get(key) is not None

    # Warning, this produces our prefered integral basis
    # But, if you have the sage number field do computations,
    # they will be in terms of a different basis
    def zk(self):
        if self.haskey('zk'):
            zkstrings = self._data['zk']
            return [str(u) for u in zkstrings]
        return list(pari(self.poly()).nfbasis())

    # 2018-4-1: is this actually used?  grep -r doesn't find anywhere it's called....
    # Used by subfields and resolvent functions to
    # take coefficients for fields and either return
    # information about the item, or a usable knowl

    # We need to return information in 2 ways: (1) list of knowls
    # and (2) list of label/polynomials
    def myhelper(self, coefmult):
        coef = string2list(coefmult[0])
        subfield = self.from_coeffs(coef)
        if subfield._data is None:
            deg = len(coef) - 1
            mypol = sage.all.latex(coeff_to_poly(coef))
            mypol = mypol.replace(' ','').replace('+','%2B').replace('{', '%7B').replace('}','%7d')
            mypol = '<a title = "Field missing" knowl="nf.field.missing" kwargs="poly=%s">Deg %d</a>' % (mypol,deg)
            return [mypol, coefmult[1]]
        return [nf_display_knowl(subfield.get_label(),subfield.field_pretty()), coefmult[1]]

    # returns resolvent dictionary
    # ae means arithmetically equivalent fields
    def resolvents(self):
        if not self.haskey('res'):
            self._data['res'] = {}
        return self._data['res']

    # Get data from group database
    def galois_sib_data(self):
        if 'repdata' not in self._data:
            repdegs = [z[0] for z in self.gg()._data['repns']]
            numae = self.gg().arith_equivalent()
            galord = int(self.gg().order())
            repcounts = Counter(repdegs)
            gc = 0
            if galord<24:
                del repcounts[galord]
                if self.degree() < galord:
                    gc = 1 
            repcounts[self.degree()] -= numae
            if repcounts[self.degree()] == 0:
                del repcounts[self.degree()]
            self._data['repdata'] = [repcounts, numae, gc]
        return self._data['repdata']

    def sibling_labels(self):
        resall = self.resolvents()
        if 'sib' in resall:
            sibs = [self.from_coeffs(str(a)) for a in resall['sib']]
            return ['' if a._data is None else a.label for a in sibs]
        return []

    def siblings(self):
        cnts = self.galois_sib_data()[0]
        resall = self.resolvents()
        if 'sib' in resall:
            # list of [degree, knowl
            helpout = [[len(string2list(a))-1,formatfield(a)] for a in resall['sib']]
        else:
            helpout = []
        degsiblist = [[d, cnts[d], [dd[1] for dd in helpout if dd[0]==d] ] for d in sorted(cnts.keys())]
        return [degsiblist, self.sibling_labels()]

    def sextic_twin(self):
        if self.degree() != 6:
            return [0,[],[]]
        resall = self.resolvents()
        if 'sex' in resall:
            sex = [self.from_coeffs(str(a)) for a in resall['sex']]
            sex = [a.label for a in sex if a._data is not None]
            # Don't include Q in labels
            sex = [z for z in sex if z != '1.1.1.1']
            labels = sorted(Set(sex))
            knowls = [formatfield(a) for a in resall['sex']]
            return [1, knowls, labels]
        return [1,[],[]]

    def galois_closure(self):
        resall = self.resolvents()
        cnt = self.galois_sib_data()[2]
        if 'gal' in resall:
            knowls= [formatfield(a) for a in resall['gal']]
            gal = [self.from_coeffs(str(a)) for a in resall['gal']]
            labs = [a.label for a in gal if a._data is not None]
            return [cnt, knowls, labs]
        return [cnt, [], []]

    def arith_equiv(self):
        resall = self.resolvents()
        cnt = self.galois_sib_data()[1]
        if 'ae' in resall:
            knowls = [formatfield(a) for a in resall['ae']]
            ae = [self.from_coeffs(str(a)) for a in resall['ae']]
            labs = [a.label for a in ae if a._data is not None]
            return [cnt, knowls, labs]
        return [cnt, [], []]

    def subfields(self):
        if not self.haskey('subs'):
            return []
        return self._data['subs']

    def subfields_show(self):
        subs = self.subfields()
        if subs == []:
            return []
        return display_multiset(subs, formatfield)

    def unit_galois_action(self):
        if not self.haskey('unitsGmodule'):
            if self.signature()==[0,2] and self.galois_t() ==2:
                return [[1,1]]
            # We don't have C_4 classification yet
            #if self.signature()==[2,0] or self.signature()==[0,2]:
            #    return [[1,1]]
            return []
        return self._data['unitsGmodule']

    def unit_galois_action_type_knowl(self):
        if not self.haskey('unitsType'):
            return None
        ty = self._data['unitsType']
        knowlid = ty.replace(' ','_')
        knowlid = knowlid.replace('(','')
        knowlid = knowlid.replace(')','')
        knowlid = knowlid.replace(')','')
        knowlid = knowlid.lower()
        knowlid = 'nf.galois_group.gmodule_v4_'+knowlid
        return '<a title = "%s [%s]" knowl="%s">%s</a>' % (ty, knowlid, knowlid, ty)

    def unit_galois_action_show(self):
        ugm = self.unit_galois_action()
        if ugm == []:
            return ''
        n = self.degree()
        t = self.galois_t()
        return modules2string(n, t, ugm)

    # Sage version of K -- should be avoided since it can be slow
    # in extreme cases
    def K(self):
        if not self.haskey('K'):
            self._data['K'] = NumberField(self.poly(), self.gen_name)
        return self._data['K']

    # pari version of K
    def gpK(self):
        if not self.haskey('gpK'):
            Qx = PolynomialRing(QQ,'x')
            # while [1] is a perfectly good basis for Z, gp seems to want []
            basis = [Qx(el.replace('a','x')) for el in self.zk()] if self.degree() > 1 else []
            k1 = gp( "nfinit([%s,%s])" % (str(self.poly()),str(basis)) )
            self._data['gpK'] = k1
        return self._data['gpK']

    def generator_name(self):
        #Add special case code for the generator if desired:
        if self.gen_name=='phi':
            return '\phi'
        else:
            return web_latex(self.gen_name)

    def variable_name(self):
        # For consistency with Sage number fields
        return self.gen_name

    def unit_rank(self):
        if not self.haskey('unit_rank'):
            sig = self.signature()
            self._data['unit_rank'] = sig[0] + sig[1] - 1
        return self._data['unit_rank']

    def regulator(self):
        if self.haskey('reg'):
            return self._data['reg']
        if self.unit_rank() == 0:
            return 1
        if self.haskey('class_number'):
            K = self.K()
            return K.regulator()
        return na_text()

    def units(self):  # fundamental units
        res = None
        if self.haskey('units'):
            res = ',&nbsp; '.join(self._data['units'])
        elif self.unit_rank() == 0:
            res = ''
        elif self.haskey('class_number'):
            K = self.K()
            units = [web_latex(u) for u in K.unit_group().fundamental_units()]
            units = ',&nbsp; '.join(units)
            res = units
        if res:
            res = res.replace('\\\\', '\\')
            return res
        return na_text()

    def disc_factored_latex(self):
        D = self.disc()
        s = ''
        if D < 0:
            s = r'-\,'
        return s + factor_base_factorization_latex(factor_base_factor(D,self.ramified_primes()))

    def web_poly(self):
        return pol_to_html(str(coeff_to_poly(self.coeffs())))

    def class_group_invariants(self):
        if not self.haskey('class_group'):
            return na_text()
        cg_list = self._data['class_group']
        if cg_list == []:
            return 'Trivial'
        #return cg_list
        return '$%s$'%str(cg_list)

    def class_group_invariants_raw(self):
        if not self.haskey('class_group'):
            return [-1]
        return self._data['class_group']

    def class_group(self):
        if self.haskey('class_group'):
            cg_list = self._data['class_group']
            return str(AbelianGroup(cg_list)) + ', order ' + self.class_number_latex()
        return na_text()

    def class_number(self):
        if self.haskey('class_number'):
            return self._data['class_number']
        return na_text()

    def class_number_latex(self):
        if self.haskey('class_number'):
            return '$%s$'%str(self._data['class_number'])
        return na_text()

    def can_class_number(self):
        if self.haskey('class_number'):
            return True
        return False

    def is_null(self):
        return self._data is None

    def used_grh(self):
        if self.haskey('used_grh'):
            return self._data['used_grh']
        return False

    def short_grh_string(self):
        if self.used_grh():
            return '<span style="font-size: x-small">(GRH)</span>'
        return ''

    def conductor(self):
        """ Computes the conductor if the extension is abelian.
            It raises an exception if the field is not abelian.
        """
        if not self.is_abelian():
            raise Exception('Invalid field for conductor')
        D = self.disc()
        plist = self.ramified_primes()
        K = self.K()
        f = ZZ(1)
        for p in plist:
            e = K.factor(p)[0][0].ramification_index()
            if p == ZZ(2):
                e = K.factor(p)[0][0].ramification_index()
                # ramification index must be a power of 2
                f *= e * 2
                c = D.valuation(p)
                res_deg = ZZ(self.degree() / e)
                # adjust disc expo for unramified part
                c = ZZ(c / res_deg)
                if is_odd(c):
                    f *= 2
            else:
                f *= p ** (e.valuation(p) + 1)
        return f

    def artin_reps(self, nfgg=None):
        if nfgg is not None:
            self._data["nfgg"] = nfgg
        else:
            if "nfgg" not in self._data:
                from artin_representations.math_classes import NumberFieldGaloisGroup
                nfgg = NumberFieldGaloisGroup.find_one({"label": self.label})
                self._data["nfgg"] = nfgg
            else:
                nfgg = self._data["nfgg"]
        return nfgg.artin_representations()

    def factor_perm_repn(self, nfgg=None):
        if 'artincoefs' in self._data:
            return self._data['artincoefs']
        try:
            if nfgg is not None:
                self._data["nfgg"] = nfgg
            elif "nfgg" not in self._data:
                from artin_representations.math_classes import NumberFieldGaloisGroup
                nfgg = NumberFieldGaloisGroup(self._data['coeffs'])
                self._data["nfgg"] = nfgg
            else:
                nfgg = self._data["nfgg"]

            cc = nfgg.conjugacy_classes()
            # cc is list, each has methods group, size, order, representative
            ccreps = [x.representative() for x in cc]
            ccns = [int(x.size()) for x in cc]
            ccreps = [x.cycle_string() for x in ccreps]
            ccgen = '['+','.join(ccreps)+']'
            ar = nfgg.artin_representations() # list of artin reps from db
            arfull = nfgg.artin_representations_full_characters() # list of artin reps from db
            gap.set('fixed', 'function(a,b) if a*b=a then return 1; else return 0; fi; end;');
            g = gap.Group(ccgen)
            h = g.Stabilizer('1')
            rc = g.RightCosets(h)
            # Permutation character for our field
            permchar = [gap.Sum(rc, 'j->fixed(j,'+x+')') for x in ccreps]
            charcoefs = [0 for x in arfull]
            # list of lists (inner are giving char values
            ar2 = [x[0] for x in arfull]
            for j in range(len(ar)):
                fieldchar = int(arfull[j][1])
                zet = CyclotomicField(fieldchar).gen()
                ar2[j] = [psum(zet, x) for x in ar2[j]]
            for j in range(len(ar)):
                charcoefs[j] = 0
                for k in range(len(ccns)):
                    charcoefs[j] += int(permchar[k])*ccns[k]*ar2[j][k]
            charcoefs = [x/int(g.Size()) for x in charcoefs]
            self._data['artincoefs'] = charcoefs
            return charcoefs

        except AttributeError:
            return []

        return []

    def dirichlet_group(self, prime_bound=10000):
        f = self.conductor()
        if f == 1:  # To make the trivial case work correctly
            return [1]
        if euler_phi(f) > dir_group_size_bound:
            return []
        # Can do quadratic fields directly
        if self.degree() == 2:
            if is_odd(f):
                return [1, f-1]
            f1 = f/4
            if is_odd(f1):
                return [1, f-1]
            # we now want f with all powers of 2 removed
            f1 = f1/2
            if is_even(f1):
                raise Exception('Invalid conductor')
            if (self.disc()/8) % 4 == 3:
                return [1, 4*f1-1]
            # Finally we want congruent to 5 mod 8 and -1 mod f1
            if (f1 % 4) == 3:
                return [1, 2*f1-1]
            return [1, 6*f1-1]

        from dirichlet_conrey import DirichletGroup_conrey
        G = DirichletGroup_conrey(f)
        K = self.K()
        S = Set(G[1].kernel()) # trivial character, kernel is whole group

        for P in K.primes_of_bounded_norm_iter(ZZ(prime_bound)):
            a = P.norm() % f
            if gcd(a,f)>1:
                continue
            S = S.intersection(Set(G[a].kernel()))
            if len(S) == self.degree():
                return list(S)

        raise Exception('Failure in dirichlet group for K=%s using prime bound %s' % (K,prime_bound))

    def full_dirichlet_group(self):
        from dirichlet_conrey import DirichletGroup_conrey
        f = self.conductor()
        return DirichletGroup_conrey(f)

    # Helper for ramified algebras table
    def get_local_algebra(self, p):
        local_algebra_dict = self._data.get('loc_algebras', None)
        if local_algebra_dict is None:
            return None
        if str(p) in local_algebra_dict:
            R = PolynomialRing(QQ, 'x')
            palg = local_algebra_dict[str(p)]
            palgs = [R(str(s)) for s in palg.split(',')]
            palgstr = [
                    list2string([int(c) for c in pol.coefficients(sparse=False)])
                    for pol in palgs]
            palgrec = [db.lf_fields.lucky({'p': p, 'coeffs': map(int, c.split(','))}) for c in palgstr]
            return [
                    [
                        LF['label'],
                        latex(f),
                        int(LF['e']),
                        int(LF['f']),
                        int(LF['c']),
                        group_display_knowl(LF['n'], LF['galT']),
                        LF['t'],
                        LF['u'],
                        LF['slopes']
                    ]
                    for LF, f in zip(palgrec, palgs) ]
        return None

    def ramified_algebras_data(self):
        if 'loc_algebras' not in self._data:
            return dnc
        return [self.get_local_algebra(p) for p in self.ramified_primes()]

    def make_code_snippets(self):
         # read in code.yaml from numberfields directory:
        _curdir = os.path.dirname(os.path.abspath(__file__))
        self.code = yaml.load(open(os.path.join(_curdir, "number_fields/code.yaml")))
        self.code['show'] = {'sage':'','pari':'', 'magma':''} # use default show names

        # Fill in placeholders for this specific field:
        for lang in ['sage', 'pari']:
            self.code['field'][lang] = self.code['field'][lang] % self.poly()
        self.code['field']['magma'] = self.code['field']['magma'] % self.coeffs()

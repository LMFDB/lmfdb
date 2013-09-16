# -*- coding: utf-8 -*-
import lmfdb.base as base
from sage.all import *
import re
import pymongo
import bson
from lmfdb.utils import *
from lmfdb.transitive_group import group_display_short, WebGaloisGroup, group_display_knowl
wnflog = make_logger("WNF")


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

def psum(val, li):
    tot=0
    for j in range(len(li)):
        tot += li[j]*val**j
    return tot

def decodedisc(ads, s):
    return ZZ(ads[3:]) * s

def nf_display_knowl(label, C, name=None):
    if not name:
        name = "Global Number Field %s" % label
    return '<a title = "%s [nf.field.data]" knowl="nf.field.data" kwargs="label=%s">%s</a>' % (name, label, name)

def nf_knowl_guts(label, C):
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
        D = str(D)
        Dfact = D + ' = ' + Dfact
    out += '<br>Discriminant: $'
    out += Dfact
    out += '$<br>Signature: '
    out += wnf.signature()
    out += '<br>Galois group: '+group_display_knowl(wnf.degree(),wnf.galois_t(),C)
    out += '</div>'
    out += '<div align="right">'
    out += '<a href="%s">%s home page</a>' % (url_for("number_fields.number_field_render_webpage", natural=label),label)
    out += '</div>'
    return out

class WebNumberField:
    """
     Class for retrieving number field information from the database
    """
    def __init__(self, label, data=None):
        self.label = label
        if data is None:
            self._data = self._get_dbdata()
        else:
            self._data = data

    # works with a string, or a list of coefficients
    @classmethod
    def from_coeffs(cls, coeffs):
        if isinstance(coeffs, list):
            coeffs = list2string(coeffs)
        if isinstance(coeffs, str):
            nfdb = base.getDBConnection().numberfields.fields
            f = nfdb.find_one({'coeffs': coeffs})
            if f is None:
                return cls('a')  # will initialize data to None
            return cls(f['label'], f)
        else:
            raise Exception('wrong type')

    @classmethod
    def from_polredabs(cls, pol):
        return cls.from_coeffs([int(c) for c in pol.coeffs()])

    @classmethod
    def from_polynomial(cls, pol):
        pol = PolynomialRing(QQ, 'x')(str(pol))
        pol *= pol.denominator()
        R = pol.parent()
        pol = R(pari(pol).polredabs())
        return cls.from_coeffs([int(c) for c in pol.coeffs()])

    # If we already have the database entry
    @classmethod
    def from_data(cls, data):
        return cls(data['label'], data)

    # For cyclotomic fields
    @classmethod
    def from_cyclo(cls, n):
        if euler_phi(n) > 15:
            return cls('none')  # Forced to fail
        pol = pari.polcyclo(n)
        R = PolynomialRing(QQ, 'x')
        coeffs = R(pol.polredabs()).coeffs()
        return cls.from_coeffs(coeffs)

    def _get_dbdata(self):
        nfdb = base.getDBConnection().numberfields.fields
        return nfdb.find_one({'label': self.label})

    def get_label(self):
        if self.label == 'a':
            return None
        return self.label

    # Return discriminant as a sage int
    def disc(self):
        return decodedisc(self._data['disc_abs_key'], self._data['disc_sign'])

    # Return a nice string for the Galois group
    def galois_string(self):
        n = self._data['degree']
        t = self._data['galois']['t']
        C = base.getDBConnection()
        return group_display_short(n, t, C)

    # Just return the t-number of the Galois group
    def galois_t(self):
        return self._data['galois']['t']

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
        return string2list(self._data['coeffs'])

    def signature(self):
        return string2list(self._data['signature'])

    def degree(self):
        return self._data['degree']

    def poly(self):
        return coeff_to_poly(string2list(self._data['coeffs']))

    def haskey(self, key):
        return key in self._data

    def K(self):
        if not self.haskey('K'):
            self._data['K'] = NumberField(self.poly(), 'a')
        return self._data['K']

    def unit_rank(self):
        if not self.haskey('unit_rank'):
            sig = self.signature()
            self._data['unit_rank'] = unit_rank = sig[0] + sig[1] - 1
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
        if self.haskey('units'):
            return ',&nbsp; '.join(self._data['units'])
        if self.unit_rank() == 0:
            return ''
        if self.haskey('class_number'):
            K = self.K()
            units = [web_latex(u) for u in K.unit_group().fundamental_units()]
            units = ',&nbsp; '.join(units)
            return units
        return na_text()

    def disc_factored_latex(self):
        D = self.disc()
        s = ''
        if D < 0:
            D = -D
            s = r'-\,'
        return s + latex(D.factor())

    def web_poly(self):
        return pol_to_html(str(coeff_to_poly(self.coeffs())))

    def class_group_invariants(self):
        if not self.haskey('class_group'):
            return na_text()
        cg_list = string2list(self._data['class_group'])
        if cg_list == []:
            return 'Trivial'
        return cg_list

    def class_group_invariants_raw(self):
        if not self.haskey('class_group'):
            return [-1]
        return string2list(self._data['class_group'])

    def class_group(self):
        if self.haskey('class_group'):
            cg_list = string2list(self._data['class_group'])
            return str(AbelianGroup(cg_list)) + ', order ' + str(self._data['class_number'])
        return na_text()

    def class_number(self):
        if self.haskey('class_number'):
            return self._data['class_number']
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
        plist = D.prime_factors()
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
                from math_classes import NumberFieldGaloisGroup
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
            else:
                if "nfgg" not in self._data:
                    from math_classes import NumberFieldGaloisGroup
                    nfgg = NumberFieldGaloisGroup.find_one({"label": self.label})
                    self._data["nfgg"] = nfgg
                else:
                    nfgg = self._data["nfgg"]

            cc = nfgg.conjugacy_classes()
            # cc is list, each has methods group, size, order, representative
            ccreps = [x.representative() for x in cc]
            ccns = [int(x.size()) for x in cc]
            ccreps = [x.cycle_string() for x in ccreps]
            ccgen = '['+','.join(ccreps)+']'
            ar = nfgg.ArtinReps() # list of artin reps from db
            gap.set('fixed', 'function(a,b) if a*b=a then return 1; else return 0; fi; end;');
            g = gap.Group(ccgen)
            h = g.Stabilizer('1')
            rc = g.RightCosets(h)
            # Permutation character for our field
            permchar = [gap.Sum(rc, 'j->fixed(j,'+x+')') for x in ccreps]
            charcoefs = [0 for x in ar]
            # list of lists (inner are giving char values
            ar2 = [x['Character'] for x in ar]
            for j in range(len(ar)):
                fieldchar = int(ar[j]['CharacterField'])
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

    def dirichlet_group(self):
        from dirichlet_conrey import DirichletGroup_conrey
        f = self.conductor()
        if f == 1:  # To make the trivial case work correctly
            return [1]
        G = DirichletGroup_conrey(f)
        pram = f.prime_factors()
        P = Primes()
        p = P.first()
        K = self.K()

        while p in pram:
            p = P.next(p)
        fres = K.factor(p)[0][0].residue_class_degree()
        a = p ** fres
        S = set(G[a].kernel())
        timeout = 10000
        while len(S) != self.degree():
            timeout -= 1
            p = P.next(p)
            if p not in pram:
                fres = K.factor(p)[0][0].residue_class_degree()
                a = p ** fres
                S = S.intersection(G[a].kernel())
            if timeout == 0:
                raise Exception('timeout in dirichlet group')

        return [b for b in S]

    def full_dirichlet_group(self):
        from dirichlet_conrey import DirichletGroup_conrey
        f = self.conductor()
        return DirichletGroup_conrey(f)


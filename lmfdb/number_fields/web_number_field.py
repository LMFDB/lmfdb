# -*- coding: utf-8 -*-
from collections import Counter
import os
import yaml

from flask import url_for
from sage.all import (
    Set, ZZ, RR, pi, euler_phi, CyclotomicField, gap, RealField, sqrt,
    QQ, NumberField, PolynomialRing, latex, pari, cached_function, Permutation)

from lmfdb import db
from lmfdb.utils import (web_latex, coeff_to_poly, pol_to_html,
        raw_typeset_poly, display_multiset, factor_base_factor,
        integer_squarefree_part, integer_is_squarefree,
        factor_base_factorization_latex)
from lmfdb.logger import make_logger
from lmfdb.galois_groups.transitive_group import WebGaloisGroup, transitive_group_display_knowl, galois_module_knowl, group_pretty_and_nTj

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
  '28.0.3053134545970524535745336759489912159909.1':29,
  '30.0.17761887753093897979823770061456102763834271.1':31,
  '16.0.18446744073709551616.1': 32, '20.0.328307557444402776721569.1': 33,
  '24.0.304383340063522342681884765625.1': 35,
  '12.0.1586874322944.1': 36,
  '36.0.7710105884424969623139759010953858981831553019262380893.1':37,
  '24.0.1706902865139206151939937338729.1': 39,
  '16.0.1048576000000000000.1': 40,
  '40.0.791717805254439023624865699561776475898803884688668051353443161.1':41,
  '42.0.9380082945933081406113456619151991432292083579779389915131296484043.1':43,
  '20.0.5829995856912430117421056.1': 44,
  '24.0.572565594852444156646728515625.1': 45,
  '46.0.1755511210260049172778020908173078657717675374080672665297567056535308458607.1':47,
  '16.0.1846757322198614016.1': 48,
  '42.0.118181386580595879976868414312001964434038548836769923458287039207.1':49,
  '32.0.352701833122210710593389803720131611763844129.1':51,
  '24.0.53885714612646242347927893704704.1': 52,
  '40.0.28789677222138897176527746894292024300433695316314697265625.1':55,
  '24.0.22459526297810799636782730182656.1': 56,
  '36.0.11636034958735032166924075841251447518799351583251569.1':57,
  '16.0.104976000000000000.1': 60,
  '36.0.1310656710125779295611091389185381649163216325999081.1':63,
  '32.0.1461501637330902918203684832716283019655932542976.1':64,
  '32.0.35190667333271321019306672876612934335729762304.1':68,
  '44.0.48891877682180103607391812819535352418736437208892474989920547427561.1':69,
  '24.0.42247883974617233597120303333376.1': 72,
  '40.0.29534212676193502024324377686070874915458261966705322265625.1':75,
  '36.0.2063964752380648518006363619171361060603216996551622656.1':76,
  '32.0.4722366482869645213696000000000000000000000000.1':80,
  '24.0.711435861303500483618465120256.1':84,
  '40.0.37371137649685869661036271274571515833850102932794388078657536.1':88,
  '44.0.27408730583433337351085467861786155262978057758761987414355526669041664.1':92,
  '32.0.14648040110065267094876580444599852735215435776.1':96,
  '40.0.9313225746154785156250000000000000000000000000000000000000000.1':100,
  '36.0.599781089369859106058502013153430001897393515831230464.1':108,
  '32.0.47330370277129322496000000000000000000000000.1':120,
  '40.0.118511797886229481159007653491590053243629014721874976833536.1':132}
# Real cyclotomic subfields
rcycloinfo = {'3.3.49.1': 7, '3.3.81.1': 9, '5.5.14641.1': 11,
  '6.6.371293.1': 13, '4.4.1125.1':15, '4.4.2048.1':16,
  '8.8.410338673.1':17, '9.9.16983563041.1':19, '4.4.2000.1':20,
  '6.6.453789.1':21, '11.11.41426511213649.1':23, '4.4.2304.1':24,
  '10.10.762939453125.1':25, '9.9.31381059609.1':27, '6.6.1075648.1':28,
  '14.14.10260628712958602189.1':29, '15.15.756943935220796320321.1':31,
  '8.8.2147483648.1':32, '10.10.572981288913.1':33,
  '12.12.551709470703125.1':35, '6.6.1259712.1':36,
  '18.18.456487940826035155404146917.1':37, '12.12.1306484927252973.1':39,
  '8.8.1024000000.1':40, '20.20.4394336169668803158610484050361.1':41,
  '21.21.467056167777397914441056671494001.1':43, '10.10.2414538435584.1':44,
  '12.12.756680642578125.1':45,
  '23.23.6111571184724799803076702357055363809.1':47,
  '8.8.1358954496.1':48,
  '21.21.129934811447123020117172145698449.1':49,
  '16.16.18780357640955901417873.1':51,
  '12.12.7340688973975552.1':52,
  '26.26.12790771483610519443342791266451996229460693.1':53,
  '20.20.169675210983039290802001953125.1':55,
  '12.12.4739148267126784.1':56,
  '18.18.107870454521778261425837337.1':57,
  '29.29.38358032782038398419973086399760468678777161743121.1':59,
  '8.8.324000000.1':60,
  '30.30.5950661074415937716058277355262049126611998411687341.1':61,
  '18.18.36202993110042424993725741.1':63,
  '16.16.604462909807314587353088.1':64,
  '24.24.12252192985362453861836887359619140625.1':65,
  '33.33.27189028279553414235049966267283185807800188603627566700161.1':67,
  '16.16.187591757103747287810048.1':68,
  '22.22.6992272712228843238468603052945581.1':69,
  '35.35.876564456148583685580741416193317498080031692578600918378223281.1':71,
  '12.12.6499837226778624.1':72,
  '36.36.164550840223975716663655069866834081172656515609690871995791535257.1':73,
  '20.20.171855208463966846466064453125.1':75,
  '18.18.1436650532447139184230793216.1':76,
  '30.30.17581401814197409148890873176573567284303576419397.1':77,
  '39.39.1287743804278744050410620426954739687963064854495168753870500853746064161.1':79,
  '16.16.68719476736000000000000.1':80,
  '27.27.706965049015104706497203195837614914543357369.1':81,
  '41.41.57959375186337998161464929843210464026538099255933595673241672975683189751201.1':83,
  '12.12.843466573910016.1':84,
  '32.32.488368614066527220997452797221673658430576324462890625.1':85,
  '28.28.14603047886206093768209337615200705673567789821.1':87,
  '20.20.6113193735657808322804901216256.1':88,
  '44.44.666454163935483494165986073535521413339908119119439689887653437787720225729135378569.1':89,
  '36.36.129739382499069208406967320777552926214641189868504834496493597.1':91,
  '22.22.165555823163769559238834502754107392.1':92,
  '30.30.254863675513583304379979153001217903140700917991797.1':93,
  '36.36.223775506846460533290697977531706040570972271263599395751953125.1':95,
  '16.16.121029087867608368152576.1':96,
  '30.30.38731022422755868071217069332926190761458900976553.1':99,
  '20.20.3051757812500000000000000000000.1':100,
  '24.24.904052273370722339459533425108859224064.1':104,
  '24.24.161761786626698377317203521728515625.1':105,
  '18.18.774455350146061749097070592.1':108,
  '36.36.2987052991985699215206951151365900403178222386352058024870316677.1':111,
  '24.24.376808323956052112639025409344139165696.1':112,
  '44.44.181375764426442332776050749828434842919201892356144879261148162186145782470703125.1':115,
  '28.28.819569564076950716311987772907236898045117333504.1':116,
  '36.36.334717470607298852954929976123524497086119009458311989825932357.1':117,
  '16.16.6879707136000000000000.1':120,
  '40.40.2760549293355133823580852196951954752012701839690650502926252551414931561.1':123,
  '30.30.19071681753690303660125890064344467877570851377250304.1':124,
  '32.32.3138550867693340381917894711603833208051177722232017256448.1':128,
  '42.42.98118980687896783910098639727548084722605054105289047332129555342401833439729.1':129,
  '20.20.344255425354822086003595935744.1':132,
  '36.36.65028396011052373244549315269863064140390224754810333251953125.1':135,
  '32.32.151142765320815856472639544599622796222554813389533609984.1':136,
  '24.24.5106705043047168064000000000000000000.1':140,
  '46.46.165269405800315006446654642733283089940652236420810887453559572571427563258244528313989.1':141,
  '24.24.708801874985091845381344307009569161216.1':144,
  '42.42.1236219045653317330764639083558080790009887216550178193020957667462329030021.1':147,
  '36.36.529834441956838404754859356629890081471398054377951743656484405248.1':148,
  '36.36.141834577785145976449731181827603110001579056521289025332042530816.1':152,
  '24.24.28637078059459331679625147758321598464.1':156,
  '32.32.20282409603651670423947251286016000000000000000000000000.1':160,
  '40.40.870502932794550416715512205314557822885758691905429612124950249853404839936.1':164,
  '40.40.100383397447978918530459891214693626269465146363712847232818603515625.1':165,
  '24.24.11935913115234869169771450911000887296.1':168,
  '42.42.41254041074227118944013302420247071185885898029927512658248841159725538158313472.1':172,
  '40.40.41090000389047069406072163992081637611400284636821909168682596532209319936.1':176,
  '24.24.9606056659007943744000000000000000000.1':180,
  '44.44.482179487665033966874817964307376476160282778171317425736173928285756467369658548224.1':184,
  '46.46.123533119255810717326269698346313186386460569318540167792790808431593601417039621597954048.1':188,
  '32.32.62912853223226562597999842165869507304166444172308381696.1':192,
  '42.42.519767234928222794437622861788597020192717533652199079454480438860528408854528.1':196,
  '40.40.10240000000000000000000000000000000000000000000000000000000000000000000000.1':200,
  '32.32.1514842838499144573219529960757824409341479409296605184.1':204,
  '36.36.41216642617644769738384985747906299013992369570201489573102485504.1':216,
  '40.40.31654584865659568778929513407372752241664000000000000000000000000000000.1':220,
  '36.36.799622233646074762983150698451178476894456963777140963130998784.1':228,
  '32.32.203282392447840896882957090816000000000000000000000000.1':240,
  '36.36.90067643300370785938616861622694756230952958181429238736879616.1':252,
  '40.40.130305099804548492884220428175380349368393046678311823693003457545895936.1':264,
  '44.44.860115008245742907292219227824365111518443501386754869093198564719785672888549376.1':276,
  '40.40.32473210254684090614318847656250000000000000000000000000000000000000000.1':300}

cyclolookup = {n:label for label,n in cycloinfo.items()}
cyclolookup[1] = '1.1.1.1'
cyclolookup[3] = '2.0.3.1'
cyclolookup[4] = '2.0.4.1'
for n, label in list(cyclolookup.items()):
    if n % 2:
        cyclolookup[2 * n] = label

rcyclolookup = {n:label for label,n in rcycloinfo.items()}
for n in [1,3,4]:
    rcyclolookup[n] = '1.1.1.1'
for n in [5,8,12]:
    rcyclolookup[n] = '2.2.%s.1'%n
for n, label in list(rcyclolookup.items()):
    if n % 2:
        rcyclolookup[2 * n] = label

def na_text():
    return "not computed"

## Turn a list into a string (without brackets)

def list2string(li):
    li2 = [str(x) for x in li]
    return ','.join(li2)

def string2list(s):
    s = str(s)
    if not s:
        return []
    return [int(a) for a in s.split(',')]

def is_fundamental_discriminant(d):
    if d in [0, 1]:
        return False
    if integer_is_squarefree(d):
        return d % 4 == 1
    else:
        return d % 16 in [8, 12] and integer_is_squarefree(d // 4)


@cached_function
def field_pretty(label):
    d, r, D, i = label.split('.')
    if d == '1':  # Q
        return r'\(\Q\)'
    if d == '2':  # quadratic field
        D = ZZ(int(D))
        if r == '0':
            D = -D
        # Don't prettify invalid quadratic field labels
        if not is_fundamental_discriminant(D):
            return label
        return r'\(\Q(\sqrt{' + str(D if D%4 else D/4) + r'}) \)'
    if label in cycloinfo:
        return r'\(\Q(\zeta_{%d})\)' % cycloinfo[label]
    if d == '4':
        wnf = WebNumberField(label)
        subs = wnf.subfields()
        if len(subs)==3: # only for V_4 fields
            subs = [wnf.from_coeffs(string2list(str(z[0]))) for z in subs]
            # Abort if we don't know one of these fields
            if not any(z._data is None for z in subs):
                labels = [str(z.get_label()) for z in subs]
                labels = [z.split('.') for z in labels]
                # extract abs disc and signature to be good for sorting
                labels = [[integer_squarefree_part(ZZ(z[2])), - int(z[1])] for z in labels]
                labels.sort()
                # put in +/- sign
                labels = [z[0]*(-1)**(1+z[1]/2) for z in labels]
                labels = ['i' if z == -1 else r'\sqrt{%d}'% z for z in labels]
                return r'\(\Q(%s, %s)\)'%(labels[0],labels[1])
    if label in rcycloinfo:
        return r'\(\Q(\zeta_{%d})^+\)' % rcycloinfo[label]
    return label

def psum(val, li):
    tot=0
    for j in range(len(li)):
        tot += li[j]*val**j
    return tot

def decodedisc(ads, s):
    return ZZ(ads[3:]) * s


def formatfield(coef, show_poly=False, missing_text=None):
    r"""
      Take a list of coefficients (which can be a string like '1,3,1'
      and either produce a number field knowl if the polynomial matches
      a number field in the database, otherwise produce a knowl which
      says say "Deg 15", which can be opened to show the degree 15
      polynomial.

      If show_poly is set to true and the polynomial is not in the
      database, just display the polynomial (no knowl).
    """
    if isinstance(coef, str):
        coef = string2list(coef)
    thefield = WebNumberField.from_coeffs(coef)
    if thefield._data is None:
        deg = len(coef) - 1
        mypolraw = coeff_to_poly(coef)
        mypol = latex(mypolraw)
        if show_poly:
            return '$'+mypol+'$'

        mypol = mypol.replace(' ','').replace('+','%2B').replace('{', '%7B').replace('}','%7d')
        mypolraw = str(mypolraw).replace(' ','').replace('+','%2B').replace('{', '%7B').replace('}','%7d')
        if missing_text is None:
            mypol = '<a title = "Field missing" knowl="nf.field.missing" kwargs="poly=%s&raw=%s">Deg %d</a>' % (mypol,mypolraw,deg)
        else:
            mypol = '<a title = "Field missing" knowl="nf.field.missing" kwargs="poly=%s">%s</a>' % (mypol,missing_text)
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

@cached_function
def nf_display_knowl(label, name=None):
    if not name:
        name = "Number field %s" % label
    return '<a title = "%s [nf.field.data]" knowl="nf.field.data" kwargs="label=%s">%s</a>' % (name, label, name)

def nf_knowl_guts(label):
    out = ''
    wnf = WebNumberField(label)
    if wnf.is_null():
        return 'Cannot find number field %s' % label
    out += "Number field %s" % label
    out += '<div>'
    out += 'Defining polynomial: '
    out += raw_typeset_poly(wnf.poly())
    D = wnf.disc()
    Dfact = wnf.disc_factored_latex()
    if D.abs().is_prime() or D == 1:
        Dfact = r"\(%s\)" % str(D)
    else:
        Dfact = r'%s = \(%s\)' % (str(D),Dfact)
    out += '<br>Discriminant: '
    out += Dfact
    out += '<br>Signature: '
    out += str(wnf.signature())
    out += '<br>Galois group: '+group_pretty_and_nTj(wnf.degree(),wnf.galois_t(), True)
    out += '<br>Class number: %s ' % str(wnf.class_number_latex())
    if wnf.can_class_number():
        out += wnf.short_grh_string()
    out += '</div>'
    out += '<div align="right">'
    out += '<a href="%s">%s home page</a>' % (str(url_for("number_fields.by_label", label=label)),label)
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
        try:
            # try to cast to ring
            pol = PolynomialRing(QQ, 'x')(pol)
        except Exception:
            # try again as a string
            pol = PolynomialRing(QQ, 'x')(str(pol))
        pol *= pol.denominator()
        # For some reason the error raised by Pari on a constant polynomial is not being caught
        if pol.degree() < 1:
            raise ValueError("Polynomial cannot be constant")
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
        n = int(n)
        if euler_phi(n) > 23:
            return cls('none')  # Forced to fail
        pol = pari.polcyclo(n)
        R = PolynomialRing(ZZ, 'x')
        coeffs = R(pol.polredabs()).coefficients(sparse=False)
        return cls.from_coeffs(coeffs)

    def _get_dbdata(self):
        return db.nf_fields.lookup(self.label)

    def is_in_db(self):
        return self._data is not None

    def get_label(self):
        if self.label == 'a':
            return None
        return self.label

    def label_pretty(self):
        from lmfdb.number_fields.number_field import nf_label_pretty
        return nf_label_pretty(self.label)

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

    # Even rd is in the database, that does not low precision for searching
    def rd(self):
        return RealField(300)(ZZ(self._data['disc_abs'])).nth_root(self.degree())

    # Return a nice string for the Galois group
    def galois_string(self, cache=None):
        if not self.haskey('galois_label'):
            return 'Not computed'
        n = self._data['degree']
        t = int(self._data['galois_label'].split('T')[1])
        return group_pretty_and_nTj(n, t, cache=cache)

    # Just return the t-number of the Galois group
    def galois_t(self):
        return int(self._data['galois_label'].split('T')[1])

    # return the Galois group
    def gg(self):
        if not self.haskey('gg'):
            self._data['gg'] = WebGaloisGroup.from_nt(self.degree(), self.galois_t())
        return self._data['gg']

    def is_galois(self):
        return self._data['is_galois']

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

    def poly(self, var="x"):
        return coeff_to_poly(self._data['coeffs'], var=var)

    def haskey(self, key):
        return self._data and self._data.get(key) is not None

    # Warning, this produces our preferred integral basis
    # But, if you have the sage number field do computations,
    # they will be in terms of a different basis
    def zk(self):
        if self.haskey('zk'):
            zkstrings = self._data['zk']
            return [str(u) for u in zkstrings]
        return list(pari(self.poly()).nfbasis())

    def monogenic(self):
        if self.haskey('monogenic'):
            if self._data['monogenic']==1:
                return 'Yes'
            if self._data['monogenic']==0:
                return 'Not computed'
            if self._data['monogenic']==-1:
                return 'No'
        return 'Not computed'

    def index(self):
        if self.haskey('index'):
            return r'$%d$'%self._data['index']
        return 'Not computed'

    def inessentialp(self):
        if self.haskey('inessentialp'):
            inep = self._data['inessentialp']
            if inep:
                return(', '.join([r'$%s$' % z for z in inep]))
            else:
                return('None')
        return 'Not computed'


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
            mypol = latex(coeff_to_poly(coef))
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
            numae = self.gg().arith_equivalent()
            galord = int(self.gg().order())
            sibcnts = self.gg()._data['siblings']
            repcounts = Counter()
            for s in sibcnts:
                repcounts[s[0][0]] += s[1]
            gc = 0
            if galord<48:
                del repcounts[galord]
                if self.degree() < galord:
                    gc = 1
            if numae>0:
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
        degsiblist = [[d, cnts[d], [dd[1] for dd in helpout if dd[0]==d] ] for d in sorted(cnts)]
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
        if not self.haskey('subfields'):
            return []
        sf = [z.replace('.',',') for z in self._data['subfields']]
        sfm = self._data['subfield_mults']
        return [[sf[j],sfm[j]] for j in range(len(sf))]
        return self._data['subs']

    def subfields_show(self):
        subs = self.subfields()
        if not subs:
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
        if not ugm:
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
            k1 = pari( "nfinit([%s,%s])" % (str(self.poly()),str(basis)) )
            self._data['gpK'] = k1
        return self._data['gpK']

    def generator_name(self):
        #Add special case code for the generator if desired:
        if self.gen_name=='phi':
            return r'\phi'
        else:
            return web_latex(self.gen_name)

    def variable_name(self):
        # For consistency with Sage number fields
        return self.gen_name

    def root_of_1_order(self):
        return self._data['torsion_order']

    def root_of_1_gen(self):
        return self._data['torsion_gen']

    def unit_rank(self):
        if not self.haskey('unit_rank'):
            sig = self.signature()
            self._data['unit_rank'] = sig[0] + sig[1] - 1
        return self._data['unit_rank']

    def regulator(self):
        if self.haskey('regulator'):
            return self._data['regulator']
        if self.unit_rank() == 0:
            return 1
        return na_text()

    def units(self):  # fundamental units
        res = None
        if self.haskey('units'):
            return self._data['units']
        elif self.unit_rank() == 0:
            res = []
        if res:
            res = res.replace('\\\\', '\\')
            return res
        return na_text()

    def cnf(self):
        if self.degree()==1:
            return r'=\frac{2^1\cdot (2\pi)^0 \cdot 1\cdot 1}{2\sqrt 1}=1$'
        if not self.haskey('class_group'):
            return r'$<td>  '+na_text()
        # Otherwise we should have what we need
        [r1,r2] = self.signature()
        reg = self.regulator()
        h = self.class_number()
        w = self.root_of_1_order()
        r1term= r'2^{%s}\cdot'% r1
        r2term= r'(2\pi)^{%s}\cdot'% r2
        disc = ZZ(self._data['disc_abs'])
        approx1 = r'\approx' if self.unit_rank()>0 else r'='
        ltx = r'%s\frac{%s%s %s \cdot %s}{%s\sqrt{%s}}'%(approx1,r1term,r2term,str(reg),h,w,disc)
        ltx += r'\approx %s$'%(2**r1*(2*RR(pi))**r2*reg*h/(w*sqrt(RR(disc))))
        return ltx

    def is_cm_field(self):
        return self._data['cm']

    def disc_factored_latex(self):
        D = self.disc()
        s = ''
        if D < 0:
            s = r'-\,'
        return s + factor_base_factorization_latex(factor_base_factor(D,self.ramified_primes()), cutoff=30)

    def web_poly(self):
        return pol_to_html(str(coeff_to_poly(self.coeffs())))

    def class_group_invariants(self, in_search_results=False):
        if not self.haskey('class_group'):
            return "n/a" if in_search_results else na_text()
        cg_list = self._data['class_group']
        if not cg_list:
            invs = 'trivial'
        else:
            invs = '$%s$'%str(cg_list)
        if in_search_results:
            invs += " " + self.short_grh_string()
        return invs

    def class_group_invariants_raw(self):
        if not self.haskey('class_group'):
            return [-1]
        return self._data['class_group']

    def class_group(self):
        if self.haskey('class_group'):
            cg_list = self._data['class_group']
            if not cg_list:
                return 'Trivial group, which has order $1$'
            cg_list = [r'C_{%s}' % z for z in cg_list]
            cg_string = r'\times '.join(cg_list)
            return '$%s$, which has order %s'%(cg_string, self.class_number_latex())
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

    def frobs(self):
        return self._data['frobs']

    def conductor(self):
        """ Computes the conductor if the extension is abelian.
            It raises an exception if the field is not abelian.
        """
        cond = self._data['conductor']
        if cond == 0: # Code for not an abelian field
            raise Exception('Invalid field for conductor')
        return ZZ(cond)

    def artin_reps(self, nfgg=None):
        if nfgg is not None:
            self._data["nfgg"] = nfgg
        else:
            if "nfgg" not in self._data:
                from lmfdb.artin_representations.math_classes import NumberFieldGaloisGroup
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
                from lmfdb.artin_representations.math_classes import NumberFieldGaloisGroup
                nfgg = NumberFieldGaloisGroup(self._data['coeffs'])
                self._data["nfgg"] = nfgg
            else:
                nfgg = self._data["nfgg"]

            cc = nfgg.conjugacy_classes()
            # cc is list, each has methods group, size, order, representative
            ccreps = [x.representative() for x in cc]
            ccns = [int(x.size()) for x in cc]
            ccreps = [Permutation(x).cycle_string() for x in ccreps]
            ccgen = '['+','.join(ccreps)+']'
            ar = nfgg.artin_representations() # list of artin reps from db
            arfull = nfgg.artin_representations_full_characters() # list of artin reps from db
            gap.set('fixed', 'function(a,b) if a*b=a then return 1; else return 0; fi; end;')
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

    def dirichlet_group(self):
        return self._data['dirichlet_group']

    # Helper for ramified algebras table
    def get_local_algebras(self):
        local_algs = self._data.get('local_algs', None)
        if local_algs is None:
            return None
        local_algebra_dict = {}
        R = PolynomialRing(QQ, 'x')
        for lab in local_algs:
            if lab[0] == 'm': # signals data about field not in lf db
                lab1 = lab[1:] # deletes marker m
                p, e, f, c = [int(z) for z in lab1.split('.')]
                deg = e*f
                if str(p) not in local_algebra_dict:
                    local_algebra_dict[str(p)] = [[deg,e,f,c]]
                else:
                    local_algebra_dict[str(p)].append([deg,e,f,c])
            else:
                LF = db.lf_fields.lookup(lab)
                f = latex(R(LF['coeffs']))
                p = LF['p']
                thisdat = [lab, f, LF['e'], LF['f'], LF['c'],
                    transitive_group_display_knowl(LF['galois_label']),
                    LF['t'], LF['u'], LF['slopes']]
                if str(p) not in local_algebra_dict:
                    local_algebra_dict[str(p)] = [thisdat]
                else:
                    local_algebra_dict[str(p)].append(thisdat)
        return local_algebra_dict

    def ramified_algebras_data(self):
        if 'local_algs' not in self._data:
            return dnc
        loc_alg_dict = self.get_local_algebras()
        return [loc_alg_dict.get(str(p), None) for p in self.ramified_primes()]

    def make_code_snippets(self):
         # read in code.yaml from numberfields directory:
        _curdir = os.path.dirname(os.path.abspath(__file__))
        self.code = yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)
        self.code['show'] = {'sage':'','pari':'', 'magma':''} # use default show names

        # Fill in placeholders for this specific field:
        for lang in ['sage', 'pari']:
            self.code['field'][lang] = self.code['field'][lang] % self.poly()
        self.code['field']['magma'] = self.code['field']['magma'] % self.coeffs()

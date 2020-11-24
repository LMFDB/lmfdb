from sage.all import CDF, round, ZZ, GCD
from collections import defaultdict
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey
import re

def round_to_half_str(num, fraction=2):
    num = round(num * 1.0 * fraction)
    if num % fraction == 0:
        return str(ZZ(num/fraction))
    else:
        return str(float(num/fraction))

def CCcmp(z1, z2):
    x1, y1 = z1.real(), z1.imag()
    x2, y2 = z2.real(), z2.imag()

    if x1 < x2:
        return -1
    elif x1 > x2:
        return 1
    elif y1 < y2:
        return -1
    elif y2 < y1:
        return 1
    return 0

def CCtuple(z):
    return (z.real(), z.imag().abs(), z.imag())


def spectral_str(x, conjugate=False):
    if conjugate:
        assert x <= 0
        x = -x
        res = "c"
    elif x < 0:
        x = -x
        res = "m"
    else:
        res = "p"
    if x == 0:
        res += "0"
    else:
        res += "%.2f" % x
    return res


def make_label(L, normalized=True):
    # special $-_.+!*'(),
    #L = db.lfunc_lfunctions.lucky({'Lhash':Lhash},['conductor', 'degree', 'central_character','gamma_factors','algebraic'])
    L = dict(L)

    # find inducing primitive character
    m, n = L['central_character']
    char = DirichletCharacter_conrey(DirichletGroup_conrey(m), n).primitive_character()
    central_character = "%d.%d" % (char.modulus(), char.number())

    GR, GC = L['gamma_factors']
    if normalized:
        analytic_normalization = 0
    else:
        analytic_normalization = L['motivic_weight']/2

    GR = [CDF(elt) + analytic_normalization for elt in GR]
    GC = [CDF(elt) + analytic_normalization for elt in GC]

    b, e = ZZ(L['conductor']).perfect_power()
    if e == 1:
        conductor = b
    else:
        conductor = "{}e{}".format(b, e)
    beginning = "-".join(map(str, [L['degree'], conductor, central_character]))


    GRcount = defaultdict(int)
    for elt in GR:
        GRcount[elt] += 1
    GCcount = defaultdict(int)
    for elt in GC:
        GCcount[elt] += 1
    # convert gamma_R to gamma_C
    for elt in GRcount:
        if elt + 1 in GRcount:
            while GRcount[elt] > 0 and GRcount[elt + 1] > 0:
                GCcount[elt] += 1
                GRcount[elt] -= 1
                GRcount[elt + 1] -= 1
    GR = sum([[m]*c for m, c in GRcount.items()], [])
    GC = sum([[m]*c for m, c in GCcount.items()], [])
    assert L['degree'] == len(GR) + 2*len(GC)
    GR.sort(key=CCtuple)
    GC.sort(key=CCtuple)

    # deal with real parts
    GR_real = [elt.real() for elt in GR]
    GC_real = [elt.real() for elt in GC]
    GRcount = defaultdict(int)
    for elt in GR_real:
        GRcount[elt] += 1
    GCcount = defaultdict(int)
    for elt in GC_real:
        GCcount[elt] += 1
    ge = GCD(GCD(list(GRcount.values())), GCD(list(GCcount.values())))
    if ge > 1:
        GR_real = sum(([k]*(v//ge) for k, v in GRcount.items()), [])
        GC_real = sum(([k]*(v//ge) for k, v in GCcount.items()), [])

    rs = ''.join(['r%d' % ZZ(elt.real()) for elt in GR_real])
    cs = ''.join(['c%d' % ZZ(elt.real()*2) for elt in GC_real])
    gammas = "-" + rs + cs
    if ge > 1:
        gammas += "e%d" % ge
    if L['algebraic']:
        end = "0"
    else:
        end = ""
        for G in [GR, GC]:
            for i, elt in enumerate(G):
                conjugate = False
                if elt.imag() <= 0 and i < len(G) - 1 and elt.conjugate() == G[i + 1]:
                    conjugate=True
                elif elt.imag() >= 0 and i > 0 and elt.conjugate() == G[i - 1]:
                    # we already listed this one as a conjugate
                    continue
                end += spectral_str(elt.imag(), conjugate=conjugate)
    label = beginning + gammas + "-" + end
    return label

def foobar(L):
    from collections import defaultdict
    def log_L_inf(s, mu, nu):
        return (sum([psi((s + elt)/2) for elt in  mu]) -len(mu)*log(pi))/2 + sum([psi(s + elt) for elt in nu]) - len(nu)*log(2*pi)
    def conductor_an(mu, nu):
        return (2*CDF(log_L_inf(1/2, mu, nu)).real()).exp()
    def conductor_ar(w, mu, nu):
        return (2*CDF(log_L_inf(1/2 + w/2, mu, nu)).real()).exp()
    def CCtuple(z):
        return (z.real(), z.imag().abs(), z.imag())


    #projection=['id', 'motivic_weight', 'gamma_factors', 'degree', 'conductor']
    #L = db.lfunc_lfunctions.lucky(projection=projection)
    w = ZZ(L['motivic_weight'])
    analytic_normalization = w/2
    mu = [CDF(elt) for elt in L['gamma_factors'][0]]
    nu = [CDF(elt) for elt in L['gamma_factors'][1]]
    assert L['degree'] == len(mu_ar) + 2*len(nu_ar)
    mu_count = defaultdict(int)
    for elt in mu_ar:
        mu_count[elt] += 1
    for elt in mu_count:
        if (elt + 1) in mu_count:
            while mu_count[elt] > 0 and mu_count[elt + 1] > 0:
                mu_count.append(elt)
                mu_count[elt] -= 1
                mu_count[elt + 1] -=1

    mu_ar = sum([[m]*c for m, c in mu_ar_count.items()], [])
    assert L['degree'] == len(mu) + 2*len(nu)
    mu.sort(key=CCtuple)
    nu.sort(key=CCtuple)
    newL = {}
    newL['id'] = L['id']
    newL['2mu_real'] = [ZZ(2*elt.real()) for elt in mu]
    newL['2nu_real'] = [ZZ(2*elt.real()) for elt in nu]
    newL['mu_imag'] = [elt.imag() for elt in mu]
    newL['nu_imag'] = [elt.imag() for elt in mu]
    newL['analytic_conductor'] = RDF(N*conductor_ar(w, mu, nu))


# out of date
#def break_label(label):
#    inv, rscs, spectral, smth = label.split('-')
#    deg, cond, char_mod, char_index = inv.split('.')
#    if 'p' in cond:
#        b, e = map(int, cond.split('p'))
#        cond = b**e
#    else:
#        cond = int(cond)
#
#    L = {'degree':int(deg),
#         'conductor': cond,
#         'central_character': ".".join([char_mod, char_index])}
#    GR = []
#    GC = []
#    for elt in re.findall('([r|c][0-9\.]+)', rscs):
#        if elt[0] == 'r':
#            G = GR
#            fraction = 1
#        else:
#            G = GC
#            fraction = 2
#        G.append(CC(elt[1:])/fraction)
#
#    if spectral == '0':
#        L['algebraic'] = True
#    else:
#        L['algebraic'] = False
#        for i, elt in enumerate(re.findall('([m|p][0-9\.]+)', spectral)):
#            if i > len(GR):
#                i -= len(GR)
#                G = GC
#            else:
#                G = GR
#            if elt[0] == 'p':
#                G[i] += CC(0,1) * CC(elt[1:])
#            elif elt[0] == 'm':
#                G[i] -= CC(0,1) * CC(elt[1:])
#    L['gamma_factors'] = [GR, GC]
#    return L

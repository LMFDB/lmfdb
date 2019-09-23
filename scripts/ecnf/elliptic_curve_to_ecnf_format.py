from sage.all import ZZ,QQ,PolynomialRing,EllipticCurve,pari
from lmfdb.WebNumberField import WebNumberField
from lmfdb.nfutils.psort import ideal_label
from scripts.ecnf.import_utils import make_curves_line

debug = False


def EllipticCurve_from_hoeij_data(line):
    """Given a line of the file "http://www.math.fsu.edu/~hoeij/files/X1N/LowDegreePlaces" 
    that is actually corresponding to an elliptic curve, this function returns the elliptic
    curve corresponding to this
    """
    Rx=PolynomialRing(QQ,'x')
    x = Rx.gen(0)
    Rxy = PolynomialRing(Rx,'y')
    y = Rxy.gen(0)
    
    N=ZZ(line.split(",")[0].split()[-1])
    x_rel=Rx(line.split(',')[-2][2:-4])
    assert x_rel.leading_coefficient()==1
    y_rel=line.split(',')[-1][1:-5]
    K = QQ.extension(x_rel,'x')
    x = K.gen(0)

    y_rel=Rxy(y_rel).change_ring(K)
    y_rel=y_rel/y_rel.leading_coefficient()
    if y_rel.degree()==1:
        y = - y_rel[0]
    else:
        #print "needing an extension!!!!"
        L = K.extension(y_rel,'y')
        y = L.gen(0)
        K = L
    #B=L.absolute_field('s')
    #f1,f2 = B.structure()
    #x,y=f2(x),f2(y)
    r = (x**2*y-x*y+y-1)/x/(x*y-1)
    s = (x*y-y+1)/x/y
    b = r*s*(r-1)
    c = s*(r-1)
    E=EllipticCurve([1-c,-b,-b,0,0])
    return N,E,K



def to_polredabs(K):
    """

    INPUT: 

    * "K" - a number field
    
    OUTPUT:

    * "phi" - an isomorphism K -> L, where L = QQ['x']/f and f a polynomial such that f = polredabs(f)
    """
    R = PolynomialRing(QQ,'x')
    x = R.gen(0)
    if K == QQ:
        L = QQ.extension(x,'w')
        return QQ.hom(L)
    L = K.absolute_field('a')
    m1 = L.structure()[1]
    f = L.absolute_polynomial()
    g = pari(f).polredabs(1)
    g,h = g[0].sage(locals={'x':x}),g[1].lift().sage(locals={'x':x})
    if debug:
        print 'f',f
        print 'g',g
        print 'h',h
    M = QQ.extension(g,'w')
    m2 = L.hom([h(M.gen(0))])
    return m2*m1
    
def base_change(E,phi):
    """
    INPUT:
    * "E" - an elliptic curve
        - phi - morphism whose domain is the base ring of E
    Output:
        - the elliptic curve obtained by applying phi to the coefficients of E
    """
    return EllipticCurve(phi.codomain(),map(phi,E.a_invariants()))

def EllipticCurve_polredabs_a_invariants(E,morphism=True):
    """
    Input:
        - E - an elliptic curve over a number field K
    Output:
        - [a1,a2,a3,a4,a6] - the a_invariants of E base changed along phi: K -> L 
                             where phi is the morphism from K to its polredabs field
    """
    K = E.base_field()
    phi = to_polredabs(K)
    ainvs = map(phi,E.a_invariants())
    if morphism:
        return ainvs,phi
    return ainvs
    #E_polred = base_change(E,phi)
    #assert E.conductor().norm() == E_polred.conductor().norm()
    #return E_polred
    
def EllipticCurve_polredabs(E):
    """
    Input:
        - E - an elliptic curve over a number field K
    Output:
        - E1 - the elliptic curve that is the base change of E along phi: K -> L 
                             where phi is the morphism from K to its polredabs field
    """
    return EllipticCurve(EllipticCurve_polredabs_a_invariants(E,False))
    
def EllipticCurve_to_ecnf_dict(E):
    """
    Make the dict that should be fed to `make_curves_line` in `lmfdb/scripts/ecnf/import_utils.py`.

    It sets `iso_label`, 'a' and `number` to '1' and `cm` and `base_change` to '?'

    INPUT:

    * E - A sage elliptic curve over a number field
    """
    E = EllipticCurve_polredabs(E)
    K = E.base_field()
    WNF = WebNumberField.from_polredabs(K.polynomial())
    ainvs = [map(str,ai) for ai in map(list,E.a_invariants())]
    conductor = E.conductor()
    conductor_str = "".join(str([conductor.norm()]+list(conductor.gens_two())).split())
    ec = {'field_label':WNF.label,
          'conductor_label':ideal_label(conductor),
          'iso_label':'a',
          'number':'1',
          'conductor_ideal':conductor_str,
          'conductor_norm':str(conductor.norm()),
          'ainvs':ainvs,
          'cm':'?',
          'base_change':'?'}
    return ec

def EllipticCurve_make_line(E):
    """
    Just make_curves_line applied to EllipticCurve_to_ecnf_dict

    INPUT:

    * E - A sage elliptic curve over a number field
    """
    return make_curves_line(EllipticCurve_to_ecnf_dict(E))

def hoeij_to_ecnf(url="http://www.math.fsu.edu/~hoeij/files/X1N/LowDegreePlaces",path="./curves.hoeij"):
    import urllib2
    file = urllib2.urlopen(url)
    data = file.read()
    file.close()
    lines = [l for l in data.splitlines() if l[:3] == "N =" and "[" in l]

    out_file = open(path,'w')
    try:
        for line in lines:
            E = EllipticCurve_from_hoeij_data(line)
            out_line =  EllipticCurve_make_line(E[1])
            out_file.write(out_line+"\n")
    finally:
        out_file.close()

# test sage script that uses pari to perform searches on Dirichlet characters
# useful for independently testing/verifying results of ListCharacters.py

from sage.all import gcd, pari

def match(q,n,mod=None,cond=None,ord=None,parity=None,primitive=None):
    """ returns True if chi_q(n,\cdot) matches search parameters """
    if mod and (q < mod[0] or q > mod[1]):
        return False
    pari(['g=idealstar(,%d,2)'%q, 'chi=znconreychar(g,%d)'%n])
    if cond:
        c = pari('znconreyconductor(g,chi)')
        c = int(c) if len(c) == 1 else int(c[0])
        if c < cond[0] or c > cond[1]:
            return False
    if ord:
        o = pari('charorder(g,chi)')
        if o < ord[0] or o > ord[1]:
            return False
    if parity:
        if parity == 'Even' and pari('zncharisodd(g,chi)'):
            return False
        if parity == 'Odd' and not pari('zncharisodd(g,chi)'):
            return False
        assert parity in ['Even','Odd']
    if primitive:
        if primitive == 'Yes' and pari('#znconreyconductor(g,chi)!=1'):
            return False
        if primitive == 'No' and pari('#znconreyconductor(g,chi)==1'):
            return False
        assert primitive in ['Yes','No']
    return True

def get_results(count,mod=None,cond=None,ord=None,parity=None,primitive=None):
    """ returns up to count characters (q,n) matching search parameters """
    res = []
    q = 1
    if not mod:
        mod = [1,99999] # ensure search is finite
    for q in xrange(mod[0],mod[1]+1):
        for n in xrange(1,max(2,q)):
            if gcd(q,n) == 1:
                if match(q,n,mod=mod,cond=cond,ord=ord,parity=parity,primitive=primitive):
                    res.append((q,n))
                    if len(res) == count:
                        return res
    return res

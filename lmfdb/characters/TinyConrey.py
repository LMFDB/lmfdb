from sage.all import gcd, Mod, Integer
from sage.misc.cachefunc import cached_method


def symbol_numerator(cond, parity):
    # Reference: Sect. 9.3, Montgomery, Hugh L; Vaughan, Robert C. (2007).
    # Multiplicative number theory. I. Classical theory. Cambridge Studies in
    # Advanced Mathematics 97
    #
    # Let F = Q(\sqrt(d)) with d a non zero squarefree integer then a real
    # Dirichlet character \chi(n) can be represented as a Kronecker symbol
    # (m / n) where { m  = d if # d = 1 mod 4 else m = 4d if d = 2,3 (mod) 4 }
    # and m is the discriminant of F. The conductor of \chi is |m|.
    #
    # symbol_numerator returns the appropriate Kronecker symbol depending on
    # the conductor of \chi.
    m = cond
    if cond % 2 == 1:
        if cond % 4 == 3:
            m = -cond
    elif cond % 8 == 4:
        # Fixed cond % 16 == 4 and cond % 16 == 12 were switched in the
        # previous version of the code.
        #
        # Let d be a non zero squarefree integer. If d  = 2,3 (mod) 4 and if
        # cond = 4d = 4 ( 4n + 2) or 4 (4n + 3) = 16 n + 8 or 16n + 12 then we
        # set m = cond.  On the other hand if d = 1 (mod) 4 and cond = 4d = 4
        # (4n +1) = 16n + 4 then we set m = -cond.
        if cond % 16 == 4:
            m = -cond
    elif cond % 16 == 8:
        if parity == 1:
            m = -cond
    else:
        return None
    return m


def kronecker_symbol(m):
    if m:
        return r'\(\displaystyle\left(\frac{%s}{\bullet}\right)\)' % (m)
    else:
        return None

###############################################################################
## Conrey character with no call to Jonathan's code
## in order to handle big moduli
##
class ConreyCharacter:
    """
    tiny implementation on Conrey index only
    """

    def __init__(self, modulus, number):
        assert gcd(modulus, number)==1
        self.modulus = Integer(modulus)
        self.number = Integer(number)

    @property
    def texname(self):
        from lmfdb.WebCharacter import WebDirichlet
        return WebDirichlet.char2tex(self.modulus, self.number)

    @cached_method
    def modfactor(self):
        return self.modulus.factor()

    @cached_method
    def conductor(self):
        cond = Integer(1);
        number = self.number
        for p,e in self.modfactor():
            mp = Mod(number, p**e);
            if mp == 1:
                continue
            if p == 2:
                cond = 4
                if number % 4 == 3:
                    mp = -mp
            else:
                cond *= p
                mp = mp**(p-1)
            while mp != 1:
                cond *= p
                mp = mp**p
        return cond

    def is_primitive(self):
        return self.conductor() == self.modulus

    @cached_method
    def parity(self):
        number = self.number
        par = 0;
        for p,e in self.modfactor():
            if p == 2:
                if number % 4 == 3:
                    par = 1 - par
            else:
                phi2 = (p-1)/Integer(2) * p **(e-1)
                if Mod(number, p ** e)**phi2 != 1:
                    par = 1 - par
        return par

    def is_odd(self):
        return self.parity() == 1

    def is_even(self):
        return self.parity() == 0

    @cached_method
    def multiplicative_order(self):
        return Mod(self.number, self.modulus).multiplicative_order()

    @property
    def order(self):
        return self.multiplicative_order()

    @cached_method
    def kronecker_symbol(self):
        c = self.conductor()
        p = self.parity()
        return kronecker_symbol(symbol_numerator(c, p))


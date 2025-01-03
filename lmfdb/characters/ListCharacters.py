# ListCharacters.py
import re
from sage.all import lcm, factor, Integers
from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.utils import flash_error, integer_divisors

# utility functions #


def modn_exponent(n):
    """ given a nonzero integer n, returns the group exponent of (Z/nZ)* """
    numer = lcm([(p - 1) * p**(e - 1) for p, e in factor(n)])
    return numer // (1 if n % 8 else 2)


def divisors_in_interval(n, a, b):
    """ given a nonzero integer n and an interval [a,b] returns a list of the divisors of n in [a,b] """
    return [d for d in integer_divisors(n) if a <= d <= b]


def parse_interval(arg, name):
    """ parses a user specified interval of positive integers (or a single integer), flashes errors and raises exceptions """
    a, b = 0, 0
    arg = arg.replace(' ', '')
    if re.match('^[0-9]+$', arg):
        a, b = (int(arg), int(arg))
    elif re.match('^[0-9]+-[0-9]+$', arg):
        s = arg.split('-')
        a, b = (int(s[0]), int(s[1]))
    elif re.match('^[0-9]+..[0-9]+$', arg):
        s = arg.split('..')
        a, b = (int(s[0]), int(s[1]))
    elif re.match(r'^\[[0-9]+..[0-9]+\]$', arg):
        s = arg[1:-1].split('..')
        a, b = (int(s[0]), int(s[1]))
    if a <= 0 or b < a:
        flash_error("%s is not a valid value for %s. It should be a positive integer (e.g. 7) or a nonempty range of positive integers (e.g. 1-10 or 1..10)", arg, name)
        raise ValueError("invalid " + name)
    return a, b


def parse_limit(arg):
    if not arg:
        return 50
    limit = -1
    arg = arg.replace(' ', '')
    if re.match('^[0-9]+$', arg):
        limit = int(arg)
    if limit > 100:
        flash_error("%s is not a valid limit on the number of results to display.  It should be a positive integer no greater than 100.", arg)
        raise ValueError("limit")
    return limit


def get_character_modulus(a, b, limit=7):
    """ this function is also used by lfunctions/LfunctionPlot.py """
    headers = list(range(1, limit))
    headers.append("more")
    entries = {}
    rows = list(range(a, b + 1))
    for row in rows:
        if row != 1:
            G = Integers(row).list_of_elements_of_multiplicative_group()
        else:
            G = [1]
        for chi_n in G:
            chi = ConreyCharacter(row, chi_n)
            multorder = chi.order
            if multorder <= limit:
                el = chi
                col = multorder
                entry = entries.get((row, col), [])
                entry.append(el)
                entries[(row, col)] = entry
    entries2 = {}

    def out(chi):
        return (chi.number, chi.is_primitive(),
                chi.order, chi.is_even())

    for k, v in entries.items():
        l = []
        v = sorted(v, key=lambda x: x.number)
        while v:
            e1 = v.pop(0)
            e1_num = e1.number
            inv_num = 1 if e1_num == 1 else e1_num.inverse_mod(e1.modulus)

            inv = ConreyCharacter(e1.modulus, inv_num)

            if e1_num == inv_num:
                l.append((out(e1),))
            else:
                l.append((out(e1), out(inv)))
                v = [x for x in v
                     if (x.modulus, x.number) != (inv.modulus, inv.number)]
        if k[1] == "more":
            l = sorted(l, key=lambda e: e[0][2])
        entries2[k] = l
    cols = headers
    return headers, entries2, rows, cols

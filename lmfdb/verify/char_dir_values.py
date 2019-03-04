
from sage.all import Integer, euler_phi

from lmfdb import db
from .verification import TableChecker, overall, slow

class char_dir_values(TableChecker):
    table = db.char_dir_values
    label = ['modulus', 'conrey_index']
    uniqueness_constraints = [['label'], label]

    @overall
    def check_total_count(self):
        """
        Total number of records should be sum of len(galois_orbit) over records in char_dir_orbits,
        """
        # Should be sum(euler_phi(n) for n in range(1,1001)) = 30397486
        return self.check_count(30397486)

    @overall
    def check_order_match(self):
        """
        order should match order in char_dir_orbits for this orbit_label
        """
        # TIME about 150s
        return self.check_crosstable('char_dir_orbits', 'order', 'orbit_label')

    @slow(projection=['modulus', 'order', 'values', 'values_gens'])
    def check_character_values(self, rec, verbose=False):
        """
        The x's listed in values and values_gens should be coprime to the modulus N in the label.
        For x's that appear in both values and values_gens, the value should be the same.
        """
        # TIME about 3000s for full table
        N = Integer(rec['modulus'])
        v2, u2 = N.val_unit(2)
        if v2 == 1:
            # Z/2 doesn't contribute generators, but 2 divides N
            adjust2 = -1
        elif v2 >= 3:
            # Z/8 and above requires two generators
            adjust2 = 1
        else:
            adjust2 = 0
        if N == 1:
            # The character stores a value in the case N=1
            ngens = 1
        else:
            ngens = len(N.factor()) + adjust2
        vals = rec['values']
        val_gens = rec['values_gens']
        val_gens_dict = dict(val_gens)
        if len(vals) != min(12, euler_phi(N)) or len(val_gens) != ngens:
            if verbose:
                print "Length failure", len(vals), euler_phi(N), len(val_gens), ngens
            return False
        if N > 2 and (vals[0][0] != N-1 or vals[1][0] != 1 or vals[1][1] != 0 or vals[0][1] not in [0, rec['order']//2]):
            if verbose:
                print "Initial value failure", N, rec['order'], vals[:2]
            return False
        if any(N.gcd(g) > 1 for g, gval in val_gens+vals):
            if verbose:
                print "gcd failure", [g for g, gval in val_gens+vals if N.gcd(g) > 1]
            return False
        for g, val in vals:
            if g in val_gens_dict and val != val_gens_dict[g]:
                if verbose:
                    print "Mismatch failure", g, val, val_gens_dict[g]
                return False
        return True

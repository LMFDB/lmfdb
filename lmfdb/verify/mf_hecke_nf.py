
from sage.all import prime_pi, mod, euler_phi, prime_range

from lmfdb.backend.database import db, SQL
from .mf import MfChecker, integer_types
from .verification import overall, slow

class mf_hecke_nf(MfChecker):
    table = db.mf_hecke_nf

    @overall
    def check_bijection(self):
        # TIME about 20s
        # there should be a record present for every record in mf_newforms that has field_poly set (and no others, check count)
        return (self.check_crosstable_count('mf_newforms', 1, 'label') +
                self.check_count(db.mf_newforms.count({'field_poly':{'$exists':True}})))

    @overall
    def check_hecke_orbit_code_newforms(self):
        # TIME about 1s
        # check that label matches hecke_orbit_code and is present in mf_newforms
        return self.check_crosstable('mf_newforms', 'hecke_orbit_code', 'label')

    @overall
    def check_field_poly(self):
        # TIME about 10s
        # check that field_poly matches field_poly in mf_newforms
        return self.check_crosstable('mf_newforms', 'field_poly', 'label')

    @overall
    def check_hecke_ring_rank(self):
        # check that hecke_ring_rank = deg(field_poly)
        return self.check_array_len_col('field_poly', 'hecke_ring_rank', shift=1)

    @overall
    def check_hecke_ring_power_basis_set(self):
        # if hecke_ring_power_basis is set, check that hecke_ring_cyclotomic_generator is 0 and hecke_ring_numerators, ... are null
        return self.check_values({'hecke_ring_cyclotomic_generator':0,
                                  'hecke_ring_numerators':None,
                                  'hecke_ring_denominators':None,
                                  'hecke_ring_inverse_numerators':None,
                                  'hecke_ring_inverse_denominators':None},
                                 {'hecke_ring_power_basis':True})

    @overall
    def check_hecke_ring_cyclotomic_generator(self):
        # if hecke_ring_cyclotomic_generator is greater than 0 check that hecke_ring_power_basis is false and hecke_ring_numerators, ... are null, and that field_poly_is_cyclotomic is set in mf_newforms record.
        return self.check_values({'hecke_ring_power_basis':False,
                                  'hecke_ring_numerators':None,
                                  'hecke_ring_denominators':None,
                                  'hecke_ring_inverse_numerators':None,
                                  'hecke_ring_inverse_denominators':None},
                                 {'hecke_ring_cyclotomic_generator':{'$gt':0}})


    @overall
    def check_field_poly_is_cyclotomic(self):
        # TIME about 2s
        # if hecke_ring_cyclotomic_generator > 0, check that field_poly_is_cyclotomic is set in mf_newforms record.
        # could be done with _run_crosstable from mf_newforms
        cur = db._execute(SQL("SELECT t1.label FROM mf_hecke_nf t1, mf_newforms t2 WHERE NOT t2.field_poly_is_cyclotomic AND t1.hecke_ring_cyclotomic_generator > 0 AND t1.label = t2.label LIMIT %s"), [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_maxp(self):
        # check that maxp is at least 997
        return self._run_query(SQL('maxp < 997'))

    @slow(projection=['label', 'level', 'char_orbit_index', 'an', 'ap', 'maxp', 'hecke_ring_cyclotomic_generator', 'hecke_ring_rank', 'hecke_ring_character_values'])
    def check_hecke_ring_character_values_and_an(self, rec):
        # TIME about 4000s for full table
        # check that hecke_ring_character_values has the correct format, depending on whether hecke_ring_cyclotomic_generator is set or not
        # check that an has length 100 and that each entry is either a list of integers of length hecke_ring_rank (if hecke_ring_cyclotomic_generator=0) or a list of pairs
        # check that ap has length pi(maxp) and that each entry is formatted correctly (as for an)
        an = rec['an']
        if len(an) != 100:
            return False
        ap = rec['ap']
        maxp = rec['maxp']
        if len(ap) != prime_pi(maxp):
            return False
        if maxp < 997:
            return False
        m = rec['hecke_ring_cyclotomic_generator']
        d = rec['hecke_ring_rank']
        def check_val(val):
            if not isinstance(val, list):
                return False
            if m == 0:
                return len(val) == d and all(isinstance(c, integer_types) for c in val)
            else:
                for pair in val:
                    if len(pair) != 2:
                        return False
                    if not isinstance(pair[0], integer_types):
                        return False
                    e = pair[1]
                    if not (isinstance(e, integer_types) and 0 <= 2*e < m):
                        return False
                return True
        if not all(check_val(a) for a in an):
            return False
        if not all(check_val(a) for a in ap):
            return False
        for p, a in zip(prime_range(100), ap):
            if a != an[p-1]:
                return False
        if rec['char_orbit_index'] != 1:
            if rec.get('hecke_ring_character_values') is None:
                return False
            N = rec['level']
            total_order = 1
            for g, val in rec['hecke_ring_character_values']:
                total_order *= mod(g, N).multiplicative_order()
                if not check_val(val):
                    return False
            return total_order == euler_phi(N)
        return True

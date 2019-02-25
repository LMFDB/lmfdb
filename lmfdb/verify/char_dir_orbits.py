

from dirichlet_conrey import DirichletGroup_conrey
from sage.all import euler_phi

from lmfdb.backend.database import db, SQL
from .verification import TableChecker, overall, overall_long, fast, slow

class char_dir_orbits(TableChecker):
    table = db.char_dir_orbits
    label_col = 'orbit_label'
    label = ['modulus', 'orbit_index']
    uniqueness_constraints = [[table._label_col], label]

    @overall
    def check_total_count(self):
        # there should be a record present for every character orbit of modulus up to 10,000 (there are 768,512)
        return self.check_count(768512)

    @overall
    def check_trivial(self):
        # TIME about 1s
        # check that orbit_index=1 if and only if order=1
        return self.check_iff({'orbit_index':1}, {'order':1})

    @overall
    def check_conductor_divides(self):
        # TIME about 2s
        # check that conductor divides modulus
        return self.check_divisible('modulus', 'conductor')

    @overall
    def check_primitive(self):
        # TIME about 5s
        # check that orbit specified by conductor,prim_orbit_index is present
        return self.check_crosstable_count('char_dir_orbits', 1, ['conductor', 'prim_orbit_index'], ['modulus', 'orbit_index'])

    @overall
    def check_is_real(self):
        # TIME about 1s
        # check that is_real is true if and only if order <= 2
        return self.check_iff({'is_real':True}, {'order':{'$lte':2}})

    @overall
    def check_galois_orbit_len(self):
        # TIME about 2s
        # check that char_degee = len(Galois_orbit)
        return self.check_array_len_col('galois_orbit', 'char_degree')

    @overall_long
    def check_char_dir_values_agg(self):
        # TIME about 750s
        # The number of entries in char_dir_values matching a given orbit_label should be char_degree
        return self.check_crosstable_count('char_dir_values', 'char_degree', 'orbit_label')

    @overall
    def check_is_primitive(self):
        # TIME about 1s
        # check that is_primitive is true if and only if modulus=conductor
        # Since we can't use constraint on modulus=conductor, we construct the constraint directly
        return self.check_iff({'is_primitive': True}, SQL("modulus = conductor"))

    @overall_long
    def check_galois_orbit(self):
        # TIME about 600s
        # galois_orbit should be the list of conrey_indexes from char_dir_values with this orbit_label Conrey index n in label should appear in galois_orbit for record in char_dir_orbits with this orbit_label
        return self.check_crosstable_aggregate('char_dir_values', 'galois_orbit', 'orbit_label', 'conrey_index')

    @overall_long
    def check_parity_value(self):
        # TIME about 500s
        # the value on -1 should agree with the parity for this char_orbit_index in char_dir_orbits
        return (self._run_crosstable(SQL("2*t2.values[1][2]"), 'char_dir_values', 'order', 'orbit_label', constraint={'parity':-1}, subselect_wrapper="ALL") +
                self._run_crosstable(SQL("t2.values[1][2]"), 'char_dir_values', 0, 'orbit_label', constraint={'parity':1}, subselect_wrapper="ALL"))

    @fast(projection=['char_degree', 'order'])
    def check_char_degree(self, rec):
        # TIME about 20s for full table
        # check that char_degree = euler_phi(order)
        return rec['char_degree'] == euler_phi(rec['order'])

    @slow(ratio=0.01, projection=['modulus', 'conductor', 'order', 'parity', 'galois_orbit'])
    def check_order_parity(self, rec):
        # TIME about 30000s for full table
        # check order and parity by constructing a Conrey character in Sage (use the first index in galois_orbit)
        char = DirichletGroup_conrey(rec['modulus'])[rec['galois_orbit'][0]]
        parity = 1 if char.is_even() else -1
        return parity == rec['parity'] and char.conductor() == rec['conductor'] and char.multiplicative_order() == rec['order']

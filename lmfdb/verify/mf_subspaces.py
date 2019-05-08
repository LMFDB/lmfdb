
from lmfdb import db
from .mf import SubspacesChecker
from .verification import overall

class mf_subspaces(SubspacesChecker):
    table = db.mf_subspaces
    label = ['level', 'weight', 'char_orbit_label']
    uniqueness_constraints = [['label', 'sub_label']]

    @overall
    def check_sub_label(self):
        """
        check that sub_label matches matches sub_level, weight, sub_char_orbit_index
        """
        # TIME about 2s
        return self.check_string_concatenation('sub_label', ['sub_level', 'weight', 'sub_char_orbit_label'])

    @overall
    def check_char_orbit_label(self):
        """
        check that char_orbit_label matches char_orbit_index
        """
        # TIME about 20s
        return self.check_letter_code('char_orbit_index', 'char_orbit_label')

    @overall
    def check_sub_char_orbit_label(self):
        """
        check that sub_char_orbit_label matches sub_char_orbit_index
        """
        # TIME about 20s
        return self.check_letter_code('sub_char_orbit_index', 'sub_char_orbit_label')

    @overall
    def check_conrey_indexes(self):
        """
        check that conrey_indexes matches galois_orbit for char_orbit_label in char_dir_orbits
        """
        # TIME about 10s
        return self.check_crosstable('char_dir_orbits', 'conrey_indexes', ['level', 'char_orbit_index'], 'galois_orbit', ['modulus', 'orbit_index'])

    @overall
    def check_sub_conrey_indexes(self):
        """
        check that sub_conrey_indexes matches galois_orbit for sub_char_orbit_label in char_dir_orbits
        """
        # TIME about 10s
        return self.check_crosstable('char_dir_orbits', 'sub_conrey_indexes', ['sub_level', 'sub_char_orbit_index'], 'galois_orbit', ['modulus', 'orbit_index'])

    @overall
    def check_sub_dim(self):
        """
        check that sub_dim = dim S_k^new(sub_level, sub_chi)
        """
        # TIME about 20s
        return self.check_crosstable('mf_newspaces', 'sub_dim', 'sub_label', 'dim', 'label')

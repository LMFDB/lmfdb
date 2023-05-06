
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
    def check_sub_dim(self):
        """
        check that sub_dim = dim S_k^new(sub_level, sub_chi)
        """
        # TIME about 20s
        return self.check_crosstable('mf_newspaces', 'sub_dim', 'sub_label', 'dim', 'label')

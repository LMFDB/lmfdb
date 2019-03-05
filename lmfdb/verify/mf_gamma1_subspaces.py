
from lmfdb import db
from .mf import SubspacesChecker
from .verification import overall

class mf_gamma1_subspaces(SubspacesChecker):
    table = db.mf_gamma1_subspaces
    label = ['level', 'weight']
    uniqueness_constraints = [['label', 'sub_level']]

    @overall
    def check_sub_dim(self):
        """
        check that sub_dim = dim S_k^new(Gamma1(sub_level))
        """
        return self.check_crosstable('mf_gamma1', 'sub_dim', ['sub_level', 'weight'], 'dim', ['level', 'weight'])

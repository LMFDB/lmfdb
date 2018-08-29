# See genus2_curves/web_g2c.py
# See templates/space.html for how functions are called


from lmfdb.db_backend import db

class WebNewformSpace(object):
    def __init__(self, data):
        # Need to set mf_dim, eis_dim, cusp_dim, new_dim, old_dim
        pass

    @staticmethod
    def by_label(label):
        # search in db.mf_newforms
        pass

    def mf_latex(self):
        pass

    def eis_latex(self):
        pass

    def cusp_latex(self):
        pass

    def new_latex(self):
        pass

    def old_latex(self):
        pass

    def decomposition(self):
        # returns a list of 5-tuples (label, url, dim, field, qexp
        # Field may need to be augmented to support pretty printing, minimal poly, knowl, etc.
        pass

    def oldspace_decomposition(self):
        # Returns a latex string giving the decomposition of the old part.  These come from levels M dividing N, with the conductor of the character dividing M.
        pass

# See genus2_curves/web_g2c.py
# See templates/space.html for how functions are called

from lmfdb.db_backend import db
from web_newform import WebNewform
from sage.all import latex, ZZ
import re
LABEL_RE = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$") # not putting in o currently
def valid_label(label):
    return LABEL_RE.match(label)

class WebNewformSpace(object):
    def __init__(self, data):
        # Need to set mf_dim, eis_dim, cusp_dim, new_dim, old_dim
        self.__dict__.update(data)
        newforms = db.mf_newforms.search({'space_label':self.label}, projection=2)
        self.newforms = [WebNewform(data, self) for data in newforms]
        oldspaces = db.mf_oldsubs.search({'space_label':self.label}, ['new_label', 'new_minimal_conrey'])
        self.oldspaces = []
        for old in oldspaces:
            old_label = old['new_label']
            conrey = old['new_minimal_conrey']
            N, k, i = map(int, valid_label(old_label).groups())
            self.oldspaces.append((N, k, i, conrey))
        self.old_dim = self.cusp_dim - self.dim
        self.properties = [] # properties box
        self.bread = [] # bread
        self.title = "Newform Space S_%d(%d,[%d])"%(self.weight, self.level, self.conrey_labels[0])
        self.friends = []

    @staticmethod
    def by_label(label):
        """
        Searches for a specific modular forms space by its label.
        Constructs the WebNewformSpace object if the space is found, raises an error otherwise
        """
        if not valid_label(label):
            raise ValueError("Invalid modular forms space label %s." % label)
        data = db.mf_newspaces.lookup(label)
        if data is None:
            raise ValueError("Space %s not found" % label)
        return WebNewformSpace(data)

    def mf_latex(self):
        return r"M_{%d}(%d, [%d])"%(self.weight, self.level, self.conrey_labels[0])

    def eis_latex(self):
        return r"E_{%d}(%d, [%d])"%(self.weight, self.level, self.conrey_labels[0])

    def eis_new_latex(self):
        return r"E_{%d}^{new}(%d, [%d])"%(self.weight, self.level, self.conrey_labels[0])

    def cusp_latex(self):
        return r"S_{%d}(%d, [%d])"%(self.weight, self.level, self.conrey_labels[0])

    def new_latex(self):
        return r"S_{%d}^{new}(%d, [%d])"%(self.weight, self.level, self.conrey_labels[0])

    def old_latex(self):
        return r"S_{%d}^{old}(%d, [%d])"%(self.weight, self.level, self.conrey_labels[0])

    def decomposition(self):
        from lmfdb.modular_forms.elliptic_modular_forms.main import url_for_newform_label
        # returns a list of 5-tuples (label, url, dim, field, qexp)
        # Field may need to be augmented to support pretty printing, minimal poly, knowl, etc.
        for newform in self.newforms:
            yield (newform.label, url_for_newform_label(newform.label), newform.dim, newform.nf_label, newform.q_expansion('oneline'))

    def oldspace_decomposition(self):
        # Returns a latex string giving the decomposition of the old part.  These come from levels M dividing N, with the conductor of the character dividing M.
        template = "S_{{{k}}}^{{\mathrm{{new}}}}({N}, [\chi_{{{chi_modulus}}}({chi_index}, \cdot)^{{\oplus 2}}"
        return "\oplus".join(template.format(k=k,
                                             N=N,
                                             chi_modulus=N,
                                             chi_index=conrey)
                             for N,k,i,conrey in self.oldspaces)

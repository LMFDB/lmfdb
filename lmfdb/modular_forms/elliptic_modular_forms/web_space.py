# See genus2_curves/web_g2c.py
# See templates/space.html for how functions are called


from lmfdb.db_backend import db
from sage.all import latex, ZZ

class WebNewformSpace(object):
    def __init__(self, newspace, newforms, oldspaces):
        # Need to set mf_dim, eis_dim, cusp_dim, new_dim, old_dim
        self.make_object(newspace, newforms, oldspaces)

    @staticmethod
    def by_label(label):
        """
        Searches for a specific modular forms space by its label.
        Constructs the WebModformSpace object if the space is found, raises an error otherwise
        """
        try:
            slabel = label.split(".")
            if len(slabel) == 3:
                newspace = db.mf_newspaces.lookup(label)
            else:
                raise ValueError("Invalid modular forms space label %s." % label)
        except AttributeError:
            raise ValueError("Invalid modular forms space label %s." % label)
        oldspaces = list(db.mf_oldsubs.search({"space_label": newspace['label']}))
        newforms = list(db.mf_newforms.search({"level": newspace['level'], "weight": newspace['weight'], "char_orbit": newspace['char_orbit']})) # TODO change this to search on space_label
        for newform in newforms:
            newform['qexp'] = list(db.mf_hecke_nf.search({"hecke_orbit_code": newform['hecke_orbit_code']}, ['n','an'], sort=['n'])) # TODO use webnewform instead
        return WebG2C(newspace, newforms, oldspaces)


    def make_object(self, newspace, newforms, oldspaces):
        from lmfdb.modular_forms.elliptic_modular_forms.main import url_for_newspace_label # TODO remove if unused

        # TODO use self._dict.update like david does!
        data = self.data = {}

        data['label'] = newspace['label']
        data['slabel'] = data['label'].split('.')

        data['level'] = ZZ(newspace['level'])
        data['weight'] = ZZ(newspace['weight'])
        data['char_orbit'] = ZZ(newspace['char_orbit'])
        data['minimal_conrey'] = ZZ(newspace['minimal_conrey'])
        data['conductor'] = ZZ(newspace['conductor'])
        data['sturm_bound'] = ZZ(newspace['sturm_bound'])
        data['dim'] = ZZ(newspace['dim'])
        data['hecke_orbit_dims'] = newspace['hecke_orbit_dims']
        data['eis_dim'] = ZZ(newspace['eis_dim'])
        data['cusp_dim'] = ZZ(newspace['cusp_dim'])
        data['mf_dim'] = ZZ(newspace['mf_dim'])
        data['newforms'] = newforms
        data['oldspaces'] = oldspaces

    def mf_latex(self):
        pass

    def eis_latex(self):
        pass

    def cusp_latex(self):
        pass

    def new_latex(self):
        return "S_{%d}"

    def old_latex(self):
        pass

    def decomposition(self):
        from lmfdb.modular_forms.elliptic_modular_forms.main import url_for_newform_label
        # returns a list of 5-tuples (label, url, dim, field, qexp)
        # Field may need to be augmented to support pretty printing, minimal poly, knowl, etc.
        for newform in self.data['newforms']:
            yield (newform['label'], url_for_newform_label(newform['label']), newform['dim'], newform['nf_label'], )

    def oldspace_decomposition(self):
        # Returns a latex string giving the decomposition of the old part.  These come from levels M dividing N, with the conductor of the character dividing M.
        return "\oplus".join("S_{{{k}}}^{{\mathrm{{new}}}}({N}, [\chi_{{{chi_modulus}}}({chi_index}, \cdot)^{{\oplus 2}}".format(k=old['weight'], N=old['level'], chi_modulus=old['level'], chi_index=old['minimal_conrey']) for old in self.data['oldspaces'])

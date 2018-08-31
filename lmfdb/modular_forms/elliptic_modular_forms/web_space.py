# See genus2_curves/web_g2c.py
# See templates/space.html for how functions are called

from lmfdb.db_backend import db
from web_newform import WebNewform
from sage.all import latex, ZZ
from flask import url_for
import re
from collections import defaultdict
LABEL_RE = re.compile(r"^([0-9]+)\.([0-9]+)\.([a-z]+)$") # not putting in o currently
GAMMA1_RE = re.compile(r"^([0-9]+)\.([0-9]+)$")
def valid_label(label):
    return LABEL_RE.match(label)
def valid_gamma1(label):
    return GAMMA1_RE.match(label)

def common_latex(level, weight, conrey=None, S="S", t=0, typ="", symbolic_chi=False):
    if conrey is None or conrey == 1:
        char = ""
    elif symbolic_chi:
        char = r", \chi"
    else:
        char = r", [\chi_{{{level}}}({conrey}, \cdot)]".format(level=level, conrey=conrey)
    if typ:
        typ = "^{{{typ}}}".format(typ=typ)
    ans = r"{S}_{{{k}}}{typ}(\Gamma_{t}({N}){char})"
    return ans.format(S=S, k=weight, typ=typ, t=t, N=level, char=char)

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
        self.title = r"Space of Modular Forms \(%s\)"%(self.mf_latex())
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

    def _vec(self):
        return [self.level, self.weight, self.conrey_labels[0]]

    def mf_latex(self):
        return common_latex(*(self._vec() + ["M"]))

    def eis_latex(self):
        return common_latex(*(self._vec() + ["E"]))

    def eis_new_latex(self):
        return common_latex(*(self._vec() + ["E",0,"new"]))

    def cusp_latex(self):
        return common_latex(*(self._vec() + ["S"]))

    def new_latex(self):
        return common_latex(*(self._vec() + ["S",0,"new"]))

    def old_latex(self):
        return common_latex(*(self._vec() + ["S",0,"old"]))

    def decomposition(self):
        from lmfdb.modular_forms.elliptic_modular_forms.main import url_for_newform_label
        # returns a list of 5-tuples (label, url, dim, field, qexp)
        # Field may need to be augmented to support pretty printing, minimal poly, knowl, etc.
        for newform in self.newforms:
            yield (newform.label, url_for_newform_label(newform.label), newform.dim, newform.__dict__.get('nf_label') or "Not in LMFDB", newform.q_expansion('oneline'))

    def oldspace_decomposition(self):
        # Returns a latex string giving the decomposition of the old part.  These come from levels M dividing N, with the conductor of the character dividing M.
        template = r"<a href={url}>\({old}\)</a>\(^{{\oplus {mult}}}\)"
        return r"\(\oplus\)".join(template.format(old=common_latex(N, k, conrey, typ="new"),
                                                  url=url_for(".render_space_webpage",label="{N}.{k}.{i}".format(N=N, k=k, i=i)),
                                                  mult=len(ZZ(self.level//N).divisors()))
                             for N,k,i,conrey in self.oldspaces)

class WebGamma1Space(object):
    def __init__(self, level, weight):
        self.level = level
        self.weight = weight
        #dirchars = db.char_dir_orbits.search({'modulus':level},['orbit_index', 'parity', 'galois_orbit', 'cyc_degree'], sort=[])
        newspaces = list(db.mf_newspaces.search({'level':level, 'weight':weight}))
        self.mf_dim = sum(space['mf_dim']*space['cyc_degree'] for space in newspaces)
        self.eis_dim = sum(space['eis_dim']*space['cyc_degree'] for space in newspaces)
        self.eis_new_dim = sum(space['eis_new_dim']*space['cyc_degree'] for space in newspaces)
        self.cusp_dim = sum(space['cusp_dim']*space['cyc_degree'] for space in newspaces)
        self.new_dim = sum(space['dim']*space['cyc_degree'] for space in newspaces)
        self.old_dim = sum((space['cusp_dim']-space['dim'])*space['cyc_degree'] for space in newspaces)
        newforms = list(db.mf_newforms.search({'level':level, 'weight':weight}, ['space_label', 'dim', 'level', 'char_orbit', 'hecke_orbit']))
        self.decomp = [(space, [form for form in newforms if form['space_label'] == space['label']])
                       for space in newspaces]
        #print "spaces", newspaces
        #print "forms", newforms
        #print "decomp", self.decomp
        print self.decomposition()
        self.properties = [] # properties box
        self.bread = [] # bread
        self.title = r"Space of Modular Forms \(%s\)"%(self.mf_latex())
        self.friends = []

    @staticmethod
    def by_label(label):
        match = valid_gamma1(label)
        if not match:
            raise ValueError("Invalid modular forms space label %s." % label)
        level, weight = map(int, match.groups())
        return WebGamma1Space(level, weight)

    def _vec(self):
        return [self.level, self.weight, None]

    def mf_latex(self):
        return common_latex(*(self._vec() + ["M",1]))

    def eis_latex(self):
        return common_latex(*(self._vec() + ["E",1]))

    def eis_new_latex(self):
        return common_latex(*(self._vec() + ["E",1,"new"]))

    def cusp_latex(self):
        return common_latex(*(self._vec() + ["S",1]))

    def new_latex(self):
        return common_latex(*(self._vec() + ["S",1,"new"]))

    def old_latex(self):
        return common_latex(*(self._vec() + ["S",1,"old"]))

    def header_latex(self):
        return r'\(' + common_latex(*(self._vec() + ["S",0,"new",True])) + '\)'

    def _link(self, N, i=None, typ="new", label=True):
        if label:
            if i is None:
                name = "{N}.{k}".format(N=N, k=self.weight)
            else:
                name = "{N}.{k}.{i}".format(N=N, k=self.weight, i=i)
        else:
            t = 1 if i is None else 0
            name = r"\(%s\)" % common_latex(N, self.weight, i, t=t, typ=typ)
        if i is None:
            url = url_for(".by_url_full_gammma1_space_label",
                          level=N, weight=self.weight)
        else:
            url = url_for(".by_url_space_label",
                          level=N, weight=self.weight, char_orbit=i)
        return r"<a href={url}>{name}</a>".format(url=url, name=name)

    def oldspace_decomposition(self):
        template = r"{link}\(^{{\oplus {mult}}}\)"
        return r"\(\oplus\)".join(template.format(link=self._link(N, label=False),
                                                  mult=len(ZZ(self.level//N).divisors()))
                                  for N in ZZ(self.level).divisors())

    def decomposition(self):
        # returns a list of 6-tuples chi_rep, num_chi, parity, space, dim, newform
        ans = []
        for space, forms in self.decomp:
            chi_rep = r"\( \chi_{{{N}}}({chi_rep}, \cdot) \)".format(N=space['level'],
                                                                     chi_rep=space['conrey_labels'][0])
            num_chi = space['cyc_degree']
            parity = "even" if space['parity'] == 1 else "odd"
            link = self._link(space['level'], space['char_orbit'])
            if not forms:
                ans.append((chi_rep, num_chi, parity, link, 0, "No newforms"))
            else:
                form = forms[0]
                ans.append((chi_rep, num_chi, parity, link, form['dim'],
                            self._link(form['level'], form['char_orbit'], form['hecke_orbit'])))
                for form in forms[1:]:
                    ans.append(("", "", "", "", form['dim'],
                                self._link(form['level'], form['char_orbit'], form['hecke_orbit'])))
        return ans

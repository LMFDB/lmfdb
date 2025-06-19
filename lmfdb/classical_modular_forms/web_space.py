# See genus2_curves/web_g2c.py
# See templates/space.html for how functions are called

from lmfdb import db
from sage.all import ZZ, prod, gp, divisors, number_of_divisors
from sage.modular.dims import sturm_bound
from sage.modules.free_module_element import vector
from sage.databases.cremona import cremona_letter_code
from lmfdb.number_fields.web_number_field import nf_display_knowl, cyclolookup, rcyclolookup
from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.utils import (
    display_knowl, raw_typeset_qexp,
    web_latex_factored_integer, prop_int_pretty)
from flask import url_for
import re
NEWLABEL_RE = re.compile(r"^([0-9]+)\.([0-9]+)\.([a-z]+)$")
OLDLABEL_RE = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")
GAMMA1_RE = re.compile(r"^([0-9]+)\.([0-9]+)$")
def valid_label(label):
    return NEWLABEL_RE.match(label) or OLDLABEL_RE.match(label)
def valid_gamma1(label):
    return GAMMA1_RE.match(label)

def get_bread(**kwds):
    # Should be called with either search=True or an initial segment of the links below
    links = [('level', 'Level %s', 'cmf.by_url_level'),
             ('weight', 'Weight %s', 'cmf.by_url_full_gammma1_space_label'),
             ('char_orbit_label', 'Character orbit %s', 'cmf.by_url_space_label'),
             ('hecke_orbit', 'Newform orbit %s', 'cmf.by_url_newform_label'),
             ('embedding_label', 'Embedding %s', 'cmf.by_url_newform_conrey5')]
    bread = [('Modular forms', url_for('modular_forms')),
             ('Classical', url_for("cmf.index"))]
    if 'other' in kwds:
        if isinstance(kwds['other'], str):
            return bread + [(kwds['other'], ' ')]
        else:
            return bread + kwds['other']
    url_kwds = {}
    for key, display, link in links:
        if key not in kwds:
            return bread
        url_kwds[key] = kwds[key]
        bread.append((display % kwds[key], url_for(link, **url_kwds)))
    return bread
def get_search_bread():
    return get_bread(other='Search results')
def get_dim_bread():
    return get_bread(other='Dimension table')

def newform_search_link(text, title=None, **kwd):
    query = '&'.join('%s=%s' % (key, val) for key, val in kwd.items())
    link = "%s?%s" % (url_for('.index'), query)
    return "<a href='%s'%s>%s</a>" % (link, "" if title is None else " title='%s'" % title, text)

def cyc_display(m, d, real_sub):
    r"""
    Used to display cyclotomic fields and their real subfields.

    INPUT:

    - ``m`` -- the order of the root of unity generating the field.
    - ``d`` -- the degree of the cyclotomic field over Q
    - ``real_sub`` -- whether to display the real subfield instead.

    OUTPUT:

    A string or knowl showing the cyclotomic field Q(\zeta_m) or Q(\zeta_m)^+.
    """
    if d == 1:
        name = r'\(\Q\)'
    elif m == 4:
        name = r'\(\Q(i)\)'
    elif real_sub:
        name = r'\(\Q(\zeta_{%s})^+\)' % m
    else:
        name = r'\(\Q(\zeta_{%s})\)' % m
    if d < 24:
        if real_sub:
            label = rcyclolookup[m]
        else:
            label = cyclolookup[m]
        return nf_display_knowl(label, name=name)
    else:
        return name

# This function is for backward compatibility when we do not have all the data
def ALdim_new_cusp_table(al_dims, level, weight):
    def sign_char(x): return "-" if x else "+"
    def url_sign_char(x): return "-" if x else "%2B"
    primes = ZZ(level).prime_divisors()
    num_primes = len(primes)
    header = [r"<th class='center'>\(%s\)</th>" % p for p in primes]
    if num_primes > 1:
        header.append(r"<th class='center'>%s</th>" % (display_knowl('cmf.fricke', title='Fricke').replace('"',"'")))
    header.append('<th>Dim</th>')
    rows = []
    fricke = [0,0]
    for i, dim in enumerate(al_dims):
        if dim == 0:
            continue
        b = list(reversed(ZZ(i).bits()))
        b = [0 for j in range(num_primes-len(b))] + b
        row = [r"<td class='center'>\(%s\)</td>" % sign_char(x) for x in b]
        sign = sum(b) % 2
        if num_primes > 1:
            row.append(r"<td class='center'>\(%s\)</td>" % sign_char(sign))
        query = {'level':level, 'weight':weight, 'char_order':1, 'atkin_lehner_string':"".join(map(url_sign_char,b))}
        link = newform_search_link(r'\(%s\)' % dim, **query)
        row.append(r'<td>%s</td>' % (link))
        fricke[sign] += dim
        if i == len(al_dims) - 1 and num_primes > 1:
            tr = "<tr class='endsection'>"
        else:
            tr = "<tr>"
        rows.append(tr + ''.join(row) + '</tr>')
    if num_primes > 1:
        plus_knowl = display_knowl('cmf.plus_space',title='Plus space').replace('"',"'")
        plus_link = newform_search_link(r'\(%s\)' % fricke[0], level=level, weight=weight, char_order=1, fricke_eigenval=1)
        minus_knowl = display_knowl('cmf.minus_space',title='Minus space').replace('"',"'")
        minus_link = newform_search_link(r'\(%s\)' % fricke[1], level=level, weight=weight, char_order=1, fricke_eigenval=-1)
        rows.append(r"<tr><td colspan='%s'>%s</td><td class='center'>\(+\)</td><td>%s</td></tr>" % (num_primes, plus_knowl, plus_link))
        rows.append(r"<tr><td colspan='%s'>%s</td><td class='center'>\(-\)</td><td>%s</td></tr>" % (num_primes, minus_knowl, minus_link))
    return ("<table class='ntdata'><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" %
            (''.join(header), ''.join(rows)))


def ALdim_table(al_dims, level, weight):
    def sign_char(x): return "-" if x else "+"
    def url_sign_char(x): return "-" if x else "%2B"
    primes = ZZ(level).prime_divisors()
    num_primes = len(primes)
    header = [r"<th rowspan=2 class='center'>\(%s\)</th>" % p for p in primes]
    if num_primes > 1:
        header.append(r"<th rowspan=2 class='center'>%s</th>" % (display_knowl('cmf.fricke', title='Fricke').replace('"',"'")))

    space_type = {'M':'Total',
                  'S':'Cusp',
                  'E':'Eisenstein'}

    subheader = []

    fricke = {}
    for X in ['M','S','E']:
        fricke[X] = {}
        header.append("<th rowspan=2></th>")
        header.append("<th class='center' colspan=3>" + space_type[X] + "</th>")
        for typ in ['all', 'new', 'old']:
            fricke[X][typ] = [0,0]
            subheader.append("<th class='center'>" + typ.capitalize() + "</th>")

    rows = []
    for i, dim in enumerate(al_dims['M']['all']):
        if dim == 0:
            continue
        b = list(reversed(ZZ(i).bits()))
        b = [0 for j in range(num_primes-len(b))] + b
        row = [r"<td class='center'>\(%s\)</td>" % sign_char(x) for x in b]
        sign = sum(b) % 2
        if num_primes > 1:
            row.append(r"<td class='center'>\(%s\)</td>" % sign_char(sign))
        query = {'level':level, 'weight':weight, 'char_order':1, 'atkin_lehner_string':"".join(map(url_sign_char,b))}
        for X in ['M','S','E']:
            row.append("<td></td>")
            for typ in ['all', 'new', 'old']:
                dim = r'\(%s\)' % al_dims[X][typ][i]
                if (X == 'S') and (typ == 'new'):
                    dim = newform_search_link(dim, **query)
                row.append(r"<td class='center'>%s</td>" % dim)
                fricke[X][typ][sign] += al_dims[X][typ][i]
        if i == len(al_dims['M']['all']) - 1 and num_primes > 1:
            tr = "<tr class='endsection'>"
        else:
            tr = "<tr>"
        rows.append(tr + ''.join(row) + '</tr>')
    if num_primes > 1:
        plus_knowl = display_knowl('cmf.plus_space',title='Plus space').replace('"',"'")
        minus_knowl = display_knowl('cmf.minus_space',title='Minus space').replace('"',"'")
        plus_row = r"<tr><td colspan='%s'>%s</td><td class='center'>\(+\)</td>" % (num_primes, plus_knowl)
        minus_row = r"<tr><td colspan='%s'>%s</td><td class='center'>\(-\)</td>" % (num_primes, minus_knowl)

        for X in ['M','S','E']:
            plus_row += "<td></td>"
            minus_row += "<td></td>"
            for typ in ['all', 'new', 'old']:
                plus_dim = r'\(%s\)' % fricke[X][typ][0]
                minus_dim = r'\(%s\)' % fricke[X][typ][1]
                if (X == 'S') and (typ == 'new'):
                    plus_dim = newform_search_link(plus_dim, level=level, weight=weight, char_order=1, fricke_eigenval=1)
                    minus_dim = newform_search_link(minus_dim, level=level, weight=weight, char_order=1, fricke_eigenval=-1)
                prefix = "<td class='center'>"
                plus_row += prefix + r"%s</td>" % (plus_dim)
                minus_row += prefix + r"%s</td>" % (minus_dim)
        plus_row += r"</tr>"
        minus_row += r"</tr>"
        rows.append(plus_row)
        rows.append(minus_row)
    return ("<table class='ntdata'><thead><tr class='middle bottomlined'>%s</tr><tr>%s</tr></thead><tbody>%s</tbody></table>" %
            (''.join(header), ''.join(subheader), ''.join(rows)))

def common_latex(level, weight, conrey=None, S="S", t=0, typ="", symbolic_chi=False):
    # symbolic_chi is currently ignored: we always use a symbolic chi
    if conrey is None:
        char = ""
    #elif symbolic_chi is True:
    #    char = r", \chi"
    #elif symbolic_chi:
    #    char = ", " + symbolic_chi
    elif conrey == 1:
        char = ""
    else:
        #char = r", [\chi_{{{level}}}({conrey}, \cdot)]".format(level=level, conrey=conrey)
        char = r", [\chi]"
    if typ:
        typ = r"^{\mathrm{%s}}" % (typ)
    if char:
        ans = r"{S}_{{{k}}}{typ}({N}{char})"
    else:
        ans = r"{S}_{{{k}}}{typ}(\Gamma_{t}({N}){char})"
    return ans.format(S=S, k=weight, typ=typ, t=t, N=level, char=char)

def convert_spacelabel_from_conrey(spacelabel_conrey):
    """
    Returns the label for a space specified using a Conrey index
    e.g. 23.2.22 -> 23.2.b (because 23.b is the character orbit label of the Conrey character 23.22)
    """
    N, k, n = map(int, spacelabel_conrey.split('.'))
    try:
        return db.mf_newspaces.lucky({'conrey_index': ConreyCharacter(N,n).min_conrey_conj, 'level': N, 'weight': k}, projection='label')
    except ValueError: # N and n not relatively prime
        pass


def trace_expansion_generic(space, prec_max=10):
    prec = min(len(space.traces)+1, prec_max)
    return raw_typeset_qexp([0] + space.traces[:prec-1])
    # return web_latex(coeff_to_power_series([0] + space.traces[:prec-1],prec=prec),enclose=True)


class DimGrid():
    def __init__(self, grid=None):
        if grid is None:
            self._grid = {'M':{'all':0,'new':0,'old':0},
                          'S':{'all':0,'new':0,'old':0},
                          'E':{'all':0,'new':0,'old':0}}
        else:
            self._grid = grid

    def __getitem__(self, X):
        return self._grid[X]

    def __add__(self, other):
        if isinstance(other,int) and other == 0: # So that we can do sum(grids)
            return self
        elif isinstance(other,DimGrid):
            grid = {}
            for X in ['M','S','E']:
                grid[X] = {}
                for typ in ['all','new','old']:
                    grid[X][typ] = self._grid[X][typ] + other._grid[X][typ]
            return DimGrid(grid)
        else:
            raise TypeError

    def __mul__(self, other):
        if isinstance(other, int):
            grid = {}
            for X in ['M','S','E']:
                grid[X] = {}
                for typ in ['all','new','old']:
                    grid[X][typ] = other * self._grid[X][typ]
            return DimGrid(grid)
        else:
            raise TypeError

    def __radd__(self, other):
        return self.__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    @staticmethod
    def from_db(data):
        grid = {'M':{'all':data['mf_dim'],
                     'new':data['dim']+data['eis_new_dim'],
                     'old':data['mf_dim']-data['dim']-data['eis_new_dim']},
                'S':{'all':data['cusp_dim'],
                     'new':data['dim'],
                     'old':data['cusp_dim']-data['dim']},
                'E':{'all':data['eis_dim'],
                     'new':data['eis_new_dim'],
                     'old':data['eis_dim']-data['eis_new_dim']}}
        return DimGrid(grid)


def new_lambda(r,s,p):
    # Formula worked out by Kevin Buzzard in http://wwwf.imperial.ac.uk/~buzzard/maths/research/notes/dimension_of_spaces_of_eisenstein_series.pdf, with one obvious typo corrected (2*s==r, p>2 case)
    assert r > 0 and s <= r
    if 2*s > r:
        if r == s:
            return 2
        if r-s == 1:
            return 2*p-4
        return 2*(p-1)**2 * p**(r-s-2)
    if 2*s == r:
        if p == 2:
            return 0
        if s == 1:
            return p-3
        return (p-2)*(p-1)*p**(s-2)
    if (r % 2) != 0:
        return 0
    return p-2 if r == 2 else (p-1)**2 * p**(r/2 - 2)


def QDimensionNewEisensteinForms(chi, k):
    # The Q-dimension of the new subspace of E_k(N,chi), the space of Eisenstein series of weight k, level N, and character chi, where N is the modulus of chi.
    from sage.all import prod
    assert k > 0, "The weight k must be a positive integer"
    if ((k % 2) == 1) == chi['is_even']:
        return 0
    N = ZZ(chi['modulus'])
    M = ZZ(chi['conductor'])
    if N == 1:
        return 1 if k > 2 else 0
    D = prod([new_lambda(N.valuation(p), M.valuation(p), p) for p in N.prime_divisors()])
    if (k == 2) and (chi['order'] == 1) and N.is_prime():
        D += 1
    # As noted by Buzzard, to handle the weight 1 case, one simply divides by 2
    if k == 1:
        assert (D % 2) == 0
        D /= 2
    return D*chi['degree']


def make_newspace_data(level, char_data, k=2):
    # Makes the data needed for creating newspace pages in cases without a corresponding entry in mf_newspaces
    data = {}
    data['has_mf_newspaces_entry'] = False
    data['Nk2'] = level * k**2
    data['char_conductor'] = char_data['conductor']
    data['char_degree'] = char_data['degree']
    data['char_is_real'] = char_data['is_real']
    data['char_orbit_index'] = char_data['orbit']
    data['char_orbit_label'] = char_data['label'].split('.')[-1]
    data['char_order'] = char_data['order']
    data['char_parity'] = 1 if char_data['is_even'] else -1
    data['conrey_index'] = char_data['first']
    data['cusp_dim'] = int(gp('mfdim([%i, %i, znchar(Mod(%i,%i))], 1)' % (level, k, data['conrey_index'], level))) * char_data['degree'] # https://pari.math.u-bordeaux.fr/pub/pari/manuals/2.15.4/users.pdf  p.595
    data['dim'] = int(gp('mfdim([%i, %i, znchar(Mod(%i,%i))], 0)' % (level, k, data['conrey_index'], level))) * char_data['degree'] # mfdim returns the dimension over Q(chi), not over Q
    data['eis_dim'] = int(gp('mfdim([%i, %i, znchar(Mod(%i,%i))], 3)' % (level, k, data['conrey_index'], level))) * char_data['degree']
    data['eis_new_dim'] = QDimensionNewEisensteinForms(char_data, k)
    data['label'] = str(level) + '.' + str(k) + '.' + data['char_orbit_label']
    data['level'] = level
    data['level_is_prime'] = ZZ(level).is_prime()
    data['level_is_prime_power'] = ZZ(level).is_prime_power()
    data['level_is_square'] = ZZ(level).is_square()
    data['level_is_squarefree'] = ZZ(level).is_squarefree()
    data['level_primes'] = ZZ(level).prime_divisors()
    data['level_radical'] = prod(data['level_primes'])
    data['mf_dim'] = data['cusp_dim'] + data['eis_dim']
    data['mf_new_dim'] = data['dim'] + data['eis_new_dim']
    data['prim_orbit_index'] = char_data['primitive_orbit']
    data['relative_dim'] = data['dim']/data['char_degree']
    data['sturm_bound'] = sturm_bound(level, k)
    data['weight'] = k
    data['weight_parity'] = (-1)**k
    return data

def make_oldspace_data(newspace_label, char_conductor, prim_orbit_index):
    # This creates enough of data to generate the oldspace decomposition on a newspace page
    level = int(newspace_label.split('.')[0])
    weight = int(newspace_label.split('.')[1])
    sub_level_list = [sub_level for sub_level in divisors(level) if (sub_level % char_conductor == 0) and sub_level != level]
    sub_chars = {char['modulus'] : char for char in db.char_dirichlet.search({'modulus':{'$in':sub_level_list}, 'conductor':char_conductor, 'primitive_orbit':prim_orbit_index})}
    if weight == 1:
        newspace_dims = {rec['level']: rec['dim'] for rec in db.mf_newspaces.search({'weight': weight, '$or': [{'level': sub_level, 'char_orbit_index': sub_chars[sub_level]['orbit']} for sub_level in sub_level_list]}, ['level', 'dim'])}
    oldspaces = []
    for sub_level in sub_level_list:
        entry = {}
        entry['sub_level'] = sub_level
        entry['sub_char_orbit_index'] = sub_chars[sub_level]['orbit']
        entry['sub_conrey_index'] = sub_chars[sub_level]['first']
        entry['sub_mult'] = number_of_divisors(level/sub_level)
        # only include subspaces with positive dimension (computed on the fly unless with weight is 1)
        if weight == 1:
            if newspace_dims[sub_level] > 0:
                oldspaces.append(entry)
        else:
            if int(gp('mfdim([%i, %i, znchar(Mod(%i,%i))], 0)' % (sub_level, weight, entry['sub_conrey_index'], sub_level))) > 0:
                oldspaces.append(entry)
    return oldspaces

class WebNewformSpace():
    def __init__(self, data):
        self.__dict__.update(data)
        self.factored_level = web_latex_factored_integer(self.level, equals=True)
        self.has_projective_image_types = all(typ+'_dim' in data for typ in ('dihedral','a4','s4','a5'))
        # The following can be removed once we change the behavior of lucky to include Nones
        self.num_forms = data.get('num_forms')
        self.trace_bound = data.get('trace_bound')
        self.has_trace_form = (data.get('traces') is not None)
        self.char_conrey = self.conrey_index
        self.char_conrey_str = r'\chi_{%s}(%s,\cdot)' % (self.level, self.char_conrey)
        self.newforms = list(db.mf_newforms.search({'space_label':self.label}, projection=2))
        oldspaces = make_oldspace_data(self.label, self.char_conductor, self.prim_orbit_index)
        self.oldspaces = [(old['sub_level'], old['sub_char_orbit_index'], old['sub_conrey_index'], old['sub_mult']) for old in oldspaces]
        self.dim_grid = DimGrid.from_db(data)
        self.plot = db.mf_newspace_portraits.lookup(self.label, projection="portrait")
        # Properties
        self.properties = [('Label',self.label)]
        if self.plot is not None and self.dim > 0:
            self.properties += [(None, '<img src="{0}" width="200" height="200"/>'.format(self.plot))]
        self.properties += [
            ('Level', prop_int_pretty(self.level)),
            ('Weight', prop_int_pretty(self.weight)),
            ('Character orbit', '%s.%s' % (self.level, self.char_orbit_label)),
            ('Rep. character', '$%s$' % self.char_conrey_str),
            ('Character field',r'$\Q%s$' % ('' if self.char_degree == 1 else r'(\zeta_{%s})' % self.char_order)),
            ('Dimension', prop_int_pretty(self.dim)),
        ]
        if self.num_forms is not None:
            self.properties.append(('Newform subspaces', prop_int_pretty(self.num_forms)))
        self.properties.append(('Sturm bound', prop_int_pretty(self.sturm_bound)))
        if data.get('trace_bound') is not None:
            self.properties.append(('Trace bound', prop_int_pretty(self.trace_bound)))
        # Work around search results not including None
        if data.get('num_forms') is None:
            self.num_forms = None

        # Breadcrumbs
        self.bread = get_bread(level=self.level, weight=self.weight, char_orbit_label=self.char_orbit_label)

        # Downloads
        self.downloads = [
            ('Trace form to text', url_for('cmf.download_traces', label=self.label)),
            ('All stored data to text', url_for('.download_newspace', label=self.label)),
            ('Underlying data', url_for('.mf_data', label=self.label)) if self.__dict__.get('has_mf_newspaces_entry', True) else ('No underlying data', None),
        ]

        if self.conrey_index == 1:
            self.trivial_character = True
            character_str = "trivial character"
            if self.dim == 0:
                self.dim_str = r"\(%s\)" % (self.dim)
            else:
                self.minus_dim = self.dim - self.plus_dim
                self.dim_str = r"\(%s + %s\)" % (self.plus_dim, self.minus_dim)
        else:
            self.trivial_character = False
            character_str = r"Character {level}.{orbit_label}".format(level=self.level, orbit_label=self.char_orbit_label)
            self.dim_str = r"\(%s\)" % (self.dim)
        self.title = r"Space of modular forms of level %s, weight %s, and %s" % (self.level, self.weight, character_str)
        gamma1_link = '/ModularForm/GL2/Q/holomorphic/%d/%d' % (self.level, self.weight)
        self.friends = [('Newspace %d.%d' % (self.level, self.weight), gamma1_link)]

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
            weight = int(label.split('.')[1])
            if (weight != 2) or (label.split('.')[-1] == 'a'):
                raise ValueError("Space %s not found" % label)
            level = int(label.split('.')[0])
            char_label = str(level) + '.' + label.split('.')[-1]
            char_data = db.char_dirichlet.lookup(char_label)
            if not char_data:
                raise ValueError("Space %s not found" % label)
            data = make_newspace_data(level, char_data)
        return WebNewformSpace(data)

    @property
    def char_orbit_link(self):
        label = '%s.%s' % (self.level, self.char_orbit_label)
        return display_knowl('character.dirichlet.orbit_data', title=label, kwargs={'label':label})

    def display_character(self):
        if self.char_order == 1:
            ord_deg = " (trivial)"
        else:
            ord_knowl = display_knowl('character.dirichlet.order', title='order')
            deg_knowl = display_knowl('character.dirichlet.degree', title='degree')
            ord_deg = r" (of %s \(%d\) and %s \(%d\))" % (ord_knowl, self.char_order, deg_knowl, self.char_degree)
        return self.char_orbit_link + ord_deg

    def _vec(self):
        return [self.level, self.weight, self.conrey_index]

    def mf_latex(self):
        return common_latex(*(self._vec() + ["M"]))

    def eis_latex(self):
        return common_latex(*(self._vec() + ["E"]))

    def eis_new_latex(self):
        return common_latex(*(self._vec() + ["E",0,"new"]))

    def eis_old_latex(self):
        return common_latex(*(self._vec() + ["E",0,"old"]))

    def cusp_latex(self):
        return common_latex(*(self._vec() + ["S"]))

    def cusp_latex_symbolic(self):
        return common_latex(*(self._vec() + ["S"]), symbolic_chi=True)

    def new_latex(self):
        return common_latex(*(self._vec() + ["S",0,"new"]))

    def old_latex(self):
        return common_latex(*(self._vec() + ["S",0,"old"]))

    def old_latex_symbolic(self):
        return common_latex(*(self._vec() + ["S",0,"old"]), symbolic_chi=True)

    def subspace_latex(self, new=False):
        return common_latex("M", self.weight, self.conrey_index, "S", 0, "new" if new else "", symbolic_chi=True)

    def oldspace_decomposition(self):
        # Returns a latex string giving the decomposition of the old part.  These come from levels M dividing N, with the conductor of the character dividing M.
        template = r"<a href={url}>\({old}\)</a>\(^{{\oplus {mult}}}\)"
        return r"\(\oplus\)".join(template.format(old=common_latex(N, self.weight, conrey, typ="new"),
                                                  url=url_for(".by_url_space_label",level=N,weight=self.weight,char_orbit_label=cremona_letter_code(i-1)),
                                                  mult=mult)
                                  for N, i, conrey, mult in self.oldspaces)

    def ALdim_table(self):
        if not hasattr(self,'ALdims_old'):
            return ALdim_new_cusp_table(self.ALdims, self.level, self.weight)
        aldims_data = {'dim' : vector(self.ALdims), 'cusp_dim' : vector(self.ALdims) + vector(self.ALdims_old),
                       'eis_new_dim' : vector(self.ALdims_eis_new), 'eis_dim' : vector(self.ALdims_eis_new) + vector(self.ALdims_eis_old)}
        aldims_data['mf_dim'] = aldims_data['cusp_dim'] + aldims_data['eis_dim']
        aldims = DimGrid.from_db(aldims_data)
        return ALdim_table(aldims, self.level, self.weight)

    def trace_expansion(self, prec_max=10):
        return trace_expansion_generic(self, prec_max)

    def hecke_cutter_display(self):
        return ", ".join(r"\(%d\)" % p for p in self.hecke_cutter_primes)

    def display_character_field(self):
        return cyc_display(self.char_order, self.char_degree, False)

class WebGamma1Space():
    def __init__(self, level, weight):
        data = db.mf_gamma1.lucky({'level':level,'weight':weight})
        if data is None:
            raise ValueError("Space not in database")
        self.__dict__.update(data)
        self.weight_parity = -1 if (self.weight % 2) == 1 else 1
        self.factored_level = web_latex_factored_integer(self.level, equals=True)
        self.has_projective_image_types = all(typ+'_dim' in data for typ in ('dihedral','a4','s4','a5'))
        # The following can be removed once we change the behavior of lucky to include Nones
        self.num_forms = data.get('num_forms')
        self.num_spaces = data.get('num_spaces')
        self.trace_bound = data.get('trace_bound')
        self.has_trace_form = (data.get('traces') is not None)
        # By default we sort on char_orbit_index
        newspaces = list(db.mf_newspaces.search({'level':level, 'weight':weight, 'char_parity': self.weight_parity}))
        self.oldspaces = [(sublevel, number_of_divisors(level/sublevel)) for sublevel in divisors(level) if sublevel != level]
        self.oldspaces.sort()
        self.dim_grid = DimGrid.from_db(data)
        self.decomp = []
        newforms = list(db.mf_newforms.search({'level':level, 'weight':weight}, ['label', 'space_label', 'dim', 'level', 'char_orbit_label', 'hecke_orbit', 'char_degree']))
        self.has_uncomputed_char = False
        if len(newspaces) == len([dim for dim in self.newspace_dims if dim != 0]):
            for space in newspaces:
                if space.get('num_forms') is None:
                    self.decomp.append((space, None))
                    self.has_uncomputed_char = True
                else:
                    self.decomp.append((space, [form for form in newforms if form['space_label'] == space['label']]))
        else:
            char_orbits = list(db.char_dirichlet.search({'modulus':level}))
            newspaces_by_label = {str(level) + '.' + ns['char_orbit_label'] : ns for ns in newspaces} # to match the full character orbit label
            newspace_dims_by_label = {char_orbits[i]['label'] : self.newspace_dims[i] for i in range(len(char_orbits))} # This relies on the fact that newspaces are sorted by char_orbit_index, which is the default at the time of writing.
            for char in char_orbits:
                if char['label'] in newspaces_by_label:
                    space = newspaces_by_label[char['label']]
                    if space.get('num_forms') is None:
                        self.decomp.append((space, None))
                        self.has_uncomputed_char = True
                    else:
                        self.decomp.append((space, [form for form in newforms if form['space_label'] == space['label']]))
                elif newspace_dims_by_label[char['label']] != 0:
                    space = {}
                    space['level'] = level
                    space['conrey_index'] = char['first']
                    space['char_orbit_label'] = char['label'].split('.')[-1]
                    space['label'] = "%s.%s.%s" % (level,weight,space['char_orbit_label'])
                    space['char_degree'] = char['degree']
                    space['dim'] = newspace_dims_by_label[char['label']]
                    space['generate_link'] = (self.weight == 2) and (space['char_orbit_label'] != 'a')
                    # generate_link is used in self.decomposition() as a marker of pages which can be generated dynamically.
                    # len(newspaces) == len([dim for dim in self.newspace_dims if dim != 0]) when there is an associated database entry, so the line above doesn't come up in those cases.
                    self.decomp.append((space, None))
                    self.has_uncomputed_char = True
        self.plot = db.mf_gamma1_portraits.lookup(self.label, projection="portrait")
        self.properties = [('Label',self.label),]
        if self.plot is not None and self.dim > 0:
            self.properties += [(None, '<a href="{0}"><img src="{0}" width="200" height="200"/></a>'.format(self.plot))]
        self.properties += [
            ('Level',str(self.level)),
            ('Weight',str(self.weight)),
            ('Dimension',str(self.dim))
        ]
        if self.num_spaces is not None:
            self.properties.append(('Nonzero newspaces',str(self.num_spaces)))
        if self.num_forms is not None:
            self.properties.append(('Newform subspaces',str(self.num_forms)))
        self.properties.append(('Sturm bound',str(self.sturm_bound)))
        if self.trace_bound is not None:
            self.properties.append(('Trace bound',str(self.trace_bound)))
        self.bread = get_bread(level=self.level, weight=self.weight)
        # Downloads
        self.downloads = [
            ('Trace form to text', url_for('cmf.download_traces', label=self.label)),
            ('All stored data to text', url_for('cmf.download_full_space', label=self.label)),
            ('Underlying data', url_for('.mf_data', label=self.label)),
        ]
        self.title = r"Space of modular forms of level %s and weight %s" % (self.level, self.weight)
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

    def eis_old_latex(self):
        return common_latex(*(self._vec() + ["E",1,"old"]))

    def cusp_latex(self):
        return common_latex(*(self._vec() + ["S",1]))

    def new_latex(self):
        return common_latex(*(self._vec() + ["S",1,"new"]))

    def subspace_latex(self, new=False):
        return common_latex("M", self.weight, None, "S", 1, "new" if new else "")

    def summand_latex(self,symbolic_chi=True):
        return common_latex(self.level, self.weight, 1, "S", 0, "new", symbolic_chi=symbolic_chi)

    def old_latex(self):
        return common_latex(*(self._vec() + ["S",1,"old"]))

    def header_latex(self):
        return r'\(' + common_latex(*(self._vec() + ["S",0,"new",True])) + r'\)'

    def _link(self, N, i=None, form=None, typ="new", label=True):
        if form is not None:
            form = cremona_letter_code(form - 1)
        if label:
            if i is None:
                name = "{N}.{k}".format(N=N, k=self.weight)
            elif form is None:
                name = "{N}.{k}.{i}".format(N=N, k=self.weight, i=i)
            else:
                name = "{N}.{k}.{i}.{f}".format(N=N, k=self.weight, i=i, f=form)
        else:
            t = 1 if i is None else 0
            name = r"\(%s\)" % common_latex(N, self.weight, i, t=t, typ=typ)
        if i is None:
            url = url_for(".by_url_full_gammma1_space_label",
                          level=N, weight=self.weight)
        elif form is None:
            url = url_for(".by_url_space_label",
                          level=N, weight=self.weight, char_orbit_label=i)
        else:
            url = url_for(".by_url_newform_label",
                          level=N, weight=self.weight, char_orbit_label=i, hecke_orbit=form)
        return r"<a href={url}>{name}</a>".format(url=url, name=name)

    def oldspace_decomposition(self):
        template = r"{link}\(^{{\oplus {mult}}}\)"
        return r"\(\oplus\)".join(template.format(link=self._link(N, label=False),
                                                  mult=mult)
                                  for N, mult in self.oldspaces)

    def decomposition(self):
        # returns a list of 6-tuples chi_rep, num_chi, space, firstform, firstdim, forms
        ans = []
        for i, (space, forms) in enumerate(self.decomp):
            rowtype = "oddrow" if i % 2 else "evenrow"
            chi_str = r"\chi_{%s}(%s, \cdot)" % (space['level'], space['conrey_index'])
            chi_rep = '<a href="' + url_for('characters.render_Dirichletwebpage',
                                             modulus=space['level'],
                                             orbit_label=space['char_orbit_label'])
            chi_rep += r'">\({}\)</a>'.format(chi_str)

            num_chi = space['char_degree']
            if space.get('generate_link', True):
                link = self._link(space['level'], space['char_orbit_label'])
            else:
                link = "{N}.{k}.{i}".format(N=space['level'], k=self.weight, i=space['char_orbit_label']) # Not actually a link
            if forms is None:
                ans.append((rowtype, chi_rep, num_chi, link, "n/a", space['dim'], []))
            elif not forms:
                ans.append((rowtype, chi_rep, num_chi, link, "None", space['dim'], []))
            else:
                dims = [form['dim'] for form in forms]
                forms = [self._link(form['level'], form['char_orbit_label'], form['hecke_orbit']) for form in forms]
                ans.append((rowtype, chi_rep, num_chi, link, forms[0], dims[0], list(zip(forms[1:], dims[1:]))))
        return ans

    def trace_expansion(self, prec_max=10):
        return trace_expansion_generic(self, prec_max)

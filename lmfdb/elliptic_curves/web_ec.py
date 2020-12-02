# -*- coding: utf-8 -*-
import re
import os
import yaml
from flask import url_for
from lmfdb import db
from lmfdb.number_fields.web_number_field import formatfield
from lmfdb.utils import web_latex, encode_plot, prop_int_pretty
from lmfdb.logger import make_logger
from lmfdb.sato_tate_groups.main import st_link_by_name

from sage.all import EllipticCurve, KodairaSymbol, latex, ZZ, QQ, prod, Factorization, PowerSeriesRing, prime_range

ROUSE_URL_PREFIX = "http://users.wfu.edu/rouseja/2adic/" # Needs to be changed whenever J. Rouse and D. Zureick-Brown move their data

OPTIMALITY_BOUND = 400000 # optimality of curve no. 1 in class (except class 990h) only proved in all cases for conductor less than this

cremona_label_regex = re.compile(r'(\d+)([a-z]+)(\d*)')
lmfdb_label_regex = re.compile(r'(\d+)\.([a-z]+)(\d*)')
lmfdb_iso_label_regex = re.compile(r'([a-z]+)(\d*)')
sw_label_regex = re.compile(r'sw(\d+)(\.)(\d+)(\.*)(\d*)')
weierstrass_eqn_regex = re.compile(r'\[(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)\]')
short_weierstrass_eqn_regex = re.compile(r'\[(-?\d+),(-?\d+)\]')

def match_lmfdb_label(lab):
    return lmfdb_label_regex.match(lab)

def match_lmfdb_iso_label(lab):
    return lmfdb_iso_label_regex.match(lab)

def match_cremona_label(lab):
    return cremona_label_regex.match(lab)

def split_lmfdb_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def split_lmfdb_iso_label(lab):
    return lmfdb_iso_label_regex.match(lab).groups()

def split_cremona_label(lab):
    return cremona_label_regex.match(lab).groups()

def curve_lmfdb_label(conductor, iso_class, number):
    return "%s.%s%s" % (conductor, iso_class, number)

def curve_cremona_label(conductor, iso_class, number):
    return "%s%s%s" % (conductor, iso_class, number)

def class_lmfdb_label(conductor, iso_class):
    return "%s.%s" % (conductor, iso_class)

def class_cremona_label(conductor, iso_class):
    return "%s%s" % (conductor, iso_class)

logger = make_logger("ec")

def split_galois_image_code(s):
    """Each code starts with a prime (1-3 digits but we allow for more)
    followed by an image code or that prime.  This function returns
    two substrings, the prefix number and the rest.
    """
    p = re.findall(r'\d+', s)[0]
    return p, s[len(p):]

def trim_galois_image_code(s):
    """Return the image code with the prime prefix removed.
    """
    return split_galois_image_code(s)[1]

def weighted_proj_to_affine_point(P):
    r""" Converts a triple of integers representing a point in weighted
    projective coordinates [a,b,c] to a tuple of rationals (a/c^2,b/c^3).
    """
    a, b, c = [ZZ(x) for x in P]
    return (a/c**2, b/c**3)

def EC_ainvs(E):
    """ Return the a-invariants of a Sage elliptic curve in the correct format for the database.
    """
    return [int(a) for a in E.ainvs()]

def make_y_coords(ainvs,x):
    a1, a2, a3, a4, a6 = ainvs
    f = ((x + a2) * x + a4) * x + a6
    b = (a1*x + a3)
    d = ZZ(b*b + 4*f).isqrt()
    y = (-b+d)//2
    return [y, -b-y] if d else [y]

def pm_pt(P):
    return r"\(({},\pm {})\)".format(P[0],P[1]) if P[1] else web_latex(P)

def count_integral_points(c):
    ainvs = c['ainvs']
    xcoords = c['xcoord_integral_points']
    return sum([len(make_y_coords(ainvs,x)) for x in xcoords])

# Custom function to make a latex 'equation' string from a-invariants
#
# assume that [a1,a2,a3] are one of the 12 reduced triples with a1,a3
# in [0,1] and a2 in [-1,0,1].

# This is the same as latex(EllipticCurve(ainvs)).replace("
# ","").replace("{3}","3").replace("{2}","2"), i.e. the only
# difference is that we have x^3 instead of x^{3} (and x^2 instead of
# x^{2} when a2!=0), and have no spaces.  I checked this on all curves
# of conductor <10000!

def latex_equation(ainvs):
    a1,a2,a3,a4,a6 = [int(a) for a in ainvs]
    return ''.join([r'\(y^2',
                    '+xy' if a1 else '',
                    '+y' if a3 else '',
                    '=x^3',
                    '+x^2' if a2==1 else '-x^2' if a2==-1 else '',
                    '{:+}x'.format(a4) if abs(a4)>1 else '+x' if a4==1 else '-x' if a4==-1 else '',
                    '{:+}'.format(a6) if a6 else '',
                    r'\)'])


class WebEC(object):
    """
    Class for an elliptic curve over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        logger.debug("Constructing an instance of WebEC")
        self.__dict__.update(dbdata)
        self.make_curve()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific elliptic curve in the curves
        collection by its label, which can be either in LMFDB or
        Cremona format.
        """
        try:
            N, iso, number = split_lmfdb_label(label)
            data = db.ec_curvedata.lucky({"lmfdb_label" : label})
            if not data:
                return "Curve not found" # caller must catch this and raise an error
            data['label_type'] = 'LMFDB'
        except AttributeError:
            try:
                N, iso, number = split_cremona_label(label)
                data = db.ec_curvedata.lucky({"label" : label})
                if not data:
                    return "Curve not found" # caller must catch this and raise an error
                data['label_type'] = 'Cremona'
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error
        return WebEC(data)

    def make_curve(self):
        data = self.data = {}
        label = self.label
        
        # Some data fields of self are just those from the database.
        # These only need some reformatting.

        data['ainvs'] =  self.ainvs
        data['conductor'] = N = self.conductor
        data['j_invariant'] = QQ(tuple(self.jinv))
        data['j_inv_factor'] = latex(0)
        if data['j_invariant']: # don't factor 0
            data['j_inv_factor'] = latex(data['j_invariant'].factor())
        data['j_inv_latex'] = web_latex(data['j_invariant'])

        # retrieve local reduction data from table ec_localdata:

        self.local_data = local_data = list(db.ec_localdata.search({"label": label}))
        for ld in local_data:
            ld['kod'] = latex(KodairaSymbol(ld['kodaira_symbol']))

        Nfac = Factorization([(ZZ(ld['prime']),ld['conductor_valuation']) for ld in local_data])
        Dfac = Factorization([(ZZ(ld['prime']),ld['discriminant_valuation']) for ld in local_data], unit=ZZ(self.signD))
        data['disc_factor'] = latex(Dfac)
        data['disc'] = D = Dfac.value()
        data['cond_factor'] =latex(Nfac)
        data['disc_latex'] = web_latex(D)
        data['cond_latex'] = web_latex(N)

        # retrieve data about MW rank, generators, heights and
        # torsion, leading term of L-function & other BSD data from
        # table ec_mwbsd:
        
        self.make_mwbsd()

        # latex equation:

        data['equation'] = latex_equation(self.ainvs)

        # minimal quadratic twist:

        data['minq_D'] = minqD = self.min_quad_twist_disc
        data['minq_label'] = db.ec_curvedata.lucky({'ainvs': self.min_quad_twist_ainvs},
                                                   projection = 'lmfdb_label' if self.label_type=='LMFDB' else 'label')
        data['minq_info'] = '(itself)' if minqD==1 else '(by {})'.format(minqD)

        # modular degree:
        
        if self.degree is None:
            data['degree'] = 0 # invalid, but will be displayed nicely
        else:
            data['degree'] = self.degree

        # coefficients of modular form / L-series:

        classdata = db.ec_classdata.lookup(self.iso)
        data['an'] = classdata['anlist']
        data['ap'] = classdata['aplist']
        
        # mod-p Galois images:
        
        data['galois_data'] = list(db.ec_galrep.search({'label': self.label}))
        for gd in data['galois_data']: # remove the prime prefix from each image code
            gd['image'] = trim_galois_image_code(gd['image'])
        
        # CM and Endo ring:
        
        data['CMD'] = self.cm
        data['CM'] = "no"
        data['EndE'] = r"\(\Z\)"
        if self.cm:
            data['cm_ramp'] = [p for p in ZZ(self.cm).support() if not p in self.nonmax_primes]
            data['cm_nramp'] = len(data['cm_ramp'])
            if data['cm_nramp']==1:
                data['cm_ramp'] = data['cm_ramp'][0]
            else:
                data['cm_ramp'] = ", ".join([str(p) for p in data['cm_ramp']])
            data['cm_sqf'] = ZZ(self.cm).squarefree_part()

            data['CM'] = r"yes (\(D=%s\))" % data['CMD']
            if data['CMD']%4==0:
                d4 = ZZ(data['CMD'])//4
                data['EndE'] = r"\(\Z[\sqrt{%s}]\)" % d4
            else:
                data['EndE'] = r"\(\Z[(1+\sqrt{%s})/2]\)" % data['CMD']
            data['ST'] = st_link_by_name(1,2,'N(U(1))')
        else:
            data['ST'] = st_link_by_name(1,2,'SU(2)')

        # Isogeny degrees:
        
        cond, iso, num = split_lmfdb_label(self.lmfdb_label)
        self.class_deg  = classdata['class_deg']
        self.one_deg = ZZ(self.class_deg).is_prime()
        isodegs = [str(d) for d in self.isogeny_degrees if d>1]
        if len(isodegs)<3:
            data['isogeny_degrees'] = " and ".join(isodegs)
        else:
            data['isogeny_degrees'] = " and ".join([", ".join(isodegs[:-1]),isodegs[-1]])


        self.make_twoadic_data()

        # Optimality

        # The optimal curve in the class is the curve whose Cremona
        # label ends in '1' except for '990h' which was labelled
        # wrongly long ago. This is proved for N up to
        # OPTIMALITY_BOUND (and when there is only one curve in an
        # isogeny class, obviously) and expected for all N.

        # Column 'optimality' is 1 for certainly optimal curves, 0 for
        # certainly non-optimal curves, and is n>1 if the curve is one
        # of n in the isogeny class which may be optimal given current
        # knowledge.

        # Column "manin_constant' is the correct Manin constant
        # assuming that the optimal curve in the class is known, or
        # otherwise if it is the curve with (Cremona) number 1.

        # The code here allows us to update the display correctly by
        # changing one line in this file (defining OPTIMALITY_BOUND)
        # without changing the data.

        data['optimality_bound'] = OPTIMALITY_BOUND
        data['manin_constant'] = self.manin_constant # (conditional on data['optimality_known'])

        if N<OPTIMALITY_BOUND:

            data['optimality_code'] = int(self.number == (3 if self.iso=='990h' else 1))
            data['optimality_known'] = True
            data['manin_known'] = True
            if self.label_type=='Cremona':
                data['optimal_label'] = '990h3' if self.iso=='990h' else self.iso+'1'
            else:
                data['optimal_label'] = '990.i3' if self.lmfdb_iso=='990.i' else self.lmfdb_iso+'1'

        else:

            data['optimality_code'] = self.optimality
            data['optimality_known'] = (self.optimality < 2)

            if self.optimality==1:
                data['manin_known'] = True
                data['optimal_label'] = self.label if self.label_type == 'Cremona' else self.lmfdb_label
            else:
                if self.number==1:
                    data['manin_known'] = False
                    data['optimal_label'] = self.label if self.label_type == 'Cremona' else self.lmfdb_label
                else:
                    # find curve #1 in this class and its optimailty code:
                    opt_curve = db.ec_curvedata.lucky({'iso': self.iso, 'number': 1},
                                                   projection=['label','lmfdb_label','optimality'])
                    data['manin_known'] = (opt_curve['optimality']==1)
                    data['optimal_label'] = opt_curve['label' if self.label_type == 'Cremona' else 'lmfdb_label']

        # p-adic data:
            
        data['p_adic_primes'] = [p for i,p in enumerate(prime_range(5, 100))
                                 if (N*data['ap'][i]) %p !=0]

        data['p_adic_data_exists'] = False
        if data['optimality_code']==1:
            data['p_adic_data_exists'] = db.ec_padic.exists({'lmfdb_iso': self.lmfdb_iso})

        # Iwasawa data (where present)

        self.make_iwasawa()

        # Torsion growth data (where present)

        self.make_torsion_growth()

        # Newform
        
        data['newform'] =  web_latex(PowerSeriesRing(QQ, 'q')(data['an'], 20, check=True))
        data['newform_label'] = self.newform_label = ".".join( [str(cond), str(2), 'a', iso] )
        self.newform_link = url_for("cmf.by_url_newform_label", level=cond, weight=2, char_orbit_label='a', hecke_orbit=iso)
        self.newform_exists_in_db = db.mf_newforms.label_exists(self.newform_label)
        self._code = None

        if self.label_type == 'Cremona':
            self.class_url = url_for(".by_ec_label", label=self.iso)
            self.class_name = self.iso
        else:
            self.class_url = url_for(".by_double_iso_label", conductor=N, iso_label=iso)
            self.class_name = self.lmfdb_iso
        data['class_name'] = self.class_name
        data['number'] = self.number
        
        self.friends = [
            ('Isogeny class ' + self.class_name, self.class_url),
            ('Minimal quadratic twist %s %s' % (data['minq_info'], data['minq_label']), url_for(".by_ec_label", label=data['minq_label'])),
            ('All twists ', url_for(".rational_elliptic_curves", jinv=self.jinv))]

        lfun_url = url_for("l_functions.l_function_ec_page", conductor_label = N, isogeny_class_label = iso)
        origin_url = lfun_url.lstrip('/L/').rstrip('/')

        if db.lfunc_instances.exists({'url':origin_url}):
            self.friends += [('L-function', lfun_url)]
        else:
            self.friends += [('L-function not available', "")]

        if not self.cm:
            if N<=300:
                self.friends += [('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', conductor = N, isogeny = iso))]
            if N<=50:
                self.friends += [('Symmetric cube L-function', url_for("l_functions.l_function_ec_sym_page", power='3', conductor = N, isogeny = iso))]
        if self.newform_exists_in_db:
            self.friends += [('Modular form ' + self.newform_label, self.newform_link)]

        self.downloads = [('q-expansion to text', url_for(".download_EC_qexp", label=self.lmfdb_label, limit=1000)),
                          ('All stored data to text', url_for(".download_EC_all", label=self.lmfdb_label)),
                          ('Code to Magma', url_for(".ec_code_download", conductor=cond, iso=iso, number=num, label=self.lmfdb_label, download_type='magma')),
                          ('Code to SageMath', url_for(".ec_code_download", conductor=cond, iso=iso, number=num, label=self.lmfdb_label, download_type='sage')),
                          ('Code to GP', url_for(".ec_code_download", conductor=cond, iso=iso, number=num, label=self.lmfdb_label, download_type='gp'))
        ]

        try:
            self.plot = encode_plot(self.E.plot())
        except AttributeError:
            self.plot = encode_plot(EllipticCurve(data['ainvs']).plot())


        self.plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)
        self.properties = [('Label', self.label if self.label_type == 'Cremona' else self.lmfdb_label),
                           (None, self.plot_link),
                           ('Conductor', prop_int_pretty(data['conductor'])),
                           ('Discriminant', prop_int_pretty(data['disc'])),
                           ('j-invariant', '%s' % data['j_inv_latex']),
                           ('CM', '%s' % data['CM']),
                           ('Rank', prop_int_pretty(self.mwbsd['rank'])),
                           ('Torsion structure', (r'\(%s\)' % self.mwbsd['tor_struct']) if self.mwbsd['tor_struct'] else 'trivial'),
                           ]

        if self.label_type == 'Cremona':
            self.title = "Elliptic curve with Cremona label {} (LMFDB label {})".format(self.label, self.lmfdb_label)
        else:
            self.title = "Elliptic curve with LMFDB label {} (Cremona label {})".format(self.lmfdb_label, self.label)

        self.bread = [('Elliptic curves', url_for("ecnf.index")),
                           (r'$\Q$', url_for(".rational_elliptic_curves")),
                           ('%s' % N, url_for(".by_conductor", conductor=N)),
                           ('%s' % iso, url_for(".by_double_iso_label", conductor=N, iso_label=iso)),
                           ('%s' % num,' ')]

    def make_mwbsd(self):
        mwbsd = self.mwbsd = db.ec_mwbsd.lookup(self.label)

        # Some components are in the main table:
        
        mwbsd['rank'] = r = self.rank
        mwbsd['torsion'] = self.torsion
        mwbsd['reg'] = self.regulator
        mwbsd['sha'] = self.sha

        # Integral points

        xintcoords = mwbsd['xcoord_integral_points']
        a1, _, a3, _, _ = ainvs = self.ainvs
        if a1 or a3:
            int_pts = sum([[(x, y) for y in make_y_coords(ainvs,x)] for x in xintcoords], [])
            mwbsd['int_points'] = ', '.join(web_latex(P) for P in int_pts)
        else:
            int_pts = [(x, make_y_coords(ainvs,x)[0]) for x in xintcoords]
            mwbsd['int_points'] = ', '.join(pm_pt(P) for P in int_pts)

        # Generators (mod torsion) and heights:
        mwbsd['generators'] = [web_latex(weighted_proj_to_affine_point(P)) for P in mwbsd['gens']] if mwbsd['ngens'] else ''

        # Torsion structure and generators:
        if mwbsd['torsion'] == 1:
            mwbsd['tor_struct'] = ''
            mwbsd['tor_gens'] = ''
        else:
            mwbsd['tor_struct'] = r' \times '.join([r'\Z/{%s}\Z' % n for n in self.torsion_structure])
            mwbsd['tor_gens'] = ', '.join(web_latex(weighted_proj_to_affine_point(P)) for P in mwbsd['torsion_generators'])

        # BSD invariants
        if r >= 2:
            mwbsd['lder_name'] = "L^{(%s)}(E,1)/%s!" % (r,r)
        elif r:
            mwbsd['lder_name'] = "L'(E,1)"
        else:
            mwbsd['lder_name'] = "L(E,1)"

        tamagawa_numbers = [ld['tamagawa_number'] for ld in self.local_data]
        cp_fac = [ZZ(cp).factor() for cp in tamagawa_numbers]
        cp_fac = [latex(cp) if len(cp)<2 else '('+latex(cp)+')' for cp in cp_fac]
        mwbsd['tamagawa_factors'] = r'\cdot'.join(cp_fac)
        mwbsd['tamagawa_product'] = prod(tamagawa_numbers)

    def make_twoadic_data(self):
        if not self.cm:
            self.twoadicdata = twoadicdata = db.ec_2adic.lookup(self.label)
            from sage.matrix.all import Matrix
            twoadicdata['gen_matrices'] = ','.join([latex(Matrix(2,2,M)) for M in twoadicdata['twoadic_gens']])
            twoadicdata['rouse_url'] = ''.join([ROUSE_URL_PREFIX, twoadicdata['twoadic_label'], ".html"])

    def make_iwasawa(self):
        iw = self.iw = {}
        iwasawadata = db.ec_iwasawa.lookup(self.label)
        if not 'iwp0' in iwasawadata: # For curves with no Iwasawa data
            return

        iw['p0'] = iwasawadata['iwp0'] # could be None
        iwdata = iwasawadata['iwdata']
        iw['data'] = []
        pp = [int(p) for p in iwdata]
        badp = self.bad_primes
        rtypes = [l['reduction_type'] for l in self.local_data]
        iw['missing_flag'] = False # flags that there is at least one "?" in the table
        iw['additive_shown'] = False # flags that there is at least one additive prime in table
        for p in sorted(pp):
            rtype = ""
            if p in badp:
                red = rtypes[badp.index(p)]
                # Additive primes are excluded from the table
                rtype = ["nonsplit","add", "split"][1+red]
            p = str(p)
            pdata = iwdata[p]
            if isinstance(pdata, type(u'?')):
                if not rtype:
                    rtype = "ordinary" if pdata=="o?" else "ss"
                if rtype == "add":
                    iw['data'] += [[p,rtype,"-","-"]]
                    iw['additive_shown'] = True
                else:
                    iw['data'] += [[p,rtype,"?","?"]]
                    iw['missing_flag'] = True
            else:
                if len(pdata)==2:
                    if not rtype:
                        rtype = "ordinary"
                    lambdas = str(pdata[0])
                    mus = str(pdata[1])
                else:
                    rtype = "ss"
                    lambdas = ",".join([str(pdata[0]), str(pdata[1])])
                    mus = str(pdata[2])
                    mus = ",".join([mus,mus])
                iw['data'] += [[p,rtype,lambdas,mus]]

    def make_torsion_growth(self):
        # The torsion growth table has one row per extension field
        tgdata = list(db.ec_torsion_growth.search({'label': self.label}))
        if not tgdata: # we only have torsion growth data for some range of conductors
            self.torsion_growth_data_exists = False
            return

        self.torsion_growth_data_exists = True
        self.tg = tg = {}
        tg['data'] = tgextra = []

        # find all base changes of this curve in the database, if any:
        bcs = list(db.ec_nfcurves.search({'base_change': {'$contains': [self.lmfdb_label]}}, projection='label'))
        # extract the fields from the labels of the base-change curves:
        bc_fields = [lab.split("-")[0] for lab in bcs]
        bc_pols = [db.nf_fields.lookup(lab, projection='coeffs') for lab in bc_fields]
        tg['fields_missing'] = False
        
        for tgd in tgdata:
            tg1 = {}
            tg1['bc_label'] = "Not in database"
            tg1['d'] = tgd['degree']
            F = tgd['field']
            tg1['f'] = formatfield(F)
            if "missing" in tg1['f']:
                tg['fields_missing'] = True
            T = tgd['torsion']
            tg1['t'] = r'\(' + r' \times '.join([r'\Z/{}\Z'.format(n) for n in T]) + r'\)'
            bcc = next((lab  for lab, pol in zip(bcs, bc_pols) if pol==F), None)
            if bcc:
                   from lmfdb.ecnf.main import split_full_label
                   F, NN, I, C = split_full_label(bcc)
                   tg1['bc_label'] = bcc
                   tg1['bc_url'] = url_for('ecnf.show_ecnf', nf=F, conductor_label=NN, class_label=I, number=C)
            tg1['m'] = 0 # holds multiplicity per degree
            tgextra.append(tg1)

        tgextra.sort(key = lambda x: x['d'])
        tg['n'] = len(tgextra)
        lastd = 1
        for tg1 in tgextra:
            d = tg1['d']
            if d!=lastd:
                tg1['m'] = len([x for x in tgextra if x['d']==d])
                lastd = d

        ## Hard-coded this for now.  Note that the *only* place where
        ## this number is used is in the ec-curve template where it
        ## says "The number fields ... of degree less than
        ## {{data.tg.maxd}} such that...".
        
        tg['maxd'] = 24

    def code(self):
        if self._code is None:
            self.make_code_snippets()
        return self._code

    def make_code_snippets(self):
        # read in code.yaml from current directory:

        _curdir = os.path.dirname(os.path.abspath(__file__))
        self._code =  yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)

        # Fill in placeholders for this specific curve:

        for lang in ['sage', 'pari', 'magma']:
            self._code['curve'][lang] = self._code['curve'][lang] % (self.data['ainvs'],self.label)
        return
        for k in self._code:
            if k != 'prompt':
                for lang in self._code[k]:
                    self._code[k][lang] = self._code[k][lang].split("\n")
                    # remove final empty line
                    if len(self._code[k][lang][-1])==0:
                        self._code[k][lang] = self._code[k][lang][:-1]

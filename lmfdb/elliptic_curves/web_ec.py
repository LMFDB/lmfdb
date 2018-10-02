# -*- coding: utf-8 -*-
import re
import os
import yaml
from flask import url_for
from lmfdb.db_backend import db
from lmfdb.utils import make_logger, web_latex, encode_plot, coeff_to_poly, web_latex_split_on_pm
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl, string2list

from sage.all import EllipticCurve, latex, ZZ, QQ, prod, Factorization, PowerSeriesRing, prime_range

ROUSE_URL_PREFIX = "http://users.wfu.edu/rouseja/2adic/" # Needs to be changed whenever J. Rouse and D. Zureick-Brown move their data

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

def parse_point(s):
    r""" Converts a string representing a point in affine or
    projective coordinates to a tuple of rationals.

    Sample input: '(-565,282)', '(4599/4,-4603/8)', '(555:10778:1)',
    '(1055:-32778:1)'
    """
    # strip parentheses and spaces
    s = s.replace(' ','')[1:-1]
    if ',' in s: # affine: comma-separated rationals
        return [QQ(str(c)) for c in s.split(',')]
    if ':' in s: # projective: colon-separated integers
        cc = [ZZ(str(c)) for c in s.split(':')]
        return [cc[0]/cc[2], cc[1]/cc[2]]
    return []

def parse_points(s):
    r""" Converts a list of strings representing points in affine or
    projective coordinates to a list of tuples of rationals.

    Sample input:  ['(-565,282)', '(4599/4,-4603/8)']
                   ['(555:10778:1)', '(1055:-32778:1)']
    """
    return [parse_point(P) for P in s]

def parse_ainvs(ai):
    r""" converts a-invariants as stored in the database to a list of ints.
    This will work whether the data is stored as a list of strings
    (the old way), e.g. ['0','0','0','0','1'] or as a single list
    e.g. '[0,0,0,0,1]' with or without the brackets.
    """
    if '[' in ai: # strip the brackets
        ai = ai[1:-1]
    if ',' in ai: # it's a single string so split it on commas
        ai = ai.split(',')
    return [int(a) for a in ai]

def EC_ainvs(E):
    """ Return the a-invariants of a Sage elliptic curve in the correct format for the database.
    """
    return [int(a) for a in E.ainvs()]

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
        # Next lines because the hyphens make trouble
        self.xintcoords = dbdata['xcoord_integral_points']
        self.non_maximal_primes = dbdata['nonmax_primes']
        self.mod_p_images = dbdata['modp_images']

        # Next lines because the python identifiers cannot start with 2
        self.twoadic_index = dbdata.get('2adic_index')
        self.twoadic_log_level = dbdata.get('2adic_log_level')
        self.twoadic_gens = dbdata.get('2adic_gens')
        self.twoadic_label = dbdata.get('2adic_label')
        # All other fields are handled here
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
            data = db.ec_curves.lucky({"lmfdb_label" : label})
        except AttributeError:
            try:
                N, iso, number = split_cremona_label(label)
                data = db.ec_curves.lucky({"label" : label})
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error

        if data:
            return WebEC(data)
        return "Curve not found" # caller must catch this and raise an error

    def make_curve(self):
        # To start with the data fields of self are just those from
        # the database.  We need to reformat these.

        # Old version: required constructing the actual elliptic curve
        # E, and computing some further data about it.

        # New version (May 2016): extra data fields now in the
        # database so we do not have to construct the curve or do any
        # computation with it on the fly.  As a failsafe the old way
        # is still included.

        data = self.data = {}
        data['ainvs'] = self.ainvs
        data['conductor'] = N = ZZ(self.conductor)
        data['j_invariant'] = QQ(str(self.jinv))
        data['j_inv_factor'] = latex(0)
        if data['j_invariant']: # don't factor 0
            data['j_inv_factor'] = latex(data['j_invariant'].factor())
        data['j_inv_str'] = unicode(str(data['j_invariant']))
        data['j_inv_latex'] = web_latex(data['j_invariant'])

        # extract data about MW rank, generators, heights and torsion:
        self.make_mw()

        # get more data from the database entry

        data['equation'] = self.equation
        local_data = self.local_data
        D = self.signD * prod([ld['p']**ld['ord_disc'] for ld in local_data])
        for ld in local_data:
            ld['kod'] = ld['kod'].replace("\\\\","\\")
        data['disc'] = D
        Nfac = Factorization([(ZZ(ld['p']),ld['ord_cond']) for ld in local_data])
        Dfac = Factorization([(ZZ(ld['p']),ld['ord_disc']) for ld in local_data], unit=ZZ(self.signD))

        data['minq_D'] = minqD = self.min_quad_twist['disc']
        minq_label = self.min_quad_twist['label']
        data['minq_label'] = db.ec_curves.lucky({'label':minq_label}, 'lmfdb_label')
        data['minq_info'] = '(itself)' if minqD==1 else '(by %s)' % minqD
        if self.degree is None:
            data['degree'] = 0 # invalid, but will be displayed nicely
        else:
            data['degree'] = self.degree
        if self.number == 1:
            data['an'] = self.anlist
            data['ap'] = self.aplist
        else:
            r = db.ec_curves.lucky({'lmfdb_iso':self.lmfdb_iso, 'number':1})
            data['an'] = r['anlist']
            data['ap'] = r['aplist']

        minq_N, minq_iso, minq_number = split_lmfdb_label(data['minq_label'])

        data['disc_factor'] = latex(Dfac)
        data['cond_factor'] =latex(Nfac)
        data['disc_latex'] = web_latex(D)
        data['cond_latex'] = web_latex(N)

        data['galois_images'] = [trim_galois_image_code(s) for s in self.mod_p_images]
        data['non_maximal_primes'] = self.non_maximal_primes
        data['galois_data'] = [{'p': p,'image': im }
                               for p,im in zip(data['non_maximal_primes'],
                                               data['galois_images'])]

        data['CMD'] = self.cm
        data['CM'] = "no"
        data['EndE'] = "\(\Z\)"
        if self.cm:
            data['cm_ramp'] = [p for p in ZZ(self.cm).support() if not p in self.non_maximal_primes]
            data['cm_nramp'] = len(data['cm_ramp'])
            if data['cm_nramp']==1:
                data['cm_ramp'] = data['cm_ramp'][0]
            else:
                data['cm_ramp'] = ", ".join([str(p) for p in data['cm_ramp']])
            data['cm_sqf'] = ZZ(self.cm).squarefree_part()

            data['CM'] = "yes (\(D=%s\))" % data['CMD']
            if data['CMD']%4==0:
                d4 = ZZ(data['CMD'])//4
                data['EndE'] = "\(\Z[\sqrt{%s}]\)" % d4
            else:
                data['EndE'] = "\(\Z[(1+\sqrt{%s})/2]\)" % data['CMD']
            data['ST'] = st_link_by_name(1,2,'N(U(1))')
        else:
            data['ST'] = st_link_by_name(1,2,'SU(2)')

        data['p_adic_primes'] = [p for i,p in enumerate(prime_range(5, 100))
                                 if (N*data['ap'][i]) %p !=0]

        cond, iso, num = split_lmfdb_label(self.lmfdb_label)
        self.class_url = url_for(".by_double_iso_label", conductor=N, iso_label=iso)
        self.one_deg = ZZ(self.class_deg).is_prime()
        self.ncurves = db.ec_curves.count({'lmfdb_iso':self.lmfdb_iso})
        isodegs = [str(d) for d in self.isogeny_degrees if d>1]
        if len(isodegs)<3:
            data['isogeny_degrees'] = " and ".join(isodegs)
        else:
            data['isogeny_degrees'] = " and ".join([", ".join(isodegs[:-1]),isodegs[-1]])


        if self.twoadic_gens:
            from sage.matrix.all import Matrix
            data['twoadic_gen_matrices'] = ','.join([latex(Matrix(2,2,M)) for M in self.twoadic_gens])
            data['twoadic_rouse_url'] = ROUSE_URL_PREFIX + self.twoadic_label + ".html"

        # Leading term of L-function & other BSD data
        self.make_bsd()

        # Optimality (the optimal curve in the class is the curve
        # whose Cremona label ends in '1' except for '990h' which was
        # labelled wrongly long ago)

        if self.iso == '990h':
            data['Gamma0optimal'] = bool(self.number == 3)
        else:
            data['Gamma0optimal'] = bool(self.number == 1)


        data['p_adic_data_exists'] = False
        if data['Gamma0optimal']:
            data['p_adic_data_exists'] = db.ec_padic.exists({'lmfdb_iso': self.lmfdb_iso})

        # Iwasawa data (where present)

        self.make_iwasawa()

        # Torsion growth data (where present)

        self.make_torsion_growth()

        data['newform'] =  web_latex(PowerSeriesRing(QQ, 'q')(data['an'], 20, check=True))
        data['newform_label'] = self.newform_label = ".".join( [str(cond), str(2), 'a', iso] )
        self.newform_link = url_for("cmf.by_url_newform_label", level=cond, weight=2, char_orbit_label='a', hecke_orbit=iso)
        self.newform_exists_in_db = db.mf_newforms.label_exists(self.newform_label)
        self._code = None

        self.class_url = url_for(".by_double_iso_label", conductor=N, iso_label=iso)
        self.friends = [
            ('Isogeny class ' + self.lmfdb_iso, self.class_url),
            ('Minimal quadratic twist %s %s' % (data['minq_info'], data['minq_label']), url_for(".by_triple_label", conductor=minq_N, iso_label=minq_iso, number=minq_number)),
            ('All twists ', url_for(".rational_elliptic_curves", jinv=self.jinv)),
            ('L-function', url_for("l_functions.l_function_ec_page", conductor_label = N, isogeny_class_label = iso))]

        if not self.cm:
            if N<=300:
                self.friends += [('Symmetric square L-function', url_for("l_functions.l_function_ec_sym_page", power='2', conductor = N, isogeny = iso))]
            if N<=50:
                self.friends += [('Symmetric cube L-function', url_for("l_functions.l_function_ec_sym_page", power='3', conductor = N, isogeny = iso))]
        if self.newform_exists_in_db:
            self.friends += [('Modular form ' + self.newform_label, self.newform_link)]

        self.downloads = [('Download coefficients of q-expansion', url_for(".download_EC_qexp", label=self.lmfdb_label, limit=1000)),
                          ('Download all stored data', url_for(".download_EC_all", label=self.lmfdb_label)),
                          ('Download Magma code', url_for(".ec_code_download", conductor=cond, iso=iso, number=num, label=self.lmfdb_label, download_type='magma')),
                          ('Download SageMath code', url_for(".ec_code_download", conductor=cond, iso=iso, number=num, label=self.lmfdb_label, download_type='sage')),
                          ('Download GP code', url_for(".ec_code_download", conductor=cond, iso=iso, number=num, label=self.lmfdb_label, download_type='gp'))
        ]

        try:
            self.plot = encode_plot(self.E.plot())
        except AttributeError:
            self.plot = encode_plot(EllipticCurve(data['ainvs']).plot())


        self.plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)
        self.properties = [('Label', self.lmfdb_label),
                           (None, self.plot_link),
                           ('Conductor', '\(%s\)' % data['conductor']),
                           ('Discriminant', '\(%s\)' % data['disc']),
                           ('j-invariant', '%s' % data['j_inv_latex']),
                           ('CM', '%s' % data['CM']),
                           ('Rank', '\(%s\)' % self.mw['rank']),
                           ('Torsion Structure', '\(%s\)' % self.mw['tor_struct'])
                           ]

        self.title = "Elliptic Curve %s (Cremona label %s)" % (self.lmfdb_label, self.label)

        self.bread = [('Elliptic Curves', url_for("ecnf.index")),
                           ('$\Q$', url_for(".rational_elliptic_curves")),
                           ('%s' % N, url_for(".by_conductor", conductor=N)),
                           ('%s' % iso, url_for(".by_double_iso_label", conductor=N, iso_label=iso)),
                           ('%s' % num,' ')]

    def make_mw(self):
        mw = self.mw = {}
        mw['rank'] = self.rank
        mw['int_points'] = ''
        if self.xintcoords:
            a1, a2, a3, a4, a6 = self.ainvs
            def lift_x(x):
                f = ((x + a2) * x + a4) * x + a6
                b = (a1*x + a3)
                d = (b*b + 4*f).sqrt()
                return (x, (-b+d)/2)
            mw['int_points'] = ', '.join(web_latex(lift_x(ZZ(x))) for x in self.xintcoords)

        mw['generators'] = ''
        mw['heights'] = []
        if self.gens:
            mw['generators'] = [web_latex(tuple(P)) for P in parse_points(self.gens)]
            mw['heights'] = self.heights

        mw['tor_order'] = self.torsion
        tor_struct = [int(c) for c in self.torsion_structure]
        if mw['tor_order'] == 1:
            mw['tor_struct'] = '\mathrm{Trivial}'
            mw['tor_gens'] = ''
        else:
            mw['tor_struct'] = ' \\times '.join(['\Z/{%s}\Z' % n for n in tor_struct])
            mw['tor_gens'] = ', '.join(web_latex(tuple(P)) for P in parse_points(self.torsion_generators))

    def make_bsd(self):
        bsd = self.bsd = {}
        r = self.rank
        if r >= 2:
            bsd['lder_name'] = "L^{(%s)}(E,1)/%s!" % (r,r)
        elif r:
            bsd['lder_name'] = "L'(E,1)"
        else:
            bsd['lder_name'] = "L(E,1)"

        bsd['reg'] = self.regulator
        bsd['omega'] = self.real_period
        bsd['sha'] = self.sha
        bsd['lder'] = self.special_value

        tamagawa_numbers = [ZZ(_ld['cp']) for _ld in self.local_data]
        cp_fac = [cp.factor() for cp in tamagawa_numbers]
        cp_fac = [latex(cp) if len(cp)<2 else '('+latex(cp)+')' for cp in cp_fac]
        bsd['tamagawa_factors'] = r'\cdot'.join(cp_fac)
        bsd['tamagawa_product'] = prod(tamagawa_numbers)

    def make_iwasawa(self):
        try:
            iwdata = self.iwdata
        except AttributeError: # For curves with no Iwasawa data
            self.iwdata = None
            return
        iw = self.iw = {}
        iw['p0'] = self.iwp0 # could be None
        iw['data'] = []
        pp = [int(p) for p in iwdata]
        badp = [l['p'] for l in self.local_data]
        rtypes = [l['red'] for l in self.local_data]
        iw['missing_flag'] = False # flags that there is at least one "?" in the table
        iw['additive_shown'] = False # flags that there is at least one additive prime in table
        for p in sorted(pp):
            rtype = ""
            if p in badp:
                red = rtypes[badp.index(p)]
                # Additive primes are excluded from the table
                # if red==0:
                #    continue
                #rtype = ["nsmult","add", "smult"][1+red]
                rtype = ["nonsplit","add", "split"][1+red]
            p = str(p)
            pdata = self.iwdata[p]
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
        if self.tor_gro is None:
            self.torsion_growth_data_exists = False
            return
        tor_gro = self.tor_gro
        self.torsion_growth_data_exists = True
        self.tg = tg = {}
        tg['data'] = tgextra = []
        # find all base-changes of this curve in the database, if any
        bcs = list(db.ec_nfcurves.search({'base_change': {'$contains': [self.lmfdb_label]}}, projection='label'))
        bcfs = [lab.split("-")[0] for lab in bcs]
        for F, T in tor_gro.items():
            tg1 = {}
            tg1['bc'] = "Not in database"
            if ":" in F:
                F = F.replace(":",".")
                field_data = nf_display_knowl(F, field_pretty(F))
                deg = int(F.split(".")[0])
                bcc = [x for x,y in zip(bcs, bcfs) if y==F]
                if bcc:
                    from lmfdb.ecnf.main import split_full_label
                    F, NN, I, C = split_full_label(bcc[0])
                    tg1['bc'] = bcc[0]
                    tg1['bc_url'] = url_for('ecnf.show_ecnf', nf=F, conductor_label=NN, class_label=I, number=C)
            else:
                field_data = web_latex_split_on_pm(coeff_to_poly(string2list(F)))
                deg = F.count(",")
            tg1['d'] = deg
            tg1['f'] = field_data
            tg1['t'] = '\(' + ' \\times '.join(['\Z/{}\Z'.format(n) for n in T.split(",")]) + '\)'
            tg1['m'] = 0
            tgextra.append(tg1)

        tgextra.sort(key = lambda x: x['d'])
        tg['n'] = len(tgextra)
        lastd = 1
        for tg1 in tgextra:
            d = tg1['d']
            if d!=lastd:
                tg1['m'] = len([x for x in tgextra if x['d']==d])
                lastd = d
        ## Hard code for now
        #tg['maxd'] = max(db.ec_curves.stats.get_oldstat('torsion_growth')['degrees'])
        tg['maxd'] = 7



    def code(self):
        if self._code == None:
            self.make_code_snippets()
        return self._code

    def make_code_snippets(self):
        # read in code.yaml from current directory:

        _curdir = os.path.dirname(os.path.abspath(__file__))
        self._code =  yaml.load(open(os.path.join(_curdir, "code.yaml")))

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

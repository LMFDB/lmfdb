#_ -*- coding: utf-8 -*-
# The class Lfunction is defined in Lfunction_base and represents an L-function
# We subclass it here:
# RiemannZeta, Lfunction_Dirichlet, Lfunction_EC_Q, Lfunction_CMF,
# Lfunction_HMF, Lfunction_Maass, Lfunction_SMF2_scalar_valued,
# DedekindZeta, ArtinLfunction, SymmetricPowerLfunction,
# Lfunction_genus2_Q


import math
import re

from flask import url_for
from sage.all import (
    CBF,
    CC,
    CDF,
    ComplexField,
    EllipticCurve,
    I,
    Integer,
    NumberField,
    PowerSeriesRing,
    QQ,
    RIF,
    RR,
    Rational,
    RealNumber,
    Reals,
    ZZ,
    ceil,
    factor,
    gcd,
    is_prime,
    lazy_attribute,
    log,
    next_prime,
    nth_prime,
    primes_first_n,
    prime_pi,
    prod,
    sqrt,
)
import sage.libs.lcalc.lcalc_Lfunction as lc

from lmfdb.backend.encoding import Json
from lmfdb.utils import (
    Downloader,
    display_complex,
    display_float,
    names_and_urls,
    round_CBF_to_half_int,
    round_to_half_int,
    str_to_CBF,
    web_latex,
)
from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.number_fields.web_number_field import WebNumberField
from lmfdb.maass_forms.web_maassform import WebMaassForm
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.siegel_modular_forms.sample import Sample
from lmfdb.artin_representations.math_classes import ArtinRepresentation
import lmfdb.hypergm.hodge
from .Lfunction_base import Lfunction
from lmfdb.lfunctions import logger
from .Lfunctionutilities import (
    string2number,
    compute_local_roots_SMF2_scalar_valued,)
from .LfunctionDatabase import (
    getEllipticCurveData,
    getHgmData,
    getHmfData,
    get_factors_instances,
    get_instance_by_url,
    get_instances_by_Lhash,
    get_instances_by_label,
    get_lfunction_by_Lhash,
    get_lfunction_by_label,
    get_lfunction_by_url,
    get_multiples_by_Lhash_and_trace_hash,
)


def validate_required_args(errmsg, args, *keys):
    missing_keys = [key for key in keys if key not in args]
    if len(missing_keys):
        raise KeyError(errmsg, "Missing required parameters: %s." % ','.join(missing_keys))

def validate_integer_args(errmsg, args, *keys):
    for key in keys:
        if key in args:
            if not isinstance(args[key],int) and not re.match(r'^\d+$',args[key].strip()):
                raise ValueError(errmsg, "Unable to convert parameter '%s' with value '%s' to a nonnegative integer." % (key, args[key]))


def constructor_logger(obj, args):
    ''' Executed when a object is constructed for debugging reasons
    '''
    logger.debug(str(obj.__class__) + str(args))


# Compute Dirichlet coefficients from Euler factors.
def an_from_data(euler_factors,upperbound=30):
    if type(euler_factors[0][0]) is int:
        R = ZZ
    else:
        R = euler_factors[0][0].parent()
    PP = PowerSeriesRing(R, 'x', Integer(upperbound).nbits())

    result = upperbound * [1]

    for i in range(0,len(euler_factors)):
        p = nth_prime(i+1)
        if p > upperbound:
            break
        f = (1 / (PP(euler_factors[i]))).padded_list(Integer(upperbound).nbits())
        k = 1
        while True:
            if p ** k > upperbound:
                break
            for j in range(1 + upperbound // (p ** k)):
                if j % p == 0:
                    continue
                result[j*p**k-1] *= f[k]
            k += 1

    return result

# Convert the information extracted from the database to the format
# expected by the L-functions homepage template.
# As of July 2015, some of the fields are hard coded specifically
# for L-functions of genus 2 curves.  Need to update after the
# general data format has been specified.
# TODO: Perhaps this should be a method of generic Lfunction class
def makeLfromdata(L):
    data = L.lfunc_data

    # Mandatory properties
    L.Lhash = data.get('Lhash')
    L.label = data.get('label')
    L.algebraic = data.get('algebraic')
    L.degree = data.get('degree')
    L.level = int(data.get('conductor'))
    L.level_factored = factor(L.level)
    L.analytic_conductor = data.get('analytic_conductor')
    L.rational =  data.get('rational')
    # FIXME
    #L.root_analytic_conductor = data.get('root_analytic_conductor')

    central_character = data.get('central_character')
    L.charactermodulus, L.characternumber = map(int, central_character.split("."))
    L.primitive = data.get('primitive', None)
    L.selfdual = data.get('self_dual', None)
    if data.get('root_number', None) is not None:
        # we first need to convert from unicode to a regular string
        L.sign = str_to_CBF(data['root_number'])
    else:
        # this is a numeric converted to LMFDB_RealLiteral
        L.sign = (2*CBF(str(data.get('sign_arg')))).exppii()
    assert (L.sign.abs() - 1).abs().mid() < 1e-5
    if L.selfdual:
        L.sign = RIF(L.sign.real()).unique_integer()
    else:
        L.sign = L.sign.mid()
    L.st_group = data.get('st_group', '')
    L.order_of_vanishing = data.get('order_of_vanishing')

    L.motivic_weight = data.get('motivic_weight', None)
    if L.motivic_weight is not None:
        L.motivic_weight = ZZ(L.motivic_weight)
        L.analytic_normalization = QQ(L.motivic_weight)/2
    else:
        # this is a numeric converted to RealLiteral
        L.analytic_normalization = round_to_half_int(data.get('analytic_normalization'))
        L.motivic_weight = '' # ZZ(2*L.analytic_normalization)


    L.mu_fe = []
    for i in range(0,len(data['gamma_factors'][0])):
        L.mu_fe.append(L.analytic_normalization +
                       string2number(data['gamma_factors'][0][i]))

    L.nu_fe = []
    for i in range(0,len(data['gamma_factors'][1])):
        L.nu_fe.append(L.analytic_normalization +
                       string2number(data['gamma_factors'][1][i]))
    L.compute_kappa_lambda_Q_from_mu_nu()

    # central_value and values
    L.leading_term = data.get('leading_term', None)

    if L.order_of_vanishing >= 1:
        central_value = 0
    elif L.leading_term is not None:
        #  convert to string in case it is in unicode string
        central_value =  CC(str(L.leading_term))
    else:
        # we use the plot_values
        if L.selfdual:
            central_value = CC(data['plot_values'][0])
        else:
            central_value = data['plot_values'][0]/sqrt(L.sign)
            # we should avoid displaying 10 digits as usual, as this is just a hack
            central_value = display_complex(central_value.real(), central_value.imag(),6)
    central_value = [0.5 + 0.5*L.motivic_weight, central_value]
    if 'values' not in data:
        L.values = [ central_value ]
    else:
        # only for Dirichlet L-functions
        #  convert to string in case it is in unicode string
        L.values = [ [float(x), CC(str(xval))] for x, xval in data['values']] + [ central_value ]


    # Optional properties
    L.coefficient_field = data.get('coefficient_field', None)

    if hasattr(L, 'base_field'):
        field_degree = int(L.base_field.split('.')[0])
        L.st_link = st_link_by_name(L.motivic_weight, L.degree // field_degree, L.st_group)
    else:
        #this assumes that the base field of the Galois representation is QQ
        L.st_link = st_link_by_name(L.motivic_weight, L.degree, L.st_group)


    if data.get('credit', None) is not None:
        L.credit = data.get('credit', None)


    # Dirichlet coefficients
    L.localfactors = data.get('euler_factors', None)
    L.bad_lfactors = data.get('bad_lfactors', None)

    # the first euler factors factored
    localfactors_factored = data.get('euler_factors_factorization', None)
    if localfactors_factored is not None:
        L.localfactors_factored_dict = dict(zip(primes_first_n(len(localfactors_factored)), localfactors_factored))
    else:
        L.localfactors_factored_dict = {}

    if L.coefficient_field == "CDF":
        # convert pairs of doubles to CDF
        pairtoCC = lambda x: CC(*tuple(x))
        L.localfactors = [[pairtoCC(q) for q in x] for x in L.localfactors]
        L.bad_lfactors = [[p, [pairtoCC(q) for q in elt]]
                          for p, elt in L.bad_lfactors]
    elif 'Maass' in data.get('origin', ''):
        R = ComplexField(ceil(data['precision']*log(10)/log(2)))
        stringtoR = lambda x: R(x) if x != '??' else R('NaN')
        L.localfactors = [[stringtoR(q) for q in x] for x in L.localfactors]
        L.bad_lfactors = [[p, [stringtoR(q) for q in elt]]
                          for p, elt in L.bad_lfactors]

    # add missing bad factors
    known_bad_lfactors = [p for p, _ in L.bad_lfactors]
    for p in sorted([elt[0] for elt in L.level_factored]):
        if p not in known_bad_lfactors:
            L.bad_lfactors.append([p, [1, None]])

    # Note: a better name would be L.dirichlet_coefficients_analytic, but that
    # would require more global changes.
    if data.get('dirichlet_coefficients', None) is not None:
        L.dirichlet_coefficients_arithmetic = data['dirichlet_coefficients']
    elif data.get('euler_factors', None) is not None:
        # ask for more, in case many are zero
        L.dirichlet_coefficients_arithmetic = an_from_data(L.localfactors, 2*L.degree*L.numcoeff)

        # get rid of extra coeff
        count = 0
        for i, elt in enumerate(L.dirichlet_coefficients_arithmetic):
            if elt != 0:
                count += 1
                if count > L.numcoeff:
                    L.dirichlet_coefficients_arithmetic = \
                        L.dirichlet_coefficients_arithmetic[:i]
                    break
    else:
        L.dirichlet_coefficients_arithmetic = [0, 1] + [ string2number(data['a' + str(i)]) for i in range(2, 11)]


    if L.analytic_normalization == 0:
        L.dirichlet_coefficients = L.dirichlet_coefficients_arithmetic[:]
    else:
        L.dirichlet_coefficients = [ an/(n+1)**L.analytic_normalization for n, an in enumerate(L.dirichlet_coefficients_arithmetic)]

    if 'coeff_info' in data and L.analytic_normalization == 0:   # hack, works only for Dirichlet L-functions
        apply_coeff_info(L, data['coeff_info'])


    # Configure the data for the zeros

    zero_truncation = 25   # show at most 25 positive and negative zeros
                           # later: implement "show more"
    L.positive_zeros_raw = [display_float(z, 12, 'round') if isinstance(z, float) else z for z in data['positive_zeros']]
    L.accuracy = data.get('accuracy', None)

    def convert_zeros(accuracy, list_zeros):
        two_power = 2 ** L.accuracy
        # the zeros were stored with .str(truncate = false)
        # we recover all the bits
        int_zeros = [ (RealNumber(elt) * two_power).round() for elt in list_zeros]
        # we convert them back to floats and we want to display their truncated version
        return [ (RealNumber(elt.str() + ".")/two_power).str(truncate = True) for elt in int_zeros]

    if L.accuracy is not None:
        L.positive_zeros_raw = convert_zeros(L.accuracy, L.positive_zeros_raw)
    L.positive_zeros = L.positive_zeros_raw[:zero_truncation]

    if L.selfdual:
        L.negative_zeros_raw = L.positive_zeros_raw[:]
        L.dual_accuracy = L.accuracy
    else:
        from .main import url_for_lfunction
        dual_L_Lhash = data['conjugate']
        dual_L_data = get_lfunction_by_Lhash(dual_L_Lhash)
        if dual_L_data.get('label'):
            L.dual_link = url_for_lfunction(dual_L_data['label'])
        elif dual_L_data.get('origin'):
            L.dual_link = '/L/' + dual_L_data['origin']
        L.dual_accuracy = dual_L_data.get('accuracy', None)
        L.negative_zeros_raw = [display_float(z, 12, 'round') if isinstance(z, float) else z for z in dual_L_data['positive_zeros']]
        if L.dual_accuracy is not None:
            L.negative_zeros_raw = convert_zeros(L.dual_accuracy, L.negative_zeros_raw)
    L.negative_zeros = L.negative_zeros_raw[:zero_truncation]
    L.negative_zeros = ["&minus;" + zero for zero in L.negative_zeros]
    L.negative_zeros_raw = [ '-' + zero for zero in reversed(L.negative_zeros_raw)]
    L.negative_zeros.reverse()
    L.negative_zeros += ['0' for _ in range(data['order_of_vanishing'])]
    L.negative_zeros = ", ".join(L.negative_zeros)
    L.positive_zeros = ", ".join(L.positive_zeros)
    if len(L.positive_zeros) > 2 and len(L.negative_zeros) > 2:  # Add comma and empty space between negative and positive
        L.negative_zeros = L.negative_zeros + ", "

    # Configure the data for the plot
    plot_delta = float(data['plot_delta'])
    if type(data['plot_values'][0]) is str:
        plot_values = [string2number(elt) for elt in data['plot_values']]
    else:
        plot_values = data['plot_values']
    pos_plot = [[j * plot_delta, elt]
                          for j, elt in enumerate( plot_values )]

    if L.selfdual:
        neg_plot = [ [-1*pt[0], L.sign * pt[1]]
                     for pt in pos_plot ][1:]
    else:
        if type(dual_L_data['plot_values'][0]) is str:
            dual_plot_values = [string2number(elt) for elt in dual_L_data['plot_values']]
        else:
            dual_plot_values = dual_L_data['plot_values']
        dual_plot_delta = float(dual_L_data['plot_delta'])
        neg_plot = [[-j * dual_plot_delta, elt]
                for j, elt in enumerate(dual_plot_values) ][1:]
    neg_plot.reverse()
    L.plotpoints = neg_plot + pos_plot

    L.trace_hash = data.get('trace_hash', None)
    L.types = data.get('types', None)

    L.fromDB = True






def apply_coeff_info(L, coeff_info):
    """ Converts the Dirichlet L-function coefficients and euler factors from
        the format in the database to algebraic and analytic form
    """

    def convert_coefficient(an, base_power_int):
        """
        this is only meant for dirichlet L-functions, and
        converts the format in the database to algebraic and analytic form
        """

        if not str(an).startswith('a'):
            res = an, an
        else:
            an_power = an[2:]
            an_power_int = int(an_power)
            this_gcd = gcd(an_power_int,base_power_int)
            an_power_int /= this_gcd
            this_base_power_int = base_power_int/this_gcd
            if an_power_int == 0:
                res = 1, 1
            elif this_base_power_int == 2:
                res = -1, -1
            elif this_base_power_int == 4:
                if an_power_int == 1:
                    res = I, I
                else:
                    res = -I, -I
            else:
                # an = e^(2 pi i an_power_int / this_base_power_int)
                arithmetic = r" $e\left(\frac{" + str(an_power_int) + "}{" + str(this_base_power_int)  + r"}\right)$"
                #exp(2*pi*I*QQ(an_power_int)/ZZ(this_base_power_int)).n()
                analytic = (2*CBF(an_power_int)/this_base_power_int).exppii()
                # round half integers
                analytic = round_CBF_to_half_int(analytic)
                res = arithmetic, analytic
        return res[0], CDF(res[1])

    base_power_int = int(coeff_info[0][2:-3])
    fix = False
    for n, an in enumerate(L.dirichlet_coefficients_arithmetic):
        L.dirichlet_coefficients_arithmetic[n], L.dirichlet_coefficients[n] =  convert_coefficient(an, base_power_int)
        # checks if we need to fix the Euler factors
        if is_prime(n) and L.dirichlet_coefficients_arithmetic[n] != 0:
            if fix:
                assert L.dirichlet_coefficients_arithmetic[n] == L.localfactors[prime_pi(n)-1]
            else:
                fix = L.dirichlet_coefficients_arithmetic[n] == L.localfactors[prime_pi(n)-1]
    def convert_euler_Lpoly(poly_coeffs):
        Fp = [convert_coefficient(c, base_power_int)[1] for c in poly_coeffs]
        # WARNING: the data in the database is wrong!
        # it lists Fp(-T) instead of Fp(T)
        # this is a temporary fix
        # the variable fix double checks that is indeed needed
        assert len(Fp) <= 2
        if len(Fp) == 2 and fix:
            Fp[1] *= -1
        return Fp
    L.bad_lfactors = [[p, convert_euler_Lpoly(poly)]
                      for p, poly in L.bad_lfactors]
    L.localfactors = [convert_euler_Lpoly(lf) for lf in L.localfactors]
    # the localfactors of the Dirichlet L-function in the DB omit the bad factors
    for p, fac in L.bad_lfactors:
        if prime_pi(p) <= len(L.localfactors):
            L.localfactors[prime_pi(p)-1] = fac
    L.coefficient_field = "CDF"


def generateSageLfunction(L):
    """ Generate a SageLfunction to do computations
    """
    logger.debug("Generating Sage Lfunction with parameters %s and there are %s coefficients "
                % ([L.coefficient_type, L.coefficient_period,
                L.Q_fe, L.sign, L.kappa_fe, L.lambda_fe,
                L.poles, L.residues], len(L.dirichlet_coefficients)))
    L.sageLfunction = lc.Lfunction_C("", L.coefficient_type,
                                        L.dirichlet_coefficients,
                                        L.coefficient_period,
                                        L.Q_fe, L.sign,
                                        L.kappa_fe, L.lambda_fe,
                                        L.poles, L.residues)




#############################################################################
# The subclasses
#############################################################################

class Lfunction_from_db(Lfunction):
    """
    Class representing a general L-function, to be retrieved from the database
    based on its lhash.

    Compulsory parameters: Lhash or label
    """
    def __init__(self, **kwargs):
        constructor_logger(self, kwargs)
        argkeys = ({'url', 'label', 'Lhash'}).intersection(set(kwargs))
        if len(argkeys) == 0:
            raise KeyError('Unable to construct L-function',
                           'Missing required parameters: label, Lhash, or url')
        if len(argkeys) > 1:
            raise ValueError("Cannot specify more than one argument in (label, Lhash, url)")

        self.numcoeff = 30
        if 'label' in kwargs:
            self.lfunc_data = get_lfunction_by_label(kwargs['label'])
        elif 'Lhash' in kwargs:
            self.lfunc_data = get_lfunction_by_Lhash(kwargs['Lhash'])
        else:
            self.lfunc_data = get_lfunction_by_Lhash(self.get_Lhash_by_url(kwargs['url']))

        makeLfromdata(self)
        self._set_knowltype()
        self.credit = ''
        self.label = self.lfunc_data['label']
        self.info = self.general_webpagedata()
        self.info['title'] = "L-function " + self.label
        if self.info['label'] == '1-1-1.1-r0-0-0':
          self.info['title'] = "L-function " + self.label + ": Riemann zeta function"

    @lazy_attribute
    def _Ltype(self):
        return "general"

    @lazy_attribute
    def langlands(self):
        # this controls data on the Euler product, but is not stored
        # systematically in the database. Default to True until this
        # is retrievable from the database.
        return True
    @lazy_attribute
    def bread(self):
        from .main import url_for_lfunction
        _, conductor, character, cr, imag, index = self.label.split('-')
        spectral_label = cr + '-' + imag
        degree = self.degree
        conductor  = conductor.replace('e', '^')
        bread = [('L-functions', url_for('.index'))]
        if self.rational:
            bread.append(('Rational', url_for('.rational')))
            route = '.by_url_rational_degree_conductor_character_spectral'
        else:
            route = '.by_url_degree_conductor_character_spectral'

        bread.extend([
            (str(degree), url_for(route, degree=degree)),
            (conductor, url_for(route,
                                degree=degree,
                                conductor=conductor)),
            (character, url_for(route,
                                degree=degree,
                                conductor=conductor,
                                character=character)),
            (spectral_label, url_for(route,
                                     degree=degree,
                                     conductor=conductor,
                                     character=character,
                                     spectral_label=spectral_label)),
            (index, url_for_lfunction(self.label))
        ])
        return bread

    @lazy_attribute
    def origin_label(self):
        return self.Lhash



    def get_Lhash_by_url(self, url):
        instance = get_instance_by_url(url)
        if instance is None:
            raise KeyError('No L-function instance data for "%s" was found in the database.' % url)
        return instance['Lhash']


    @lazy_attribute
    def origins(self):
        # objects that arise the same identical L-function
        return names_and_urls(get_instances_by_label(self.label))

    @property
    def friends(self):
        """
        This populates Related objects
        dual L-fcn and other objects that this L-fcn divides
        """
        # dual L-function and objects such that the L-functions contain this L-function as a factor
        related_objects = []
        if not self.selfdual and hasattr(self, 'dual_link'):
            related_objects.append(("Dual L-function", self.dual_link))

        instances = get_multiples_by_Lhash_and_trace_hash(
                self.Lhash, self.degree, self.trace_hash)
        return related_objects + names_and_urls(instances)

    @lazy_attribute
    def factors_origins(self):
        # objects for the factors
        return names_and_urls(get_factors_instances(self.Lhash, self.degree, self.trace_hash))

    @lazy_attribute
    def instances(self):
        return [] # disable instances
        # we got here by tracehash or Lhash
        if self._Ltype == "general":
            linstances = []
            for instance in get_instances_by_Lhash(self.Lhash):
                url = instance['url']
                url = "/L/" + url
                linstances.append((url[1:], url))
            return linstances
        else:
            return []

    @lazy_attribute
    def downloads(self):
        return [['Euler factors to text', self.download_euler_factors_url],
                ['Zeros to text', self.download_zeros_url],
                ['Dirichlet coefficients to text', self.download_dirichlet_coeff_url]]

    @lazy_attribute
    def download_euler_factors_url(self):
        return url_for('.download_euler_factors', label=self.label)

    @lazy_attribute
    def download_zeros_url(self):
        return url_for('.download_zeros', label=self.label)

    @lazy_attribute
    def download_dirichlet_coeff_url(self):
        return url_for('.download_dirichlet_coeff', label=self.label)

    @lazy_attribute
    def download_url(self):
        return url_for('.download', label=self.label)

    def download_euler_factors(self):
        filename = self.label
        data  = {}
        data['bad_lfactors'] = self.bad_lfactors
        ps = primes_first_n(len(self.localfactors))
        data['first_lfactors'] = [ [ps[i], l] for i, l in enumerate(self.localfactors)]
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.euler_factors',
                lang = 'text',
                title = 'Euler Factors of %s' % self.label)

    def download_zeros(self):
        filename = self.label
        data  = {}
        data['order_of_vanishing'] = self.order_of_vanishing
        data['positive_zeros'] = self.positive_zeros_raw
        data['negative_zeros'] = self.negative_zeros_raw
        data['positive_zeros_accuracy'] = self.accuracy
        data['negative_zeros_accuracy'] = self.dual_accuracy
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.zeros',
                lang = 'text',
                title = 'Zeros of %s' % self.label)

    def download_dirichlet_coeff(self):
        filename = self.label
        data  = {}
        data['an'] = an_from_data(self.localfactors, next_prime(nth_prime(len(self.localfactors)+1)) - 1)
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.dir_coeffs',
                lang = 'text',
                title = 'Dirichlet coefficients of %s' % self.label)

    def download(self):
        filename = self.label
        data  = dict(self.__dict__)
        for k in ['level_factored', 'dirichlet_coefficients']:
            if isinstance(data[k], list):
                data[k] = list(map(str, data[k]))
            else:
                data[k] = str(data[k])
        data.pop('level_factored')
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.lfunction',
                lang = 'text',
                title = 'The L-function object of %s' % self.label)


    @lazy_attribute
    def htmlname(self):
        return "<em>L</em>(<em>s</em>)"

    @lazy_attribute
    def htmlname_arithmetic(self):
        return self.htmlname

    @lazy_attribute
    def texname(self):
        return "L(s)"

    @lazy_attribute
    def texname_arithmetic(self):
        return self.texname

    @lazy_attribute
    def texnamecompleted1ms(self):
        if self.selfdual:
            return r"\Lambda(1-s)"
        else:
            return r"\overline{\Lambda}(1-s)"

    @lazy_attribute
    def texnamecompleted1ms_arithmetic(self):
        if self.selfdual:
            return r"\Lambda(%d-s)" % (self.motivic_weight + 1)
        else:
            return r"\overline{\Lambda}(%d-s)" % (self.motivic_weight + 1)

    @lazy_attribute
    def texnamecompleteds(self):
        return r"\Lambda(s)"

    @lazy_attribute
    def texnamecompleteds_arithmetic(self):
        return self.texnamecompleteds

    #def _retrieve_lfunc_data_from_db(self):
    #    self.lfunc_data = get_lfunction_by_url(self.url)
    #    if not self.lfunc_data:
    #        raise KeyError('No L-function instance data for "%s" was found in the database.' % self.url)
    #    return

    @lazy_attribute
    def knowltype(self):
        return None

    def _set_knowltype(self):
        if self.knowltype is not None:
            self.info['knowltype'] = self.knowltype




#############################################################################

class Lfunction_Maass(Lfunction):
    """Class representing the L-function of a Maass form

    Compulsory parameters: maass_id (if not from DB)
                           fromDB  (True if data is in Lfuntions database)

    Possible parameters: group,level,char,R,ap_id  (if data is in Lfunctions DB)
    """
    def __init__(self, **args):
        constructor_logger(self, args)

        # Initialize default values
        self.numcoeff = 30  # set default to 30 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)

        # Check for compulsory arguments
        if self.fromDB:
            validate_required_args ('Unable to construct L-function of Maass form.',
                                    args, 'group', 'level', 'char', 'R', 'ap_id')
        else:
            validate_required_args ('Unable to construct L-function of Maass form.',
                                    args, 'maass_id')

        self._Ltype = "maass"

        if self.fromDB:   # L-function data is in Lfunctions DB
            # Load data from the database
            self.maass_id = "ModularForm/%s/Q/Maass/%s/%s/%s/%s/" % (
                self.group, self.level, self.char, self.R, self.ap_id)
            self.lfunc_data = get_lfunction_by_url(self.maass_id)
            if self.lfunc_data is None:
                raise KeyError('No L-function instance data for "%s" was found in the database.' % self.maass_id)

            # Extract the data
            makeLfromdata(self)

            # Mandatory properties
            self.coefficient_period = 0
            self.coefficient_type = 0
            self.poles = []
            self.residues = []
            self.langlands = True
            self.quasidegree = self.degree

            # Specific properties
            if not self.selfdual:
                self.dual_link = '/L' + self.lfunc_data.get('conjugate', None)
            title_end = ""  #" on $%s$" % (self.group)

        else:   # Generate from Maass form

            # Create the Maass form
            self.mf = WebMaassForm.by_maass_id(self.maass_id)
            self.group = 'GL2'

            # Extract the L-function information from the Maass form object
            self.symmetry = self.mf.symmetry
            self.level = int(self.mf.level)
            self.level_factored = factor(self.level)
            self.charactermodulus = self.level
            self.weight = int(self.mf.weight)
            self.characternumber = int(self.mf.conrey_index)
            if self.level > 1:
                try:
                    self.fricke = self.mf.fricke_eigenvalue
                except Exception:
                    raise KeyError('No Fricke information available for '
                                   + 'Maass form so not able to compute '
                                   + 'the L-function. ')
            else:  # no fricke for level 1
                self.fricke = 1
            if self.symmetry == -1: # odd
                self.sign = -self.fricke
                aa = 1
            else:
                self.sign = self.fricke
                aa = 0

            # Mandatory properties
            self.coefficient_type = 2
            self.coefficient_period = 0
            self.poles = []
            self.residues = []
            self.langlands = True
            self.primitive = True
            self.degree = 2
            self.quasidegree = 2
            self.eigenvalue = self.mf.spectral_parameter if self.mf.spectral_parameter else 0
            self.mu_fe = [aa + self.eigenvalue * I, aa - self.eigenvalue * I]
            self.nu_fe = []
            self.compute_kappa_lambda_Q_from_mu_nu()
            self.algebraic = False
            # Todo: If self has dimension >1, link to specific L-functions
            self.dirichlet_coefficients = self.mf.coeffs
            if 0 in self.dirichlet_coefficients and self.dirichlet_coefficients[0] == 0:
                self.dirichlet_coefficients.pop(0)
            self.checkselfdual()
            self.credit = self.mf.contributor if 'contributor' in dir(self.mf) else ''

            title_end = " and $R= %s$" % (self.eigenvalue)

            # Generate a function to do computations
            minNumberOfCoefficients = 100     # TODO: Fix this to take level into account
            if len(self.dirichlet_coefficients) >= minNumberOfCoefficients:
                generateSageLfunction(self)
            else:
                self.sageLfunction = None

        # Text for the web page
        self.texname = "L(s,f)"
        self.texnamecompleteds = r"\Lambda(s,f)"

        if self.selfdual:
            self.texnamecompleted1ms = r"\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = r"\Lambda(1-s,\overline{f})"
        self.origin_label = self.maass_id

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "mf.maass"
        if self.degree > 2:
            R_commas = "(" + self.R.replace("_", ", ") + ")"
            self.info['title'] = ("L-function of degree %s, " % (self.degree)
                      + "conductor %s, and " % (self.level)
                      + "spectral parameters %s" % (R_commas)
                      + title_end)
        else:
            self.info['title'] = ("$L(s,f)$, where $f$ is a Maass cusp form with "
                      + "level %s" % (self.level)) + title_end


class Lfunction_HMF(Lfunction):
    """Class representing a Hilbert modular form L-function

    Compulsory parameters: label

    Possible parameters: number, character

    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        validate_required_args ('Unable to construct Hilbert modular form ' +
                                'L-function.', args, 'label', 'number', 'character')
        validate_integer_args ('Unable to construct Hilbert modular form L-function.',
                               args, 'character','number')

        self._Ltype = "hilbertmodularform"

        # Put the arguments into the object dictionary
        self.origin_label = args['label']
        self.number = int(args['number'])
        self.character= int(args['character'])
        if self.character != 0:
            raise KeyError('L-function of Hilbert form of non-trivial character not implemented yet.')

        # Load form (f) from database
        (f, F_hmf) = getHmfData(self.origin_label)
        if f is None:
            # NB raising an error is not a good way to handle this on website!
            raise KeyError('No Hilbert modular form with label "%s" found in database.'%self.origin_label)
        try:
            self.weight = int(f['parallel_weight'])
        except KeyError:
            self.weight = int(f['weight'].split(', ')[0][1:])

        # Load the field (F)
        F = WebNumberField(f['field_label'])
        if not F or F.is_null():
            raise KeyError('Error constructing number field %s'%f['field_label'])
        self.field_disc = F.disc()
        self.field_degree = int(F.degree())

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 3
        self.coefficient_period = 0
        self.poles = []
        self.residues = []
        self.langlands = True
        self.primitive = True
        self.degree = 2 * self.field_degree
        self.quasidegree = self.degree
        self.level = f['level_norm'] * self.field_disc ** 2
        self.level_factored = factor(self.level)
        self.mu_fe = []
        self.nu_fe = [Rational(self.weight - 1)/2 for i in range(self.field_degree)]
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.algebraic = True
        self.motivic_weight = self.weight - 1
        self.automorphyexp = self.motivic_weight / 2.

        # Compute Dirichlet coefficients ########################
        R = QQ['x']
        (x,) = R._first_ngens(1)
        K = NumberField(R(str(f['hecke_polynomial']).replace('^', '**')), 'e')
        iota = K.complex_embeddings()[self.number]

        hecke_eigenvalues = [iota(K(str(ae))) for ae in f['hecke_eigenvalues']]
        primes = [pp_str.split(', ') for pp_str in F_hmf['primes']]
        primes = [[int(pp[0][1:]), int(pp[1])] for pp in primes]
        primes = [[pp[0], pp[1], factor(pp[0])[0][1]] for pp in primes]

        PP = primes[-1][0]
        self.numcoeff = PP  # The number of coefficients is given by the
                            # norm of the last prime

        Fhmfprimes = [st.replace(' ','') for st in F_hmf['primes']]

        ppmidNN = [c[0].replace(' ','') for c in f['AL_eigenvalues']]

        ratl_primes = [p for p in range(primes[-1][0] + 1) if is_prime(p)]
        RCC = CC['T']
        (T,) = RCC._first_ngens(1)
        heckepols = [RCC(1) for p in ratl_primes]
        for l in range(len(hecke_eigenvalues)):
            if Fhmfprimes[l] in ppmidNN:
                heckepols[ratl_primes.index(primes[l][1])] *= (
                    1 - hecke_eigenvalues[l] / float(sqrt(primes[l][0]))
                    * (T ** primes[l][2]))
            else:
                heckepols[ratl_primes.index(primes[l][1])] *= (
                    1 - hecke_eigenvalues[l] / float(
                    sqrt(primes[l][0])) * (T ** primes[l][2])
                    + (T ** (2 * primes[l][2])))

        # Compute inverses up to given degree
        heckepolsinv = [heckepols[i].xgcd(T ** ceil(log(PP * 1.0) /
                                    log(ratl_primes[i] * 1.0)))[1]
                                    for i in range(len(heckepols))]

        dcoeffs = [0, 1]
        for n in range(2, ratl_primes[-1] + 1):
            nfact = factor(n)
            if len(nfact) == 1:
                # prime power
                p = nfact[0][0]
                k = nfact[0][1]
                # S = [1] + [dcoeffs[p ** i] for i in range(1, k)]
                heckepol = heckepolsinv[ratl_primes.index(p)]
                dcoeffs.append(heckepol[k])
            else:
                # composite
                ancoeff = prod([dcoeffs[pe[0] ** pe[1]] for pe in nfact])
                dcoeffs.append(ancoeff)

        self.dirichlet_coefficients = dcoeffs[1:]

        # Compute the sign ########################
        if self.level == 1:  # For level 1, the sign is always plus
            self.sign = 1
        else:  # for level>1, calculate sign from Fricke involution and weight
            ALeigs = [str(al[1]).replace('^', '**') for al in f['AL_eigenvalues']]
            # the above fixed a bug at
            # L/ModularForm/GL2/TotallyReal/2.2.104.1/holomorphic/2.2.104.1-5.2-c/0/0/
            # but now the sign is wrong (i.e., not of absolute value 1 *)
            AL_signs = [iota(K(str(al))) for al in ALeigs]
            self.sign = prod(AL_signs) * (-1) ** (float(self.weight *
                                                        self.field_degree / 2))
        self.checkselfdual()

        # Text for the web page
        self.texname = "L(s,f)"
        self.texnamecompleteds = r"\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = r"\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = r"\Lambda(1-s,\overline{f})"
        self.credit = ''

        # Generate a function to do computations
        generateSageLfunction(self)

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "mf.hilbert"
        self.info['title'] = ("$L(s,f)$, " + "where $f$ is a holomorphic Hilbert cusp form "
                      + "over " + F.field_pretty()
                      + " with parallel weight " + str(self.weight)
                      + ", level norm " + str(f['level_norm']) )
        if self.character:
            self.info['title'] += ", and character " + str(self.character)
        else:
            self.info['title'] += ", and trivial character"

    def original_object(self):
        return self.f


#############################################################################

class Lfunction_SMF2_scalar_valued(Lfunction):
    """Class representing an L-function for a scalar valued Siegel modular form of degree 2

    Compulsory parameters: weight
                           orbit (SMF sample name is weight_orbt (e.g. 16_Klingen))

    Optional parameters: number (indicates choice of embedding)
    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        validate_required_args('Unable to construct Siegel modular form L-function.',
                               args, 'weight', 'orbit')
        if self.orbit[0] == 'U':
            self._Ltype = "siegelnonlift"
        elif self.orbit[0] == 'E':
            self._Ltype = "siegeleisenstein"
        elif self.orbit[0] == 'K':
            self._Ltype = "siegelklingeneisenstein"
        elif self.orbit[0] == 'M':
            self._Ltype = "siegelmaasslift"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.weight = int(self.weight)
        if args['number']:
            self.number = int(args['number'])
        else:
            self.number = 0     # Default embedding of the coefficients

        # Load form (S) from database
        label = '%d_%s'%(self.weight,self.orbit)
        self.S = Sample('Sp4Z', label)
        if not self.S:
            raise KeyError("Siegel modular form Sp4Z.%s not found in database." % label)
        self.field = self.S.field()
        evlist = self.S.available_eigenvalues()
        if len(evlist) < 3: # FIXME -- we should sanity check that we have enough eigenvalues for it make sense to display an L-function page (presumably 3 is not enough)
            raise ValueError("Eigenvalue data for Siegel modular form Sp4Z.%s not available or insufficient." % label)
        self.evs = self.S.eigenvalues(self.S.available_eigenvalues())
        for ev in self.evs:
            self.evs[ev] = self.field(self.evs[ev])

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 3
        self.coefficient_period = 0
        if self.orbit[0] == 'U':  # if the form isn't a lift but is a cusp form
            self.poles = []  # the L-function is entire
            self.residues = []
            self.primitive = True  # and primitive
        elif self.orbit[0] == 'E':  # if the function is an Eisenstein series
            self.poles = [float(3) / float(2)]
            self.residues = [math.pi ** 2 / 6]  # FIXME: fix this
            self.primitive = False
        elif self.orbit[0] == 'M':  # if the function is a lift and a cusp form
            self.poles = [float(3) / float(2)]
            self.residues = [math.pi ** 2 / 6]  # FIXME: fix this
            self.primitive = False
        elif self.orbit[0] == 'K':
            self.poles = [float(3) / float(2)]
            self.residues = [math.pi ** 2 / 6]  # FIXME: fix this
            self.primitive = False
        self.langlands = True
        self.degree = 4
        self.quasidegree = 1
        self.level_factored = self.level = 1
        self.mu_fe = []  # the shifts of the Gamma_R to print
        self.automorphyexp = float(self.weight) - float(1.5)
        self.nu_fe = [Rational(1/2), self.automorphyexp]  # the shift of the Gamma_C to print
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.algebraic = True
        self.motivic_weight = 2*self.weight - 3 # taken from A. Panchiskin's talk @ Oberwolfach, Oct. 2007

        # Compute Dirichlet coefficients ########################
        roots = compute_local_roots_SMF2_scalar_valued(self.field, self.evs, self.weight, self.number)  # compute the roots of the Euler factors
        self.numcoeff = max([a[0] for a in roots])+1  # include a_0 = 0

        # FIXME: the function compute_siegel_dirichlet_coefficients is not defined anywhere!
        # self.dirichlet_coefficients = compute_siegel_dirichlet_series(roots, self.numcoeff)  # these are in the analytic normalization, coeffs from Gamma(ks+lambda)

        self.sign = (-1) ** float(self.weight)
        self.checkselfdual()

        # Text for the web page
        self.texname = "L(s,F)"
        self.texnamecompleteds = r"\Lambda(s,F)"
        if self.selfdual:
            self.texnamecompleted1ms = r"\Lambda(1-s,F)"
        else:
            self.texnamecompleted1ms = r"\Lambda(1-s,\overline{F})"
        self.credit = ''

        # Generate a function to do computations
        generateSageLfunction(self)
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "mf.siegel"
        self.info['title'] = ("$L(s,F)$, " + "Where $F$ is a Scalar-valued Siegel " +
                      "Modular form of weight " + str(self.weight) + ".")

    def original_object(self):
        return self.S

#############################################################################



class DedekindZeta(Lfunction):
    """Class representing the Dedekind zeta-function

    Compulsory parameters: label

    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        validate_required_args ('Unable to construct Dedekind zeta function.', args, 'label')
        self._Ltype = "dedekindzeta"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.origin_label = self.label
        self.__dict__.pop('label')

        # Fetch the polynomial of the field from the database
        wnf = WebNumberField(self.origin_label)
        if not wnf or wnf.is_null():
            raise KeyError('Unable to construct Dedekind zeta function.', 'No data for the number field "%s" was found in the database'%self.origin_label)
        self.NF = wnf.K()
        self.h = wnf.class_number()
        self.R = wnf.regulator()
        self.w = len(self.NF.roots_of_unity())
        self.signature = self.NF.signature()

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 3
        self.coefficient_period = 0
        self.poles = [1, 0]  # poles of the Lambda(s) function
        if self.h == "Not computed" or self.R == "Not computed":
            self.res = self.residues = 0  # Not able to compute residue
        else:
            self.res = RR(2 ** self.signature[0] * self.h * self.R) / self.w
            self.residues = [self.res, -self.res]
        self.poles_L = [1]  # poles of L(s) used by createLcalcfile_ver2
        self.residues_L = [1234] # residues of L(s) used by createLcalcfile_ver2,
                                 # TODO: needs to be set
        self.langlands = True
        self.primitive = False
        self.degree = self.NF.degree()
        self.quasidegree = sum(self.signature)
        self.level = self.NF.discriminant().abs()
        self.level_factored = factor(self.level)
        self.mu_fe = self.signature[0] * [0]
        self.nu_fe = self.signature[1] * [0]
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.algebraic = True
        self.motivic_weight = 0
        self.dirichlet_coefficients = [Integer(x) for x in
                                       self.NF.zeta_coefficients(5000)] # TODO: adjust nr of coef
        self.sign = 1
        self.selfdual = True

        # Specific properties
        # Determine the factorization
        self.grh = wnf.used_grh()
        if self.degree > 1:
            if wnf.is_abelian() and len(wnf.dirichlet_group())>0:
                dir_group = wnf.dirichlet_group()
                # Remove 1 from the list
                j = 0
                while dir_group[j] != 1:
                    j += 1
                dir_group.pop(j)
                self.factorization = (r'\(\zeta_K(s) =\) ' +
                                      r'<a href="/L/Riemann/">\(\zeta(s)\)</a>')
                cond = wnf.conductor()
                for j in dir_group:
                    chij = ConreyCharacter(cond, j)
                    mycond = chij.conductor()
                    myj = j % mycond
                    self.factorization += (r'\(\;\cdot\) <a href="/L/Character/Dirichlet/%d/%d/">\(L(s,\chi_{%d}(%d, \cdot))\)</a>'
                                           % (mycond, myj, mycond, myj))
            elif wnf.factor_perm_repn():
                nfgg = wnf.factor_perm_repn() # first call cached it
                ar = wnf.artin_reps() # these are in the same order
                self.factorization = (r'\(\zeta_K(s) =\) <a href="/L/Riemann/">'
                                           +r'\(\zeta(s)\)</a>')
                for j in range(len(ar)):
                    if nfgg[j]>0:
                        the_rep = ar[j]
                        if (the_rep.dimension()>1 or
                                  str(the_rep.conductor())!=str(1)):
                            ar_url = url_for("l_functions.l_function_artin_page",
                                             label=the_rep.label())
                            right = (r'\({}^{%d}\)' % (nfgg[j])
                                     if nfgg[j]>1 else r'')
                            self.factorization += r'\(\;\cdot\)'
                            tex_label = the_rep.label()
                            tex_label = tex_label.replace('_',r'\_')
                            self.factorization += (r'<a href="%s">\(L(s, \rho_{%s})\)</a>' % (ar_url, tex_label))
                            self.factorization += right

        # Text for the web page
        self.texname = r"\zeta_K(s)"
        self.texnamecompleteds = r"\Lambda_K(s)"
        self.texnamecompleted1ms = r"\Lambda_K(1-s)"
        self.credit = 'Sage'

        # Generate a function to do computations
        # But only if we know the residue and when the degree is at most 4, due to bugs in the
        # Sage lcalc library (see issues #1687 and #1691)
        if self.res and self.degree <= 4:
            generateSageLfunction(self)
        else:
            self.sageLfunction = None

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "nf"
        self.info['label'] = ''
        self.info['title'] = r"Dedekind zeta-function: $\zeta_K(s)$, where $K$ is the number field with defining polynomial %s" %  web_latex(self.NF.defining_polynomial())

    def original_object(self):
        return self.NF



class ArtinLfunction(Lfunction):
    """Class representing the Artin L-function

    Compulsory parameters: label

    """
    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        validate_required_args('Unable to construct Artin L-function', args, 'label')
        self._Ltype = "artin"

        # Put the arguments into the object dictionary
        self.origin_label = args["label"]

        # Create the Artin representation
        try:
            self.artin = ArtinRepresentation(self.origin_label)
        except Exception as err:
            raise KeyError('Error constructing Artin representation %s.'%self.origin_label, *err.args)

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 0
        self.poles = self.artin.completed_poles()
        self.residues = self.artin.completed_residues()
        self.poles_L = self.artin.poles()
        self.residues_L = self.artin.residues()
        self.langlands = self.artin.langlands()
        self.primitive = self.artin.primitive()
        self.degree = self.artin.dimension()
        self.level = self.artin.conductor()
        self.level_factored = factor(self.level)
        self.mu_fe = self.artin.mu_fe()
        self.nu_fe = self.artin.nu_fe()
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.quasidegree = len(self.mu_fe) + len(self.nu_fe)
        self.algebraic = True
        self.motivic_weight = 0
        cc = self.artin.central_character()
        if not cc:
            raise ValueError('Error constructing Artin representation %s, unable to compute central character, possibly because the modulus is too large.'%self.origin_label)
        self.charactermodulus, self.characternumber = cc.modulus, cc.number

        # Compute Dirichlet coefficients and period ########################
        if self.degree == 1:
            self.coefficient_period = Integer(self.artin.conductor())
            self.dirichlet_coefficients = self.artin.coefficients_list(
                upperbound=self.coefficient_period)
        else:
            self.coefficient_period = 0
            self.dirichlet_coefficients = self.artin.coefficients_list(
                upperbound=1000)

        self.sign = self.artin.root_number()
        self.selfdual = self.artin.selfdual()

        # Text for the web page
        self.texname = r"L(s,\rho)"
        self.texnamecompleteds = r"\Lambda(s)"
        if self.selfdual:
            self.texnamecompleted1ms = r"\Lambda(1-s)"
        else:
            self.texnamecompleted1ms = r"\overline{\Lambda(1-\overline{s})}"
        self.credit = ('Sage, lcalc, and data precomputed in ' +
                       'Magma by Tim Dokchitser')

        # Generate a function to do computations
        if self.sign == 0:
            self.sageLfunction = None
        else:
            generateSageLfunction(self)

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "artin"
        self.info['title'] = ("L-function for Artin representation " + str(self.origin_label))

    def original_object(self):
        return self.artin

#############################################################################

class HypergeometricMotiveLfunction(Lfunction):
    """Class representing the hypergeometric L-function

    Two options for parameters:
        label, for instance 'A2.2.2.2_B1.1.1.1_t1.2'
    or
        family, for instance 'A2.2.2.2_B1.1.1.1'
        and t for instance 't1.2'
    """
    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        if "t" in args and "family" in args:
            args["label"] = args["family"] + "_" + args["t"]
        validate_required_args ('Unable to construct hypergeometric motive L-function.', args, 'label')
        self._Ltype = "hgmQ"

        # Put the arguments into the object dictionary
        self.origin_label = args["label"]

        # Get the motive from the database
        self.motive = getHgmData(self.origin_label)
        if not self.motive:
            raise KeyError('No data for the hypergeometric motive "%s" was found in the database.'%self.origin_label)

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 0
        self.coefficient_period = 0
        # level, residues, selfdual, primitive, langlands
        # will not work for some values!!!!
        self.poles = []
        self.residues = []
        self.langlands = True
        self.primitive = True
        self.degree = self.motive["degree"]
        self.level = self.motive["cond"]
        self.level_factored = factor(self.level)
        self.mu_fe, self.nu_fe = lmfdb.hypergm.hodge.mu_nu(self.motive["hodge"], self.motive["sig"])
        self.compute_kappa_lambda_Q_from_mu_nu()            # Somehow this doesn t work, and I don t know why!
        self.quasidegree = len(self.mu_fe) + len(self.nu_fe)
        self.algebraic = True
        self.motivic_weight =  self.motive["weight"]
        # Compute Dirichlet coefficients ########################
        try:
            self.arith_coeffs = self.motive["coeffs"]
        except Exception:
            self.arith_coeffs = [Integer(k)
                                 for k in self.motive["coeffs_string"]]
        self.dirichlet_coefficients = [Reals()(Integer(x))/Reals()(n+1)**(self.motivic_weight/2.)
                                       for n, x in enumerate(self.arith_coeffs)]
        self.sign = self.motive["sign"]
        self.selfdual = True

        # Text for the web page
        self.texname = "L(s)"
        self.texnamecompleteds = r"\Lambda(s)"
        if self.selfdual:
            self.texnamecompleted1ms = r"\Lambda(1-s)"
        else:
            self.texnamecompleted1ms = r"\overline{\Lambda(1-\overline{s})}"
        self.credit = 'Dave Roberts, using Magma'

        # Generate a function to do computations
##        Lexponent = self.motivic_weight/2.
##        normalize =lambda coeff, n, exponent: Reals()(coeff)/n**exponent
##        self.dirichlet_coefficient = [normalize(coeff, i+1, Lexponent) for i, coeff in enumerate(self.arith_coeffs)]
##        Are these coefficients not the same as dirichlet_coefficients computed above
        self.sageLfunction = lc.Lfunction_D("LfunctionHypergeometric", 0, self.dirichlet_coefficients, self.coefficient_period,
                                            self.Q_fe, self.sign, self.kappa_fe, self.lambda_fe, self.poles, self.residues)


        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "hgm"
        self.info['title'] = ("L-function for the hypergeometric motive with label "+self.origin_label)

    def original_object(self):
        return self.motive

 #############################################################################


class SymmetricPowerLfunction(Lfunction):
    """Class representing the Symmetric power of an L-function

    Only implemented for (non-CM) elliptic curves

    Compulsory parameters: power, underlying_type, field
    For ellitic curves: conductor, isogeny

    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        validate_required_args('Unable to construct symmetric power L-function.',
                               args, 'power', 'underlying_type', 'field',
                               'conductor', 'isogeny')
        validate_integer_args ('The power has to be an integer.',
                               args, 'power', 'conductor')
        self._Ltype = "SymmetricPower"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.m = int(self.power)
        self.origin_label = str(self.conductor) + '.' + self.isogeny
        if self.underlying_type != 'EllipticCurve' or self.field != 'Q':
            raise TypeError("The symmetric L-functions have been implemented " +
                            "only for elliptic curves over Q.")

        # Create the elliptic curve
        Edata = getEllipticCurveData(self.origin_label + '1')
        if Edata is None:
            raise KeyError('No elliptic curve with label %s exists in the database' % self.origin_label)
        else:
            self.E = EllipticCurve([int(a) for a in Edata['ainvs']])

        if self.E.has_cm():
            raise TypeError('This Elliptic curve has complex multiplication' +
                            ' and the symmetric power of its L-function is ' +
                            'then not primitive. This has not yet been ' +
                            'implemented')

        # Create the symmetric power L-function
        from lmfdb.symL.symL import SymmetricPowerLFunction
        self.S = SymmetricPowerLFunction(self.E, self.m)

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 0
        self.coefficient_period = 0
        self.poles = self.S._poles
        self.residues = self.S._residues
        self.langlands = True
        self.primitive = True
        self.degree = self.m + 1
        self.level = self.S.conductor
        self.level_factored = factor(self.level)
        self.kappa_fe = self.S._kappa_fe
        self.lambda_fe = self.S._lambda_fe
        self.Q_fe = self.S._Q_fe
        pairs_fe = list(zip(self.kappa_fe, self.lambda_fe))
        self.mu_fe = [lambda_fe*2. for kappa_fe, lambda_fe in pairs_fe if abs(kappa_fe - 0.5) < 0.001]
        self.nu_fe = [lambda_fe for kappa_fe, lambda_fe in pairs_fe if abs(kappa_fe - 1) < 0.001]
        self.quasidegree = len(self.mu_fe) + len(self.nu_fe)
        self.algebraic = True
        self.motivic_weight = self.m
        self.dirichlet_coefficients = self.S._coeffs
        self.sign = self.S.root_number
        self.selfdual = True

        # Text for the web page
        self.texname = r"L(s, E, \mathrm{sym}^{%d})" % self.m
        self.texnamecompleteds = r"\Lambda(s,E,\mathrm{sym}^{%d})" % self.S.m
        self.texnamecompleted1ms = (r"\Lambda(1-{s}, E,\mathrm{sym}^{%d})"
                                    % self.S.m)
        self.credit = ' '

        # Generate a function to do computations
        if self.level < 15000:
            self.sageLfunction = self.S._construct_L()
        else:
            self.sageLfunction = None

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "sym"

        def ordinal(n):
            if n == 2:
                return "Square"
            elif n == 3:
                return "Cube"
            elif 10 <= n % 100 < 20:
                return str(n) + "th Power"
            else:
                return (str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, "th") +
                        " Power")

        self.info['title'] = (r"The Symmetric %s $L$-function $L(s,E,\mathrm{sym}^{%d})$ of elliptic curve isogeny class %s"
                      % (ordinal(self.m), self.m, self.origin_label))


    def original_object(self):
        return self.S


#############################################################################

# This class it not used anywhere and has not been touched since January 2014.  The key function TensorProduct is not defined anywhere, so it won't work
# There is closely related code in lmfdb/tensor_products that perhaps is meant to supersede this?
# This should either be fully implemented or removed when #500 is addressed (Release 2.0)

class TensorProductLfunction(Lfunction):
    """
    Class representing the L-function of a tensor product
    (currently only of a elliptic curve with a Dirichlet character)

    arguments are

    - charactermodulus
    - characternumber
    - ellipticcurvelabel

    """

    def __init__(self, **args):

        # Check for compulsory arguments
        validate_required_args('Unable to construct tensor product L-function.', args, 'charactermodulus', 'characternumber', 'ellipticcurvelabel')

        self._Ltype = "tensorproduct"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.charactermodulus = int(self.charactermodulus)
        self.characternumber = int(self.characternumber)
        self.Elabel = self.ellipticcurvelabel

        # Create the tensor product

        # No TensorProduct class exists in the LMFDB at present, there is code in lmfdb/tensor_products for computing tensor product L-functions,
        # but it does not implement the TensorProduct class (see issue #500)
        raise NotImplementedError
        # self.tp = TensorProduct(self. Elabel, self.charactermodulus, self.characternumber)
        # chi = self.tp.chi
        # E = self.tp.E

        self.motivic_weight = 1
        self.weight = 2
        self.algebraic = True
        self.poles = []
        self.residues = []
        self.langlands = True
        self.primitive = True
        self.degree = 2
        self.quasidegree = 1
        self.level = int(self.tp.conductor())
        self.sign = self.tp.root_number()
        self.coefficient_type = 3
        self.coefficient_period = 0


        # We may want to change this later to a better estimate.
        self.numcoeff = 20 + ceil(sqrt(self.tp.conductor()))

        self.mu_fe = []
        self.nu_fe = [Rational('1/2')]
        self.compute_kappa_lambda_Q_from_mu_nu()

        li = self.tp.an_list(upper_bound=self.numcoeff)
        for n in range(1,len(li)):
            # now renormalise it for s <-> 1-s as the functional equation
            li[n] /= sqrt(float(n))
        self.dirichlet_coefficients = li

        self.texname = r"L(s,E,\chi)"
        self.texnamecompleteds = r"\Lambda(s,E,\chi)"
        self.title = r"$L(s,E,\chi)$, where $E$ is the elliptic curve %s and $\chi$ is the Dirichlet character of conductor %s, modulo %s, number %s"%(self.ellipticcurvelabel, self.tp.chi.conductor(), self.charactermodulus, self.characternumber)

        self.credit = 'Workshop in Besancon, 2014'

        generateSageLfunction(self)

        constructor_logger(self, args)

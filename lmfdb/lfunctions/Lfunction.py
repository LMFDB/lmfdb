# -*- coding: utf-8 -*-
# The class Lfunction is defined in Lfunction_base and represents an L-function
# We subclass it here:
# RiemannZeta, Lfunction_Dirichlet, Lfunction_EC_Q, Lfunction_CMF,
# Lfunction_HMF, Lfunction_Maass, Lfunction_SMF2_scalar_valued,
# DedekindZeta, ArtinLfunction, SymmetricPowerLfunction,
# Lfunction_genus2_Q

import math
import re

from flask import url_for, request
from lmfdb.db_encoding import Json

from Lfunctionutilities import (string2number, get_bread,
                                compute_local_roots_SMF2_scalar_valued,
                                names_and_urls)
from LfunctionComp import isogeny_class_cm

from LfunctionDatabase import get_lfunction_by_Lhash, get_instances_by_Lhash, get_instances_by_trace_hash, get_lfunction_by_url, get_instance_by_url, getHmfData, getHgmData, getEllipticCurveData
from Lfunction_base import Lfunction

from lmfdb.db_backend import db
from lmfdb.lfunctions import logger
from lmfdb.utils import web_latex, round_to_half_int, round_CBF_to_half_int, display_complex, str_to_CBF

from sage.all import ZZ, QQ, RR, CC, Integer, Rational, Reals, nth_prime, is_prime, factor,  log, real,  I, gcd, sqrt, prod, ceil,  EllipticCurve, NumberField, RealNumber, PowerSeriesRing, CDF, latex, CBF, RBF, RIF, primes_first_n, next_prime
import sage.libs.lcalc.lcalc_Lfunction as lc

from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.WebNumberField import WebNumberField
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_classes import WebMaassForm
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.siegel_modular_forms.sample import Sample
from lmfdb.artin_representations.math_classes import ArtinRepresentation
import lmfdb.hypergm.hodge
from lmfdb.downloader import Downloader

def validate_required_args(errmsg, args, *keys):
    missing_keys = [key for key in keys if not key in args]
    if len(missing_keys):
        raise KeyError(errmsg, "Missing required parameters: %s." % ','.join(missing_keys))

def validate_integer_args(errmsg, args, *keys):
    for key in keys:
        if key in args:
            if not isinstance(args[key],int) and not re.match('^\d+$',args[key].strip()):
                raise ValueError(errmsg, "Unable to convert parameter '%s' with value '%s' to a nonnegative integer." % (key, args[key]))

def constructor_logger(object, args):
    ''' Executed when a object is constructed for debugging reasons
    '''
    logger.debug(str(object.__class__) + str(args))

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
    L.Lhash = data.get('Lhash');
    L.algebraic = data.get('algebraic')
    L.degree = data.get('degree')
    L.level = int(data.get('conductor'))
    L.level_factored = factor(L.level)

    central_character = data.get('central_character')
    L.charactermodulus, L.characternumber = map(int, central_character.split("."))
    L.primitive = data.get('primitive', None)
    L.selfdual = data.get('self_dual', None)
    if data.get('root_number', None) is not None:
        # we first need to convert from unicode to a regular strin
        L.sign = str_to_CBF(data['root_number'])
    else:
        # this is a numeric converted to LMFDB_RealLiteral
        L.sign = 2*RBF(str(data.get('sign_arg'))).exppii()
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
        # this is a numeric convered to RealLiteral
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
        central_value =  CDF(str(L.leading_term))
    else:
        # we use the plot_values
        if L.selfdual:
            central_value = CDF(data['plot_values'][0])
        else:
            central_value = data['plot_values'][0]/sqrt(L.sign)
        # we should avoid displaying 10 digits as usual, as this is just a hack
        central_value = display_complex(central_value.real(), central_value.imag(),6)
    central_value = [0.5 + 0.5*L.motivic_weight, central_value]
    if 'values' not in data:
        L.values = [ central_value ]
    else:
        #  convert to string in case it is in unicode string
        L.values = [ [float(x), CDF(str(xval))] for x, xval in data['values']] + [ central_value ]


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
    if L.coefficient_field == "CDF":
        # convert pairs of doubles to CDF
        pairtoCDF = lambda x: CDF(tuple(x))
        pairtoCDF = lambda x: CDF(*tuple(x))
        L.localfactors = map(lambda x: map(pairtoCDF, x), L.localfactors)
        L.bad_lfactors = [ [p, map(pairtoCDF, elt)] for p, elt in L.bad_lfactors]


    # Note: a better name would be L.dirichlet_coefficients_analytic, but that
    # would require more global changes.
    if data.get('dirichlet_coefficients', None) is not None:
        L.dirichlet_coefficients_arithmetic = data['dirichlet_coefficients']
    elif data.get('euler_factors', None) is not None:
        # ask for more, in case many are zero
        L.dirichlet_coefficients_arithmetic = an_from_data(L.localfactors, 2*L.degree*L.numcoeff)

        # get rid of extra coeff
        count = 0;
        for i, elt in enumerate(L.dirichlet_coefficients_arithmetic):
            if elt != 0:
                count += 1;
                if count > L.numcoeff:
                    L.dirichlet_coefficients_arithmetic = \
                        L.dirichlet_coefficients_arithmetic[:i];
                    break;
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
    L.positive_zeros_raw = map(str, data['positive_zeros'])
    L.accuracy = data.get('accuracy', None);

    def convert_zeros(accuracy, list_zeros):
        two_power = 2 ** L.accuracy;
        # the zeros were stored with .str(truncate = false)
        # we recover all the bits
        int_zeros = [ (RealNumber(elt) * two_power).round() for elt in list_zeros];
        # we convert them back to floats and we want to display their truncated version
        return [ (RealNumber(elt.str() + ".")/two_power).str(truncate = True) for elt in int_zeros]

    if L.accuracy is not None:
        L.positive_zeros_raw = convert_zeros(L.accuracy, L.positive_zeros_raw)
    L.positive_zeros = L.positive_zeros_raw[:zero_truncation]

    if L.selfdual:
        L.negative_zeros_raw = L.positive_zeros_raw[:]
        L.dual_accuracy = L.accuracy
    else:
        dual_L_label = data['conjugate']
        dual_L_data = get_lfunction_by_Lhash(dual_L_label)
        L.dual_link = '/L/' + dual_L_data['origin']
        L.dual_accuracy = dual_L_data.get('accuracy', None);
        L.negative_zeros_raw = map(str, dual_L_data['positive_zeros'])
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
    """ Converts the dirichlet L-function coefficients and euler factors from
        the format in the database to algebraic and analytic form
    """

    def convert_coefficient(an, base_power_int):
        """
        this is only meant for dirichlet L-functions, and
        converts the format in the database to algebraic and analytic form
        """

        if not str(an).startswith('a'):
            return an, an
        else:
            an_power = an[2:]
            an_power_int = int(an_power)
            this_gcd = gcd(an_power_int,base_power_int)
            an_power_int /= this_gcd
            this_base_power_int = base_power_int/this_gcd
            if an_power_int == 0:
                return 1, 1
            elif this_base_power_int == 2:
                return -1, -1
            elif this_base_power_int == 4:
                if an_power_int == 1:
                    return I, I
                else:
                    return -I, -I
            else:
                # an = e^(2 pi i an_power_int / this_base_power_int)
                arithmetic = " $e\\left(\\frac{" + str(an_power_int) + "}{" + str(this_base_power_int)  + "}\\right)$"
                #exp(2*pi*I*QQ(an_power_int)/ZZ(this_base_power_int)).n()
                analytic = (2*CBF(an_power_int)/this_base_power_int).exppii()
                # round half integers
                analytic = round_CBF_to_half_int(analytic)
                return arithmetic, analytic

    base_power_int = int(coeff_info[0][2:-3])
    for n, an in enumerate(L.dirichlet_coefficients_arithmetic):
        L.dirichlet_coefficients_arithmetic[n] , L.dirichlet_coefficients[n] =  convert_coefficient(an, base_power_int)



    convert_euler_Lpoly = lambda poly_coeffs: map(lambda c: convert_coefficient(c, base_power_int)[1], poly_coeffs)
    L.bad_lfactors = [ [p, convert_euler_Lpoly(poly)] for p, poly in L.bad_lfactors]
    L.localfactors = map(convert_euler_Lpoly, L.localfactors)
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

class RiemannZeta(Lfunction):
    """Class representing the Riemann zeta fucntion

    Possible parameters: numcoeff  (the number of coefficients when computing)
    """

    def __init__(self, **args):
        constructor_logger(self, args)

        self._Ltype = "riemann"

        # Initialize default values
        self.numcoeff = 30  # set default to 30 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.numcoeff = int(self.numcoeff)

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 1
        self.coefficient_period = 0
        self.poles = [0, 1]
        self.residues = [-1, 1]
        self.poles_L = [1]  # poles of L(s), used by createLcalcfile_ver2
        self.residues_L = [1]  # residues of L(s) createLcalcfile_ver2
        self.langlands = True
        self.primitive = True
        self.degree = 1
        self.quasidegree = 1
        self.level_factored = self.level = 1
        self.mu_fe = [0]
        self.nu_fe = []
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.algebraic = True
        self.motivic_weight = 0
        self.sign = 1
        self.selfdual = True
        self.dirichlet_coefficients = [1 for n in range(self.numcoeff)]
        self.label = "zeta"

        # Specific properties
        self.is_zeta = True

        # Text for the web page
        self.texname = "\\zeta(s)"
        self.texnamecompleteds = "\\xi(s)"
        self.texnamecompleted1ms = "\\xi(1-s)"
        self.credit = 'Sage'

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "riemann"
        self.info['title'] = "Riemann Zeta-function: $\\zeta(s)$"

        # Generate a function to do computations
        self.sageLfunction = lc.Lfunction_Zeta()

#############################################################################


class Lfunction_Dirichlet(Lfunction):
    """Class representing the L-function of a Dirichlet character

    Compulsory parameters: charactermodulus
                           characternumber
    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        validate_required_args ('Unable to construct Dirichlet L-function.',
                                args, 'charactermodulus', 'characternumber')
        validate_integer_args ('Unable to construct Dirichlet L-function.',
                               args, 'charactermodulus', 'characternumber')

        self._Ltype = "dirichlet"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.numcoeff = 30

        # Check that the arguments give a primitive Dirichlet character in the database
        self.charactermodulus = int(self.charactermodulus)
        self.characternumber = int(self.characternumber)
        if self.charactermodulus > 10**20: # avoid trying to factor anything really big
            raise ValueError('Unable to construct Dirichlet L-function.',
                             'The specified modulus %d is too large.'%self.charactermodulus)
        if self.characternumber > self.charactermodulus:
            raise ValueError('Unable to construct Dirichlet L-function.',
                             'The Conrey index %d should not exceed the modulus %d.'%(self.characternumber,self.charactermodulus))
        if gcd(self.charactermodulus,self.characternumber) != 1:
            raise ValueError('Unable to construct Dirichlet L-function.',
                             'The specified Conrey index %d is not coprime to the modulus %d.'%(self.characternumber,self.charactermodulus))
        # Use ConreyCharacter to check primitivity (it can handle a huge modulus
        if not ConreyCharacter(self.charactermodulus,self.characternumber).is_primitive():
            raise ValueError('Unable to construct Dirichlet L-function,',
                             'The Dirichlet character $\chi_{%d}(%d,\cdot)$ is imprimitive; only primitive characters have L-functions).'%(self.charactermodulus,self.characternumber))

        # Load data from the database
        self.label = str(self.charactermodulus) + "." + str(self.characternumber)
        Lhash = "dirichlet_L_{0}.{1}".format(self.charactermodulus,
                                                self.characternumber)
        try:
            self.lfunc_data = get_lfunction_by_Lhash(Lhash)
        except:
            raise KeyError('No L-function data for the Dirichlet character $\chi_{%d}(%d,\cdot)$ found in the database.'%(self.charactermodulus,self.characternumber))

        # Extract the data
        makeLfromdata(self)
        self.fromDB = True

       # Mandatory properties
        self.coefficient_period = self.charactermodulus
        if self.selfdual:
            self.coefficient_type = 2
            for n in range(0, self.numcoeff - 1):
                self.dirichlet_coefficients[n] = int(round(real(self.dirichlet_coefficients[n])))
        else:
            self.coefficient_type = 3
        self.poles = []
        self.residues = []
        self.langlands = True
        self.quasidegree = self.degree

        # Specific properties
        if not self.selfdual:  #TODO: This should be done on a general level
            modnumDual = self.lfunc_data['conjugate'].split('_')[2]
            numDual = modnumDual.split('.')[1]
            self.dual_link = "/L/Character/Dirichlet/%s/%s" % (self.level, numDual)

        # Text for the web page
        self.htmlname = "<em>L</em>(<em>s,&chi;</em>)"
        self.texname = "L(s,\\chi)"
        self.htmlname_arithmetic = "<em>L</em>(<em>&chi;,s</em>)"
        self.texname_arithmetic = "L(\\chi,s)"
        self.texnamecompleteds = "\\Lambda(s,\\chi)"
        self.texnamecompleteds_arithmetic = "\\Lambda(\\chi,s)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\chi)"
            self.texnamecompleted1ms_arithmetic = "\\Lambda(\\chi,1-s)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{\\chi})"
            self.texnamecompleted1ms_arithmetic = "\\Lambda(\overline{\\chi},1-s)"
        title_end = ("where $\\chi$ is the Dirichlet character with label "
                     + self.label)
        self.credit = 'Sage'

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "character.dirichlet"
        self.info['title'] = "$" + self.texname + "$" + ", " + title_end
        self.info['title_arithmetic'] = ("$" + self.texname_arithmetic + "$" +
                                 ", " + title_end)
        self.info['title_analytic'] = "$" + self.texname + "$" + ", " + title_end


#############################################################################


class Lfunction_from_db(Lfunction):
    """
    Class representing a general L-function, to be retrieved from the database
    based on its lhash.

    Compulsory parameters: Lhash
    """
    def __init__(self, **kwargs):
        constructor_logger(self, kwargs)
        if 'Lhash' not in kwargs and 'url' not in kwargs:
            raise KeyError('Unable to construct L-function from Lhash or url',
                               'Missing required parameters: Lhash or url')
        self.numcoeff = 30

        self.__dict__.update(kwargs)
        if 'url' in kwargs and 'Lhash' not in kwargs:
            self.Lhash = self.get_Lhash_by_url(self.url)
        self.lfunc_data = get_lfunction_by_Lhash(self.Lhash)
        if 'url' not in kwargs:
            self.url = self.lfunc_data['origin']
        makeLfromdata(self)
        self.info = self.general_webpagedata()
        self._set_knowltype()
        self._set_title()
        self.credit = ''
        self.label = ''

    @property
    def _Ltype(self):
        return "general"

    @property
    def langlands(self):
        # this controls data on the Euler product, but is not stored
        # systematically in the database. Default to True until this
        # is retrievable from the database.
        return True
    @property
    def bread(self):
        return get_bread(self.degree)

    @property
    def origin_label(self):
        return self.Lhash

    @property
    def factors_origins(self):
        lfactors = []
        if "," in self.Lhash:
            for factor_Lhash in  self.Lhash.split(","):
                # a temporary fix while we don't replace the old Lhash (=trace_hash)
                elt = db.lfunc_lfunctions.lucky({'Lhash': factor_Lhash}, projection = ['trace_hash', 'degree'])
                trace_hash = elt.get('trace_hash',None)
                if trace_hash is not None:
                    instances = get_instances_by_trace_hash(elt['degree'], str(trace_hash))
                else:
                    instances = get_instances_by_Lhash(factor_Lhash)
                lfactors.extend(names_and_urls(instances))
        return lfactors

    def get_Lhash_by_url(self, url):
        instance = get_instance_by_url(url)
        if instance is None:
            raise KeyError('No L-function instance data for "%s" was found in the database.' % url)
        return instance['Lhash']


    @property
    def origins(self):
        lorigins = []
        instances = get_instances_by_Lhash(self.Lhash)
        # a temporary fix while we don't replace the old Lhash (=trace_hash)
        if self.trace_hash is not None:
            instances = get_instances_by_trace_hash(self.degree, str(self.trace_hash))
        lorigins = names_and_urls(instances)
        if not self.selfdual and hasattr(self, 'dual_link'):
            lorigins.append(("Dual L-function", self.dual_link))
        return lorigins

    @property
    def instances(self):
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

    @property
    def friends(self):
        return []

    @property
    def downloads(self):
        return [['Download Euler factors', self.download_euler_factor_url],
                ['Download zeros', self.download_zeros_url],
                ['Download Dirichlet coefficients', self.download_dirichlet_coeff_url]]

    @property
    def download_euler_factor_url(self):
        return request.path.replace('/L/', '/L/download_euler/')

    @property
    def download_zeros_url(self):
        return request.path.replace('/L/', '/L/download_zeros/')
    @property
    def download_dirichlet_coeff_url(self):
        return request.path.replace('/L/', '/L/download_dirichlet_coeff/')

    @property
    def download_url(self):
        return request.path.replace('/L/', '/L/download/')

    def download_euler_factors(self):
        filename = self.url.replace('/','_')
        data  = {}
        data['bad_lfactors'] = self.bad_lfactors
        ps = primes_first_n(len(self.localfactors))
        data['first_lfactors'] = [ [ps[i], l] for i, l in enumerate(self.localfactors)]
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.euler_factors',
                lang = 'text',
                title = 'Euler Factors of %s' % self.url)

    def download_zeros(self):
        filename = self.url.replace('/','_')
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
                title = 'Zeros of %s' % self.url)

    def download_dirichlet_coeff(self):
        filename = self.url.replace('/','_')
        data  = {}
        data['an'] = an_from_data(self.localfactors, next_prime(nth_prime(len(self.localfactors)+1)) - 1)
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.dir_coeffs',
                lang = 'text',
                title = 'Dirichlet coefficients of %s' % self.url)


    def download(self):
        filename = self.url.replace('/','_')
        data  = dict(self.__dict__)
        for k in ['level_factored', 'dirichlet_coefficients']:
            if isinstance(data[k], list):
                data[k] = map(str, data[k])
            else:
                data[k] = str(data[k])
        data.pop('level_factored')
        return Downloader()._wrap(
                Json.dumps(data),
                filename + '.lfunction',
                lang = 'text',
                title = 'The L-function object of %s' % self.url)




    @property
    def chilatex(self):
        try:
            if int(self.characternumber) != 1:
                return "character $\chi_{%s} (%s, \cdot)$" % (self.charactermodulus, self.characternumber)
            else:
                return "trivial character"
        except KeyError:
            return None


    def _set_title(self):
        '''
        If `charactermodulus` and `characternumber` are defined, make a title
        which includes the character. Otherwise, make a title without character.
        '''
        if len(str(self.level)) < sum([len(str(elt)) + min(2, k) for elt, k in self.level_factored]):
            conductor_str = "$%s$" % self.level
        else:
            conductor_str = "$%s$" % latex(self.level_factored)

        if self.chilatex is not None:
            title_end = (
                    " of degree {degree}, motivic weight {weight},"
                    " conductor {conductor}, and {character}"
                    ).format(degree=self.degree, weight=self.motivic_weight,
                            conductor=conductor_str, character=self.chilatex)
        else:
            title_end = (
                    " of degree {degree}, motivic weight {weight},"
                    " and conductor {conductor}"
                    ).format(degree=self.degree, weight=self.motivic_weight,
                            conductor=conductor_str)
        self.info['title'] = "$" + self.texname + "$" + ", " + title_end
        self.info['title_arithmetic'] = ("L-function" + title_end)
        self.info['title_analytic'] = ("L-function" + title_end)
        return

    @property
    def htmlname(self):
        return "<em>L</em>(<em>s</em>)"

    @property
    def htmlname_arithmetic(self):
        return self.htmlname

    @property
    def texname(self):
        return "L(s)"

    @property
    def texname_arithmetic(self):
        return self.texname

    @property
    def texnamecompleted1ms(self):
        if self.selfdual:
            return "\\Lambda(1-s)"
        else:
            return "\\overline{\\Lambda}(1-s)"
    @property
    def texnamecompleted1ms_arithmetic(self):
        if self.selfdual:
            return "\\Lambda(%d-s)" % (self.motivic_weight + 1)
        else:
            return "\\overline{\\Lambda}(%d-s)" % (self.motivic_weight + 1)

    @property
    def texnamecompleteds(self):
        return  "\\Lambda(s)"
    @property
    def texnamecompleteds_arithmetic(self):
        return self.texnamecompleteds

    #def _retrieve_lfunc_data_from_db(self):
    #    self.lfunc_data = get_lfunction_by_url(self.url)
    #    if not self.lfunc_data:
    #        raise KeyError('No L-function instance data for "%s" was found in the database.' % self.url)
    #    return

    @property
    def knowltype(self):
        return None

    def _set_knowltype(self):
        if self.knowltype is not None:
            self.info['knowltype'] = self.knowltype





####################################################################################################

class Lfunction_CMF(Lfunction_from_db):
    """Class representing an classical modular form L-function

    Compulsory parameters: weight
                           level
                           character
                           hecke_orbit
                           number
    """

    def __init__(self, **kwargs):
        constructor_logger(self, kwargs)
        validate_required_args('Unable to construct classical modular form L-function.',
                               kwargs, 'weight','level','character','hecke_orbit','number')
        validate_integer_args('Unable to construct classical modular form L-function.',
                              kwargs, 'weight','level','character','number')
        for key in ['weight','level','character','number']:
            kwargs[key] = int(kwargs[key])
        # self.level is the conductor
        self.modform_level = kwargs['level']
        self.kwargs = kwargs
        # Put the arguments in the object dictionary
        self.__dict__.update(kwargs)
        self.label_args = (self.modform_level, self.weight, self.char_orbit_label, self.hecke_orbit, self.character, self.number)
        self.url = "ModularForm/GL2/Q/holomorphic/%d/%d/%s/%s/%d/%d" % self.label_args
        Lfunction_from_db.__init__(self, url = self.url)

        self.numcoeff = 30

    @property
    def _Ltype(self):
        return  "classical modular form"

    @property
    def origin_label(self):
        return ".".join(map(str, self.label_args))

    @property
    def bread(self):
        return get_bread(2, [('Cusp Form', url_for('.l_function_cuspform_browse_page', degree='degree2'))])

#    def _set_title(self):
#        title = "L-function of a homomorphic cusp form of weight %s, level %s, and %s" % (
#            self.weight, self.level, self.chilatex)
#
#        self.info['title'] = self.info['title_analytic'] = self.info['title_arithmetic'] = title
#

#############################################################################

class Lfunction_CMF_orbit(Lfunction_from_db):
    """Class representing an classical modular form L-function

    Compulsory parameters: weight
                           level
                           char_orbit_label
                           hecke_orbit
    """

    def __init__(self, **kwargs):
        constructor_logger(self, kwargs)
        validate_required_args('Unable to construct classical modular form L-function.',
                               kwargs, 'weight','level','char_orbit_label','hecke_orbit')
        validate_integer_args('Unable to construct classical modular form L-function.',
                              kwargs, 'weight','level')
        for key in ['weight','level']:
            kwargs[key] = int(kwargs[key])
        # self.level is the conductor
        self.modform_level = kwargs['level']
        self.kwargs = kwargs
        # Put the arguments in the object dictionary
        self.__dict__.update(kwargs)
        self.label_args = (self.modform_level, self.weight, self.char_orbit_label, self.hecke_orbit)
        self.url = "ModularForm/GL2/Q/holomorphic/%d/%d/%s/%s" % self.label_args
        self.Lhash = self.get_Lhash_by_url(self.url)
        Lfunction_from_db.__init__(self, Lhash = self.Lhash)

        self.numcoeff = 30

    @property
    def _Ltype(self):
        return  "classical modular form orbit"

    @property
    def origin_label(self):
        return ".".join(map(str, self.label_args))

    @property
    def bread(self):
        return get_bread(self.degree, [('Cusp Form', url_for('.l_function_cuspform_browse_page', degree='degree' + str(self.degree)))])

#    def _set_title(self):
#        conductor_str = "$ %s $" % latex(self.modform_level)
#        title = "L-function of a Hecke orbit of a homomorphic cusp form of weight %s and level %s" % (
#            self.weight, conductor_str)
#
#        self.info['title'] = self.info['title_analytic'] = self.info['title_arithmetic'] = title
#
#################################################################################################


class Lfunction_EC(Lfunction_from_db):
    """
    Class representing an elliptic curve L-function
    over a number field, possibly QQ.
    It should be called with a dictionary of the forms:

    dict = { 'field_label': <field_label>, 'conductor_label': <conductor_label>,
             'isogeny_class_label': <isogeny_class_label> }
    """
    def __init__(self, **kwargs):
        constructor_logger(self, kwargs)
        validate_required_args('Unable to construct elliptic curve L-function.',
                               kwargs, 'field_label', 'conductor_label',
                               'isogeny_class_label')

        # Put the arguments into the object dictionary
        self.__dict__.update(kwargs)

        # Set field, conductor, isogeny information from labels
        self._parse_labels()

        self.url = "EllipticCurve/%s/%s/%s" % (self.field,
                                                        self.conductor_label,
                                                        self.isogeny_class_label)
        Lfunction_from_db.__init__(self, url = self.url)

        self.numcoeff = 30

    @property
    def _Ltype(self):
        return "ellipticcurve"

    @property
    def base_field(self):
        """base_field of the EC"""
        return self.field_label


    def _parse_labels(self):
        """Set field, conductor, isogeny information from labels."""
        (self.field_degree,
            self.field_real_signature,
            self.field_absdisc,
            self.field_index)  = map(int, self.field_label.split("."))
        #field_signature = [self.field_real_signature,
        #        (self.field_degree - self.field_real_signature) // 2]
        # number of actual Gamma functions
        #self.quasidegree = sum( field_signature )
        #self.ec_conductor_norm  = int(self.conductor_label.split(".")[0])
        #self.conductor = self.ec_conductor_norm * (self.field_absdisc ** self.field_degree)
        self.long_isogeny_class_label = self.conductor_label + '.' + self.isogeny_class_label
        return

    @property
    def bread(self):
        """breadcrumbs for webpage"""
        if self.base_field == '1.1.1.1': #i.e. QQ
            lbread = get_bread(2,
                    [
                      ('Elliptic Curve', url_for('.l_function_ec_browse_page')),
                    ])
        else:
            lbread = get_bread(self.degree, [])
        return lbread


    @property
    def field(self):
        return "Q" if self.field_degree == 1 else self.field_label

    @property
    def friends(self):
        """The 'friends' to show on webpage."""
        lfriends = []
        if self.base_field == '1.1.1.1': #i.e. QQ
            # only show symmetric powers for non-CM curves
            if not isogeny_class_cm(self.origin_label):
                lfriends.append(('Symmetric square L-function',
                                url_for(".l_function_ec_sym_page_label",
                                    power='2', label=self.origin_label)))
                lfriends.append(('Symmetric cube L-function',
                                url_for(".l_function_ec_sym_page_label",
                                    power='3', label=self.origin_label)))
        return lfriends


    @property
    def origin_label(self):
        if self.field_degree == 1:
            llabel = self.long_isogeny_class_label
        else:
            llabel = self.field_label + "-" + self.long_isogeny_class_label
        return llabel
    @property
    def knowltype(self):
        if self.field_degree == 1:
            return "ec.q"
        else:
            return "ec.nf"

#############################################################################

class Lfunction_genus2_Q(Lfunction_from_db):
    """Class representing the L-function of a genus 2 curve over Q

    Compulsory parameters: label

    """

    def __init__(self, **args):
        # Check for compulsory arguments
        validate_required_args('Unabel to construct L-function of genus 2 curve.',
                               args, 'label')

        # Put the arguments into the object dictionary
        self.__dict__.update(args)

        # Load data from the database
        self.url = "Genus2Curve/Q/" + self.label.replace(".","/")
        self.isogeny_class_label = self.label
        Lfunction_from_db.__init__(self, url = self.url)
        self.numcoeff = 30

    @property
    def origin_label(self):
        return  self.isogeny_class_label

    @property
    def _Ltype(self):
        return "genus2curveQ"

    @property
    def knowltype(self):
        return "g2c.q"

    @property
    def factors_origins(self):
        # this is just a hack, and the data should be replaced
        instances = []
        # either the factors are stored in the DB as products of EC
        for elt in db.lfunc_instances.search({'Lhash': self.Lhash, 'type':'ECQP'}, projection = 'url'):
            if '|' in elt:
                for url in elt.split('|'):
                    url = url.rstrip('/')
                    # Lhash = trace_hash
                    instances.extend(get_instances_by_trace_hash(2, db.lfunc_instances.lucky({'url': url}, 'Lhash')))
                break
        # or we need to use the trace_hash to find other factorizations
        if str(self.trace_hash) == self.Lhash:
            for elt in db.lfunc_lfunctions.search({'trace_hash': self.trace_hash, 'degree' : 4}, projection = 'Lhash'):
                if ',' in elt:
                    for factor_Lhash in  elt.split(","):
                        trace_hash = db.lfunc_lfunctions.lucky({'Lhash': factor_Lhash}, projection = 'trace_hash')
                        if trace_hash is not None:
                            instancesf = get_instances_by_trace_hash(str(trace_hash))
                        else:
                            instancesf = get_instances_by_Lhash(factor_Lhash)
                        instances.extend(instancesf)
        return names_and_urls(instances)

    #def _set_title(self):
    #    title = "L-function of the Jacobian of a genus 2 curve with label %s" %  (self.origin_label)
    #    self.info['title'] = self.info['title_analytic'] = self.info['title_arithmetic'] = title



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
            title_end = " on $%s$" % (self.group)

        else:   # Generate from Maass form

            # Create the Maass form
            self.mf = WebMaassForm(self.maass_id, get_dirichlet_c_only=1)
            self.group = 'GL2'

            # Extract the L-function information from the Maass form object
            self.symmetry = self.mf.symmetry
            self.level = int(self.mf.level)
            self.level_factored = factor(self.level)
            self.charactermodulus = self.level
            self.weight = int(self.mf.weight)
            self.characternumber = int(self.mf.character)
            if self.level > 1:
                try:
                    self.fricke = self.mf.fricke()
                except:
                    raise KeyError('No Fricke information available for '
                                   + 'Maass form so not able to compute '
                                   + 'the L-function. ')
            else:  # no fricke for level 1
                self.fricke = 1
            if self.symmetry == "odd" or self.symmetry == 1:
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
            self.eigenvalue = self.mf.R if self.mf.R else 0
            self.mu_fe = [aa + self.eigenvalue * I, aa - self.eigenvalue * I]
            self.nu_fe = []
            self.compute_kappa_lambda_Q_from_mu_nu()
            self.algebraic = False
            # Todo: If self has dimension >1, link to specific L-functions
            self.dirichlet_coefficients = self.mf.coeffs
            if 0 in self.dirichlet_coefficients and self.dirichlet_coefficients[0] == 0:
                self.dirichlet_coefficients.pop(0)
            self.checkselfdual()
            self.credit = self.mf.contributor_name if 'contributor_name' in dir(self.mf) else ''

            title_end = " and $R= %s$" % (self.eigenvalue)

            # Generate a function to do computations
            minNumberOfCoefficients = 100     # TODO: Fix this to take level into account
            if len(self.dirichlet_coefficients) >= minNumberOfCoefficients:
                generateSageLfunction(self)
            else:
                self.sageLfunction = None

        # Text for the web page
        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"

        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
        self.label = self.maass_id

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "mf.maass"
        self.info['title'] = ("$L(s,f)$, where $f$ is a Maass cusp form with "
                      + "level %s" % (self.level)) + title_end

#############################################################################


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
        self.label = args['label']
        self.number = int(args['number'])
        self.character= int(args['character'])
        if self.character != 0:
            raise KeyError('L-function of Hilbert form of non-trivial character not implemented yet.')

        # Load form (f) from database
        (f, F_hmf) = getHmfData(self.label)
        if f is None:
            # NB raising an error is not a good way to handle this on website!
            raise KeyError('No Hilbert modular form with label "%s" found in database.'%self.label)
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
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
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
        self.texnamecompleteds = "\\Lambda(s,F)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,F)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{F})"
        self.credit = ''

        # Generate a function to do computations
        generateSageLfunction(self)
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "mf.siegel"
        self.info['title'] = ("$L(s,F)$, " + "Where $F$ is a Scalar-valued Siegel " +
                      "Modular Form of Weight " + str(self.weight) + ".")

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

        # Fetch the polynomial of the field from the database
        wnf = WebNumberField(self.label)
        if not wnf or wnf.is_null():
            raise KeyError('Unable to construct Dedekind zeta function.', 'No data for the number field "%s" was found in the database'%self.label)
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
                # cond = wnf.conductor()
                dir_group = wnf.dirichlet_group()
                # Remove 1 from the list
                j = 0
                while dir_group[j] != 1:
                    j += 1
                dir_group.pop(j)
                self.factorization = (r'\(\zeta_K(s) =\) ' +
                                      '<a href="/L/Riemann/">\(\zeta(s)\)</a>')
                fullchargroup = wnf.full_dirichlet_group()
                for j in dir_group:
                    chij = fullchargroup[j]
                    mycond = chij.conductor()
                    myj = j % mycond
                    self.factorization += (r'\(\;\cdot\) <a href="/L/Character/Dirichlet/%d/%d/">\(L(s,\chi_{%d}(%d, \cdot))\)</a>'
                                           % (mycond, myj, mycond, myj))
            elif len(wnf.factor_perm_repn())>0:
                nfgg = wnf.factor_perm_repn() # first call cached it
                ar = wnf.artin_reps() # these are in the same order
                self.factorization = (r'\(\zeta_K(s) =\) <a href="/L/Riemann/">'
                                           +'\(\zeta(s)\)</a>')
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
        self.texname = "\\zeta_K(s)"
        self.texnamecompleteds = "\\Lambda_K(s)"
        self.texnamecompleted1ms = "\\Lambda_K(1-s)"
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
        self.info['label'] = self.label
        self.info['title'] = "Dedekind zeta-function: $\\zeta_K(s)$, where $K$ is the number field with defining polynomial %s" %  web_latex(self.NF.defining_polynomial())

    def original_object(self):
        return self.NF


#############################################################################

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
        self.label = args["label"]

        # Create the Artin representation
        try:
            self.artin = ArtinRepresentation(self.label)
        except Exception as err:
            raise KeyError('Error constructing Artin representation %s.'%self.label, *err.args)

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
        self.texname = "L(s,\\rho)"
        self.texnamecompleteds = "\\Lambda(s)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s)"
        else:
            self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"
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
        self.info['title'] = ("L-function for Artin representation " + str(self.label))

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
        self.label = args["label"]

        # Get the motive from the database
        self.motive = getHgmData(self.label)
        if not self.motive:
            raise KeyError('No data for the hypergeometric motive "%s" was found in the database.'%self.label)

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
        except:
            self.arith_coeffs = map(Integer, self.motive["coeffs_string"])
        self.dirichlet_coefficients = [Reals()(Integer(x))/Reals()(n+1)**(self.motivic_weight/2.)
                                       for n, x in enumerate(self.arith_coeffs)]
        self.sign = self.motive["sign"]
        self.selfdual = True

        # Text for the web page
        self.texname = "L(s)"
        self.texnamecompleteds = "\\Lambda(s)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s)"
        else:
            self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"
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
        self.info['title'] = ("L-function for the hypergeometric motive with label "+self.label)

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
        self.label = str(self.conductor) + '.' + self.isogeny
        if self.underlying_type != 'EllipticCurve' or self.field != 'Q':
            raise TypeError("The symmetric L-functions have been implemented " +
                            "only for Elliptic Curves over Q.")

        # Create the elliptic curve
        Edata = getEllipticCurveData(self.label + '1')
        if Edata is None:
            raise KeyError('No elliptic curve with label %s exists in the database' % self.label)
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
        pairs_fe = zip(self.kappa_fe, self.lambda_fe)
        self.mu_fe = [lambda_fe*2. for kappa_fe, lambda_fe in pairs_fe if abs(kappa_fe - 0.5) < 0.001]
        self.nu_fe = [lambda_fe for kappa_fe, lambda_fe in pairs_fe if abs(kappa_fe - 1) < 0.001]
        self.quasidegree = len(self.mu_fe) + len(self.nu_fe)
        self.algebraic = True
        self.motivic_weight = self.m
        self.dirichlet_coefficients = self.S._coeffs
        self.sign = self.S.root_number
        self.selfdual = True

        # Text for the web page
        self.texname = "L(s, E, \mathrm{sym}^{%d})" % self.m
        self.texnamecompleteds = "\\Lambda(s,E,\mathrm{sym}^{%d})" % self.S.m
        self.texnamecompleted1ms = ("\\Lambda(1-{s}, E,\mathrm{sym}^{%d})"
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

        self.info['title'] = ("The Symmetric %s $L$-function $L(s,E,\mathrm{sym}^{%d})$ of Elliptic Curve Isogeny Class %s"
                      % (ordinal(self.m), self.m, self.label))


    def original_object(self):
        return self.S


#############################################################################

# This class it not used anywhere and has not been touched since January 2014.  The key function TensorProduct is not defined anywhere, so it won't work
# There is closely related code in lmfdb/tensor_products that perhaps is meant to supersed this?
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

        self.texname = "L(s,E,\\chi)"
        self.texnamecompleteds = "\\Lambda(s,E,\\chi)"
        self.title = "$L(s,E,\\chi)$, where $E$ is the elliptic curve %s and $\\chi$ is the Dirichlet character of conductor %s, modulo %s, number %s"%(self.ellipticcurvelabel, self.tp.chi.conductor(), self.charactermodulus, self.characternumber)

        self.credit = 'Workshop in Besancon, 2014'

        generateSageLfunction(self)

        constructor_logger(self, args)

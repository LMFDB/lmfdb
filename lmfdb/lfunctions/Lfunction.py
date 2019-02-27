# -*- coding: utf-8 -*-
# The class Lfunction is defined in Lfunction_base and represents an L-function
# We subclass it here:
# RiemannZeta, Lfunction_Dirichlet, Lfunction_EC_Q, Lfunction_EMF,
# Lfunction_HMF, Lfunction_Maass, Lfunction_SMF2_scalar_valued,
# DedekindZeta, ArtinLfunction, SymmetricPowerLfunction,
# Lfunction_genus2_Q

import math
import re

from flask import url_for

from Lfunctionutilities import (p2sage, string2number, get_bread,
                                compute_local_roots_SMF2_scalar_valued,
                                signOfEmfLfunction,
                                name_and_object_from_url)
from LfunctionComp import EC_from_modform, isogeny_class_cm

from LfunctionDatabase import get_lfunction_by_Lhash, get_instances_by_Lhash, get_lfunction_by_url, getHmfData, getHgmData, getEllipticCurveData
import LfunctionLcalc
from Lfunction_base import Lfunction
from lmfdb.lfunctions import logger
from lmfdb.utils import web_latex

import sage
from sage.all import ZZ, QQ, RR, CC, Integer, Rational, Reals, nth_prime, is_prime, factor, exp, log, real, pi, I, gcd, sqrt, prod, ceil, NaN, EllipticCurve, NumberField, RealNumber
import sage.libs.lcalc.lcalc_Lfunction as lc

from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.WebNumberField import WebNumberField
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_classes import WebMaassForm
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.siegel_modular_forms.sample import Sample
from lmfdb.artin_representations.math_classes import ArtinRepresentation
import lmfdb.hypergm.hodge

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
    PP = sage.rings.all.PowerSeriesRing(sage.rings.all.RationalField(), 'x', Integer(upperbound).nbits())
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
    L.Lhash = data['Lhash'];
    L.algebraic = data['algebraic']
    L.degree = data['degree']
    L.level = data['conductor']
    central_character = data['central_character']
    L.charactermodulus, L.characternumber = central_character.split(".")
    L.charactermodulus = int(L.charactermodulus)
    L.characternumber = int(L.characternumber)
    L.primitive = data['primitive']
    L.selfdual = data['self_dual']
    if 'root_number' in data:
        L.sign = string2number(data['root_number'])
    else:
        L.sign = exp(2*pi*I*float(data['sign_arg'])).n()
    L.st_group = data['st_group']
    L.order_of_vanishing = data['order_of_vanishing']

    L.mu_fe = []
    for i in range(0,len(data['gamma_factors'][0])):
        L.mu_fe.append(string2number(data['analytic_normalization']) +
                       string2number(data['gamma_factors'][0][i]))

    L.nu_fe = []
    for i in range(0,len(data['gamma_factors'][1])):
        L.nu_fe.append(string2number(data['analytic_normalization']) +
                       string2number(data['gamma_factors'][1][i]))
    L.compute_kappa_lambda_Q_from_mu_nu()

    # Optional properties
    if 'motivic_weight' in data:
        L.motivic_weight = data['motivic_weight']
    else:
        L.motivic_weight = ''

    if hasattr(L, 'base_field'):
        field_degree = int(L.base_field().split('.')[0])
        L.st_link = st_link_by_name(L.motivic_weight, L.degree // field_degree, L.st_group)
    else:
        #this assumes that the base field of the Galois representation is QQ
        L.st_link = st_link_by_name(L.motivic_weight, L.degree, L.st_group)
    # Convert L.motivic_weight from python 'int' type to sage integer type.
    # This is necessary because later we need to do L.motivic_weight/2
    # when we write Gamma-factors in the arithmetic normalization.
    L.motivic_weight = ZZ(data['motivic_weight'])
    if 'credit' in data.keys():
        L.credit = data['credit']

    # Dirichlet coefficients
    if 'dirichlet_coefficients' in data:
        L.dirichlet_coefficients_arithmetic = data['dirichlet_coefficients']
    else:
        # ask for more, in case many are zero
        L.dirichlet_coefficients_arithmetic = an_from_data(p2sage(
            data['euler_factors']), 2*L.degree*L.numcoeff)

        # get rid of extra coeff
        count = 0;
        for i, elt in enumerate(L.dirichlet_coefficients_arithmetic):
            if elt != 0:
                count += 1;
                if count > L.numcoeff:
                    L.dirichlet_coefficients_arithmetic = \
                        L.dirichlet_coefficients_arithmetic[:i];
                    break;

    L.dirichlet_coefficients = L.dirichlet_coefficients_arithmetic[:]
    L.normalize_by = string2number(data['analytic_normalization'])
    for n in range(0, len(L.dirichlet_coefficients_arithmetic)):
        an = L.dirichlet_coefficients_arithmetic[n]
        if L.normalize_by > 0:
            L.dirichlet_coefficients[n] = float(an/(n+1)**L.normalize_by)
        else:
            L.dirichlet_coefficients[n] = an

    if 'coeff_info' in data:   # hack, works only for Dirichlet L-functions
        convert_dirichlet_Lfunction_coefficients(L, data['coeff_info'])

    L.localfactors = p2sage(data['euler_factors'])
    # Currently the database stores the bad_lfactors as a list and the euler_factors
    # as a string.  Those should be the same.  Once that change is made, either the
    # line above or the line below will break.  (DF and SK, Aug 4, 2015)
    L.bad_lfactors = data['bad_lfactors']

    # Configure the data for the zeros
    if 'accuracy' in data:
        L.accuracy = data['accuracy'];
    else:
        L.accuracy = None

    zero_truncation = 25   # show at most 25 positive and negative zeros
                           # later: implement "show more"
    L.positive_zeros = map(str, data['positive_zeros'][:zero_truncation])

    if L.accuracy is not None:
        two_power = 2 ** L.accuracy;
        # the zeros were stored with .str(truncate = false)
        # we recover all the bits
        int_zeros = [ (RealNumber(elt) * two_power).round() for elt in L.positive_zeros];
        # we convert them back to floats and we want to display their truncated version
        L.positive_zeros = [ (RealNumber(elt.str() + ".")/two_power).str(truncate = True) for elt in int_zeros]

    if L.selfdual:
        L.negative_zeros = ["&minus;" + pos_zero for pos_zero in L.positive_zeros]
    else:
        dual_L_label = data['conjugate']
        dual_L_data = get_lfunction_by_Lhash(dual_L_label)
        L.negative_zeros = ["&minus;" + str(pos_zero) for pos_zero in
                            dual_L_data['positive_zeros']]
        L.negative_zeros = L.negative_zeros[:zero_truncation]

    L.negative_zeros.reverse()
    L.negative_zeros += ['0' for _ in range(data['order_of_vanishing'])]
    L.negative_zeros = ", ".join(L.negative_zeros)
    L.positive_zeros = ", ".join(L.positive_zeros)
    if len(L.positive_zeros) > 2 and len(L.negative_zeros) > 2:  # Add comma and empty space between negative and positive
        L.negative_zeros = L.negative_zeros + ", "

    # Configure the data for the plot
    pos_plot = [[j * string2number(data['plot_delta']),
                 string2number(data['plot_values'][j])]
                          for j in range(len(data['plot_values']))]
    if L.selfdual:
        neg_plot = [ [-1*pt[0], string2number(data['root_number']) * pt[1]]
                     for pt in pos_plot ][1:]
    else:
        neg_plot = [[-j * string2number(dual_L_data['plot_delta']),
                 string2number(dual_L_data['plot_values'][j])]
                          for j in range(1,len(dual_L_data['plot_values']))]
    neg_plot.reverse()
    L.plotpoints = neg_plot[:] + pos_plot[:]

    L.fromDB = True




def convert_dirichlet_Lfunction_coefficients(L, coeff_info):
    """ Converts the dirichlet L-function coefficients from
        the format in the database to algebaric and analytic form
    """
    base_power_int = int(coeff_info[0][2:-3])
    L.dirichlet_coefficients_analytic = L.dirichlet_coefficients_arithmetic[:]
    for n in range(0, len(L.dirichlet_coefficients_arithmetic)):
        an = L.dirichlet_coefficients_arithmetic[n]
        if not str(an).startswith('a'):
            L.dirichlet_coefficients_arithmetic[n] = an
            L.dirichlet_coefficients_analytic[n] = an
        else:
            an_power = an[2:]
            an_power_int = int(an_power)
            this_gcd = gcd(an_power_int,base_power_int)
            an_power_int /= this_gcd
            this_base_power_int = base_power_int/this_gcd
            if an_power_int == 0:
                L.dirichlet_coefficients_arithmetic[n] = 1
                L.dirichlet_coefficients_analytic[n] = 1
            elif this_base_power_int == 2:
                L.dirichlet_coefficients_arithmetic[n] = -1
                L.dirichlet_coefficients_analytic[n] = -1
            elif this_base_power_int == 4:
                if an_power_int == 1:
                    L.dirichlet_coefficients_arithmetic[n] = I
                    L.dirichlet_coefficients_analytic[n] = I
                else:
                    L.dirichlet_coefficients_arithmetic[n] = -1*I
                    L.dirichlet_coefficients_analytic[n] = -1*I
            else:
                L.dirichlet_coefficients_arithmetic[n] = " $e\\left(\\frac{" + str(an_power_int) + "}{" + str(this_base_power_int)  + "}\\right)$"
                L.dirichlet_coefficients_analytic[n] = exp(2*pi*I*float(an_power_int)/float(this_base_power_int)).n()

    L.dirichlet_coefficients = L.dirichlet_coefficients_analytic[:]
    # Note: a better name would be L.dirichlet_coefficients_analytic, but that
    # would require more global changes.



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
        self.level = 1
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
        validate_required_args('Unable to construct L-function from lhash.',
                               kwargs, 'Lhash')
        self._Ltype = "general"
        self.numcoeff = 30

        # this controls data on the Euler product, but is not stored
        # systematically in the database. Default to False until this
        # is retrievable from the database.
        self.langlands = False

        self.__dict__.update(kwargs)
        self.lfunc_data = get_lfunction_by_Lhash(self.Lhash)
        makeLfromdata(self)
        self._set_web_displaynames()
        self.info = self.general_webpagedata()
        self._set_title()
        self.credit = ''
        self.label = ''

    @property
    def bread(self):
        return [('L-functions', url_for('.l_function_top_page'))]

    @property
    def factors(self):
        lfactors = []
        if "," in self.Lhash:
            for factor_Lhash in  self.Lhash.split(","):
                for instance in sorted(get_instances_by_Lhash(factor_Lhash),
                                       key=lambda elt: elt['url']):
                    url = instance['url']
                    name, obj_exists = name_and_object_from_url(url)
                    if obj_exists:
                        lfactors.append((name,  "/" + url))
                    else:
                        name += '&nbsp;  n/a';
                        lfactors.append((name, ""))
        return lfactors

    @property
    def instances(self):
        linstances = []
        for instance in sorted(get_instances_by_Lhash(self.Lhash),
                               key=lambda elt: elt['url']):
            url = instance['url']
            linstances.append((str(url), "/L/" + url))
        return linstances

    @property
    def origins(self):
        lorigins = []
        for instance in sorted(get_instances_by_Lhash(self.Lhash),
                               key=lambda elt: elt['url']):
            name, obj_exists = name_and_object_from_url(instance['url'])
            if not name:
                name = ''
            if obj_exists:
                lorigins.append((name, "/"+instance['url']))
            else:
                name += '&nbsp;  n/a';
                lorigins.append((name, ""))
        return lorigins

    @property
    def friends(self):
        return []

    def _set_title(self):
        '''
        If `charactermodulus` and `characternumber` are defined, make a title
        which includes the character. Otherwise, make a title without character.
        '''
        try:
            chilatex = ("$\chi_{" + str(self.charactermodulus) +
                        "} (" + str(self.characternumber) +", \cdot )$")
        except KeyError:
            chilatex = ''
        if chilatex:
            title_end = (
                    " of degree {degree}, weight {weight},"
                    " conductor {conductor}, and character {character}"
                    ).format(degree=self.degree, weight=self.motivic_weight,
                            conductor=self.level, character=chilatex)
        else:
            title_end = (
                    " of degree {degree}, weight {weight},"
                    " and conductor {conductor}"
                    ).format(degree=self.degree, weight=self.motivic_weight,
                            conductor=self.level)
        self.info['title_arithmetic'] = ("L-function" + title_end)
        self.info['title_analytic'] = ("L-function" + title_end)
        return

    def _set_web_displaynames(self):
        self.htmlname_arithmetic = "<em>L</em>(<em>s</em>)"
        self.texname = "L(s)"
        self.texname_arithmetic = "L(s)"
        self.texnamecompleted1ms = "\\Lambda(1-s)"
        self.texnamecompleteds_arithmetic = "\\Lambda(s)"
        self.texnamecompleted1ms_arithmetic = "\\Lambda(" + str(self.motivic_weight + 1) + "-s)"
        self.texnamecompleteds = "\\Lambda(s)"
        return


#############################################################################


class Lfunction_EC(Lfunction):
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
        self._Ltype = "ellipticcurve"
        self.numcoeff = 30

        # Put the arguments into the object dictionary
        self.__dict__.update(kwargs)

        # Set field, conductor, isogeny information from labels
        self._parse_labels()

        self._retrieve_lfunc_data_from_db()
        # Extract the data
        makeLfromdata(self)

        # Mandatory properties
        self.coefficient_period = 0
        self.coefficient_type = 2
        self.poles = []
        self.residues = []
        self.degree = self.field_degree * 2;
        self.langlands = self.is_langlands()

        self.initialize_webpage_data()

    def base_field(self):
        """base_field of the EC"""
        return self.field_label

    def ground_field(self):
        """Field of the Dirichlet coefficients"""
        return 'Q'

    def initialize_webpage_data(self):
        self._set_web_displaynames()
        self.info = self.general_webpagedata()
        self._set_title()
        self.credit = ''
        self._set_knowltype()
        return

    def is_langlands(self):
        if self.field_degree == 1 or \
                (self.field_degree == 2 and self.field_real_signature == 2):
            return True
        return False

    @property
    def bread(self):
        """breadcrumbs for webpage"""
        if self.base_field() == '1.1.1.1': #i.e. QQ
            lbread = get_bread(2,
                    [
                      ('Elliptic Curve', url_for('.l_function_ec_browse_page')),
                      (self.label, url_for('.l_function_ec_page',
                              conductor_label=self.conductor,
                              isogeny_class_label = self.isogeny_class_label))
                    ])
        else:
            lbread = get_bread(self.degree,
                [
                    # FIXME there is no .l_function_ecnf_browse_page
                    #('Elliptic Curve', url_for('.l_function_ec_browse_page')),
                    (self.label,
                     url_for('.l_function_ecnf_page',
                            field_label = self.field_label,
                            conductor_label = self.conductor_label,
                            isogeny_class_label = self.long_isogeny_class_label))
                ])
        return lbread

    @property
    def factors(self):
        """
        If L-function factors as a product of other L-functions, this is a list
        of those factors. Otherwise, this is an empty list.
        """
        lfactors = []
        if "," in self.Lhash:
            for factor_Lhash in  self.Lhash.split(","):
                for instance in sorted(get_instances_by_Lhash(factor_Lhash),
                                       key=lambda elt: elt['url']):
                    url = instance['url']
                    name, obj_exists = name_and_object_from_url(url)
                    if obj_exists:
                        lfactors.append((name,  "/" + url))
                    else:
                        name += '&nbsp;  n/a';
                        lfactors.append((name, ""))
        return lfactors

    @property
    def field(self):
        return "Q" if self.field_degree == 1 else self.field_label

    @property
    def friends(self):
        """The 'friends' to show on webpage."""
        lfriends = []
        if self.base_field() == '1.1.1.1': #i.e. QQ
            # only show symmetric powers for non-CM curves
            if not isogeny_class_cm(self.label):
                lfriends.append(('Symmetric square L-function',
                                url_for(".l_function_ec_sym_page_label",
                                    power='2', label=self.label)))
                lfriends.append(('Symmetric cube L-function',
                                url_for(".l_function_ec_sym_page_label",
                                    power='3', label=self.label)))
        return lfriends

    @property
    def instances(self):
        # Currently elliptic curve L-fns don't track other instances of the
        # L-fn, but the website expects this property to exist.
        return []

    @property
    def label(self):
        if self.field_degree == 1:
            llabel = self.long_isogeny_class_label
        else:
            llabel = self.field_label + "." + self.long_isogeny_class_label
        return llabel

    @property
    def origins(self):
        lorigins = []
        for instance in sorted(get_instances_by_Lhash(self.Lhash),
                               key=lambda elt: elt['url']):
            url = instance['url'];
            name, obj_exists = name_and_object_from_url(url);
            if not name:
                name = ''
            if obj_exists:
                lorigins.append((name, "/"+url));
            else:
                name += '&nbsp;  n/a';
                lorigins.append((name, ""));
        if self.base_field() == '1.1.1.1': #i.e. QQ
            #TODO replace classical modular forms origin by adding an object to the database
            if self.conductor <= 101:
                lorigins.append(
                   ('Modular form ' + (self.long_isogeny_class_label).replace('.', '.2'),
                       url_for("emf.render_elliptic_modular_forms",
                       level=self.conductor, weight=2,
                       character=1, label=self.isogeny_class_label)
                   ))
            else:
                lorigins.append(('Modular form ' + (self.long_isogeny_class_label)
                                .replace('.', '.2') +'&nbsp;  n/a', ""))
        return lorigins

    def _parse_labels(self):
        """Set field, conductor, isogeny information from labels."""
        (self.field_degree,
            self.field_real_signature,
            self.field_absdisc,
            self.field_index)  = map(int, self.field_label.split("."))
        field_signature = [self.field_real_signature,
                (self.field_degree - self.field_real_signature) // 2]
        # number of actual Gamma functions
        self.quasidegree = sum( field_signature )
        self.ec_conductor_norm  = int(self.conductor_label.split(".")[0])
        self.conductor = self.ec_conductor_norm * (self.field_absdisc ** self.field_degree)
        self.long_isogeny_class_label = self.conductor_label + '.' + self.isogeny_class_label
        return


    def _retrieve_lfunc_data_from_db(self):
        isogeny_class_url = "EllipticCurve/%s/%s/%s" % (self.field,
                                                        self.conductor_label,
                                                        self.isogeny_class_label)
        self.lfunc_data = get_lfunction_by_url(isogeny_class_url)
        if not self.lfunc_data:
            raise KeyError('No L-function instance data for "%s" was found in the database.' % isogeny_class_url)
        return

    def _set_knowltype(self):
        if self.field_degree == 1:
            self.info['knowltype'] = "ec.q"
        else:
            self.info['knowltype'] = "ec.nf"
        return

    def _set_title(self):
        title_end = (" of degree %d, weight 1, conductor %d,"
                     " and trivial character" % (self.degree, self.conductor))
        self.info['title'] = "$" + self.texname + "$" + ", " + title_end
        self.info['title_arithmetic'] = "L-function "  + title_end
        self.info['title_analytic'] = "L-function " + title_end
        return

    def _set_web_displaynames(self):
        self.texname = "L(s)"  # "L(s,E)"
        self.htmlname = "<em>L</em>(<em>s</em>)"  # "<em>L</em>(<em>s,E</em>)"
        self.texname_arithmetic = "L(s)"  # "L(E,s)"
        self.htmlname_arithmetic = "<em>L</em>(<em>s</em>)"  # "<em>L</em>(<em>E,s</em>)"
        self.texnamecompleteds = "\\Lambda(s)"  # "\\Lambda(s,E)"
        self.texnamecompleted1ms = "\\Lambda(1-s)"  # "\\Lambda(1-s,E)"
        self.texnamecompleteds_arithmetic = "\\Lambda(s)"  # "\\Lambda(E,s)"
        self.texnamecompleted1ms_arithmetic = "\\Lambda(" + str(self.motivic_weight + 1) + "-s)"
        # "\\Lambda(E, " + str(self.motivic_weight + 1) + "-s)"
        return


class Lfunction_EMF(Lfunction):
    """Class representing an elliptic modular form L-function

    Compulsory parameters: weight
                           level
                           character
                           label
                           number
    """

    def __init__(self, **args):
        constructor_logger(self, args)

        validate_required_args('Unable to construct elliptic modular form L-function.',
                               args, 'weight','level','character','label','number')
        validate_integer_args('Unable to construct elliptic modular form L-function.',
                              args, 'weight','level','character','number')

        self._Ltype = "ellipticmodularform"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.weight = int(self.weight)
        self.level = int(self.level)
        self.character = int(self.character)
        self.number = int(self.number)
        self.numcoeff = 20 + int(5 * math.ceil(  # Testing NB: Need to learn
            self.weight * sqrt(self.level)))     # how to use more coefficients

        # Create the modular form
        try:
            self.MF = WebNewForm(weight = self.weight, level = self.level,
                                 character = self.character, label = self.label,
                                 prec = self.numcoeff)
            # Currently WebNewForm never generates an error so check that it has coefficients
            test_if_loaded = self.MF.coefficient_embedding(1,self.number)
            test_if_loaded = test_if_loaded # shut up pyflakes
        except:
            raise KeyError("The specified modular form does not appear to be in the database.")

        # Mandatory properties
        self.fromDB = False
        self.coefficient_type = 0
        self.coefficient_period = 0
        self.poles = []
        self.residues = []
        self.langlands = True
        self.primitive = True
        self.degree = 2
        self.quasidegree = 1
        self.mu_fe = []
        self.nu_fe = [Rational(self.weight - 1)/2]
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.algebraic = True
        self.motivic_weight = self.weight - 1
        self.automorphyexp = self.motivic_weight / 2.
        # List of Dirichlet coefficients ################
        self.dirichlet_coefficients_arithmetic = []
        for n in range(1, self.numcoeff + 1):
            self.dirichlet_coefficients_arithmetic.append(self.MF.coefficient_embedding(n,self.number))

        self.dirichlet_coefficients = []
        for n in range(1, len(self.dirichlet_coefficients_arithmetic) + 1):
            self.dirichlet_coefficients.append(
                self.dirichlet_coefficients_arithmetic[n-1] /
                float(n ** self.automorphyexp))
        # Determining the sign ########################
        if self.level == 1:  # For level 1, sign = (-1)^(k/2)
            self.sign = (-1)** (self.weight/2)
        else:  # for level>1, calculate sign from Fricke involution and weight
            if self.character > 0:
                self.sign = signOfEmfLfunction(self.level, self.weight,
                                               self.dirichlet_coefficients_arithmetic)
            else:
                self.AL = self.MF.atkin_lehner_eigenvalues()
                self.sign = (self.AL[self.level]
                             * (-1) ** (self.weight / 2.))
        self.checkselfdual()

        # Specific properties
        # Get the data for the corresponding elliptic curve if possible
        if self.weight == 2 and self.MF.is_rational:
            self.ellipticcurve = EC_from_modform(self.level, self.label)
            #self.nr_of_curves_in_class = nr_of_EC_in_isogeny_class(self.ellipticcurve)
        else:
            self.ellipticcurve = False

        # Text for the web page
        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"

        if self.character != 0:
            characterName = (" character \(%s\)" %
                             (self.MF.character.latex_name))
        else:
            characterName = " trivial character"
        self.credit = 'Sage'

        # Generate a function to do computations
        if ( (self.number == 1 and (1 + self.level) * self.weight > 50) or
               (self.number > 1 and self.level * self.weight > 50)):
            self.sageLFunction = None
        else:
            generateSageLfunction(self)

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "mf"
        self.info['label'] = '{0}.{1}.{2}.{3}.{4}'.format(str(self.level), str(self.weight),
                                str(self.character), str(self.label), str(self.number))
        self.info['title'] = ("$L(s,f)$, where $f$ is a holomorphic cusp form " +
            "with weight %s, level %s, and %s" % (
            self.weight, self.level, characterName))

    def original_object(self):
        return self.MF

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
                self.dual_link = '/L' + self.lfunc_data['conjugate']
            title_end = " on $%s$" % (self.group)

        else:   # Generate from Maass form

            # Create the Maass form
            self.mf = WebMaassForm(self.maass_id, get_dirichlet_c_only=1)
            self.group = 'GL2'

            # Extract the L-function information from the Maass form object
            self.symmetry = self.mf.symmetry
            self.level = int(self.mf.level)
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
        self.level = 1
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

class Lfunction_genus2_Q(Lfunction):
    """Class representing the L-function of a genus 2 curve over Q

    Compulsory parameters: label

    """

    def __init__(self, **args):
        # Check for compulsory arguments
        validate_required_args('Unabel to construct L-function of genus 2 curve.',
                               args, 'label')

        self._Ltype = "genus2curveQ"

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.numcoeff = 30

        # Load data from the database
        label_slash = self.label.replace(".","/")
        db_label = "Genus2Curve/Q/" + label_slash
        self.lfunc_data = get_lfunction_by_url(db_label)
        if self.lfunc_data == None:
            raise KeyError('No L-function instance data for "%s" was found '% db_label +
                           'in the database.' )

        # Extract the data
        makeLfromdata(self)
        self.fromDB = True

        # Mandatory properties
        self.coefficient_period = 0
        self.coefficient_type = 2
        self.poles = []
        self.residues = []
        self.langlands = True
        self.quasidegree = 2

        # Text for the web page
        self.htmlname = "<em>L</em>(<em>s,A</em>)"
        self.texname = "L(s,A)"
        self.htmlname_arithmetic = "<em>L</em>(<em>A,s</em>)"
        self.texname_arithmetic = "L(A,s)"
        self.texnamecompleteds = "\\Lambda(s,A)"
        self.texnamecompleted1ms = "\\Lambda(1-s,A)"
        self.texnamecompleteds_arithmetic = "\\Lambda(A,s)"
        self.texnamecompleted1ms_arithmetic = "\\Lambda(A, " + str(self.motivic_weight + 1) + "-s)"
        title_end = ("where $A$ is the Jacobian of a genus 2 curve "
                      + "with label " + self.label)
        self.credit = ''

        # Initiate the dictionary info that contains the data for the webpage
        self.info = self.general_webpagedata()
        self.info['knowltype'] = "g2c.q"
        self.info['title'] = "$" + self.texname + "$" + ", " + title_end
        self.info['title_arithmetic'] = ("$" + self.texname_arithmetic + "$" + ", " +
                                 title_end)
        self.info['title_analytic'] = "$" + self.texname + "$" + ", " + title_end


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


class Lfunction_lcalc(Lfunction):
    """Class representing an L-function coming from an lcalc source,
    either a URL or a file
    It can be called with a dictionary of these forms:

    dict = { 'Ltype': 'lcalcurl', 'url': ... }  url is any url for an lcalcfile
    dict = { 'Ltype': 'lcalcfile', 'filecontents': ... }  filecontents is the
           contents of an lcalcfile
    """
    def __init__(self, **args):
        constructor_logger(self, args)
        # Initialize some default values
        self.coefficient_type = 0
        self.coefficient_period = 0
        self.poles = []
        self.residues = []
        self.langlands = True
        self.primitive = True
        self.kappa_fe = []
        self.lambda_fe = []
        self.mu_fe = []
        self.nu_fe = []
        self.selfdual = False
        self.texname = "L(s)"
        self.texnamecompleteds = "\\Lambda(s)"
        self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"
        self.primitive = None
        self.credit = ''
        self.motivic_weight = NaN
        self.algebraic = True

        self._Ltype = args.pop("Ltype")
        # Put the args into the object dictionary
        self.__dict__.update(args)

        # Get the lcalcfile from the web
        if self._Ltype == 'lcalcurl':
            if 'url' in args.keys():
                try:
                    import urllib
                    logger.debug(self.url)
                    self.filecontents = urllib.urlopen(self.url).read()
                except:
                    raise Exception("Wasn't able to read the file at the url")
            else:
                raise Exception("You forgot to supply an url.")

        LfunctionLcalc.parseLcalcfile_ver1(self, self.filecontents)

        # Check if self dual
        self.checkselfdual()

        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s)"

        try:
            self.originalfile = re.match(".*/([^/]+)$", self.url)
            self.originalfile = self.originalfile.group(1)
            self.title = ("An L-function generated by an Lcalc file: " +
                          self.originalfile)

        except:
            self.originalfile = ''
            self.title = "An L-function generated by an Lcalc file."

        logger.debug("Start generating Sage L")
        generateSageLfunction(self)

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

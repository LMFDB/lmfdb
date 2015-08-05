# -*- coding: utf-8 -*-
# The class Lfunction is defined in Lfunction_base and represents an L-function
# We subclass it here:
# RiemannZeta, Lfunction_Dirichlet, Lfunction_EC_Q, Lfunction_EMF,
# Lfunction_HMF, Lfunction_Maass, Lfunction_SMF2_scalar_valued,
# DedekindZeta, ArtinLfunction, SymmetricPowerLfunction,
# Lfunction_genus2_Q

import math
import re

from Lfunctionutilities import (p2sage, seriescoeff,
                                compute_local_roots_SMF2_scalar_valued,
                                compute_dirichlet_series,
                                number_of_coefficients_needed,
                                signOfEmfLfunction)
from LfunctionComp import (nr_of_EC_in_isogeny_class, modform_from_EC,
                           EC_from_modform)
import LfunctionDatabase
import LfunctionLcalc
from Lfunction_base import Lfunction
from lmfdb.lfunctions import logger

from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
from sage.rings.rational import Rational

from lmfdb.WebCharacter import WebDirichletCharacter
from lmfdb.WebNumberField import WebNumberField
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import *
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_classes \
     import WebMaassForm

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
def makeLfromdata(L):
    data = L.lfunc_data
    L.algebraic = data['algebraic']
    L.degree = data['degree']
    L.level = data['conductor']
    L.primitive = data['primitive']
    # Convert L.motivic_weight from python 'int' type to sage integer type.
    # This is necessary because later we need to do L.motivic_weight/2
    # when we write Gamma-factors in the arithmetic normalization.
    L.motivic_weight = ZZ(data['motivic_weight'])
    L.sign = p2sage(data['root_number'])
           # p2sage converts from the python string format in the database.
    L.mu_fe = [x+p2sage(data['analytic_normalization'])
        for x in p2sage(data['gamma_factors'])[0]]
    L.nu_fe = [x+p2sage(data['analytic_normalization'])
        for x in p2sage(data['gamma_factors'])[1]]
    L.compute_kappa_lambda_Q_from_mu_nu()
    # start items specific to hyperelliptic curves
    L.langlands = True
    L.poles = []
    L.residues = []
    L.coefficient_period = 0
    L.coefficient_type = 2
    # end items specific to hyperelliptic curves
    L.numcoeff = 30
    # an(analytic) = An(arithmetic)/n^(motivic_weight/2), where an/An are Dir. coeffs
    L.dirichlet_coefficients_arithmetic = an_from_data(p2sage(data['euler_factors']),L.numcoeff)
    L.normalize_by = p2sage(data['analytic_normalization'])
    L.dirichlet_coefficients = L.dirichlet_coefficients_arithmetic[:]
    for n in range(0, len(L.dirichlet_coefficients)):
        an = L.dirichlet_coefficients[n]
        L.dirichlet_coefficients[n] = float(an/(n+1)**L.normalize_by)
    # Note: a better name would be L.dirichlet_coefficients_analytic, but that
    # would require more global changes.
    L.localfactors = p2sage(data['euler_factors'])
    # Currently the database stores the bad_lfactors as a list and the euler_factors
    # as a string.  Those should be the same.  Once that change is made, either the
    # line above or the line below will break.  (DF and SK, Aug 4, 2015)
    L.bad_lfactors = data['bad_lfactors']
    L.checkselfdual()  # needs to be changed to read from database
    generateSageLfunction(L)  # DF: why is this needed if pulling from database?

def generateSageLfunction(L):
    """ Generate a SageLfunction to do computations
    """
    from lmfdb.lfunctions import logger
    logger.debug("Generating Sage Lfunction with parameters %s and there are %s coefficients "
                % ([L.title, L.coefficient_type, L.coefficient_period,
                L.Q_fe, L.sign, L.kappa_fe, L.lambda_fe,
                L.poles, L.residues], len(L.dirichlet_coefficients)))
    import sage.libs.lcalc.lcalc_Lfunction as lc
    L.sageLfunction = lc.Lfunction_C(L.title, L.coefficient_type,
                                        L.dirichlet_coefficients,
                                        L.coefficient_period,
                                        L.Q_fe, L.sign,
                                        L.kappa_fe, L.lambda_fe,
                                        L.poles, L.residues)
    
            # self.poles:           Needs poles of _completed_ L-function
            # self.residues:        Needs residues of _completed_ L-function
            # self.kappa_fe:        What ultimately appears if you do
            #     lcalc.lcalc_Lfunction._print_data_to_standard_output() as the
            #                                                       gamma[1]
            # self.lambda_fe:       What ultimately appears if you do
            #     lcalc.lcalc_Lfunction._print_data_to_standard_output() as the
            #                                                       lambda[1]
            # According to Rishi, as of March 2012 (sage <=5.0),
            # the documentation to his wrapper is wrong


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
        self.initStandard()
        self.kappa_fe = []
        self.lambda_fe = []
        self.mu_fe = []
        self.nu_fe = []
        self.selfdual = False
        self.texname = "L(s)"  
        self.texnamecompleteds = "\\Lambda(s)"  
        self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"  
        self.primitive = None  
        self.citation = ''
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
    
    def Lkey(self):
        return {"filecontents": self.filecontents}
    
    def source_object(self):
        return self.filecontents

#############################################################################
# The subclasses
#############################################################################
class Lfunction_EC_Q(Lfunction):
    """Class representing an elliptic curve L-function
    It can be called with a dictionary of these forms:

    dict = { 'label': ... }  label is the LMFDB label of the elliptic curve

    """
    #     This is bad, it assumes the label is Cremona's and the ground
    #     field is Q
    def __init__(self, **args):
        constructor_logger(self, args)
        # Check for compulsory arguments
        if not 'label' in args.keys():
            raise Exception("You have to supply a label for an elliptic " +
                            "curve L-function")

        # Initialize default values
        max_height = 30
        modform_translation_limit = 101

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.algebraic = True

        # Remove the ending number (if given) in the label to only get isogeny
        # class
        while self.label[len(self.label) - 1].isdigit():
            self.label = self.label[0:len(self.label) - 1]

        # Compute the # of curves in the isogeny class
        self.nr_of_curves_in_class = nr_of_EC_in_isogeny_class(self.label)

        # Create the elliptic curve
        Edata = LfunctionDatabase.getEllipticCurveData(self.label + '1')
        if Edata is None:
            raise KeyError('No elliptic curve with label %s exists in the database' % self.label)
        else:
            self.E = EllipticCurve([int(a) for a in Edata['ainvs']])

        # Extract the L-function information from the elliptic curve
        self.quasidegree = 1
        self.level = self.E.conductor()
        self.sign = self.E.lseries().dokchitser().eps

        self.mu_fe = []
        self.nu_fe = [Rational('1/2')]
        
        self.compute_kappa_lambda_Q_from_mu_nu()
        
        self.numcoeff = round(self.Q_fe * 220 + 10)
        # logger.debug("numcoeff: {0}".format(self.numcoeff))
        self.langlands = True
        self.degree = 2
        self.motivic_weight = 1

        # Get the data for the corresponding modular form if possible
        if self.level <= modform_translation_limit:
            self.modform = modform_from_EC(self.label)
        else:
            self.modform = False

        #remove a0
        self.dirichlet_coefficients = self.E.anlist(self.numcoeff)[1:]

        self.dirichlet_coefficients_arithmetic = (
            self.dirichlet_coefficients[:])
        self.normalize_by = Rational('1/2')

        # Renormalize the coefficients
        for n in range(0, len(self.dirichlet_coefficients)):
            an = self.dirichlet_coefficients[n]
            self.dirichlet_coefficients[n] = float(an) / float(sqrt(n + 1))

        self.poles = []
        self.residues = []
        self.coefficient_period = 0
        self.selfdual = True
        self.primitive = True
        self.coefficient_type = 2
        self.texname = "L(s,E)"
        self.texnamecompleteds = "\\Lambda(s,E)"
        self.texnamecompleted1ms = "\\Lambda(1-s,E)"
        self.title = ("L-function $L(s,E)$ for the Elliptic Curve Isogeny " +
                      "Class " + self.label)
        self.properties = [('Degree ', '%s' % self.degree)]
        self.properties.append(('Level', '%s' % self.level))
        self.credit = 'Sage'
        self.citation = ''
        self.sageLfunction = lc.Lfunction_from_elliptic_curve(self.E,
                                                        int(self.numcoeff))

        constructor_logger(self, args)
    
    def Ltype(self):
        return "ellipticcurveQ"

    def ground_field(self):
        return "Q"

    def Lkey(self):
        # If over Q, the lmfdb label determines the curve
        return {"label": self.label}
    
    def original_object(self):
        return self.E


#############################################################################

class Lfunction_EMF(Lfunction):
    """Class representing an elliptic modular form L-function

    Compulsory parameters: weight
                           level

    Possible parameters: character
                         label
                         number
    
    Actually, some of the possible parameters are required depending
    on the value of the possible parameters

    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        if not ('weight' in args.keys() and 'level' in args.keys()
                and 'character' in args.keys() and 'label' in args.keys()
                and 'number' in args.keys()):
            raise KeyError("You have to supply weight, level, character, " +
                           "label and number for an " +
                           "elliptic modular form L-function")

        modform_translation_limit = 101

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.initStandard()
        self.algebraic = True
        self.degree = 2
        self.quasidegree = 1

        self.weight = int(self.weight)
        self.motivic_weight = self.weight - 1
        self.level = int(self.level)
        self.character = int(self.character)
        self.number = int(self.number)
        self.numcoeff = 20 + int(5 * math.ceil(  # Testing NB: Need to learn
            self.weight * sqrt(self.level)))     # how to use more coefficients
        
        # Create the modular form
        try:
            self.MF = WebNewForm(k = self.weight, N = self.level,
                                 chi = self.character, label = self.label, 
                                 prec = self.numcoeff, verbose=0)
        except:
            raise KeyError("No data available yet for this modular form, so" +
                           " not able to compute its L-function")
        
        # Extract the L-function information from the elliptic modular form
        self.automorphyexp = (self.weight - 1) / 2.
        self.mu_fe = []
        self.nu_fe = [Rational(self.weight - 1)/2]
        self.compute_kappa_lambda_Q_from_mu_nu()


        # Get the data for the corresponding elliptic curve if possible
        if self.weight == 2 and self.MF.is_rational():
            self.ellipticcurve = EC_from_modform(self.level, self.label)
            self.nr_of_curves_in_class = nr_of_EC_in_isogeny_class(
                                                    self.ellipticcurve)
        else:
            self.ellipticcurve = False

        # Appending list of Dirichlet coefficients
        embeddings = self.MF.q_expansion_embeddings(self.numcoeff + 1)
        self.algebraic_coefficients = []
        for n in range(1, self.numcoeff + 1):
            self.algebraic_coefficients.append(embeddings[n][self.number])
            
        self.dirichlet_coefficients = []
        for n in range(1, len(self.algebraic_coefficients) + 1):
            self.dirichlet_coefficients.append(
                self.algebraic_coefficients[n-1] /
                float(n ** self.automorphyexp))

        # Determining the sign
        if self.level == 1:  # For level 1, the sign is always plus
            self.sign = 1
        else:  # for level>1, calculate sign from Fricke involution and weight
            if self.character > 0:
                self.sign = signOfEmfLfunction(self.level, self.weight,
                                               self.algebraic_coefficients)
            else:
                logger.debug('Startin atkin lehner')
                self.AL = self.MF.atkin_lehner_eigenvalues()
                logger.debug(self.AL)
                self.sign = (self.AL[self.level]
                             * (-1) ** (self.weight / 2.))
        logger.debug("Sign: " + str(self.sign))
        self.checkselfdual()

        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"

        if self.character != 0:
            characterName = (" character \(%s\)" %
                             (self.MF.conrey_character_name()))
        else:
            characterName = " trivial character"
        self.title = ("$L(s,f)$, where $f$ is a holomorphic cusp form " +
            "with weight %s, level %s, and %s" % (
            self.weight, self.level, characterName))
        self.credit = 'Sage'

        generateSageLfunction(self)

    def Ltype(self):
        return "ellipticmodularform"
    
    def Lkey(self):
        return {"weight": self.weight, "level": self.level}
        
    def original_object(self):
        return self.MF

#############################################################################


class Lfunction_HMF(Lfunction):
    """Class representing a Hilbert modular form L-function

    Compulsory parameters: label

    Possible parameters: number

    """

    def __init__(self, **args):
        # Check for compulsory arguments
        if not ('label' in args.keys()):
            raise KeyError("You have to supply label for a Hilbert modular " +
                           "form L-function")
        logger.debug(str(args))
        # Initialize default values
        if not args['number']:
            args['number'] = 0  # Default choice of embedding of coefficients
        args['character'] = 0   # Only trivial character

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.algebraic = True
        logger.debug(str(self.character) + str(self.label) + str(self.number))

        # Load form from database
        (f, F_hmf) = LfunctionDatabase.getHmfData(self.label)
        if f is None:
            raise KeyError("There is no Hilbert modular form with that label")

        F = WebNumberField(f['field_label'])

        self.character = args['character']
        if self.character > 0:
            raise KeyError("The L-function of a Hilbert modular form with "
                           + "non-trivial character has not been "
                           + "implemented yet.")
        self.number = int(args['number'])

        # It is a Sage int
        self.field_disc = F.disc()
        self.field_degree = int(F.degree())
        try:
            self.weight = int(f['parallel_weight'])
        except KeyError:
            self.weight = int(f['weight'].split(', ')[0][1:])

        self.motivic_weight = self.weight - 1
        self.level = f['level_norm'] * self.field_disc ** 2

        # Extract the L-function information from the hilbert modular form
        self.automorphyexp = float(self.weight - 1) / float(2)
        
        self.mu_fe = []
        self.nu_fe = [self.automorphyexp for i in range(self.field_degree)]
        
        
        self.kappa_fe = [1 for i in range(self.field_degree)]
        self.lambda_fe = [self.automorphyexp for i in range(self.field_degree)]
        self.Q_fe = (float(sqrt(self.level)) / (2 * math.pi) **
                     (self.field_degree))

        # POD: Consider using self.compute_kappa_lambda_Q_from_mu_nu (inherited from Lfunction or overloaded for this particular case), this will help standardize, reuse code and avoid problems
        

        R = QQ['x']
        (x,) = R._first_ngens(1)
        K = NumberField(R(str(f['hecke_polynomial']).replace('^', '**')), 'e')
        e = K.gens()[0]
        iota = K.complex_embeddings()[self.number]

        if self.level == 1:  # For level 1, the sign is always plus
            self.sign = 1
        else:  # for level>1, calculate sign from Fricke involution and weight
            AL_signs = [iota(eval(al[1])) for al in f['AL_eigenvalues']]
            self.sign = prod(AL_signs) * (-1) ** (float(self.weight *
                                                        self.field_degree / 2))
        logger.debug("Sign: " + str(self.sign))

        self.selfdual = True
        self.langlands = True
        self.primitive = True
        self.degree = 2 * self.field_degree
        self.poles = []
        self.residues = []

        # Compute Dirichlet coefficients
        hecke_eigenvalues = [iota(K(str(ae))) for ae in f['hecke_eigenvalues']]
        primes = [pp_str.split(', ') for pp_str in F_hmf['primes']]
        primes = [[int(pp[0][1:]), int(pp[1])] for pp in primes]
        primes = [[pp[0], pp[1], factor(pp[0])[0][1]] for pp in primes]

        PP = primes[-1][0]
        self.numcoeff = PP  # The number of coefficients is given by the
                            # norm of the last prime

        ppmidNN = [c[0] for c in f['AL_eigenvalues']]

        ratl_primes = [p for p in range(primes[-1][0] + 1) if is_prime(p)]
        RCC = CC['T']
        (T,) = RCC._first_ngens(1)
        heckepols = [RCC(1) for p in ratl_primes]
        for l in range(len(hecke_eigenvalues)):
            if F_hmf['primes'][l] in ppmidNN:
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
                S = [1] + [dcoeffs[p ** i] for i in range(1, k)]
                heckepol = heckepolsinv[ratl_primes.index(p)]
                dcoeffs.append(heckepol[k])
            else:
                # composite
                ancoeff = prod([dcoeffs[pe[0] ** pe[1]] for pe in nfact])
                dcoeffs.append(ancoeff)

        # ff = open('dcoeffs.txt', 'w')
        # ff.write(str(primes) + '\n')
        # ff.write(str(heckepols) + '\n')
        # ff.write(str(ratl_primes) + '\n')
        # ff.close()

        self.dirichlet_coefficients = dcoeffs[1:]

        self.coefficient_period = 0
        self.coefficient_type = 3
        self.quasidegree = 1

        self.checkselfdual()

        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
        self.title = ("$L(s,f)$, " + "where $f$ is a holomorphic Hilbert cusp "
                      + "form with parallel weight " + str(self.weight)
                      + ", level norm " + str(f['level_norm']) )
        if self.character:
            self.title += ", and character " + str(self.character)
        else:
            self.title += ", and trivial character"

        self.citation = ''
        self.credit = ''

        generateSageLfunction(self)
        constructor_logger(self, args)

    def Ltype(self):
        return "hilbertmodularform"
        
    def Lkey(self):
        return {"label", self.label}


#############################################################################

class RiemannZeta(Lfunction):
    """Class representing the Riemann zeta fucntion

    Possible parameters: numcoeff  (the number of coefficients when computing)

    """

    def __init__(self, **args):
        constructor_logger(self, args)

        # Initialize default values
        self.numcoeff = 30  # set default to 30 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.algebraic = True
        self.numcoeff = int(self.numcoeff)

        self.coefficient_type = 1
        self.quasidegree = 1
        self.mu_fe = [0]
        self.nu_fe = []
        self.sign = 1
        self.langlands = True
        self.degree = 1
        self.level = 1
        self.dirichlet_coefficients = [1 for n in range(self.numcoeff)]
        
        self.poles = [0, 1]
        self.residues = [-1, 1]
        self.poles_L = [1]  # poles of L(s), used by createLcalcfile_ver2
        self.residues_L = [1]  # residues of L(s) createLcalcfile_ver2
        self.coefficient_period = 0
        self.selfdual = True
        
        self.compute_kappa_lambda_Q_from_mu_nu()
        self.texname = "\\zeta(s)"
        self.texnamecompleteds = "\\xi(s)"
        self.texnamecompleted1ms = "\\xi(1-s)"
        self.credit = 'Sage'
        self.primitive = True
        self.citation = ''
        self.title = "Riemann Zeta-function: $\\zeta(s)$"
        self.is_zeta = True

        self.sageLfunction = lc.Lfunction_Zeta()
        self.motivic_weight = 0

    def Ltype(self):
        return "riemann"

    def Lkey(self):
        return {}

#############################################################################


class Lfunction_Dirichlet(Lfunction):
    """Class representing the L-function of a Dirichlet character

    Compulsory parameters: charactermodulus
                           characternumber

    Possible parameters: numcoeff  (the number of coefficients when computing)

    """

    def __init__(self, **args):

        # Check for compulsory arguments
        if not ('charactermodulus' in args.keys()
                and 'characternumber' in args.keys()):
            raise KeyError("You have to supply charactermodulus and "
                           + "characternumber for the L-function of "
                           + "a Dirichlet character")

        # Initialize default values
        self.numcoeff = 30    # set default to 30 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.algebraic = True
        self.charactermodulus = int(self.charactermodulus)
        self.characternumber = int(self.characternumber)
        self.numcoeff = int(self.numcoeff)

        # Create the Dirichlet character
        self.web_chi = WebDirichletCharacter( modulus=self.charactermodulus,
                                number = self.characternumber)
        chi = self.web_chi.chi
        self.motivic_weight = 0

        if chi.is_primitive():

            # Extract the L-function information from the Dirichlet character
            # Warning: will give nonsense if character is not primitive
            aa = 1 - chi.is_even()   # usually denoted \frak a
            self.quasidegree = 1
            self.mu_fe = [aa]
            self.nu_fe = []
            
            
            self.kappa_fe = [0.5]
            self.lambda_fe = [0.5 * aa]
            self.Q_fe = float(sqrt(self.charactermodulus) / sqrt(math.pi))
            # POD: Consider using self.compute_kappa_lambda_Q_from_mu_nu (inherited from Lfunction or overloaded for this particular case), this will help standardize, reuse code and avoid problems
            
            self.sign = 1 / (I ** aa * float(sqrt(self.charactermodulus)) /
                             (chi.gauss_sum_numerical()))
            self.langlands = True
            self.primitive = True
            self.degree = 1
            self.coefficient_period = self.charactermodulus
            self.level = self.charactermodulus

            chival = [ CC(z.real,z.imag) for z in chi.values()]
            self.dirichlet_coefficients = [ chival[k % self.level] for k in range(1,self.numcoeff) ]

            self.poles = []
            self.residues = []

            # Determine if the character is real
            # (i.e., if the L-function is selfdual)

            self.selfdual = chi.multiplicative_order() <= 2

            if self.selfdual:
                self.coefficient_type = 2
                for n in range(0, self.numcoeff - 1):
                    self.dirichlet_coefficients[n] = int(
                        round(real(self.dirichlet_coefficients[n])))
            else:
                self.coefficient_type = 3

            self.texname = "L(s,\\chi)"
            self.texnamecompleteds = "\\Lambda(s,\\chi)"

            if self.selfdual:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\chi)"
            else:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{\\chi})"

            self.credit = 'Sage'
            self.citation = ''
            self.title = "Dirichlet L-function: $L(s,\\chi)$"
            self.title = (self.title + ", where $\\chi$ is the " +
                          "character modulo " +
                          str(self.charactermodulus) + ", number " +
                          str(self.characternumber))

            self.sageLfunction = lc.Lfunction_from_character(chi.sage_character())

        else:  # Character not primitive
            raise Exception("The dirichlet character you choose is " +
                            "not primitive so it's Dirichlet series " +
                            "is not an L-function.", "UserError")

        constructor_logger(self, args)

    def Ltype(self):
        return "dirichlet"

    def Lkey(self):
        return {"charactermodulus": self.charactermodulus,
                "characternumber": self.characternumber}


#############################################################################

class Lfunction_Maass(Lfunction):
    """Class representing the L-function of a Maass form

    Compulsory parameters: dbid

    Possible parameters: dbName  (the name of the database for the Maass form)
                        dbColl  (the name of the collection for the Maass form)

    """
    def __init__(self, **args):
        constructor_logger(self, args)

        # Check for compulsory arguments
        if not 'dbid' in args.keys():
            raise KeyError("You have to supply dbid for the L-function of a "
                           + "Maass form")

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.initStandard()
        self.algebraic = False

        [dbName, dbColl, dbEntry] = LfunctionDatabase.getLmaassByDatabaseId(args['dbid'])
        # Fetch the information from the database
        if dbColl == 'LemurellMaassHighDegree':  # Data from Lemurell

            # Extract the L-function information from the database entry
            self.__dict__.update(dbEntry)

            # Extract L-function information from lcalfile in the database
            import LfunctionLcalc
            LfunctionLcalc.parseLcalcfile_ver1(self, self.lcalcfile)

        elif dbColl == 'FarmerMaass':
            self.__dict__.update(dbEntry)

        elif dbColl == 'LemurellTest':
            self.__dict__.update(dbEntry)
            aa = self.real_shiftsR[0]
            self.mu_fe = [aa + self.eigenvalue * I, aa - self.eigenvalue * I]
            self.lambda_fe = [0.5 * self.mu_fe[0], 0.5 * self.mu_fe[1]]
            self.title = ("$L(s,f)$, where $f$ is a Maass cusp form with "
                          + "level %s, eigenvalue %s, and %s" % (
                          self.level, self.eigenvalue, self.characterName))

        else:  # GL2 data from Then or Stromberg

            DB = LfunctionDatabase.getMaassDb()
            self.mf = WebMaassForm(DB, self.dbid, get_dirichlet_c_only=1)
            self.group = 'GL2'

            # Extract the L-function information from the Maass form object
            self.symmetry = self.mf.symmetry
            self.eigenvalue = float(self.mf.R)
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

            # Todo: If self has dimension >1, link to specific L-functions
            self.dirichlet_coefficients = self.mf.coeffs
            if self.dirichlet_coefficients[0] == 0:
                self.dirichlet_coefficients.pop(0)

            # Set properties of the L-function
            self.coefficient_type = 2
            self.checkselfdual()
            self.primitive = True
            self.degree = 2
            self.quasidegree = 2
            if self.symmetry == "odd" or self.symmetry == 1:
                self.sign = -self.fricke
                aa = 1
            else:
                self.sign = self.fricke
                aa = 0
            
            self.mu_fe = [aa + self.eigenvalue * I, aa - self.eigenvalue * I]
            self.nu_fe = []           
            self.kappa_fe = [0.5, 0.5]
            self.lambda_fe = [0.5 * aa + self.eigenvalue *
                              I / 2, 0.5 * aa - self.eigenvalue * I / 2]
            self.Q_fe = float(sqrt(self.level)) / float(math.pi)
            # POD: Consider using self.compute_kappa_lambda_Q_from_mu_nu (inherited from Lfunction or overloaded for this particular case), this will help standardize, reuse code and avoid problems


            self.texname = "L(s,f)"
            self.texnamecompleteds = "\\Lambda(s,f)"

            if self.selfdual:
                self.texnamecompleted1ms = "\\Lambda(1-s,f)"
            else:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"

            if self.characternumber != 1:
                self.characterName = (" character \(\chi_{%s}(%s,\cdot)\)"
                                 % (self.level, self.characternumber))
            else:
                self.characterName = " trivial character"
            self.title = ("$L(s,f)$, where $f$ is a Maass cusp form with "
                          + "level %s, eigenvalue %s, and %s" % (
                          self.level, self.eigenvalue, self.characterName))
            self.citation = ''
            self.credit = self.mf.contributor_name

        generateSageLfunction(self)

    def Ltype(self):
        return "maass"
    
    def Lkey(self):
        return {"dbid": self.dbid}


#############################################################################

class DedekindZeta(Lfunction):   # added by DK
    """Class representing the Dedekind zeta-function

    Compulsory parameters: label

    """

    def __init__(self, **args):
        if not 'label' in args.keys():
            raise Exception("You have to supply a label for a " +
                            "Dedekind zeta function")
        
        constructor_logger(self, args)
        self.motivic_weight = 0
        # Check for compulsory arguments
        
        # Initialize default values

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.algebraic = True

        # Fetch the polynomial of the field from the database
        wnf = WebNumberField(self.label)
        # poly_coeffs = wnf.coeffs()

        # Extract the L-function information from the polynomial
        R = QQ['x']
        (x,) = R._first_ngens(1)
        # self.polynomial = (sum([poly_coeffs[i]*x**i
        # for i in range(len(poly_coeffs))]))
        self.NF = wnf.K()  # NumberField(self.polynomial, 'a')
        self.signature = wnf.signature()  # self.NF.signature()
        self.sign = 1
        self.quasidegree = sum(self.signature)
        self.level = wnf.disc().abs()  # self.NF.discriminant().abs()
        self.degreeofN = self.NF.degree()
        
        self.mu_fe = self.signature[0] * [0]  
        self.nu_fe = self.signature[1] * [0] 
        self.compute_kappa_lambda_Q_from_mu_nu()
        
        self.langlands = True
        # self.degree = self.signature[0] + 2 * self.signature[1] # N = r1 +2r2
        self.degree = self.degreeofN
        self.dirichlet_coefficients = [Integer(x) for x in
                                       self.NF.zeta_coefficients(5000)]
        self.h = wnf.class_number()  # self.NF.class_number()
        self.R = wnf.regulator()  # self.NF.regulator()
        self.w = len(self.NF.roots_of_unity())
        # r1 = self.signature[0]
        self.res = RR(2 ** self.signature[0] * self.h * self.R) / self.w
        self.grh = wnf.used_grh()
        if self.degree > 1:
            if wnf.is_abelian() and len(wnf.dirichlet_group())>0:
                cond = wnf.conductor()
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
                                  str(the_rep.conductor())!=str(1) or
                                  the_rep.index()>1):
                            ar_url = url_for("l_functions.l_function_artin_page",
                                             dimension=the_rep.dimension(),
                                             conductor=the_rep.conductor(),
                                             tim_index=the_rep.index())
                            right = (r'\({}^{%d}\)' % (nfgg[j])
                                     if nfgg[j]>1 else r'')
                            self.factorization += r'\(\;\cdot\)' 
                            self.factorization += (r'<a href="%s">\(L(s, \rho_{%d,%s,%d})\)</a>' % (ar_url,
                                            the_rep.dimension(),
                                            str(the_rep.conductor()),
                                            the_rep.index()))
                            self.factorization += right

        self.poles = [1, 0]  # poles of the Lambda(s) function
        self.residues = [self.res, -self.res] #residues of Lambda(s) function

        self.poles_L = [1]  # poles of L(s) used by createLcalcfile_ver2
        self.residues_L = [1234]
            # residues of L(s) used by createLcalcfile_ver2,
            # XXXXXXXXXXXX needs to be set

        self.coefficient_period = 0
        self.selfdual = True
        self.primitive = True
        self.coefficient_type = 3
        self.texname = "\\zeta_K(s)"
        self.texnamecompleteds = "\\Lambda_K(s)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda_K(1-s)"
        else:
            self.texnamecompleted1ms = "\\Lambda_K(1-s)"
        self.title = "Dedekind zeta-function: $\\zeta_K(s)$"
        self.title = (self.title + ", where $K$ is the " +
                      str(self.NF).replace("in a ", ""))
        self.credit = 'Sage'
        self.citation = ''

        generateSageLfunction(self)

    def Ltype(self):
        return "dedekindzeta"

    def Lkey(self):
        return {"label": self.label}

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
        if "t" in args and "family" in args:
            args["label"] = args["family"] + "_" + args["t"]
        if not ('label' in args.keys()):
            raise KeyError("You have to supply a label for a hypergeometric motive L-function")            
        self.label = args["label"]
        self.motive = LfunctionDatabase.getHgmData(self.label)
        
        self.conductor = self.motive["cond"]

        self.level = self.conductor
        self.title = ("L-function for the hypergeometric motive with label  "+self.label)

        self.credit = 'Dave Roberts, using Magma'
        
        
        
        self.motivic_weight = 0
        self.algebraic = True
        self.coefficient_type = 0
        self.degree = self.motive["degree"]
        try:
            self.arith_coeffs = self.motive["coeffs"]
        except:
            self.arith_coeffs = map(Integer, self.motive["coeffs_string"])

        self.support = "Support by Paul-Olivier Dehaye"
        
        self.sign = self.motive["sign"]
        self.motivic_weight =  self.motive["weight"]
        
        # level, residues, selfdual, primitive, langlands
        # will not work for some values!!!!
        self.poles = []
        self.residues = []
        self.primitive = True
        self.langlands = True
            
        hodge = self.motive["hodge"]
        signature = self.motive["sig"]
        hodge_index = lambda p: hodge[p]
            # The hodge number p,q
        
        from lmfdb.hypergm.hodge import mu_nu
        
        
        
        self.mu_fe, self.nu_fe = mu_nu(hodge, signature)
         
        self.selfdual = True 
        self.coefficient_period = 0

        self.compute_kappa_lambda_Q_from_mu_nu()            # Somehow this doesn t work, and I don t know why!
                
        self.dirichlet_coefficients = [Reals()(Integer(x))/Reals()(n+1)**(self.motivic_weight/2.) for n, x in enumerate(self.arith_coeffs)]

        
        self.texname = "L(s)"  
        self.texnamecompleteds = "\\Lambda(s)"  
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s)" 
        else:
            self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"
        import sage.libs.lcalc.lcalc_Lfunction as lc
        
        Lexponent = self.motivic_weight/2.            
        normalize =lambda coeff, n, exponent: Reals()(coeff)/n**exponent
        self.dirichlet_coefficient = [normalize(coeff, i+1, Lexponent) for i, coeff in enumerate(self.arith_coeffs)]

        period = 0
        
        self.sageLfunction = lc.Lfunction_D("LfunctionHypergeometric", 0, self.dirichlet_coefficient, period, self.Q_fe, self.sign, self.kappa_fe, self.lambda_fe, self.poles, self.residues)
        
    def Ltype(self):
        return "hgmQ"
        
    def Lkey(self):
        return {"label":self.label}
        
#############################################################################

class ArtinLfunction(Lfunction):
    """Class representing the Artin L-function

    Compulsory parameters: dimension, conductor, tim_index

    """
    def __init__(self, **args):
        constructor_logger(self, args)
        if not ('dimension' in args.keys() and 'conductor' in args.keys() and 'tim_index' in args.keys()):
            raise KeyError("You have to supply dimension, conductor and " +
                           "tim_index for an Artin L-function")    
        
        from lmfdb.math_classes import ArtinRepresentation
        self.dimension = args["dimension"]
        self.conductor = args["conductor"]
        self.tim_index = args["tim_index"]
        self.artin = ArtinRepresentation(self.dimension,
                                         self.conductor, self.tim_index)

        self.title = ("L function for an Artin representation of dimension "
                      + str(self.dimension)
                      + ", conductor " + str(self.conductor))

        self.motivic_weight = 0
        self.algebraic = True
        self.degree = self.artin.dimension()
        self.coefficient_type = 0
        
        if self.degree == 1:
            self.coefficient_period = Integer(self.artin.conductor())
            self.dirichlet_coefficients = self.artin.coefficients_list(
                upperbound=self.coefficient_period)
        else:
            self.coefficient_period = 0
            self.dirichlet_coefficients = self.artin.coefficients_list(
                upperbound=1000)
        
        

        
        self.sign = self.artin.root_number()
        self.poles_L = self.artin.poles()
        self.residues_L = self.artin.residues()
        self.poles = self.artin.completed_poles()
        self.residues = self.artin.completed_residues()
        self.level = self.artin.conductor()
        self.selfdual = self.artin.selfdual()
        self.primitive = self.artin.primitive()
        self.langlands = self.artin.langlands()
        self.mu_fe = self.artin.mu_fe()
        self.nu_fe = self.artin.nu_fe()
        
        
        self.Q_fe = self.Q_fe = float(sqrt(Integer(self.conductor))/2.**len(self.nu_fe)/pi**(len(self.mu_fe)/2.+len(self.nu_fe)))
        self.kappa_fe = [.5 for m in self.mu_fe] + [1. for n in self.nu_fe] 
        self.lambda_fe = [m/2. for m in self.mu_fe] + [n for n in self.nu_fe]
        
        self.credit = ('Sage, lcalc, and data precomputed in ' +
                       'Magma by Tim Dokchitser')
        
        
        self.citation = ''
        self.support = "Support by Paul-Olivier Dehaye"

        self.texname = "L(s)"  
        self.texnamecompleteds = "\\Lambda(s)"  
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s)" 
        else:
            self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"
        
        generateSageLfunction(self)

    def Ltype(self):
        return "artin"
        
    def Lkey(self):
        return {"dimension": self.dimension, "conductor": self.conductor,
                "tim_index": self.tim_index}

#############################################################################


class SymmetricPowerLfunction(Lfunction):
    """Class representing the Symmetric power of an L-function

    Only implemented for (non-CM) elliptic curves

    Compulsory parameters: power, underlying_type, field
    For ellitic curves: label

    """

    def __init__(self, **args):
        constructor_logger(self, args)
        if not ('power' in args.keys() and 'underlying_type' in args.keys() and
                'field' in args.keys()):
                    raise KeyError("You have to supply power, underlying " +
                                   "type and field for a symmetric power " +
                                   "L-function")
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

        # Put the arguments into the object dictionary
        # They are: power, underlying_type, field, label  (for EC)
        self.__dict__.update(args)

        try:
            self.m = int(self.power)
        except TypeError:
            raise TypeError("The power has to be an integer")
        if self.underlying_type != 'EllipticCurve' or self.field != 'Q':
            raise TypeError("The symmetric L-functions have been implemented " +
                            "only for Elliptic Curves over Q")

        # Create the elliptic curve
        Edata = LfunctionDatabase.getEllipticCurveData(self.label + '1')
        if Edata is None:
            raise KeyError('No elliptic curve with label %s exists in the database' % self.label)
        else:
            self.E = EllipticCurve([int(a) for a in Edata['ainvs']])

        if self.E.has_cm():
            raise TypeError('This Elliptic curve has complex multiplication' +
                            ' and the symmetric power of its L-function is ' +
                            'then not primitive. This has not yet been ' +
                            'implemented')

        from lmfdb.symL.symL import SymmetricPowerLFunction
        self.S = SymmetricPowerLFunction(self.E, self.m)
        self.algebraic = True
        self.title = ("The Symmetric %s $L$-function $L(s,E,\mathrm{sym}^{%d})$ of Elliptic Curve Isogeny Class %s"
                      % (ordinal(self.m), self.m, self.label))

        self.dirichlet_coefficients = self.S._coeffs

        self.sageLfunction = self.S._construct_L()

        # Initialize some default values
        self.coefficient_period = 0
        self.degree = self.m + 1
        self.Q_fe = self.S._Q_fe
        self.poles = self.S._poles
        self.residues = self.S._residues
        self.kappa_fe = self.S._kappa_fe
        self.lambda_fe = self.S._lambda_fe
        
        self.compute_some_mu_nu()
        
        
        
        #self.mu_fe = self.kappa_fe
        #self.nu_fe = self.lambda_fe
        
        self.sign = self.S.root_number
        self.motivic_weight = self.m
        self.selfdual = True
        self.langlands = True
        self.texname = "L(s, E, \mathrm{sym}^{%d})" % self.m  
        self.texnamecompleteds = "\\Lambda(s,E,\mathrm{sym}^{%d})" % self.S.m
        self.texnamecompleted1ms = ("\\Lambda(1-{s}, E,\mathrm{sym}^{%d})"
                                    % self.S.m)
        self.primitive = True  
        self.citation = ' '
        self.credit = ' '
        self.level = self.S.conductor

    def Ltype(self):
        return "SymmetricPower"
    
    def Lkey(self):
        return {"power": power, "underlying_type": underlying_type,
                "field": field}

#############################################################################

class Lfunction_SMF2_scalar_valued(Lfunction):
    """Class representing an L-function for a scalar valued
    Siegel modular form of degree 2

    Compulsory parameters: weight
                           orbit

    Optional parameters: number



    """

    def __init__(self, **args):

        # Check for compulsory arguments
        if not ('weight' in args.keys() and 'orbit' in args.keys()):
            raise KeyError("You have to supply weight and orbit for a Siegel " +
                           "modular form L-function")
        # logger.debug(str(args))

        if not args['number']:
            args['number'] = 0     # Default embedding of the coefficients

        self.__dict__.update(args)
        self.algebraic = True
        self.weight = int(self.weight)
        self.motivic_weight = 2*self.weight - 3 # taken from A. Panchiskin's talk @ Oberwolfach, Oct. 2007 
        self.number = int(self.number)

        # Load the eigenvalues
        if (self.weight == 20 or self.weight == 22 or self.weight == 24 or
                self.weight == 26) and self.orbit[0] == 'U':
            loc = ("http://data.countnumber.de/Siegel-Modular-Forms/Sp4Z/xeigenvalues/"
                    + str(self.weight) + "_" + self.orbit + "-ev.sobj")

        else:
            loc = ("http://data.countnumber.de/Siegel-Modular-Forms/Sp4Z/eigenvalues/"
                   + str(self.weight) + "_" + self.orbit + "-ev.sobj")

        self.ev_data = load(loc)
        self.mu_fe = []  # the shifts of the Gamma_R to print
        self.automorphyexp = float(self.weight) - float(1.5)
        self.nu_fe = [float(1) / float(2), self.automorphyexp]  # the shift of
                                                                # the Gamma_C to print
        self.level = 1
        self.compute_kappa_lambda_Q_from_mu_nu()

        self.sign = (-1) ** float(self.weight)

        self.degree = 4
        roots = compute_local_roots_SMF2_scalar_valued(
            self.ev_data, self.weight,
            self.number)  # compute the roots of the Euler factors

        self.numcoeff = max([a[0] for a in roots])  # include a_0 = 0
        self.dirichlet_coefficients = compute_dirichlet_series(
            roots, self.numcoeff)  # these are in the analytic normalization
                                   # the coefficients from Gamma(ks+lambda)
        self.selfdual = True
        if self.orbit[0] == 'U':  # if the form isn't a lift but is a cusp form
            self.poles = []  # the L-function is entire
            self.residues = []
            self.langlands = True
            self.primitive = True  # and primitive
        elif self.orbit[0] == 'E':  # if the function is an Eisenstein series
            self.poles = [float(3) / float(2)]
            self.residues = [math.pi ** 2 / 6]  # fix this
            self.langlands = True
            self.primitive = False
        elif self.orbit[0] == 'M':  # if the function is a lift and a cusp form
            self.poles = [float(3) / float(2)]
            self.residues = [math.pi ** 2 / 6]  # fix this
            self.langlands = True
            self.primitive = False
        elif self.orbit[0] == 'K':
            self.poles = [float(3) / float(2)]
            self.residues = [math.pi ** 2 / 6]  # fix this
            self.langlands = True
            self.primitive = False

        # FIX the coefficients by applying the analytic normalization and
        # K = self.ev_data[0].parent().fraction_field()
        # if K == QQ:
        # d = self.dirichlet_coefficients
        # self.dirichlet_coefficients = [ d[i]/float(i)**self.automorphyexp for i in range(1,len(d)) ]
        # else:
        # d = self.dirichlet_coefficients
        # self.dirichlet_coefficients = [ emb(d[i])/float(i)**self.automorphyexp for i in range(1,len(d)) ]
        self.coefficient_period = 0
        self.coefficient_type = 3
        self.quasidegree = 1

        self.checkselfdual()

        self.texname = "L(s,F)"
        self.texnamecompleteds = "\\Lambda(s,F)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,F)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{F})"
        self.title = ("$L(s,F)$, " + "where $F$ is a scalar-valued Siegel " +
                      "modular form of weight " + str(self.weight) + ".")

        self.citation = ''
        self.credit = ''

        generateSageLfunction(self)

    def Ltype(self):
        if self.orbit[0] == 'U':
            return "siegelnonlift"
        elif self.orbit[0] == 'E':
            return "siegeleisenstein"
        elif self.orbit[0] == 'K':
            return "siegelklingeneisenstein"
        elif self.orbit[0] == 'M':
            return "siegelmaasslift"
    
    def Lkey():
        return {"weight": self.weight, "orbit": self.orbit}

#############################################################################


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
        if not ('charactermodulus' in args.keys()
                and 'characternumber' in args.keys()
                and 'ellipticcurvelabel' in args.keys() ):
            raise KeyError("You have to supply charactermodulus, "
                           + "characternumber and a curve label "
                           + "for the L-function of "
                           + "a tensor product")

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.charactermodulus = int(self.charactermodulus)
        self.characternumber = int(self.characternumber)
        self.Elabel = self.ellipticcurvelabel

        # Create the tensor product
        # try catch later
        self.tp = TensorProduct(self. Elabel, self.charactermodulus,
                                self.characternumber)
        chi = self.tp.chi
        E = self.tp.E

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

    def Ltype(self):
        return "tensorproduct"

    def Lkey(self):
        return {"ellipticcurvelabel": self.Elabel,
                "charactermodulus": self.charactermodulus,
                "characternumber": self.characternumber}

#############################################################################

class Lfunction_genus2_Q(Lfunction):
    """Class representing the L-function of a genus 2 curve over Q

    Compulsory parameters: label

    """

    def __init__(self, **args):
        # Check for compulsory arguments
        if not ('label' in args.keys()):
            raise KeyError("You have to supply label for a genus 2 curve " +
                           "L-function")
        logger.debug(str(args))

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.label = args['label']

        # Load form from database
        isoclass = LfunctionDatabase.getGenus2IsogenyClass(self.label)
        if isoclass is None:
            raise KeyError("There is no genus 2 isogeny class with that label")

        self.number = int(0)
        self.quasidegree = 2

        self.citation = ''
        self.credit = ''

        self.title = "not really the title"
        self.texname = "LLLLLLL"
        self.texnamecompleteds = "AAAAAAA"
        self.texnamecompleted1ms = "BBBBBBB"
        # Extract the L-function information
        # The data are stored in a database, so extract it and then convert
        # to the format expected by the L-function homepage template.

        self.lfunc_data = LfunctionDatabase.getGenus2Ldata(isoclass['hash'])
        makeLfromdata(self)

        # Need an option for the arithmetic normalization, leaving the
        # analytic normalization as the default.
        self.texname = "L(s,A)"
        self.texname_arithmetic = "L(A,s)"
        self.texnamecompleteds = "\\Lambda(s,A)"
        self.texnamecompleted1ms = "\\Lambda(1-s,A)"
        self.texnamecompleteds_arithmetic = "\\Lambda(A,s)"
        self.texnamecompleted1ms_arithmetic = "\\Lambda(A, " + str(self.motivic_weight + 1) + "-s)"
#        self.title = ("$L(s,A)$, " + "where $A$ is genus 2 curve "
#                      + "of conductor " + str(isoclass['cond']))
        self.title_end = ("where $A$ is a genus 2 curve "
                      + "of conductor " + str(isoclass['cond']))
        self.title_arithmetic = "$" + self.texname_arithmetic + "$" + ", " + self.title_end
        self.title = "$" + self.texname + "$" + ", " + self.title_end

        constructor_logger(self, args)

    def Ltype(self):
        return "genus2curveQ"
        
    def Lkey(self):
        return {"label", self.label}


#############################################################################


# class GaloisRepresentationLfunction(Lfunction, GaloisRepresentation):
#    """
#    Class representing the L-function of a general galois representation
#    This is mainly used for twisting two such constructed from other
#    classes above.
#
#    Most of the values are inherited from GaloisRepresentation, where
#    things are done a bit more systematic.
#    """
#
# This is implemented in lmfdb.tensor_products.galois_reps instead.

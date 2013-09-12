# -*- coding: utf-8 -*-
# The class Lfunction is defined in Lfunction_base and represents an L-function
# We subclass it here:
# RiemannZeta, Lfunction_Dirichlet, Lfunction_EC_Q, Lfunction_EMF,
# Lfunction_HMF, Lfunction_Maass, Lfunction_SMF2_scalar_valued,
# DedekindZeta, ArtinLfunction, SymmetricPowerLfunction

from lmfdb import base
import math
from Lfunctionutilities import (seriescoeff,
                                compute_local_roots_SMF2_scalar_valued,
                                compute_dirichlet_series,
                                number_of_coefficients_needed,
                                signOfEmfLfunction)
from LfunctionComp import (nr_of_EC_in_isogeny_class, modform_from_EC,
                           EC_from_modform)
import LfunctionLcalc
from lmfdb.lfunctions import logger
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
from sage.rings.rational import Rational
import re
import pymongo
import bson
from lmfdb.WebCharacter import WebCharacter
from lmfdb.WebNumberField import WebNumberField

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import *
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db \
     import MaassDB
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_classes \
     import WebMaassForm
from Lfunction_base import Lfunction

def constructor_logger(object, args):
    ''' Executed when a object is constructed for debugging reasons
    '''
    logger.info(str(object.__class__) + str(args))



def generateSageLfunction(L):
    """ Generate a SageLfunction to do computations
    """
    from lmfdb.lfunctions import logger
    logger.info("Generating Sage Lfunction with parameters %s and coefficients (maybe shortened in this msg, but there are %s) %s"
                % ([L.title, L.coefficient_type, L.coefficient_period,
                L.Q_fe, L.sign, L.kappa_fe, L.lambda_fe,
                L.poles, L.residues], len(L.dirichlet_coefficients),
                L.dirichlet_coefficients[:20]))
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
        self.coefficient_period = 0
        self.poles = []
        self.residues = []
        self.kappa_fe = []
        self.lambda_fe = []
        self.mu_fe = []
        self.nu_fe = []
        self.selfdual = False
        self.langlands = True
        self.texname = "L(s)"  # default, will be set later in many cases
        self.texnamecompleteds = "\\Lambda(s)"  # default, often set later
        self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"  
        self.primitive = True  # should be changed later
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
                    self.filecontents = urllib.urlopen(self.url).read()
                except:
                    raise Exception("Wasn't able to read the file at the url")
            else:
                raise Exception("You forgot to supply an url.")

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
        curves = base.getDBConnection().elliptic_curves.curves
        Edata = curves.find_one({'lmfdb_label': self.label + '1'})
        if Edata is None:
            raise KeyError('No elliptic curve with label %s exists in the database' % self.label)
        else:
            self.E = EllipticCurve([int(a) for a in Edata['ainvs']])

        # Extract the L-function information from the elliptic curve
        self.quasidegree = 1
        self.level = self.E.conductor()
        self.Q_fe = float(sqrt(self.level) / (2 * math.pi))
        self.sign = self.E.lseries().dokchitser().eps
        self.kappa_fe = [1]
        self.lambda_fe = [0.5]
        self.numcoeff = round(self.Q_fe * 220 + 10)
        # logger.debug("numcoeff: {0}".format(self.numcoeff))
        self.mu_fe = []
        self.nu_fe = [Rational('1/2')]
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

        self.dirichlet_coefficients_unnormalized = (
            self.dirichlet_coefficients[:])
        self.normalize_by = Rational('1/2')

        # Renormalize the coefficients
        for n in range(0, len(self.dirichlet_coefficients) - 1):
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

        # Check for compulsory arguments
        if not ('weight' in args.keys() and 'level' in args.keys()):
            raise KeyError("You have to supply weight and level for an " +
                           "elliptic modular form L-function")
        logger.debug(str(args))
        self.addToLink = ''  # This is to take care of the case where
                             # character and/or label is not given
        # Initialize default values
        if not args['character']:
            args['character'] = 0  # Trivial character is default
            self.addToLink = '/0'
        if not args['label']:
            args['label'] = 'a'      # No label, OK If space is one-dimensional
            self.addToLink += '/a'
        if not args['number']:
            args['number'] = 0     # Default choice of embedding of the
                                   # coefficients
            self.addToLink += '/0'

        modform_translation_limit = 101

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.algebraic = True
        # logger.debug(str(self.character)+str(self.label)+str(self.number))
        self.weight = int(self.weight)
        self.motivic_weight = self.weight - 1
        self.level = int(self.level)
        self.character = int(self.character)
        # if self.character > 0:
        # raise KeyError, "The L-function of a modular form with non-trivial
        # character has not been implemented yet."
        self.number = int(self.number)

        # Create the modular form
        try:
            self.MF = WebNewForm(self.weight, self.level, self.character,
                                 self.label, verbose=1)
        except:
            raise KeyError("No data available yet for this modular form, so" +
                           " not able to compute its L-function")
        # Extract the L-function information from the elliptic modular form
        self.automorphyexp = float(self.weight - 1) / float(2)
        self.Q_fe = float(sqrt(self.level) / (2 * math.pi))
        # logger.debug("ALeigen: " + str(self.MF.atkin_lehner_eigenvalues()))

        self.kappa_fe = [1]
        self.lambda_fe = [self.automorphyexp]
        self.mu_fe = []
        self.nu_fe = [Rational(str(self.weight - 1) + '/2')]
        self.selfdual = True
        self.langlands = True
        self.primitive = True
        self.degree = 2
        self.poles = []
        self.residues = []
        self.numcoeff = 20 + int(5 * math.ceil(  # Testing NB: Need to learn
            self.weight * sqrt(self.level)))     # how to use more coefficients
        self.algebraic_coefficients = []

        # Get the data for the corresponding elliptic curve if possible
        if self.level <= modform_translation_limit and self.weight == 2:
            self.ellipticcurve = EC_from_modform(self.level, self.label)
            self.nr_of_curves_in_class = nr_of_EC_in_isogeny_class(
                                                    self.ellipticcurve)
        else:
            self.ellipticcurve = False

        # Appending list of Dirichlet coefficients
        GaloisDegree = self.MF.degree()  # number of forms in the Galois orbit
        if GaloisDegree == 1:
            # when coeffs are rational, q_expansion_embedding()
            # is the list of Fourier coefficients
            self.algebraic_coefficients = self.MF.q_expansion_embeddings(
                self.numcoeff + 1)[1:self.numcoeff + 1] 
                                                   
            self.coefficient_type = 2 # In this case, the L-function also comes
                                      # from an elliptic curve. We tell that to
                                      # lcalc, even if the coefficients are not
                                      # produced using the elliptic curve
        else:
            # logger.debug("Start computing coefficients.")

            embeddings = self.MF.q_expansion_embeddings(self.numcoeff + 1)
            for n in range(1, self.numcoeff + 1):
                self.algebraic_coefficients.append(embeddings[n][self.number])
                
            # In this case the coefficients are neither periodic nor coming
            # from an elliptic curve so
            self.coefficient_type = 0
            
        self.dirichlet_coefficients = []
        for n in range(1, len(self.algebraic_coefficients) + 1):
            self.dirichlet_coefficients.append(
                self.algebraic_coefficients[n - 1] /
                float(n ** self.automorphyexp))

        if self.level == 1:  # For level 1, the sign is always plus
            self.sign = 1
        else:  # for level>1, calculate sign from Fricke involution and weight
            if self.character > 0:
                self.sign = signOfEmfLfunction(self.level, self.weight,
                                               self.algebraic_coefficients)
            else:
                self.sign = (self.MF.atkin_lehner_eigenvalues()[self.level]
                             * (-1) ** (float(self.weight / 2)))
        # logger.debug("Sign: " + str(self.sign))

        self.coefficient_period = 0

        self.quasidegree = 1

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

        self.citation = ''
        self.credit = ''

        generateSageLfunction(self)
        constructor_logger(self, args)

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
        C = base.getDBConnection()
        f = C.hmfs.forms.find_one({'label': self.label})
        if f is None:
            raise KeyError("There is no Hilbert modular form with that label")
        logger.debug(str(args))

        F = WebNumberField(f['field_label'])
        F_hmf = C.hmfs.fields.find_one({'label': f['field_label']})

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
        self.Q_fe = (float(sqrt(self.level)) / (2 * math.pi) **
                     (self.field_degree))

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

        self.kappa_fe = [1 for i in range(self.field_degree)]
        self.lambda_fe = [self.automorphyexp for i in range(self.field_degree)]
        self.mu_fe = []
        self.nu_fe = [self.automorphyexp for i in range(self.field_degree)]
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

        self.coefficient_period = 0  # HUH?
        self.coefficient_type = 0  # HUH?
        self.quasidegree = 1  # HUH?

        self.checkselfdual()

        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
        self.title = ("$L(s,f)$, " + "where $f$ is a holomorphic Hilbert cusp "
                      + "form with parallel weight " + str(self.weight)
                      + ", level norm " + str(f['level_norm'])
                      + ", and character "
                      + str(self.character))

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
        self.Q_fe = float(1 / sqrt(math.pi))
        self.sign = 1
        self.kappa_fe = [0.5]
        self.lambda_fe = [0]
        self.mu_fe = [0]
        self.nu_fe = []
        self.langlands = True
        self.degree = 1
        self.level = 1
        self.dirichlet_coefficients = []
        for n in range(self.numcoeff):
            self.dirichlet_coefficients.append(1)
        self.poles = [0, 1]
        self.residues = [-1, 1]
        self.poles_L = [1]  # poles of L(s), used by createLcalcfile_ver2
        self.residues_L = [1]  # residues of L(s) createLcalcfile_ver2
        self.coefficient_period = 0
        self.selfdual = True
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
        self.web_chi = WebCharacter({'type': 'dirichlet',
                                     'modulus': self.charactermodulus,
                                     'number': self.characternumber})
        chi = self.web_chi.chi_sage
        self.chi_sage = chi
        self.motivic_weight = 0

        if chi.is_primitive():

            # Extract the L-function information from the Dirichlet character
            # Warning: will give nonsense if character is not primitive
            aa = int((1 - chi(-1)) / 2)   # usually denoted \frak a
            self.quasidegree = 1
            self.Q_fe = float(sqrt(self.charactermodulus) / sqrt(math.pi))
            self.sign = 1 / (I ** aa * float(sqrt(self.charactermodulus)) /
                             (chi.gauss_sum_numerical()))
            self.kappa_fe = [0.5]
            self.lambda_fe = [0.5 * aa]
            self.mu_fe = [aa]
            self.nu_fe = []
            self.langlands = True
            self.primitive = True
            self.degree = 1
            self.coefficient_period = self.charactermodulus
            self.level = self.charactermodulus
            self.numcoeff = self.coefficient_period

            self.dirichlet_coefficients = []
            for n in range(1, self.numcoeff):
                self.dirichlet_coefficients.append(chi(n).n())

            self.poles = []
            self.residues = []

            # Determine if the character is real
            # (i.e., if the L-function is selfdual)
            chivals = chi.values_on_gens()
            self.selfdual = True
            for v in chivals:
                if abs(imag_part(v)) > 0.0001:
                    self.selfdual = False

            if self.selfdual:
                self.coefficient_type = 1
                for n in range(0, self.numcoeff - 1):
                    self.dirichlet_coefficients[n] = int(
                        round(self.dirichlet_coefficients[n]))
            else:
                self.coefficient_type = 2

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

            self.sageLfunction = lc.Lfunction_from_character(chi)

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

        # Initialize default values
        self.dbName = 'MaassWaveForm'    # Set default database
        self.dbColl = 'HT'               # Set default collection

        # Put the arguments into the object dictionary
        self.__dict__.update(args)

        self.algebraic = False
        # Fetch the information from the database
        if self.dbName == 'Lfunction':  # Data from Lemurell

            connection = base.getDBConnection()
            db = pymongo.database.Database(connection, self.dbName)
            collection = pymongo.collection.Collection(db, self.dbColl)
            dbEntry = collection.find_one({'_id': self.dbid})

            # Extract the L-function information from the database entry
            self.__dict__.update(dbEntry)
            # Kludge to deal with improperly formatted SL or GL in the database
            # Current database entries only have SL in titles.  Note, this
            # will break for PSL or PGL.  Ideally, the database entries
            # should be changed.
            self.title = re.sub(r'(?<!\\)SL', r'\SL', self.title)
            self.title = re.sub(r'(?<!\\)GL', r'\GL', self.title)

            self.coefficient_period = 0
            self.poles = []
            self.residues = []

            # Extract the L-function information
            # from the lcalfile in the database
            import LfunctionLcalc
            LfunctionLcalc.parseLcalcfile_ver1(self, self.lcalcfile)

        else:  # GL2 data from Then or Stromberg

            host = base.getDBConnection().host
            port = base.getDBConnection().port
            DB = MaassDB(host=host, port=port)
            logger.debug("count={0}".format(DB.count()))
            logger.debug(self.dbid)
            self.mf = WebMaassForm(DB, self.dbid, get_dirichlet_c_only=1)
            self.group = 'GL2'
            logger.debug(self.mf.R)
            logger.debug(self.mf.symmetry)
            # Extract the L-function information from the Maass form object
            self.symmetry = self.mf.symmetry
            self.eigenvalue = float(self.mf.R)

            self.level = int(self.mf.level)
            self.charactermodulus = self.level

            self.weight = int(self.mf.weight)
            self.characternumber = int(self.mf.character)

            # We now use the Conrey naming scheme for characters
            # in Maass forms too.
            # if self.characternumber <> 1:
            #    raise KeyError, 'TODO L-function of Maass form with
            #                   non-trivial character not implemented. '

            if self.level > 1:
                try:
                    self.fricke = self.mf.cusp_evs[1]
                    logger.info("Fricke: {0}".format(self.fricke))
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
            self.selfdual = True
            self.primitive = True
            self.quasidegree = 2
            self.Q_fe = float(sqrt(self.level)) / float(math.pi)

            logger.debug("Symmetry: {0}".format(self.symmetry))
            if self.symmetry == "odd" or self.symmetry == 1:
                self.sign = -1
                aa = 1
            else:
                self.sign = 1
                aa = 0

            logger.debug("Sign (without Fricke): {0}".format(self.sign))
            if self.level > 1:
                self.sign = self.fricke * self.sign
            logger.debug("Sign: {0}".format(self.sign))

            self.kappa_fe = [0.5, 0.5]
            self.lambda_fe = [0.5 * aa + self.eigenvalue *
                              I / 2, 0.5 * aa - self.eigenvalue * I / 2]
            self.mu_fe = [aa + self.eigenvalue * I, aa - self.eigenvalue * I]
            self.nu_fe = []
            self.langlands = True
            self.degree = 2
            self.poles = []
            self.residues = []
            self.coefficient_period = 0

            self.checkselfdual()

            self.texname = "L(s,f)"
            self.texnamecompleteds = "\\Lambda(s,f)"

            if self.selfdual:
                self.texnamecompleted1ms = "\\Lambda(1-s,f)"
            else:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"

            if self.characternumber != 1:
                characterName = (" character \(\chi_{%s}(%s,\cdot)\)"
                                 % (self.level, self.characternumber))
            else:
                characterName = " trivial character"
            self.title = ("$L(s,f)$, where $f$ is a Maass cusp form with "
                          + "level %s, eigenvalue %s, and %s" % (
                          self.level, self.eigenvalue, characterName))
            self.citation = ''
            self.credit = ''

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

        self.Q_fe = float(sqrt(self.level) / 
                        (2 ** (self.signature[1]) * (math.pi) **
                        (float(self.degreeofN) / 2.0)))

        self.kappa_fe = self.signature[0] * [0.5] + self.signature[1] * [1]
        self.lambda_fe = self.quasidegree * [0]
        self.mu_fe = self.signature[0] * [0]  # not in use?
        self.nu_fe = self.signature[1] * [0]  # not in use?
        self.langlands = True
        # self.degree = self.signature[0] + 2 * self.signature[1] # N = r1 +2r2
        self.degree = self.degreeofN
        self.dirichlet_coefficients = [Integer(x) for x in
                                       self.NF.zeta_coefficients(5000)]
        self.h = wnf.class_number()  # self.NF.class_number()
        self.R = wnf.regulator()  # self.NF.regulator()
        self.w = len(self.NF.roots_of_unity())
        # r1 = self.signature[0]
        self.res = RR(2 ** self.signature[0] * self.h * self.R / self.w)  
        self.grh = wnf.used_grh()
        if self.degree > 1:
            if wnf.is_abelian():
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
        self.coefficient_type = 0
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

    Compulsory parameters: label, for instance 'A2.2.2.2_B1.1.1.1_t1.2'
    """
    def __init__(self, **args):
        constructor_logger(self, args)
        if not ('label' in args.keys()):
            raise KeyError("You have to supply a label for a hypergeometric motive L-ffunction")            
        C = base.getDBConnection()
        self.motive = C.hgm.motives_copy.find_one({"label": args["label"]})
        
        self.label = args["label"]
        import operator
        self.conductor = reduce(operator.__mul__, map(lambda x, y: x**y , self.motive["conductor"]))
        self.factored_conductor = self.motive["conductor"]
        self.level = self.conductor
        self.title = ("L function for the hypergeometric motive with label  "
                      + str(label))

        self.credit = 'Data precomputed by Dave Roberts'
        self.citation = 'MAGMA package hypergeometric due to Mark Watkins'
        
        self.motivic_weight = 0
        self.algebraic = True
        self.coefficient_type = 0
        self.degree = self.motive["degree"]
        
        try:
            self.arith_coeffs = self.motive["arith_coeff"]
        except:
            self.arith_coeffs = map(Integer, self.motive["arith_coeff_string"])

        self.support = "Support by Paul-Olivier Dehaye"
        
        self.sign = self.motive.sign
        
        
        # level, residues, selfdual, primitive, langlands, Q_fe, kappa_fe, lambda_fe?
        
        # Hardcoded for 'A2.2.2.2_B1.1.1.1_t1.2'
        self.mu_fe = []                     
        self.nu_fe = [0.5,1.5]              

        self.texname = "L(s)"  
        self.texnamecompleteds = "\\Lambda(s)"  
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s)" 
        else:
            self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"
        generateSageLfunction(self)

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
        if not ('dimension' in args.keys() and 'conductor' in args.keys() and
                'tim_index' in args.keys()):
            raise KeyError("You have to supply dimension, conductor and " +
                           "tim_index for an Artin L-function")    
        
        from lmfdb.math_classes import ArtinRepresentation
        self.dimension = args["dimension"]
        self.conductor = args["conductor"]
        self.tim_index = args["tim_index"]
        self.artin = ArtinRepresentation(self.dimension,
                                         self.conductor, self.tim_index)

        self.title = ("L function for an Artin representation of dimension "
                      + str(dimension) + ", conductor " + str(conductor))

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

        # self.Q_fe = (Integer(self.artin.conductor())/float(math.pi)**
                        # int(self.degree))
        self.Q_fe = (sqrt(Integer(self.artin.conductor()) * 1. /
                          float(math.pi) ** int(self.degree)))
        self.sign = self.artin.root_number()
        self.kappa_fe = self.artin.kappa_fe()
        self.lambda_fe = self.artin.lambda_fe()
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
            logger.debug(self.m)
        except TypeError:
            raise TypeError("The power has to be an integer")
        if self.underlying_type != 'EllipticCurve' or self.field != 'Q':
            raise TypeError("The symmetric L-functions have been implemented " +
                            "only for Elliptic Curves over Q")

        # Create the elliptic curve
        self.algebraic = True
        curves = base.getDBConnection().elliptic_curves.curves
        Edata = curves.find_one({'lmfdb_label': self.label + '1'})
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
        self.title = ("The Symmetric %s $L$-function $L(s,E,\mathrm{sym}^%d)$ of Elliptic Curve Isogeny Class %s"
                      % (ordinal(self.m), self.m, self.label))

        self.dirichlet_coefficients = self.S._coeffs

        self.sageLfunction = self.S._construct_L()

        # Initialize some default values
        self.coefficient_period = 0
        self.degree = self.m + 1
        self.Q_fe = self.S._Q_fe
        self.poles = self.S._poles
        self.residues = self.S._residues
        self.mu_fe = self.S._mu_fe
        self.nu_fe = self.S._nu_fe
        self.kappa_fe = self.mu_fe
        self.lambda_fe = self.nu_fe
        self.sign = self.S.root_number
        self.motivic_weight = self.m
        self.selfdual = True
        self.langlands = True
        self.texname = "L(s, E, \mathrm{sym}^%d)" % self.m  
        self.texnamecompleteds = "\\Lambda(s,E,\mathrm{sym}^{%d})" % self.S.m
        self.texnamecompleted1ms = ("\\Lambda(1-{s}, E,\mathrm{sym}^{%d})"
                                    % self.S.m)
        self.primitive = True  
        self.citation = ' '
        self.credit = ' '
        self.level = self.S.conductor
        self.euler = ("\\begin{align} L(s,E, \\mathrm{sym}^{%d}) = & \\prod_{p \\nmid %d } \\prod_{j=0}^{%d} \\left(1- \\frac{\\alpha_p^j\\beta_p^{%d-j}}{p^{s}} \\right)^{-1} "
                      % (self.m, self.E.conductor(),self.m, self.m))
        for p in self.S.bad_primes:
            poly = self.S.eulerFactor(p)
            poly_string = " "
            if len(poly) > 1:
                poly_string = "\\\\ & \\times (1"
                if poly[1] != 0:
                    if poly[1] == 1:
                        poly_string += "+%d^{ -s}" % p
                    elif poly[1] == -1:
                        poly_string += "-%d^{- s}" % p
                    elif poly[1] < 0:
                        poly_string += "%d\\ %d^{- s}" % (poly[1], p)
                    else:
                        poly_string += "+%d\\ %d^{- s}" % (poly[1], p)

                for j in range(2, len(poly)):
                    if poly[j] == 0:
                        continue
                    if poly[j] == 1:
                        poly_string += "%d^{-%d s}" % (p, j)
                    elif poly[j] == -1:
                        poly_string += "-%d^{-%d s}" % (p, j)
                    elif poly[j] < 0:
                        poly_string += "%d \\ %d^{-%d s}" % (poly[j], p, j)
                    else:
                        poly_string += "+%d\\ %d^{-%d s}" % (poly[j], p, j)
                poly_string += ")^{-1}"
            self.euler += poly_string
        self.euler += "\\end{align}"

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
        self.number = int(self.number)

        # Load the eigenvalues
        if (self.weight == 20 or self.weight == 22 or self.weight == 24 or
                self.weight == 26) and self.orbit[0] == 'U':
            loc = ("http://data.countnumber.de/Siegel-Modular-Forms/Sp4Z/xeigenvalues/"
                    + str(self.weight) + "_" + self.orbit + "-ev.sobj")

        else:
            loc = ("http://data.countnumber.de/Siegel-Modular-Forms/Sp4Z/eigenvalues/"
                   + str(self.weight) + "_" + self.orbit + "-ev.sobj")

        # logger.debug(loc)
        self.ev_data = load(loc)

        print self.ev_data

        self.automorphyexp = float(self.weight) - float(1.5)
        self.Q_fe = float(1 / (4 * math.pi ** 2))  # the Q in the FE as in lcalc

        self.sign = (-1) ** float(self.weight)

        self.level = 1
        self.degree = 4
        # logger.debug(str(self.degree))

        roots = compute_local_roots_SMF2_scalar_valued(
            self.ev_data, self.weight,
            self.number)  # compute the roots of the Euler factors

        # logger.debug(str(self.ev_data))
        self.numcoeff = max([a[0] for a in roots])  # include a_0 = 0
        self.dirichlet_coefficients = compute_dirichlet_series(
            roots, self.numcoeff)  # these are in the analytic normalization
        # the coefficients from Gamma(ks+lambda)
        self.kappa_fe = [1, 1]  
        self.lambda_fe = [float(1) / float(2), self.automorphyexp]  
        self.mu_fe = []  # the shifts of the Gamma_R to print

        self.nu_fe = [float(1) / float(2), self.automorphyexp]  # the shift of
                                                                # the Gamma_C to print
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
        self.coefficient_type = 2
        self.quasidegree = 1

        # self.checkselfdual()

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

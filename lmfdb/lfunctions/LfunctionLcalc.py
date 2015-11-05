# Contains code for constructing and parsing lcalc files

import math
import time  # for printing the date on an lcalc file
import socket  # for printing the machine used to generate the lcalc file
from sage.all import Infinity, imag_part, real_part
from Lfunctionutilities import splitcoeff, pair2complex


def parse_complex_number(z):
    z_parsed = "(" + str(real_part(z)) + "," + str(imag_part(z)) + ")"
    return z_parsed

# Lcalc Version 2 ###########################################################


def createLcalcfile_ver2(L, url):
    thefile = ""
    thefile += "##########################################################################################################\n"
    thefile += "###\n"
    thefile += "### lcalc file for the url: " + url + "\n"
    thefile += "### This file assembled: " + time.asctime() + "\n"
    thefile += "### on machine: " + socket.gethostname() + "\n"
    thefile += "###\n"
    try:
        thefile += "###     type = %s\n" % L.Ltype()
        thefile += "### Data passed to lcalc wrapper, if it is used: \n"
        thefile += "###     title = %s \n" % L.title
        thefile += "###     coefficient_type = %s \n" % L.coefficient_type
        thefile += "###     dirichlet_coefficients = %s \n" % L.dirichlet_coefficients[:50]
        thefile += "###         (here limited to 50, but in reality %s are passed )\n" % len(
            L.dirichlet_coefficients)
        thefile += "###     coefficient_period = %s \n" % L.coefficient_period
        thefile += "###     Q_fe = %s \n" % L.Q_fe
        thefile += "###     sign = %s \n" % L.sign
        thefile += "###     kappa_fe = %s \n" % L.kappa_fe
        thefile += "###     lambda_fe = %s \n" % L.lambda_fe
        thefile += "###     poles = %s \n" % L.poles
        thefile += "###     residues = %s \n" % L.residues
    except AttributeError:
        pass
    thefile += "##########################################################################################################\n\n"
    thefile += "lcalcfile_version = 2    ### lcalc files should have a version number for future enhancements\n\n"

    thefile += """\
##########################################################################################################
### Specify the functional equation using the Gamma_R and Gamma_C
### notation. Let Gamma_R = pi^(-s/2) Gamma(s/2), and  Gamma_C = (2 pi)^(-s) Gamma(s).
###
### Let Lambda(s) :=
###
###                  a
###               --------'
###              '  |  |
###          s      |  |
###   sqrt(N)       |  |   Gamma_{R or C}(s + lambda_j)  L(s)
###                 |  |
###                j = 1
###
###                          ___________
###                                    _
### satisfy Lambda(s) = omega Lambda(1-s), where N is a positive integer, |omega|=1,
### Each of the Gamma factors can be a Gamma_R or Gamma_C.

### Specify the conductor. Other possible keywords: N, level."""

# omega, and Gamma_R and Gamma_C factors:"""
    thefile += "\n\n"
    thefile += "conductor = " + str(L.level) + "\n\n"

    thefile += "### Specify the sign of the functional equation.\n"
    thefile += "### Complex numbers should be specified as:\n"
    thefile += "### omega = (Re(omega),Im(omega)). Other possible keyword: sign\n\n"
    if L.selfdual:
        thefile += "omega = " + str(L.sign) + "\n\n"
    else:
        thefile += "omega = " + parse_complex_number(L.sign) + "\n\n"

    thefile += "### Gamma_{R or C}_list lists the associated lambda_j's. Lines with empty lists can be omitted.\n\n"
    thefile += "Gamma_R_list = " + str(L.mu_fe) + "\n"
    thefile += "Gamma_C_list = " + str(L.nu_fe) + "\n\n"

    thefile += """\
##########################################################################################################
### Specify, as lists, the poles and residues of L(s) in Re(s)>1/2 (i.e. assumes that there are no
### poles on s=1/2). Also assumes that the poles are simple. Lines with empty lists can be omitted."""
    thefile += "\n\n"
    if hasattr(L, 'poles_L'):
        thefile += "pole_list = " + str(L.poles_L) + "\n"
    else:
        thefile += "pole_list = []\n"

    if hasattr(L, 'residues_L'):
        thefile += "residue_list = " + str(L.residues_L) + "\n\n"
    else:
        thefile += "residue_list = []\n\n"

    thefile += """\
##########################################################################################################
### Optional:"""

    thefile += "\n\n"

    thefile += "name = \"" + url.partition('/L/')[2].partition('?download')[0].strip('/') + "\"\n"
    kind = url.partition('/L/')[2].partition('?download')[0].partition('/')[0]
    kind_of_L = url.partition('/L/')[2].partition('?download')[0].split('/')
    # thefile += str(kind_of_L) + "\n\n\n\n"
    if len(kind_of_L) > 2:
        thefile += "kind = \"" + kind_of_L[0] + "/" + kind_of_L[1] + "\"\n\n"
    elif len(kind_of_L) == 2:
        thefile += "kind = \"" + kind_of_L[0] + "\"\n\n"

    thefile += """\
##########################################################################################################
### Specify the Dirichlet coefficients, whether they are periodic
### (relevant for Dirichlet L-functions), and whether to normalize them
### if needed to get a functional equation s <--> 1-s
###
### periodic should be set to either True (in the case of Dirichlet L-functions,
### for instance), or False (the default). If True, then lcalc assumes that the coefficients
### given, a[0]...a[N], specify all a[n] with a[n]=a[m] if n=m mod (N+1).
### For example, for the real character mod 4, one should,
### have periodic = True and at the bottom of this file, then specify:
### dirichlet_coefficient =[
### 0,
### 1,
### 0,
### -1
### ]
###
### Specify whether Dirichlet coefficients are periodic:"""
    thefile += "\n\n"
    if(L.coefficient_period != 0 or hasattr(L, 'is_zeta')):
        thefile += "periodic = True\n\n"
    else:
        thefile += "periodic = False\n\n"

    thefile += """\
##########################################################################################################
### The default is to assume that the Dirichlet coefficients are provided
### normalized so that the functional equation is s <--> 1-s, i.e. `normalize_by'
### is set to 0 by default.
###
### Sometimes, such as for an elliptic curve L-function, it is more convenient to
### record the Dirichlet coefficients normalized differently, for example, as
### integers rather than as floating point approximations.
###
### For example, an elliptic curve L-function is assumed by lcalc to be of the
### form:
###
###     L(s) = sum (a(n)/n^(1/2)) n^(-s),
###
### i.e. to have Dirichlet coefficients a(n)/n^(1/2) rather than a(n),
### where a(p) = p+1-#E(F_p), and functional equation of the form
###
###     Lambda(s):=(sqrt(N)/(2 pi))^s Gamma(s+1/2) L(s) = omega Lambda(1-s),
###
### where omega = \pm 1.
###
### So, the normalize_by variable is meant to allow the convenience, for example,
### of listing the a(n)'s rather than the a(n)/sqrt(n)'s."""
    thefile += "\n\n"

    if hasattr(L, 'normalize_by'):
        thefile += "normalize_by = " + str(L.normalize_by) + "    ### floating point is also okay.\n"
        thefile += "### Normalize, below, the n-th Dirichlet coefficient by n^(" + str(
            L.normalize_by) + ")\n\n"
    else:
        thefile += "normalize_by = 0    # the default, i.e. no normalizing\n\n"

    thefile += """\
##########################################################################################################
### The last entry must be the dirichlet_coefficient list, one coefficient per
### line, separated # by commas. The 0-th entry is ignored unless the Dirichlet
### coefficients are periodic. One should always include it, however, because, in
### computer languages such as python, the 0-th entry is the `first' entry of an
### array. Since this file is meant to be compatible also with python, we assume
### that the 0-th entry is also listed.
###
### Complex numbers should be entered, as usual as a pair of numbers, separated
### by a comma. If no complex numbers appear amongst the Dirichlet coefficients,
### lcalc will assume the L-function is self-dual."""
    thefile += "\n\n"

    thefile += "Dirichlet_coefficient = [\n"

    if hasattr(L, 'is_zeta'):
        thefile += "1    ### the Dirichlet coefficients of zeta are all 1\n]\n"

    else:
        thefile += "0,\t\t\t### set Dirichlet_coefficient[0]\n"
        if L.coefficient_period == 0:
            period = Infinity
        else:
            period = L.coefficient_period

        if hasattr(L, 'dirichlet_coefficients_arithmetic'):
            total = min(len(L.dirichlet_coefficients_arithmetic), period - 1)
            for n in range(0, total):
                if L.selfdual:
                    thefile += str(L.dirichlet_coefficients_arithmetic[n])
                else:
                    thefile += parse_complex_number(L.dirichlet_coefficients_arithmetic[n])
                if n < total - 1:           # We will be back
                    thefile += ","
                if n < 2:
                    thefile += "\t\t\t### set Dirichlet_coefficient[" + str(n + 1) + "] \n"
                else:
                    thefile += "\n"
        else:
            total = min(len(L.dirichlet_coefficients), period - 1)
            for n in range(0, total):
                if L.selfdual:
                    thefile += str(L.dirichlet_coefficients[n])
                else:
                    thefile += parse_complex_number(L.dirichlet_coefficients[n])
                if n < total - 1:           # We will be back
                    thefile += ","
                if n < 2:
                    thefile += "\t\t\t### set Dirichlet_coefficient[" + str(n + 1) + "] \n"
                else:
                    thefile += "\n"
        # thefile = thefile[:-2]
        thefile += "]\n"

    return(thefile)


# Lcalc Version 1 ###########################################################
def parseLcalcfile_ver1(L, filecontents):
    """ Extracts informtion from the lcalcfile, version 1
    """

    lines = filecontents.split('\n', 6)
    L.coefficient_type = int(lines[0])
    # Rishi tells me that for his wrapper
    # 0 is for general, 1 is for periodic and 2 is for elliptic curves.
    # Mike seems to only use 0 and 1.
    # POD
    L.quasidegree = int(lines[4])
    lines = filecontents.split('\n', 8 + 2 * L.quasidegree)
    L.Q_fe = float(lines[5 + 2 * L.quasidegree])
    L.sign = pair2complex(lines[6 + 2 * L.quasidegree])

    L.kappa_fe = []
    L.lambda_fe = []
    L.mu_fe = []
    L.nu_fe = []

    for i in range(L.quasidegree):
        localdegree = float(lines[5 + 2 * i])
        L.kappa_fe.append(localdegree)
        locallambda = pair2complex(lines[6 + 2 * i])
        L.lambda_fe.append(locallambda)
        if math.fabs(localdegree - 0.5) < 0.00001:
            L.mu_fe.append(2 * locallambda)
        elif math.fabs(localdegree - 1) < 0.00001:
            L.nu_fe.append(locallambda)
        else:
            L.nu_fe.append(locallambda)
            L.langlands = False

    """ Do poles here later
    """

    L.degree = int(round(2 * sum(L.kappa_fe)))

    L.level = int(round(math.pi ** float(L.degree) * 4 ** len(L.nu_fe) * L.Q_fe ** 2))
    # note:  math.pi was not compatible with the sage type of degree

    L.dirichlet_coefficients = splitcoeff(lines[-1])


def createLcalcfile_ver1(L):
    """ Creates the lcalcfile of L, version 1
    """

    thefile = ""
    if L.selfdual:
        thefile += "2\n"  # 2 means real coefficients
    else:
        thefile += "3\n"  # 3 means complex coefficients

    thefile += "0\n"  # 0 means unknown type

    thefile += str(len(L.dirichlet_coefficients)) + "\n"

    thefile += "0\n"  # assume the coefficients are not periodic

    thefile += str(L.quasidegree) + "\n"  # number of actual Gamma functions

    for n in range(0, L.quasidegree):
        thefile = thefile + str(L.kappa_fe[n]) + "\n"
        thefile = thefile + str(real_part(L.lambda_fe[n])) + " " + str(imag_part(L.lambda_fe[n])) + "\n"

    thefile += str(real_part(L.Q_fe)) + "\n"

    thefile += str(real_part(L.sign)) + " " + str(imag_part(L.sign)) + "\n"

    thefile += str(len(L.poles)) + "\n"  # counts number of poles

    for n in range(0, len(L.poles)):
        thefile += str(real_part(L.poles[n])) + " " + str(imag_part(L.poles[n])) + "\n"  # pole location
        thefile += str(
            real_part(L.residues[n])) + " " + str(imag_part(L.residues[n])) + "\n"  # residue at pole

    for n in range(0, len(L.dirichlet_coefficients)):
        thefile += str(real_part(L.dirichlet_coefficients[n]))   # add real part of Dirichlet coefficient
        if not L.selfdual:  # if not selfdual
            thefile += " " + str(imag_part(L.dirichlet_coefficients[n]))
                                 # add imaginary part of Dirichlet coefficient
        thefile += "\n"

    return(thefile)

from flask import url_for
from sage.all import ZZ, is_prime, latex, imag_part
from Lfunctionutilities import (lfuncDShtml, lfuncEPtex, lfuncFEtex,
                                styleTheSign, specialValueString,
                                specialValueTriple)


#############################################################################
# The base Lfunction class. The goal is to make this dependent on the least
# possible, so it can be loaded from sage or even python
# Please do not pollute with flask, postgres, logger or similar
#############################################################################

class Lfunction:
    """Class representing a general L-function
    """

    def Ltype(self):
        return self._Ltype

    def checkselfdual(self):
        """ Checks whether coefficients are real to determine
            whether L-function is selfdual
        """

        if not hasattr(self, 'selfdual'):
            self.selfdual = True
            for n in range(1, min(8, len(self.dirichlet_coefficients))):
                if abs(imag_part(self.dirichlet_coefficients[n] / self.dirichlet_coefficients[0])) > 0.00001:
                    self.selfdual = False

    def compute_kappa_lambda_Q_from_mu_nu(self):
        """ Computes some kappa, lambda and Q from mu, nu, which might not be optimal for computational purposes
        """
        try:
	    from sage.functions.other import sqrt 
            from sage.rings.all import Integer
            from math import pi
            self.Q_fe = float(sqrt(Integer(self.level))/2.**len(self.nu_fe)/pi**(len(self.mu_fe)/2.+len(self.nu_fe)))
            self.kappa_fe = [.5 for m in self.mu_fe] + [1. for n in self.nu_fe] 
            self.lambda_fe = [m/2. for m in self.mu_fe] + [n for n in self.nu_fe]
        except Exception as e:
            raise Exception("Expecting a mu and a nu to be defined"+str(e))


    ############################################################################
    ### other useful methods not implemented universally yet
    ############################################################################

    def compute_web_zeros(self, time_allowed = 10, **kwargs):
	""" A function that dispatches web computations to the correct tool"""
        # Do not pass 0 to either lower bound or step_size
        # Not dependent on time actually
        # Manual tuning required
        if (self.degree > 2 or self.Ltype() == "maass" or
            self.Ltype() == "hgmQ" or
            self.Ltype() == "artin" ):
            allZeros = self.compute_heuristic_zeros(**kwargs)
        else:
            allZeros = self.compute_checked_zeros(**kwargs)

        # Sort the zeros and divide them into negative and positive ones
        if not isinstance(allZeros,str):
            allZeros.sort()
        return allZeros

    def compute_checked_zeros(self, count = None, do_negative = False, **kwargs):
        if self.selfdual:
            count = count or 6
        else:
            count = count or 8
        return self.compute_lcalc_zeros(via_N = True, count = count, do_negative = do_negative or not self.selfdual)

    def compute_heuristic_zeros(self, step_size = 0.02, upper_bound = 20, lower_bound = None):
     #   if self.Ltype() == "hilbertmodularform":
        if self.Ltype() not in ["riemann", "maass"]:
            upper_bound = 10
        if self.selfdual:
            lower_bound = lower_bound or - step_size / 2
        else:
            lower_bound = lower_bound or -20
        return self.compute_lcalc_zeros(via_N = False, step_size = step_size, upper_bound = upper_bound, lower_bound = lower_bound)

    def compute_lcalc_zeros(self, via_N = True, **kwargs):

        if not hasattr(self,"fromDB"):
            self.fromDB = False

        if via_N == True:
            count = kwargs["count"]
            do_negative = kwargs["do_negative"]
            if self.fromDB:
                return "not available"
            if not self.sageLfunction:
                return "not available"
            return self.sageLfunction.find_zeros_via_N(count, do_negative)
        else:
            T1 = kwargs["lower_bound"]
            T2 = kwargs["upper_bound"]
            stepsize = kwargs["step_size"]
            if self.fromDB:
                return "not available"
            if not self.sageLfunction:
                return "not available"
            return self.sageLfunction.find_zeros(T1, T2, stepsize)

    def general_webpagedata(self):
        info = {}
        try:
            info['support'] = self.support
        except AttributeError:
            info['support'] = ''

        info['Ltype'] = self.Ltype()

        try:
            info['label'] = self.label
        except AttributeError:
            info['label'] = ""

        try:
            info['credit'] = self.credit
        except AttributeError:
            info['credit'] = ""

        info['degree'] = int(self.degree)
        info['conductor'] = self.level
        if not is_prime(int(self.level)):
            if self.level >= 10**8:
                info['conductor'] = latex(self.level_factored)
            else:
                info['conductor_factored'] = latex(self.level_factored)


        info['sign'] = "$" + styleTheSign(self.sign) + "$"
        info['algebraic'] = self.algebraic
        if self.selfdual:
            info['selfdual'] = 'yes'
        else:
            info['selfdual'] = 'no'
        if self.primitive:
            info['primitive'] = 'yes'
        else:
            info['primitive'] = 'no'
        info['dirichlet'] = lfuncDShtml(self, "analytic")
        # Hack, fix this more general?
        info['dirichlet'] = info['dirichlet'].replace('*I','<em>i</em>')

        info['eulerproduct'] = lfuncEPtex(self, "abstract")
        info['functionalequation'] = lfuncFEtex(self, "analytic")
        info['functionalequationSelberg'] = lfuncFEtex(self, "selberg")

        if hasattr(self, 'positive_zeros'):
            info['positive_zeros'] = self.positive_zeros
            info['negative_zeros'] = self.negative_zeros

        if hasattr(self, 'plot'):
            info['plot'] = self.plot

        if hasattr(self, 'factorization'):
            info['factorization'] = self.factorization

        if self.fromDB and self.algebraic:
            info['dirichlet_arithmetic'] = lfuncDShtml(self, "arithmetic")
            info['eulerproduct_arithmetic'] = lfuncEPtex(self, "arithmetic")
            info['functionalequation_arithmetic'] = lfuncFEtex(self, "arithmetic")

            if self.motivic_weight % 2 == 0:
               arith_center = "\\frac{" + str(1 + self.motivic_weight) + "}{2}"
            else:
               arith_center = str(ZZ(1)/2 + self.motivic_weight/2)
            svt_crit = specialValueTriple(self, 0.5, '\\frac12',arith_center)
            info['sv_critical'] = svt_crit[0] + "\\ =\\ " + svt_crit[2]
            info['sv_critical_analytic'] = [svt_crit[0], svt_crit[2]]
            info['sv_critical_arithmetic'] = [svt_crit[1], svt_crit[2]]

            if self.motivic_weight % 2 == 1:
               arith_edge = "\\frac{" + str(2 + self.motivic_weight) + "}{2}"
            else:
               arith_edge = str(ZZ(1) + self.motivic_weight/2)

            svt_edge = specialValueTriple(self, 1, '1',arith_edge)
            info['sv_edge'] = svt_edge[0] + "\\ =\\ " + svt_edge[2]
            info['sv_edge_analytic'] = [svt_edge[0], svt_edge[2]]
            info['sv_edge_arithmetic'] = [svt_edge[1], svt_edge[2]]

            chilatex = "$\chi_{" + str(self.charactermodulus) + "} (" + str(self.characternumber) +", \cdot )$"
            info['chi'] = ''
            if self.charactermodulus != self.level:
                info['chi'] += "induced by "
            info['chi'] += '<a href="' + url_for('characters.render_Dirichletwebpage', 
                                                    modulus=self.charactermodulus, number=self.characternumber)
            info['chi'] += '">' + chilatex + '</a>'

            info['st_group'] = self.st_group
            info['st_link'] = self.st_link
            info['rank'] = self.order_of_vanishing
            info['motivic_weight'] = r'\(%d\)' % self.motivic_weight

        elif self.Ltype() != "artin" or (self.Ltype() == "artin" and self.sign != 0):
            try:
                info['sv_edge'] = specialValueString(self, 1, '1')
                info['sv_critical'] = specialValueString(self, 0.5, '1/2')
            except:
                info['sv_critical'] = "L(1/2): not computed"
                info['sv_edge'] = "L(1): not computed"

        return info




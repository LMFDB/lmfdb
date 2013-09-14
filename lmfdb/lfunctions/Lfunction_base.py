from sage.all import imag_part

#############################################################################
# The base Lfunction class. The goal is to make this dependent on the least possible, so it can be loaded from sage or even python
# Please do not pollute with flask, pymongo, logger or similar
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

        self.selfdual = True
        for n in range(1, min(8, len(self.dirichlet_coefficients))):
            if abs(imag_part(self.dirichlet_coefficients[n] / self.dirichlet_coefficients[0])) > 0.00001:
                self.selfdual = False

    def Lkey(self):
        # Lkey should be a dictionary
        raise Error("not all L-function implement the Lkey scheme atm")

    def source_object(self):
        raise Error("not all L-functions give back a source object. This might be due to limited knowledge or missing code")

    def source_information(self):
        # Together, these give in principle enough to identify the object
        # In practice, might be better to require Ltype to be the constructor class and Lkey to be the argument to that constructor        
        return self.Ltype(), self.Lkey()
        

    def compute_mu_nu(self):
        raise NotImplementedError               # time-consuming to get exactly right
        
    def compute_standard_mu_nu(self):
        raise NotImplementedError               # time-consuming to get exactly right
    def compute_some_mu_nu(self):
        pairs_fe = zip(self.kappa_fe, self.lambda_fe)
        self.mu_fe = [lambda_fe/2. for kappa_fe, lambda_fe in pairs_fe if abs(kappa_fe - 0.5) < 0.001]
        self.nu_fe = [lambda_fe for kappa_fe, lambda_fe in pairs_fe if abs(kappa_fe - 1) < 0.001]
        
        
    def compute_kappa_lambda_Q_from_mu_nu(self):
        """ Computes some kappa, lambda and Q from mu, nu, which might not be optimal for computational purposes
        """
        try:
            self.Q_fe = float(sqrt(Integer(self.conductor))/2.**len(self.nu_fe)/pi**(len(self.mu_fe)/2.+len(self.nu_fe)))
            self.kappa_fe = [.5 for m in self.mu_fe] + [1. for n in self.nu_fe] 
            self.lambda_fe = [m/2. for m in self.mu_fe] + [n for n in self.nu_fe]
        except:
            Exception("Expecting a mu and a nu to be defined")
    
    def compute_lcalc_parameters_from_mu_nu(self):
        """ Computes some kappa, lambda and Q from mu, nu, which might not be optimal for computational purposes
            Ideally would be optimized
        """
        try:
            self.Q_fe = float(sqrt(Integer(self.conductor))/2**len(self.nu_fe)/pi**(len(self.mu_fe)/2.+len(self.nu_fe)))
            self.kappa_fe = [.5 for m in self.mu_fe] + [1. for n in self.nu_fe] 
            self.lambda_fe = [m/2. for m in self.mu_fe] + [n for n in self.nu_fe]
        except:
            Exception("Expecting a mu and a nu to be defined")
    
        
    ############################################################################
    ### other useful methods not implemented universally yet
    ############################################################################

    def compute_quick_zeros(self, time_allowed = 10, lower_bound = None, upper_bound = None, step_size = None, count = None, do_negative = False, **kwargs):
        # Do not pass 0 to either lower bound or step_size
        # Not dependent on time actually
        # Manual tuning required
        if self.degree > 2 or self.Ltype() == "maass":  # Too slow to be rigorous here  ( or self.Ltype()=="ellipticmodularform")
            step_size = 0.02
            if self.selfdual:
                lower_bound = lower_bound or - step_size / 2
            else:
                lower_bound = lower_bound or -20
            allZeros = self.compute_lcalc_zeros(via_N = False, step_size = step_size, upper_bound = upper_bound or 20, lower_bound = lower_bound)
        else:
            if self.selfdual:
                count = count or 6
            else:
                count = count or 8
            allZeros = self.compute_lcalc_zeros(via_N = True, count = count, do_negative = do_negative or not self.selfdual)
    
        # Sort the zeros and divide them into negative and positive ones
        allZeros.sort()
        return allZeros
    
    def compute_realistic_zeros(self, lower_bound = None, upper_bound = None, step_size = None, count = None, do_negative = False, **kwargs):
        # Do not pass 0 to either lower bound or step_size
        
        if self.degree > 2 or self.Ltype() == "maass":  # Too slow to be rigorous here  ( or self.Ltype()=="ellipticmodularform")
            step_size = 0.02
            if self.selfdual:
                lower_bound = lower_bound or - step_size / 2
            else:
                lower_bound = lower_bound or -20
            allZeros = self.compute_lcalc_zeros(via_N = False, step_size = step_size, upper_bound = upper_bound or 20, lower_bound = lower_bound)
        else:
            if self.selfdual:
                count = count or 6
            else:
                count = count or 8
            allZeros = self.compute_lcalc_zeros(via_N = True, count = count, do_negative = do_negative or not self.selfdual)
    
        # Sort the zeros and divide them into negative and positive ones
        allZeros.sort()
        return allZeros
    
    def compute_lcalc_zeros(self, via_N = True, **kwargs):
        if via_N == True:
            count = kwargs["count"]
            do_negative = kwargs["do_negative"]
            return self.sageLfunction.find_zeros_via_N(count, do_negative)
        else:
            T1 = kwargs["lower_bound"]
            T2 = kwargs["upper_bound"]
            stepsize = kwargs["step_size"]
            return self.sageLfunction.find_zeros(T1, T2, stepsize)
    
    def compute_zeros(algorithm , **kwargs):
        if algorithm == "realistic":
            return self.compute_realistic_zeros(self, **kwargs)
        if algorithm == "lcalc":
            return self.compute_lcalc_zeros(self, **kwargs)
        if algorithm == "quick":
            return self.compute_quick_zeros(self, **kwargs)
            

    def critical_value(self):
        pass

    def conductor(self, advocate):
        # Advocate could be IK, CFKRS or B
        pass
  

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
        
    def compute_kappa_lambda_from_mu_nu(self):
        """ Computes some kappa and lambda from mu, nu, which might not be optimal for computational purposes
        """
        try:
            self.kappa_fe = [.5 for m in self.mu_fe] + [1. for n in self.nu_fe] 
            self.lambda_fe = [m/2 for m in self.mu_fe] + [n for n in self.nu_fe]
            self.Q_fe = float(sqrt(self.conductor)/2**len(self.nu_fe)/pi**(len(self.mu_fe)/2+len(self.nu_fe)))
        except:
            Exception("Expecting a mu and a nu to be defined")
    
    def compute_lcalc_parameters_from_mu_nu(self):
        """ This should be made optimal, trying to group the kappas and lambdas that can be"""
        return self.compute_kappa_lambda_from_mu_nu()
    
    ############################################################################
    ### other useful methods not implemented universally yet
    ############################################################################

    def critical_value(self):
        pass

    def conductor(self, advocate):
        # Advocate could be IK, CFKRS or B
        pass
  

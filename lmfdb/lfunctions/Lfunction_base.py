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

        
    ############################################################################
    ### other useful methods not implemented universally yet
    ############################################################################

    def critical_value(self):
        pass

    def conductor(self, advocate):
        # Advocate could be IK, CFKRS or B
        pass
  

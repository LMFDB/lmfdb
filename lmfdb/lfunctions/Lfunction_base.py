

#############################################################################
# The base Lfunction class. The goal is to make this dependent on the least possible, so it can be loaded from sage or even python
# Please do not pollute with flask, pymongo, logger or similar
# and actually try to remove these dependencies from within methods
#############################################################################

class Lfunction:
    """Class representing a general L-function
    """

    def __init__(self, **args):
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
        self.texname = "L(s)"  # default name.  will be set later, for most L-functions
        self.texnamecompleteds = "\\Lambda(s)"  # default name.  will be set later, for most L-functions
        self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"  # default name.  will be set later, for most L-functions
        self.primitive = True  # should be changed later
        self.citation = ''
        self.credit = ''
        self.motivic_weight = NaN
        self.algebraic = True
        self.dirichlet_coefficients = []
        self._Ltype = "Lfunction"
        self._constructor_args = args

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

    def generateSageLfunction(self):
        """ Generate a SageLfunction to do computations
        """
        from lmfdb.lfunctions import logger
        logger.info("Generating Sage Lfunction with parameters %s and coefficients (maybe shortened in this msg, but there are %s) %s" % ([self.title, self.coefficient_type, self.coefficient_period, self.Q_fe, self.sign, self.kappa_fe, self.lambda_fe, self.poles, self.residues], len(self.dirichlet_coefficients), self.dirichlet_coefficients[:20]))
        import sage.libs.lcalc.lcalc_Lfunction as lc
        self.sageLfunction = lc.Lfunction_C(self.title, self.coefficient_type,
                                            self.dirichlet_coefficients,
                                            self.coefficient_period,
                                            self.Q_fe, self.sign,
                                            self.kappa_fe, self.lambda_fe,
                                            self.poles, self.residues)
                    # self.poles:           Needs poles of _completed_ L-function
                    # self.residues:        Needs residues of _completed_ L-function
                    # self.kappa_fe:        What ultimately appears if you do lcalc.lcalc_Lfunction._print_data_to_standard_output() as the gamma[1]
                    # self.lambda_fe:       What ultimately appears if you do lcalc.lcalc_Lfunction._print_data_to_standard_output() as the lambda[1]
                    # According to Rishi, as of March 2012 (sage <=5.0), the documentation to
                    # his wrapper is wrong

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
  
import pymongo
from sage.rings.integer import Integer
from sage.misc.sage_eval import sage_eval
import sage.structure.sage_object
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.integer_ring import IntegerRing


def find_sample( dct):

    # DB_URL = 'mongodb://localhost:40000/'
    # client = pymongo.MongoClient( DB_URL)
    import lmfdb.base
    client = lmfdb.base.getDBConnection()

    db = client.siegel_modular_forms
    smps = db.samples
    smple = smps.find_one( dct)
    client.close()
    return smple



class Sample (sage.structure.sage_object.SageObject):
    """

    """
    def __init__( self, collection, name):
        dct = { 'collection': collection, 'name': name}
        smple = find_sample( dct)
        assert smple, '%s: sample does not exist' % dct
        self.__collection = collection
        self.__name = name
        weight = smple.get( 'weight')
        field = smple.get( 'field')
        fcs = smple.get('Fourier_coefficients')
        evs = smple.get( 'eigenvalues')
        self.__weight = Integer( weight) if weight else weight
        R = PolynomialRing( IntegerRing(), name = 'x')
        self.__field = sage_eval( field, locals = R.gens_dict()) if field else field
        loc_f = self.__field.gens_dict()
        P = PolynomialRing( self.__field, names = 'x,y')
        loc = P.gens_dict()
        loc.update ( loc_f)
        self.__fcs = dict( (tuple( eval(f)),
                            sage_eval( fcs[f], locals = loc))
                           for f in fcs) if fcs else fcs
        loc = self.field().gens_dict()
        self.__evs = dict( (eval(l), sage_eval( evs[l], locals = loc_f)) for l in evs)\
            if evs else evs
        self.__explicit_formula = smple.get( 'explicit_formula')


    def collection( self):
        return self.__collection

    def name( self):
        return self.__name

    def weight( self):
        return self.__weight

    def field( self):
        return self.__field

    def Fourier_coefficients( self):
        return self.__fcs

    def eigenvalues( self):
        return self.__evs

    def explicit_formula( self):
        return self.__explicit_formula


    
            

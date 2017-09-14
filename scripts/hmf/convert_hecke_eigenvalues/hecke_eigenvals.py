# If Hecke eigenfield is in the LMFDB, expresses eigenvalues in terms of listed integral basis
# TODO: Integrate with LLL-reduced basis? (see NotImplementedError below)

import pymongo, hashlib
from sage.all import PolynomialRing, QQ, preparse, gp, NumberField, matrix, vector
#from sage.all import *

#P = subprocess.Popen(["ssh","mongo","-N"])
_C = None

def makeDBconnection():
    global _C
    _C = pymongo.MongoClient("localhost:37010");
    #_C = pymongo.MongoClient("m0.lmfdb.xyz:27017");
    #_C = pymongo.MongoClient("readonly.lmfdb.xyz:27017");
    _C.admin.authenticate("lmfdb","lmfdb")

def getDBconnection():
    if _C is None:
        makeDBconnection()
    return _C

def get_hmfs_hecke_field_and_eigenvals(label):
    """Get the Hecke field and eigenvalues for the Hilbert modular form with given label.

    INPUT:
        label -- string, the label of the Hilbert modular form

    OUTPUT:
        K_old -- number field, the field containing the Hecke eigenvalues
        e -- number field element, a generator for K_old over QQ
        eigenvals -- list, a list of the Hecke eigenvalues
    """
    C = getDBconnection()
    # Should I use find_one, or something else?
    R = PolynomialRing(QQ,names=('x'))
    form = C.hmfs.forms.find_one({'label':label})
    poly = R(str(form['hecke_polynomial']))
    K_old = NumberField(poly, names=('e',))
    (e,) = K_old._first_ngens(1)
    eigenvals_str = form['hecke_eigenvalues']
    eigenvals = [K_old(eval(preparse(el))) for el in eigenvals_str]
    return K_old, e, eigenvals

def polredabs_coeffs(poly):
    """Apply gp.polredabs to the given polynomial and return the coefficients as a comma-separated string.

    INPUT:
        poly -- polynomial, a polynomial with coefficients in QQ

    OUTPUT:
        cs_string -- string, the coefficients of the normalized polynomial (the output of gp.polredabs(poly)), given as a comma-separated string with no spaces 
    """
    R = poly.parent()
    (x,) = R._first_ngens(1)
    poly_new = R(str(gp.polredabs(poly)))
    cs = poly_new.coefficients(sparse=False)
    cs_string = ",".join([str(el) for el in cs])
    return cs_string

def coeffs_to_poly(c_string):
    """Given a string of coefficients, returns the polynomial with those coefficients

    INPUT:
        c_string -- string, a a comma-separated string (with no spaces) of rational numbers

    OUTPUT:
        The polynomial with these coefficients
    """
    R = PolynomialRing(QQ, names=('x',))
    (x,) = R._first_ngens(1)
    tup = eval(c_string)
    return sum([tup[i]*x**i for i in range(0,len(tup))])

def field_coeffs_string_to_hash(c_string):
    """Given a string of coefficients, returns their hash

    INPUT:
        c_string -- string, a comma-separated string (with no spaces) of rational numbers

    OUTPUT:
        c_hash -- string, the hash of the string of coefficients
    """
    c_hash = hashlib.md5(c_string).hexdigest()
    return c_hash

def get_number_field_integral_basis(c_string):
    r"""Get the integral basis for the field specified by the string.

    INPUT:
        c_string -- string, a string of comma-separated coefficients with no spaces: the coefficients of the normalized (using gp.polredabs) defining polynomial

    OUTPUT:
        fld_bool -- bool, True if the number field has a page in the LMFDB, False otherwise
        K_new -- number field, the number field with defining polynomial that is the normalized version (given by gp.polredabs) of the one with coefficients specified by c_string
        a -- number field element, generator for K_new
        the integral basis for K_new recorded on its LMFDB page 
    """
    C = getDBconnection()
    c_hash = field_coeffs_string_to_hash(c_string)
    field = C.numberfields.fields.find_one({'coeffhash':c_hash})
    fld_bool = True
    try:
        field['degree']
    except TypeError:
        fld_bool = False
    if fld_bool:
        field_str = field['coeffs']
        int_basis_str = field['zk']
        poly = coeffs_to_poly(field_str)
        K_new = NumberField(poly, names=('a',))
        (a,) = K_new._first_ngens(1)
        return fld_bool, K_new, a, [K_new(eval(preparse(el))) for el in int_basis_str]
    else:
        # could add polynomial to list of number fields missing from LMFDB here
        return fld_bool, None, None, None

def vector_to_string(vec):
    """Convert vector of integers to string

    INPUT:
        vec -- vector, a vector of integers

    OUTPUT:
        A comma-separated string with no spaces containing the integers in vec
    """
    vec_string = ""
    for i in range(0,len(vec)-1):
        vec_string += str(vec[i]) + ","
    vec_string += str(vec[len(vec)-1]) # don't forget to append last entry!
    return vec_string

def convert_hecke_eigenvalues(K_old, eigenvals, K_new, int_basis):
    """Re-express the Hecke eigenvalues in terms of the integral basis given in the LMFDB

    INPUT:
        K_old -- the field containing the Hecke eigenvalues
        eigenvals -- the Hecke eigenvalues, in terms of a field generator (usually the eigenvalue for T_2) for the field K_old
        K_new -- a "nicer" field isomorphic to K_old (often one whose polynomial has been polredabs'd)
        int_basis -- an integral basis for the ring of integers of K_new

    OUTPUT:
        eigenvals_new -- list, a list of strings of the coefficients of the Hecke eigenvalues with respect to the integral basis recorded in the LMFDB
        K_new -- number field, the (normalized) number field containing the Hecke eigenvalues, as given in the LMFDB
        a -- number field element, the generator for the field K_new
        int_basis -- list, a list containing the integral basis for K_new
    """
    if not K_old.is_isomorphic(K_new):
        return "Error! Fields not isomorphic!"
    iota = K_old.embeddings(K_new)[0]
    (a,) = K_new._first_ngens(1)

    # make change of basis matrix
    chg_basis_entries = []
    for el in int_basis:
        chg_basis_entries.append(el.list())
    chg_basis_mat = matrix(chg_basis_entries) # changes from int_basis to 1, a, a^2, ..., a^(n-1)
    chg_basis_mat = chg_basis_mat.inverse() # changes from 1, a, a^2, ..., a^(n-1) to int_basis

    # convert entries
    eigenvals_new = []
    for el in eigenvals:
        v = vector(iota(el).list())
        eigenvals_new.append(v*chg_basis_mat)

    # verify correctness of new expression for eigenvalues
    eigenvals_old = [iota(el) for el in eigenvals]
    for j in range(0,len(eigenvals)):
        new_val = 0
        for i in range(0,len(int_basis)):
            new_val += eigenvals_new[j][i]*int_basis[i]
        assert new_val == eigenvals_old[j]

    eigen_strings = []
    for c in eigenvals_new:
        eigen_strings.append(vector_to_string(c))   
    return eigen_strings, K_new, a, int_basis

# Wrapper for above functions
def convert_hmfs_hecke_eigenvalues_from_label(label):
    """Given the label of a Hilbert modular form, look for the entry of its Hecke eigenfield in the LMFDB and re-express the Hecke eigenvalues in terms of the integral basis given there

    INPUT:
        label -- string, the label of a Hilbert modular form

    OUTPUT:
        eigenvals_new -- list, a list of strings of the coefficients of the Hecke eigenvalues with respect to the integral basis recorded in the LMFDB
        K_new -- number field, the (normalized) number field containing the Hecke eigenvalues, as given in the LMFDB
        a -- number field element, the generator for the field K_new
        int_basis -- list, a list containing the integral basis for K_new
    """
    K_old, e, eigenvals = get_hmfs_hecke_field_and_eigenvals(label)
    old_poly = K_old.defining_polynomial()
    c_string = polredabs_coeffs(old_poly)
    fld_bool, K_new, a, int_basis = get_number_field_integral_basis(c_string)
    if not fld_bool:
        raise NotImplementedError("No number field entry found in the LMFDB.")
    else:
        return convert_hecke_eigenvalues(K_old, eigenvals, K_new, int_basis)


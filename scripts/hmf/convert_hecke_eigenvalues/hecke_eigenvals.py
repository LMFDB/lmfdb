import pymongo, hashlib
from sage.all import PolynomialRing, QQ, preparse, gp, NumberField, Integer, magma
#from sage.all import *

#P = subprocess.Popen(["ssh","mongo","-N"])
_C = None

def makeDBconnection():
	global _C
	#_C = pymongo.MongoClient("localhost:37010");
	#_C = pymongo.MongoClient("m0.lmfdb.xyz:27017");
	_C = pymongo.MongoClient("readonly.lmfdb.xyz:27017");
	_C.admin.authenticate("lmfdb","lmfdb")

def getDBconnection():
	if _C is None:
		makeDBconnection()
	return _C

def get_hmfs_hecke_field_and_eigenvals(label):
	# Input: The label of the Hilbert modular form, given as a string
	# Output: The polynomial defining the number field containing the Hecke eigenvalues, the generator for the field, and the eigenvalues
	C = getDBconnection()
	# Should I use find_one, or something else?
	R = PolynomialRing(QQ,names=('x'))
	form = C.hmfs.forms.find_one({'label':label})
	poly = R(str(form['hecke_polynomial']))
	K_old = NumberField(poly, names=('e',))
	(e,) = K_old._first_ngens(1)
	eigenvals_str = form['hecke_eigenvalues']
	eigenvals = [eval(preparse(el)) for el in eigenvals_str]
	return K_old, e, eigenvals

def polredabs_coeffs(poly):
	# Input: A polynomial with coeffs in QQ
	# Output: The coefficients of polredabs of that polynomial, given as a string with no spaces
	R = poly.parent()
	(x,) = R._first_ngens(1)
	poly_new = R(str(gp.polredabs(poly)))
	cs = poly_new.coefficients(sparse=False)
	cs_string = ",".join([str(el) for el in cs])
	return cs_string

def coeffs_to_poly(c_string):
	# Input: A string of comma-separated coefficients with no spaces
	# Output: The polynomial with these coefficients
	R = PolynomialRing(QQ, names=('x',))
	(x,) = R._first_ngens(1)
	tup = eval(c_string)
	return sum([tup[i]*x**i for i in range(0,len(tup))])

def field_coeffs_string_to_hash(c_string):
	# Input: A string of comma-separated coefficients with no spaces
	# Output: The hash of these coefficients
	c_hash = hashlib.md5(c_string).hexdigest()
	return c_hash

def get_number_field_integral_basis(c_string):
	# Input: A string of comma-separated coefficients with no spaces (the coefficients for the defining polynomial, polredabs'd)
	# Output: The corresponding field, the generator for the field, and the integral basis recorded in the LMFDB
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
		return fld_bool, K_new, a, [eval(preparse(el)) for el in int_basis_str]
	else:
		#could add polynomial to list of number fields missing from LMFDB here
		return fld_bool, None, None, None

def convert_hmfs_hecke_eigenvalues(label):
	# Wrapper for above functions
	# Input: A label for a Hilbert modular form
	# Output: Coefficients for the Hecke eigenvalues written in terms of int_basis, the Hecke eigenfield K_new as given in the LMFDB, the generator for K_new listed, an integral basis for K_new
	K_old, e, eigenvals = get_hmfs_hecke_field_and_eigenvals(label)
	old_poly = K_old.defining_polynomial()
	c_string = polredabs_coeffs(old_poly)
	fld_bool, K_new, a, int_basis = get_number_field_integral_basis(c_string)
	if not fld_bool:
		return "No number field file found in LMFDB."
	magma.load("convert.m")
	eigenvals_new = magma.ConvertHeckeEigenvalues(K_old, eigenvals, K_new, int_basis)
	return eigenvals_new, K_new, a, int_basis
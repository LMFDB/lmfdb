# -*- coding: utf-8 -*-
import base
from sage.all import *
import re
import pymongo
import bson
from utils import *
from transitive_group import group_display_short
#logger = make_logger("DC")

def na_text():
  return "Not computed"

## Turn a list into a string (without brackets)
def list2string(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def string2list(s):
  s = str(s)
  if s=='': return []
  return [int(a) for a in s.split(',')]

def decodedisc(ads, s):
  return ZZ(ads[3:])*s

class WebNumberField:
  """
   Class for retrieving number field information from the database
  """
  def __init__(self, label, data=None):
    self.label = label
    if data is None:
      self._data = self._get_dbdata()
    else:
      self._data = data

  # works with a string, or a list of coefficients
  @classmethod
  def from_coeffs(cls, coeffs):
    if isinstance(coeffs, list):
      coeffs = list2string(coeffs)
    if isinstance(coeffs, str):
      nfdb = base.getDBConnection().numberfields.fields
      f = nfdb.find_one({'coeffs': coeffs})
      if f is None:
        return cls('a')  # will initialize data to None
      return cls(f['label'], f)
    else:
      raise Exception('wrong type')

  # If we already have the database entry
  @classmethod
  def from_data(cls, data):
    return cls(data['label'], data)

  def _get_dbdata(self):
    nfdb = base.getDBConnection().numberfields.fields
    return nfdb.find_one({'label': self.label})

  # Return discriminant as a sage int
  def disc(self):
    return decodedisc(self._data['disc_abs_key'], self._data['disc_sign'])

  # Return a nice string for the Galois group
  def galois_string(self):
    n = self._data['degree']
    t = self._data['galois']['t']
    C = base.getDBConnection()
    return group_display_short(n, t, C)

  # Just return the t-number of the Galois group
  def galois_t(self):
    return self._data['galois']['t']

  def coeffs(self):
    return string2list(self._data['coeffs'])

  def signature(self):
    return string2list(self._data['sig'])

  def degree(self):
    return self._data['degree']

  def poly(self):
    return coeff_to_poly(string2list(self._data['coeffs']))

  def haskey(self, key):
    return key in self._data

  def K(self):
    if not self.haskey('K'):
      self._data['K'] = NumberField(self.poly(), 'a')
    return self._data['K']

  def unit_rank(self):
    if not self.haskey('unit_rank'):
      sig = self.signature()
      self._data['unit_rank'] = unit_rank = sig[0]+sig[1]-1
    return self._data['unit_rank']

  def regulator(self):
    if self.haskey('reg'): return self._data['reg']
    if self.unit_rank() ==0:
      return 1
    if self.haskey('class_number'):
      K = self.K()
      return K.regulator()
    return na_text()

  def units(self): # fundamental units
    if self.haskey('units'): 
      return ',&nbsp; '.join(self._data['units'])
    if self.unit_rank() == 0:
      return ''
    if self.haskey('class_number'):
      K = self.K()
      units = [web_latex(u) for u in K.unit_group().fundamental_units()]
      units = ',&nbsp; '.join(units)
      return units
    return na_text()

  def disc_factored_latex(self):
    D = self.disc()
    s = ''
    if D<0:
      D= -D
      s = r'-\,'
    return s+ latex(D.factor())

  def web_poly(self):
    return pol_to_html(str(coeff_to_poly(self.coeffs())))

  def class_group_invariants(self):
    if not self.haskey('cl_group'):
      return na_text()
    cg_list = string2list(self._data['cl_group'])    
    if cg_list == []:
      return 'Trivial'
    return cg_list

  def class_group_invariants_raw(self):
    if not self.haskey('cl_group'):
      return [-1]
    return string2list(self._data['cl_group'])    

  def class_group(self):
    if self.haskey('cl_group'):
      cg_list = string2list(self._data['cl_group'])
      return str(AbelianGroup(cg_list)) + ', order ' + str(self._data['class_number'])
    return na_text()

  def class_number(self):
    if self.haskey('class_number'):
      return self._data['class_number']
    return na_text()

  def is_null(self):
    return self._data is None
    
